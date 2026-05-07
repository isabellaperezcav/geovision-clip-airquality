from azure.identity import DefaultAzureCredential

# Storage canónico
STORAGE_ACCOUNT = "stanaliticafinal"
FILESYSTEM = "geovision"
BRONZE_PREFIX = "01-bronze/maiac"
META_PREFIX = "_meta/manifest/maiac"
LOG_PREFIX = "_meta/logs/maiac"


# Auth ADLS Gen2: DefaultAzureCredential hereda az login local. Sin Account Keys.
# Auto-crea el filesystem si no existe.
from azure.storage.filedatalake import DataLakeServiceClient

credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
credential.get_token("https://storage.azure.com/.default")  # sanity early failure

fs = adlfs.AzureBlobFileSystem(account_name=STORAGE_ACCOUNT, credential=credential)

dlsc = DataLakeServiceClient(
    account_url=f"https://{STORAGE_ACCOUNT}.dfs.core.windows.net",
    credential=credential,
)
existing_fs = {f.name for f in dlsc.list_file_systems()}
if FILESYSTEM not in existing_fs:
    dlsc.create_file_system(file_system=FILESYSTEM)
    print(f"[{RUN_ID}] filesystem '{FILESYSTEM}' creado en {STORAGE_ACCOUNT}.")
else:
    print(f"[{RUN_ID}] filesystem '{FILESYSTEM}' ya existe.")

try:
    paths = fs.ls(f"{FILESYSTEM}/")
    print(f"[{RUN_ID}] ADLS OK via DefaultAzureCredential. {len(paths)} entradas en raíz.")
except Exception as exc:
    raise RuntimeError(
        f"No se pudo listar abfss://{FILESYSTEM}@{STORAGE_ACCOUNT}.dfs.core.windows.net/. "
        f"Verificar Storage Blob Data Contributor sobre {STORAGE_ACCOUNT}. Error: {exc}"
    )

def hash_file_dual(path: Path) -> dict:
    """Calcula SHA256 (canónico FAIR) y MD5 (compat. ADLS Content-MD5) en un solo paso."""
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            sha.update(chunk)
            md5.update(chunk)
    return {"sha256": sha.hexdigest(), "md5": md5.hexdigest(), "size_bytes": path.stat().st_size}


def parse_yyyy_mm(granule_name: str) -> tuple[str, str]:
    """MCD19A2.A2024001.h10v08.061.2024004175601.hdf -> ('2024', '01').

    Fix vs run previo: usar timedelta(days=doy-1) en lugar de datetime(year,1,doy)
    que rompe con DOY > 31 ('day is out of range for month').
    """
    julian = granule_name.split(".")[1]  # 'A2024001'
    year = julian[1:5]
    doy = int(julian[5:8])
    dt = datetime(int(year), 1, 1) + timedelta(days=doy - 1)
    return year, f"{dt.month:02d}"


@contextlib.contextmanager
def redirect_to_log(log_path: Path):
    """Redirige stdout y stderr a `log_path` (append). Útil para silenciar earthaccess/tqdm/rich."""
    with log_path.open("a", encoding="utf-8", buffering=1) as fh:
        with contextlib.redirect_stdout(fh), contextlib.redirect_stderr(fh):
            yield


def log(msg: str) -> None:
    """Log conjunto: stdout + log file (con timestamp)."""
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# Sanity check del fix antes de empezar (DOY 60 -> 1 marzo bisiesto / 1 marzo no)
assert parse_yyyy_mm("MCD19A2.A2020060.h10v08.061.x.hdf") == ("2020", "02"), "fix DOY rota"
assert parse_yyyy_mm("MCD19A2.A2021060.h10v08.061.x.hdf") == ("2021", "03"), "fix DOY rota"
assert parse_yyyy_mm("MCD19A2.A2024366.h10v08.061.x.hdf") == ("2024", "12"), "fix DOY rota"
log("parse_yyyy_mm: sanity OK (DOY 60 bisiesto = feb, no bisiesto = mar; DOY 366 = dic).")

# Loop principal: descarga local -> hash -> upload streaming a ADLS -> borrar local.
# Idempotencia: si el remote_path existe, saltar (los 150 granules del run previo
# 20260504T011528Z-75f904dd se saltan automáticamente).
# Output de earthaccess.download (rich + tqdm) se redirige al log file del run.

manifest_entries = []
skipped = []
failed = []

t0 = time.time()
log(f"iniciando loop sobre {len(results)} granules. tmp={TMP_DIR}, log={LOG_FILE}")

for i, granule in enumerate(results, 1):
    name = "<unknown>"
    try:
        urls = granule.data_links()
        if not urls:
            failed.append({"granule": str(granule), "reason": "sin data_links"})
            continue
        url = urls[0]
        name = url.split("/")[-1]
        year, month = parse_yyyy_mm(name)
        remote_path = f"{FILESYSTEM}/{BRONZE_PREFIX}/year={year}/month={month}/{name}"

        # Idempotencia: si ya está en ADLS, saltar (sin tocar LP DAAC).
        if fs.exists(remote_path):
            skipped.append(name)
            if i % 100 == 0:
                log(f"progreso {i}/{len(results)}: ok={len(manifest_entries)} skipped={len(skipped)} failed={len(failed)}")
            continue

        # Descarga (rich/tqdm silenciado al log file).
        with redirect_to_log(LOG_FILE):
            downloaded = earthaccess.download([granule], local_path=str(TMP_DIR), threads=1)
        if not downloaded:
            failed.append({"granule": name, "reason": "earthaccess.download retornó lista vacía"})
            continue
        local = Path(downloaded[0])
        if not local.exists() or local.stat().st_size < 1024:
            failed.append({"granule": name, "reason": f"archivo vacío o ausente: {local}"})
            continue

        # Sanity: header HDF-EOS2 esperado.
        with local.open("rb") as fh:
            header = fh.read(4)
        if header != b"\x0e\x03\x13\x01":
            failed.append({"granule": name, "reason": f"header inválido: {header.hex()}"})
            local.unlink(missing_ok=True)
            continue

        hashes = hash_file_dual(local)

        # Upload streaming a ADLS.
        with local.open("rb") as src, fs.open(remote_path, "wb") as dst:
            while chunk := src.read(8 * 1024 * 1024):
                dst.write(chunk)

        manifest_entries.append({
            "granule": name,
            "remote_path": f"abfss://{remote_path}",
            "year": year,
            "month": month,
            "sha256": hashes["sha256"],
            "md5": hashes["md5"],
            "size_bytes": hashes["size_bytes"],
            "source_url": url,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        })

        # Liberar disco local.
        local.unlink(missing_ok=True)

        if i % 50 == 0:
            elapsed = time.time() - t0
            rate = i / max(elapsed, 1)
            eta = (len(results) - i) / max(rate, 1e-9) / 60
            log(f"progreso {i}/{len(results)}: ok={len(manifest_entries)} skipped={len(skipped)} "
                f"failed={len(failed)} | rate={rate:.2f}/s eta={eta:.1f}min")

        # Backoff conservador para LP DAAC (20-60 req/min límite dinámico).
        time.sleep(2)

    except Exception as exc:
        failed.append({"granule": name, "reason": str(exc)[:200]})
        # Backoff exponencial leve en errores (5s, 10s) para no martillar en cascada.
        time.sleep(5 if len(failed) % 5 else 10)

elapsed = time.time() - t0
log(f"loop terminado en {elapsed/60:.1f} min: ok={len(manifest_entries)} "
    f"skipped={len(skipped)} failed={len(failed)}")

# Manifest YAML (esquema canónico doc 06-manifest-zarr-parquet.md:74-197)
manifest = {
    "dataset": "maiac_aod_mcd19a2_v061",
    "run_id": RUN_ID,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "execution_mode": "local",
    "previous_runs": [
        # los 150 granules de DOY 1-31 vinieron de este run (subidos correctamente,
        # validados size+sha256+header HDF-EOS2 contra manifest 2026-05-04).
        "20260504T011528Z-75f904dd",
    ],
    "source": {
        "provider": "NASA LP DAAC",
        "product": "MCD19A2",
        "version": "061",
        "tile": TILE_MODIS,
        "endpoint": "https://cmr.earthdata.nasa.gov/search",
    },
    "spatial": {
        "bbox_lon_min": BBOX_CALI[0],
        "bbox_lat_min": BBOX_CALI[1],
        "bbox_lon_max": BBOX_CALI[2],
        "bbox_lat_max": BBOX_CALI[3],
    },
    "temporal": {"start": PERIODO[0], "end": PERIODO[1]},
    "counts": {
        "granules_found": len(results),
        "downloaded": len(manifest_entries),
        "skipped_idempotent": len(skipped),
        "failed": len(failed),
    },
    "hash_algo": ["sha256", "md5"],
    "granules": manifest_entries,
    "failures": failed,
}

manifest_path = f"{FILESYSTEM}/{META_PREFIX}/{RUN_ID}.yaml"
with fs.open(manifest_path, "w") as f:
    yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)

total_gb = sum(e["size_bytes"] for e in manifest_entries) / 1e9
log(f"manifest escrito en abfss://{manifest_path}")
log(f"total descargado en este run: {total_gb:.2f} GB ({len(manifest_entries)} granules)")
log(f"saltados por idempotencia: {len(skipped)} granules ya en bucket")

# Subir log file a ADLS y limpiar tmp local.
import shutil

remote_log = f"{FILESYSTEM}/{LOG_PREFIX}/{RUN_ID}.log"
with LOG_FILE.open("rb") as src, fs.open(remote_log, "wb") as dst:
    while chunk := src.read(1 * 1024 * 1024):
        dst.write(chunk)
print(f"[{RUN_ID}] log subido a abfss://{remote_log}")

# Cleanup tmp local. Saltar con env MAIAC_KEEP_TMP=1 para auditoría manual.
if os.environ.get("MAIAC_KEEP_TMP") == "1":
    print(f"[{RUN_ID}] MAIAC_KEEP_TMP=1: tmp preservado en {TMP_DIR}")
else:
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    print(f"[{RUN_ID}] tmp limpio. Notebook MAIAC finalizado.")