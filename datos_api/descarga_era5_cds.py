"""
=============================================================
GeoVision-CLIP Cali — Descarga ERA5-Land (ERA5-Land hourly)
Fuente : Copernicus Climate Data Store (CDS API)
Ruta   : D:/analitica/era5/
=============================================================
REQUISITOS
    pip install cdsapi tqdm

CONFIGURACIÓN (una sola vez)
    1. Regístrate en https://cds.climate.copernicus.eu
    2. En "My Account" → "API key" copia tu UID y key
    3. Crea el archivo  C:/Users/<tu_usuario>/.cdsapirc  con:

        url: https://cds.climate.copernicus.eu/api/v2
        key: <UID>:<API_KEY>

    (en Linux/Mac va en ~/.cdsapirc)

VARIABLES descargadas
    - 2m_temperature          (T2m)
    - 10m_u_component_of_wind (U10)
    - 10m_v_component_of_wind (V10)
    - surface_pressure        (SP)
    - total_precipitation     (TP)
    - boundary_layer_height   (BLH)
    - 2m_dewpoint_temperature (D2m → para calcular HR)
"""

import cdsapi
import hashlib
import json
import os
import time
from pathlib import Path
from tqdm import tqdm

# ── Configuración ─────────────────────────────────────────
BASE_DIR   = Path("D:/analitica/era5")
START_YEAR = 2020
END_YEAR   = 2024

# Bounding box Cali:  Norte, Oeste, Sur, Este
AREA_CALI  = [3.55, -76.60, 3.30, -76.40]

VARIABLES  = [
    "2m_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "surface_pressure",
    "total_precipitation",
    "boundary_layer_height",
    "2m_dewpoint_temperature",
]

HORAS      = [f"{h:02d}:00" for h in range(24)]   # todas las horas
MANIFEST_PATH = Path("D:/analitica/manifest_era5.json")


# ── md5 ───────────────────────────────────────────────────
def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Descargar un mes ──────────────────────────────────────
def descargar_mes(client: cdsapi.Client, year: int, month: int) -> dict | None:
    """
    Descarga ERA5-Land horario para un mes completo sobre Cali.
    Formato NetCDF (.nc). Devuelve entrada de manifest.
    """
    dest_dir = BASE_DIR / str(year)
    dest_dir.mkdir(parents=True, exist_ok=True)

    fname  = f"era5_cali_{year}_{month:02d}.nc"
    dest   = dest_dir / fname

    if dest.exists():
        print(f"  [ERA5] Ya existe: {fname}")
        return {
            "file":   str(dest),
            "year":   year,
            "month":  month,
            "md5":    md5_file(dest),
            "bytes":  dest.stat().st_size,
        }

    dias_del_mes = [str(d) for d in range(1, 32)]   # CDS ignora días inexistentes

    request = {
        "product_type": "reanalysis",
        "variable":     VARIABLES,
        "year":         str(year),
        "month":        f"{month:02d}",
        "day":          dias_del_mes,
        "time":         HORAS,
        "area":         AREA_CALI,
        "format":       "netcdf",
    }

    try:
        client.retrieve(
            "reanalysis-era5-land",
            request,
            str(dest),
        )
        entrada = {
            "file":   str(dest),
            "year":   year,
            "month":  month,
            "md5":    md5_file(dest),
            "bytes":  dest.stat().st_size,
        }
        print(f"  [ERA5] ✓ {fname}  ({entrada['bytes']/1e6:.1f} MB)")
        return entrada

    except Exception as e:
        print(f"  [ERA5] ✗ Error {year}-{month:02d}: {e}")
        return None


# ── Main ──────────────────────────────────────────────────
def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # cdsapi lee automáticamente ~/.cdsapirc
    client   = cdsapi.Client()
    manifest = []
    total_bytes = 0

    meses = [
        (y, m)
        for y in range(START_YEAR, END_YEAR + 1)
        for m in range(1, 13)
    ]

    print(f"[ERA5] Descargando {len(meses)} meses ({START_YEAR}–{END_YEAR})")
    print(f"       Variables: {', '.join(VARIABLES)}\n")

    for year, month in tqdm(meses, desc="ERA5-Land"):
        entrada = descargar_mes(client, year, month)
        if entrada:
            manifest.append(entrada)
            total_bytes += entrada["bytes"]
        # CDS pone cola: espera un poco entre solicitudes
        time.sleep(2)

    # ── Guardar manifest ──────────────────────────────────
    with open(MANIFEST_PATH, "w") as f:
        json.dump({
            "fuente":    "ERA5-Land Hourly (Copernicus CDS)",
            "variables": VARIABLES,
            "periodo":   f"{START_YEAR}-01 / {END_YEAR}-12",
            "area_cali": AREA_CALI,
            "total_gb":  round(total_bytes / 1e9, 3),
            "archivos":  manifest,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n[ERA5] ✓ Descarga finalizada")
    print(f"       Total descargado: {total_bytes/1e9:.2f} GB")
    print(f"       Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
