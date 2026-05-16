## ✅ EDA Sentinel-2 — Completado

**Script**: `datos_api/eda_sentinel2.py`  
**Salida**: `eda/sentinel2/` (12 gráficas PNG + CSV + reporte TXT)

### 12 visualizaciones generadas

| # | Archivo | Contenido | Estado |
|---|---------|-----------|--------|
| 1 | `01_escenas_por_ano.png` | Barras + línea de tendencia 2020–2024 | ✅ |
| 2 | `02_escenas_por_mes.png` | Barras apiladas por año y mes | ✅ |
| 3 | `03_heatmap_temporal.png` | Heatmap año×mes con anotaciones | ✅ |
| 4 | `04_tiles_satelites.png` | Pie charts: 18NUJ vs 18NUK + S2A vs S2B | ✅ |
| 5 | `05_mapa_cobertura.png` | Mapa con tiles MGRS, bbox, estaciones DAGMA | ✅ |
| 6 | `06_boxplot_bandas.png` | Boxplots de reflectancia por banda | ✅ |
| 7 | `07_histogramas_bandas.png` | 10 histogramas de distribución por banda | ✅ |
| 8 | `08_correlacion_bandas.png` | Matriz de correlación Pearson | ✅ |
| 9 | `09_ndvi_histograma.png` | Histograma NDVI + categorías (pie) | ✅ |
| 10 | `10_ndvi_serie_temporal.png` | Serie temporal NDVI mediana mensual | ✅ |
| 11 | `11_completitud_pixeles.png` | Completitud y píxeles válidos por escena | ✅ |
| 12 | `12_escenas_por_tile_ano.png` | Barras agrupadas por tile y año | ✅ |

### Hallazgos clave

| Hallazgo | Detalle |
|----------|---------|
| **2022 es un outlier** | Solo 33 escenas vs. 108 en 2020. Posible El Niño o nubosidad extrema. |
| **Estacionalidad marcada** | Ene (51) vs. Mar (17). Cali tiene el valle más húmedo en Marzo–Mayo. |
| **NDVI mediano: 0.35** | Área mixta urbano-rural con vegetación fragmentada. |
| **Reflectancia NIR >> Red** | B08 mediana 0.34 vs B04 mediana 0.11 → señal de vegetación activa. |
| **Correlación entre bandas adyacentes: >0.93** | Esperado. La correlación más baja es B02–B12 (0.96) → dominada por estructura espacial. |
| **Completitud ~55%** | Solo la mitad de los píxeles del tile rectangular son válidos (área de imagen irregular dentro del tile UTM). |
| **No hay archivos corruptos** | 3,470 archivos existen en disco. MD5s verificados (spot-check 5/5). |

### Recomendaciones de funciones NO pertenecientes al EDA

Estas tareas requieren scripts separados de procesamiento/transformación:

1. **Conversión a Zarr** — empaquetar 277 GB en arrays N-dimensionales con chunking `(año, banda, y, x)`
2. **Alineamiento S2 ↔ S5P** — reproyectar S2 (10/20m, UTM) a la grilla de S5P (1.1km, WGS84) para entrenar el ConvLSTM
3. **Recorte tiles 64×64** — generar parches cuadrados para el dataset de pares imagen-texto de CLIP
4. **Índices avanzados** — NDBI (urbanización), NDWI (humedad), BSI (suelo desnudo), NBR (quemas de caña)
5. **Filtro QA60** — aplicar banda de calidad para filtrar cirrus y sombras de nubes (actualmente solo se filtró `<60% nubes` en STAC)
6. **Extensión 2025–2026** — descargar datos más recientes si el periodo actual es insuficiente

---

