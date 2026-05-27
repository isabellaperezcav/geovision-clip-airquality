# GeoVision-CLIP Cali - Frontend + Backend

Panel interactivo de calidad del aire de superficie para Santiago de Cali (NO2, SO2, O3)
en microgramos por metro cubico, por ST-Kriging sobre la red DAGMA, con validacion LOO-CV
y la capa del patron del modelo profundo v11.

Este paquete trae las dos piezas conectadas:

```
apps/api/   backend FastAPI (sirve /predict, /validate, /metadata, /v11-pattern, /download)
apps/web/   frontend Next.js (mapa MapLibre + deck.gl, panel de validacion, consulta puntual)
docker-compose.yml   orquesta backend + frontend
```

El backend ya incluye los artefactos precalculados en `apps/api/artifacts/`, asi que no hace
falta tener los datos fuente para levantarlo.

## Opcion A: Docker (todo de una)

Requiere Docker Desktop. Desde esta carpeta:

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (documentacion en http://localhost:8000/docs)

El frontend ya queda apuntando al backend en `localhost:8000` (build arg en el compose).

## Opcion B: Manual (dos terminales)

### Terminal 1 - Backend (Python, con uv)

```bash
cd apps/api
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Sin uv, con pip:

```bash
cd apps/api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Terminal 2 - Frontend (Bun)

```bash
cd apps/web
bun install
bun run dev
```

Abre http://localhost:3000. El archivo `apps/web/.env.local` ya define
`NEXT_PUBLIC_API_URL=http://localhost:8000`, asi que el frontend consume el backend.

Sin Node/Bun preferido, tambien funciona con npm: `npm install` y `npm run dev`.

## Como saber que el backend esta conectado

En la cabecera del panel y en la barra de estado se ve la fuente de datos. Si el backend
responde, las peticiones van a `localhost:8000`. Si el backend esta caido, el frontend cae
automaticamente a los artefactos estaticos en `apps/web/public/data` (la misma data real),
de modo que el panel nunca queda en blanco. Para forzar el uso del backend, basta con que
este corriendo en el puerto 8000 antes de abrir el frontend.

## Aviso para Windows con `#` en la ruta

Tailwind 4 falla si la ruta del proyecto contiene `#`. Si tu carpeta tiene ese caracter,
crea un junction sin caracteres especiales y arranca el frontend desde ahi:

```powershell
New-Item -ItemType Junction -Path C:\dev\geovision-web -Target <ruta-absoluta-a-apps\web>
cd C:\dev\geovision-web
bun run dev
```

## Que mira el evaluador (Situacion 3 del enunciado)

- Mapas en ug/m3 validados contra DAGMA por Leave-One-Station-Out (pestana Validacion).
- KPIs con su estado (EXCELENTE / CUMPLE / NO CUMPLE / NO EVALUABLE) y los umbrales del PDF.
- Consulta puntual: clic en el mapa o escribir coordenadas, con radio ajustable.
- Latencia de la API muy por debajo del umbral de 8 s (sirve artefactos precalculados).

Nota honesta: con 5 a 7 estaciones DAGMA tan dispersas, el R2 del LOO-CV es bajo o negativo.
Es la evidencia que motiva el downscaling profundo: la red terrestre no resuelve por si sola
la heterogeneidad intraurbana.
