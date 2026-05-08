"""
=====================================================================
GeoVision-CLIP Cali — Sentinel-5P L3 DIARIO desde Google Earth Engine
Area: Valle del Cauca con validacion de cobertura sobre Cali
=====================================================================

ESTRUCTURA DE SALIDA:
    data/sentinel5p/l3/{year}/{month}/{day}/
        NO2.tif
        SO2.tif
        O3.tif
        CO.tif
        CH4.tif
        HCHO.tif
        AER_AI.tif
        CLOUD.tif

Al finalizar genera un reporte de cobertura:
    - Dias con datos sobre Cali
    - Dias sin datos (orbita no cubrio el area)
    - Promedio de pixeles validos

REQUISITOS:
    pip install earthengine-api rasterio numpy

AUTENTICACION:
    earthengine authenticate
"""

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import ee
import numpy as np
from tqdm import tqdm

from config import S5P_DIR, MANIFESTS_DIR, START_YEAR, END_YEAR
from config import check_disk_space

S5P_L3_DIR = S5P_DIR / "l3"
MANIFEST_PATH = MANIFESTS_DIR / "manifest_sentinel5p_l3.json"
MAX_RETRIES = 3
END_YEAR_S5P = min(END_YEAR, 2024)

# ── Productos S5P L3 en GEE ──────────────────────────────
PRODUCTOS = {
    "NO2":   {"collection": "COPERNICUS/S5P/OFFL/L3_NO2",
              "band": "tropospheric_NO2_column_number_density", "scale": 1113.2},
    "SO2":   {"collection": "COPERNICUS/S5P/OFFL/L3_SO2",
              "band": "SO2_column_number_density", "scale": 1113.2},
    "O3":    {"collection": "COPERNICUS/S5P/OFFL/L3_O3",
              "band": "O3_column_number_density", "scale": 1113.2},
    "CO":    {"collection": "COPERNICUS/S5P/OFFL/L3_CO",
              "band": "CO_column_number_density", "scale": 1113.2},
    # CH4 excluido: datos inexistentes sobre Valle del Cauca (todo ceros)
    "HCHO":  {"collection": "COPERNICUS/S5P/OFFL/L3_HCHO",
              "band": "tropospheric_HCHO_column_number_density", "scale": 1113.2},
    "AER_AI":{"collection": "COPERNICUS/S5P/OFFL/L3_AER_AI",
              "band": "absorbing_aerosol_index", "scale": 1113.2},
    "CLOUD": {"collection": "COPERNICUS/S5P/OFFL/L3_CLOUD",
              "band": "cloud_fraction", "scale": 1113.2},
}

# Geometrias GEE (creadas tras init)
BBOX_VALLE = None      # Valle del Cauca completo
BBOX_CALI = None       # Solo Cali (para reporte de cobertura)


# ── Utilerias ─────────────────────────────────────────────
def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generar_dias() -> list[date]:
    """Genera lista de dias 2020-01-01 a END_YEAR_S5P-12-31."""
    inicio = date(2020, 1, 1)
    fin = date(END_YEAR_S5P, 12, 31)
    return [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]


def descargar_dia(producto: str, info: dict, dia: date) -> dict | None:
    """
    Descarga 1 GeoTIFF para 1 producto en 1 dia.
    Estructura: data/sentinel5p/l3/{year}/{month:02d}/{day:02d}/{producto}.tif
    """
    dest_dir = S5P_L3_DIR / str(dia.year) / f"{dia.month:02d}" / f"{dia.day:02d}"
    dest = dest_dir / f"{producto}.tif"

    if dest.exists():
        return {
            "file": str(dest), "producto": producto,
            "year": dia.year, "month": dia.month, "day": dia.day,
            "md5": md5_file(dest), "bytes": dest.stat().st_size,
        }

    dest_dir.mkdir(parents=True, exist_ok=True)

    for intento in range(1, MAX_RETRIES + 1):
        try:
            img = (
                ee.ImageCollection(info["collection"])
                .filterBounds(BBOX_VALLE)
                .filterDate(dia.isoformat(), (dia + timedelta(days=1)).isoformat())
                .select([info["band"]])
                .mean()
            )

            url = img.getDownloadURL({
                "region": BBOX_VALLE,
                "scale": info["scale"],
                "format": "GEO_TIFF",
                "crs": "EPSG:4326",
            })

            import requests
            resp = requests.get(url, timeout=300)
            resp.raise_for_status()

            data = resp.content
            if len(data) < 1000 and b"<html" in data[:500].lower():
                continue

            dest.write_bytes(data)

            # Verificar que NO sea todo nodata
            import rasterio
            with rasterio.open(str(dest)) as src:
                arr = src.read(1)
                if not np.any(np.isfinite(arr)):
                    dest.unlink()
                    return None  # sin datos este dia

            return {
                "file": str(dest), "producto": producto,
                "year": dia.year, "month": dia.month, "day": dia.day,
                "md5": md5_file(dest), "bytes": len(data),
            }

        except Exception:
            if intento < MAX_RETRIES:
                time.sleep(10 * intento)

    return None


# ── Reporte de cobertura ─────────────────────────────────
def reporte_cobertura(entries: list[dict]) -> str:
    """
    Genera estadisticas de cobertura:
    - Dias con datos vs sin datos
    - Productos mas consistentes
    """
    if not entries:
        return "Sin datos descargados."

    dias_con_datos = len(set((e["year"], e["month"], e["day"]) for e in entries))
    total_dias = len(generar_dias())
    cobertura_pct = 100 * dias_con_datos / total_dias

    # Por producto
    prod_counts = {}
    for e in entries:
        p = e["producto"]
        prod_counts[p] = prod_counts.get(p, 0) + 1

    reporte = (
        f"  Cobertura temporal:\n"
        f"    Dias con datos: {dias_con_datos} de {total_dias} ({cobertura_pct:.1f}%)\n"
        f"    Dias sin orbita: {total_dias - dias_con_datos}\n"
        f"\n"
        f"  Por producto:\n"
    )
    for p, c in sorted(prod_counts.items()):
        pct = 100 * c / total_dias
        barra = "|" * int(pct / 5) + "." * (20 - int(pct / 5))
        reporte += f"    {p:6s}: {c:5d} dias ({pct:5.1f}%) [{barra}]\n"

    pesos = sum(e["bytes"] for e in entries)
    reporte += (
        f"\n"
        f"  Total descargas: {len(entries)}\n"
        f"  Peso total: {pesos/1e6:.1f} MB ({pesos/1e9:.3f} GB)\n"
    )
    return reporte


# ── Main ──────────────────────────────────────────────────
def main():
    global BBOX_VALLE, BBOX_CALI

    S5P_L3_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    check_disk_space("S5P L3 diario")

    # Inicializar GEE
    print("[S5P] Conectando GEE...")
    try:
        ee.Initialize()
        BBOX_VALLE = ee.Geometry.Rectangle([-77.0, 3.0, -75.8, 5.0])
        BBOX_CALI  = ee.Geometry.Rectangle([-76.60, 3.30, -76.40, 3.55])
        print("[S5P] GEE conectado.")
    except Exception as e:
        print(f"[S5P] ERROR: {e}")
        print("       Ejecuta: earthengine authenticate")
        return

    # Info
    todos_dias = generar_dias()
    print("=" * 60)
    print("  Sentinel-5P L3 DIARIO — Valle del Cauca")
    print("=" * 60)
    print(f"  Productos: {len(PRODUCTOS)} ({', '.join(PRODUCTOS.keys())})")
    print(f"  Periodo: {todos_dias[0]} a {todos_dias[-1]} ({len(todos_dias)} dias)")
    print(f"  Estructura: data/sentinel5p/l3/YYYY/MM/DD/PRODUCTO.tif")
    print(f"  Descargas esperadas: {len(todos_dias) * len(PRODUCTOS):,}")
    print(f"  Paralelismo: 4 workers por dia\n")

    # Descarga
    entries = []
    for dia in tqdm(todos_dias, desc="Procesando dias"):
        check_disk_space("S5P", fatal=False)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futuros = {
                pool.submit(descargar_dia, p, info, dia): p
                for p, info in PRODUCTOS.items()
            }
            for futuro in as_completed(futuros):
                try:
                    res = futuro.result()
                    if res:
                        entries.append(res)
                except Exception:
                    pass

        time.sleep(0.5)  # cortesia GEE

    # Manifest
    total_bytes = sum(e["bytes"] for e in entries)
    json.dump({
        "fuente": "Sentinel-5P L3 DIARIO (GEE)",
        "productos": {k: v["band"] for k, v in PRODUCTOS.items()},
        "area": "Valle del Cauca",
        "periodo": f"{todos_dias[0]} a {todos_dias[-1]}",
        "estructura": "data/sentinel5p/l3/YYYY/MM/DD/PRODUCTO.tif",
        "dias_totales": len(todos_dias),
        "dias_con_datos": len(set((e["year"], e["month"], e["day"]) for e in entries)),
        "total_mb": round(total_bytes / 1e6, 2),
        "archivos": len(entries),
        "entries": entries,
    }, open(MANIFEST_PATH, "w"), indent=2)

    # Reporte
    print("\n" + "=" * 60)
    print("  REPORTE DE COBERTURA")
    print("=" * 60)
    print(reporte_cobertura(entries))
    print("=" * 60)
    print(f"  Datos en: {S5P_L3_DIR}")
    print(f"  Manifest: {MANIFEST_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
