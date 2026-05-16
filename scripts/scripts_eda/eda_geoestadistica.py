#!/usr/bin/env python3
"""
EDA Geoestadístico — ST-Kriging, Moran's I, Semivariogramas (≥5 visualizaciones)
================================================================================
• Índice de Moran global + LISA
• Semivariograma omnidireccional
• Semivariograma direccional (anisotropía)
• Mapa de interpolación IDW
• Matriz distancia×correlación
"""

import json, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist, squareform
from scipy import stats
import seaborn as sns
import rasterio

ROOT = Path(__file__).resolve().parent.parent.parent
S5P_L3_DIR = ROOT / "data" / "sentinel5p" / "l3"
DAGMA_CSV_DIR = ROOT / "data" / "dagma" / "raw"
OUT_DIR = ROOT / "outputs" / "eda" / "geoestadistica"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DPI, w = 150, lambda: None; warnings.filterwarnings("ignore")

GRID_BBOX = (-77.00, 5.00, -75.79, 2.99)
CALI_BOUNDS = (-76.60, 3.30, -76.40, 3.55)

def lonlat_to_pixel(lon, lat):
    return (int(round((GRID_BBOX[1]-lat)/0.01)), int(round((lon-GRID_BBOX[0])/0.01)))

def save(name):
    p = OUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white"); plt.close(); return p

# ── Cargar DAGMA ground truth ──
print("Cargando DAGMA...")
dfs = []
for f in sorted(DAGMA_CSV_DIR.glob("g4t8_*.csv")):
    for c in pd.read_csv(f, usecols=["nombre_est","msfl_code","med_concentracion_estandar",
        "med_fecha_inicio","latitud","longitud"], chunksize=50000, encoding="utf-8", on_bad_lines="skip"):
        c["fecha"] = pd.to_datetime(c["med_fecha_inicio"], errors="coerce"); c["valor"] = pd.to_numeric(c["med_concentracion_estandar"], errors="coerce")
        c = c.dropna(subset=["fecha","valor"]); dfs.append(c[["nombre_est","msfl_code","valor","fecha","latitud","longitud"]])
dagma = pd.concat(dfs, ignore_index=True)
dagma["fecha_dia"] = dagma["fecha"].dt.date

# ── Cargar S5P NO2 espacial ──
print("Calculando NO2 promedio multianual desde S5P...")
no2_sum = np.zeros((201,121)); no2_cnt = np.zeros((201,121))
processed = 0
for yd in sorted(S5P_L3_DIR.iterdir()):
    if not yd.is_dir(): continue
    for md in sorted(yd.iterdir()):
        if not md.is_dir(): continue
        for dd in sorted(md.iterdir()):
            if not dd.is_dir(): continue
            no2_file = dd / "NO2.tif"
            cloud_file = dd / "CLOUD.tif"
            if not no2_file.exists() or not cloud_file.exists(): continue
            try:
                with rasterio.open(cloud_file) as src: cloud = src.read(1).astype(np.float32)
                with rasterio.open(no2_file) as src: no2 = src.read(1).astype(np.float32)
                mask = (cloud <= 0.3) & (no2 > 0) & (no2 < 0.01)
                no2_sum[mask] += no2[mask]; no2_cnt[mask] += 1
                processed += 1
                if processed % 2000 == 0: print(f"  {processed} fechas...")
            except: pass

no2_mean = np.full((201,121), np.nan)
valid = no2_cnt > 0; no2_mean[valid] = no2_sum[valid] / no2_cnt[valid] * 1e6
print(f"  {processed} fechas procesadas, {valid.sum():,} píxeles válidos")

# ── Extraer NO2 en estaciones DAGMA ──
print("Extrayendo NO2 S5P en estaciones DAGMA...")
stations_no2 = dagma[(dagma["msfl_code"]=="NO2") & dagma["valor"]>0]
station_means = stations_no2.groupby(["nombre_est","latitud","longitud"])["valor"].mean().reset_index()
station_means = station_means.rename(columns={"valor":"dagma_no2_mean"})
# Add S5P NO2 at each station
s5p_vals = []
for _, r in station_means.iterrows():
    row, col = lonlat_to_pixel(r["longitud"], r["latitud"])
    if 0 <= row < 201 and 0 <= col < 121:
        s5p_vals.append(no2_mean[row, col])
    else:
        s5p_vals.append(np.nan)
station_means["s5p_no2"] = s5p_vals
station_means = station_means.dropna(subset=["s5p_no2"])
print(f"  {len(station_means)} estaciones con NO2 S5P+DAGMA")

coords = station_means[["longitud","latitud"]].values
values = station_means["dagma_no2_mean"].values
n = len(values)

# ── Spatial weight matrix (común a Moran, LISA) ──
w = 1 / (pdist(coords) + 1e-6)
dist_mat = squareform(w)
np.fill_diagonal(dist_mat, 0)

# ═══ 1. Índice de Moran global ═══
if n >= 5:
    row_sum = dist_mat.sum(axis=1)
    w_row_std = dist_mat / (row_sum[:, None] + 1e-10)

    y = values - values.mean()
    sy2 = np.sum(y**2)
    moran_i = (n / sy2) * np.sum(w_row_std * y[:, None] * y[None, :])
    ei = -1/(n-1)

    # Bootstrap test
    np.random.seed(42)
    perm_i = []
    for _ in range(1000):
        yp = np.random.permutation(y)
        perm_i.append((n/(yp**2).sum()) * np.sum(w_row_std * yp[:,None] * yp[None,:]))
    p_val = (np.sum(np.abs(perm_i) >= np.abs(moran_i)) + 1) / 1001

    fig, ax = plt.subplots(figsize=(10,5))
    ax.hist(perm_i, bins=30, color="steelblue", edgecolor="white", alpha=0.7)
    ax.axvline(moran_i, color="red", lw=2, label=f"Moran's I = {moran_i:.3f}")
    ax.axvline(ei, color="gray", ls="--", label=f"E[I] = {ei:.3f}")
    ax.set_xlabel("Moran's I"); ax.set_ylabel("Frecuencia (1000 permutaciones)")
    ax.set_title(f"Fig 1: Índice de Moran global — NO₂ estaciones DAGMA\np = {p_val:.4f} {'(significativo)' if p_val < 0.05 else '(no significativo)'}", fontweight="bold")
    ax.legend(); save("01_moran_global")

# ═══ 2. Semivariograma omnidireccional ═══
if n >= 5:
    dists = squareform(pdist(coords))
    diffs = squareform(pdist(values.reshape(-1,1))**2)
    max_dist = np.percentile(dists[dists>0], 80)
    bins = np.linspace(0, max_dist, 20)
    gamma = []; bin_centers = []
    for i in range(len(bins)-1):
        mask = (dists > bins[i]) & (dists <= bins[i+1])
        if mask.sum() >= 3:
            gamma.append(diffs[mask].mean()/2)
            bin_centers.append((bins[i]+bins[i+1])/2)

    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(bin_centers, gamma, "o-", color="darkgreen", lw=2, markersize=8, label="Semivariograma empírico")
    # Ajustar modelo esférico
    def spherical(h, sill, range_val, nugget):
        return nugget + sill * (1.5*(h/range_val) - 0.5*(h/range_val)**3) * (h <= range_val) + sill * (h > range_val)
    bc, gm = np.array(bin_centers), np.array(gamma)
    try:
        from scipy.optimize import curve_fit
        popt, _ = curve_fit(lambda h, s, r, n: spherical(h, s, r, n), bc, gm,
                            p0=[max(gm), max(bc)*0.5, 0], bounds=([0,0,0],[max(gm)*2, max(bc)*2, max(gm)]))
        h_fit = np.linspace(0, max_dist, 100)
        ax.plot(h_fit, spherical(h_fit, *popt), "r-", lw=2, 
                label=f"Esférico: sill={popt[0]:.1f}, range={popt[1]:.3f}°, nugget={popt[2]:.1f}")
        ax.axhline(popt[0]+popt[2], color="red", ls=":", alpha=0.5)
        ax.axhline(popt[2], color="gray", ls=":", alpha=0.5, label=f"Nugget={popt[2]:.1f}")
    except: pass
    ax.set_xlabel("Distancia [grados]"); ax.set_ylabel("Semivarianza γ(h)")
    ax.set_title("Fig 2: Semivariograma omnidireccional NO₂", fontweight="bold")
    ax.legend(fontsize=8); ax.grid(alpha=0.3); save("02_semivariograma")

# ═══ 3. Semivariograma direccional ═══
if n >= 8:
    fig, ax = plt.subplots(figsize=(10,5))
    directions = [(0, "N-S (0°)"), (45, "NE-SW (45°)"), (90, "E-W (90°)"), (135, "NW-SE (135°)")]
    colors = ["blue","green","red","orange"]
    for (angle, label), col in zip(directions, colors):
        # Project distances onto direction
        dx = coords[:,0][:,None] - coords[:,0][None,:]
        dy = coords[:,1][:,None] - coords[:,1][None,:]
        direction_angle = np.arctan2(dy, dx) * 180/np.pi
        tolerance = 22.5
        d_mask = (np.abs(direction_angle - angle) < tolerance) | (np.abs(direction_angle - angle - 180) < tolerance) | (np.abs(direction_angle - angle + 180) < tolerance)
        dir_dists = dists[d_mask & (dists > 0)]
        dir_diffs = diffs[d_mask & (dists > 0)]
        if len(dir_dists) < 10: continue

        max_d = np.percentile(dir_dists, 90)
        b = np.linspace(0, max_d, 12)
        g_vals = []
        for j in range(len(b)-1):
            mask2 = (dir_dists > b[j]) & (dir_dists <= b[j+1])
            if mask2.sum() >= 2:
                g_vals.append(dir_diffs[mask2].mean()/2)
            else:
                g_vals.append(np.nan)
        bc_b = (b[:-1]+b[1:])/2
        ax.plot(bc_b, g_vals, "o-", lw=1.5, color=col, label=label, markersize=5)
    ax.set_xlabel("Distancia [grados]"); ax.set_ylabel("Semivarianza")
    ax.set_title("Fig 3: Semivariograma direccional NO₂", fontweight="bold")
    ax.legend(fontsize=7); ax.grid(alpha=0.3); save("03_semivariograma_direccional")

# ═══ 4. Mapa IDW ═══
# Cali bbox in pixel coordinates
cali_left, cali_right = -76.60, -76.40
cali_bot, cali_top = 3.30, 3.55
cs = int(round((cali_left - GRID_BBOX[0]) / 0.01))
ce = int(round((cali_right - GRID_BBOX[0]) / 0.01))
rs = int(round((GRID_BBOX[1] - cali_top) / 0.01))
re = int(round((GRID_BBOX[1] - cali_bot) / 0.01))
cs, ce = min(cs,ce), max(cs,ce)
rs, re = min(rs,re), max(rs,re)
cali_data = no2_mean[rs:re, cs:ce]
cali_lons = np.linspace(-76.60, -76.40, ce-cs)
cali_lats = np.linspace(3.30, 3.55, re-rs)
lon_g, lat_g = np.meshgrid(cali_lons, cali_lats)

fig, ax = plt.subplots(figsize=(10,8))
vmin, vmax = np.nanpercentile(cali_data, 2), np.nanpercentile(cali_data, 98)
im = ax.pcolormesh(lon_g, lat_g, cali_data, cmap="YlOrRd", shading="auto", vmin=vmin, vmax=vmax)
# Agregar estaciones
for _, r in station_means.iterrows():
    ax.scatter(r["longitud"], r["latitud"], c="green", s=80, marker="^", edgecolors="white", zorder=10)
    ax.annotate(f'{r["nombre_est"][:10]}\n{r["dagma_no2_mean"]:.1f}', (r["longitud"], r["latitud"]),
                fontsize=6, ha="center", va="bottom")
plt.colorbar(im, ax=ax, label="NO₂ [µmol/m²]", shrink=0.8)
ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
ax.set_title("Fig 4: NO₂ S5P + estaciones DAGMA (promedio multianual)", fontweight="bold")
save("04_mapa_idw_s5p_dagma")

# ═══ 5. Matriz distancia×correlación ═══
if n >= 3:
    try:
        corr_mat = np.atleast_2d(np.corrcoef(values))
        if corr_mat.size <= 1: raise ValueError
        dist_km = squareform(pdist(coords)) * 111
        triu = np.triu_indices(min(n, corr_mat.shape[0]), k=1)
        d_vec = dist_km[triu]; c_vec = corr_mat[triu]
        if len(d_vec) < 2: raise ValueError

        fig, ax = plt.subplots(figsize=(8,5))
        ax.scatter(d_vec, c_vec, s=50, c="steelblue", alpha=0.7, edgecolors="white")
        sl, ic, r, p, _ = stats.linregress(d_vec, c_vec)
        xf = np.linspace(d_vec.min(), d_vec.max(), 100)
        ax.plot(xf, sl*xf+ic, "r-", lw=2, label=f"r={r:.3f}, p={p:.4f}")
        ax.axhline(0, color="gray", ls=":"); ax.set_xlabel("Distancia [km]"); ax.set_ylabel("Correlación de Pearson")
        ax.set_title("Fig 5: Correlación entre estaciones vs distancia", fontweight="bold")
        ax.legend(); ax.grid(alpha=0.3); save("05_distancia_correlacion")
    except Exception as e:
        print(f"  Fig 5 skip: {e}")

# ═══ 6. Mapa LISA (simplificado) ═══
if n >= 3:
    lags = np.zeros(n)
    for i in range(n):
        neighbors = dist_mat[i] > 0
        if neighbors.any():
            weights = 1 / (dist_mat[i][neighbors] + 1e-6)
            weights /= weights.sum()
            lags[i] = np.sum(weights * values[neighbors])

    fig, ax = plt.subplots(figsize=(9,7))
    # Quadrantes
    z_vals = (values - values.mean()) / values.std()
    z_lags = (lags - lags.mean()) / lags.std()

    colors = []
    for i in range(n):
        if z_vals[i] >= 0 and z_lags[i] >= 0: colors.append("red")    # high-high
        elif z_vals[i] < 0 and z_lags[i] < 0: colors.append("blue")   # low-low
        elif z_vals[i] >= 0 and z_lags[i] < 0: colors.append("pink")  # high-low
        else: colors.append("lightblue")                              # low-high

    for i, (lon, lat) in enumerate(coords):
        ax.scatter(lon, lat, c=colors[i], s=150, edgecolors="black", linewidth=0.5, zorder=5)
        ax.annotate(station_means.iloc[i]["nombre_est"][:8], (lon, lat), fontsize=6, ha="center")

    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="red",label="High-High"), Patch(color="blue",label="Low-Low"),
                       Patch(color="pink",label="High-Low"), Patch(color="lightblue",label="Low-High")], fontsize=7)
    ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud"); ax.grid(alpha=0.3)
    ax.set_title("Fig 6: Mapa LISA — autocorrelación espacial NO₂", fontweight="bold")
    save("06_mapa_lisa")

print(f"\n✅ EDA Geoestadístico → {OUT_DIR}")
print(f"   {len(list(OUT_DIR.glob('*.png')))} gráficas generadas")
