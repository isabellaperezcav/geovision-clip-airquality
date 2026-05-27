# GeoVision-CLIP Cali - Frontend Next.js (imagen multi-stage)
# Stage 1: build con Bun (instala dependencias y compila la salida standalone).
FROM oven/bun:1 AS builder
WORKDIR /app

# La URL del backend es NEXT_PUBLIC_ (se hornea en build). Si se deja vacia, el
# frontend usa los artefactos estaticos en /public/data (datos reales igualmente).
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json bun.lock* ./
RUN bun install
COPY . .
RUN bun run build

# Stage 2: runtime minimo (el standalone de Next corre sobre Node).
FROM node:20-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
