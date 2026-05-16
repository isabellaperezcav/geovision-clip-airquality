"""
GeoVision-CLIP Cali — ERA5 + ERA5-Land ROBUSTA
"""

import os, sys, cdsapi, hashlib, json, time, psutil, zipfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import check_disk_space, check_ram, DISK_WARN_GB, RAM_WARN_PCT

# =============================================================
# CONFIG — rutas locales GeoVision-CLIP
# =============================================================
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = ROOT / "data" / "era5"
MANIFESTS_DIR = ROOT / "data" / "manifests"
MANIFEST_PATH = MANIFESTS_DIR / "manifest_era5.json"
LOG_PATH = BASE_DIR / "era5_descarga.log"

START_YEAR = 2020
END_YEAR   = 2025

AREA_CALI = [3.60, -76.65, 3.25, -76.35]

# =============================================================
# VARIABLES
# =============================================================

VARIABLES = {

    # 🌡️ Temperatura
    "t2m":  "2m_temperature",
    "d2m":  "2m_dewpoint_temperature",

    # 🌬️ Viento
    "u10":  "10m_u_component_of_wind",
    "v10":  "10m_v_component_of_wind",

    # 🌧️ Hidrología
    "tp":   "total_precipitation",

    # 🌍 Presión
    "sp":   "surface_pressure",

    # 🌫️ Boundary Layer Height (SOLO ERA5)
    "blh":  "boundary_layer_height",

    # 🌱 Suelo
    "stl1": "soil_temperature_level_1",

    # ☀️ Radiación
    "ssr":  "surface_solar_radiation_downwards",
}

HORAS = [f"{h:02d}:00" for h in range(24)]

WAIT_OK = 3
WAIT_ERROR = 30
MAX_REINTENTOS = 3

MIN_BYTES_VALIDO = 20_000

# =============================================================
# LOGGING
# =============================================================

def log(msg):

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    txt = f"[{ts}] {msg}"

    print(txt)

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(txt + "\n")

# =============================================================
# HASH MD5
# =============================================================

def md5_archivo(ruta):

    h = hashlib.md5()

    with open(ruta, "rb") as f:

        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()

# =============================================================
# DETECCIÓN ROBUSTA
# =============================================================

def detectar_formato(ruta):

    with open(ruta, "rb") as f:

        magic = f.read(16)

    if magic.startswith(b"GRIB"):
        return "GRIB"

    if magic.startswith(b"CDF"):
        return "NetCDF3"

    if b"HDF" in magic or magic.startswith(b"\x89HDF"):
        return "NetCDF4"

    if magic.startswith(b"<"):
        return "HTML"

    return "DESCONOCIDO"

# =============================================================
# VALIDACIÓN
# =============================================================

def validar_archivo(ruta):

    formato = detectar_formato(ruta)

    size_kb = ruta.stat().st_size / 1e3

    if formato == "HTML":
        return False, "Respuesta HTML (error CDS)"

    if formato in ["GRIB", "NetCDF3", "NetCDF4"]:
        return True, formato

    if size_kb > 50:
        return True, "DESCONOCIDO_PERO_OK"

    return False, "Archivo inválido"

# =============================================================
# DESCARGA
# =============================================================

def descargar_variable_mes(client, year, month, var_corto, var_cds):

    dest_dir = BASE_DIR / str(year)

    dest_dir.mkdir(parents=True, exist_ok=True)

    fname = f"era5_cali_{year}_{month:02d}_{var_corto}.nc"

    dest = dest_dir / fname

    # =========================================================
    # YA EXISTE
    # =========================================================

    if dest.exists() and dest.stat().st_size > MIN_BYTES_VALIDO:

        log(
            f"[{var_corto}] ⏭ Ya existe "
            f"({dest.stat().st_size/1e3:.0f} KB)"
        )

        return None

    # =========================================================
    # SOLICITUD
    # =========================================================

    solicitud = {

        "variable": var_cds,

        "year": str(year),

        "month": f"{month:02d}",

        "day": [f"{d:02d}" for d in range(1, 32)],

        "time": HORAS,

        "area": AREA_CALI,

        "format": "netcdf",
    }

    # =========================================================
    # DATASET SEGÚN VARIABLE
    # =========================================================

    # 🌫️ BLH -> ERA5 NORMAL
    if var_corto == "blh":

        dataset = "reanalysis-era5-single-levels"

        solicitud["product_type"] = "reanalysis"

    # 🌍 RESTO -> ERA5-Land
    else:

        dataset = "reanalysis-era5-land"

    # =========================================================
    # DESCARGA
    # =========================================================

    for intento in range(1, MAX_REINTENTOS + 1):

        log(f"[{var_corto}] ⬇ Intento {intento} {fname}")

        try:

            client.retrieve(
                dataset,
                solicitud,
                str(dest)
            )

            if not dest.exists():
                raise Exception("No se creó archivo")

            size = dest.stat().st_size

            if size < MIN_BYTES_VALIDO:

                raise Exception(
                    f"Archivo demasiado pequeño ({size/1e3:.1f} KB)"
                )

            valido, info = validar_archivo(dest)

            if not valido:
                raise Exception(info)

            log(
                f"[{var_corto}] ✅ OK "
                f"{size/1e3:.0f} KB ({info})"
            )

            return {

                "archivo": str(dest),

                "anio": year,

                "mes": month,

                "variable": var_corto,

                "dataset": dataset,

                "bytes": size,

                "md5": md5_archivo(dest)
            }

        except Exception as e:

            log(f"[{var_corto}] ❌ Error: {e}")

            if dest.exists():
                dest.unlink()

            if intento < MAX_REINTENTOS:

                time.sleep(WAIT_ERROR)

            else:

                return None

# =============================================================
# MAIN
# =============================================================

def main():

    check_disk_space("ERA5")
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    client = cdsapi.Client()

    # =========================================================
    # MANIFEST
    # =========================================================

    if MANIFEST_PATH.exists():

        with open(MANIFEST_PATH) as f:

            manifest = json.load(f)

    else:

        manifest = []

    ya_descargados = {

        (e["anio"], e["mes"], e["variable"])

        for e in manifest
    }

    # =========================================================
    # LOOP PRINCIPAL
    # =========================================================

    for y in range(START_YEAR, END_YEAR + 1):

        check_ram("ERA5")

        for m in range(1, 13):

            check_disk_space("ERA5", fatal=False)

            for vc, vd in VARIABLES.items():

                if (y, m, vc) in ya_descargados:
                    continue

                res = descargar_variable_mes(
                    client,
                    y,
                    m,
                    vc,
                    vd
                )

                if res:

                    manifest.append(res)

                    with open(MANIFEST_PATH, "w") as f:

                        json.dump(
                            manifest,
                            f,
                            indent=2
                        )

                time.sleep(WAIT_OK)

    print("✅ DESCARGA COMPLETA")

# =============================================================

if __name__ == "__main__":

    main()