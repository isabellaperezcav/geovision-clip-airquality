"""
=============================================================
GeoVision-CLIP Cali — Descarga MODIS MAIAC AOD (MCD19A2)
Fuente : NASA Earthdata (LP DAAC)
Ruta   : D:/analitica/modis/
=============================================================
REQUISITOS
    pip install requests tqdm

CONFIGURACIÓN (una sola vez)
    1. Regístrate en https://urs.earthdata.nasa.gov
    2. En "Applications" → "Authorized Apps", acepta el acceso a LP DAAC
    3. Crea el archivo  C:/Users/<tu_usuario>/.netrc  con:

        machine urs.earthdata.nasa.gov
           login <tu_usuario>
           password <tu_contraseña>

    4. Crea también  C:/Users/<tu_usuario>/.urs_cookies  (archivo vacío)

    O bien: pon tus credenciales en las constantes EARTHDATA_USER / PASS
    (menos seguro, solo para pruebas).

NOTAS
    - Tile MODIS que cubre Cali: h10v09  (horizontal=10, vertical=9)
    - Producto: MCD19A2.061 (MAIAC Land Aerosol Optical Depth)
    - Resolución: 1 km, diario
    - Banda usada: Optical_Depth_047  (AOD a 0.47 µm — proxy PM2.5)
"""

import hashlib
import json
import os
import re
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from tqdm import tqdm

# ── Configuración ─────────────────────────────────────────
BASE_DIR        = Path("D:/analitica/modis")
START_DATE      = date(2020, 1, 1)
END_DATE        = date(2024, 12, 31)
TILE            = "h10v09"                   # tile MODIS para Cali
PRODUCTO        = "MCD19A2.061"
EARTHDATA_USER  = ""                         # déjalo vacío si usas .netrc
EARTHDATA_PASS  = ""
CMR_SEARCH_URL  = "https://cmr.earthdata.nasa.gov/search/granules.json"
MANIFEST_PATH   = Path("D:/analitica/manifest_modis.json")
MAX_RETRIES     = 3


# ── Sesión autenticada ────────────────────────────────────
def get_session() -> requests.Session:
    s = requests.Session()
    if EARTHDATA_USER and EARTHDATA_PASS:
        s.auth = (EARTHDATA_USER, EARTHDATA_PASS)
    else:
        # Usa .netrc automáticamente mediante requests
        import netrc
        try:
            n   = netrc.netrc()
            creds = n.authenticators("urs.earthdata.nasa.gov")
            if creds:
                s.auth = (creds[0], creds[2])
        except Exception:
            print("[MODIS] No se encontró .netrc — autenticación puede fallar")
    return s


# ── Buscar granules via CMR ───────────────────────────────
def buscar_granules(session: requests.Session,
                    start: date, end: date,
                    tile: str, producto: str) -> list[dict]:
    """
    Consulta el Common Metadata Repository (CMR) de NASA para obtener
    la lista de granules disponibles para el tile y rango de fechas.
    Devuelve lista de {fecha, url_download, nombre}.
    """
    params = {
        "short_name":      producto.split(".")[0],   # "MCD19A2"
        "version":         producto.split(".")[1],    # "061"
        "temporal":        f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
        "producer_granule_id": f"*{tile}*",
        "page_size":       500,
        "page_num":        1,
    }

    granules = []
    while True:
        resp = session.get(CMR_SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("feed", {}).get("entry", [])
        if not items:
            break
        for item in items:
            links = [l for l in item.get("links", [])
                     if l.get("rel") == "http://esipfed.org/ns/fedsearch/1.1/data#"
                     and l.get("href", "").endswith(".hdf")]
            if links:
                granules.append({
                    "nombre": item["producer_granule_id"],
                    "fecha":  item["time_start"][:10],
                    "url":    links[0]["href"],
                })
        params["page_num"] += 1
        if len(items) < params["page_size"]:
            break

    return granules


# ── Descargar un granule .hdf ─────────────────────────────
def descargar_granule(session: requests.Session,
                      url: str, nombre: str,
                      fecha: str, dest_dir: Path) -> dict | None:
    dest = dest_dir / nombre
    if dest.exists():
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)

    for intento in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, stream=True, timeout=120)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(1024 * 256):
                    f.write(chunk)

            md5 = hashlib.md5(dest.read_bytes()).hexdigest()
            return {
                "file":   str(dest),
                "nombre": nombre,
                "fecha":  fecha,
                "url":    url,
                "md5":    md5,
                "bytes":  dest.stat().st_size,
            }
        except Exception as e:
            print(f"  [MODIS] Intento {intento}/{MAX_RETRIES} falló: {e}")
            time.sleep(5 * intento)

    return None


# ── Main ──────────────────────────────────────────────────
def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    session  = get_session()
    manifest = []
    total_bytes = 0

    print(f"[MODIS] Buscando granules {PRODUCTO} tile={TILE}")
    print(f"        Periodo: {START_DATE} → {END_DATE}\n")

    granules = buscar_granules(session, START_DATE, END_DATE, TILE, PRODUCTO)
    print(f"[MODIS] Granules encontrados: {len(granules)}\n")

    for g in tqdm(granules, desc="MCD19A2"):
        year     = g["fecha"][:4]
        dest_dir = BASE_DIR / year
        entrada  = descargar_granule(session, g["url"], g["nombre"],
                                     g["fecha"], dest_dir)
        if entrada:
            manifest.append(entrada)
            total_bytes += entrada["bytes"]
        time.sleep(0.3)

    # ── Guardar manifest ──────────────────────────────────
    with open(MANIFEST_PATH, "w") as f:
        json.dump({
            "fuente":    f"MODIS MAIAC AOD — {PRODUCTO}",
            "tile":      TILE,
            "periodo":   f"{START_DATE} / {END_DATE}",
            "total_gb":  round(total_bytes / 1e9, 3),
            "granules":  len(manifest),
            "archivos":  manifest,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n[MODIS] ✓ Descarga finalizada")
    print(f"        Granules descargados: {len(manifest)}")
    print(f"        Total: {total_bytes/1e9:.2f} GB")
    print(f"        Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
