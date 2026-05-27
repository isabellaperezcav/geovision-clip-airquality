# GeoVision-CLIP Cali - Backend (FastAPI)

API que sirve los mapas de calidad del aire de superficie (ug/m3) para Santiago de
Cali y la validacion geoestadistica. Cumple el contrato de endpoints del enunciado
(`/predict`, `/validate`) sobre artefactos precalculados, con latencia muy por debajo
del umbral de 8 s.

## Que sirve

| Capa | Fuente | Unidad |
|------|--------|--------|
| Mapa principal (9 superficies: 3 contaminantes x 3 horizontes) | ST-Kriging Ordinario sobre observaciones reales DAGMA (`data/processed/dagma_target/overpass.parquet`) | ug/m3 |
| Incertidumbre por celda | sigma de Kriging combinada con el error temporal del pronostico por horizonte | ug/m3 |
| Capa overlay del modelo profundo | patron espacial de v11 (GeoVision-CLIP + GRU), geolocalizado por `sam_segment` | relativo [0,1] |
| Validacion | Leave-One-Station-Out vs DAGMA (O3, SO2) y validacion temporal (NO2) | ug/m3 |

Diseno por contaminante (segun la cobertura real de la red DAGMA):
- **O3**: 7 estaciones, Kriging espacial solido (Moran I cerca de 0,99).
- **SO2**: 5 estaciones. El autoajuste del variograma exponential degenera a microescala y
  colapsa el campo a la media; se detecta y se impone un variograma esferico de escala urbana
  (`_build_ok`), recuperando la estructura espacial (Moran I cerca de 0,97).
- **NO2**: 1 sola estacion (Univalle); el nivel se ancla a Univalle y la textura intraurbana la aporta el patron de v11. Validacion temporal, no espacial.

Pronostico por horizonte (T+1/T+3/T+7): reversion a la media AR(1) (`forecast_reversion`),
el campo regresa hacia la climatologia al crecer el horizonte, por eso los tres mapas evolucionan.

> Nota honesta: con 5 a 7 estaciones tan dispersas, el R2 del LOO-CV es bajo o negativo.
> Es la evidencia que motiva el downscaling profundo: la red terrestre no resuelve la
> heterogeneidad intraurbana por si sola.

## Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/health` | estado del servicio |
| GET | `/metadata` | unidades, grilla, Indice de Moran, rangos por archivo |
| GET | `/predict?pollutant=NO2&horizon=T+1` | superficie completa (GeoJSON de poligonos con `value` y `sigma`) |
| POST | `/predict` | consulta puntual: body `{lat, lon, radio_km, contaminante, horizonte}` -> valor en el punto + celdas dentro del radio |
| GET | `/validate` | metricas LOO-CV vs DAGMA por estacion y resumen por contaminante |
| GET | `/v11-pattern?pollutant=NO2` | capa overlay del patron del modelo profundo |
| GET | `/download?pollutant=O3&horizon=T+1&format=csv\|geotiff` | descarga del producto |

## Ejecucion local (uv)

Los artefactos ya vienen precalculados en `artifacts/`, asi que para levantar la API basta
instalar dependencias y correr uvicorn. La regeneracion (paso opcional) requiere los datos
fuente (DAGMA + v11) que no se incluyen en este paquete.

```powershell
# 1. Instalar dependencias (entorno aislado)
uv sync --project apps/api

# 2. Levantar la API (sirve artifacts/ precalculado)
uv run --project apps/api --directory apps/api uvicorn main:app --host 0.0.0.0 --port 8000

# (opcional) regenerar artefactos, solo si se tienen los datos fuente:
# uv run --project apps/api python apps/api/build_artifacts.py
```

Sin uv, con pip: `pip install -r requirements.txt` y luego `uvicorn main:app --port 8000`
desde `apps/api/`.

La documentacion interactiva queda en `http://localhost:8000/docs`.

## Docker

```bash
# Desde la raiz del repo
docker compose up --build api        # solo backend
docker compose up --build            # backend + frontend
```

La imagen es multi-stage (build de dependencias + runtime minimo) e incluye los
artefactos precalculados, asi que el contenedor es autosuficiente.

## Estructura

```
apps/api/
  main.py             FastAPI (endpoints)
  geostats.py         Kriging Ordinario, forecast, LOO-CV, Moran (funciones puras)
  build_artifacts.py  preprocesamiento -> artifacts/
  artifacts/          9 grids GeoJSON + 3 capas v11 + metadata.json + validate.json
  Dockerfile          imagen multi-stage
  requirements.txt    dependencias congeladas (para Docker)
```

## Reproducibilidad

`SEED = 137` (semilla del proyecto). El Indice de Moran usa 999 permutaciones.
