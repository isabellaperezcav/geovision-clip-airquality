# Facultad de Ingenierías
**Analítica de Datos I**  
Ingeniería de Datos e IA  
**Prof's. Carlos Ferro - Cristian E García**

---

# Proyecto Final

*GeoVision-CLIP Cali — Estimación de Contaminación Atmosférica en Puntos No Muestreados mediante Deep Learning + Estadística Geoespacial Avanzada*

Tercer Corte · Unidad III · Grupos de 3 estudiantes · Duración: 4 semanas

---

## Condiciones:

- Subir el proyecto en formato PDF en la plataforma UAO-Virtual. Se debe entregar un informe y los archivos adicionales (códigos, notebooks, checkpoints, manifests) se deben entregar como anexo. El informe no debe contener más de 25 páginas, incluidas las imágenes y tablas.
- Es necesario incluir el código de Python (PyTorch + GeoPandas + PyKrige + PySAL). Mostrar los resultados mediante tablas, gráficos o indicadores que les permitan responder a los planteamientos. Los KPIs deben reportarse con evidencia computacional verificable (hashes MD5 de checkpoints, logs de entrenamiento, capturas del sistema desplegado).
- Deben interpretar los resultados obtenidos en cada situación de acuerdo al contexto agroclimático y de salud ambiental de Santiago de Cali y su área metropolitana.
- Realizar la actividad en los grupos definidos anteriormente (3 integrantes). Cada integrante debe poder defender técnicamente cualquier sección del proyecto.
- Subir la tarea en un archivo .ZIP que contenga el informe en PDF, los notebooks Jupyter ejecutados con outputs visibles, el manifest del dataset (con hashes MD5), el Dockerfile y las URLs públicas del sistema desplegado y del repositorio Git.
- Está PROHIBIDO usar Streamlit, Gradio o cualquier framework de prototipado rápido como frontend principal. Se exige aplicación web profesional (React / Vue / Next.js).

---

## Resumen Ejecutivo

Santiago de Cali es la tercera ciudad de Colombia y enfrenta una problemática creciente de calidad del aire asociada al transporte vehicular, la industria del Valle del Cauca, las quemas de caña de azúcar y los aportes regionales del Pacífico biogeográfico. La red de monitoreo terrestre del DAGMA (9 estaciones operativas) y los reportes del IDEAM al SISAIRE proporcionan series temporales puntuales de NO₂, SO₂ y O₃ troposférico, pero su densidad espacial es insuficiente para representar la heterogeneidad de la exposición poblacional a escala intraurbana. El presente proyecto integrador propone resolver este problema mediante una arquitectura híbrida que combina: (i) un sistema de aprendizaje multimodal contrastivo basado en CLIP + Sparse Autoencoders sobre imágenes Sentinel-2 y Sentinel-5P, (ii) un módulo espacio-temporal de pronóstico mediante ConvLSTM, y (iii) Kriging Espacio-Temporal (ST-Kriging) que cierra el ciclo geoestadístico estimando concentraciones de los tres contaminantes en puntos no muestreados, con cuantificación explícita de la incertidumbre.

El proyecto se evalúa sobre tres situaciones secuenciales y acumulativas. La Situación 1 obliga a los estudiantes a construir un panel analítico de al menos 50 GB en formato optimizado (Zarr o Parquet) sobre infraestructura cloud, ejercitando capacidades reales de ingeniería de datos masivos. La Situación 2 implementa el núcleo de Deep Learning (GeoVision-CLIP + SAE) y valida psicométricamente las representaciones latentes mediante AFE/AFC. La Situación 3 articula el aprendizaje profundo con la estadística geoespacial avanzada para producir mapas continuos de contaminación validados contra las estaciones del DAGMA mediante leave-one-out cross-validation, y caracteriza perfiles tipológicos de zonas críticas dentro de la huella urbana de Cali.

---

## Contexto y Fundamentación

### Problema científico y de salud pública

La Resolución 2254 de 2017 del Ministerio de Ambiente establece niveles máximos permisibles para NO₂, SO₂ y O₃, pero su verificación a escala urbana depende de redes de monitoreo costosas y dispersas. El DAGMA opera nueve estaciones distribuidas heterogéneamente sobre los 564 km² del municipio, lo que deja amplias zonas de Cali sin cobertura directa (laderas, sur del municipio, zona industrial Yumbo–Acopi). La pregunta operativa es: ¿podemos estimar las concentraciones de NO₂, SO₂ y O₃ en cualquier punto (lat, lon) de la ciudad, con incertidumbre cuantificada, usando exclusivamente datos satelitales gratuitos y unas pocas estaciones de validación?

### Por qué Deep Learning + Estadística Geoespacial

Sentinel-5P TROPOMI provee columnas troposféricas de NO₂, SO₂ y O₃ con resolución nativa de 3.5 × 5.5 km y revisita diaria, pero esta resolución es demasiado gruesa para diferenciar la exposición de un barrio respecto a otro. Sentinel-2 MSI, por el contrario, ofrece 10 m de resolución pero no observa los gases directamente: solo proporciona covariables proxy (NDVI, BSI, índices urbanos, sombra de edificaciones). El reto es realizar downscaling estadístico fusionando ambas fuentes. La hipótesis del proyecto es que un modelo CLIP fino-ajustado al dominio satelital aprende un espacio latente donde los embeddings codifican simultáneamente firma espectral y semántica geográfica; sobre ese espacio, un ConvLSTM captura la dinámica temporal y un Kriging Espacio-Temporal lo proyecta a una superficie continua interpretable, con varianza de predicción que sirve como mapa de confianza. El cierre del ciclo es estadístico: el variograma experimental de los residuos del modelo profundo debe ser nugget puro para considerarse adecuado, y el Índice de Moran sobre las predicciones cuantifica si el modelo aprendió coherencia geográfica o predice ruido.

---

## Situación 1 (1.0 Pts)
### Construcción del Panel Espacio-Temporal y Arquitectura Cloud

Se requiere construir un panel analítico longitudinal de mínimo 50 GB que integre 5 años de imágenes satelitales sobre el área metropolitana de Santiago de Cali (latitud 3.30°N a 3.55°N; longitud −76.60°W a −76.40°W), incluyendo el corredor industrial Yumbo–Acopi y la zona de cultivos de caña del norte del Valle. El panel debe permitir el estudio conjunto de: (a) columnas troposféricas de NO₂, SO₂ y O₃ provenientes de Sentinel-5P TROPOMI, (b) covariables ópticas de alta resolución provenientes de Sentinel-2 MSI, (c) covariables meteorológicas de reanálisis ERA5-Land, y (d) ground truth puntual de las estaciones del DAGMA y los reportes SISAIRE.

### Fuentes de datos obligatorias

| Fuente | Variable | Resolución espacial | Periodicidad | Acceso |
|--------|----------|---------------------|--------------|--------|
| Sentinel-5P L2 OFFL | NO₂ troposférico | 3.5 × 5.5 km | Diaria (1–2 órbitas) | Copernicus DataSpace · GEE |
| Sentinel-5P L2 OFFL | SO₂ vertical column | 3.5 × 5.5 km | Diaria | Copernicus DataSpace · GEE |
| Sentinel-5P L2 OFFL | O₃ total column | 3.5 × 5.5 km | Diaria | Copernicus DataSpace · GEE |
| Sentinel-2 L2A | 13 bandas (B2-B12) | 10/20/60 m | 5 días | Copernicus · GEE · AWS Open Data |
| MODIS MCD19A2 | AOD (proxy PM) | 1 km | Diaria | NASA Earthdata · GEE |
| ERA5-Land | T2m, viento, BLH, RH | 9 km | Horaria | Copernicus CDS |
| DAGMA / SISAIRE | NO₂, SO₂, O₃ in-situ | 9 estaciones | Horaria | sisaire.ideam.gov.co |

### Verificación del peso del dataset

El equipo docente verificó analíticamente la viabilidad del umbral. Considerando 5 años (1825 días), 2 órbitas/día sobre Cali y 3 contaminantes, el volumen del componente Sentinel-5P L2 sin recortar asciende a ≈ 10.2 TB. Aplicando recorte HARP a la huella metropolitana de Cali, se reduce a ≈ 254 GB para Sentinel-5P solamente. Sumando 4 tiles de Sentinel-2 con filtro de nubosidad < 60% (≈ 164 adquisiciones útiles/tile), el componente óptico añade ≈ 513 GB. ERA5-Land aporta ≈ 143 GB y MODIS MAIAC ≈ 89 GB. Cualquier escenario realista de implementación supera holgadamente el umbral de 50 GB, lo que obliga al uso de almacenamiento de objetos y procesamiento distribuido.

| Escenario de descarga | Recortes aplicados | Peso estimado |
|-----------------------|--------------------|---------------|
| Mínimo (Cali + S2 parcial) | BBox Cali, S2 50% | ≈ 626 GB |
| Intermedio (Colombia recortado) | BBox Colombia + todas las fuentes | ≈ 2.4 TB |
| Completo (granules sin recorte) | Sin recorte espacial | ≈ 10.9 TB |
| **Umbral mínimo del proyecto** | — | **≥ 50 GB** |

### Tareas obligatorias

1. Configurar credenciales de Google Earth Engine y Copernicus DataSpace Ecosystem (CDSE). Autenticar la API de Earthdata para acceder a MAIAC.
2. Implementar pipeline de descarga distribuido en Dask o Spark. Las descargas no pueden hacerse de forma secuencial single-thread: deben paralelizar por banda, fecha y tile.
3. Aplicar recorte HARP sobre los granules L2 de Sentinel-5P para reducir a la huella metropolitana de Cali (use harpconvert con bin_spatial sobre BBox −76.60, 3.30, −76.40, 3.55).
4. Convertir las series temporales a formato Zarr (recomendado para arrays N-dimensionales con chunking espacio-temporal) o Parquet particionado por (año, mes, contaminante).
5. Persistir el panel en almacenamiento de objetos: Google Cloud Storage, AWS S3 o Azure Blob (cualquier free tier con créditos académicos es suficiente).
6. Construir un manifest JSON con: ruta de cada archivo, hash MD5, dimensiones, fecha de adquisición, fuente y bounding box. Este manifest debe estar versionado en Git.
7. Generar un reporte EDA con: distribución temporal de adquisiciones por contaminante, mapa de cobertura espacial efectiva, porcentaje de píxeles válidos por escena, y serie temporal media de cada contaminante para las 9 estaciones DAGMA.

### Script base de descarga (referencia)

```python
import ee, dask, geemap
from dask.distributed import Client

ee.Initialize(project='geovision-cali')
client = Client(n_workers=4, threads_per_worker=2, memory_limit='4GB')
cali = ee.Geometry.Rectangle([-76.60, 3.30, -76.40, 3.55])

# 5 años de NO2, SO2, O3 (Sentinel-5P)
for poll, col in [('NO2','COPERNICUS/S5P/OFFL/L3_NO2'),
                  ('SO2','COPERNICUS/S5P/OFFL/L3_SO2'),
                  ('O3' ,'COPERNICUS/S5P/OFFL/L3_O3')]:
    ic = (ee.ImageCollection(col)
          .filterBounds(cali)
          .filterDate('2020-01-01','2024-12-31'))
    # exportar a GCS particionado por mes (paraleliza con Dask)
    futures = client.map(export_monthly_chunk, ic.toList(ic.size()), pollutant=poll)

# Verificar peso ≥ 50 GB antes de continuar
assert manifest_total_size_gb() >= 50, 'Dataset insuficiente'
```

### Entregables Situación 1

- Diagrama de arquitectura cloud (almacenamiento + cómputo + orquestación).
- Manifest JSON con ≥ 50 GB de datos verificados y hashes MD5.
- Notebook EDA con mínimo 8 visualizaciones del panel.
- Reporte de costos cloud (descarga + almacenamiento) y discusión de cuellos de botella.

---

## Situación 2 (1.5 Pts)
### GeoVision-CLIP — Aprendizaje Multimodal y Reducción de Dimensionalidad

Una vez consolidado el panel, los estudiantes deben construir un modelo multimodal que aprenda representaciones conjuntas imagen-texto sobre tiles satelitales de Cali. El núcleo arquitectónico es un encoder visual ViT-B/32 inicializado con pesos de RemoteCLIP (variante de CLIP especializada en teledetección), un encoder textual multilingüe (XLM-RoBERTa o paraphrase-multilingual-MiniLM), y dos Sparse Autoencoders simétricos insertados entre los encoders y sus projection heads. La función objetivo combina pérdida contrastiva InfoNCE con la pérdida de reconstrucción y regularización L1 de los SAE.

### Especificación del modelo

**Loss total (entrenamiento end-to-end):**

```
L_total = L_InfoNCE + α · (L_sae_img + L_sae_txt)

L_InfoNCE = −(1/N) · Σᵢ log[ exp(sim(eᵢ,fᵢ)/τ) / Σⱼ exp(sim(eᵢ,fⱼ)/τ) ]

L_sae = ‖x − x̂‖² + λ · ‖z‖₁
```

donde:
- τ = temperatura learnable (init 0.07)
- α = 0.1 (peso regularización SAE)
- λ = 1e-3 (peso sparsity)
- d = 512 (dimensión embedding SAE)
- e_img, e_txt ∈ ℝ^256 (espacio contrastivo)

### Construcción del dataset de pares imagen–texto

- Mínimo 1000 pares (tile Sentinel-2 64×64 px, descripción en español) distribuidos en al menos 5 clases: `contaminación_alta_NO₂`, `contaminación_alta_SO₂`, `ozono_anómalo`, `vegetación_densa`, `suelo_urbano`.
- Etiquetado semi-supervisado: usar las concentraciones de Sentinel-5P sobre el centroide del tile como pseudo-label, agrupado por percentiles (p25, p50, p75, p90, p99 de la distribución sobre Cali en los 5 años).
- Split estratificado 70/15/15 con semilla fija (SEED=42).
- Series temporales: ≥ 30 secuencias de 8 fechas consecutivas para alimentar el módulo de forecasting de la Situación 3.

### Validación psicométrica de los embeddings (AFE + AFC)

Sobre la matriz de embeddings de la rama visual (n × 512), aplicar Análisis Factorial Exploratorio con extracción por Componentes Principales y rotación Varimax. Determinar el número de factores m a retener vía Scree Plot y varianza acumulada (criterio: m que explique ≥ 80%). Posteriormente, especificar un modelo de medición confirmatorio con cuatro constructos latentes hipotetizados — Carga Antropogénica, Estrés Vegetal, Densidad Urbana, Volatilidad Atmosférica — y evaluar bondad de ajuste con RMSEA, CFI y SRMR. Concluir sobre la validez de constructo.

### KPIs de la Situación 2

| KPI | Umbral mínimo | Excelente | Cómo medirlo |
|-----|---------------|-----------|--------------|
| Recall@1 imagen→texto | ≥ 0.45 | ≥ 0.65 | `clip_metrics.recall_at_k(1)` |
| Recall@5 imagen→texto | ≥ 0.70 | ≥ 0.85 | `clip_metrics.recall_at_k(5)` |
| Sparsity ratio SAE visual | ≥ 0.70 | ≥ 0.85 | `mean(z < 0.01)` |
| Loss reconstrucción SAE | ≤ 0.05 | ≤ 0.02 | MSE val |
| Varianza explicada AFE (m factores) | ≥ 80% | ≥ 90% | scree plot + acumulada |
| RMSEA (modelo AFC) | < 0.08 | < 0.05 | lavaan / semopy |
| CFI (modelo AFC) | > 0.90 | > 0.95 | lavaan / semopy |

### Entregables Situación 2

- Checkpoint del modelo entrenado (.pt) con MD5 verificable y reproducible entre los integrantes del grupo.
- Curvas de entrenamiento: loss total, loss InfoNCE, loss SAE, sparsity ratio por epoch.
- Reporte AFE+AFC con matriz de cargas rotada, scree plot e índices de bondad de ajuste.
- Análisis de neuronas activas del SAE para cada clase (interpretabilidad mecánica).

---

## Situación 3 (2.5 Pts)
### Predicción Geoestadística Espacio-Temporal de Contaminantes en Puntos No Muestreados

Esta situación es el corazón del proyecto: articular el modelo profundo entrenado en la Situación 2 con técnicas avanzadas de estadística geoespacial para producir, dado cualquier punto (lat, lon) en la huella metropolitana de Cali y un horizonte temporal {T+1, T+3, T+7 días}, una estimación puntual de la concentración esperada de NO₂, SO₂ y O₃, junto con su varianza de predicción Kriging. El producto final son seis mapas de gradiente (3 contaminantes × 3 horizontes) renderizados como overlays interactivos en el frontend, validados externamente contra las series horarias del DAGMA mediante leave-one-out cross-validation espacial.

### Pipeline integral

```
INPUT: (lat, lon) ∈ Cali, radio R ∈ [1, 15] km, contaminante ∈ {NO₂, SO₂, O₃}

PASO 1 — Generar grilla N×N de puntos en círculo de radio R (resolución 0.005°)
PASO 2 — Para cada punto, recuperar tile S2 + serie S5P histórica (últimas 8 fechas)
PASO 3 — Pasar tiles por GeoVision-CLIP+SAE → embeddings ∈ ℝ^(N×N × 8 × 256)
PASO 4 — ConvLSTM espacio-temporal → predicción (3 horizontes × N×N) por contaminante
PASO 5 — Ajustar variograma experimental sobre residuos del DL → modelo teórico
PASO 6 — ST-Kriging sobre las predicciones del DL → superficie continua + var(σ²)
PASO 7 — Validación externa: LOO-CV contra estaciones DAGMA → RMSE, MAE, R²
PASO 8 — Análisis de Moran (global y LISA) sobre la superficie predicha

OUTPUT: 9 mapas de gradiente (3 contaminantes × 3 horizontes) + mapas de incertidumbre
```

### Componente A — ConvLSTM (Deep Learning)

Una sola red ConvLSTM bidireccional (hidden=128, kernel=3, 2 capas) procesa secuencias temporales de embeddings reorganizados en grilla espacial. La salida es un tensor (B, 3, 3, H, W) correspondiente a [horizonte] × [contaminante] × [grilla]. La capa de salida es una conv 1×1 que mapea los canales latentes a las 9 predicciones simultáneas. Entrenar con AdamW (lr=1e-4), early stopping sobre RMSE espacial en val, batch_size=16 secuencias.

### Componente B — Kriging Espacio-Temporal (Estadística)

Sobre las predicciones del ConvLSTM en la grilla discreta, ajustar un variograma experimental separable en espacio y tiempo. Calcular nugget, sill y range para los componentes espacial y temporal. Validar el ajuste con la función objetivo de mínimos cuadrados ponderados. Posteriormente, ejecutar Kriging Ordinario 3D (PyKrige.OrdinaryKriging3D) que interpola simultáneamente en (lat, lon, t) y produce no solo el valor estimado sino también la varianza de predicción σ²(s,t), que se usa para construir el mapa de incertidumbre con opacidad inversamente proporcional a σ.

```python
from pykrige.ok3d import OrdinaryKriging3D
import numpy as np

def st_kriging(lats, lons, times, values, q_lats, q_lons, q_t,
               variogram='exponential'):
    # Normalización (evita anisotropía espuria)
    lat_n = (lats - lats.mean()) / lats.std()
    lon_n = (lons - lons.mean()) / lons.std()
    t_n   = (times - times.mean()) / (times.std() + 1e-8)

    ok = OrdinaryKriging3D(lat_n, lon_n, t_n, values,
                           variogram_model=variogram,
                           verbose=False)
    z, var = ok.execute('points',
                        (q_lats - lats.mean()) / lats.std(),
                        (q_lons - lons.mean()) / lons.std(),
                        (q_t   - times.mean()) / (times.std() + 1e-8))
    return z, var  # valor predicho + varianza Kriging
```

### Componente C — Validación geoestadística rigurosa

- **Leave-One-Out CV espacial** sobre las 9 estaciones DAGMA: para cada estación e_i, entrenar con las 8 restantes y predecir e_i. Reportar RMSE, MAE y R² agregados por contaminante.
- **Variograma de residuos**: el variograma de los residuos (observado − predicho) sobre las estaciones de validación debe ser nugget puro (sin estructura espacial remanente). Esto certifica que el modelo capturó la autocorrelación.
- **Índice de Moran Global I** sobre la superficie predicha, con prueba de hipótesis (permutation test, n=999). Se espera I > 0.30 con p < 0.05.
- **Análisis LISA** (Local Indicators of Spatial Association) para identificar clusters de alta y baja contaminación con significancia local.
- **Comparación de semivariogramas**: el semivariograma de la serie observada debe ser estadísticamente equivalente al de la predicción (validación de coherencia espacial del modelo).

### KPIs de la Situación 3

| KPI | Mínimo | Excelente | Verificación |
|-----|--------|-----------|--------------|
| RMSE LOO-CV NO₂ (T+1) | ≤ 8 µg/m³ | ≤ 4 µg/m³ | vs. DAGMA |
| RMSE LOO-CV SO₂ (T+1) | ≤ 6 µg/m³ | ≤ 3 µg/m³ | vs. DAGMA |
| RMSE LOO-CV O₃ (T+1) | ≤ 12 µg/m³ | ≤ 6 µg/m³ | vs. DAGMA |
| R² LOO-CV (promedio 3 contaminantes) | ≥ 0.55 | ≥ 0.75 | scikit-learn |
| Índice de Moran I (predicciones) | > 0.30 (p<0.05) | > 0.50 | esda.Moran |
| Variograma residuos (nugget puro) | Sin estructura | Sin estructura | PyKrige |
| Cobertura cinturón 95% (σ Kriging) | ≥ 92% | ≥ 95% | Empírico LOO |
| Degradación T+1 → T+7 (RMSE) | < 60% aumento | < 30% | Ratio RMSE |
| Latencia inferencia end-to-end | < 8 s | < 3 s | time.perf_counter |

### Entregables Situación 3

- Notebook de entrenamiento del ConvLSTM con curvas y métricas reproducibles.
- Reporte geoestadístico: variogramas (experimental + teórico ajustado), Moran I y LISA con mapas de significancia.
- Tabla de validación LOO-CV por estación DAGMA y por contaminante.
- Sistema desplegado: dado un (lat, lon) y un horizonte, devuelve los 9 mapas de gradiente con sus respectivos mapas de incertidumbre.
- Análisis de perfiles tipológicos (clustering K-Means sobre las superficies predichas) para identificar zonas crónicas de alta contaminación en Cali.

---

## Frontend, Despliegue e Informe Final

### Especificación del frontend

El frontend debe ser una aplicación web profesional desarrollada en React + Vite, Vue 3 o Next.js. Está prohibido usar Streamlit o Gradio. La interfaz incluye un mapa interactivo Leaflet centrado en Cali con las 9 estaciones DAGMA georreferenciadas. El usuario puede: (i) hacer click en cualquier punto del mapa para consultar predicciones, (ii) seleccionar contaminante y horizonte temporal mediante controles, (iii) visualizar los 9 mapas de gradiente (3×3) con slider temporal animado entre T+1, T+3, T+7, (iv) ver la incertidumbre como capa de opacidad superpuesta, (v) inspeccionar tooltips con valor predicho ± σ, (vi) descargar la predicción como GeoTIFF o CSV.

### Stack tecnológico recomendado

| Capa | Tecnología | Notas |
|------|------------|-------|
| Almacenamiento | Zarr / Parquet en GCS o S3 | Particionado por (año, mes, contaminante) |
| ETL distribuido | Dask / Spark | obligatorio por volumen |
| Modelo CLIP+SAE | PyTorch + RemoteCLIP | frozen visual encoder |
| ConvLSTM | PyTorch nn.Module | custom implementación propia |
| Geoestadística | PyKrige + PySAL (esda) | OK3D + Moran |
| Backend API | FastAPI + Uvicorn | endpoints /predict, /validate |
| Frontend | React + Vite + Leaflet | no Streamlit/Gradio |
| Contenedor | Docker + docker-compose | imagen multi-stage |
| Despliegue | HuggingFace Spaces / Render | free tier suficiente |
| Trazabilidad | Weights & Biases | logging de runs |

### Estructura del informe técnico (15–25 páginas)

| Sección | Contenido | Pág. |
|---------|-----------|------|
| 1. Resumen ejecutivo | Problema, solución, KPIs alcanzados, URL del sistema | 1 |
| 2. Construcción del panel | Arquitectura cloud, manifest, EDA | 3-4 |
| 3. Modelo GeoVision-CLIP | Arquitectura, entrenamiento, validación AFE/AFC | 3-4 |
| 4. Pipeline DL + Geoestadística | ConvLSTM + ST-Kriging integrados | 3-4 |
| 5. Resultados y validación | KPIs, LOO-CV, Moran/LISA, mapas | 4-5 |
| 6. Análisis de ablación | Con/sin SAE, DL solo vs DL+Kriging | 2 |
| 7. Despliegue | Diagrama, latencia, URL pública | 1-2 |
| 8. Discusión y trabajo futuro | Limitaciones, mejoras, replicabilidad | 1-2 |
| Apéndice A | Hashes MD5, manifest, semillas | — |
| Apéndice B | Código clave comentado | — |

---

## Rúbrica de Calificación

| Componente | Peso | Criterios |
|------------|------|-----------|
| Construcción del panel (Sit. 1) | 20% | ≥ 50 GB verificado, manifest con MD5, EDA completo, ETL distribuido |
| Modelo CLIP + SAE (Sit. 2) | 20% | KPIs de retrieval/sparsity alcanzados, AFE/AFC reportado |
| DL + Geoestadística (Sit. 3) | 30% | ConvLSTM + ST-Kriging integrados, validación LOO-CV con DAGMA |
| Frontend y despliegue | 10% | URL pública, mapas interactivos, latencia < 8 s |
| Informe técnico | 10% | Estructura completa, rigor, KPIs con evidencia computacional |
| Pitch y defensa | 10% | Demo en vivo, dominio de cualquier sección por cualquier integrante |

### Penalizaciones

- Dataset < 50 GB verificado: −40% del componente Situación 1.
- Usar Streamlit/Gradio como frontend principal: −30% del componente despliegue.
- Reportar KPIs sin evidencia computacional: −50% del componente afectado.
- MD5 del checkpoint no coincide entre integrantes: −20% del componente modelo.
- Validación LOO-CV no realizada o filtrada: −60% del componente Situación 3.
- Pasar las concentraciones de Sentinel-5P como input directo del modelo (data leakage): −25% del proyecto.

### Bonificaciones

- Modo oscuro implementado en frontend: +2 puntos.
- Tercer modalidad de input (audio Whisper): +3 puntos.
- Análisis de equidad espacial (rendimiento del modelo por estrato socioeconómico de Cali): +4 puntos.
- Comparación con OMI/AURA o GOME-2 como segunda fuente independiente de validación: +3 puntos.

---

## Recursos y Referencias

### Repositorios de datos

- Copernicus Data Space Ecosystem: https://dataspace.copernicus.eu
- Google Earth Engine — colecciones Sentinel-5P: `COPERNICUS/S5P/OFFL/L3_NO2` (también L3_SO2, L3_O3)
- Sentinel-2 L2A en AWS Open Data: `s3://sentinel-cogs/sentinel-s2-l2a-cogs/`
- MODIS MAIAC AOD: NASA Earthdata Search → MCD19A2
- ERA5-Land: Copernicus Climate Data Store (CDS API)
- SISAIRE — IDEAM: http://sisaire.ideam.gov.co/ideam-sisaire-web/
- DAGMA Cali — Sistema de Vigilancia: https://www.cali.gov.co/dagma/

### Referencias técnicas clave

- Veefkind, J.P. et al. (2012). TROPOMI on the ESA Sentinel-5 Precursor. *Remote Sensing of Environment*, 120, 70–83.
- van Geffen, J. et al. (2022). Sentinel-5P TROPOMI NO₂ retrieval. *AMT*.
- Theys, N. et al. (2017). Sulfur dioxide retrievals from TROPOMI onboard Sentinel-5 Precursor. *AMT*.
- Liu et al. (2024). RemoteCLIP: A Vision Language Foundation Model for Remote Sensing. *IEEE TGRS*.
- Cressie, N. & Wikle, C. (2011). *Statistics for Spatio-Temporal Data*. Wiley.
- Anselin, L. (1995). Local Indicators of Spatial Association — LISA. *Geographical Analysis* 27(2).
- Templeton, T. et al. (2023). Sparse Autoencoders for Mechanistic Interpretability. *Anthropic Technical Report*.

---

*Universidad Autónoma de Occidente · Facultad de Ingenierías*  
*Programa de Ingeniería de Datos e IA · Cali, Colombia · 2026*
