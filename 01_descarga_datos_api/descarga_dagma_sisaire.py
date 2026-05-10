"""
=====================================================================
GeoVision-CLIP Cali — Descarga DAGMA — Ground Truth in-situ
Fuente: datos.gov.co (dataset g4t8-zkc3) · datos.cali.gov.co · SISAIRE
=====================================================================

Red de monitoreo DAGMA Cali (9 estaciones):
  1. BASE AÉREA          — Nororiente
  2. CAÑAVERALEJO        — Suroriente
  3. COMPARTIR           — Oriente
  4. ERA OBRERO          — Centro
  5. LA ERMITA           — Centro
  6. LA FLORA            — Norte
  7. PANCE               — Sur
  8. TRANSITORIA-NAVARRO — Oriente
  9. UNIVERSIDAD DEL VALLE — Sur

DATASETS:
  g4t8-zkc3 → Calidad del Aire en Colombia (IDEAM) — datos NO₂/SO₂/O₃
               Filtrar: nombre_fgda=DAGMA + msfl_code in (NO2,SO2,O3)
  jbjb-meez → ICA Cali (403 — no accesible via API)
  8e8d-7zqn → Cañaveralejo (403 — no accesible via API)

NOTA: Cobertura publicada ~2014–2021. Para 2022–2024 usar SISAIRE manual.
"""

import hashlib
import json
import time
from pathlib import Path

import pandas as pd
import requests

from config import DAGMA_DIR as BASE_DIR
from config import MANIFESTS_DIR, START_DATE, END_DATE, START_YEAR, END_YEAR
from config import check_disk_space, DISK_WARN_GB, check_ram

# ── Dataset único ─────────────────────────────────────────
DATASET_G4T8 = "g4t8-zkc3"

# ── Autoridades ambientales a incluir ─────────────────────
AUTORIDADES = ["DAGMA", "CVC"]

# ── Estaciones DAGMA + CVC en Cali–Yumbo ─────────────────
ESTACIONES = {
    # DAGMA — Cali urbano
    "BASE AEREA":              {"red": "DAGMA", "id": "BASE_AEREA",       "zona": "Nororiente",
                                "lat": 3.478, "lon": -76.488},
    "CAÑAVERALEJO":            {"red": "DAGMA", "id": "CANAVERALEJO",     "zona": "Suroriente",
                                "lat": 3.417, "lon": -76.511},
    "COMPARTIR":               {"red": "DAGMA", "id": "COMPARTIR",        "zona": "Oriente",
                                "lat": 3.432, "lon": -76.505},
    "ERA OBRERO":              {"red": "DAGMA", "id": "ERA_OBRERO",       "zona": "Centro",
                                "lat": 3.450, "lon": -76.525},
    "LA ERMITA":               {"red": "DAGMA", "id": "LA_ERMITA",        "zona": "Centro",
                                "lat": 3.451, "lon": -76.532},
    "LA FLORA":                {"red": "DAGMA", "id": "LA_FLORA",         "zona": "Norte",
                                "lat": 3.478, "lon": -76.518},
    "PANCE":                   {"red": "DAGMA", "id": "PANCE",            "zona": "Sur",
                                "lat": 3.338, "lon": -76.558},
    "TRANSITORIA-NAVARRO":     {"red": "DAGMA", "id": "TRANSITORIA",      "zona": "Oriente",
                                "lat": 3.426, "lon": -76.482},
    "UNIVERSIDAD DEL VALLE":   {"red": "DAGMA", "id": "UNIVALLE",         "zona": "Sur",
                                "lat": 3.375, "lon": -76.534},
    # CVC — Yumbo + Cali rural
    "ACOPI-CELSIA":            {"red": "CVC",   "id": "ACOPI_CELSIA",     "zona": "Yumbo",
                                "lat": 3.5164, "lon": -76.5019},
    "YUMBO-ALBERTO MENDOZA":   {"red": "CVC",   "id": "YUMBO_ALBERTO",    "zona": "Yumbo",
                                "lat": 3.5792, "lon": -76.4895},
    "LAS AMERICAS":            {"red": "CVC",   "id": "LAS_AMERICAS",     "zona": "Yumbo",
                                "lat": 3.5642, "lon": -76.4925},
    "CASCAJAL":                {"red": "CVC",   "id": "CASCAJAL",         "zona": "Cali rural",
                                "lat": 3.3173, "lon": -76.5211},
}

MANIFEST_PATH = MANIFESTS_DIR / "manifest_dagma.json"
SODA_PAGE_SIZE = 50000


# ── Utilidades ────────────────────────────────────────────
def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def normalizar_estacion(nombre: str) -> str | None:
    """Encuentra estación por nombre (case-insensitive, parcial)."""
    n = nombre.strip().upper().replace("Á","A").replace("É","E").replace("Í","I")
    n = n.replace("Ó","O").replace("Ú","U").replace("Ñ","N").replace("Ü","U")
    for ename in ESTACIONES:
        en = ename.upper().replace("Á","A").replace("É","E").replace("Í","I")
        en = en.replace("Ó","O").replace("Ú","U").replace("Ñ","N")
        # Coincidencia exacta o el nombre real está contenido en el campo
        if en == n or n.startswith(en) or en.startswith(n):
            return ename
    return None


# ── Descargar dataset g4t8-zkc3 (DAGMA) ──────────────────
def descargar_anio(anio: int) -> list[dict]:
    """
    Descarga un año completo de datos DAGMA desde g4t8-zkc3.
    Cada año empieza con offset=0 (evita timeouts de paginacion profunda).
    """
    entries_anio = []
    total_anio = 0
    offset = 0
    lote_anio = 0

    start = f"{anio}-01-01T00:00:00"
    end = f"{anio + 1}-01-01T00:00:00" if anio < END_YEAR else f"{END_YEAR}-12-31T23:59:59"
    auth_filter = " or ".join(f"nombre_fgda='{a}'" for a in AUTORIDADES)
    where_year = (
        f"({auth_filter}) "
        f"and med_fecha_inicio >= '{start}' "
        f"and med_fecha_inicio < '{end}'"
    )

    while True:
        check_ram(f"DAGMA {anio}")
        check_disk_space(f"DAGMA {anio}", fatal=False)

        params = {
            "$where": where_year,
            "$limit": SODA_PAGE_SIZE,
            "$offset": offset,
            "$order": "med_fecha_inicio ASC",
        }

        lote_path = BASE_DIR / "raw" / f"g4t8_{anio}_{lote_anio:03d}.csv"
        lote_path.parent.mkdir(parents=True, exist_ok=True)

        exito = False
        bytes_written = 0
        for intento in range(1, 4):
            try:
                resp = requests.get(
                    "https://www.datos.gov.co/resource/g4t8-zkc3.csv",
                    params=params, stream=True, timeout=600)
                resp.raise_for_status()
                with open(lote_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            bytes_written += len(chunk)
                exito = True
                break
            except requests.exceptions.RequestException as e:
                print(f"    {anio} offset={offset} intento {intento}/3: {e}")
                if intento < 3:
                    espera = 15 * intento
                    print(f"      Reintentando en {espera}s...")
                    time.sleep(espera)

        if not exito:
            print(f"    Abandonando {anio} offset={offset} tras 3 intentos.")
            break

        # Contar lineas
        lineas = 0
        with open(lote_path, "rb") as f:
            for _ in f:
                lineas += 1
        lineas -= 1  # menos header

        if lineas <= 0:
            lote_path.unlink(missing_ok=True)
            break

        total_anio += lineas
        print(f"    {anio} lote {lote_anio:02d} (offset={offset:>5}): "
              f"{lineas:>6} reg | {bytes_written/1e6:.1f} MB | año: {total_anio:>6}")

        import gc
        gc.collect()

        entries_anio.append({
            "dataset": "g4t8-zkc3",
            "anio": anio,
            "lote": lote_anio,
            "file": str(lote_path),
            "md5": md5_file(lote_path),
            "bytes": bytes_written,
            "registros": lineas,
        })

        if lineas < SODA_PAGE_SIZE:
            break

        lote_anio += 1
        offset += SODA_PAGE_SIZE
        time.sleep(1.0)

    return entries_anio


def descargar_g4t8() -> list[dict]:
    """
    Descarga todos los anos DAGMA, un ano a la vez.
    Cada ano usa paginacion fresca (evita timeouts de Socrata con offsets grandes).
    """
    print("\n  [DAGMA] g4t8-zkc3: Calidad del Aire Colombia (IDEAM)")
    print("          Descargando por año para evitar timeouts...")

    entries = []
    total = 0

    for anio in range(START_YEAR, END_YEAR + 1):
        print(f"\n  --- Año {anio} ---")
        e = descargar_anio(anio)
        if e:
            regs = sum(x["registros"] for x in e)
            mb = sum(x["bytes"] for x in e) / 1e6
            print(f"  [DAGMA] {anio}: {len(e)} lotes, {regs} registros, {mb:.1f} MB")
            entries.extend(e)
            total += regs

    print(f"\n  [DAGMA] Total: {total} registros en {len(entries)} lotes")
    return entries


# ── Estrategia B: archivos manuales ──────────────────────
def procesar_manuales() -> list[dict]:
    """Procesa CSVs en data/dagma/manuales/<ESTACION>/ de SISAIRE o datos.cali.gov.co."""
    manual_dir = BASE_DIR / "manuales"
    if not manual_dir.exists():
        return []

    entries = []
    print(f"\n  [DAGMA] Archivos manuales: {manual_dir}")
    for est_dir in manual_dir.iterdir():
        if not est_dir.is_dir():
            continue
        for csv_path in est_dir.glob("*.csv"):
            try:
                data = csv_path.read_bytes()
                dest = BASE_DIR / est_dir.name / csv_path.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                entries.append({
                    "estacion": est_dir.name,
                    "file": str(dest),
                    "fuente": "manual",
                    "md5": md5_bytes(data),
                    "bytes": len(data),
                })
                print(f"    OK {est_dir.name}/{csv_path.name}")
            except Exception as e:
                print(f"    Error {csv_path}: {e}")
    return entries


# ── GeoJSON ──────────────────────────────────────────────
def guardar_geojson():
    features = []
    for ename, info in ESTACIONES.items():
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [info["lon"], info["lat"]]},
            "properties": {"id": info["id"], "nombre": ename,
                           "zona": info["zona"], "red": info["red"]},
        })
    path = BASE_DIR / "estaciones_dagma.geojson"
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"\n  [DAGMA] GeoJSON: {path} ({len(features)} estaciones)")


# ── Reporte de estaciones ────────────────────────────────
def reporte_estaciones():
    print(f"\n{'='*60}")
    print("  ESTACIONES — Ground Truth Cali + Yumbo")
    print(f"{'='*60}")
    print(f"  {'Estacion':<30} {'Red':<6} {'Zona':<14} {'Lat':>7} {'Lon':>9}")
    print(f"  {'-'*30} {'-'*6} {'-'*14} {'-'*7} {'-'*9}")
    for ename, info in ESTACIONES.items():
        print(f"  {ename:<30} {info['red']:<6} {info['zona']:<14} "
              f"{info['lat']:>7.4f} {info['lon']:>9.4f}")
    print(f"{'='*60}")


# ── Main ──────────────────────────────────────────────────
def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    check_disk_space("DAGMA")

    print("=" * 60)
    print("  GeoVision-CLIP Cali — Descarga Ground Truth")
    print("=" * 60)
    print(f"  Datos en: {BASE_DIR}")
    print(f"  Dataset: {DATASET_G4T8}")
    print(f"  Redes: {', '.join(AUTORIDADES)}")
    print(f"  Estaciones documentadas: {len(ESTACIONES)}")
    print(f"  Descarga por año (evita timeouts)")

    reporte_estaciones()

    # Estrategia A: API (todos los contaminantes DAGMA)
    entries = descargar_g4t8()

    # Estrategia B: manuales (SISAIRE para 2022-2024)
    entries += procesar_manuales()

    total_bytes = sum(e.get("bytes", 0) for e in entries)

    if not entries:
        print("\n  [DAGMA] No se obtuvieron datos de la API.")
        print("  Opciones:")
        print("    1. Revisa conectividad con datos.gov.co")
        print("    2. Descarga CSVs de datos.cali.gov.co (tag='calidad del aire')")
        print(f"       y colócalos en: {BASE_DIR / 'manuales/<ESTACION>/'}")
        print("    3. Para 2022-2024: exportar desde SISAIRE")
        json.dump({"fuente": f"Ground Truth ({', '.join(AUTORIDADES)})",
                   "dataset": DATASET_G4T8,
                   "autoridades": AUTORIDADES,
                   "estaciones": list(ESTACIONES.keys()),
                   "total_mb": 0, "archivos": [],
                   "advertencia": "Sin datos"},
                  open(MANIFEST_PATH, "w"), indent=2)
        guardar_geojson()
        return

    json.dump({
        "fuente": f"Ground Truth Cali-Yumbo ({', '.join(AUTORIDADES)})",
        "dataset": f"{DATASET_G4T8} (IDEAM)",
        "registros_totales": sum(e.get("registros",0) for e in entries if "registros" in e),
        "estaciones": {k: {"zona": v["zona"], "lat": v["lat"], "lon": v["lon"]}
                       for k, v in ESTACIONES.items()},
        "total_mb": round(total_bytes / 1e6, 2),
        "archivos": len(entries),
        "entries": entries,
        "nota": "Datos 2020-2024 via datos.gov.co. Años sin datos requieren descarga manual de SISAIRE.",
        "anos_con_datos": sorted(set(e.get("anio",0) for e in entries if "anio" in e)),
        "anos_faltantes": [a for a in range(START_YEAR, END_YEAR+1)
                           if a not in set(e.get("anio",0) for e in entries if "anio" in e)],
        "sisaire_url": "http://sisaire.ideam.gov.co/ideam-sisaire-web/",
    }, open(MANIFEST_PATH, "w"), indent=2)

    guardar_geojson()

    # Determinar qué años tienen datos de la API vs necesitan SISAIRE
    anos_api = sorted(set(e.get("anio", 0) for e in entries if "anio" in e))
    anos_faltantes = [a for a in range(START_YEAR, END_YEAR + 1) if a not in anos_api]

    print(f"\n  [DAGMA] Manifest: {MANIFEST_PATH}")
    print(f"  [DAGMA] Total: {total_bytes/1e6:.1f} MB en {len(entries)} archivos")

    if anos_faltantes:
        print(f"\n  Años SIN datos en datos.gov.co: {anos_faltantes}")
        print(f"  Descargar manualmente de SISAIRE web y colocar en:")
        print(f"  {BASE_DIR / 'manuales/<ESTACION>/<archivo>.csv'}")
        print(f"  URL: http://sisaire.ideam.gov.co/ideam-sisaire-web/")

    print("\n  [DAGMA] Listo.")


if __name__ == "__main__":
    main()
