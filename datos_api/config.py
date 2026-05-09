"""
=============================================================
GeoVision-CLIP Cali — Configuración del pipeline
=============================================================

USO:
    from config import DATA_DIR, MANIFESTS_DIR, BBOX_CALI

Todas las rutas son relativas al proyecto.
Para sobrescribir el directorio de datos:

    export GEOVISION_DATA_DIR=/ruta/a/datos
"""

import os
import shutil
import sys
import time
from pathlib import Path

# ── Detectar raíz del proyecto ────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Directorio de datos ───────────────────────────────────
_data_dir_env = os.environ.get("GEOVISION_DATA_DIR")
DATA_DIR = Path(_data_dir_env) if _data_dir_env else PROJECT_ROOT / "data"

# ── Subdirectorios ────────────────────────────────────────
DAGMA_DIR      = DATA_DIR / "dagma"
S5P_DIR        = DATA_DIR / "sentinel5p"
SENTINEL2_DIR  = DATA_DIR / "sentinel2"
ERA5_DIR       = DATA_DIR / "era5"
MODIS_DIR      = DATA_DIR / "modis"
ZARR_DIR       = DATA_DIR / "zarr"
MANIFESTS_DIR  = DATA_DIR / "manifests"

# ── Bounding Box Cali ─────────────────────────────────────
BBOX_CALI = {
    "lat_min": 3.30, "lat_max": 3.55,
    "lon_min": -76.60, "lon_max": -76.40,
}

# ── Periodo ───────────────────────────────────────────────
START_YEAR = 2020
END_YEAR   = 2026
START_DATE = "2020-01-01"
END_DATE   = "2026-12-31"

# ── Contaminantes ─────────────────────────────────────────
CONTAMINANTES = ["NO2", "SO2", "O3"]

# ── Guardia de espacio en disco ───────────────────────────
_DISK_WARN_ENV = os.environ.get("GEOVISION_DISK_WARN_GB")
DISK_WARN_GB = int(_DISK_WARN_ENV) if _DISK_WARN_ENV else 25

# ── Guardia de RAM ────────────────────────────────────────
_RAM_WARN_ENV = os.environ.get("GEOVISION_RAM_WARN_PCT")
RAM_WARN_PCT = int(_RAM_WARN_ENV) if _RAM_WARN_ENV else 80  # % de RAM usada


def check_ram(origen: str = "desconocido", fatal: bool = False) -> float:
    """
    Verifica que la RAM usada no supere RAM_WARN_PCT.
    Si se acerca al límite, espera 10s y reintenta hasta 3 veces.

    Returns:
        float: porcentaje de RAM usado
    """
    try:
        import psutil
        pct = psutil.virtual_memory().percent
    except ImportError:
        return 0.0

    if pct >= RAM_WARN_PCT:
        msg = (f"\n[RAM] {origen}: {pct:.0f}% usado >= {RAM_WARN_PCT}% limite\n"
               f"      Esperando 10s para liberar memoria...")
        print(msg)
        time.sleep(10)
        # Reintentar
        try:
            pct = psutil.virtual_memory().percent
        except ImportError:
            return 0.0
        if pct >= RAM_WARN_PCT:
            msg2 = f"[RAM] {origen}: aun en {pct:.0f}% despues de espera"
            if fatal:
                print(msg2 + ". ABORTANDO.")
                sys.exit(1)
            else:
                print(msg2 + ". Continuando con precaucion.")

    return pct


def check_disk_space(origen: str = "desconocido", fatal: bool = True) -> float:
    try:
        free_gb = shutil.disk_usage(DATA_DIR).free / (1024 ** 3)
    except Exception:
        return 0.0
    if free_gb < DISK_WARN_GB:
        msg = f"\n[GUARDIA] {origen}: {free_gb:.1f} GB libres < {DISK_WARN_GB} GB\n"
        if fatal:
            print(msg + "ABORTANDO. Libera espacio o cambia GEOVISION_DATA_DIR.")
            sys.exit(1)
        else:
            print(msg + "ADVERTENCIA: espacio bajo.")
    return free_gb


def crear_directorios():
    for d in [DATA_DIR, DAGMA_DIR, MANIFESTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
