#!/usr/bin/env python3
"""
EDA MODIS MCD19A2 (MAIAC AOD) — Cali — Basado en metadata
===========================================================
* 1,822 granules HDF-EOS2 · 12.7 GB · 2020-2024 · tile h10v08
* NOTA: Sin lector HDF4 disponible → EDA usa metadata (fechas, tamaños, conteos)
* Las visualizaciones capturan cobertura temporal y características del dataset
"""

import json, warnings
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "modis" / "raw"
MANIFEST_PATH = ROOT / "data" / "manifests" / "manifest_modis_maiac.json"
OUT_DIR = ROOT / "outputs" / "eda" / "modis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DPI = 150
warnings.filterwarnings("ignore")

def save(name):
    p = OUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(); return p

print("Cargando manifiesto MODIS...")
m = json.loads(MANIFEST_PATH.read_text())
granules = m["granules"]
print(f"  Granules: {len(granules)}")
print(f"  Total GB: {m['total_gb']}")
print(f"  Tile: {m['tile']}")

# --- Construir DataFrame de metadata ---
records = []
for g in granules:
    name = g["name"]
    # MCD19A2.A2024001.h10v08.061.PID.hdf
    parts = name.split(".")
    julian = parts[1]
    year, doy = int(julian[1:5]), int(julian[5:8])
    date = pd.Timestamp(year, 1, 1) + pd.Timedelta(days=doy-1)
    fpath = Path(g["file"])
    records.append({
        "date": date, "year": year, "month": date.month, "doy": doy,
        "size_mb": g["bytes"] / 1e6, "name": name,
    })
df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
df["weekday"] = df["date"].dt.dayofweek
df["year_month"] = df["date"].dt.to_period("M")

print(f"  Periodo: {df['date'].min().date()} → {df['date'].max().date()}")
print(f"  Días únicos: {df['date'].nunique()}")
print(f"  Tamaño medio: {df['size_mb'].mean():.1f} MB")

# ═══ 1. Granules por año ═══
cnt = df["year"].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(10,5))
ax.bar(cnt.index.astype(str), cnt.values, color="teal", edgecolor="white")
for x, v in zip(range(len(cnt)), cnt.values):
    ax.text(x, v+2, str(v), ha="center", fontweight="bold", fontsize=11)
ax.set_ylabel("Granules descargados"); ax.grid(axis="y", alpha=0.3)
ax.set_title("Fig 1: Granules MODIS MCD19A2 por año", fontweight="bold")
save("01_granules_por_ano")

# ═══ 2. Granules por mes (apilado) ═══
ym = df.groupby(["year","month"]).size().unstack(fill_value=0)
fig, ax = plt.subplots(figsize=(14,5))
colors = plt.cm.viridis(np.linspace(0.1,0.9, len(ym.index)))
bottom = np.zeros(12)
for yi, y in enumerate(ym.index):
    ax.bar(range(12), ym.loc[y].values, bottom=bottom, label=str(y), color=colors[yi], alpha=0.85)
    bottom += ym.loc[y].values
ax.set_xticks(range(12)); ax.set_xticklabels(["E","F","M","A","M","J","J","A","S","O","N","D"])
ax.set_ylabel("Granules"); ax.legend(title="Año", fontsize=8)
ax.set_title("Fig 2: Granules por mes (apilado por año)", fontweight="bold"); ax.grid(axis="y", alpha=0.3)
save("02_granules_por_mes")

# ═══ 3. Heatmap días con datos ═══
fig, ax = plt.subplots(figsize=(13,4))
sns.heatmap(ym, annot=True, fmt="d", cmap="YlOrRd", ax=ax, cbar_kws={"label":"Granules"})
ax.set_title("Fig 3: Granules por año-mes", fontweight="bold")
ax.set_xlabel("Mes"); ax.set_ylabel("Año")
ax.set_xticklabels(["E","F","M","A","M","J","J","A","S","O","N","D"])
save("03_heatmap_mensual")

# ═══ 4. Días únicos por mes ═══
daily = df.groupby(df["date"].dt.to_period("M"))["date"].nunique()
fig, ax = plt.subplots(figsize=(16,4))
ax.bar(range(len(daily)), daily.values, color="steelblue", edgecolor="white")
ax.set_xticks(range(0,len(daily),6))
ax.set_xticklabels([str(daily.index[i]) for i in range(0,len(daily),6)], rotation=45, fontsize=7)
ax.set_ylabel("Días con datos"); ax.grid(axis="y", alpha=0.3)
ax.set_title("Fig 4: Días únicos con AOD por mes", fontweight="bold")
save("04_dias_unicos_mes")

# ═══ 5. Tamaño de archivo por año ═══
fig, ax = plt.subplots(figsize=(10,5))
for y in sorted(df["year"].unique()):
    dy = df[df["year"]==y]["size_mb"]
    ax.hist(dy, bins=25, alpha=0.5, label=str(y), edgecolor="white")
ax.set_xlabel("Tamaño (MB)"); ax.set_ylabel("Frecuencia"); ax.legend(fontsize=8)
ax.set_title("Fig 5: Distribución de tamaño de archivo por año", fontweight="bold")
save("05_tamano_archivos")

# ═══ 6. Tamaño acumulado ═══
cumsum = df.set_index("date")["size_mb"].cumsum() / 1024
fig, ax = plt.subplots(figsize=(16,4))
ax.fill_between(cumsum.index, cumsum.values, alpha=0.3, color="teal")
ax.plot(cumsum.index, cumsum.values, lw=2, color="teal")
ax.set_ylabel("Tamaño acumulado [GB]"); ax.grid(alpha=0.3)
ax.set_title("Fig 6: Tamaño acumulado de descarga MODIS", fontweight="bold")
save("06_tamano_acumulado")

# ═══ 7. Cobertura por día del año ═══
doy_counts = df.groupby("doy").size()
fig, ax = plt.subplots(figsize=(14,4))
ax.fill_between(doy_counts.index, doy_counts.values, alpha=0.3, color="darkgreen")
ax.plot(doy_counts.index, doy_counts.values, lw=1.5, color="darkgreen")
ax.axhline(doy_counts.mean(), color="red", ls="--", alpha=0.5, label=f"Media={doy_counts.mean():.1f}")
ax.set_xlabel("Día del año"); ax.set_ylabel("Granules (5 años)")
ax.set_title("Fig 7: Cobertura por día del año (2020-2024 combinados)", fontweight="bold")
ax.legend(); ax.grid(alpha=0.3); save("07_cobertura_doy")

# ═══ 8. Días de la semana ═══
wd = df["weekday"].value_counts().sort_index()
dias = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
fig, ax = plt.subplots(figsize=(8,5))
ax.bar([dias[i] for i in wd.index], wd.values, color="teal", edgecolor="white")
for i, v in enumerate(wd.values):
    ax.text(i, v+1, str(v), ha="center", fontweight="bold")
ax.set_ylabel("Granules"); ax.grid(axis="y", alpha=0.3)
ax.set_title("Fig 8: Distribución por día de la semana", fontweight="bold")
save("08_dia_semana")

# ═══ 9. Completitud vs máximo teórico ═══
max_days = {2020:366,2021:365,2022:365,2023:365,2024:366}
pct = {y: df[df["year"]==y]["date"].nunique()/max_days.get(y,365)*100 for y in sorted(df["year"].unique())}
fig, ax = plt.subplots(figsize=(8,5))
ax.bar([str(y) for y in pct], pct.values(), color="darkgreen", edgecolor="white")
for i, (y, v) in enumerate(pct.items()):
    ax.text(i, v+1, f"{v:.1f}%", ha="center", fontweight="bold")
ax.set_ylabel("% días con datos"); ax.set_ylim(0,105)
ax.set_title("Fig 9: Completitud de cobertura temporal", fontweight="bold")
ax.grid(axis="y", alpha=0.3); save("09_completitud")

# ═══ 10. Mapa de calor: disponibilidad por día del año y año ═══
pivot_doy = df.pivot_table(index="doy", columns="year", values="date", aggfunc="count").fillna(0)
fig, ax = plt.subplots(figsize=(10,8))
sns.heatmap(pivot_doy, cmap="YlOrRd", ax=ax, cbar_kws={"label":"Granules"})
ax.set_title("Fig 10: Disponibilidad por día del año × año", fontweight="bold")
ax.set_ylabel("Día del año"); ax.set_xlabel("Año"); save("10_doy_vs_ano")

# ═══ 11. Estadísticas de archivos ═══
fig, ax = plt.subplots(figsize=(9,6))
ax.axis("off")
stats = f"""ESTADÍSTICAS MODIS MCD19A2 — Cali (h10v08)
{'='*45}
Granules totales:        {len(df)}
Días únicos:             {df['date'].nunique()}
Tamaño total:            {m['total_gb']:.2f} GB
Tamaño medio/granule:    {df['size_mb'].mean():.1f} MB
Periodo:                 {df['date'].min().date()} → {df['date'].max().date()}"""
for y in sorted(df["year"].unique()):
    dy = df[df["year"]==y]
    stats += f"\n  {y}: {len(dy)} granules, {dy['date'].nunique()} días"
ax.text(0.05, 0.5, stats, fontsize=11, fontfamily="monospace", va="center", transform=ax.transAxes)
ax.set_title("Fig 11: Resumen estadístico MODIS", fontweight="bold")
save("11_resumen_estadistico")

# ═══ 12. Estructura del dataset ═══
subdirs = defaultdict(int)
for f in DATA_DIR.rglob("*.hdf"):
    y, m = f.parent.parent.name, f.parent.name
    subdirs[f"{y}/{m}"] += 1
fig, ax = plt.subplots(figsize=(16,5))
months_sorted = sorted(subdirs.keys())
ax.bar(months_sorted, [subdirs[k] for k in months_sorted], color="teal", edgecolor="white")
ax.set_xticks(range(len(months_sorted)))
ax.set_xticklabels(months_sorted, rotation=90, fontsize=5)
ax.set_ylabel("Archivos"); ax.set_title("Fig 12: Archivos por carpeta año/mes", fontweight="bold")
ax.grid(axis="y", alpha=0.3); save("12_estructura_carpetas")

print(f"\n✅ EDA MODIS completo → {OUT_DIR}")
print(f"   {len(list(OUT_DIR.glob('*.png')))} gráficas generadas")
print("   NOTA: Solo metadata. Para AOD values se requiere lector HDF4 (pyhdf/gdal)")
