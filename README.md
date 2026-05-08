# GeoVision-CLIP Cali — Pipeline de Descarga DAGMA

## Alcance actual

Solo el dataset **DAGMA / SISAIRE** (ground truth in-situ). Los demás datasets (Sentinel-5P, Sentinel-2, MODIS, ERA5) quedan fuera de este pipeline.

## Datos disponibles

### 9 estaciones DAGMA

| Estación | Zona | Cobertura publicada |
|----------|------|---------------------|
| Transitoria | Oriente | 2014–2019 |
| Pance | Sur | 2014–2021 |
| Compartir | Oriente | 2014–2021 |
| Univalle | Sur | 2014–2021 |
| Base Aérea | Nororiente | 2014–2021 |
| La Flora | Norte | 2014–2021 |
| Esc. Rep. Argentina | Centro | 2014–2021 |
| Cañaveralejo | Suroriente | 2014–2021 |
| La Ermita | Centro | 2013–2021 |

### Fuentes de acceso

- **datos.gov.co** (API Socrata): datasets `jbjb-meez` (ICA Cali), `8e8d-7zqn` (Cañaveralejo), `53gx-j5pc` (Calidad Aire Colombia)
- **datos.cali.gov.co** (CSV manuales): descarga por estación con tag `calidad del aire`
- **SISAIRE** (IDEAM): para datos 2022-2024 que no están en datos abiertos

### ⚠️ Limitación

La cobertura en datos abiertos llega hasta **diciembre 2021**. Para completar el periodo 2022–2024 del proyecto, descargar manualmente desde SISAIRE web y colocar los CSV en `data/dagma/manuales/<ESTACION>/`.

## Almacenamiento

```bash
# SSD (M.2, rápido)
export GEOVISION_DATA_DIR="/mnt/ssd_m2/almacenamiento/carlos_andres_ferro/geovision-clip-airquality/data"

# HDD (más espacio)
export GEOVISION_DATA_DIR="/mnt/hdd/datasets/carlos_andres_ferro/geovision-data"

# Umbral de guardia (default: 25 GB)
export GEOVISION_DISK_WARN_GB=5
```

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Descargar todo
python datos_api/maestro_descarga.py

# O solo el script DAGMA
python datos_api/descarga_dagma_sisaire.py

# Solo consolidar manifests
python datos_api/maestro_descarga.py --consolidar
```

## Credenciales

Ningún dataset requiere autenticación. Las APIs de datos.gov.co son públicas.
Ver `docs/credenciales.md` para más detalles.

## Estructura del proyecto

```
datos_api/
  config.py                       # Configuración central
  descarga_dagma_sisaire.py       # Descarga DAGMA (ground truth)
  maestro_descarga.py              # Pipeline + consolidación
  descarga_sentinel5p_cdse.py     # [LEGACY] no en uso
  descarga_sentinel2_aws.py       # [LEGACY] no en uso
  descarga_era5_cds.py            # [LEGACY] no en uso
  descarga_modis_earthdata.py     # [LEGACY] no en uso
  pipeline_harp.py                # [LEGACY] no en uso
  pipeline_zarr.py                # [LEGACY] no en uso
data/
  dagma/                           # Datos DAGMA descargados
    raw/                           # CSVs crudos de datos.gov.co
    manuales/<ESTACION>/           # CSVs manuales de SISAIRE / datos.cali.gov.co
    estaciones_dagma.geojson       # GeoJSON con ubicación de estaciones
  manifests/                       # Manifests JSON
docs/
  credenciales.md                  # Documentación de APIs
  planes/                          # Planes de implementación
requirements.txt
```
