"""
=============================================================
GeoVision-CLIP Cali — Descarga Sentinel-5P (NO2, SO2, O3)
Fuente : Google Earth Engine (COPERNICUS/S5P/OFFL/L3_*)
Ruta   : D:/analitica/sentinel5p/
=============================================================
REQUISITOS
    pip install earthengine-api geemap tqdm
    Autenticarse una sola vez con: earthengine authenticate
"""

import ee
import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm

# ── Configuración ─────────────────────────────────────────
BASE_DIR   = Path("D:/analitica/sentinel5p")
START_DATE = "2020-01-01"
END_DATE   = "2026-12-31"
BBOX_CALI  = [-76.60, 3.30, -76.40, 3.55]   # xmin, ymin, xmax, ymax
GCS_BUCKET = "geovision-cali-bucket"         # cambia por tu bucket real
SCALE_M    = 5000                            # resolución export (5 km)

CONTAMINANTES = {
    "NO2": {
        "collection": "COPERNICUS/S5P/OFFL/L3_NO2",
        "band":       "tropospheric_NO2_column_number_density",
    },
    "SO2": {
        "collection": "COPERNICUS/S5P/OFFL/L3_SO2",
        "band":       "SO2_column_number_density",
    },
    "O3": {
        "collection": "COPERNICUS/S5P/OFFL/L3_O3",
        "band":       "O3_column_number_density",
    },
}

# ── Inicializar GEE ───────────────────────────────────────
def init_gee(project: str = "geovision-cali"):
    """
    Autentica GEE. La primera vez ejecuta 'earthengine authenticate'
    en la terminal y pega el token que entrega Google.
    """
    try:
        ee.Initialize(project=project)
        print(f"[GEE] Inicializado con proyecto: {project}")
    except Exception:
        print("[GEE] Lanzando flujo de autenticación...")
        ee.Authenticate()
        ee.Initialize(project=project)


# ── Generar lista de meses ────────────────────────────────
def meses_entre(start: str, end: str):
    """Genera tuplas (año, mes) entre dos fechas YYYY-MM-DD."""
    cur = datetime.strptime(start, "%Y-%m-%d").replace(day=1)
    fin = datetime.strptime(end,   "%Y-%m-%d")
    while cur <= fin:
        yield cur.year, cur.month
        # avanzar al primer día del mes siguiente
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)


# ── Exportar un mes a GCS ─────────────────────────────────
def exportar_mes_gee(poll_name: str, meta: dict, year: int, month: int,
                     region: ee.Geometry, bucket: str):
    """
    Exporta la imagen media mensual de un contaminante a Google Cloud Storage
    en formato GeoTIFF. Devuelve el objeto Task para monitoreo.
    """
    t0  = f"{year}-{month:02d}-01"
    dt  = datetime(year, month, 1)
    t1_dt = (dt + timedelta(days=32)).replace(day=1)
    t1  = t1_dt.strftime("%Y-%m-%d")

    ic  = (ee.ImageCollection(meta["collection"])
           .filterBounds(region)
           .filterDate(t0, t1)
           .select(meta["band"]))

    img = ic.mean().toFloat()

    desc     = f"{poll_name}_{year}_{month:02d}"
    gcs_path = f"sentinel5p/{poll_name}/{year}"

    task = ee.batch.Export.image.toCloudStorage(
        image          = img,
        description    = desc,
        bucket         = bucket,
        fileNamePrefix = f"{gcs_path}/{desc}",
        region         = region,
        scale          = SCALE_M,
        crs            = "EPSG:4326",
        fileFormat     = "GeoTIFF",
        maxPixels      = 1e10,
    )
    task.start()
    return task, desc


# ── Verificar estado de tareas ────────────────────────────
def esperar_tareas(tareas: list, intervalo: int = 30):
    """
    Espera que todas las tareas GEE terminen.
    tareas: lista de (task, nombre_descriptivo)
    """
    pendientes = list(tareas)
    print(f"\n[GEE] Monitoreando {len(pendientes)} tareas de exportación...")
    while pendientes:
        tiempo.sleep(intervalo)
        nuevas = []
        for task, nombre in pendientes:
            estado = task.status()["state"]
            if estado in ("COMPLETED",):
                print(f"  ✓ {nombre}")
            elif estado in ("FAILED", "CANCELLED"):
                print(f"  ✗ {nombre} → {task.status().get('error_message','')}")
            else:
                nuevas.append((task, nombre))
        pendientes = nuevas
    print("[GEE] Todas las tareas completadas.\n")


# ── md5 de un archivo local ───────────────────────────────
def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Main ──────────────────────────────────────────────────
def main():
    init_gee()

    region = ee.Geometry.Rectangle(BBOX_CALI)
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    todas_las_tareas = []

    for poll, meta in CONTAMINANTES.items():
        print(f"\n[{poll}] Enviando tareas de exportación a GCS...")
        for year, month in tqdm(list(meses_entre(START_DATE, END_DATE)),
                                desc=poll):
            task, desc = exportar_mes_gee(
                poll, meta, year, month, region, GCS_BUCKET
            )
            todas_las_tareas.append((task, desc))
            # breve pausa para no saturar la API
            time.sleep(0.5)

    # Esperar que GEE procese todo
    esperar_tareas(todas_las_tareas)

    # ── NOTA: tras la exportación a GCS debes descargar los GeoTIFFs
    # con gsutil o la librería google-cloud-storage. Ejemplo rápido:
    #
    #   from google.cloud import storage
    #   client  = storage.Client()
    #   bucket  = client.bucket(GCS_BUCKET)
    #   blobs   = bucket.list_blobs(prefix="sentinel5p/")
    #   for blob in blobs:
    #       dest = BASE_DIR / blob.name
    #       dest.parent.mkdir(parents=True, exist_ok=True)
    #       blob.download_to_filename(str(dest))
    #       print(f"Descargado: {dest}")

    print("\n[GEE] Pipeline Sentinel-5P completado.")
    print(f"      Archivos en GCS bucket: gs://{GCS_BUCKET}/sentinel5p/")


if __name__ == "__main__":
    import time as tiempo   # alias para evitar conflicto con el módulo time
    time  = tiempo
    main()
