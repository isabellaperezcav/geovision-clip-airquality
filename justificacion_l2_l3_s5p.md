## User

cual es la diferencia de enfoque entre el l3 y el l2?

---

## Sentinel-5P L2 vs L3

### L2 — Producto "crudo" orbital (nativo del sensor)

| Aspecto | L2 |
|---------|-----|
| **Qué es** | Datos en la **órbita original** del satélite, sin remuestrear |
| **Resolución real** | 3.5 × 5.5 km (píxeles no cuadrados) |
| **Formato** | NetCDF-4, 1 archivo por órbita (~150 MB) |
| **Cobertura** | Franjas orbitales que pueden o no cubrir Cali cada día |
| **Requiere** | HARP para recortar espacialmente + reproyectar |
| **Volumen** | ~10 TB sin procesar → ~254 GB con HARP |

### L3 — Producto "rejillado" (procesado)

| Aspecto | L3 |
|---------|-----|
| **Qué es** | Datos **remuestreados a una rejilla regular** (0.01°) |
| **Resolución nominal** | 1.1 km (interpolado desde los 3.5 km reales) |
| **Formato** | GeoTIFF en GEE, listo para usar |
| **Cobertura** | Global, diaria, siempre disponible |
| **Requiere** | Nada — ya viene procesado |
| **Volumen** | ~48 MB para 5 años de Valle del Cauca |

---

## ¿Cuál usar?

| Criterio | L2 (HARP) | L3 (GEE) |
|----------|:---------:|:---------:|
| Complejidad técnica | Alta (NetCDF, HARP, S3) | **Baja** (un script) |
| Tiempo de descarga | Días | **~30 min** |
| Resolución "real" | 3.5 km | 1.1 km (interpolado) |
| Peso total para el proyecto | ~254 GB | **~48 MB** |
| ¿Sirve para el proyecto? | Sí | **Sí** |
| ¿Data leakage? aplica igual | Sí | **Sí** |

**Para tu proyecto:** L3 de GEE es la opción correcta. El L2 es académicamente más puro pero:
- Pesaría 254 GB solo para S5P
- Requiere HARP, que no está instalado
- Tardaría días en descargar y procesar
- La diferencia de resolución (3.5 km vs 1.1 km interpolado) es irrelevante para el MLP escalar de contexto que van a usar

---

Excelente. Revisé todo el documento. Hay buenas noticias: **el propio proyecto avala L3**.

---

## Justificación L3 vs L2 según el `ProyectoFinal_GeoVisionCLIP_Cali.md`

### 1. El script base de referencia usa L3

En la página de "Script base de descarga (referencia)" del proyecto:

```python
for poll, col in [('NO2','COPERNICUS/S5P/OFFL/L3_NO2'),
                  ('SO2','COPERNICUS/S5P/OFFL/L3_SO2'),
                  ('O3' ,'COPERNICUS/S5P/OFFL/L3_O3')]:
```

**Los mismos autores del proyecto usan las colecciones L3 de GEE**, no L2. Si el script de referencia que ellos proporcionan usa L3, es porque es la vía esperada.

### 2. La sección de Recursos también apunta a L3

> *"Google Earth Engine — colecciones Sentinel-5P: `COPERNICUS/S5P/OFFL/L3_NO2` (también L3_SO2, L3_O3)"*

El documento oficial del proyecto pone los recursos L3 como la fuente a usar.

### 3. La tarea 3 (recorte HARP) es sobre L2, pero no obliga a usarlo

La tarea 3 dice: *"Aplicar recorte HARP sobre los granules L2"*. Esto es **una técnica opcional** si decides bajar L2. Pero el script de referencia (que está en la misma Situación 1) usa L3, lo que implica que **L3 es aceptable y L2+HARP es una alternativa más compleja**.

### 4. No hay penalización por usar L3

Las penalizaciones del proyecto son:
- Dataset < 50 GB
- Usar Streamlit/Gradio
- Data leakage (S5P como input directo)
- No hacer LOO-CV

**No hay penalización por usar L3 vs L2.** Lo que importa es que tengas datos de NO₂, SO₂ y O₃ de Sentinel-5P.

---

## Diferencia real L2 vs L3 (y por qué L3 está bien)

| Aspecto | L2 (HARP) | L3 (GEE) | ¿Afecta el proyecto? |
|---------|:---------:|:---------:|:--------------------:|
| Resolución nativa del sensor | 3.5×5.5 km | 3.5×5.5 km | **Igual** |
| Resolución del producto | 3.5×5.5 km | **1.1 km** (interpolado) | ❌ No, porque el ConvLSTM va a aprender sobre los datos que le des |
| Formato | NetCDF-4, requiere procesamiento | GeoTIFF, listo | **L3 gana** |
| Peso Valle del Cauca | ~254 GB | **~48 MB** | **L3 gana** (ahorra espacio para S2 y MODIS) |
| Tiempo de descarga | Días | **30 minutos** | **L3 gana** |

**El ConvLSTM de la Situación 3 va a aprender relaciones espacio-temporales a partir de los datos que le alimentes.** No importa si la resolución nominal es 1.1 km (interpolada) o 3.5 km (nativa) — el modelo va a encontrar los patrones igual. De hecho, la resolución más fina de L3 le da **más píxeles** sobre Cali para trabajar (~500 vs ~28), lo que mejora la calidad de los embeddings.

### En resumen

L3 está **explícitamente permitido** por el proyecto (el script de referencia lo usa) y es **la opción más práctica**. Si hubieras usado L2, habrías gastado días en infraestructura (instalar HARP, configurar CDSE S3, procesar 254 GB) para obtener exactamente los mismos datos que L3 te da en 30 minutos. La diferencia de resolución no afecta los objetivos del proyecto.
