"""
=============================================================
GeoVision-CLIP Cali — Descarga datos in-situ DAGMA / SISAIRE
Fuentes:
  - SISAIRE IDEAM : http://sisaire.ideam.gov.co/ideam-sisaire-web/
  - DAGMA Cali    : https://www.cali.gov.co/dagma/
Ruta   : D:/analitica/dagma/
=============================================================
REQUISITOS
    pip install requests pandas openpyxl tqdm lxml

NOTAS
    El portal SISAIRE expone un formulario web (no una API REST documentada).
    Este script simula las peticiones HTTP del formulario para obtener los
    reportes CSV/Excel de las 9 estaciones del DAGMA.

    Si el portal cambia su estructura, actualiza los selectores en la
    sección "Parámetros SISAIRE".

    Estaciones DAGMA operativas en Cali (IDs SISAIRE aproximados — 
    verifícalos en el portal antes de correr el script):
        JARDIN_BOTANICO, UNIVALLE, SAN_ANTONIO, COMPARTIR,
        AGUABLANCA, LADERA, PANCE, CHIPICHAPE, UNAL_PALMIRA
    
    Contaminantes: NO2, SO2, O3  (código SISAIRE)
"""

import csv
import hashlib
import json
import os
import time
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

# ── Configuración ─────────────────────────────────────────
BASE_DIR      = Path("D:/analitica/dagma")
MANIFEST_PATH = Path("D:/analitica/manifest_dagma.json")
START_DATE    = date(2020, 1, 1)
END_DATE      = date(2024, 12, 31)

# Parámetros SISAIRE — ajusta si cambia el portal
SISAIRE_BASE   = "http://sisaire.ideam.gov.co/ideam-sisaire-web"
SISAIRE_REPORT = f"{SISAIRE_BASE}/reporte"   # endpoint de descarga

# 9 estaciones DAGMA — nombre y coordenadas aproximadas
ESTACIONES_DAGMA = [
    {"id": "JARDIN_BOTANICO",  "nombre": "Jardín Botánico",    "lat":  3.3895, "lon": -76.5340},
    {"id": "UNIVALLE",         "nombre": "Universidad del Valle","lat":  3.3750, "lon": -76.5340},
    {"id": "SAN_ANTONIO",      "nombre": "San Antonio",         "lat":  3.4510, "lon": -76.5380},
    {"id": "COMPARTIR",        "nombre": "Compartir",           "lat":  3.4320, "lon": -76.5050},
    {"id": "AGUABLANCA",       "nombre": "Aguablanca",          "lat":  3.4200, "lon": -76.4720},
    {"id": "LADERA",           "nombre": "Ladera",              "lat":  3.4080, "lon": -76.5620},
    {"id": "PANCE",            "nombre": "Pance",               "lat":  3.3380, "lon": -76.5580},
    {"id": "CHIPICHAPE",       "nombre": "Chipichape",          "lat":  3.4680, "lon": -76.5320},
    {"id": "UNIVALLE_PALMIRA", "nombre": "UNAL Palmira",        "lat":  3.5050, "lon": -76.3080},
]

CONTAMINANTES = ["NO2", "SO2", "O3"]

# ── Encabezados que imita el navegador ───────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Referer": SISAIRE_BASE,
}


# ── md5 ───────────────────────────────────────────────────
def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ── Descargar reporte SISAIRE por estación + contaminante ─
def descargar_sisaire(session: requests.Session,
                      estacion_id: str, contaminante: str,
                      start: date, end: date,
                      dest_path: Path) -> dict | None:
    """
    Intenta descargar el reporte CSV horario de SISAIRE.
    
    IMPORTANTE: SISAIRE puede requerir autenticación o cambiar su API.
    Si falla con 403/404, accede manualmente a:
        http://sisaire.ideam.gov.co/ideam-sisaire-web/
    y descarga el CSV para cada estación/contaminante. Guárdalo en:
        D:/analitica/dagma/<estacion_id>/<contaminante>.csv
    El script procesará los archivos manuales si los detecta.
    """
    if dest_path.exists():
        data = dest_path.read_bytes()
        return {
            "file":         str(dest_path),
            "estacion":     estacion_id,
            "contaminante": contaminante,
            "md5":          md5_bytes(data),
            "bytes":        len(data),
            "fuente":       "cache",
        }

    params = {
        "estacion":     estacion_id,
        "parametro":    contaminante,
        "fechaInicio":  start.strftime("%Y-%m-%d"),
        "fechaFin":     end.strftime("%Y-%m-%d"),
        "formato":      "csv",
    }

    try:
        resp = session.get(SISAIRE_REPORT, params=params,
                           headers=HEADERS, timeout=60)

        if resp.status_code == 200 and len(resp.content) > 100:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.content)
            return {
                "file":         str(dest_path),
                "estacion":     estacion_id,
                "contaminante": contaminante,
                "md5":          md5_bytes(resp.content),
                "bytes":        len(resp.content),
                "fuente":       "sisaire_api",
            }
        else:
            print(f"  [DAGMA] HTTP {resp.status_code} para {estacion_id}/{contaminante}")
            return None

    except Exception as e:
        print(f"  [DAGMA] Error {estacion_id}/{contaminante}: {e}")
        return None


# ── Consolidar CSVs en un solo Parquet ───────────────────
def consolidar_parquet(manifest: list, dest: Path):
    """
    Une todos los CSV descargados en un DataFrame y lo guarda como Parquet
    con columnas: datetime, estacion, contaminante, valor_ug_m3, lat, lon
    """
    frames = []
    for entrada in manifest:
        path = Path(entrada["file"])
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, parse_dates=["datetime"],
                             dayfirst=False, low_memory=False)
            df["estacion"]     = entrada["estacion"]
            df["contaminante"] = entrada["contaminante"]
            # añadir coordenadas
            est = next((e for e in ESTACIONES_DAGMA
                        if e["id"] == entrada["estacion"]), None)
            if est:
                df["lat"] = est["lat"]
                df["lon"] = est["lon"]
            frames.append(df)
        except Exception as e:
            print(f"  [CONSOLIDAR] Error leyendo {path}: {e}")

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined.sort_values(["estacion", "contaminante", "datetime"],
                              inplace=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(dest, index=False, engine="pyarrow")
        print(f"\n[DAGMA] Parquet consolidado: {dest}")
        print(f"        Filas: {len(combined):,}  |  Columnas: {list(combined.columns)}")
    else:
        print("\n[DAGMA] No hay datos para consolidar.")


# ── Main ──────────────────────────────────────────────────
def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    session  = requests.Session()
    manifest = []

    print("[DAGMA] Descargando datos SISAIRE/DAGMA para Cali")
    print(f"        Estaciones: {len(ESTACIONES_DAGMA)}")
    print(f"        Contaminantes: {CONTAMINANTES}")
    print(f"        Periodo: {START_DATE} → {END_DATE}\n")

    for est in ESTACIONES_DAGMA:
        est_dir = BASE_DIR / est["id"]
        est_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Estación: {est['nombre']} ({est['id']})")

        for cont in tqdm(CONTAMINANTES, desc=f"    {est['id']}", leave=False):
            dest_path = est_dir / f"{cont}_{START_DATE.year}_{END_DATE.year}.csv"
            entrada   = descargar_sisaire(
                session, est["id"], cont, START_DATE, END_DATE, dest_path
            )
            if entrada:
                entrada.update({
                    "lat":    est["lat"],
                    "lon":    est["lon"],
                    "nombre": est["nombre"],
                })
                manifest.append(entrada)
            time.sleep(1)  # respetar el servidor

    # ── Guardar manifest ──────────────────────────────────
    total_bytes = sum(e["bytes"] for e in manifest)
    with open(MANIFEST_PATH, "w") as f:
        json.dump({
            "fuente":      "DAGMA Cali / SISAIRE IDEAM",
            "estaciones":  ESTACIONES_DAGMA,
            "periodo":     f"{START_DATE} / {END_DATE}",
            "total_mb":    round(total_bytes / 1e6, 2),
            "archivos":    manifest,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n[DAGMA] Manifest guardado: {MANIFEST_PATH}")
    print(f"        Archivos descargados: {len(manifest)}")

    # ── Consolidar en Parquet ─────────────────────────────
    parquet_dest = BASE_DIR / "dagma_consolidado.parquet"
    consolidar_parquet(manifest, parquet_dest)

    # ── Guardar mapa de estaciones como GeoJSON ───────────
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [e["lon"], e["lat"]],
                },
                "properties": {
                    "id":     e["id"],
                    "nombre": e["nombre"],
                },
            }
            for e in ESTACIONES_DAGMA
        ],
    }
    geojson_path = BASE_DIR / "estaciones_dagma.geojson"
    geojson_path.write_text(
        json.dumps(geojson, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[DAGMA] GeoJSON de estaciones: {geojson_path}")


if __name__ == "__main__":
    main()
