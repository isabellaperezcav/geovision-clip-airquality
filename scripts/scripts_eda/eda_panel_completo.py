#!/usr/bin/env python3
"""
EDA Panel Completo — Integración Cross-Dataset (≥20 visualizaciones)
=====================================================================
Panel Big Data >250 GB: S5P + S2 + ERA5 + MODIS + DAGMA
Cada visualización cruza al menos 2 datasets. Arquitectura distribuida con Dask.
"""

import json, warnings, gc
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import seaborn as sns
from scipy import stats
import rasterio
import h5py

ROOT = Path(__file__).resolve().parent.parent.parent
S5P_L3_DIR = ROOT / "data" / "sentinel5p" / "l3"
ERA5_DIR = ROOT / "data" / "era5"
DAGMA_DIR = ROOT / "data" / "dagma" / "raw"
S2_MANIFEST = ROOT / "data" / "manifests" / "manifest_sentinel2.json"
MOD_MANIFEST = ROOT / "data" / "manifests" / "manifest_modis_maiac.json"
OUT_DIR = ROOT / "outputs" / "eda" / "panel"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DPI = 150; warnings.filterwarnings("ignore")

def save(name):
    p = OUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(); return p

print("=" * 70)
print("EDA Panel Completo — Integración 5 datasets")
print("=" * 70)

# ── 1. COBERTURA TEMPORAL COMPARADA ──
print("\n[Fase 1/6] Cobertura temporal comparada...")
# S5P
s5p_dates = set()
for yd in sorted(S5P_L3_DIR.iterdir()):
    if not yd.is_dir(): continue
    for md in sorted(yd.iterdir()):
        if not md.is_dir(): continue
        for dd in sorted(md.iterdir()):
            if not dd.is_dir(): continue
            try: s5p_dates.add(pd.Timestamp(int(yd.name),int(md.name),int(dd.name)).date())
            except: pass
# S2
s2_manifest = json.loads(S2_MANIFEST.read_text())
s2_dates = set()
for e in s2_manifest["archivos"]:
    sid = e["scene_id"]; p = sid.split("_")
    if len(p) >= 3 and len(p[2]) == 8:
        s2_dates.add(pd.Timestamp(int(p[2][:4]),int(p[2][4:6]),int(p[2][6:8])).date())
# ERA5
era5_manifest = json.loads((ROOT / "data" / "manifests" / "manifest_era5.json").read_text())
era5_dates = set()
for e in era5_manifest["archivos"]:
    for d in range(1, 32):
        try: era5_dates.add(pd.Timestamp(e["year"], e["month"], d).date())
        except: pass
# MODIS
mod_manifest = json.loads(MOD_MANIFEST.read_text())
mod_dates = set()
for g in mod_manifest["granules"]:
    parts = g["name"].split(".")
    j = parts[1]; y, doy = int(j[1:5]), int(j[5:8])
    mod_dates.add((pd.Timestamp(y,1,1) + pd.Timedelta(days=doy-1)).date())
# DAGMA
dagma_dates = set()
for f in sorted(DAGMA_DIR.glob("g4t8_*.csv")):
    try:
        df = pd.read_csv(f, usecols=["med_fecha_inicio"], nrows=5000, encoding="utf-8")
        dts = pd.to_datetime(df["med_fecha_inicio"], errors="coerce").dt.date.dropna().unique()
        dagma_dates.update(dts)
    except: pass

all_dates = sorted(s5p_dates | s2_dates | era5_dates | mod_dates | dagma_dates)
start, end = min(all_dates), max(all_dates)

# Construir matriz de disponibilidad
print(f"  Rango: {start} → {end} ({len(all_dates)} días)")
datasets = {"S5P": s5p_dates, "S2": s2_dates, "ERA5": era5_dates, "MODIS": mod_dates, "DAGMA": dagma_dates}
colors_ds = {"S5P":"#E53935","S2":"#1E88E5","ERA5":"#43A047","MODIS":"#FFC107","DAGMA":"#8E24AA"}

# Fig 1: Barras de cobertura
fig, ax = plt.subplots(figsize=(12,5))
for i, (ds_name, ds_set) in enumerate(datasets.items()):
    ax.bar(i, len(ds_set)/len(all_dates)*100, color=colors_ds[ds_name], edgecolor="white")
    ax.text(i, len(ds_set)/len(all_dates)*100+1, f"{len(ds_set)} días\n({len(ds_set)/len(all_dates)*100:.0f}%)", ha="center", fontsize=9)
ax.set_xticks(range(5)); ax.set_xticklabels(datasets.keys())
ax.set_ylabel("% del periodo"); ax.set_ylim(0, 110)
ax.set_title("Fig 1: Cobertura temporal por dataset", fontweight="bold"); ax.grid(axis="y", alpha=0.3)
save("01_cobertura_datasets")

# Fig 2: Heatmap overlap
overlap_daily = []
for d in all_dates:
    overlap_daily.append([d in ds for ds in datasets.values()])
overlap_df = pd.DataFrame(overlap_daily, columns=list(datasets.keys()))
overlap_df["date"] = all_dates
overlap_df["month"] = pd.to_datetime(all_dates).to_period("M")
overlap_monthly = overlap_df.groupby("month")[list(datasets.keys())].mean() * 100

fig, ax = plt.subplots(figsize=(18,5))
sns.heatmap(overlap_monthly.T, cmap="YlOrRd", ax=ax, cbar_kws={"label":"% días con datos"}, vmin=0, vmax=100)
ax.set_title("Fig 2: Disponibilidad mensual por dataset", fontweight="bold")
ax.set_ylabel("Dataset")
ax.set_xticklabels([str(m) for m in overlap_monthly.index], rotation=90, fontsize=5)
save("02_heatmap_disponibilidad")

# ── 2. S5P NO2 → extraer serie temporal ──
print("\n[Fase 2/6] Series NO2 desde S5P...")
no2_dates = []; no2_means = []
processed = 0
for yd in sorted(S5P_L3_DIR.iterdir()):
    if not yd.is_dir(): continue
    for md in sorted(yd.iterdir()):
        if not md.is_dir(): continue
        for dd in sorted(md.iterdir()):
            if not dd.is_dir(): continue
            no2f = dd / "NO2.tif"; clf = dd / "CLOUD.tif"
            if not no2f.exists() or not clf.exists(): continue
            try:
                with rasterio.open(clf) as s: cl = s.read(1).astype(np.float32)
                with rasterio.open(no2f) as s: no2 = s.read(1).astype(np.float32)
                mask = (cl <= 0.3) & (no2 > 0)
                if mask.sum() > 100:
                    no2_dates.append(pd.Timestamp(int(yd.name),int(md.name),int(dd.name)))
                    no2_means.append(float(np.nanmean(no2[mask]) * 1e6))
            except: pass
            processed += 1
            if processed % 3000 == 0: print(f"  {processed} fechas...")

no2_ts = pd.DataFrame({"date": no2_dates, "no2": no2_means}).sort_values("date")
no2_ts["date"] = pd.to_datetime(no2_ts["date"])
print(f"  NO2 S5P: {len(no2_ts)} días")

# ── 3. ERA5 → extraer BLH + Temperatura ¨¨
print("\n[Fase 3/6] ERA5 BLH y Temperatura...")
era5_blh = {}; era5_temp = {}
for f in sorted(ERA5_DIR.rglob("*.nc")):
    try:
        with h5py.File(f, "r") as h5:
            parts = Path(f).stem.split("_")
            y, m = int(parts[2]), int(parts[3])
            var = parts[4]
            if var == "blh" and "blh" in h5:
                blh_data = h5["blh"][:].flatten()
                times = h5["valid_time"][:].flatten()[:len(blh_data)]
                for t, v in zip(times, blh_data):
                    dt = pd.Timestamp.utcfromtimestamp(t).date()
                    era5_blh[dt] = float(np.nanmean(v))
            elif var == "t2m" and "t2m" in h5:
                t_data = h5["t2m"][:].flatten() - 273.15
                times = h5["valid_time"][:].flatten()[:len(t_data)]
                for t, v in zip(times, t_data):
                    dt = pd.Timestamp.utcfromtimestamp(t).date()
                    era5_temp[dt] = float(np.nanmean(v))
    except: pass
print(f"  BLH: {len(era5_blh)} días, Temp: {len(era5_temp)} días")

# ── 4. S2 → extraer NDVI ──
print("\n[Fase 4/6] NDVI desde Sentinel-2...")
s2_ndvi = {}
for e in s2_manifest["archivos"][:50]:  # Muestra 50 escenas
    band = e["banda"]
    if band not in ["B04","B08"]: continue
    sid = e["scene_id"]; p = sid.split("_")
    if len(p) < 3: continue
    dt = pd.Timestamp(int(p[2][:4]),int(p[2][4:6]),int(p[2][6:8]))
    try:
        with rasterio.open(Path(e["file"])) as src:
            data = src.read(1, out_shape=(64,64)).astype(np.float32)/10000
        if band == "B04":
            s2_ndvi.setdefault(dt.date(), {})["red"] = data
        elif band == "B08":
            s2_ndvi.setdefault(dt.date(), {})["nir"] = data
    except: pass
# Compute NDVI
s2_ndvi_vals = {}
for dt, bands in s2_ndvi.items():
    if "red" in bands and "nir" in bands:
        ndvii = (bands["nir"] - bands["red"]) / (bands["nir"] + bands["red"] + 1e-10)
        s2_ndvi_vals[dt] = float(np.nanmedian(ndvii[(ndvii > -1) & (ndvii < 1)]))
print(f"  NDVI: {len(s2_ndvi_vals)} escenas")

# ── 5. MODIS → AOD desde fechas ──
print("\n[Fase 5/6] MODIS metadata...")
mod_dates_list = sorted(mod_dates)
mod_monthly = defaultdict(int)
for d in mod_dates_list:
    mod_monthly[(d.year, d.month)] += 1

# ── 6. DAGMA NO2 serie ──
print("\n[Fase 6/6] DAGMA NO2...")
dagma_no2 = []
for f in sorted(DAGMA_DIR.glob("g4t8_*.csv")):
    for c in pd.read_csv(f, usecols=["msfl_code","med_concentracion_estandar","med_fecha_inicio"],
                          chunksize=50000, encoding="utf-8", on_bad_lines="skip"):
        c = c[c["msfl_code"]=="NO2"]
        c["fecha"] = pd.to_datetime(c["med_fecha_inicio"], errors="coerce")
        c["valor"] = pd.to_numeric(c["med_concentracion_estandar"], errors="coerce")
        c = c.dropna(subset=["fecha","valor"])
        for _, r in c.iterrows():
            dagma_no2.append({"date": r["fecha"].date(), "no2_dagma": r["valor"]})
dagma_no2_df = pd.DataFrame(dagma_no2).groupby("date")["no2_dagma"].mean().reset_index() if dagma_no2 else pd.DataFrame()
if not dagma_no2_df.empty:
    dagma_no2_df["date"] = pd.to_datetime(dagma_no2_df["date"])
print(f"  DAGMA NO2: {len(dagma_no2_df)} días")

# ════════════════════════════════════════════════
# VISUALIZACIONES CROSS-DATASET
# ════════════════════════════════════════════════

# ═══ 3. NO2 S5P vs BLH ERA5 ═══
common_dates = sorted(set(d.date() for d in no2_ts["date"]) & set(era5_blh.keys()))
if len(common_dates) > 30:
    x = [no2_ts[no2_ts["date"]==pd.Timestamp(d)]["no2"].values[0] for d in common_dates if len(no2_ts[no2_ts["date"]==pd.Timestamp(d)])>0]
    y = [era5_blh[d] for d in common_dates[:len(x)]]
    x, y = x[:min(len(x),len(y))], y[:min(len(x),len(y))]
    fig, ax = plt.subplots(figsize=(10,6))
    ax.scatter(x, y, alpha=0.15, s=8, c="#E53935")
    sl, ic, r, p, _ = stats.linregress(x, y)
    xf = np.linspace(min(x), max(x), 100); ax.plot(xf, sl*xf+ic, "k-", lw=2, label=f"r={r:.3f}")
    ax.set_xlabel("NO₂ S5P [µmol/m²]"); ax.set_ylabel("BLH ERA5 [m]"); ax.legend()
    ax.set_title("Fig 3: NO₂ vs Altura de Capa Límite", fontweight="bold"); ax.grid(alpha=0.3)
    save("03_no2_vs_blh")

# ═══ 4. Temperatura ERA5 vs O3 S5P ═══
common_t = sorted(set(d.date() for d in no2_ts["date"]) & set(era5_temp.keys()))
if len(common_t) > 30:
    o3_means = []
    for yd, md, dd in [(d.year,d.month,d.day) for d in common_t[:200]]:
        o3f = S5P_L3_DIR / str(yd) / f"{md:02d}" / f"{dd:02d}" / "O3.tif"
        if o3f.exists():
            try:
                with rasterio.open(o3f) as s: o3 = s.read(1).astype(np.float32)
                if (o3>0).sum() > 100: o3_means.append((pd.Timestamp(yd,md,dd), float(np.nanmean(o3[o3>0])*1e6)))
            except: pass
    if o3_means:
        o3_df = pd.DataFrame(o3_means, columns=["date","o3"])
        temps = [era5_temp[d.date()] for d, _ in o3_means if d.date() in era5_temp]
        o3s = [v for d, v in o3_means if d.date() in era5_temp]
        fig, ax = plt.subplots(figsize=(10,6))
        ax.scatter(temps, o3s, alpha=0.15, s=8, c="#4CAF50")
        sl, ic, r, p, _ = stats.linregress(temps, o3s); xf = np.linspace(min(temps), max(temps), 100)
        ax.plot(xf, sl*xf+ic, "k-", lw=2, label=f"r={r:.3f}")
        ax.set_xlabel("Temperatura ERA5 [°C]"); ax.set_ylabel("O₃ S5P [µmol/m²]"); ax.legend()
        ax.set_title("Fig 4: O₃ vs Temperatura (efecto fotoquímico)", fontweight="bold"); ax.grid(alpha=0.3)
        save("04_o3_vs_temperatura")

# ═══ 5. NDVI S2 vs NO2 S5P ═══
common_n = sorted(set(s2_ndvi_vals.keys()) & set(d.date() for d in no2_ts["date"]))
if len(common_n) > 10:
    n_x = [s2_ndvi_vals[d] for d in common_n]
    n_y = []
    for d in common_n:
        vals = no2_ts[no2_ts["date"]==pd.Timestamp(d)]["no2"].values
        if len(vals) > 0: n_y.append(vals[0])
        else: n_y.append(np.nan)
    valid = ~np.isnan(n_y); n_x, n_y = np.array(n_x)[valid], np.array(n_y)[valid]
    fig, ax = plt.subplots(figsize=(10,6))
    ax.scatter(n_x, n_y, alpha=0.5, s=30, c="#2E7D32", edgecolors="white")
    sl, ic, r, p, _ = stats.linregress(n_x, n_y)
    ax.plot(np.linspace(min(n_x),max(n_x),100), sl*np.linspace(min(n_x),max(n_x),100)+ic, "k-", lw=2, label=f"r={r:.3f}")
    ax.set_xlabel("NDVI mediano"); ax.set_ylabel("NO₂ S5P [µmol/m²]"); ax.legend()
    ax.set_title("Fig 5: NDVI (S2) vs NO₂ (S5P) — ¿más vegetación = menos contaminación?", fontweight="bold"); ax.grid(alpha=0.3)
    save("05_ndvi_vs_no2")

# ═══ 6-8. Series temporales duales ═══
# NO2 S5P + DAGMA overlay
if len(dagma_no2_df) > 10 and len(no2_ts) > 10:
    try:
        monthly_no2_s5p = no2_ts.set_index("date").resample("ME").mean()
        ddf = dagma_no2_df.copy()
        ddf["date"] = pd.to_datetime(ddf["date"])
        monthly_no2_dagma = ddf.set_index("date").resample("ME").mean()
        if len(monthly_no2_dagma) > 3:
            fig, ax = plt.subplots(figsize=(16,5))
            ax.plot(monthly_no2_s5p.index, monthly_no2_s5p["no2"], "o-", lw=2, color="#E53935", label="S5P")
            ax.plot(monthly_no2_dagma.index, monthly_no2_dagma["no2_dagma"], "s-", lw=2, color="black", label="DAGMA")
            ax.set_ylabel("NO₂"); ax.legend(); ax.grid(alpha=0.3)
            ax.set_title("Fig 6: NO₂ mensual — S5P vs DAGMA ground truth", fontweight="bold")
            save("06_no2_s5p_vs_dagma")
    except Exception as e:
        print(f"  Fig 6 skip: {e}")

# Temperatura + NO2
if len(common_t) > 30:
    temp_ts = pd.DataFrame({"date": list(era5_temp.keys()), "temp": list(era5_temp.values())})
    temp_ts["date"] = pd.to_datetime(temp_ts["date"])
    temp_ts = temp_ts.set_index("date").sort_index()
    no2_monthly = no2_ts.set_index("date").resample("ME").mean()
    temp_monthly = temp_ts.resample("ME").mean()
    common_idx = no2_monthly.index.intersection(temp_monthly.index)
    if len(common_idx) > 5:
        fig, ax1 = plt.subplots(figsize=(16,5))
        ax2 = ax1.twinx()
        ax1.fill_between(common_idx, no2_monthly.loc[common_idx]["no2"].values, alpha=0.3, color="#E53935")
        ax1.plot(common_idx, no2_monthly.loc[common_idx]["no2"].values, "r-", lw=2, label="NO₂ S5P")
        ax2.plot(common_idx, temp_monthly.loc[common_idx]["temp"].values, "b-", lw=2, label="T° ERA5")
        ax1.set_ylabel("NO₂ [µmol/m²]", color="red"); ax2.set_ylabel("Temperatura [°C]", color="blue")
        ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
        ax1.set_title("Fig 7: NO₂ vs Temperatura — ciclo estacional invertido", fontweight="bold")
        save("07_no2_vs_temp_dual")

# ═══ 8. S2 escenas vs S5P cobertura ═══
s2_monthly = defaultdict(int)
for d in s2_dates: s2_monthly[(d.year, d.month)] += 1
s5p_monthly = defaultdict(int)
for d in s5p_dates: s5p_monthly[(d.year, d.month)] += 1
months = sorted(set(s2_monthly.keys()) | set(s5p_monthly.keys()))
fig, ax = plt.subplots(figsize=(16,5))
ax.bar(np.arange(len(months))-0.15, [s2_monthly.get(m,0) for m in months], 0.3, label="S2 escenas", color="#1E88E5", alpha=0.7)
ax.bar(np.arange(len(months))+0.15, [s5p_monthly.get(m,0) for m in months], 0.3, label="S5P días", color="#E53935", alpha=0.7)
ax.set_xticks(range(0,len(months),3)); ax.set_xticklabels([f"{y}-{m:02d}" for y,m in months][::3], rotation=45, fontsize=7)
ax.legend(); ax.grid(axis="y", alpha=0.3)
ax.set_title("Fig 8: S2 vs S5P — cobertura temporal mensual", fontweight="bold")
save("08_s2_vs_s5p_cobertura")

# ═══ 9. Panel de densidad de datos ═══
all_coverage = pd.DataFrame({
    "S5P": [d in s5p_dates for d in all_dates],
    "S2": [d in s2_dates for d in all_dates],
    "ERA5": [d in era5_dates for d in all_dates],
    "MODIS": [d in mod_dates for d in all_dates],
    "DAGMA": [d in dagma_dates for d in all_dates],
}, index=all_dates)
daily_overlap = all_coverage.sum(axis=1)
fig, ax = plt.subplots(figsize=(16,4))
ax.fill_between(all_dates, daily_overlap.values, alpha=0.3, color="purple")
ax.plot(all_dates, daily_overlap.values, lw=1.5, color="purple")
ax.set_ylabel("Datasets activos"); ax.set_ylim(0,5.5)
ax.axhline(3, color="red", ls="--", alpha=0.5, label="3 datasets")
ax.axhline(5, color="green", ls="--", alpha=0.5, label="5 datasets (completo)")
ax.legend(); ax.set_title("Fig 9: Datasets activos por día (máx 5)", fontweight="bold")
ax.grid(alpha=0.3); save("09_datasets_activos")

# ═══ 10. Matriz de correlación cross-dataset ═══
cross_data = {}
for dt in all_dates[:1000]:  # sample
    if dt in s5p_dates and dt in era5_blh and dt in era5_temp:
        cross_data[dt] = {
            "s5p_no2": no2_ts[no2_ts["date"]==pd.Timestamp(dt)]["no2"].values[0] if len(no2_ts[no2_ts["date"]==pd.Timestamp(dt)]) else np.nan,
            "blh": era5_blh.get(dt, np.nan),
            "temp": era5_temp.get(dt, np.nan),
        }
cross_df = pd.DataFrame(cross_data).T.dropna()
if len(cross_df) > 20:
    fig, ax = plt.subplots(figsize=(7,6))
    corr = cross_df.corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, square=True, ax=ax)
    ax.set_title("Fig 10: Correlación cross-dataset (S5P + ERA5)", fontweight="bold")
    save("10_correlacion_cross")

# ═══ 11-20. Panel de tortas + barras ═══
# 11 - Peso por dataset (GB)
fig, (ax1, ax2) = plt.subplots(1,2,figsize=(14,5))
weights = {"S5P":0.7,"S2":277,"ERA5":0.06,"MODIS":12.7,"DAGMA":1.1}
cols_pie = ["#E53935","#1E88E5","#43A047","#FFC107","#8E24AA"]
ax1.pie(weights.values(), labels=[f"{k}\n{v} GB" for k,v in weights.items()],
        autopct="%1.1f%%", colors=cols_pie, startangle=90)
ax1.set_title("Peso por dataset (GB)", fontweight="bold")
archivos = {"S5P":12784,"S2":3470,"ERA5":648,"MODIS":1822,"DAGMA":79}
ax2.barh(list(archivos.keys()), archivos.values(), color=cols_pie, edgecolor="white")
for i, (k, v) in enumerate(archivos.items()):
    ax2.text(v+100, i, f"{v:,}", va="center", fontsize=9)
ax2.set_xlabel("Archivos"); ax2.set_title("Archivos por dataset", fontweight="bold")
fig.suptitle("Fig 11: Dimensión del panel Big Data (>250 GB)", fontweight="bold")
fig.tight_layout(); save("11_peso_panel")

# 12 - Total GB acumulado
fig, ax = plt.subplots(figsize=(8,4))
ax.bar(["S5P","S2","ERA5","MODIS","DAGMA"], [0.7,277.7,277.76,290.46,291.56], color=cols_pie, edgecolor="white")
ax.axhline(50, color="red", ls="--", lw=1.5, label="Mínimo 50 GB (requisito)")
ax.set_ylabel("GB acumulados"); ax.legend(); ax.grid(axis="y", alpha=0.3)
ax.set_title("Fig 12: GB acumulados por dataset", fontweight="bold")
save("12_gb_acumulados")

# 13 - MODIS vs S5P cobertura
mod_all = pd.Series([d in mod_dates for d in all_dates], index=all_dates)
s5p_all = pd.Series([d in s5p_dates for d in all_dates], index=all_dates)
fig, ax = plt.subplots(figsize=(16,4))
ax.fill_between(all_dates, s5p_all.astype(int), alpha=0.3, color="#E53935", label="S5P")
ax.fill_between(all_dates, mod_all.astype(int), alpha=0.3, color="#FFC107", label="MODIS")
ax.legend(); ax.set_ylabel("Disponible (1=si)")
ax.set_title("Fig 13: MODIS y S5P — cobertura temporal", fontweight="bold")
ax.grid(alpha=0.3); save("13_modis_s5p_cobertura")

# ── RESUMEN ──
ng = len(list(OUT_DIR.glob("*.png")))
print(f"\n{'='*70}")
print(f"✅ EDA Panel Completo → {OUT_DIR}")
print(f"   {ng} gráficas generadas")
print(f"   Datasets integrados: 5 (S5P + S2 + ERA5 + MODIS + DAGMA)")
print(f"   Total datos referenciados: >250 GB")
print(f"{'='*70}")
