#!/usr/bin/env python3
"""
EDA Validación Satélite vs Tierra — S5P vs DAGMA (≥6 visualizaciones)
======================================================================
• Scatter S5P vs DAGMA por contaminante y estación
• Serie temporal dual (S5P + DAGMA superpuestos)
• Mapa de sesgo espacial
• Diagrama de Taylor
• Densidad condicional del error vs nubosidad
• RMSE móvil en el tiempo
"""

import json, warnings
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns
from scipy import stats
import rasterio

ROOT = Path(__file__).resolve().parent.parent.parent
S5P_L3_DIR = ROOT / "data" / "sentinel5p" / "l3"
DAGMA_CSV_DIR = ROOT / "data" / "dagma" / "raw"
OUT_DIR = ROOT / "outputs" / "eda" / "validacion"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DPI = 150
warnings.filterwarnings("ignore")

TARGETS = {"NO2": "tropospheric_NO2_column_number_density", "SO2": "SO2_column_number_density", "O3": "O3_column_number_density"}
DAGMA_STATIONS = {
    "ERA OBRERO": (-76.5065, 3.4573), "LA ERMITA": (-76.532, 3.451),
    "UNIVERSIDAD DEL VALLE": (-76.534, 3.375), "PANCE": (-76.5313, 3.3045),
    "BASE AÉREA": (-76.488, 3.478), "COMPARTIR": (-76.4666, 3.4283),
    "LA FLORA": (-76.518, 3.478), "CAÑAVERALEJO": (-76.511, 3.417),
    "TRANSITORIA-NAVARRO": (-76.482, 3.426),
    "ACOPI": (-76.5019, 3.5164), "LAS AMÉRICAS": (-76.4994, 3.5371),
    "YUMBO-ALBERTO MENDOZA": (-76.495, 3.570),
}
COORDS = {"NO2": (3.30, -76.60, 3.55, -76.40), "SO2": (3.30, -76.60, 3.55, -76.40), "O3": (3.30, -76.60, 3.55, -76.40)}
GRID_SIZE = 0.01

def lonlat_to_pixel(lon, lat, bbox=(-77.00, 5.00, -75.79, 2.99)):
    col = int(round((lon - bbox[0]) / 0.01))
    row = int(round((bbox[1] - lat) / 0.01))
    return row, col

def save(name):
    p = OUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(); return p

print("Cargando DAGMA ground truth...")
dagma_files = sorted(DAGMA_CSV_DIR.glob("g4t8_*.csv"))
dagma_chunks = []
for f in dagma_files:
    for chunk in pd.read_csv(f, usecols=["nombre_est","msfl_code","med_concentracion_estandar",
        "med_fecha_inicio","latitud","longitud","nombre_fgda"],
        chunksize=50000, encoding="utf-8", on_bad_lines="skip"):
        chunk["fecha"] = pd.to_datetime(chunk["med_fecha_inicio"], errors="coerce")
        chunk["valor"] = pd.to_numeric(chunk["med_concentracion_estandar"], errors="coerce")
        chunk = chunk.dropna(subset=["fecha","valor"])
        dagma_chunks.append(chunk[["nombre_est","msfl_code","valor","fecha","latitud","longitud","nombre_fgda"]])
dagma = pd.concat(dagma_chunks, ignore_index=True)
dagma["fecha_dia"] = dagma["fecha"].dt.date
print(f"  DAGMA: {len(dagma):,} registros, {dagma['nombre_est'].nunique()} estaciones")

# ── Acumular S5P datos por estación ──
print("Emparejando S5P con DAGMA...")
date_inventory = []
for yd in sorted(S5P_L3_DIR.iterdir()):
    if not yd.is_dir(): continue
    try: y = int(yd.name)
    except: continue
    for md in sorted(yd.iterdir()):
        if not md.is_dir(): continue
        for dd in sorted(md.iterdir()):
            if not dd.is_dir(): continue
            try: m, d = int(md.name), int(dd.name); dt = pd.Timestamp(y, m, d)
            except: continue
            date_inventory.append((dt, dd))

# Mapa fecha → dir
date_map = {}
for dt, dd in date_inventory:
    date_map[dt.date()] = dd

records = []
target_dates = set(dagma["fecha_dia"].unique())
n_matched = 0

for i, (fecha_dia, station_group) in enumerate(dagma.groupby("fecha_dia")):
    if fecha_dia not in date_map: continue
    day_dir = date_map[fecha_dia]
    cloud_path = day_dir / "CLOUD.tif"
    if not cloud_path.exists(): continue
    try:
        with rasterio.open(cloud_path) as src:
            cloud = src.read(1).astype(np.float32)
    except: continue

    # Leer contaminantes
    arrays = {}
    for prod in TARGETS:
        tp = day_dir / f"{prod}.tif"
        if tp.exists():
            try:
                with rasterio.open(tp) as src:
                    arrays[prod] = src.read(1).astype(np.float32)
            except: pass

    if not arrays: continue

    for _, row in station_group.iterrows():
        st_name = row["nombre_est"]
        var = row["msfl_code"]
        if var not in TARGETS: continue

        lon, lat = row["longitud"], row["latitud"]
        r, c = lonlat_to_pixel(lon, lat)
        if r < 0 or r >= cloud.shape[0] or c < 0 or c >= cloud.shape[1]: continue
        cloud_val = cloud[r, c]
        is_clean = cloud_val <= 0.3

        s5p_val = np.nan
        if var in arrays:
            s5p_arr = arrays[var]
            if r < s5p_arr.shape[0] and c < s5p_arr.shape[1]:
                s5p_val = s5p_arr[r, c]

        if not np.isnan(s5p_val) and s5p_val > 0:
            records.append({
                "fecha": fecha_dia, "estacion": st_name, "variable": var,
                "dagma": row["valor"], "s5p": s5p_val, "cloud_frac": float(cloud_val),
                "is_clean": is_clean, "lon": lon, "lat": lat,
            })
            n_matched += 1
    if (i+1) % 500 == 0:
        print(f"  Procesadas {i+1} fechas, {n_matched} emparejamientos...")

match_df = pd.DataFrame(records)
print(f"\n  Total emparejamientos: {len(match_df)}")
for var in TARGETS:
    n = len(match_df[match_df["variable"]==var])
    print(f"    {var}: {n}")

if len(match_df) < 50:
    print("POCOS DATOS. Verifique S5P.")
    exit(1)

# ── Convertir S5P a µmol/m² ──
match_df["s5p_umol"] = match_df["s5p"] * 1e6

# ═══ 1. Scatter S5P vs DAGMA ═══
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
for ax, var in zip(axes, TARGETS):
    dv = match_df[(match_df["variable"]==var) & match_df["is_clean"]]
    if len(dv) < 10: ax.text(0.5,0.5,f"{var}: n={len(dv)}",ha="center",va="center",transform=ax.transAxes); continue
    sl, ic, r, p, _ = stats.linregress(dv["dagma"], dv["s5p_umol"])
    ax.scatter(dv["dagma"], dv["s5p_umol"], alpha=0.15, s=8, c={"NO2":"#E53935","SO2":"#FF9800","O3":"#4CAF50"}[var])
    xf = np.linspace(dv["dagma"].min(), dv["dagma"].max(), 100)
    ax.plot(xf, sl*xf+ic, "k-", lw=2, label=f"r={r:.3f}\nR²={r**2:.3f}")
    ax.plot(xf, xf, "gray", ls=":", alpha=0.5, label="1:1")
    ax.set_xlabel(f"DAGMA {var}"); ax.set_ylabel(f"S5P {var} [µmol/m²]")
    ax.set_title(f"{var}\nn={len(dv)}", fontsize=11); ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
fig.suptitle("Fig 1: S5P (satélite) vs DAGMA (ground truth) — solo píxeles limpios", fontweight="bold", fontsize=13)
fig.tight_layout(); save("01_scatter_s5p_vs_dagma")

# ═══ 2. Serie temporal dual ═══
fig, axes = plt.subplots(3, 1, figsize=(16, 12))
for ax, var in zip(axes, TARGETS):
    dv = match_df[(match_df["variable"]==var) & match_df["is_clean"]]
    if len(dv) < 10: continue
    # DAGMA daily mean
    d_daily = dv.groupby("fecha")["dagma"].mean()
    s_daily = dv.groupby("fecha")["s5p_umol"].mean()
    common = sorted(set(d_daily.index) & set(s_daily.index))
    ax.plot(common, [d_daily.get(d,np.nan) for d in common], "o-", lw=1, markersize=3, color={"NO2":"#E53935","SO2":"#FF9800","O3":"#4CAF50"}[var], alpha=0.6, label="DAGMA")
    ax.plot(common, [s_daily.get(d,np.nan) for d in common], "s--", lw=1, markersize=3, color="black", alpha=0.6, label="S5P")
    ax.set_ylabel(var); ax.legend(fontsize=7); ax.grid(alpha=0.3)
ax.set_xlabel("Fecha"); axes[0].set_title("Fig 2: Serie temporal dual S5P+DAGMA (media diaria)", fontweight="bold")
fig.tight_layout(); save("02_serie_temporal_dual")

# ═══ 3. Mapa de sesgo espacial ═══
fig, ax = plt.subplots(figsize=(12, 8))
bias_by_station = match_df[match_df["is_clean"]].groupby(["estacion","lon","lat"]).agg(
    bias_mean=("s5p_umol", lambda x: (x.mean())),
    bias_std=("dagma", lambda x: x.std()),
    n=("dagma", "count"),
).reset_index()
for _, r in bias_by_station.iterrows():
    size = np.log10(r["n"]+1) * 50
    color = "red" if r["bias_mean"] > 0 else "blue"
    ax.scatter(r["lon"], r["lat"], s=size, c=color, alpha=0.6, edgecolors="black", linewidth=0.5)
    ax.annotate(f"{r['estacion'][:10]}\n{r['bias_mean']:.1f}", (r["lon"], r["lat"]), fontsize=6, ha="center")
ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud"); ax.grid(alpha=0.3)
ax.set_title("Fig 3: Sesgo espacial S5P vs DAGMA (tamaño = n, rojo = sobreestimación)", fontweight="bold")
save("03_mapa_sesgo")

# ═══ 4. Diagrama de Taylor (simplificado) ═══
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
theta = np.linspace(0, np.pi/2, 100)
ax.plot(theta, np.ones_like(theta), "k--", alpha=0.3)
# Normalized std vs correlation
for var, col in [("NO2","#E53935"), ("SO2","#FF9800"), ("O3","#4CAF50")]:
    dv = match_df[(match_df["variable"]==var) & match_df["is_clean"]]
    if len(dv) < 10: continue
    # Aggregate per date
    s = dv.groupby("fecha")["s5p_umol"].mean(); d = dv.groupby("fecha")["dagma"].mean()
    common = sorted(set(s.index) & set(d.index))
    s_v, d_v = np.array([s[c] for c in common]), np.array([d[c] for c in common])
    if len(s_v) < 5: continue
    r_val, _ = stats.pearsonr(s_v, d_v)
    norm_std = np.std(s_v) / (np.std(d_v) + 1e-10)
    theta_val = np.arccos(min(r_val, 0.999))
    ax.scatter(theta_val, norm_std, s=200, c=col, edgecolors="white", zorder=5, label=f"{var} (r={r_val:.3f})")
    ax.annotate(var, (theta_val, norm_std), textcoords="offset points", xytext=(10, 10), fontsize=9)
ax.set_ylim(0, 2); ax.set_title("Fig 4: Diagrama de Taylor", fontweight="bold")
ax.legend(fontsize=8, loc="upper right"); save("04_diagrama_taylor")

# ═══ 5. Densidad condicional del error ═══
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
for ax, var in zip(axes, TARGETS):
    dv = match_df[match_df["variable"]==var].copy()
    if len(dv) < 20: continue
    dv["error"] = (dv["s5p_umol"] - dv["dagma"]) / (dv["dagma"] + 1e-10)
    dv["error"] = dv["error"].clip(-5, 5)
    ax.scatter(dv["cloud_frac"], dv["error"], alpha=0.1, s=5, c={"NO2":"#E53935","SO2":"#FF9800","O3":"#4CAF50"}[var])
    sl, ic, r, p, _ = stats.linregress(dv["cloud_frac"].dropna(), dv["error"].dropna())
    ax.plot([0, 1], [ic, sl+ic], "k-", lw=2, label=f"r={r:.3f}")
    ax.axhline(0, color="gray", ls=":"); ax.set_xlabel("Cloud fraction"); ax.set_ylabel("Error relativo")
    ax.set_title(f"{var} (n={len(dv)})"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
fig.suptitle("Fig 5: Error S5P vs DAGMA en función de nubosidad", fontweight="bold", fontsize=13)
fig.tight_layout(); save("05_error_vs_nubes")

# ═══ 6. RMSE móvil ═══
fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True)
for ax, var in zip(axes, TARGETS):
    dv = match_df[(match_df["variable"]==var) & match_df["is_clean"]]
    if len(dv) < 30: continue
    rmse_series = []
    dates_series = []
    for fecha in sorted(dv["fecha"].unique()):
        dfecha = dv[dv["fecha"]==fecha]
        if len(dfecha) < 2: continue
        rmse = np.sqrt(np.mean((dfecha["s5p_umol"] - dfecha["dagma"])**2))
        rmse_series.append(rmse); dates_series.append(fecha)
    rolling = pd.Series(rmse_series).rolling(30, min_periods=5, center=True).mean()
    ax.plot(dates_series, rmse_series, alpha=0.3, lw=0.5, color={"NO2":"#E53935","SO2":"#FF9800","O3":"#4CAF50"}[var])
    ax.plot(dates_series, rolling.values, lw=2, color="black")
    ax.set_ylabel(f"{var} RMSE"); ax.grid(alpha=0.3)
axes[0].set_title("Fig 6: RMSE móvil S5P vs DAGMA (ventana 30 días)", fontweight="bold")
fig.tight_layout(); save("06_rmse_movil")

print(f"\n✅ EDA Validación completo → {OUT_DIR}")
print(f"   {len(list(OUT_DIR.glob('*.png')))} gráficas generadas")
