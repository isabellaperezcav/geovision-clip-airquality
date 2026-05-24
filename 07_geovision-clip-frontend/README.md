# GeoVisionCLIP Cali · Frontend MVP

Panel interactivo de predicción de calidad del aire para Santiago de Cali. Forma parte del proyecto académico GeoVisionCLIP-Cali (UAO, Analítica). El backend con el modelo GRU/ConvLSTM aún no está integrado: este MVP usa datos mock con la geometría y semántica correctas para que el reemplazo posterior sea trivial.

## Stack

- Next.js 16 + React 19 + TypeScript + App Router + Turbopack
- Tailwind 4 con tokens propios (Geist-inspired)
- Geist Sans + Geist Mono (paquete `geist`)
- MapLibre GL JS 5 + react-map-gl 8 + deck.gl 9 (preparado para capas analíticas)
- shadcn/ui patterns + Radix primitives (Tooltip, Dialog, Tabs, Separator)
- Sonner para notificaciones, cmdk para Cmd+K
- Zustand para estado UI, next-themes para light/dark

## Quickstart

```bash
cd apps/web
bun install
bun run dev
```

Abre `http://localhost:3000`.

### Aviso Windows

Tailwind 4 (`@tailwindcss/node`) tiene un bug con rutas que contienen `#` en Windows: interpreta el carácter como null byte y aborta. Si el repo está en una ruta con `#`, crear un junction sin caracteres especiales y arrancar desde ahí:

```powershell
New-Item -ItemType Junction -Path C:\dev\geovision-web -Target <ruta-absoluta-a-apps\web>
Set-Location C:\dev\geovision-web
bun run dev
```

## Estructura

```
app/
  layout.tsx          Root layout (Geist fonts, providers)
  page.tsx            Mount del Dashboard
  globals.css         Tokens Geist + reset + estilos MapLibre
  api/
    predict/route.ts  Stub /predict por contaminante + horizonte
    validate/route.ts Stub /validate con métricas LOO-CV mock

components/
  dashboard.tsx       Layout principal (header + sidebar + tabs + status bar)
  header.tsx          Brand, búsqueda Cmd+K, theme toggle
  sidebar.tsx         Selectores y toggles de capas
  map/
    cali-map.tsx          Componente MapLibre (client-only)
    cali-map-dynamic.tsx  Wrapper next/dynamic con ssr:false
  legend.tsx          Leyenda colorimétrica
  status-bar.tsx      Coord, valor, σ en hover
  command-palette.tsx Cmd+K con cmdk
  validation-panel.tsx Tabla LOO-CV mock
  brand/
    logo.tsx, pollutant-icon.tsx, station-marker.tsx  SVGs propios
  ui/
    button.tsx, tooltip.tsx, separator.tsx, segmented.tsx, toggle-row.tsx

lib/
  domain.ts           Pollutants, horizontes, BBox, 9 estaciones DAGMA reales
  store.ts            Zustand
  utils.ts            cn, formatNumber, formatPlusMinus, relativeTime
  colors.ts           Helpers de escalas y opacidad por sigma
  map-style.ts        URLs Carto Positron (light/dark)

public/
  mock/               9 grids GeoJSON + stations + metadata
  geo/
    comunas-cali.geojson      22 comunas, WFS IDESC
    dagma-stations-wfs.geojson 9 estaciones reales, WFS dagma
```

## Datos

### Reales

- `public/geo/comunas-cali.geojson` (770 KB): 22 comunas, WFS IDESC `idesc:mc_comunas` con `srsName=EPSG:4326`. Última actualización del dataset oficial: 2026-03-25.
- `public/geo/dagma-stations-wfs.geojson` (3.5 KB): 9 estaciones con coordenadas, nombres, código, comuna y barrio. WFS `dagma:obs_aire_estaciones_monitoreo`.

### Mock

- `public/mock/grid_<pollutant>_<horizon>.geojson`: 9 grids (NO2/SO2/O3 × T+1/T+3/T+7), 2000 celdas a 0.005° sobre el BBox de Cali. Cada feature tiene `value` y `sigma`.
- `public/mock/stations.geojson` y `public/mock/metadata.json`.

Para regenerar (desde la raíz del repo):

```bash
uv run --with numpy scripts/frontend/generate_mock_predictions.py
```

Seed fija en 67 (regla del proyecto: nunca 42).

## Integración con el backend real

Cuando el backend FastAPI esté disponible:

1. Apuntar `app/api/predict/route.ts` al endpoint real (proxy server-side).
2. Apuntar `app/api/validate/route.ts` al endpoint real.
3. Mantener o no `public/mock/` como fallback offline.

El contrato del grid no debe cambiar: FeatureCollection con polígonos cuadrados y propiedades `value` y `sigma`. Si el backend produce raster (GeoTIFF, COG), agregar un adapter en `lib/api.ts`.

## Anti-tropes de IA aplicados

Ver `agent-docs/investigaciones/2026-05-23-frontend-design-y-apis-geograficas.md` para la lista completa y citas. Resumen:

- Geist Sans + Mono, letter-spacing negativo en headings. Tabular-nums en todo número.
- Paleta neutra (zinc) + acento semántico. Sin gradientes en UI funcional.
- border-radius 6-12 px. Sin `rounded-2xl` uniforme.
- Bordes en `rgba(0,0,0,0.08)` light / `rgba(255,255,255,0.08)` dark.
- Sidebar fija con divisores sutiles, sin top-nav genérico.
- Cmd+K desde el día 1.
- Animaciones solo `transform` + `opacity`, 100-300 ms, easings asimétricos.
- SVGs propios para identidad. Lucide solo para iconos genéricos.
- Cero emojis decorativos, cero glassmorphism, cero hero con 3 cards de features.
- Acento de color solo en estado (success/warning/danger).

## Próximos pasos

- Reemplazar stubs por backend FastAPI real cuando el GRU/ConvLSTM esté listo.
- Selector de fecha (no sólo horizonte relativo).
- Capa de incertidumbre con hatch pattern via `BitmapLayer` de deck.gl.
- Slider temporal animado entre T+1, T+3, T+7 (v0.2).
- Exportación GeoTIFF/CSV (vacío D07 del plan original, v0.2).
- Modalidad audio Whisper para input (+3 puntos bonus, vacío E01, v0.2).
