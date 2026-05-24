# GeoVisionCLIP Cali · Frontend MVP

Panel interactivo de predicción de calidad del aire para Santiago de Cali. Next.js 16 + React 19 + Tailwind 3 + MapLibre GL JS. Backend de modelo aún no integrado: este MVP usa datos mock con la geometría correcta y reemplazables.

## Requisitos

- **Bun 1.3+** (recomendado): https://bun.com/docs/installation
  - Windows PowerShell: `powershell -c "irm bun.com/install.ps1 | iex"`
  - macOS / Linux: `curl -fsSL https://bun.com/install | bash`
- O **Node.js 20+** + npm/pnpm si no quieres Bun.

## Quickstart

Descomprime el ZIP. Desde una terminal en la carpeta resultante:

```bash
bun install
bun run dev
```

Abre `http://localhost:3000`.

### Con npm en lugar de Bun

```bash
npm install
npm run dev
```

### Con pnpm

```bash
pnpm install
pnpm run dev
```

## Aviso para Windows

Tailwind 3 funciona bien en cualquier ruta. Pero si decides actualizar a Tailwind 4 a futuro y tu ruta contiene `#`, el módulo `@tailwindcss/node` interpreta `#` como null byte y aborta. La solución es crear un junction a una ruta corta:

```powershell
New-Item -ItemType Junction -Path C:\dev\geovision-web -Target <ruta-absoluta-al-proyecto>
Set-Location C:\dev\geovision-web
bun run dev
```

Esto ya está aplicado en este MVP.

## Qué incluye

- 22 comunas reales de Cali (descargadas del WFS oficial de IDESC).
- 9 estaciones DAGMA reales con coordenadas oficiales.
- 9 grids de predicción mock (NO2 / SO2 / O3 × T+1 / T+3 / T+7) sobre el BBox `[-76.60, 3.30, -76.40, 3.55]`.
- Tab Predicción con mapa MapLibre, leyenda de color, capa de incertidumbre, tooltips por celda.
- Tab Validación con tabla LOO-CV mock por estación (RMSE, MAE, R², bias).
- Command palette Cmd+K / Ctrl+K.
- Modo claro y oscuro con basemap diferenciado (Carto Positron / Dark Matter).

## Estructura

```
app/
  layout.tsx, page.tsx, globals.css
  api/predict/route.ts   stub /api/predict reemplazable
  api/validate/route.ts  stub /api/validate reemplazable
components/
  dashboard.tsx, header.tsx, sidebar.tsx,
  legend.tsx, status-bar.tsx, command-palette.tsx,
  validation-panel.tsx, theme-toggle.tsx, providers.tsx,
  map/                   componente MapLibre (client-only)
  brand/                 SVGs propios (logo, moléculas, marker)
  ui/                    Button, Tooltip, Separator, Segmented, ToggleRow
lib/
  domain.ts, store.ts, utils.ts, colors.ts, map-style.ts
public/
  geo/                   GeoJSON reales (IDESC + DAGMA WFS)
  mock/                  9 grids de predicción + metadata
```

## Integrar el modelo real (cuando esté disponible)

1. Editar `app/api/predict/route.ts` para que haga proxy server-side al endpoint FastAPI real (mantener el mismo shape de respuesta: FeatureCollection con `value` y `sigma` por celda).
2. Editar `app/api/validate/route.ts` igual: que devuelva métricas LOO-CV por estación.
3. Opcionalmente eliminar `public/mock/` cuando el backend ya esté estable.

El frontend no necesita más cambios: los selectores, la leyenda y los tooltips ya consumen el mismo contrato.

## Stack y decisiones de diseño

- Next.js 16 App Router con Turbopack.
- Tailwind 3.4 con tokens propios inspirados en Geist.
- Geist Sans + Geist Mono via paquete `geist`.
- MapLibre GL JS 5 + react-map-gl 8 + deck.gl 9 (deck.gl preparado para hatch pattern de incertidumbre, no usado aún).
- shadcn patterns + Radix primitives (Tooltip, Dialog, Tabs, Separator).
- Carto Positron / Dark Matter como basemap (sin token, sin registro).
- IDESC Cali GeoServer WFS para datos administrativos y estaciones.

## Anti-tropes de IA aplicados

- Geist Sans + Mono con `tabular-nums`. Sin Inter.
- Paleta zinc neutra + acentos semánticos. Sin gradientes.
- Bordes en `rgba(0,0,0,0.08)` light / `rgba(255,255,255,0.08)` dark.
- border-radius 6-12 px. Sin `rounded-2xl` uniforme.
- SVGs propios para identidad (logo, moléculas NO2/SO2/O3, marker).
- Lucide para iconos genéricos (sun, moon, search, code).
- Cero emojis decorativos, cero glassmorphism, cero hero con 3 cards.
- Microinteracciones solo `transform` + `opacity`, 100-300 ms, easings asimétricos.

## Comandos disponibles

```bash
bun run dev      # dev con HMR
bun run build    # build de producción
bun run start    # servir el build
bun run lint     # ESLint
```

## Variables de entorno

Ninguna. El MVP es 100% self-contained. Cuando integres el backend real, podrías agregar `BACKEND_URL` en `.env.local` y leerla desde los route handlers de `app/api/`.

## Licencia

Proyecto académico UAO, Analítica, Semestre 7. Sin licencia comercial.
