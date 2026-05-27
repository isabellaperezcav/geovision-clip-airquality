"""
main.py - Backend FastAPI de GeoVision-CLIP Cali.

Sirve los artefactos precalculados por build_artifacts.py (no hace inferencia en vivo:
el modelo profundo v11 ya corrio y el campo de superficie se obtiene por ST-Kriging
sobre DAGMA; servir precalculado garantiza latencia muy por debajo del umbral de 8 s).

Endpoints (contrato del enunciado: /predict, /validate):
  GET  /health                                  estado del servicio
  GET  /metadata                                unidades, grilla, Moran, rangos
  GET  /predict?pollutant&horizon               superficie completa (GeoJSON)
  POST /predict  {lat,lon,radio_km,contaminante,horizonte}
                                                consulta puntual + recorte al radio
  GET  /validate                                metricas LOO-CV vs DAGMA por estacion
  GET  /v11-pattern?pollutant                   capa overlay del modelo profundo v11
  GET  /download?pollutant&horizon&format=csv|geotiff   descarga del producto
"""

from __future__ import annotations

import io
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"

POLLUTANTS = {"NO2", "SO2", "O3"}
HORIZON_SLUG = {"T+1": "t1", "T+3": "t3", "T+7": "t7"}

app = FastAPI(
    title="GeoVision-CLIP Cali API",
    version="1.0.0",
    description="Mapas de contaminacion de superficie (ug/m3) para Santiago de Cali: "
                "ST-Kriging sobre DAGMA, validacion LOO-CV y capa del modelo profundo v11.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # frontend Next.js (ajustar a dominio en produccion)
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Utilidades de carga (cache en memoria)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=32)
def _read_json(name: str) -> str:
    path = ART / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"artefacto no encontrado: {name}")
    return path.read_text(encoding="utf-8")


def _grid_slug(pollutant: str, horizon: str) -> str:
    if pollutant not in POLLUTANTS:
        raise HTTPException(400, f"pollutant invalido: use {sorted(POLLUTANTS)}")
    if horizon not in HORIZON_SLUG:
        raise HTTPException(400, f"horizon invalido: use {list(HORIZON_SLUG)}")
    return f"grid_{pollutant.lower()}_{HORIZON_SLUG[horizon]}.geojson"


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _cell_center(feature) -> tuple[float, float]:
    """Centro (lon, lat) de un poligono de celda (promedio de los 4 vertices unicos)."""
    ring = feature["geometry"]["coordinates"][0][:4]
    lon = sum(p[0] for p in ring) / 4.0
    lat = sum(p[1] for p in ring) / 4.0
    return lon, lat


# ---------------------------------------------------------------------------
# Endpoints basicos
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "GeoVision-CLIP Cali API",
        "units": "ug/m3",
        "endpoints": ["/health", "/metadata", "/predict", "/validate",
                      "/v11-pattern", "/download"],
    }


@app.get("/health")
def health():
    ok = (ART / "metadata.json").exists()
    return {"status": "ok" if ok else "sin-artefactos", "artifacts": str(ART)}


@app.get("/metadata")
def metadata():
    return JSONResponse(content=json.loads(_read_json("metadata.json")))


# ---------------------------------------------------------------------------
# /predict
# ---------------------------------------------------------------------------

@app.get("/predict")
def predict_grid(
    pollutant: str = Query("NO2"),
    horizon: str = Query("T+1"),
):
    """Superficie completa del contaminante y horizonte (GeoJSON de poligonos)."""
    slug = _grid_slug(pollutant, horizon)
    data = _read_json(slug)
    return Response(content=data, media_type="application/geo+json",
                    headers={"x-data-source": "stkriging-dagma+v11",
                             "cache-control": "public, max-age=120"})


class PredictPoint(BaseModel):
    lat: float = Field(..., ge=3.30, le=3.55, description="latitud en el BBox de Cali")
    lon: float = Field(..., ge=-76.60, le=-76.40, description="longitud en el BBox de Cali")
    radio_km: float = Field(5.0, ge=1.0, le=15.0, description="radio de consulta (1-15 km)")
    contaminante: str = Field("NO2")
    horizonte: str = Field("T+1")


@app.post("/predict")
def predict_point(req: PredictPoint):
    """
    Consulta puntual estilo enunciado: dado (lat, lon, radio_km, contaminante, horizonte)
    devuelve el valor estimado en el punto (celda mas cercana) y las celdas dentro del
    circulo de radio_km, con su incertidumbre.
    """
    slug = _grid_slug(req.contaminante, req.horizonte)
    fc = json.loads(_read_json(slug))
    feats = fc["features"]

    best = None
    best_d = float("inf")
    dentro = []
    for f in feats:
        lon, lat = _cell_center(f)
        d = _haversine_km(req.lat, req.lon, lat, lon)
        if d <= req.radio_km:
            dentro.append(f)
        if d < best_d:
            best_d, best = d, f

    point = None
    if best is not None:
        point = {"value": best["properties"]["value"],
                 "sigma": best["properties"]["sigma"],
                 "dist_km": round(best_d, 3)}

    return {
        "pollutant": req.contaminante,
        "horizon": req.horizonte,
        "units": "ug/m3",
        "query": {"lat": req.lat, "lon": req.lon, "radio_km": req.radio_km},
        "point": point,
        "n_celdas": len(dentro),
        "cells": {"type": "FeatureCollection",
                  "properties": fc.get("properties", {}),
                  "features": dentro},
    }


# ---------------------------------------------------------------------------
# /validate
# ---------------------------------------------------------------------------

@app.get("/validate")
def validate():
    """Metricas LOO-CV vs DAGMA por estacion y resumen por contaminante (ug/m3)."""
    return JSONResponse(content=json.loads(_read_json("validate.json")))


# ---------------------------------------------------------------------------
# /v11-pattern (capa overlay del modelo profundo)
# ---------------------------------------------------------------------------

@app.get("/v11-pattern")
def v11_pattern(pollutant: str = Query("NO2")):
    if pollutant not in POLLUTANTS:
        raise HTTPException(400, f"pollutant invalido: use {sorted(POLLUTANTS)}")
    data = _read_json(f"v11_pattern_{pollutant.lower()}.geojson")
    return Response(content=data, media_type="application/geo+json")


# ---------------------------------------------------------------------------
# /download (CSV y GeoTIFF)
# ---------------------------------------------------------------------------

@app.get("/download")
def download(
    pollutant: str = Query("NO2"),
    horizon: str = Query("T+1"),
    format: str = Query("csv", pattern="^(csv|geotiff)$"),
):
    slug = _grid_slug(pollutant, horizon)
    fc = json.loads(_read_json(slug))
    feats = fc["features"]
    base = f"{pollutant.lower()}_{HORIZON_SLUG[horizon]}"

    if format == "csv":
        lines = ["lon,lat,value_ugm3,sigma_ugm3"]
        for f in feats:
            lon, lat = _cell_center(f)
            p = f["properties"]
            lines.append(f"{lon:.6f},{lat:.6f},{p['value']},{p['sigma']}")
        csv = "\n".join(lines)
        return StreamingResponse(
            io.StringIO(csv), media_type="text/csv",
            headers={"content-disposition": f'attachment; filename="{base}.csv"'})

    # GeoTIFF (2 bandas: value, sigma)
    try:
        import rasterio
        from rasterio.transform import from_origin
    except Exception:
        raise HTTPException(501, "GeoTIFF no disponible (rasterio no instalado); use format=csv")

    meta = json.loads(_read_json("metadata.json"))
    bbox, cell = meta["bbox"], meta["cellDeg"]
    nrow, ncol = meta["gridShape"]
    value = np.full((nrow, ncol), np.nan, dtype="float32")
    sigma = np.full((nrow, ncol), np.nan, dtype="float32")
    for f in feats:
        lon, lat = _cell_center(f)
        j = int(round((lon - bbox["xmin"]) / cell - 0.5))
        i = int(round((lat - bbox["ymin"]) / cell - 0.5))
        if 0 <= i < nrow and 0 <= j < ncol:
            # fila 0 arriba (norte): invertir el eje de latitud para el raster
            value[nrow - 1 - i, j] = f["properties"]["value"]
            sigma[nrow - 1 - i, j] = f["properties"]["sigma"]
    transform = from_origin(bbox["xmin"], bbox["ymax"], cell, cell)
    buf = io.BytesIO()
    with rasterio.open(buf, "w", driver="GTiff", height=nrow, width=ncol, count=2,
                       dtype="float32", crs="EPSG:4326", transform=transform,
                       nodata=float("nan")) as dst:
        dst.write(value, 1); dst.set_band_description(1, "value_ugm3")
        dst.write(sigma, 2); dst.set_band_description(2, "sigma_ugm3")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="image/tiff",
        headers={"content-disposition": f'attachment; filename="{base}.tif"'})
