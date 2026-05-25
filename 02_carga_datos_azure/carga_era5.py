import os
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import adlfs
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

# =============================================================
# FIX WINDOWS AZ CLI
# =============================================================

os.environ["PATH"] += r";C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin"

# =============================================================
# CONFIG
# =============================================================

LOCAL_DIR = Path(r"D:/analitica/era5")

STORAGE_ACCOUNT = "stanaliticafinal"
FILESYSTEM = "geovision"

BRONZE_PREFIX = "01-bronze/climate/era5-land"
META_PREFIX = "_meta/manifest/era5-land"
LOG_PREFIX = "_meta/logs/era5-land"

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

LOG_FILE = Path(f"D:/analitica/upload_era5_{RUN_ID}.log")

# =============================================================
# LOGGING
# =============================================================

def log(msg: str) -> None:

    line = (
        f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
        f"{msg}"
    )

    print(line)

    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

# =============================================================
# HASH
# =============================================================

def hash_file_dual(path: Path) -> dict:

    sha = hashlib.sha256()
    md5 = hashlib.md5()

    with path.open("rb") as f:

        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):

            sha.update(chunk)
            md5.update(chunk)

    return {
        "sha256": sha.hexdigest(),
        "md5": md5.hexdigest(),
        "size_bytes": path.stat().st_size,
    }

# =============================================================
# AUTH ADLS
# =============================================================

credential = DefaultAzureCredential(
    exclude_managed_identity_credential=True
)

# sanity early failure
credential.get_token("https://storage.azure.com/.default")

# adlfs filesystem
fs = adlfs.AzureBlobFileSystem(
    account_name=STORAGE_ACCOUNT,
    credential=credential,
)

# datalake client
dlsc = DataLakeServiceClient(
    account_url=f"https://{STORAGE_ACCOUNT}.dfs.core.windows.net",
    credential=credential,
)

# =============================================================
# CREATE FILESYSTEM IF NOT EXISTS
# =============================================================

existing_fs = {f.name for f in dlsc.list_file_systems()}

if FILESYSTEM not in existing_fs:

    dlsc.create_file_system(file_system=FILESYSTEM)

    log(f"filesystem '{FILESYSTEM}' creado.")

else:

    log(f"filesystem '{FILESYSTEM}' ya existe.")

# =============================================================
# SANITY CHECK ADLS
# =============================================================

try:

    paths = fs.ls(f"{FILESYSTEM}/")

    log(f"ADLS OK. {len(paths)} entradas en raíz.")

except Exception as exc:

    raise RuntimeError(
        f"No se pudo listar "
        f"abfss://{FILESYSTEM}@{STORAGE_ACCOUNT}.dfs.core.windows.net/. "
        f"Error: {exc}"
    )

# =============================================================
# DISCOVER FILES
# =============================================================

files = sorted(LOCAL_DIR.rglob("*.nc"))

if not files:
    raise RuntimeError(f"No se encontraron archivos .nc en {LOCAL_DIR}")

log(f"archivos encontrados: {len(files)}")

# =============================================================
# UPLOAD LOOP
# =============================================================

manifest_entries = []
skipped = []
failed = []

t0 = time.time()

for i, local_file in enumerate(files, 1):

    name = local_file.name

    try:

        relative = local_file.relative_to(LOCAL_DIR)

        year = relative.parts[0]

        remote_path = (
            f"{FILESYSTEM}/"
            f"{BRONZE_PREFIX}/"
            f"year={year}/"
            f"{name}"
        )

        # =====================================================
        # IDEMPOTENCIA
        # =====================================================

        if fs.exists(remote_path):

            skipped.append(name)

            if i % 25 == 0:

                log(
                    f"progreso {i}/{len(files)} | "
                    f"ok={len(manifest_entries)} "
                    f"skipped={len(skipped)} "
                    f"failed={len(failed)}"
                )

            continue

        # =====================================================
        # HASH
        # =====================================================

        hashes = hash_file_dual(local_file)

        # =====================================================
        # UPLOAD STREAMING
        # =====================================================

        with local_file.open("rb") as src, fs.open(remote_path, "wb") as dst:

            while chunk := src.read(8 * 1024 * 1024):
                dst.write(chunk)

        manifest_entries.append({
            "file": name,
            "remote_path": f"abfss://{remote_path}",
            "year": year,
            "sha256": hashes["sha256"],
            "md5": hashes["md5"],
            "size_bytes": hashes["size_bytes"],
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })

        size_mb = hashes["size_bytes"] / 1e6

        log(
            f"[{i}/{len(files)}] OK "
            f"{name} | {size_mb:.2f} MB"
        )

        # throttle leve
        time.sleep(0.2)

    except Exception as exc:

        failed.append({
            "file": name,
            "reason": str(exc)[:300],
        })

        log(f"ERROR {name}: {exc}")

        time.sleep(1)

# =============================================================
# SUMMARY
# =============================================================

elapsed = time.time() - t0

log(
    f"upload terminado en {elapsed/60:.1f} min | "
    f"ok={len(manifest_entries)} "
    f"skipped={len(skipped)} "
    f"failed={len(failed)}"
)

# =============================================================
# MANIFEST JSON
# =============================================================

manifest = {
    "dataset": "era5_land_cali",
    "run_id": RUN_ID,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "execution_mode": "local",
    "storage_account": STORAGE_ACCOUNT,
    "filesystem": FILESYSTEM,
    "prefix": BRONZE_PREFIX,
    "counts": {
        "files_found": len(files),
        "uploaded": len(manifest_entries),
        "skipped": len(skipped),
        "failed": len(failed),
    },
    "hash_algo": ["sha256", "md5"],
    "files": manifest_entries,
    "failures": failed,
}

manifest_path = (
    f"{FILESYSTEM}/"
    f"{META_PREFIX}/"
    f"{RUN_ID}.json"
)

import json

with fs.open(manifest_path, "w") as f:

    json.dump(
        manifest,
        f,
        indent=2,
    )

log(f"manifest escrito: abfss://{manifest_path}")

# =============================================================
# SUBIR LOG
# =============================================================

remote_log = (
    f"{FILESYSTEM}/"
    f"{LOG_PREFIX}/"
    f"{RUN_ID}.log"
)

with LOG_FILE.open("rb") as src, fs.open(remote_log, "wb") as dst:

    while chunk := src.read(1 * 1024 * 1024):
        dst.write(chunk)

log(f"log subido: abfss://{remote_log}")

# =============================================================
# FINAL
# =============================================================

total_gb = (
    sum(e["size_bytes"] for e in manifest_entries)
    / 1e9
)

print("\n=================================================")
print("UPLOAD ERA5 FINALIZADO")
print("=================================================")
print(f"Subidos : {len(manifest_entries)}")
print(f"Saltados: {len(skipped)}")
print(f"Fallidos: {len(failed)}")
print(f"Total GB: {total_gb:.2f}")
print("=================================================")

print(
    f"\nDestino:\n"
    f"abfss://{FILESYSTEM}@"
    f"{STORAGE_ACCOUNT}.dfs.core.windows.net/"
    f"{BRONZE_PREFIX}/"
)