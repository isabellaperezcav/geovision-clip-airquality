import type { Horizon, Pollutant } from "./domain";

// Cliente de datos del frontend.
// Si NEXT_PUBLIC_API_URL apunta al backend FastAPI, se consume ese servicio
// (endpoints /predict, /validate, /metadata, /v11-pattern). Si no esta definido
// o el backend no responde, cae a los artefactos estaticos servidos desde /data
// (copia precalculada de apps/api/artifacts). Ambos contienen los mismos datos
// reales: ST-Kriging sobre DAGMA en ug/m3 mas la capa del modelo profundo v11.

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
const STATIC_BASE = "/data";

export const API_INFO = {
  base: API_BASE || `${STATIC_BASE} (estatico)`,
  usingBackend: Boolean(API_BASE),
};

function horizonSlug(h: Horizon): string {
  return h.replace("+", "").toLowerCase(); // "T+1" -> "t1"
}

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return (await r.json()) as T;
}

async function withFallback<T>(remote: string | null, staticUrl: string): Promise<T> {
  if (remote) {
    try {
      return await getJson<T>(remote);
    } catch {
      // backend no disponible: se usa el artefacto estatico
    }
  }
  return getJson<T>(staticUrl);
}

export type GridFeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Polygon,
  { value: number; sigma: number }
> & {
  properties?: { valueMin: number; valueMax: number; sigmaMin: number; sigmaMax: number };
};

export type StationMetric = {
  rmse: number | null;
  mae: number | null;
  r2: number | null;
  bias: number | null;
  n: number;
};

export type KpiGrade = "EXCELENTE" | "CUMPLE" | "NO_CUMPLE" | "NO_EVALUABLE";

export type KpiEntry = {
  value: number | null;
  grade: KpiGrade;
  thresholds?: Record<string, number>;
  [key: string]: unknown;
};

export type ValidationKpis = {
  r2_loo_avg?: KpiEntry & { gases_evaluables: string[]; gases_excluidos: string[] };
  moran_i?: KpiEntry & { min_I: number | null; max_p: number | null; n_pass: number; n_total: number };
  rmse_t1?: Record<string, KpiEntry & { reason?: string }>;
  degradacion_ratio?: KpiEntry & { gases: string[] };
};

export type ValidationResponse = {
  method: string;
  modelVersion: string;
  generatedAt: string;
  summary: Record<string, StationMetric & { metodo?: string }>;
  stations: Array<{
    id: string;
    name: string;
    zone: string;
    metrics: Record<string, StationMetric>;
  }>;
  kpis?: ValidationKpis;
};

export type PointQueryResult = {
  pollutant: string;
  horizon: string;
  units: string;
  query: { lat: number; lon: number; radio_km: number };
  point: { value: number; sigma: number; dist_km: number } | null;
  n_celdas: number;
};

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = 6371.0;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dphi = toRad(lat2 - lat1);
  const dlmb = toRad(lon2 - lon1);
  const a =
    Math.sin(dphi / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dlmb / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

function cellCenter(feature: GeoJSON.Feature<GeoJSON.Polygon>): [number, number] {
  const ring = feature.geometry.coordinates[0].slice(0, 4);
  const lon = ring.reduce((s, p) => s + p[0], 0) / 4;
  const lat = ring.reduce((s, p) => s + p[1], 0) / 4;
  return [lon, lat];
}

// Consulta puntual estilo POST /predict, pero calculada en el cliente sobre el grid
// estatico. Permite que el campo de coordenadas funcione sin backend.
function pointFromGrid(
  grid: GridFeatureCollection,
  lat: number,
  lon: number,
  radio_km: number,
  contaminante: string,
  horizonte: string,
): PointQueryResult {
  let best: { value: number; sigma: number } | null = null;
  let bestD = Infinity;
  let nDentro = 0;
  for (const f of grid.features) {
    const [clon, clat] = cellCenter(f as GeoJSON.Feature<GeoJSON.Polygon>);
    const d = haversineKm(lat, lon, clat, clon);
    if (d <= radio_km) nDentro++;
    if (d < bestD) {
      bestD = d;
      best = { value: f.properties.value, sigma: f.properties.sigma };
    }
  }
  return {
    pollutant: contaminante,
    horizon: horizonte,
    units: "ug/m3",
    query: { lat, lon, radio_km },
    point: best ? { value: best.value, sigma: best.sigma, dist_km: Number(bestD.toFixed(3)) } : null,
    n_celdas: nDentro,
  };
}

export async function postPredict(
  lat: number,
  lon: number,
  radio_km: number,
  contaminante: string,
  horizonte: string,
): Promise<PointQueryResult | null> {
  if (API_BASE) {
    try {
      const r = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ lat, lon, radio_km, contaminante, horizonte }),
      });
      if (r.ok) return (await r.json()) as PointQueryResult;
    } catch {
      // backend no disponible: se calcula en el cliente con el grid estatico
    }
  }
  try {
    const grid = await getGrid(contaminante as Pollutant, horizonte as Horizon);
    return pointFromGrid(grid, lat, lon, radio_km, contaminante, horizonte);
  } catch {
    return null;
  }
}

export type MetadataResponse = {
  generatedAt: string;
  modelVersion: string;
  units: string;
  bbox: { xmin: number; ymin: number; xmax: number; ymax: number };
  cellDeg: number;
  gridShape: [number, number];
  moran?: Record<string, { I: number; p: number } | null>;
  files: Array<{ pollutant: string; horizon: string; valueRange: [number, number] }>;
};

export function getGrid(pollutant: Pollutant, horizon: Horizon) {
  const remote = API_BASE
    ? `${API_BASE}/predict?pollutant=${pollutant}&horizon=${encodeURIComponent(horizon)}`
    : null;
  const stat = `${STATIC_BASE}/grid_${pollutant.toLowerCase()}_${horizonSlug(horizon)}.geojson`;
  return withFallback<GridFeatureCollection>(remote, stat);
}

export function getMetadata() {
  return withFallback<MetadataResponse>(
    API_BASE ? `${API_BASE}/metadata` : null,
    `${STATIC_BASE}/metadata.json`,
  );
}

export function getValidation() {
  return withFallback<ValidationResponse>(
    API_BASE ? `${API_BASE}/validate` : null,
    `${STATIC_BASE}/validate.json`,
  );
}

export function getV11Pattern(pollutant: Pollutant) {
  const remote = API_BASE ? `${API_BASE}/v11-pattern?pollutant=${pollutant}` : null;
  return withFallback<GeoJSON.FeatureCollection>(
    remote,
    `${STATIC_BASE}/v11_pattern_${pollutant.toLowerCase()}.geojson`,
  );
}
