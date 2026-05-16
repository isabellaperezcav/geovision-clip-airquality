#!/usr/bin/env python3
"""
=============================================================================
GeoVision-CLIP Cali — EDA Sentinel-2 L2A
=============================================================================
Análisis exploratorio del dataset de imágenes Sentinel-2 (347 escenas, 10 bandas,
277 GB) según los requisitos de Situación 1 del proyecto final.

VISUALIZACIONES (≥10):
  1. Escenas por año (barras + tendencia)
  2. Escenas por mes (barras apiladas por año)
  3. Heatmap densidad temporal año×mes
  4. Distribución por tile (18NUJ vs 18NUK) — pie chart
  5. Mapa de cobertura espacial (footprints de tiles sobre Cali)
  6. Boxplots de reflectancia por banda
  7. Histogramas de distribución por banda
  8. Matriz de correlación entre bandas (Pearson)
  9. Serie temporal NDVI (mediana mensual)
  10. Completitud de píxeles por escena
  11. Tabla resumen de estadísticas descriptivas

USO:
    python scripts/scripts_eda/eda_sentinel2.py

OUTPUT:
    outputs/eda/sentinel2/  →  gráficas PNG + reporte TXT + CSV
"""

import json
import random
import sys
import warnings
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import rasterio
import seaborn as sns
from matplotlib.patches import Rectangle
from scipy import stats
from tqdm import tqdm

# ── Config ─────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = ROOT / "data" / "manifests" / "manifest_sentinel2.json"
OUT_DIR = ROOT / "outputs" / "eda" / "sentinel2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_SAMPLE_SCENES = 40  # escenas aleatorias para estadísticas de píxeles
OVERVIEW_LEVEL = 4    # overview level 4 = 1/16 resolución (~686×686 px)
RANDOM_SEED = 42

warnings.filterwarnings("ignore")
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 9,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
})

# ── Banda info ─────────────────────────────────────────

BANDAS = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
BANDA_LABELS = {
    "B02": "Blue (490 nm)",
    "B03": "Green (560 nm)",
    "B04": "Red (665 nm)",
    "B05": "RedEdge 1 (705 nm)",
    "B06": "RedEdge 2 (740 nm)",
    "B07": "RedEdge 3 (783 nm)",
    "B08": "NIR (842 nm)",
    "B8A": "NIR narrow (865 nm)",
    "B11": "SWIR 1 (1610 nm)",
    "B12": "SWIR 2 (2190 nm)",
}
BANDA_RES = {
    "B02": "10m", "B03": "10m", "B04": "10m", "B08": "10m",
    "B05": "20m", "B06": "20m", "B07": "20m", "B8A": "20m",
    "B11": "20m", "B12": "20m",
}
COLORS = plt.cm.tab10(np.linspace(0, 1, 10))

# ── Helpers ────────────────────────────────────────────

def parse_scene_date(scene_id: str) -> datetime:
    """S2B_18NUJ_20200127_0_L2A → datetime(2020, 1, 27)."""
    parts = scene_id.split("_")
    if len(parts) >= 3 and len(parts[2]) == 8:
        return datetime.strptime(parts[2], "%Y%m%d")
    return None

def parse_tile(scene_id: str) -> str:
    """S2B_18NUJ_20200127_0_L2A → '18NUJ'."""
    parts = scene_id.split("_")
    return parts[1] if len(parts) >= 2 else "?"

def parse_sat(scene_id: str) -> str:
    """S2B_18NUJ_20200127_0_L2A → 'S2B'."""
    return scene_id.split("_")[0]

def guardar_fig(fig, name):
    path = OUT_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path

def fmt_bytes(b):
    if b > 1e9: return f"{b/1e9:.2f} GB"
    if b > 1e6: return f"{b/1e6:.2f} MB"
    return f"{b/1e3:.2f} KB"

# ── Load manifest ─────────────────────────────────────

def load_manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════
# SECCIÓN 1 — PANORAMA TEMPORAL (desde manifest, sin leer GeoTIFFs)
# ═══════════════════════════════════════════════════════

def plot_escenas_por_ano(entries):
    """Fig 1: Barras de escenas por año + línea de tendencia."""
    years = Counter()
    for e in entries:
        dt = parse_scene_date(e["scene_id"])
        if dt:
            years[dt.year] += 1
    df = pd.DataFrame({"año": list(years.keys()), "escenas": list(years.values())}).sort_values("año")
    fig, ax1 = plt.subplots(figsize=(10, 5))
    bars = ax1.bar(df["año"], df["escenas"], color="#2196F3", alpha=0.8, edgecolor="white")
    ax1.plot(df["año"], df["escenas"], "o-", color="#C62828", linewidth=2, markersize=8, zorder=5)
    for bar, val in zip(bars, df["escenas"]):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height()+2, str(val),
                 ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Año")
    ax1.set_ylabel("Escenas (imágenes completas, 10 bandas)")
    ax1.set_title("Fig 1: Escenas Sentinel-2 por año\n(2020–2024, nubes <60%)",
                  fontweight="bold")
    ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax1.set_xticks(df["año"])
    # Anotación sobre 2022
    ax1.annotate("2022: mínimo de nubes\nen Cali o El Niño?\n(verificar con ERA5)",
                 xy=(2022, df[df["año"]==2022]["escenas"].values[0]),
                 xytext=(2021, df["escenas"].max()*0.85),
                 arrowprops=dict(arrowstyle="->", color="darkred"),
                 fontsize=8, color="darkred", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    ax1.grid(axis="y", alpha=0.3)
    return guardar_fig(fig, "01_escenas_por_ano")


def plot_escenas_por_mes(entries):
    """Fig 2: Barras apiladas por año para cada mes."""
    year_month = defaultdict(lambda: defaultdict(int))
    all_years = set()
    for e in entries:
        dt = parse_scene_date(e["scene_id"])
        if dt:
            year_month[dt.month][dt.year] += 1
            all_years.add(dt.year)
    all_years = sorted(all_years)
    months = range(1, 13)
    month_names = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    data = np.zeros((12, len(all_years)))
    for mi, m in enumerate(months):
        for yi, y in enumerate(all_years):
            data[mi, yi] = year_month[m].get(y, 0)

    fig, ax = plt.subplots(figsize=(12, 5))
    colors_years = plt.cm.viridis(np.linspace(0.1, 0.95, len(all_years)))
    bottom = np.zeros(12)
    for yi, y in enumerate(all_years):
        ax.bar(range(12), data[:, yi], bottom=bottom, label=str(y),
               color=colors_years[yi], alpha=0.85, edgecolor="white", linewidth=0.5)
        bottom += data[:, yi]
    ax.set_xticks(range(12))
    ax.set_xticklabels(month_names)
    ax.set_xlabel("Mes")
    ax.set_ylabel("Escenas")
    ax.set_title("Fig 2: Escenas Sentinel-2 por mes (apilado por año)", fontweight="bold")
    ax.legend(title="Año", ncol=3, fontsize=8, title_fontsize=9)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.grid(axis="y", alpha=0.3)
    return guardar_fig(fig, "02_escenas_por_mes")


def plot_heatmap_temporal(entries):
    """Fig 3: Heatmap año×mes de densidad de escenas."""
    year_month = defaultdict(lambda: defaultdict(int))
    for e in entries:
        dt = parse_scene_date(e["scene_id"])
        if dt:
            year_month[dt.year][dt.month] += 1
    years = sorted(year_month.keys())
    data = np.zeros((len(years), 12))
    for yi, y in enumerate(years):
        for m in range(1, 13):
            data[yi, m-1] = year_month[y].get(m, 0)

    fig, ax = plt.subplots(figsize=(12, 4))
    sns.heatmap(data, annot=True, fmt=".0f", cmap="YlOrRd",
                xticklabels=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"],
                yticklabels=years,
                cbar_kws={"label": "Escenas"}, linewidths=0.5, linecolor="white",
                vmin=0, vmax=data.max(), ax=ax)
    ax.set_title("Fig 3: Heatmap de densidad temporal (escenas por año-mes)", fontweight="bold")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Año")
    # Anotar meses sin datos
    for yi in range(len(years)):
        for mi in range(12):
            if data[yi, mi] == 0:
                ax.add_patch(plt.Rectangle((mi, yi), 1, 1, fill=False,
                                           edgecolor="red", lw=1.5, hatch="///"))
    return guardar_fig(fig, "03_heatmap_temporal")


# ═══════════════════════════════════════════════════════
# SECCIÓN 2 — COBERTURA ESPACIAL
# ═══════════════════════════════════════════════════════

def plot_pie_tiles(entries):
    """Fig 4: Distribución por tile MGRS."""
    tiles = Counter()
    sats = Counter()
    for e in entries:
        tiles[parse_tile(e["scene_id"])] += 1
        sats[parse_sat(e["scene_id"])] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    # Pie: tiles
    tile_labels = [f"{t}\n({c} escenas)" for t, c in tiles.items()]
    colors_tile = ["#1E88E5", "#FFC107"]
    ax1.pie(tiles.values(), labels=tile_labels, autopct="%1.1f%%",
            colors=colors_tile, startangle=90, textprops={"fontsize": 10})
    ax1.set_title("Distribución por tile MGRS", fontweight="bold")
    # Pie: satellites
    sat_labels = [f"{s} ({c})" for s, c in sats.items()]
    ax2.pie(sats.values(), labels=sat_labels, autopct="%1.1f%%",
            colors=["#4CAF50", "#FF5722"], startangle=90, textprops={"fontsize": 10})
    ax2.set_title("Distribución por satélite", fontweight="bold")
    fig.suptitle("Fig 4: Cobertura espacial — tiles y satélites", fontweight="bold", y=1.02)
    return guardar_fig(fig, "04_tiles_satelites")


def plot_mapa_cobertura(entries):
    """Fig 5: Mapa de cobertura espacial con tiles MGRS."""
    # Tiles MGRS approximate bounds (UTM 18N)
    # 18NUJ: roughly Cali city + south
    # 18NUK: roughly Yumbo + north
    # BBox download: [-76.65, 3.25, -76.35, 3.60]
    # We'll draw in lat/lon

    tile_18NUJ_lon = [-76.60, -76.45, -76.45, -76.60, -76.60]
    tile_18NUJ_lat = [3.30, 3.30, 3.55, 3.55, 3.30]
    tile_18NUK_lon = [-76.60, -76.45, -76.45, -76.60, -76.60]
    tile_18NUK_lat = [3.55, 3.55, 3.70, 3.70, 3.55]

    fig, ax = plt.subplots(figsize=(9, 8))
    # Draw tiles
    ax.fill(tile_18NUJ_lon, tile_18NUJ_lat, alpha=0.15, color="#1E88E5", label="18NUJ (Cali)")
    ax.fill(tile_18NUK_lon, tile_18NUK_lat, alpha=0.15, color="#FFC107", label="18NUK (Yumbo)")
    ax.plot(tile_18NUJ_lon, tile_18NUJ_lat, "b-", linewidth=2)
    ax.plot(tile_18NUK_lon, tile_18NUK_lat, "orange", linewidth=2)
    # Draw bbox
    bbox_lon = [-76.65, -76.35, -76.35, -76.65, -76.65]
    bbox_lat = [3.25, 3.25, 3.60, 3.60, 3.25]
    ax.plot(bbox_lon, bbox_lat, "r--", linewidth=1.5, label="BBox descarga")
    # Mark Cali
    ax.scatter(-76.532, 3.451, marker="*", s=300, color="darkred", zorder=10,
               label="Cali centro", edgecolors="white", linewidth=1.5)
    # DAGMA stations
    dagma_stations = {
        "Base Aérea": (-76.488, 3.478), "Cañaveralejo": (-76.511, 3.417),
        "Compartir": (-76.505, 3.432), "ERA Obrero": (-76.525, 3.450),
        "La Ermita": (-76.532, 3.451), "La Flora": (-76.518, 3.478),
        "Pance": (-76.558, 3.338), "Navarro": (-76.482, 3.426),
        "Univalle": (-76.534, 3.375),
    }
    for name, (lon, lat) in dagma_stations.items():
        ax.scatter(lon, lat, marker="o", s=30, color="green", zorder=8)
        ax.annotate(name, (lon, lat), textcoords="offset points", xytext=(3, 3),
                    fontsize=6, alpha=0.8)
    # Yumbo industrial
    ax.scatter(-76.5019, 3.5164, marker="s", s=50, color="darkorange", zorder=9,
               label="Acopi-Yumbo")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Fig 5: Mapa de cobertura espacial Sentinel-2\nTiles MGRS + estaciones DAGMA",
                 fontweight="bold")
    ax.legend(loc="lower left", fontsize=7, ncol=2)
    ax.set_xlim(-76.68, -76.32)
    ax.set_ylim(3.22, 3.63)
    ax.grid(alpha=0.3)
    ax.set_aspect("equal")
    return guardar_fig(fig, "05_mapa_cobertura")


# ═══════════════════════════════════════════════════════
# SECCIÓN 3 — ESTADÍSTICAS DE BANDAS (muestreo de píxeles)
# ═══════════════════════════════════════════════════════

def sample_scenes(entries, n=N_SAMPLE_SCENES):
    """Sample N unique scene IDs randomly with fixed seed."""
    scene_ids = list(set(e["scene_id"] for e in entries))
    random.seed(RANDOM_SEED)
    return random.sample(scene_ids, min(n, len(scene_ids)))

def read_band_preview(scene_dir: Path, banda: str, ov_level=OVERVIEW_LEVEL):
    """Read a single band at overview level, return valid pixel values."""
    tif = scene_dir / f"{banda}.tif"
    if not tif.exists():
        return None
    try:
        with rasterio.open(tif) as src:
            if ov_level and src.overviews(1):
                # Use the highest available overview that's >= requested level
                available = [o for o in src.overviews(1) if o <= ov_level]
                if available:
                    level = max(available)
                    data = src.read(1, out_shape=(src.height // level, src.width // level))
                else:
                    data = src.read(1)
            else:
                data = src.read(1)
            # Filter valid: > 0 (nodata) and < practical max (reflectance * 10000)
            valid = data[(data > 0) & (data < 20000)]
            if len(valid) < 100:
                return None
            return valid
    except Exception as e:
        print(f"    ⚠ Error reading {tif}: {e}")
        return None

def read_ndvi(scene_dir: Path, ov_level=OVERVIEW_LEVEL):
    """Compute NDVI = (NIR - Red) / (NIR + Red)."""
    try:
        red_path = scene_dir / "B04.tif"
        nir_path = scene_dir / "B08.tif"
        if not red_path.exists() or not nir_path.exists():
            return None
        with rasterio.open(red_path) as r, rasterio.open(nir_path) as n:
            if ov_level and r.overviews(1) and n.overviews(1):
                level_r = max([o for o in r.overviews(1) if o <= ov_level])
                level_n = max([o for o in n.overviews(1) if o <= ov_level])
                red = r.read(1, out_shape=(r.height // level_r, r.width // level_r)).astype(np.float32)
                nir = n.read(1, out_shape=(n.height // level_n, n.width // level_n)).astype(np.float32)
            else:
                red = r.read(1).astype(np.float32)
                nir = n.read(1).astype(np.float32)
        # Sentinel-2 L2A: reflectance * 10000
        red = red / 10000.0
        nir = nir / 10000.0
        mask = (red > 0) & (red < 1.0) & (nir > 0) & (nir < 1.0)
        ndvi = np.zeros_like(red)
        denom = nir + red
        valid = mask & (denom > 0.001)
        ndvi[valid] = (nir[valid] - red[valid]) / denom[valid]
        ndvi_valid = ndvi[mask & (denom > 0.001)]
        if len(ndvi_valid) < 100:
            return None, None
        return ndvi, ndvi_valid
    except Exception as e:
        return None, None

def compute_band_stats(entries):
    """Sample scenes and compute per-band statistics."""
    scene_ids = sample_scenes(entries)
    # Build scene → dir mapping
    scene_dir_map = {}
    for e in entries:
        sid = e["scene_id"]
        if sid in scene_ids and sid not in scene_dir_map:
            p = Path(e["file"]).parent
            scene_dir_map[sid] = p

    all_bands = {b: [] for b in BANDAS}
    completeness_by_scene = []
    ndvi_values = []
    ndvi_by_month = defaultdict(list)

    for sid in tqdm(scene_dir_map, desc="Muestreando escenas"):
        scene_dir = scene_dir_map[sid]
        dt = parse_scene_date(sid)
        month_key = dt.strftime("%Y-%m") if dt else None
        pixel_counts = []
        for banda in BANDAS:
            vals = read_band_preview(scene_dir, banda)
            if vals is not None:
                all_bands[banda].append(vals)
                pixel_counts.append(len(vals))
        if pixel_counts:
            total = np.sum(pixel_counts)
            max_pix = max(pixel_counts) if pixel_counts else 1
            # Approximate completeness: fraction of max
            completeness_by_scene.append({
                "scene_id": sid,
                "date": dt,
                "total_valid_pixels": total,
                "fraccion_vs_max": np.mean(pixel_counts) / max_pix if max_pix > 0 else 0,
            })
        ndvi_array, ndvi_valid = read_ndvi(scene_dir)
        if ndvi_valid is not None and len(ndvi_valid) > 0:
            ndvi_values.append(ndvi_valid)
            if month_key:
                ndvi_by_month[month_key].append(ndvi_valid)

    return all_bands, completeness_by_scene, ndvi_values, ndvi_by_month


def plot_boxplot_bandas(all_bands):
    """Fig 6: Boxplots de reflectancia por banda."""
    fig, ax = plt.subplots(figsize=(13, 6))
    data_to_plot = []
    positions = []
    labels = []
    for i, b in enumerate(BANDAS):
        if all_bands[b]:
            vals = np.concatenate([v / 10000.0 for v in all_bands[b]], axis=0)
            # Sub-sample to keep it manageable
            if len(vals) > 50000:
                vals = np.random.choice(vals, 50000, replace=False)
            data_to_plot.append(vals)
            positions.append(i + 1)
            labels.append(f"{b}\n({BANDA_RES[b]})")

    bp = ax.boxplot(data_to_plot, positions=positions, widths=0.6, patch_artist=True,
                    showfliers=False, medianprops={"color": "black", "linewidth": 1.5})
    for i, box in enumerate(bp["boxes"]):
        box.set_facecolor(COLORS[i])
        box.set_alpha(0.7)
    # Add mean points
    for i, vals in enumerate(data_to_plot):
        ax.scatter(positions[i], np.mean(vals), marker="D", color="darkred", s=30, zorder=10)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Reflectancia de superficie (×1)")
    ax.set_title("Fig 6: Distribución de reflectancia por banda Sentinel-2\n(boxplots con mediana + media ♦)",
                 fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    return guardar_fig(fig, "06_boxplot_bandas")


def plot_histogramas_bandas(all_bands):
    """Fig 7: Histogramas de reflectancia por banda."""
    n_bands = len([b for b in BANDAS if all_bands[b]])
    cols = 5
    rows = (n_bands + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(16, 3.5 * rows))
    axes = axes.flatten() if n_bands > 1 else [axes]
    for i, b in enumerate(BANDAS):
        ax = axes[i]
        if all_bands[b]:
            vals = np.concatenate([v / 10000.0 for v in all_bands[b]], axis=0)
            # Focus on 1st–99th percentile
            lo, hi = np.percentile(vals, [1, 99])
            ax.hist(np.clip(vals, lo, hi), bins=80, color=COLORS[i], alpha=0.7,
                    edgecolor="white", linewidth=0.3)
            ax.axvline(np.median(vals), color="darkred", linestyle="--", linewidth=1.2)
            ax.axvline(np.mean(vals), color="darkblue", linestyle=":", linewidth=1.2)
        ax.set_title(f"{b} ({BANDA_RES[b]})", fontsize=10)
        ax.set_xlabel("Reflectancia")
        ax.set_ylabel("Frecuencia")
    # Hide unused axes
    for j in range(i+1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Fig 7: Histogramas de reflectancia por banda (muestra de {} escenas)".format(
        len([v for v in all_bands[list(all_bands.keys())[0]] if v is not None])),
        fontweight="bold", y=1.02)
    plt.tight_layout()
    return guardar_fig(fig, "07_histogramas_bandas")


def plot_correlation_matrix(all_bands):
    """Fig 8: Matriz de correlación de Pearson entre bandas."""
    # Build a 2D array: sample medians per scene per band
    n_scenes = min(len(v) for v in all_bands.values() if v)
    if n_scenes == 0:
        print("  ⚠ No hay datos para matriz de correlación")
        return None
    data = np.zeros((n_scenes, len(BANDAS)))
    valid_mask = np.ones(n_scenes, dtype=bool)
    for bi, b in enumerate(BANDAS):
        for si, vals in enumerate(all_bands[b][:n_scenes]):
            if vals is not None and len(vals) > 0:
                data[si, bi] = np.median(vals) / 10000.0
            else:
                valid_mask[si] = False
    data = data[valid_mask]

    corr = np.corrcoef(data.T)
    fig, ax = plt.subplots(figsize=(9, 7))
    mask_upper = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                vmin=-1, vmax=1, xticklabels=BANDAS, yticklabels=BANDAS,
                mask=mask_upper, linewidths=0.5, square=True,
                cbar_kws={"label": "Pearson r", "shrink": 0.8}, ax=ax)
    ax.set_title("Fig 8: Matriz de correlación entre bandas Sentinel-2\n(reflectancia mediana por escena)",
                 fontweight="bold")
    return guardar_fig(fig, "08_correlacion_bandas")


# ═══════════════════════════════════════════════════════
# SECCIÓN 4 — NDVI
# ═══════════════════════════════════════════════════════

def plot_ndvi_histogram(ndvi_values):
    """Fig 9: Histograma NDVI global."""
    if not ndvi_values:
        return None
    all_ndvi = np.concatenate(ndvi_values)
    # Filter to [-1, 1]
    all_ndvi = all_ndvi[(all_ndvi > -1) & (all_ndvi < 1)]
    if len(all_ndvi) < 100:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.hist(all_ndvi, bins=100, color="green", alpha=0.7, edgecolor="white")
    ax1.axvline(0, color="gray", linestyle="--", label="NDVI=0 (límite vegetación)")
    ax1.axvline(np.median(all_ndvi), color="darkred", linestyle="-", linewidth=2,
                label=f"Mediana={np.median(all_ndvi):.3f}")
    ax1.set_xlabel("NDVI")
    ax1.set_ylabel("Frecuencia (píxeles)")
    ax1.set_title("Distribución global NDVI", fontweight="bold")
    ax1.legend(fontsize=8)

    # Categorías NDVI
    categories = {
        "Agua / Nubes (NDVI<0)": np.sum(all_ndvi < 0),
        "Suelo desnudo (0–0.2)": np.sum((all_ndvi >= 0) & (all_ndvi < 0.2)),
        "Vegetación baja (0.2–0.5)": np.sum((all_ndvi >= 0.2) & (all_ndvi < 0.5)),
        "Vegetación densa (0.5–0.8)": np.sum((all_ndvi >= 0.5) & (all_ndvi < 0.8)),
        "Vegetación muy densa (>0.8)": np.sum(all_ndvi >= 0.8),
    }
    cat_names = list(categories.keys())
    cat_vals = list(categories.values())
    colors_pie = ["#42A5F5", "#FFCA28", "#66BB6A", "#2E7D32", "#1B5E20"]
    ax2.pie(cat_vals, labels=cat_names, autopct="%1.1f%%", colors=colors_pie,
            textprops={"fontsize": 7})
    ax2.set_title("Categorías NDVI", fontweight="bold")
    fig.suptitle("Fig 9: Índice de Vegetación (NDVI) — área metropolitana Cali",
                 fontweight="bold")
    return guardar_fig(fig, "09_ndvi_histograma")


def plot_ndvi_time_series(ndvi_by_month):
    """Fig 10: Serie temporal NDVI mediano mensual."""
    if not ndvi_by_month:
        return None
    months = sorted(ndvi_by_month.keys())
    medians = []
    p25 = []
    p75 = []
    for m in months:
        vals = np.concatenate([v for v in ndvi_by_month[m]])
        vals = vals[(vals > -1) & (vals < 1)]
        medians.append(np.median(vals))
        p25.append(np.percentile(vals, 25))
        p75.append(np.percentile(vals, 75))

    fig, ax = plt.subplots(figsize=(14, 5))
    x = range(len(months))
    ax.fill_between(x, p25, p75, alpha=0.3, color="green", label="P25–P75")
    ax.plot(x, medians, "o-", color="darkgreen", linewidth=2, markersize=5, label="Mediana")
    # Anotar tendencia
    z = np.polyfit(x, medians, 1)
    trend = np.poly1d(z)
    ax.plot(x, trend(x), "--", color="darkred", linewidth=1.5, alpha=0.7,
            label=f"Tendencia (slope={z[0]:.5f}/mes)")
    # Every 3rd month label
    tick_positions = x[::3]
    tick_labels = [months[i] for i in range(0, len(months), 3)]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Mes")
    ax.set_ylabel("NDVI")
    ax.set_title("Fig 10: Serie temporal NDVI — mediana mensual\n(área metropolitana Cali, 2020–2024)",
                 fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_ylim(-0.1, 1.0)
    return guardar_fig(fig, "10_ndvi_serie_temporal")


# ═══════════════════════════════════════════════════════
# SECCIÓN 5 — COMPLETITUD DE PÍXELES
# ═══════════════════════════════════════════════════════

def plot_completitud(completeness_by_scene):
    """Fig 11: Completitud de píxeles por escena."""
    if not completeness_by_scene:
        return None
    df = pd.DataFrame(completeness_by_scene)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    # Histogram of completeness fraction
    ax1.hist(df["fraccion_vs_max"], bins=30, color="#42A5F5", edgecolor="white", alpha=0.8)
    ax1.axvline(np.median(df["fraccion_vs_max"]), color="darkred", linestyle="--",
                label=f"Mediana={np.median(df['fraccion_vs_max']):.2f}")
    ax1.set_xlabel("Fracción de completitud (vs. banda más completa)")
    ax1.set_ylabel("Frecuencia (escenas)")
    ax1.set_title("Completitud relativa por escena", fontweight="bold")
    ax1.legend()

    # Total valid pixels per scene
    df_sorted = df.sort_values("date")
    ax2.bar(range(len(df_sorted)), df_sorted["total_valid_pixels"] / 1e6, color="#66BB6A",
            alpha=0.7, width=1.0)
    ax2.set_xlabel("Escenas ordenadas por fecha")
    ax2.set_ylabel("Millones de píxeles válidos")
    ax2.set_title("Píxeles válidos totales por escena", fontweight="bold")
    fig.suptitle("Fig 11: Completitud de píxeles Sentinel-2", fontweight="bold")
    plt.tight_layout()
    return guardar_fig(fig, "11_completitud_pixeles")


# ═══════════════════════════════════════════════════════
# SECCIÓN 6 — RESUMEN ESTADÍSTICO
# ═══════════════════════════════════════════════════════

def tabla_resumen(all_bands):
    """Fig 12: Tabla de estadísticas descriptivas."""
    stats_list = []
    for b in BANDAS:
        if all_bands[b]:
            vals = np.concatenate([v / 10000.0 for v in all_bands[b]], axis=0)
            stats_list.append({
                "Banda": f"{b} ({BANDA_RES[b]})",
                "Descripción": BANDA_LABELS.get(b, ""),
                "N píxeles": len(vals),
                "Media": np.mean(vals),
                "Mediana": np.median(vals),
                "Std": np.std(vals),
                "P1": np.percentile(vals, 1),
                "P99": np.percentile(vals, 99),
                "CV": np.std(vals) / (np.mean(vals) + 1e-10),
            })
    df = pd.DataFrame(stats_list)
    return df


def plot_stacked_bar_tile_heatmap(entries):
    """Fig extra: cómo se distribuyen los tiles por año."""
    year_tile = defaultdict(lambda: defaultdict(int))
    for e in entries:
        dt = parse_scene_date(e["scene_id"])
        tile = parse_tile(e["scene_id"])
        if dt and tile in ("18NUJ", "18NUK"):
            year_tile[dt.year][tile] += 1

    years = sorted(year_tile.keys())
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(years))
    width = 0.35
    nu18j = [year_tile[y].get("18NUJ", 0) for y in years]
    nu18k = [year_tile[y].get("18NUK", 0) for y in years]
    ax.bar(x - width/2, nu18j, width, label="18NUJ (Cali)",
           color="#1E88E5", alpha=0.8, edgecolor="white")
    ax.bar(x + width/2, nu18k, width, label="18NUK (Yumbo)",
           color="#FFC107", alpha=0.8, edgecolor="white")
    for i, (v1, v2) in enumerate(zip(nu18j, nu18k)):
        total = v1 + v2
        ax.text(i, total + 1, str(total), ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_xlabel("Año")
    ax.set_ylabel("Escenas")
    ax.set_title("Fig 12: Escenas por año y tile (18NUJ vs 18NUK)", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    return guardar_fig(fig, "12_escenas_por_tile_ano")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("GeoVision-CLIP Cali — EDA Sentinel-2 L2A")
    print("=" * 70)

    # ── Load ──
    manifest = load_manifest()
    entries = manifest["archivos"]
    print(f"\nManifest: {len(entries)} archivos ({manifest['total_gb']} GB)")
    escenas = list(set(e["scene_id"] for e in entries))
    print(f"Escenas únicas: {len(escenas)}")
    print(f"Periodo: {manifest['periodo']}")

    # ── Phase 1: Temporal analysis (no GeoTIFF reading) ──
    print("\n[Fase 1/5] Análisis temporal...")
    plot_escenas_por_ano(entries)
    print("  ✓ Fig 1: Escenas por año")
    plot_escenas_por_mes(entries)
    print("  ✓ Fig 2: Escenas por mes")
    plot_heatmap_temporal(entries)
    print("  ✓ Fig 3: Heatmap temporal")

    # ── Phase 2: Spatial coverage ──
    print("\n[Fase 2/5] Cobertura espacial...")
    plot_pie_tiles(entries)
    print("  ✓ Fig 4: Tiles y satélites")
    plot_mapa_cobertura(entries)
    print("  ✓ Fig 5: Mapa de cobertura")

    # ── Phase 3: Band statistics (sample GeoTIFFs) ──
    print(f"\n[Fase 3/5] Estadísticas de bandas (muestreando {N_SAMPLE_SCENES} escenas)...")
    all_bands, completeness, ndvi_vals, ndvi_monthly = compute_band_stats(entries)
    print(f"  Escenas muestreadas: {len([v for v in all_bands['B04'] if v is not None])}")
    total_pixels = sum(len(v) for b in BANDAS for v in all_bands[b] if v is not None)
    print(f"  Píxeles analizados: {total_pixels:,}")

    plot_boxplot_bandas(all_bands)
    print("  ✓ Fig 6: Boxplot de bandas")
    plot_histogramas_bandas(all_bands)
    print("  ✓ Fig 7: Histogramas por banda")
    corr_path = plot_correlation_matrix(all_bands)
    if corr_path:
        print("  ✓ Fig 8: Matriz de correlación")

    # ── Phase 4: NDVI ──
    print("\n[Fase 4/5] Índices espectrales (NDVI)...")
    ndvi_hist_path = plot_ndvi_histogram(ndvi_vals)
    if ndvi_hist_path:
        print("  ✓ Fig 9: Histograma NDVI")
    ndvi_ts_path = plot_ndvi_time_series(ndvi_monthly)
    if ndvi_ts_path:
        print("  ✓ Fig 10: Serie temporal NDVI")

    # ── Phase 5: Completeness & summary ──
    print("\n[Fase 5/5] Completitud y resumen...")
    comp_path = plot_completitud(completeness)
    if comp_path:
        print("  ✓ Fig 11: Completitud de píxeles")
    plot_stacked_bar_tile_heatmap(entries)
    print("  ✓ Fig 12: Escenas por tile y año")

    # ── Stats table ──
    df_stats = tabla_resumen(all_bands)
    df_stats.to_csv(OUT_DIR / "estadisticas_bandas.csv", index=False)
    print("\n  ✓ Tabla de estadísticas → eda/sentinel2/estadisticas_bandas.csv")

    # ── Report TXT ──
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("GeoVision-CLIP Cali — EDA Sentinel-2 L2A")
    report_lines.append("=" * 70)
    report_lines.append("")
    report_lines.append(f"Datos: {len(entries)} archivos · {manifest['total_gb']} GB · {len(escenas)} escenas")
    report_lines.append(f"Periodo: {manifest['periodo']}")
    report_lines.append(f"Bbox: {manifest['bbox']}")
    report_lines.append(f"Escenas muestreadas: {N_SAMPLE_SCENES}")
    report_lines.append(f"Píxeles analizados: {total_pixels:,}")
    report_lines.append("")
    report_lines.append("─ Estadísticas descriptivas ─")
    report_lines.append(df_stats.to_string(index=False))
    report_lines.append("")
    report_lines.append("─ Completitud ─")
    report_lines.append(f"  Escenas con datos de completitud: {len(completeness)}")
    if completeness:
        fracs = [c["fraccion_vs_max"] for c in completeness]
        report_lines.append(f"  Mediana completitud: {np.median(fracs):.2f}")
        report_lines.append(f"  P25 completitud: {np.percentile(fracs, 25):.2f}")
    report_lines.append("")
    report_lines.append("─ Resumen temporal ─")
    for y in range(2020, 2025):
        scenes_y = set(e["scene_id"] for e in entries if parse_scene_date(e["scene_id"]) and parse_scene_date(e["scene_id"]).year == y)
        report_lines.append(f"  {y}: {len(scenes_y)} escenas únicas (×10 bandas = {len(scenes_y)*10} archivos)")
    # Per month summary
    meses_totales = Counter()
    for e in entries:
        dt = parse_scene_date(e["scene_id"])
        if dt:
            meses_totales[(dt.year, dt.month)] += 1
    report_lines.append("")
    report_lines.append("  Distribución mensual (escenas únicas por año-mes):")
    for y in range(2020, 2025):
        row = "    " + str(y) + ": "
        row += " ".join(f"{meses_totales[(y,m)]//10:2d}" for m in range(1,13))
        report_lines.append(row)

    report_path = OUT_DIR / "reporte_eda.txt"
    report_path.write_text("\n".join(report_lines))
    print(f"  ✓ Reporte → eda/sentinel2/reporte_eda.txt")

    # ── Final ──
    print("\n" + "=" * 70)
    print("EDA COMPLETO")
    print(f"  Gráficas: {len(list(OUT_DIR.glob('*.png')))} PNGs")
    print(f"  CSV: estadisticas_bandas.csv")
    print(f"  Reporte: reporte_eda.txt")
    print(f"  Directorio: {OUT_DIR}")

    # Delete old outputs from legacy location if any
    legacy = ROOT / "eda" / "sentinel2"
    if legacy.exists():
        import shutil
        shutil.rmtree(legacy)
        print(f"  Limpiado directorio legacy: {legacy}")

    # ── Recomendaciones ──
    print("\n[RECOMENDACIONES — funciones NO pertenecientes al EDA]")
    print("  · Conversión a Zarr: script para empaquetar los 277 GB S2 en arrays")
    print("    N-dimensionales con chunking (año, tile, banda, y, x)")
    print("  · Alineamiento S2↔S5P: reproyectar S2 a la grilla de S5P (1.1 km)")
    print("    para entrenar ConvLSTM")
    print("  · Generación de tiles 64×64: recortar S2 en parches para CLIP multimodal")
    print("  · Cálculo de índices avanzados: NDBI, NDWI, BSI, NBR para detección de")
    print("    urbanización y quemas de caña")
    print("  · Filtro de nubes QA60: verificar banda de calidad para filtrar cirrus")
    print("    (actualmente solo se filtró por <60% de nubosidad en STAC)")
    print("  · Descarga 2025–2026: extender la ventana temporal si se necesitan")
    print("    datos más recientes")

if __name__ == "__main__":
    main()
