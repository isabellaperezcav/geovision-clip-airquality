# GeoVisionCLIP Cali · Frontend

Panel interactivo de predicción de calidad del aire de superficie para Santiago de Cali.
Forma parte del proyecto académico GeoVisionCLIP-Cali (UAO, Analítica). Consume el backend
FastAPI (`apps/api`): mapas en ug/m3 por ST-Kriging sobre la red DAGMA, validación LOO-CV y
la capa del patrón del modelo profundo v11. Si el backend no está disponible, cae a los
artefactos estáticos en `public/data` (la misma data real).

## Stack

- Next.js 16 + React 19 + TypeScript + App Router + Turbopack
- Tailwind 4 con tokens propios (Geist-inspired)
- Geist Sans + Geist Mono (paquete `geist`)
- MapLibre GL JS 5 + react-map-gl 8 + deck.gl 9
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

Para consumir el backend real, levantarlo en paralelo (ver `apps/api/README.md`) y definir
`NEXT_PUBLIC_API_URL` en `.env.local` (ya viene como `http://localhost:8000`). Sin esa
variable o con el backend caído, el panel usa `public/data` y funciona igual.

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

components/
  dashboard.tsx       Layout principal (header + sidebar + tabs + status bar)
  header.tsx          Brand, búsqueda Cmd+K, theme toggle
  sidebar.tsx         Selectores, toggles de capas (incluye patrón v11)
  map/
    cali-map.tsx          Componente MapLibre (grid + estaciones + comunas + patrón v11)
    cali-map-dynamic.tsx  Wrapper next/dynamic con ssr:false
  legend.tsx          Leyenda colorimétrica
  status-bar.tsx      Coord, valor, sigma en hover
  command-palette.tsx Cmd+K con cmdk
  validation-panel.tsx Tabla LOO-CV real (consume /validate)

lib/
  api.ts              Cliente de datos: backend FastAPI o fallback estático /data
  domain.ts           Pollutants, horizontes, BBox, 9 estaciones DAGMA reales
  store.ts            Zustand
  utils.ts            cn, formatNumber, formatPlusMinus, relativeTime
  colors.ts           Helpers de escalas y opacidad por sigma
  map-style.ts        URLs Carto Positron (light/dark)

public/
  data/               9 grids GeoJSON + 3 capas v11 + metadata.json + validate.json
                      (copia de apps/api/artifacts; fallback cuando no hay backend)
  geo/
    comunas-cali.geojson      22 comunas, WFS IDESC
    dagma-stations-wfs.geojson 9 estaciones reales, WFS dagma
```

## Datos

### Geográficos reales

- `public/geo/comunas-cali.geojson` (770 KB): 22 comunas, WFS IDESC `idesc:mc_comunas`, EPSG:4326.
- `public/geo/dagma-stations-wfs.geojson` (3.5 KB): 9 estaciones con coordenadas, código, comuna y barrio. WFS `dagma:obs_aire_estaciones_monitoreo`.

### Producto del modelo

- `public/data/grid_<pollutant>_<horizon>.geojson`: 9 superficies (NO2/SO2/O3 por T+1/T+3/T+7), 2000 celdas a 0.005 grados sobre el BBox de Cali, con `value` y `sigma` en ug/m3.
- `public/data/v11_pattern_<pollutant>.geojson`: patrón espacial del modelo profundo v11 (capa overlay).
- `public/data/metadata.json` y `public/data/validate.json`.

Estos archivos los genera `apps/api/build_artifacts.py`. Para regenerarlos y recopiarlos:

```powershell
uv run --project apps/api python apps/api/build_artifacts.py
Copy-Item apps/api/artifacts/* apps/web/public/data/ -Force
```

## Integración con el backend

`lib/api.ts` resuelve cada petición así: si `NEXT_PUBLIC_API_URL` está definido, llama al
backend FastAPI (`/predict`, `/validate`, `/metadata`, `/v11-pattern`); si falla o no está
definido, usa `public/data`. El contrato del grid es FeatureCollection de polígonos con
`value` y `sigma`, idéntico en ambas rutas.

## Docker

```bash
# Desde la raíz del repo (backend + frontend)
docker compose up --build
```

`output: "standalone"` en `next.config.ts` produce la salida autocontenida que copia el
Dockerfile multi-stage. `NEXT_PUBLIC_API_URL` se pasa como build arg.

## Anti-tropes de IA aplicados

- Geist Sans + Mono, letter-spacing negativo en headings. Tabular-nums en todo número.
- Paleta neutra (zinc) + acento semántico. Sin gradientes en UI funcional.
- border-radius 6-12 px. Sin `rounded-2xl` uniforme.
- Bordes en `rgba(0,0,0,0.08)` light / `rgba(255,255,255,0.08)` dark.
- Sidebar fija con divisores sutiles, sin top-nav genérico.
- Cmd+K desde el día 1.
- Animaciones solo `transform` + `opacity`, 100-300 ms, easings asimétricos.
- SVGs propios para identidad. Lucide solo para iconos genéricos.
- Cero emojis decorativos, cero glassmorphism.
- Acento de color solo en estado (success/warning/danger).

## Próximos pasos

- Selector de fecha absoluta (no solo horizonte relativo).
- Slider temporal animado entre T+1, T+3, T+7.
- Consulta puntual por click en el mapa (POST /predict con radio).
