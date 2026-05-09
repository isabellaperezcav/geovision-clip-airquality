"""
=====================================================================
GeoVision-CLIP Cali — Descarga Sentinel-2 L2A (AWS STAC) IDEMPOTENTE
=====================================================================
IDEMPOTENCIA:
  - Si un archivo .tif ya existe y pesa >= 2 MB, NO lo re-descarga
  - Si el manifest.json existe al arrancar, carga los archivos previos
  - Descarga atomica: escribe a .tmp, renombra solo si completo
  - Si se interrumpe, al re-ejecutar retoma donde quedó

USO:
    python descarga_sentinel2_aws.py              # descarga normal
    python descarga_sentinel2_aws.py --verify     # verifica integridad
    python descarga_sentinel2_aws.py --missing    # descarga solo faltantes

3 VARIABLES OBJETIVO (NO2, SO2, O3):
  Sentinel-2 provee COVARIABLES opticas (13 bandas), NO los contaminantes.
  Los contaminantes objetivo vienen de:
    - S5P L3 (ya descargado): NO2, SO2, O3 troposfericos diarios
    - DAGMA (ya descargado): NO2, SO2, O3 horarios (ground truth)
  S2 se usa para el CLIP multimodal (imagenes) y ConvLSTM (covariables).

REQUISITOS:
    pip install requests tqdm
"""

import hashlib
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

from config import SENTINEL2_DIR as BASE_DIR
from config import MANIFESTS_DIR, BBOX_CALI
from config import check_disk_space, check_ram, DISK_WARN_GB

MANIFEST_PATH = MANIFESTS_DIR / "manifest_sentinel2.json"
LOG_PATH      = BASE_DIR / "sentinel2_errores.log"

BBOX = [-76.65, 3.25, -76.35, 3.60]
PERIODO_INICIO = datetime(2020, 1, 1)
PERIODO_FIN    = datetime(2024, 12, 31)
MAX_NUBE_PCT   = 60
MIN_BANDA_BYTES = 2 * 1024 * 1024

STAC_URL = "https://earth-search.aws.element84.com/v1/search"

BANDAS_MAP = {
    "blue": "B02", "green": "B03", "red": "B04", "nir": "B08",
    "rededge1": "B05", "rededge2": "B06", "rededge3": "B07",
    "nir08": "B8A", "swir16": "B11", "swir22": "B12",
}

BASE_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()])
log = logging.getLogger("S2")


def md5_streaming(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def descargar_url(url: str, dest: Path, min_bytes: int = MIN_BANDA_BYTES,
                  max_reintentos: int = 5) -> bool:
    """IDEMPOTENTE: si dest existe y pesa >= min_bytes, NO descarga."""
    if dest.exists():
        if dest.stat().st_size >= min_bytes:
            log.info(f"    SKIP {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
            return True
        else:
            log.warning(f"    RE-DESCARGANDO {dest.name} (truncado: {dest.stat().st_size} bytes)")
            dest.unlink()

    tmp = dest.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()

    for intento in range(1, max_reintentos + 1):
        try:
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            bytes_ok = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*512):
                    if chunk:
                        f.write(chunk)
                        bytes_ok += len(chunk)
            if bytes_ok < min_bytes:
                tmp.unlink(missing_ok=True)
                raise ValueError(f"Truncado: {bytes_ok} < {min_bytes}")
            tmp.rename(dest)
            return True
        except Exception as e:
            tmp.unlink(missing_ok=True)
            espera = 2 ** intento
            log.warning(f"Intento {intento}/{max_reintentos} {dest.name}: {e} — esperando {espera}s")
            time.sleep(espera)
    log.error(f"FALLO DEFINITIVO: {url}")
    return False


def buscar_stac(year: int, month: int) -> list:
    t_ini = f"{year}-{month:02d}-01T00:00:00Z"
    t_end = f"{year}-{month+1:02d}-01T00:00:00Z" if month < 12 else f"{year+1}-01-01T00:00:00Z"
    query = {
        "collections": ["sentinel-2-l2a"],
        "bbox": BBOX,
        "datetime": f"{t_ini}/{t_end}",
        "query": {"eo:cloud_cover": {"lt": MAX_NUBE_PCT}},
        "limit": 100,
    }
    try:
        r = requests.post(STAC_URL, json=query, timeout=30)
        r.raise_for_status()
        items = r.json().get("features", [])
        log.info(f"  STAC {year}-{month:02d}: {len(items)} escenas")
        return items
    except Exception as e:
        log.error(f"STAC error {year}-{month:02d}: {e}")
        return []


def descargar_escena(item: dict, dest_dir: Path) -> list[dict]:
    assets = item.get("assets", {})
    scene_id = item.get("id", "unknown")
    dest_dir.mkdir(parents=True, exist_ok=True)
    resultados = []
    for asset_name, banda in BANDAS_MAP.items():
        if asset_name not in assets:
            continue
        url = assets[asset_name]["href"]
        dest = dest_dir / f"{banda}.tif"
        if descargar_url(url, dest):
            size = dest.stat().st_size
            md5 = md5_streaming(dest)
            resultados.append({
                "file": str(dest), "scene_id": scene_id,
                "banda": banda, "bytes": size, "md5": md5,
            })
        else:
            log.error(f"    FAIL {banda}")
    return resultados


def guardar_manifest(manifest: list, total_bytes: int):
    """Guarda manifest de forma atomica (.tmp -> replace)."""
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    data = {
        "fuente": "Sentinel-2 L2A AWS STAC",
        "bbox": BBOX,
        "periodo": f"{PERIODO_INICIO.date()} / {PERIODO_FIN.date()}",
        "total_gb": round(total_bytes / 1e9, 3),
        "total_archivos": len(manifest),
        "archivos": manifest,
    }
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(MANIFEST_PATH)


# ── Modo --verify: verificar que archivos en manifest existen y MD5 ──
def verify():
    """Verifica que todos los archivos del manifest existan y tengan MD5 correcto."""
    if not MANIFEST_PATH.exists():
        log.error("No hay manifest que verificar.")
        return
    data = json.loads(MANIFEST_PATH.read_text())
    archivos = data.get("archivos", [])
    log.info(f"Verificando {len(archivos)} archivos del manifest...")
    ok = fail = 0
    for e in archivos:
        path = Path(e["file"])
        if not path.exists():
            log.error(f"  FALTA: {e['file']}")
            fail += 1
        elif e.get("md5") and md5_streaming(path) != e["md5"]:
            log.error(f"  MD5 INCORRECTO: {e['file']}")
            fail += 1
        else:
            ok += 1
    log.info(f"Verificacion: {ok} OK, {fail} FALLOS")


def main():
    modo_verify = "--verify" in sys.argv
    modo_missing = "--missing" in sys.argv

    if modo_verify:
        verify()
        return

    check_disk_space("S2 AWS")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    log.info("="*60)
    log.info("GeoVision-CLIP Cali — Sentinel-2 L2A AWS (IDEMPOTENTE)")
    log.info(f"  Bbox: {BBOX}")
    log.info(f"  Periodo: {PERIODO_INICIO.date()} a {PERIODO_FIN.date()}")
    log.info(f"  Nubes max: {MAX_NUBE_PCT}%")
    log.info(f"  Bandas: {len(BANDAS_MAP)}")
    log.info(f"  IDEMPOTENTE: archivos existentes se saltan")
    log.info("="*60)

    # Cargar manifest existente (idempotencia)
    manifest = []
    total_bytes = 0
    if MANIFEST_PATH.exists():
        data = json.loads(MANIFEST_PATH.read_text())
        manifest = data.get("archivos", [])
        total_bytes = data.get("total_gb", 0) * 1e9
        log.info(f"Retomando: {len(manifest)} archivos ya registrados ({total_bytes/1e9:.2f} GB)")
    existentes = {e["file"] for e in manifest}

    if modo_missing:
        log.info("Modo --missing: descargando solo archivos faltantes...")

    for y in range(PERIODO_INICIO.year, PERIODO_FIN.year + 1):
        for m in range(1, 13):
            check_ram("S2 AWS")
            check_disk_space("S2 AWS", fatal=False)

            items = buscar_stac(y, m)
            for item in items:
                scene_id = item["id"]
                dest_dir = BASE_DIR / scene_id
                resultados = descargar_escena(item, dest_dir)
                for r in resultados:
                    if r["file"] not in existentes:
                        manifest.append(r)
                        total_bytes += r["bytes"]
                        existentes.add(r["file"])
                guardar_manifest(manifest, total_bytes)
                time.sleep(0.5)

    log.info("="*60)
    log.info(f"Completado: {len(manifest)} archivos | {total_bytes/1e9:.2f} GB")
    log.info(f"Manifest: {MANIFEST_PATH}")
    log.info("="*60)


if __name__ == "__main__":
    main()
