---
title: Profundizacion NO2-Univalle, SO2-Ermita, O3-Pance en bucket vs Excel
date: 2026-05-20
tags:
  - auditoria
  - dagma
  - no2
  - so2
  - o3
  - calidad-aire
  - distribucion-temporal
aliases:
  - Distribucion 3 series target Cali
---

# Profundizacion en las 3 series mejor cubiertas

> [!info] Resumen
> Las 3 mejores series ground truth (NO2 Univalle 49,9%, SO2 Ermita 82,9%, O3 Pance 81,1%) tienen problemas serios al compararlas entre el bucket Azure y el Excel SVCASC_FT_50. Bucket y Excel NO coinciden numericamente (Pearson r=0,08 para SO2-Ermita y r=0,29 para O3-Pance), aun probando shifts horarios para descartar timezones. Univalle NO2 no existe en el bucket. La cobertura en Excel parece prometedora a nivel agregado pero esconde rachas de NA de 119 a 367 dias continuos en momentos criticos del periodo del proyecto.

Para esta profundizacion descargue los 79 chunks completos del bucket (770,9 MiB) y extraje todas las mediciones Cali NO2/SO2/O3 (72.919 filas DAGMA, ninguna NO2). Las cifras de cobertura del Excel se calculan sobre las 86 columnas-serie, descontando "NA" textual.

## 1. NO2 - Univalle

### 1.1. En el bucket: inexistente

| Operador | Estacion | Variable | Mediciones bucket |
|---|---|---|---|
| Cualquiera | Cualquier estacion Cali | NO2 | **0** |

Verificado sobre las 72.919 filas DAGMA-Cali (suma de NO2, SO2, O3): solo aparecen `msfl_code` igual a `SO2` y `O3`. El SISAIRE no exporta NO2 para ninguna estacion DAGMA de Cali en el periodo 2020-2024 a traves de este canal.

Esto confirma el hallazgo previo de Juan Andres+Natalia ("Univalle sin NO2 2019-2024") y la decision de Cristian Clase 34 (2026-05-08) que autorizo libertad metodologica para tratar el NO2 con columnas troposfericas de Sentinel-5P o extrapolacion.

### 1.2. En el Excel: solo Univalle, con grandes huecos

| Indicador | Valor |
|---|---|
| Mediciones validas | 26.259 |
| Cobertura sobre grilla 6 anos | 49,9% |
| Periodo cubierto | 2020-01 a 2024-12 (no llega a 2025) |

**Cobertura por ano:**

| Ano | Mediciones | % cobertura |
|---|---|---|
| 2020 | 6.992 | 79,6% |
| 2021 | 3.564 | 40,7% |
| 2022 | 7.449 | 85,0% |
| 2023 | 6.276 | 71,6% |
| 2024 | 1.978 | 22,5% |
| 2025 | 0 | 0,0% |

**Rachas de NA mas largas (Excel - Univalle NO2):**

| Duracion | Fecha inicio | Fecha fin | Implicacion |
|---|---|---|---|
| 8.823 h (367,6 dias) | 2024-12-29 10:00 | 2026-01-01 00:00 | Sensor NO2 retirado o averiado desde fines de 2024 |
| 4.542 h (189,2 dias) | 2024-06-19 12:00 | 2024-12-25 18:00 | Toda la segunda mitad de 2024 sin dato |
| 3.434 h (143,1 dias) | 2021-04-15 20:00 | 2021-09-05 22:00 | Hueco enorme en 2021 (verano boreal) |
| 1.101 h (45,9 dias) | 2021-02-28 00:00 | 2021-04-14 21:00 | Continua el hueco hasta tocar el de 143 dias |
| 938 h (39,1 dias) | 2024-04-22 18:00 | 2024-05-31 20:00 | Inicio del colapso 2024 |
| 706 h (29,4 dias) | 2020-02-12 20:00 | 2020-03-13 06:00 | Hueco al inicio del registro |

Total: 809 rachas de NA, cuya cola larga concentra los huecos. La grilla horaria del Excel termina vacia desde 2024-12-29.

**Estadisticos descriptivos (sobre las 26.259 mediciones validas, ug/m3):**

| Estadistico | Valor |
|---|---|
| min | 0,000 |
| p25 | 6,958 |
| mediana | 12,147 |
| p75 | 18,973 |
| max | 91,858 |
| media | 14,058 |
| std | 10,052 |
| CV | 71,5% |
| Ceros | 602 (2,3%) |
| Outliers IQR | 866 (3,30% del total valido) |

**Comparacion con normativa:**

| Norma | Umbral | Excedencias en Excel |
|---|---|---|
| OMS 2021 anual NO2 | 10 ug/m3 | media 14,06 supera anual (no es comparacion 1 a 1) |
| OMS 2021 24h NO2 | 25 ug/m3 | 3.380 horas (12,87% del valido) |
| Colombia Res. 2254 anual | 60 ug/m3 | 58 horas (0,22%) |
| Colombia Res. 2254 24h | 200 ug/m3 | 0 |

La media anual del proyecto en Univalle ya supera el limite OMS (10 ug/m3) pero queda dentro del de Colombia (60 ug/m3). El 12,87% de excedencias horarias sobre el umbral OMS de 24h confirma episodios cronicos de exposicion.

### 1.3. Implicacion para el proyecto

Univalle es la unica estacion con NO2 en cualquier fuente accesible. Por lo tanto:

1. **No hay LOO-CV multi-estacion para NO2** (necesitas mas de una estacion para validar Kriging espacial). Esto rompe el plan original.
2. La unica salida limpia es la **extrapolacion via Sentinel-5P** ya autorizada por Cristian.
3. Si se intenta usar Univalle igualmente, el hueco de 367 dias (2024-12 a 2025-12) deja todo el periodo de validacion final del proyecto fuera de cobertura.
4. La estrategia LSTM bidireccional con ventana movil 6 meses (recomendada en Clase 35.1) puede llenar los huecos internos del periodo 2020-2024, pero no el corte de 2025.

## 2. SO2 - La Ermita

### 2.1. En el bucket

| Indicador | Valor |
|---|---|
| Mediciones bucket | 8.627 |
| Periodo cubierto | 2020-01-01 a 2022-10-25 |
| Cobertura | parcial, irregular, **se corta en oct-2022** |

**Cobertura por ano:**

| Ano | Mediciones | % cobertura |
|---|---|---|
| 2020 | 5.831 | 66,4% |
| 2021 | 686 | 7,8% |
| 2022 | 2.110 | 24,1% |
| 2023+ | 0 | 0% |

Es un dropout severo: en 2021 cae a 7,8% y desaparece tras 2022-10.

**Estadisticos descriptivos (bucket, ug/m3):**

| Estadistico | Valor |
|---|---|
| min | 0,00 |
| p25 | 0,94 |
| mediana | 3,19 |
| p75 | 4,90 |
| max | 16,03 |
| media | 3,27 |
| std | 2,69 |
| CV | 82,4% |
| Ceros | 1.701 (19,7%) |
| Casi-ceros (<0,5) | 1.944 (22,5%) |
| Outliers IQR | 84 (0,97%) |

**Excedencias normativas (bucket):**

| Norma | Umbral | Excedencias |
|---|---|---|
| OMS 2021 24h | 40 ug/m3 | 0 |
| Colombia 24h | 50 ug/m3 | 0 |
| Alerta horaria OMS | 125 ug/m3 | 0 |

El bucket nunca cruza 16 ug/m3 en SO2. Esto es internamente sospechoso: una estacion urbana de Cali sin un solo evento sobre 16 ug/m3 en 3 anos parece subreportada o saturada a la baja.

### 2.2. En el Excel

| Indicador | Valor |
|---|---|
| Mediciones validas | 43.597 |
| Cobertura sobre grilla 6 anos | 82,9% |
| Periodo cubierto | 2020-01 a 2025-11 |
| Mejor estacion para SO2 en el Excel | Ermita |

**Cobertura por ano:**

| Ano | Mediciones | % cobertura |
|---|---|---|
| 2020 | 5.689 | 64,8% |
| 2021 | 8.536 | 97,4% |
| 2022 | 8.347 | 95,3% |
| 2023 | 8.236 | 94,0% |
| 2024 | 6.111 | 69,6% |
| 2025 | 6.678 | 76,2% |

**Rachas de NA mas largas (Excel - Ermita SO2):**

| Duracion | Fecha inicio | Fecha fin | Observacion |
|---|---|---|---|
| 2.856 h (119 dias) | 2020-03-09 01:00 | 2020-07-06 01:00 | Coincide con cuarentena COVID-19 |
| 1.334 h (55,6 dias) | 2024-11-05 11:00 | 2024-12-31 01:00 | Caida fin de ano 2024 |
| 946 h (39,4 dias) | 2025-11-22 15:00 | 2026-01-01 00:00 | Caida fin de ano 2025 (patron estacional?) |
| 575 h (24 dias) | 2024-05-26 11:00 | 2024-06-19 10:00 | |
| 505 h (21 dias) | 2025-03-31 11:00 | 2025-04-21 12:00 | |
| 480 h (20 dias) | 2023-11-24 05:00 | 2023-12-14 05:00 | |
| 480 h (20 dias) | 2025-06-23 13:00 | 2025-07-13 13:00 | |

Total: 290 rachas. El hueco COVID 2020 es estructural; los huecos de fin de ano 2024/2025 sugieren mantenimiento programado o falla de calibracion anual.

**Estadisticos descriptivos (Excel, ug/m3):**

| Estadistico | Valor |
|---|---|
| min | 0,000 |
| p25 | 2,173 |
| mediana | 3,587 |
| p75 | 6,315 |
| p90 | 10,87 |
| p95 | 15,50 |
| p99 | 30,30 |
| p99,9 | 73,04 |
| max | **479,02** |
| media | 5,411 |
| std | 7,292 |
| CV | 134,8% |
| Ceros | 19 (0,04%) |
| Outliers IQR | 3.345 (7,67%) |

**Excedencias normativas (Excel):**

| Norma | Umbral | Excedencias |
|---|---|---|
| OMS 2021 24h | 40 ug/m3 | 206 (0,47%) |
| Colombia 24h | 50 ug/m3 | 117 (0,27%) |
| Alerta horaria OMS | 125 ug/m3 | 15 (0,03%) |

**Top valores extremos Excel Ermita SO2 (sospechosos):**

| Timestamp | Valor (ug/m3) |
|---|---|
| 2021-01-07 14:00 | 479,02 |
| 2021-01-19 08:00 | 379,89 |
| 2021-04-23 09:00 | 276,49 |
| 2021-05-03 08:00 | 212,61 |
| 2020-10-20 08:00 | 187,89 |
| 2021-04-12 10:00 | 169,77 |
| 2021-03-09 09:00 | 152,83 |

15 valores horarios sobre 125 ug/m3 son fisicamente plausibles bajo eventos extremos (incendios, refinerias, quema agricola del Valle del Cauca en marzo a abril), pero los 479 ug/m3 estan en el limite de lo creible. Validacion adicional con boletines DAGMA del trimestre 2021Q1 es necesaria.

### 2.3. Cruce bucket vs Excel - Ermita SO2

Pares disponibles (mismo timestamp en ambas fuentes): **6.738**.

| Estadistico | Bucket | Excel |
|---|---|---|
| Media | 2,97 | 7,94 |
| Mediana | 2,44 | 4,37 |

**Diferencia (bucket - excel):**

| Metrica | Valor |
|---|---|
| Media | -4,977 ug/m3 |
| Mediana | -2,383 ug/m3 |
| p25 | -7,539 |
| p75 | +0,051 |
| |diff| max | 140,1 |
| Pares con |diff| <= 1 ug/m3 | 17,6% |
| Pares con |diff| <= 5 ug/m3 | 61,7% |
| Pearson r | **0,0790** |

**Test de desfase horario** (descartar timezone como causa):

| Shift horas | Pearson r |
|---|---|
| -2 | 0,1006 |
| -1 | 0,1003 |
| 0 | 0,0790 |
| +1 | 0,0787 |
| +2 | 0,0660 |
| +3 | 0,0609 |

El maximo r es 0,10. No es un problema de timezone; las dos fuentes simplemente no coinciden.

**Patron de discrepancia:**

- En 1.604 casos (24%) el bucket reporta 0,00 pero el Excel tiene una media de 7,56 ug/m3.
- Los 10 pares con mayor desviacion estan todos en 2020 (julio a diciembre), con bucket cerca de 0 y Excel entre 89 y 140 ug/m3.
- Hipotesis: el bucket aplica un truncamiento bajo limite de deteccion (mapeo a 0) o sufre una falla de validacion mal etiquetada (el sensor con falla manda 0 en lugar de NA).

### 2.4. Implicaciones para SO2

1. **Excel es la fuente preferida** para SO2-Ermita en el proyecto: 5x mas mediciones, cobertura hasta 2025.
2. **Bucket inutilizable como ground truth de SO2**: subreporte sistematico, ceros artificiales, sin correlacion con Excel.
3. Si se quiere usar el bucket como complemento, hay que filtrar `bucket > 0` o `bucket > LOD` antes de cualquier comparacion.
4. Validar los 15 valores sobre 125 ug/m3 del Excel contra boletines DAGMA antes de incluirlos en el dataset de entrenamiento.
5. La Ermita SO2 tiene la mejor cobertura para SO2 en Cali; no hay sustituto local.

## 3. O3 - Pance

### 3.1. En el bucket

| Indicador | Valor |
|---|---|
| Mediciones bucket | 5.861 |
| Periodo cubierto | 2020-01-01 a 2022-10-27 |
| Cobertura | parcial, se corta en oct-2022 (igual que Ermita SO2) |

**Cobertura por ano:**

| Ano | Mediciones | % cobertura |
|---|---|---|
| 2020 | 3.492 | 39,8% |
| 2021 | 486 | 5,5% |
| 2022 | 1.883 | 21,5% |
| 2023+ | 0 | 0% |

**Estadisticos descriptivos (bucket, ug/m3):**

| Estadistico | Valor |
|---|---|
| min | 0,00 |
| p25 | 0,03 |
| mediana | 4,22 |
| p75 | 12,40 |
| max | 132,14 |
| media | 14,07 |
| std | 24,47 |
| CV | 174,0% |
| Ceros | 789 (13,5%) |
| Casi-ceros (<0,5) | 2.085 (35,6%) |
| Outliers IQR | 854 (14,57%) |

El bucket tiene 35,6% de mediciones casi-cero (<0,5 ug/m3) que probablemente representan limite de deteccion o fallos del sensor de O3 (notoriamente sensible a humedad e interferencias).

**Excedencias (bucket):**

| Norma | Umbral | Excedencias |
|---|---|---|
| OMS 2021 8h O3 | 100 ug/m3 | 81 (1,38%) |

### 3.2. En el Excel

| Indicador | Valor |
|---|---|
| Mediciones validas | 42.643 |
| Cobertura sobre grilla 6 anos | 81,1% |
| Periodo cubierto | 2020-01 a 2025-11 |

**Cobertura por ano:**

| Ano | Mediciones | % cobertura |
|---|---|---|
| 2020 | 6.823 | 77,7% |
| 2021 | 7.622 | 87,0% |
| 2022 | 7.232 | 82,6% |
| 2023 | 7.605 | 86,8% |
| 2024 | 7.057 | 80,3% |
| 2025 | 6.304 | 72,0% |

Pance es la serie de O3 con cobertura mas pareja del Excel: nunca baja del 72% en ningun ano.

**Estadisticos descriptivos (Excel, ug/m3):**

| Estadistico | Valor |
|---|---|
| min | 0,000 |
| p25 | 6,866 |
| mediana | 19,226 |
| p75 | 55,912 |
| max | 207,365 |
| media | 35,513 |
| std | 37,082 |
| CV | 104,4% |
| Ceros | 877 (2,06%) |
| Casi-ceros (<0,5) | 1.141 (2,68%) |
| Outliers IQR | 997 (2,34%) |

**Excedencias (Excel):**

| Norma | Umbral | Excedencias |
|---|---|---|
| OMS 2021 8h O3 | 100 ug/m3 | 3.566 (8,36%) |
| Umbral alerta horaria | 160 ug/m3 | 139 (0,33%) |

Pance es zona rural-forestal al sur de Cali; el alto numero de excedencias O3 es consistente con fotoquimica favorecida por radiacion solar alta y vegetacion (compuestos organicos volatiles biogenicos como precursores).

### 3.3. Cruce bucket vs Excel - Pance O3

Pares disponibles: **4.900**.

| Estadistico | Bucket | Excel |
|---|---|---|
| Media | 14,57 | 38,54 |
| Mediana | 4,47 | 20,99 |

**Diferencia (bucket - excel):**

| Metrica | Valor |
|---|---|
| Media | -23,969 ug/m3 |
| Mediana | -12,500 ug/m3 |
| p25 | -29,616 |
| p75 | -1,592 |
| |diff| max | 198,3 |
| Pares con |diff| <= 1 ug/m3 | 5,4% |
| Pares con |diff| <= 5 ug/m3 | 19,3% |
| Pearson r | **0,2924** |

**Test de desfase horario:**

| Shift horas | Pearson r |
|---|---|
| -2 | 0,1629 |
| -1 | 0,2393 |
| 0 | 0,2924 |
| +1 | **0,3043** |
| +2 | 0,2689 |
| +3 | 0,2016 |

El maximo r es 0,30 con shift +1h, lo que sugiere que **el bucket reporta el inicio del intervalo y el Excel el fin del intervalo**, pero aun con el shift optimo la correlacion sigue siendo baja.

**Patron de discrepancia:**

- 630 casos en que bucket = 0 mientras Excel reporta media 23,2 ug/m3.
- Los 10 pares mas divergentes estan todos en 2020 (jul a sep), con bucket cerca de 0 y Excel sobre 170 ug/m3.

### 3.4. Implicaciones para O3

1. **Excel es la unica fuente confiable** para O3-Pance: 7x mas mediciones, cobertura continua hasta 2025, valores fisicamente coherentes con zona forestal.
2. **Bucket sufre sub-deteccion sistematica**: 35,6% de las mediciones bucket son casi cero, contra 2,7% en el Excel. El sensor de O3 del bucket parece estar mal calibrado o el SISAIRE aplica un filtro mas agresivo.
3. El maximo del bucket (132 ug/m3) es muy inferior al maximo del Excel (207 ug/m3), reforzando la hipotesis de saturacion baja.
4. La diferencia de media (-24 ug/m3) es estadisticamente enorme: usar el bucket como ground truth subestimaria O3 troposferico en 60% para Pance.
5. Para LOO-CV se debe usar el Excel; el bucket solo sirve si se aplica un filtro `bucket > 1 ug/m3` y se reporta el sesgo.

## 4. Sintesis comparativa de las 3 series

### 4.1. Tabla maestra de cobertura

| Estacion-Variable | Fuente | N validas | % cobertura | Periodo | Mejor |
|---|---|---|---|---|---|
| Univalle NO2 | Bucket | 0 | 0% | nada | - |
| Univalle NO2 | Excel | 26.259 | 49,9% | 2020-01 a 2024-12 | **unica** |
| Ermita SO2 | Bucket | 8.627 | 16,4% | 2020-01 a 2022-10 | - |
| Ermita SO2 | Excel | 43.597 | 82,9% | 2020-01 a 2025-11 | **Excel** |
| Pance O3 | Bucket | 5.861 | 11,1% | 2020-01 a 2022-10 | - |
| Pance O3 | Excel | 42.643 | 81,1% | 2020-01 a 2025-11 | **Excel** |

### 4.2. Patron comun de discrepancia bucket vs Excel

1. **Bucket sub-reporta sistematicamente** (media bucket es 30-40% de la media Excel en SO2; 38% en O3).
2. **Bucket tiene exceso de ceros y casi-ceros**: 20-35% de las mediciones son <0,5 ug/m3, lo que sugiere mapeo de "<LOD" a 0 o fallo de sensor mal etiquetado.
3. **Bucket se corta en oct-2022**: 28 meses de datos contra 71 meses del Excel. Sin cobertura 2023-2025.
4. **Correlacion bucket-Excel baja** incluso con shift horario optimo (r=0,10 SO2, r=0,30 O3). No son la misma observacion validada.

### 4.3. Causa probable de la divergencia

El bucket viene del CKAN SISAIRE Valle del Cauca, que recibe datos "validados externamente" por IDEAM con un protocolo estricto (mas conservador, recorta valores dudosos a la baja). El Excel SVCASC_FT_50 es entrega DAGMA directa, sin pasar por el pipeline IDEAM. Resultado: Excel conserva la senal completa (incluyendo eventos extremos y horas problematicas) mientras el bucket aplica filtros adicionales.

Esto no significa que el Excel sea mas "correcto" en sentido absoluto. Significa que las dos fuentes representan distintos niveles de procesamiento, y la pregunta "cual es la verdad" depende del proposito:

- Para reconstruir series largas con maxima cobertura -> Excel.
- Para detectar valores quality-controlled por IDEAM -> bucket (cuando exista).
- Para LOO-CV del modelo Kriging -> usar Excel pero validar episodios extremos manualmente.

## 5. Acciones recomendadas

1. **Para NO2:** asumir Sentinel-5P como proxy principal (autorizado por Cristian). Usar Excel-Univalle solo como ancla puntual y nunca como ground truth multi-estacion.
2. **Para SO2 y O3:** declarar el Excel como fuente primaria y el bucket como auxiliar de control de calidad. Documentar el sesgo a la baja del bucket en la metodologia.
3. **Limpieza del Excel antes de modelar:**
   - Convertir `"NA"` a `NaN`.
   - Excluir valores > 99,9 percentil (probablemente errores de instrumentacion).
   - Validar los top-15 extremos contra boletines DAGMA del trimestre correspondiente.
   - Eliminar las rachas de NA mayores que 1 mes (no son imputables sin riesgo).
4. **Limpieza del bucket si se usa:**
   - Filtrar `med_concentracion_estandar > 0,1` para descartar LOD.
   - Aplicar shift +1h al timestamp para alinear con Excel (sugerido por test de correlacion en O3).
5. **Reportar las rachas de NA del Excel como limitaciones** en la seccion de metodologia: el modelo no puede generalizar a periodos que nunca observo (especialmente 2024-12 a 2025-12 para NO2).

## 6. Anexos reproducibles

### 6.1. Archivos intermedios generados

- `C:\Users\mitgar14\AppData\Local\Temp\bucket-dagma-full\bucket_cali_target.parquet` (72.919 filas, todas las observaciones bucket Cali NO2/SO2/O3)
- `C:\Users\mitgar14\AppData\Local\Temp\bucket-dagma-full\excel_target.parquet` (52.608 filas grilla horaria con Univalle_NO2, Ermita_SO2, Pance_O3)

### 6.2. Comandos clave

```powershell
# Descarga paralela 79 chunks
$dl = "C:\Users\mitgar14\AppData\Local\Temp\bucket-dagma-full"
az storage fs file list --account-name stanaliticafinal --file-system geovision --path "dagma/raw" --auth-mode login --query "[].name" -o tsv `
  | ForEach-Object -ThrottleLimit 8 -Parallel {
      $name = Split-Path $_ -Leaf
      az storage fs file download --account-name stanaliticafinal --file-system geovision `
        --path $_ --destination "$using:dl\$name" --auth-mode login --only-show-errors
    }
```

```python
# Pandas: extraccion eficiente de las 3 series
import pandas as pd
from pathlib import Path
files = sorted(Path("bucket-dagma-full").glob("g4t8_*.csv"))
big = pd.concat([
    pd.read_csv(f, low_memory=False,
                usecols=["nombre_fgda","nombre_est","msfl_code",
                         "med_concentracion_estandar","med_fecha_inicio",
                         "duraci_n","municipio","sigla_unidad"])
      .query("municipio == 'Santiago de Cali' and msfl_code in ['NO2','SO2','O3']")
    for f in files
], ignore_index=True)
big["ts"] = pd.to_datetime(big["med_fecha_inicio"], errors="coerce")
```

### 6.3. Limites de la auditoria

- Mediciones extremas del Excel (>99,9 percentil) **no han sido validadas** contra boletines DAGMA. Pendiente.
- Hipotesis del bucket mapeando "<LOD" a 0 no esta confirmada con metadata del proveedor SISAIRE. Pendiente: consultar documentacion oficial CVC.
- El test de shift horario solo se hizo con resolucion de 1 hora; no se exploraron desfases sub-horarios.
- No se cruzo con datos de Sentinel-5P, que es la siguiente etapa logica para NO2.
