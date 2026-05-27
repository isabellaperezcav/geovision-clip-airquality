"""
build_artifacts.py - Genera los artefactos que sirve el backend GeoVision-CLIP Cali.

Producto (todo en ug/m3, concentracion de superficie):
  - grid_{no2,so2,o3}_{t1,t3,t7}.geojson : 9 superficies por ST-Kriging sobre DAGMA,
    con value y sigma por celda (poligonos de 0.005 grados sobre el BBox de Cali).
  - v11_pattern_{no2,so2,o3}.geojson      : capa overlay del patron espacial del modelo
    profundo v11 (puntos geolocalizados por sam_segment, valor relativo normalizado).
  - metadata.json                         : unidades, grilla, rangos por archivo.
  - validate.json                         : metricas LOO-CV vs DAGMA por estacion.

Diseno por contaminante (justificado por la cobertura DAGMA real):
  - O3  : 7 estaciones -> Kriging Ordinario espacial + LOO-CV espacial.
  - SO2 : 5 estaciones -> Kriging Ordinario espacial + LOO-CV espacial.
  - NO2 : 1 estacion (Univalle) -> el campo espacial no es resoluble con DAGMA; se ancla
          el nivel de Univalle y la textura intraurbana la aporta el patron del modelo v11.
          La validacion de NO2 es temporal (persistencia), no espacial.

Forecast T+1/T+3/T+7: reversion a la media AR(1) (el valor regresa hacia la climatologia
al crecer el horizonte, por eso los tres mapas evolucionan), con sigma = RMSE de
persistencia al horizonte (crece con el horizonte, cota conservadora del error).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import geostats as gs

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                      # raiz del repo
DAGMA_DIR = ROOT / "data" / "processed" / "dagma_target"
V11_DIR = Path(r"C:\Users\mitgar14\Downloads\v11_latefusion")
OUT_DIR = HERE / "artifacts"

BBOX = dict(xmin=-76.60, ymin=3.30, xmax=-76.40, ymax=3.55)
CELL = 0.005
POLLUTANTS = ["NO2", "SO2", "O3"]
HORIZONS = {"T1": 1, "T3": 3, "T7": 7}
MODEL_VERSION = "v11-latefusion+stkriging-dagma"

# Mapeo nombre DAGMA (overpass/meta) -> id/zona del frontend (domain.ts).
STATION_META = {
    "Base Aérea": ("base-aerea", "Base Aérea Marco Fidel Suárez", "Comuna 7"),
    "ERA Obrero": ("era-obrero", "ERA Obrero", "Comuna 9"),
    "Cañaveralejo": ("canaveralejo", "Cañaveralejo", "Comuna 19"),
    "Univalle": ("univalle", "Universidad del Valle", "Comuna 17"),
    "Pance": ("pance", "Pance", "Comuna 53"),
    "Transitoria": ("transitoria", "Estación Transitoria EDB Navarro", "Comuna 13"),
    "Compartir": ("compartir", "Compartir", "Comuna 21"),
    "La Flora": ("flora", "La Flora", "Comuna 2"),
    "La Ermita": ("ermita", "La Ermita", "Comuna 3"),
}


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def load_dagma():
    """Devuelve (coords, series): coords[estacion]=(lon,lat); series[(gas,estacion)]=np.array."""
    meta = json.loads((DAGMA_DIR / "meta.json").read_text(encoding="utf-8"))
    coords = {k: (v[0], v[1]) for k, v in meta["estaciones"].items()}

    ov = pd.read_parquet(DAGMA_DIR / "overpass.parquet")
    ov["fecha"] = pd.to_datetime(ov["fecha"])
    ov = ov.sort_values("fecha")
    series = {}
    for (gas, est), grp in ov.groupby(["variable", "estacion"]):
        series[(gas, est)] = grp["valor"].to_numpy(dtype=float)
    return coords, series


def load_v11_pattern():
    """
    Geolocaliza el parquet multihorizonte de v11 usando solo coords fiables
    (fuente_centroide == 'sam_segment') y filtra al BBox de Cali. Devuelve un DataFrame
    con [tile_id, lat, lon, P_NO2_T*, P_SO2_T*, P_O3_T*] o None si v11 no esta disponible.
    """
    jsonl = V11_DIR / "dataset_multimodal.jsonl"
    multi = V11_DIR / "predicciones_gru_multihorizonte.parquet"
    if not jsonl.exists() or not multi.exists():
        return None

    recs = [json.loads(l) for l in jsonl.open(encoding="utf-8")]
    dfj = pd.DataFrame(recs)
    seg = dfj[dfj.fuente_centroide == "sam_segment"]
    coord = seg.groupby("tile_idx").agg(lat=("lat", "mean"), lon=("lon", "mean")).reset_index()

    dfm = pd.read_parquet(multi)
    g = dfm.merge(coord.rename(columns={"tile_idx": "tile_id"}), on="tile_id", how="inner")
    inb = ((g.lon >= BBOX["xmin"]) & (g.lon <= BBOX["xmax"]) &
           (g.lat >= BBOX["ymin"]) & (g.lat <= BBOX["ymax"]))
    g = g[inb].drop_duplicates("tile_id").reset_index(drop=True)
    return g if len(g) else None


# ---------------------------------------------------------------------------
# Grilla
# ---------------------------------------------------------------------------

def make_grid():
    ncol = int(round((BBOX["xmax"] - BBOX["xmin"]) / CELL))   # 40 en lon
    nrow = int(round((BBOX["ymax"] - BBOX["ymin"]) / CELL))   # 50 en lat
    glon = BBOX["xmin"] + (np.arange(ncol) + 0.5) * CELL
    glat = BBOX["ymin"] + (np.arange(nrow) + 0.5) * CELL
    return glon, glat, nrow, ncol


def idw_on_grid(lons, lats, vals, glon, glat, power=2.0):
    """IDW de puntos dispersos a la grilla (para el patron v11)."""
    gl, ga = np.meshgrid(glon, glat)
    z = np.zeros_like(gl, dtype=float)
    lons, lats, vals = map(lambda a: np.asarray(a, float), (lons, lats, vals))
    for i in range(gl.shape[0]):
        for j in range(gl.shape[1]):
            d = np.sqrt((lons - gl[i, j]) ** 2 + (lats - ga[i, j]) ** 2)
            if np.any(d < 1e-9):
                z[i, j] = vals[int(np.argmin(d))]
            else:
                w = 1.0 / d ** power
                z[i, j] = float(np.sum(w * vals) / np.sum(w))
    return z


# ---------------------------------------------------------------------------
# Construccion de un grid (value, sigma) por contaminante y horizonte
# ---------------------------------------------------------------------------

def build_field(gas, hkey, coords, series, glon, glat, v11):
    """Devuelve (z, sigma) en ug/m3 para un contaminante y horizonte."""
    h = HORIZONS[hkey]
    estaciones = [e for (g, e) in series if g == gas]

    # forecast por estacion (reversion a la media AR(1): evoluciona con el horizonte)
    pts_lon, pts_lat, pts_val, sig_temp = [], [], [], []
    for est in estaciones:
        fc = gs.forecast_reversion(series[(gas, est)], h)
        if not np.isfinite(fc.valor) or est not in coords:
            continue
        lon, lat = coords[est]
        pts_lon.append(lon); pts_lat.append(lat)
        pts_val.append(fc.valor); sig_temp.append(fc.sigma)

    pts_lon = np.array(pts_lon); pts_lat = np.array(pts_lat)
    pts_val = np.array(pts_val); sig_temp = np.array(sig_temp)
    sigma_temporal = float(np.median(sig_temp)) if sig_temp.size else 0.0

    if pts_val.size >= 3:
        # Kriging espacial (O3, SO2)
        z, sig_k = gs.kriging_ordinario(pts_lon, pts_lat, pts_val, glon, glat)
        sigma = np.sqrt(sig_k ** 2 + sigma_temporal ** 2)
    elif pts_val.size >= 1:
        # NO2: anclar nivel de la unica estacion y modular con el patron v11.
        base = float(np.mean(pts_val))
        gl, ga = np.meshgrid(glon, glat)
        z = np.full(gl.shape, base, dtype=float)
        col = f"P_{gas}_{hkey}"
        if v11 is not None and col in v11.columns and len(v11) >= 4:
            patt = idw_on_grid(v11.lon, v11.lat, v11[col].to_numpy(), glon, glat)
            zc = (patt - np.nanmean(patt)) / (np.nanstd(patt) + 1e-12)
            z = base * (1.0 + 0.18 * np.clip(zc, -3, 3))   # textura suave del modelo
        # incertidumbre dominada por la no resolubilidad espacial
        sigma = np.full(gl.shape, np.sqrt(sigma_temporal ** 2 + (0.35 * base) ** 2))
    else:
        gl, _ = np.meshgrid(glon, glat)
        z = np.full(gl.shape, np.nan); sigma = np.full(gl.shape, np.nan)

    z = np.clip(z, 0.0, None)   # concentraciones no negativas
    return z, sigma


# ---------------------------------------------------------------------------
# Exportacion GeoJSON
# ---------------------------------------------------------------------------

def grid_to_geojson(z, sigma, glon, glat, path):
    """Escribe la superficie como FeatureCollection de poligonos (celdas)."""
    feats = []
    half = CELL / 2.0
    vmin = float(np.nanmin(z)); vmax = float(np.nanmax(z))
    smin = float(np.nanmin(sigma)); smax = float(np.nanmax(sigma))
    for i, lat in enumerate(glat):
        for j, lon in enumerate(glon):
            v = z[i, j]
            if not np.isfinite(v):
                continue
            x0, x1 = lon - half, lon + half
            y0, y1 = lat - half, lat + half
            feats.append({
                "type": "Feature",
                "properties": {"value": round(float(v), 4),
                               "sigma": round(float(sigma[i, j]), 4)},
                "geometry": {"type": "Polygon", "coordinates": [[
                    [round(x0, 6), round(y0, 6)], [round(x1, 6), round(y0, 6)],
                    [round(x1, 6), round(y1, 6)], [round(x0, 6), round(y1, 6)],
                    [round(x0, 6), round(y0, 6)],
                ]]},
            })
    fc = {
        "type": "FeatureCollection",
        "properties": {"valueMin": round(vmin, 4), "valueMax": round(vmax, 4),
                       "sigmaMin": round(smin, 4), "sigmaMax": round(smax, 4)},
        "features": feats,
    }
    path.write_text(json.dumps(fc), encoding="utf-8")
    return (vmin, vmax), (smin, smax)


def v11_pattern_to_geojson(gas, v11, path):
    """Capa overlay: puntos del modelo v11 con su valor relativo normalizado [0,1]."""
    col = f"P_{gas}_T1"
    if v11 is None or col not in v11.columns:
        return False
    vals = v11[col].to_numpy(dtype=float)
    rng = np.nanmax(vals) - np.nanmin(vals)
    norm = (vals - np.nanmin(vals)) / rng if rng > 1e-12 else np.zeros_like(vals)
    feats = []
    for (_, r), nv in zip(v11.iterrows(), norm):
        feats.append({
            "type": "Feature",
            "properties": {"tile_id": int(r.tile_id), "pattern": round(float(nv), 4)},
            "geometry": {"type": "Point", "coordinates": [round(float(r.lon), 6),
                                                          round(float(r.lat), 6)]},
        })
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}),
                    encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Validacion LOO-CV
# ---------------------------------------------------------------------------

def build_validation(coords, series):
    """LOO-CV espacial (O3, SO2) y validacion temporal (NO2). Contrato del frontend."""
    stations_out = {}     # id -> {id,name,zone,metrics:{gas:{rmse,mae,r2,bias,n}}}
    summary = {}

    for gas in POLLUTANTS:
        estaciones = [e for (g, e) in series if g == gas and e in coords]
        # valor representativo por estacion = mediana del overpass (clima local)
        lon = np.array([coords[e][0] for e in estaciones])
        lat = np.array([coords[e][1] for e in estaciones])
        val = np.array([float(np.median(series[(gas, e)])) for e in estaciones])

        if val.size >= 3:
            res = gs.loo_cv(lon, lat, val)
            pred, resid = res["pred"], res["resid"]
            glob = res["global"]
            summary[gas] = {"rmse": _r(glob.rmse), "mae": _r(glob.mae),
                            "r2": _r(glob.r2), "bias": _r(glob.bias),
                            "n": glob.n, "metodo": "LOSO-Kriging"}
            for k, est in enumerate(estaciones):
                if not np.isfinite(resid[k]):
                    continue
                _add_metric(stations_out, est, gas,
                            abs(float(resid[k])), abs(float(resid[k])),
                            float("nan"), float(resid[k]), int(series[(gas, est)].size))
        else:
            # NO2: validacion temporal por persistencia en la unica estacion
            for est in estaciones:
                s = series[(gas, est)]
                if s.size > 7:
                    e1 = s[1:] - s[:-1]
                    rmse = float(np.sqrt(np.mean(e1 ** 2)))
                    mae = float(np.mean(np.abs(e1)))
                    bias = float(np.mean(e1))
                else:
                    rmse = mae = bias = float("nan")
                _add_metric(stations_out, est, gas, _r(rmse), _r(mae),
                            float("nan"), _r(bias), int(s.size))
            summary[gas] = {"rmse": _r(rmse), "mae": _r(mae), "r2": None,
                            "bias": _r(bias), "n": int(s.size),
                            "metodo": "validacion temporal (1 estacion)"}

    stations = list(stations_out.values())
    return {
        "method": "LOO-CV",
        "modelVersion": MODEL_VERSION,
        "generatedAt": pd.Timestamp.now("UTC").isoformat(),
        "summary": summary,
        "stations": stations,
    }


def _add_metric(d, est, gas, rmse, mae, r2, bias, n):
    sid, name, zone = STATION_META.get(est, (est, est, ""))
    if sid not in d:
        d[sid] = {"id": sid, "name": name, "zone": zone, "metrics": {}}
    # _r() sanea NaN/inf -> None para que el JSON sea valido y serializable.
    d[sid]["metrics"][gas] = {"rmse": _r(rmse), "mae": _r(mae), "r2": _r(r2),
                              "bias": _r(bias), "n": int(n)}


def _r(x, nd=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), nd)


def _grade(value, min_thr, exc_thr, higher_is_better=True):
    """EXCELENTE/CUMPLE/NO_CUMPLE/NO_EVALUABLE segun umbral del PDF."""
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "NO_EVALUABLE"
    if higher_is_better:
        if value >= exc_thr: return "EXCELENTE"
        elif value >= min_thr: return "CUMPLE"
        else: return "NO_CUMPLE"
    else:
        if value <= exc_thr: return "EXCELENTE"
        elif value <= min_thr: return "CUMPLE"
        else: return "NO_CUMPLE"


def compute_kpis(summary, moran_all, sigma_grids):
    """
    Calcula los KPIs de Situacion 3 del PDF y los clasifica con grado semantico.
    moran_all: dict[(gas, hkey)] -> {I, p}
    sigma_grids: dict[(gas, hkey)] -> np.array sigma
    """
    kpis = {}

    # 1. R2 LOO-CV promedio de gases evaluables (SO2 + O3)
    evaluables = [g for g in ["SO2", "O3"] if summary.get(g, {}).get("r2") is not None]
    if evaluables:
        avg_r2 = float(np.mean([summary[g]["r2"] for g in evaluables]))
        kpis["r2_loo_avg"] = {
            "value": _r(avg_r2), "grade": _grade(avg_r2, 0.55, 0.75),
            "gases_evaluables": evaluables,
            "gases_excluidos": [g for g in POLLUTANTS if g not in evaluables],
            "thresholds": {"min": 0.55, "exc": 0.75},
        }
    else:
        kpis["r2_loo_avg"] = {"value": None, "grade": "NO_EVALUABLE",
                               "gases_evaluables": [], "gases_excluidos": POLLUTANTS}

    # 2. Indice Moran I (todos los mapas generados)
    moran_vals = [(g, h, moran_all.get((g, h))) for g in POLLUTANTS for h in HORIZONS
                  if moran_all.get((g, h)) and moran_all[(g, h)].get("I")]
    if moran_vals:
        min_I = min(m["I"] for _, _, m in moran_vals)
        max_p = max(m.get("p", 1.0) for _, _, m in moran_vals)
        n_pass = sum(1 for _, _, m in moran_vals if m["I"] > 0.30 and m.get("p", 1.0) < 0.05)
        n_total = len(moran_vals)
        if min_I > 0.50 and max_p < 0.05:
            grade = "EXCELENTE"
        elif min_I > 0.30 and max_p < 0.05:
            grade = "CUMPLE"
        else:
            grade = "NO_CUMPLE"
        kpis["moran_i"] = {
            "min_I": _r(min_I), "max_p": _r(max_p),
            "n_pass": n_pass, "n_total": n_total, "grade": grade,
            "thresholds": {"min_I": 0.30, "exc_I": 0.50, "max_p": 0.05},
        }
    else:
        kpis["moran_i"] = {"min_I": None, "max_p": None, "n_pass": 0, "n_total": 0,
                            "grade": "NO_EVALUABLE"}

    # 3. RMSE LOO-CV T+1 por gas
    kpis["rmse_t1"] = {}
    for gas in POLLUTANTS:
        if gas == "NO2":
            kpis["rmse_t1"][gas] = {"value": None, "grade": "NO_EVALUABLE",
                                     "reason": "una sola estacion DAGMA, LOO-CV no defendible"}
        elif gas in summary:
            rmse = summary[gas].get("rmse")
            thr = {"min": 6.0, "exc": 3.0} if gas == "SO2" else {"min": 12.0, "exc": 6.0}
            kpis["rmse_t1"][gas] = {
                "value": rmse,
                "grade": _grade(rmse, thr["min"], thr["exc"], False) if rmse else "NO_EVALUABLE",
                "thresholds": thr,
            }

    # 4. Degradacion ratio T+7/T+1 (sobre sigma mediana del Kriging, gases evaluables)
    ratios = []
    for gas in ["SO2", "O3"]:
        key1, key7 = (gas, "T1"), (gas, "T7")
        if key1 in sigma_grids and key7 in sigma_grids:
            s1 = float(np.nanmedian(sigma_grids[key1]))
            s7 = float(np.nanmedian(sigma_grids[key7]))
            if s1 > 0:
                ratios.append(s7 / s1 - 1.0)
    if ratios:
        ratio = float(np.mean(ratios))
        kpis["degradacion_ratio"] = {
            "value": _r(ratio), "grade": _grade(ratio, 0.60, 0.30, False),
            "gases": ["SO2", "O3"],
            "thresholds": {"min": 0.60, "exc": 0.30},
        }
    else:
        kpis["degradacion_ratio"] = {"value": None, "grade": "NO_EVALUABLE", "gases": ["SO2", "O3"]}

    return kpis


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    np.random.seed(gs.SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coords, series = load_dagma()
    v11 = load_v11_pattern()
    glon, glat, nrow, ncol = make_grid()
    print(f"grilla {nrow}x{ncol} | estaciones-gas: {len({k for k in series})} | "
          f"v11 tiles en Cali: {0 if v11 is None else len(v11)}")

    files_meta = []
    moran_all = {}    # (gas, hkey) -> {I, p}
    sigma_grids = {}  # (gas, hkey) -> np.array sigma
    for gas in POLLUTANTS:
        for hkey in HORIZONS:
            z, sigma = build_field(gas, hkey, coords, series, glon, glat, v11)
            slug = f"grid_{gas.lower()}_{hkey.lower()}.geojson"
            (vr, sr) = grid_to_geojson(z, sigma, glon, glat, OUT_DIR / slug)
            files_meta.append({"file": slug, "pollutant": gas, "horizon": f"T+{HORIZONS[hkey]}",
                               "valueRange": [round(vr[0], 4), round(vr[1], 4)],
                               "sigmaRange": [round(sr[0], 4), round(sr[1], 4)]})
            moran_all[(gas, hkey)] = gs.moran_global(z)
            sigma_grids[(gas, hkey)] = sigma
            print(f"  {slug}: value [{vr[0]:.3f},{vr[1]:.3f}] sigma [{sr[0]:.3f},{sr[1]:.3f}]")
        v11_pattern_to_geojson(gas, v11, OUT_DIR / f"v11_pattern_{gas.lower()}.geojson")

    moran_t1 = {g: moran_all.get((g, "T1")) for g in POLLUTANTS}

    metadata = {
        "generatedAt": pd.Timestamp.now("UTC").isoformat(),
        "seed": gs.SEED,
        "modelVersion": MODEL_VERSION,
        "units": "ug/m3",
        "target": "surface_concentration",
        "bbox": BBOX,
        "cellDeg": CELL,
        "gridShape": [nrow, ncol],
        "pollutants": POLLUTANTS,
        "horizons": ["T+1", "T+3", "T+7"],
        "moran": moran_t1,
        "notes": {
            "o3": "Kriging Ordinario sobre 7 estaciones DAGMA (overpass 12-14h). LOO-CV espacial.",
            "so2": "Kriging Ordinario sobre 5 estaciones DAGMA. LOO-CV espacial.",
            "no2": "Una sola estacion (Univalle): nivel anclado + textura del modelo v11. Validacion temporal.",
            "v11": "Capa overlay v11_pattern_*: patron espacial del modelo profundo (columna troposferica, normalizada).",
        },
        "files": files_meta,
    }
    (OUT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                                           encoding="utf-8")

    validation = build_validation(coords, series)
    kpis = compute_kpis(validation["summary"], moran_all, sigma_grids)
    validation["kpis"] = kpis
    (OUT_DIR / "validate.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
    print("Moran I (T+1):", {g: round(moran_t1[g].get("I", float('nan')), 3) if moran_t1[g] else None for g in POLLUTANTS})
    print("validate summary:", json.dumps(validation["summary"], ensure_ascii=False))
    print("KPIs:", json.dumps({k: v.get("grade") for k, v in kpis.items() if isinstance(v, dict) and "grade" in v}, ensure_ascii=False))
    print(f"OK -> {OUT_DIR}")


if __name__ == "__main__":
    main()
