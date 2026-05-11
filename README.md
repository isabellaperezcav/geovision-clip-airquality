# 05 · Modelado Multimodal — GeoVisionCLIP-Cali

Pipeline end-to-end de estimación espacio-temporal de contaminación atmosférica
sobre la región metropolitana de Cali (incluye Yumbo y Rozo).

---

## Estructura

```
05_modelado_multimodal/
├── 01_ETL_Distribuido_Sentinel2.ipynb     # Fase 1: Dask + Rasterio → Zarr
├── 02_Ingesta_S5P_y_Alineacion.ipynb      # Fase 2: Azure ADLS + KDTree + JSONL
├── 03_Entrenamiento_SAE_Multimodal.ipynb  # Fase 3: GeoRSCLIP + SAE + Exportación
├── .env.template                          # Plantilla de credenciales (NO subir .env real)
└── README.md
```

---

## Orden de Ejecución

1. **`01_ETL_Distribuido_Sentinel2.ipynb`**
   - Lee `D:\analitica\sentinel2\manifest_sentinel2.json`
   - Procesa bandas B02, B03, B04, B08 con Dask (4 workers × 6 GB)
   - Normaliza con stats de GeoRSCLIP y guarda en `D:\analitica\procesado_zarr\sentinel2_224.zarr`

2. **`02_Ingesta_S5P_y_Alineacion.ipynb`**
   - Conecta al Azure ADLS2 usando credenciales desde `.env`
   - Descarga datos S5P L3 (NO₂, SO₂, O₃) para el BBox de Cali
   - Alinea espacio-temporalmente con S2 usando KDTree (tolerancia ±3 días)
   - Calcula percentiles históricos (p25→p99)
   - Genera `dataset_multimodal.jsonl` con ≥1000 pares imagen-texto en español

3. **`03_Entrenamiento_SAE_Multimodal.ipynb`**
   - Carga GeoRSCLIP congelado (HuggingFace: `Zilun/GeoRSCLIP`)
   - Entrena SAE (512→2048→512) con loss MSE + L1
   - KPIs objetivo: Reconstrucción ≥70%, Sparsity ≥70%, Recall@1 ≥0.45
   - Exporta artefactos para el equipo

---

## Requisitos de Hardware

| Recurso | Valor | Notas |
|---------|-------|-------|
| RAM | 32 GB | Dask limitado a 4×6 GB = 24 GB |
| VRAM | 6.4 GB | RTX 3050 Laptop, TF32 activado |
| Disco | ~50 GB libres en D:\ | Para Zarr + caché S5P + checkpoints |
| SO | Windows 11 | Paths con `r"D:\..."` |

---

## Artefactos Exportados

| Archivo | Destino | Formato |
|---------|---------|---------|
| `embeddings_visuales_sae.pt` | Martín (AFE/AFC) | Tensor (n × 512) |
| `interpretabilidad_latentes.json` | Martín (AFE/AFC) | JSON clases→índices latentes |
| `secuencias_gru.pt` | Luz Ángela (GRU) | Tensor (n_ventanas × 8 × 2048) |
| `sae_cali_final.pt` | Trazabilidad | Pesos del SAE entrenado |
| `manifest_artefactos.json` | Trazabilidad | MD5 de todos los artefactos |

---

## Credenciales Azure

Copiar `.env.template` como `.env` en `D:\analitica\` y completar
`AZURE_CLIENT_ID` y `AZURE_CLIENT_SECRET`. El `.env` **DEBE** estar en `.gitignore`.

---

## Dependencias Principales

```bash
pip install dask[distributed] rasterio zarr numcodecs \
            azure-storage-blob azure-identity python-dotenv \
            open-clip-torch transformers huggingface_hub \
            torch torchvision scipy pandas matplotlib seaborn tqdm
```
