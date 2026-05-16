#!/usr/bin/env python3
"""
=====================================================================
GeoVision-CLIP Cali — Descarga MODIS MCD19A2 (MAIAC AOD) LOCAL
=====================================================================
Adaptado de: datos_api/01-extract-maiac.ipynb (Azure ADLS → local)

Producto: MCD19A2 v061 — Aerosol Optical Depth (MAIAC)
Tile MODIS: h10v08 (único tile que cubre Cali)
Volumen estimado: ~12 GB (1822 granules × ~6.7 MB)
API: NASA Earthdata via earthaccess

ESTRUCTURA DE SALIDA:
    data/modis/raw/{year}/{month}/{granule}.hdf

USO:
    export EARTHDATA_USERNAME=tu_usuario
    export EARTHDATA_PASSWORD=tu_password
    python datos_api/descarga_modis_maiac.py

REQUISITOS: pip install earthaccess tqdm
=====================================================================
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import earthaccess
from tqdm import tqdm

# ── Rutas locales ──────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = ROOT / "data" / "modis" / "raw"
MANIFESTS_DIR = ROOT / "data" / "manifests"
MANIFEST_PATH = MANIFESTS_DIR / "manifest_modis_maiac.json"
LOG_PATH = BASE_DIR / "descarga_maiac.log"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import check_disk_space, check_ram

# ── Config ─────────────────────────────────────────────
BBOX_CALI = (-76.60, 3.30, -76.40, 3.55)
PERIODO = ("2020-01-01", "2024-12-31")
TILE_MODIS = "h10v08"
PRODUCTO = "MCD19A2"
VERSION = "061"
MAX_REINTENTOS = 3

# ── Colors para log ───────────────────────────────────
def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def md5_archivo(ruta: Path) -> str:
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_yyyy_mm(granule_name: str) -> tuple[str, str]:
    """MCD19A2.A2024001.h10v08.061.PID.hdf → ('2024', '01')."""
    julian = granule_name.split(".")[1]  # 'A2024001'
    year, doy = julian[1:5], int(julian[5:8])
    dt = datetime(int(year), 1, 1) + timedelta(days=doy - 1)
    return year, f"{dt.month:02d}"


def main():
    # ── Cargar .env si existe ──
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v

    # Mapear EARTHDATA_USER/PASS → USERNAME/PASSWORD (convención earthaccess)
    if not os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_USER"):
        os.environ["EARTHDATA_USERNAME"] = os.environ["EARTHDATA_USER"]
    if not os.environ.get("EARTHDATA_PASSWORD") and os.environ.get("EARTHDATA_PASS"):
        os.environ["EARTHDATA_PASSWORD"] = os.environ["EARTHDATA_PASS"]

    check_disk_space("MODIS MAIAC")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Auth NASA Earthdata ──
    log("Autenticando NASA Earthdata via earthaccess...")
    try:
        auth = earthaccess.login(strategy="environment", persist=False)
        if not auth.authenticated:
            log("ERROR: No se pudo autenticar. Verificar EARTHDATA_USERNAME/PASSWORD", "ERROR")
            sys.exit(1)
        log("Autenticado ✓")
    except Exception as e:
        log(f"ERROR: {e}", "ERROR")
        sys.exit(1)

    # ── Buscar granules ──
    log("Buscando granules CMR...")
    results = earthaccess.search_data(
        short_name=PRODUCTO, version=VERSION,
        bounding_box=BBOX_CALI, temporal=PERIODO,
    )
    log(f"  → {len(results)} granules encontrados")
    if len(results) == 0:
        log("ERROR: 0 granules. Verificar bbox y periodo.", "ERROR")
        sys.exit(1)

    # ── Verificar tile ──
    first_url = results[0].data_links()[0]
    first_name = first_url.split("/")[-1]
    if TILE_MODIS not in first_name:
        log(f"ERROR: Primer granule no es {TILE_MODIS}: {first_name}", "ERROR")
        sys.exit(1)
    log(f"Sanity OK. Primer granule: {first_name}")

    # ── Cargar manifest existente ──
    manifest = []
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f).get("granules", [])
    existentes = {e["name"] for e in manifest}
    log(f"Retomando: {len(manifest)} granules ya registrados")

    # ── Descarga ──
    log(f"Iniciando descarga de {len(results)} granules...")
    failed = []
    t0 = time.time()

    for i, granule in enumerate(tqdm(results, desc="Descargando MODIS"), 1):
        check_ram("MODIS")
        check_disk_space("MODIS", fatal=False)

        try:
            urls = granule.data_links()
            if not urls:
                failed.append({"reason": "sin data_links"})
                continue
            url = urls[0]
            name = url.split("/")[-1]

            # Idempotencia
            if name in existentes:
                continue

            year, month = parse_yyyy_mm(name)
            dest_dir = BASE_DIR / year / month
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / name

            # Verificar existencia en disco
            if dest.exists() and dest.stat().st_size >= 1024:
                entry = {"name": str(name), "year": year, "month": month,
                         "file": str(dest), "bytes": dest.stat().st_size,
                         "md5": md5_archivo(dest)}
                manifest.append(entry)
                existentes.add(name)
                continue

            # Descargar con reintentos
            for intento in range(1, MAX_REINTENTOS + 1):
                try:
                    downloaded = earthaccess.download(
                        [granule], local_path=str(TMP_DIR), threads=1
                    )
                    if not downloaded:
                        raise Exception("earthaccess.download retornó vacío")

                    local = Path(downloaded[0])
                    if not local.exists() or local.stat().st_size < 1024:
                        raise Exception("archivo vacío o ausente")

                    # Verificar header HDF-EOS2
                    with local.open("rb") as fh:
                        header = fh.read(4)
                    if header != b"\x0e\x03\x13\x01":
                        raise Exception(f"header inválido: {header.hex()}")

                    # Mover a destino final
                    local.rename(dest)
                    entry = {"name": str(name), "year": year, "month": month,
                             "file": str(dest), "bytes": dest.stat().st_size,
                             "md5": md5_archivo(dest)}
                    manifest.append(entry)
                    existentes.add(name)
                    break
                except Exception as e:
                    log(f"  Retry {intento}/{MAX_REINTENTOS} {name}: {e}", "WARN")
                    time.sleep(2 ** intento)
            else:
                failed.append({"name": name, "reason": f"falló {MAX_REINTENTOS} reintentos"})

        except Exception as e:
            failed.append({"name": name if 'name' in vars() else '?', "reason": str(e)})

        # Guardar manifest cada 50 granules
        if i % 50 == 0:
            data = {"fuente": f"MODIS {PRODUCTO} v{VERSION}",
                    "tile": TILE_MODIS, "bbox": BBOX_CALI, "periodo": PERIODO,
                    "total_granules": len(manifest),
                    "total_gb": round(sum(e["bytes"] for e in manifest) / 1e9, 3),
                    "failures": len(failed), "granules": manifest}
            tmp = MANIFEST_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(MANIFEST_PATH)

    # ── Manifest final ──
    data = {"fuente": f"MODIS {PRODUCTO} v{VERSION}",
            "tile": TILE_MODIS, "bbox": list(BBOX_CALI), "periodo": PERIODO,
            "total_granules": len(manifest), "failures": len(failed),
            "total_gb": round(sum(e["bytes"] for e in manifest) / 1e9, 3),
            "granules": manifest, "failed": failed}
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(MANIFEST_PATH)

    elapsed = time.time() - t0
    log(f"")
    log(f"✓ DESCARGA COMPLETA — {elapsed:.0f}s")
    log(f"  Total granules: {len(manifest)}")
    log(f"  Total GB:       {data['total_gb']:.2f}")
    log(f"  Fallidos:       {len(failed)}")
    log(f"  Manifest:       {MANIFEST_PATH}")
    log(f"  Destino:        {BASE_DIR}")


# ── TMP_DIR para descarga ──
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    main()
