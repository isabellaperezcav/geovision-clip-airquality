"""
=============================================================
GeoVision-CLIP Cali — Descarga Sentinel-2 L2A (AWS STAC)
VERSIÓN CORREGIDA
Correcciones aplicadas:
  1. MD5 calculado en streaming (no carga todo en RAM)
  2. Verificación de tamaño mínimo y truncamiento
  3. Descarga atómica: escribe a .tmp, renombra solo si completa
  4. Retry con backoff exponencial
  5. Logging de errores a archivo para no perder el progreso
=============================================================
REQUISITOS
    pip install requests tqdm
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────
BASE_DIR      = Path("D:/analitica/sentinel2")
START_DATE    = datetime(2020, 1, 1)
END_DATE      = datetime(2026, 12, 31)
MAX_NUBE_PCT  = 60
MANIFEST_PATH = Path("D:/analitica/manifest_sentinel2.json")
LOG_PATH      = Path("D:/analitica/sentinel2_errores.log")

BBOX = [-76.60, 3.30, -76.40, 3.55]

STAC_URL = "https://earth-search.aws.element84.com/v1/search"

# Tamaño mínimo esperado por banda (bytes).
# Una banda S2 COG completa pesa al menos 3 MB.
# Si el archivo es más pequeño, está truncado.
MIN_BANDA_BYTES = 2  * 1024 * 1024   # 3 MB

BANDAS_MAP = {
    "blue":      "B02",
    "green":     "B03",
    "red":       "B04",
    "nir":       "B08",
    "rededge1":  "B05",
    "rededge2":  "B06",
    "rededge3":  "B07",
    "nir08":     "B8A",
    "swir16":    "B11",
    "swir22":    "B12",
}

# ── Logging ───────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s %(levelname)s %(message)s",
    handlers = [
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger("S2")


# ── MD5 en streaming (no carga el archivo en RAM) ─────────
def md5_streaming(path: Path) -> str:
    """Calcula MD5 leyendo el archivo en chunks de 1 MB."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Descarga atómica con retry ────────────────────────────
def descargar_url(url: str, dest: Path,
                  min_bytes: int = MIN_BANDA_BYTES,
                  max_reintentos: int = 5) -> bool:
    """
    Descarga url → dest de forma atómica:
      - Escribe a dest.tmp
      - Solo renombra a dest si el archivo está completo
      - Borra .tmp si falla
      - Verifica que el tamaño sea >= min_bytes
    Devuelve True si la descarga fue exitosa.
    """
    tmp = dest.with_suffix(".tmp")

    # Ya descargado y válido
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return True

    # Limpiar tmp anterior si quedó de un intento previo
    if tmp.exists():
        tmp.unlink()

    session = requests.Session()

    for intento in range(1, max_reintentos + 1):
        try:
            resp = session.get(url, stream=True, timeout=120)
            resp.raise_for_status()

            bytes_escritos = 0
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 512):  # 512 KB
                    if chunk:
                        f.write(chunk)
                        bytes_escritos += len(chunk)

            # Verificar que no esté truncado
            if bytes_escritos < min_bytes:
                log.warning(
                    f"Archivo truncado ({bytes_escritos/1e6:.1f} MB < "
                    f"{min_bytes/1e6:.1f} MB mínimo): {dest.name}"
                )
                tmp.unlink(missing_ok=True)
                raise ValueError("Archivo truncado")

            # Renombrar solo si está completo ← esto es lo clave
            tmp.rename(dest)
            return True

        except Exception as e:
            tmp.unlink(missing_ok=True)
            espera = 2 ** intento   # backoff: 2, 4, 8, 16, 32 segundos
            log.warning(f"Intento {intento}/{max_reintentos} fallido para {dest.name}: {e} "
                        f"— esperando {espera}s")
            time.sleep(espera)

    log.error(f"FALLO DEFINITIVO: {url}")
    return False


# ── Buscar escenas en STAC ────────────────────────────────
def buscar_stac(year: int, month: int) -> list:
    t_ini = f"{year}-{month:02d}-01T00:00:00Z"
    if month < 12:
        t_end = f"{year}-{month+1:02d}-01T00:00:00Z"
    else:
        t_end = f"{year+1}-01-01T00:00:00Z"

    query = {
        "collections": ["sentinel-2-l2a"],
        "bbox":        BBOX,
        "datetime":    f"{t_ini}/{t_end}",
        "query":       {"eo:cloud_cover": {"lt": MAX_NUBE_PCT}},
        "limit":       100,
    }

    try:
        r = requests.post(STAC_URL, json=query, timeout=30)
        r.raise_for_status()
        items = r.json().get("features", [])
        log.info(f"  STAC {year}-{month:02d}: {len(items)} escenas")
        return items
    except Exception as e:
        log.error(f"Error STAC {year}-{month:02d}: {e}")
        return []


# ── Descargar todas las bandas de una escena ──────────────
def descargar_escena(item: dict, dest_dir: Path) -> list[dict]:
    """
    Descarga las bandas definidas en BANDAS_MAP para una escena.
    Devuelve lista de entradas para el manifest.
    """
    assets   = item.get("assets", {})
    scene_id = item.get("id", "unknown")

    dest_dir.mkdir(parents=True, exist_ok=True)
    resultados = []

    for asset_name, banda in BANDAS_MAP.items():
        if asset_name not in assets:
            log.warning(f"    [{scene_id}] Asset '{asset_name}' no disponible — saltando")
            continue

        url  = assets[asset_name]["href"]
        dest = dest_dir / f"{banda}.tif"

        ok = descargar_url(url, dest)

        if ok:
            size = dest.stat().st_size
            md5  = md5_streaming(dest)   # ← streaming, no carga en RAM
            resultados.append({
                "file":     str(dest),
                "scene_id": scene_id,
                "banda":    banda,
                "bytes":    size,
                "md5":      md5,
            })
            log.info(f"    ✓ {banda}  ({size/1e6:.1f} MB)")
        else:
            log.error(f"    ✗ {banda} FALLÓ definitivamente")

    return resultados


# ── Guardar manifest incremental ──────────────────────────
def guardar_manifest(manifest: list, total_bytes: int):
    """
    Escribe el manifest atómicamente (escribe a .tmp, renombra).
    Así nunca queda corrupto aunque el proceso se interrumpa.
    """
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    data = {
        "fuente":    "Sentinel-2 L2A — AWS STAC (earth-search.aws.element84.com)",
        "bbox":      BBOX,
        "periodo":   f"{START_DATE.date()} / {END_DATE.date()}",
        "total_gb":  round(total_bytes / 1e9, 3),
        "archivos":  manifest,
    }
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    # En Windows, rename() falla si el destino ya existe → usar replace()
    tmp.replace(MANIFEST_PATH)


# ── Main ──────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("GeoVision-CLIP Cali — Descarga Sentinel-2 L2A")
    log.info("=" * 60)

    BASE_DIR.mkdir(parents=True, exist_ok=True)

    manifest    = []
    total_bytes = 0

    # Cargar manifest existente (si se interrumpió y se retoma)
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            data = json.load(f)
        manifest    = data.get("archivos", [])
        total_bytes = data.get("total_gb", 0) * 1e9
        log.info(f"Retomando: {len(manifest)} archivos ya registrados "
                 f"({total_bytes/1e9:.2f} GB)")

    archivos_ya_registrados = {e["file"] for e in manifest}

    for y in range(START_DATE.year, END_DATE.year + 1):
        for m in range(1, 13):
            log.info(f"\nMes {y}-{m:02d}")
            items = buscar_stac(y, m)

            for item in items:
                scene_id = item["id"]
                dest_dir = BASE_DIR / scene_id

                log.info(f"  Escena: {scene_id}")

                resultados = descargar_escena(item, dest_dir)

                for r in resultados:
                    if r["file"] not in archivos_ya_registrados:
                        manifest.append(r)
                        total_bytes += r["bytes"]
                        archivos_ya_registrados.add(r["file"])

                # Guardar manifest después de cada escena
                guardar_manifest(manifest, total_bytes)

                time.sleep(0.5)  # pausa entre escenas

    log.info("\n" + "=" * 60)
    log.info(f"Descarga finalizada")
    log.info(f"Total: {len(manifest)} archivos | {total_bytes/1e9:.2f} GB")
    log.info(f"Manifest: {MANIFEST_PATH}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()