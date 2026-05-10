from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
from pathlib import Path
import adlfs

STORAGE_ACCOUNT = "stanaliticafinal"
FILESYSTEM = "geovision"

BASE_DIR = Path("D:/analitica/sentinel2")

credential = DefaultAzureCredential(exclude_managed_identity_credential=True)

fs = adlfs.AzureBlobFileSystem(
    account_name=STORAGE_ACCOUNT,
    credential=credential
)

def upload_file(local_path: Path):

    relative_path = local_path.relative_to(BASE_DIR)

    remote_path = (
        f"{FILESYSTEM}/sentinel2/{relative_path.as_posix()}"
    )

    # evitar resubir
    if fs.exists(remote_path):
        print(f"SKIP {remote_path}")
        return

    with local_path.open("rb") as src, fs.open(remote_path, "wb") as dst:
        while chunk := src.read(8 * 1024 * 1024):
            dst.write(chunk)

    print(f"✓ Subido: {remote_path}")

# recorrer todo tu dataset
for file in BASE_DIR.rglob("*.tif"):
    upload_file(file)