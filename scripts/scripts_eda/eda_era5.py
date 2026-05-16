#!/usr/bin/env python3
"""
EDA ERA5 — Variables Meteorológicas Cali (≥10 visualizaciones)
===============================================================
9 variables: t2m, d2m, u10, v10, tp, sp, blh, stl1, ssr
Formato: NetCDF4/HDF5 horario, 2020-2025
"""

import json, glob, warnings
from pathlib import Path
import numpy as np
import h5py
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "era5"
OUT_DIR = ROOT / "outputs" / "eda" / "era5"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DPI = 150
warnings.filterwarnings("ignore")

VARS = {
    "t2m": "2m Temperature [K]", "d2m": "2m Dewpoint [K]",
    "u10": "U-wind [m/s]", "v10": "V-wind [m/s]",
    "tp": "Total Precip [m]", "sp": "Surface Pressure [Pa]",
    "blh": "Boundary Layer Height [m]", "stl1": "Soil Temp [K]",
    "ssr": "Solar Radiation [J/m²]",
}
VAR_KEYS = {"ssr": "ssrd"}
UNITS = {"t2m":"°C", "tp":"mm", "ssr":"W/m²"}

def save(name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(); return p

def read_file(path, var_short):
    """Lee un NetCDF ERA5 y extrae serie temporal media espacial."""
    try:
        with h5py.File(path, "r") as f:
            vn = VAR_KEYS.get(var_short, var_short)
            if vn not in f: return None, None
            data = f[vn][:]  # (time, lat, lon) o (1, time, lat, lon)
            # Get time
            time_key = "valid_time" if "valid_time" in f else "time"
            time_data = f[time_key][:]
            # Squeeze
            while data.ndim > 2 and data.shape[0] == 1:
                data = data[0]
            # Spatial mean
            if data.ndim == 2:
                mean_ts = np.nanmean(data, axis=(1,))
            else:
                mean_ts = data.flatten()
            return mean_ts, time_data
    except Exception as e:
        return None, None

print("Cargando ERA5 (648 archivos)...")
files = sorted(DATA_DIR.rglob("*.nc"))
print(f"  → {len(files)} archivos")

# ── Acumular series temporales ──
ts_data = {v: {"time": [], "values": []} for v in VARS}

for f in files:
    parts = f.stem.split("_")
    if len(parts) < 5: continue
    var = parts[4] if parts[4] in VARS else parts[-1]
    if var not in VARS:
        for i in [4,5,6]:
            if i < len(parts) and parts[i] in VARS:
                var = parts[i]; break
        else: continue
    mean_ts, time_ts = read_file(f, var)
    if mean_ts is not None and len(mean_ts) > 0 and time_ts is not None:
        # Asegurar misma longitud
        l = min(len(mean_ts.flatten()), len(time_ts.flatten()))
        ts_data[var]["time"].extend(time_ts.flatten()[:l].tolist())
        ts_data[var]["values"].extend(mean_ts.flatten()[:l].tolist())

# ── Construir DataFrames ──
dfs = {}
for var in VARS:
    if ts_data[var]["values"]:
        df = pd.DataFrame({
            "time": pd.to_datetime(ts_data[var]["time"], unit="s", origin="unix"),
            "value": ts_data[var]["values"],
        }).sort_values("time").drop_duplicates("time")
        # Convertir unidades
        val = df["value"].values
        if var == "t2m" or var == "d2m" or var == "stl1":
            val = val - 273.15
        elif var == "tp":
            val = val * 1000
        elif var == "ssr" or var == "ssrd":
            val = val / 3600
        elif var == "sp":
            val = val / 100
        df["value"] = val
        dfs[var] = df

print(f"  Variables cargadas: {len(dfs)}")
for v, df in sorted(dfs.items()):
    print(f"    {v}: {len(df)} puntos, {df['time'].min()} → {df['time'].max()}")

# ═══ 1. Temperatura serie temporal ═══
if "t2m" in dfs:
    d = dfs["t2m"].set_index("time").resample("D").mean().dropna()
    roll = d["value"].rolling(30, center=True, min_periods=5).mean()
    fig, ax = plt.subplots(figsize=(16,5))
    ax.plot(d.index, d["value"], alpha=0.3, lw=0.5, color="darkred")
    ax.plot(d.index, roll, lw=2, color="darkred", label="Media móvil 30d")
    ax.set_ylabel("Temperatura [°C]"); ax.legend()
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Fig 1: Temperatura 2m — serie temporal (2020-2025)", fontweight="bold"); ax.grid(alpha=0.3)
    save("01_temperatura_serie")

# ═══ 2. Precipitación acumulada mensual ═══
if "tp" in dfs:
    d = dfs["tp"].copy(); d["mes"] = d["time"].dt.to_period("M")
    monthly = d.groupby("mes")["value"].sum()
    fig, ax = plt.subplots(figsize=(16,5))
    ax.bar(range(len(monthly)), monthly.values, color="steelblue", edgecolor="white")
    ax.set_xticks(range(0,len(monthly),12)); ax.set_xticklabels([str(monthly.index[i]) for i in range(0,len(monthly),12)], rotation=45)
    ax.set_ylabel("Precipitación [mm/mes]")
    ax.set_title("Fig 2: Precipitación total mensual (2020-2025)", fontweight="bold"); ax.grid(axis="y", alpha=0.3)
    save("02_precipitacion_mensual")

# ═══ 3. Ciclo anual temperatura (boxplots) ═══
if "t2m" in dfs:
    d = dfs["t2m"].copy(); d["mes"] = d["time"].dt.month
    data = [d[d["mes"]==m]["value"].dropna().values for m in range(1,13)]
    fig, ax = plt.subplots(figsize=(12,5))
    bp = ax.boxplot(data, patch_artist=True, showfliers=False)
    for p in bp["boxes"]: p.set_facecolor("darkred"); p.set_alpha(0.6)
    ax.set_xticklabels(["E","F","ME","A","ME","J","J","A","S","O","N","D"])
    ax.set_ylabel("Temperatura [°C]"); ax.grid(axis="y", alpha=0.3)
    ax.set_title("Fig 3: Ciclo anual de temperatura 2m", fontweight="bold")
    save("03_temperatura_ciclo_anual")

# ═══ 4. Ciclo diurno temperatura ═══
if "t2m" in dfs:
    d = dfs["t2m"].copy(); d["hora"] = d["time"].dt.hour
    hourly = d.groupby("hora")["value"].mean()
    fig, ax = plt.subplots(figsize=(10,5))
    ax.fill_between(hourly.index, hourly.values-1, hourly.values+1, alpha=0.2, color="darkred")
    ax.plot(hourly.index, hourly.values, "o-", lw=2, color="darkred")
    ax.set_xlabel("Hora"); ax.set_ylabel("Temperatura [°C]"); ax.set_xticks(range(0,24,3))
    ax.set_title("Fig 4: Ciclo diurno de temperatura", fontweight="bold"); ax.grid(alpha=0.3)
    save("04_temperatura_ciclo_diurno")

# ═══ 5. Viento: rosa ═══
if "u10" in dfs and "v10" in dfs:
    d_u = dfs["u10"].set_index("time").resample("3h").mean().dropna()
    d_v = dfs["v10"].set_index("time").resample("3h").mean().dropna()
    common = d_u.index.intersection(d_v.index)
    wspd = np.sqrt(d_u.loc[common]["value"]**2 + d_v.loc[common]["value"]**2)
    wdir = np.arctan2(d_u.loc[common]["value"], d_v.loc[common]["value"]) * 180/np.pi + 180
    fig, ax = plt.subplots(figsize=(7,7), subplot_kw={'projection':'polar'})
    bins = np.linspace(0, 2*np.pi, 17)
    dir_rad = np.deg2rad(wdir)
    ax.hist(dir_rad, bins=bins, color="steelblue", alpha=0.7, edgecolor="white")
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    ax.set_title("Fig 5: Rosa de vientos (2020-2025)", fontweight="bold")
    save("05_rosa_vientos")

# ═══ 6. Boundary Layer Height ═══
if "blh" in dfs:
    d = dfs["blh"].set_index("time").resample("D").mean().dropna()
    roll = d["value"].rolling(30, center=True, min_periods=5).mean()
    fig, ax = plt.subplots(figsize=(16,5))
    ax.plot(d.index, d["value"], alpha=0.3, lw=0.5, color="purple")
    ax.plot(d.index, roll, lw=2, color="purple")
    ax.set_ylabel("BLH [m]"); ax.set_title("Fig 6: Altura de capa límite (2020-2025)", fontweight="bold"); ax.grid(alpha=0.3)
    save("06_blh_serie")

# ═══ 7. Radiación solar ═══
if "ssr" in dfs:
    d = dfs["ssr"].set_index("time").resample("D").mean().dropna()
    daily = d.groupby(d.index.dayofyear)["value"].mean()
    fig, ax = plt.subplots(figsize=(12,5))
    ax.fill_between(daily.index, daily.values, alpha=0.3, color="orange")
    ax.plot(daily.index, daily.values, lw=1.5, color="darkorange")
    ax.set_xlabel("Día del año"); ax.set_ylabel("Radiación solar [W/m²]")
    ax.set_title("Fig 7: Radiación solar — ciclo anual", fontweight="bold"); ax.grid(alpha=0.3)
    save("07_radiacion_solar")

# ═══ 8. Mapa de calor ═══
if len(dfs) >= 5:
    fig, axes = plt.subplots(2, 4, figsize=(18,9))
    plot_vars = ["t2m","tp","ssr","blh","u10","v10","sp","d2m"]
    for ax, var in zip(axes.flat, plot_vars):
        if var in dfs:
            d = dfs[var].copy(); d["mes"] = d["time"].dt.to_period("M")
            m = d.groupby("mes")["value"].mean()
            ax.plot(range(len(m)), m.values, lw=1.5, color=plt.cm.tab10(plot_vars.index(var)))
            ax.set_title(var, fontsize=10); ax.set_xticks(range(0,len(m),12))
            ax.set_xticklabels([str(m.index[i]) for i in range(0,len(m),12)], rotation=45, fontsize=6)
            ax.grid(alpha=0.3)
    fig.suptitle("Fig 8: Panorama multivariable ERA5", fontweight="bold", fontsize=13)
    fig.tight_layout(); save("08_panorama_multivariable")

# ═══ 9. Comparación temperatura vs precipitación ═══
if "t2m" in dfs and "tp" in dfs:
    d_t = dfs["t2m"].set_index("time").resample("ME").mean()
    d_p = dfs["tp"].copy(); d_p["mes"] = d_p["time"].dt.to_period("M"); d_p = d_p.groupby("mes")["value"].sum()
    common = d_t.index.intersection(pd.to_datetime([str(m) for m in d_p.index]))
    fig, ax1 = plt.subplots(figsize=(16,5))
    ax1.bar(range(len(d_p)), d_p.values/100, color="steelblue", alpha=0.5, label="Precipitación")
    ax1.set_ylabel("Precipitación [mm/100]"); ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(range(len(d_t)), d_t["value"], "r-", lw=1.5, label="Temperatura")
    ax2.set_ylabel("Temperatura [°C]"); ax2.legend(loc="upper right")
    ax1.set_title("Fig 9: Temperatura vs Precipitación mensual", fontweight="bold")
    ax1.set_xticks(range(0,len(d_p),12)); ax1.set_xticklabels([str(d_p.index[i]) for i in range(0,len(d_p),12)], rotation=45)
    save("09_temp_vs_precip")

# ═══ 10. Correlación entre variables ═══
corr_vars = {}
for v in ["t2m","tp","ssr","blh","u10","v10","sp","d2m"]:
    if v in dfs:
        corr_vars[v] = dfs[v].set_index("time")["value"].resample("D").mean().dropna()
if len(corr_vars) >= 4:
    corr_df = pd.DataFrame(corr_vars).corr()
    fig, ax = plt.subplots(figsize=(9,7))
    sns.heatmap(corr_df, annot=True, fmt=".2f", cmap="RdBu_r", center=0, square=True, ax=ax)
    ax.set_title("Fig 10: Matriz de correlación — variables ERA5", fontweight="bold")
    save("10_correlacion_era5")

# ═══ 11. Ciclo diurno por mes ═══
if "t2m" in dfs:
    d = dfs["t2m"].copy(); d["hora"] = d["time"].dt.hour; d["mes"] = d["time"].dt.month
    pivot = d.groupby(["mes","hora"])["value"].mean().unstack()
    fig, ax = plt.subplots(figsize=(14,5))
    im = ax.imshow(pivot.T, aspect="auto", cmap="RdYlBu_r", origin="lower")
    ax.set_xticks(range(12)); ax.set_xticklabels(["E","F","ME","A","ME","J","J","A","S","O","N","D"])
    ax.set_yticks(range(0,24,3)); ax.set_yticklabels(range(0,24,3))
    ax.set_xlabel("Mes"); ax.set_ylabel("Hora")
    plt.colorbar(im, ax=ax, label="°C", shrink=0.8)
    ax.set_title("Fig 11: Temperatura — ciclo diurno × mes", fontweight="bold")
    save("11_temp_diurno_mes")

# ═══ 12. Tendencia anual ═══
if "t2m" in dfs:
    d = dfs["t2m"].copy(); d["ano"] = d["time"].dt.year
    annual = d.groupby("ano")["value"].agg(["mean","std"])
    fig, ax = plt.subplots(figsize=(8,5))
    ax.errorbar(annual.index, annual["mean"], yerr=annual["std"], fmt="o-", lw=2, color="darkred", capsize=5)
    ax.set_xlabel("Año"); ax.set_ylabel("Temperatura [°C]")
    ax.set_title("Fig 12: Temperatura media anual ± σ", fontweight="bold"); ax.grid(alpha=0.3)
    z = np.polyfit(annual.index, annual["mean"], 1)
    ax.plot(annual.index, np.poly1d(z)(annual.index), "--", color="gray", label=f"Tendencia: {z[0]:.3f}°C/año")
    ax.legend(); save("12_tendencia_temperatura")

print(f"\n✅ EDA ERA5 completo → {OUT_DIR}")
print(f"   {len(list(OUT_DIR.glob('*.png')))} gráficas generadas")
