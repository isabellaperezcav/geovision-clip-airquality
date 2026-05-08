"""
=====================================================================
GeoVision-CLIP Cali — Script Maestro
=====================================================================

USO:
    python maestro_descarga.py                  # DAGMA completo + muestras
    python maestro_descarga.py --solo-muestras  # solo samples de S2/S5P/ERA5/MODIS
    python maestro_descarga.py --solo-dagma     # solo DAGMA completo
    python maestro_descarga.py --consolidar     # solo consolida manifests
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import PROJECT_ROOT, DATA_DIR, MANIFESTS_DIR
from config import check_disk_space

MANIFEST_GLOBAL = MANIFESTS_DIR / "manifest_global.json"


def md5_file(path: Path) -> str:
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tamano_directorio_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def main():
    solo_muestras = "--solo-muestras" in sys.argv
    solo_dagma    = "--solo-dagma" in sys.argv
    consolidar    = "--consolidar" in sys.argv

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("  GeoVision-CLIP Cali — Pipeline")
    print(f"  Proyecto: {PROJECT_ROOT}")
    print(f"  Datos en: {DATA_DIR}")
    print("="*60)

    scripts_a_correr = []

    if not consolidar:
        check_disk_space("Pipeline")

        if not solo_muestras:
            scripts_a_correr.append(("DAGMA completo", "descarga_dagma_sisaire.py"))

        if not solo_dagma:
            print("\n  [INFO] Muestras de otros datasets disponibles con:")
            print("         python datos_api/descarga_muestras.py")
            # No incluimos muestras automaticamente porque requieren APIs externas
            # con credenciales que el usuario debe configurar primero.
            scripts_a_correr.append(("Muestras", "descarga_muestras.py"))

        for nombre, script in scripts_a_correr:
            ruta = PROJECT_ROOT / "datos_api" / script
            if not ruta.exists():
                print(f"\n  [!] Script no encontrado: {ruta.name}")
                continue
            print(f"\n  Ejecutando: {script}")
            r = subprocess.run([sys.executable, str(ruta)])
            print(f"  {'OK' if r.returncode==0 else 'ERROR ('+str(r.returncode)+')'}")

    # Consolidar manifests
    manifests_info = {}
    for key, path in [("dagma", "manifest_dagma.json"),
                      ("muestras", "manifest_muestras.json")]:
        fp = MANIFESTS_DIR / path
        if fp.exists():
            manifests_info[key] = json.loads(fp.read_text())

    peso_mb = (tamano_directorio_mb(DATA_DIR / "dagma") +
               tamano_directorio_mb(DATA_DIR / "muestras"))

    dagma_data = manifests_info.get("dagma", {})
    muestras_data = manifests_info.get("muestras", {})
    archivos = len(dagma_data.get("entries", dagma_data.get("archivos", []))) + \
               len(muestras_data.get("entries", muestras_data.get("archivos", [])))
    total_mb = dagma_data.get("total_mb", 0) + muestras_data.get("total_mb", 0)
    if total_mb == 0:
        total_mb = peso_mb

    json.dump({
        "proyecto": "GeoVision-CLIP Cali",
        "generado": datetime.now().isoformat(),
        "directorio_datos": str(DATA_DIR),
        "total_mb": round(total_mb, 2),
        "archivos": archivos,
        "estado": "OK" if archivos > 0 else "SIN_DATOS",
        "dagma": dagma_data,
        "muestras": muestras_data,
    }, open(MANIFEST_GLOBAL, "w"), indent=2)

    print(f"\n{'='*60}")
    print(f"  REPORTE FINAL")
    print(f"{'='*60}")
    print(f"  DAGMA:       {dagma_data.get('total_mb', 0):>8.1f} MB")
    print(f"  Muestras:    {muestras_data.get('total_mb', 0):>8.1f} MB")
    print(f"  {'─'*40}")
    print(f"  TOTAL:       {total_mb:>8.1f} MB")
    print(f"  Archivos:    {archivos}")
    print(f"  Manifest:    {MANIFEST_GLOBAL}")
    print(f"{'='*60}")

    if not consolidar and solo_dagma:
        print("\n  Sugerencia: descarga muestras de otros datasets con:")
        print("  python datos_api/descarga_muestras.py")


if __name__ == "__main__":
    main()
