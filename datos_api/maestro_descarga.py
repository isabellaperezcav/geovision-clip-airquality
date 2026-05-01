"""
=============================================================
GeoVision-CLIP Cali — SCRIPT MAESTRO
Genera el manifest global con hashes MD5 y verifica >= 50 GB
Ruta base: D:/analitica/
=============================================================
ORDEN DE EJECUCIÓN RECOMENDADO
    1. pip install -r requirements_geovision.txt
    2. earthengine authenticate        (una vez)
    3. Configurar .cdsapirc            (una vez)
    4. Configurar .netrc Earthdata     (una vez)
    5. python maestro_descarga.py

SCRIPTS INDIVIDUALES (si quieres correr por separado)
    python descarga_sentinel5p_gee.py
    python descarga_sentinel2_aws.py
    python descarga_era5_cds.py
    python descarga_modis_earthdata.py
    python descarga_dagma_sisaire.py
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR      = Path("D:/analitica")
MANIFEST_GLOBAL = BASE_DIR / "manifest_global.json"
MIN_GB_REQUERIDO = 50.0

# Manifests parciales generados por cada script
MANIFESTS_PARCIALES = {
    "sentinel5p": BASE_DIR / "manifest_sentinel5p.json",   # generado por GEE post-descarga
    "sentinel2":  BASE_DIR / "manifest_sentinel2.json",
    "era5":       BASE_DIR / "manifest_era5.json",
    "modis":      BASE_DIR / "manifest_modis.json",
    "dagma":      BASE_DIR / "manifest_dagma.json",
}

SCRIPTS = {
    "sentinel5p": "descarga_sentinel5p_gee.py",
    "sentinel2":  "descarga_sentinel2_aws.py",
    "era5":       "descarga_era5_cds.py",
    "modis":      "descarga_modis_earthdata.py",
    "dagma":      "descarga_dagma_sisaire.py",
}


# ── Utilidades ────────────────────────────────────────────
def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tamaño_directorio_gb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1e9


def barra(pct: float, ancho: int = 30) -> str:
    lleno = int(pct / 100 * ancho)
    return "█" * lleno + "░" * (ancho - lleno)


# ── Correr un script individual ───────────────────────────
def correr_script(nombre: str, script: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  Ejecutando: {script}")
    print(f"{'='*60}")
    resultado = subprocess.run(
        [sys.executable, script],
        capture_output=False,
    )
    if resultado.returncode != 0:
        print(f"[ERROR] {script} terminó con código {resultado.returncode}")
        return False
    return True


# ── Consolidar todos los manifests parciales ──────────────
def consolidar_manifests() -> dict:
    global_entries = []
    resumen        = {}

    for fuente, manifest_path in MANIFESTS_PARCIALES.items():
        if not manifest_path.exists():
            print(f"  [!] Manifest no encontrado: {manifest_path}")
            resumen[fuente] = {"total_gb": 0, "archivos": 0, "estado": "faltante"}
            continue

        with open(manifest_path) as f:
            data = json.load(f)

        archivos = data.get("archivos", [])
        total_gb = data.get("total_gb", 0)

        resumen[fuente] = {
            "total_gb": total_gb,
            "archivos": len(archivos),
            "estado":   "ok",
        }

        for entrada in archivos:
            entrada["fuente"] = fuente
            global_entries.append(entrada)

    return {"resumen": resumen, "archivos": global_entries}


# ── Verificación de hashes MD5 ────────────────────────────
def verificar_hashes(entries: list) -> tuple[int, int]:
    ok = fallos = 0
    print("\n[VERIFY] Verificando hashes MD5...")
    for entrada in entries:
        path = Path(entrada.get("file", ""))
        expected_md5 = entrada.get("md5", "")
        if not path.exists() or not expected_md5:
            continue
        actual_md5 = md5_file(path)
        if actual_md5 == expected_md5:
            ok += 1
        else:
            print(f"  [✗] Hash incorrecto: {path.name}")
            print(f"      Esperado: {expected_md5}")
            print(f"      Obtenido: {actual_md5}")
            fallos += 1
    return ok, fallos


# ── Reporte final ─────────────────────────────────────────
def imprimir_reporte(resumen: dict, total_gb: float,
                     ok_hash: int, fail_hash: int):
    print("\n" + "═" * 60)
    print("  REPORTE FINAL — GeoVision-CLIP Cali")
    print("═" * 60)

    for fuente, info in resumen.items():
        gb    = info["total_gb"]
        archi = info["archivos"]
        estado = "✓" if info["estado"] == "ok" else "✗"
        pct   = min(gb / MIN_GB_REQUERIDO * 100, 100) / len(resumen)
        print(f"  {estado} {fuente:<15} {gb:6.2f} GB   ({archi} archivos)")

    print("─" * 60)
    pct_total = min(total_gb / MIN_GB_REQUERIDO * 100, 100)
    print(f"  TOTAL              {total_gb:6.2f} GB")
    print(f"  [{barra(pct_total)}] {pct_total:.0f}%")
    print(f"  Mínimo requerido:  {MIN_GB_REQUERIDO:.0f} GB")

    if total_gb >= MIN_GB_REQUERIDO:
        print(f"\n  ✅ DATASET VÁLIDO — supera los {MIN_GB_REQUERIDO} GB requeridos")
    else:
        falta = MIN_GB_REQUERIDO - total_gb
        print(f"\n  ❌ DATASET INSUFICIENTE — faltan {falta:.2f} GB")
        print(f"     Considera ampliar el rango de fechas o reducir el filtro de nubosidad S2")

    print(f"\n  Hashes MD5 verificados: {ok_hash} ✓   {fail_hash} ✗")
    print("═" * 60)


# ── Main ──────────────────────────────────────────────────
def main(correr_scripts: bool = True):
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Paso 1: ejecutar scripts de descarga (opcional si ya se corrieron)
    if correr_scripts:
        for nombre, script in SCRIPTS.items():
            if not Path(script).exists():
                print(f"[!] Script no encontrado: {script} — saltando")
                continue
            exito = correr_script(nombre, script)
            if not exito:
                print(f"[!] {script} falló. Continuando con el siguiente...")

    # Paso 2: consolidar manifests parciales
    print("\n[MAESTRO] Consolidando manifests parciales...")
    datos = consolidar_manifests()
    resumen  = datos["resumen"]
    archivos = datos["archivos"]

    total_gb = sum(v["total_gb"] for v in resumen.values())

    # Paso 3: verificar hashes
    ok_hash, fail_hash = verificar_hashes(archivos)

    # Paso 4: guardar manifest global
    manifest_global = {
        "proyecto":     "GeoVision-CLIP Cali",
        "generado":     datetime.utcnow().isoformat() + "Z",
        "total_gb":     round(total_gb, 3),
        "minimo_requerido_gb": MIN_GB_REQUERIDO,
        "supera_minimo": total_gb >= MIN_GB_REQUERIDO,
        "hashes_ok":    ok_hash,
        "hashes_error": fail_hash,
        "resumen":      resumen,
        "archivos":     archivos,
    }

    MANIFEST_GLOBAL.write_text(
        json.dumps(manifest_global, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # Paso 5: reporte en consola
    imprimir_reporte(resumen, total_gb, ok_hash, fail_hash)
    print(f"\n  Manifest global guardado: {MANIFEST_GLOBAL}")

    # Paso 6: assert requerido por el proyecto
    assert total_gb >= MIN_GB_REQUERIDO, (
        f"Dataset insuficiente: {total_gb:.2f} GB < {MIN_GB_REQUERIDO} GB requeridos"
    )


if __name__ == "__main__":
    # Cambia a False si los scripts ya corrieron y solo quieres regenerar el manifest
    main(correr_scripts=True)
