"""
=============================================================
GeoVision-CLIP Cali — Descarga Sentinel-2 L2A (AWS Open Data)
Fuente : s3://sentinel-cogs/sentinel-s2-l2a-cogs/
Ruta   : D:/analitica/sentinel2/
=============================================================
REQUISITOS
    pip install boto3 requests tqdm shapely

NOTAS
    - El bucket s3://sentinel-cogs es público, NO necesitas credenciales AWS.
    - Los tiles de Cali son: 18NVL  y  18NUL  (sistema UTM MGRS)
      (puedes verificar en https://mgrs-mapper.com apuntando a Cali)
    - Bandas descargadas: B02 B03 B04 B08 (10m) + B05 B06 B07 B8A B11 B12 (20m) + B01 B09 (60m)
    - Filtra escenas con nubosidad < 60%
"""

import boto3
import json
import hashlib
import os
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
from botocore import UNSIGNED
from botocore.config import Config

# ── Configuración ─────────────────────────────────────────
BASE_DIR      = Path("D:/analitica/sentinel2")
START_DATE    = datetime(2020, 1, 1)
END_DATE      = datetime(2024, 12, 31)
MAX_NUBE_PCT  = 60          # descartar escenas con más del 60% de nubes
TILES_CALI    = ["18NVL", "18NUL"]   # tiles MGRS que cubren Cali
BUCKET_NAME   = "sentinel-cogs"
BANDAS        = ["B02", "B03", "B04", "B05", "B06",
                 "B07", "B08", "B8A", "B09", "B11", "B12"]

MANIFEST_PATH = Path("D:/analitica/manifest_sentinel2.json")


# ── Cliente S3 anónimo (bucket público) ───────────────────
def get_s3_client():
    return boto3.client(
        "s3",
        region_name    = "us-west-2",
        config         = Config(signature_version=UNSIGNED),
    )


# ── Listar escenas disponibles ────────────────────────────
def listar_escenas(s3, tile: str, year: int, month: int) -> list:
    """
    Estructura del bucket:
    sentinel-s2-l2a-cogs/{utm_zone}/{lat_band}/{square}/{year}/{month}/{scene_id}/
    tile 18NVL → utm_zone=18, lat_band=N, square=VL
    """
    utm_zone = tile[:2]          # "18"
    lat_band = tile[2]           # "N"
    square   = tile[3:]          # "VL"

    prefix = f"sentinel-s2-l2a-cogs/{utm_zone}/{lat_band}/{square}/{year}/{month}/"
    paginator = s3.get_paginator("list_objects_v2")
    escenas = []

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            escenas.append(cp["Prefix"])

    return escenas


# ── Leer metadatos JSON de la escena (nubosidad) ──────────
def obtener_metadatos(s3, escena_prefix: str) -> dict | None:
    json_key = escena_prefix + "tileInfo.json"
    try:
        obj  = s3.get_object(Bucket=BUCKET_NAME, Key=json_key)
        meta = json.loads(obj["Body"].read())
        return meta
    except Exception:
        return None


# ── Descargar una banda ───────────────────────────────────
def descargar_banda(s3, escena_prefix: str, banda: str, dest_dir: Path) -> dict | None:
    """
    Descarga un GeoTIFF de una banda. Devuelve entrada de manifest o None.
    """
    key  = f"{escena_prefix}{banda}.tif"
    dest = dest_dir / f"{banda}.tif"

    if dest.exists():
        return None  # ya descargado

    try:
        obj      = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        data     = obj["Body"].read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

        md5 = hashlib.md5(data).hexdigest()
        return {
            "file":   str(dest),
            "source": f"s3://{BUCKET_NAME}/{key}",
            "banda":  banda,
            "md5":    md5,
            "bytes":  len(data),
        }
    except Exception as e:
        print(f"  [!] Error descargando {key}: {e}")
        return None


# ── Calcular meses a iterar ───────────────────────────────
def meses_entre(start: datetime, end: datetime):
    cur = start.replace(day=1)
    while cur <= end:
        yield cur.year, cur.month
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)


# ── Main ──────────────────────────────────────────────────
def main():
    s3 = get_s3_client()
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    manifest   = []
    total_bytes = 0
    escenas_ok  = 0
    escenas_nube = 0

    for tile in TILES_CALI:
        print(f"\n[S2] Tile: {tile}")

        for year, month in tqdm(list(meses_entre(START_DATE, END_DATE)),
                                 desc=f"  meses {tile}"):
            escenas = listar_escenas(s3, tile, year, month)

            for esc_prefix in escenas:
                meta = obtener_metadatos(s3, esc_prefix)
                if meta is None:
                    continue

                nube_pct = meta.get("cloudyPixelPercentage", 100)
                fecha    = meta.get("timestamp", "")[:10]

                if nube_pct > MAX_NUBE_PCT:
                    escenas_nube += 1
                    continue

                # Carpeta local: sentinel2/tile/fecha/
                scene_id  = esc_prefix.rstrip("/").split("/")[-1]
                dest_dir  = BASE_DIR / tile / fecha / scene_id
                dest_dir.mkdir(parents=True, exist_ok=True)

                print(f"\n  Escena {scene_id}  nubosidad={nube_pct:.1f}%  fecha={fecha}")
                escenas_ok += 1

                for banda in tqdm(BANDAS, desc="    bandas", leave=False):
                    entrada = descargar_banda(s3, esc_prefix, banda, dest_dir)
                    if entrada:
                        entrada.update({
                            "tile":       tile,
                            "scene_id":   scene_id,
                            "fecha":      fecha,
                            "nube_pct":   nube_pct,
                        })
                        manifest.append(entrada)
                        total_bytes += entrada["bytes"]

                time.sleep(0.1)  # pausa cortés

    # ── Guardar manifest ──────────────────────────────────
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump({
            "fuente":        "Sentinel-2 L2A AWS Open Data",
            "tiles":         TILES_CALI,
            "periodo":       f"{START_DATE.date()} / {END_DATE.date()}",
            "max_nube_pct":  MAX_NUBE_PCT,
            "escenas_ok":    escenas_ok,
            "escenas_filtradas_nube": escenas_nube,
            "total_gb":      round(total_bytes / 1e9, 3),
            "archivos":      manifest,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n[S2] ✓ Descarga finalizada")
    print(f"     Escenas válidas : {escenas_ok}")
    print(f"     Escenas filtradas (nube): {escenas_nube}")
    print(f"     Total descargado: {total_bytes/1e9:.2f} GB")
    print(f"     Manifest guardado: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
