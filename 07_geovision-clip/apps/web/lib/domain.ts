export const POLLUTANTS = ["NO2", "SO2", "O3"] as const;
export type Pollutant = (typeof POLLUTANTS)[number];

export const HORIZONS = ["T+1", "T+3", "T+7"] as const;
export type Horizon = (typeof HORIZONS)[number];

// El modelo predice CONCENTRACION SUPERFICIAL en ug/m3 (target del enunciado oficial,
// validado contra estaciones DAGMA por LOO-CV), no la columna troposferica satelital.
// safeThreshold: nivel maximo de referencia segun Resolucion 2254 de 2017 (Colombia).
// looRmse: rango [excelente, minimo aceptable] del RMSE LOO-CV objetivo por contaminante (KPIs Situacion 3).
export const POLLUTANT_META: Record<
  Pollutant,
  {
    label: string;
    unit: string;
    fullName: string;
    safeThreshold: number;
    looRmse: readonly [number, number];
    colorScale: readonly [string, string, string, string, string];
  }
> = {
  NO2: {
    label: "NO₂",
    unit: "μg/m³",
    fullName: "Dióxido de nitrógeno",
    safeThreshold: 60,
    looRmse: [4, 8],
    colorScale: ["#e0f2fe", "#7dd3fc", "#0284c7", "#1e3a8a", "#0f172a"],
  },
  SO2: {
    label: "SO₂",
    unit: "μg/m³",
    fullName: "Dióxido de azufre",
    safeThreshold: 50,
    looRmse: [3, 6],
    colorScale: ["#fef3c7", "#fcd34d", "#d97706", "#92400e", "#451a03"],
  },
  O3: {
    label: "O₃",
    unit: "μg/m³",
    fullName: "Ozono total",
    safeThreshold: 100,
    looRmse: [6, 12],
    colorScale: ["#f0fdf4", "#86efac", "#16a34a", "#166534", "#052e16"],
  },
};

export const HORIZON_META: Record<Horizon, { label: string; days: number; description: string }> = {
  "T+1": { label: "T+1", days: 1, description: "Predicción a 1 día" },
  "T+3": { label: "T+3", days: 3, description: "Predicción a 3 días" },
  "T+7": { label: "T+7", days: 7, description: "Predicción a 7 días" },
};

export const BBOX = {
  xmin: -76.6,
  ymin: 3.3,
  xmax: -76.4,
  ymax: 3.55,
} as const;

export const CALI_CENTER: [number, number] = [
  (BBOX.xmin + BBOX.xmax) / 2,
  (BBOX.ymin + BBOX.ymax) / 2,
];

export type DagmaStation = {
  id: string;
  name: string;
  zone: string;
  coordinates: [number, number];
  variables: Pollutant[];
  coverage: number;
};

// Coordenadas y nombres oficiales del WFS de IDESC dagma:obs_aire_estaciones_monitoreo.
export const DAGMA_STATIONS: DagmaStation[] = [
  {
    id: "base-aerea",
    name: "Base Aérea Marco Fidel Suárez",
    zone: "Comuna 7",
    coordinates: [-76.50653649, 3.45731978],
    variables: ["NO2", "SO2", "O3"],
    coverage: 0.91,
  },
  {
    id: "era-obrero",
    name: "ERA Obrero",
    zone: "Comuna 9",
    coordinates: [-76.51908184, 3.4475941],
    variables: ["NO2", "SO2"],
    coverage: 0.79,
  },
  {
    id: "canaveralejo",
    name: "Cañaveralejo",
    zone: "Comuna 19",
    coordinates: [-76.54961789, 3.41545841],
    variables: ["NO2", "O3"],
    coverage: 0.74,
  },
  {
    id: "univalle",
    name: "Universidad del Valle",
    zone: "Comuna 17",
    coordinates: [-76.53372474, 3.37796681],
    variables: ["NO2", "SO2", "O3"],
    coverage: 0.93,
  },
  {
    id: "pance",
    name: "Pance",
    zone: "Comuna 53",
    coordinates: [-76.53125401, 3.30449556],
    variables: ["O3"],
    coverage: 0.62,
  },
  {
    id: "transitoria",
    name: "Estación Transitoria EDB Navarro",
    zone: "Comuna 13",
    coordinates: [-76.49495633, 3.41717874],
    variables: ["NO2", "SO2"],
    coverage: 0.58,
  },
  {
    id: "compartir",
    name: "Compartir",
    zone: "Comuna 21",
    coordinates: [-76.46657547, 3.42825808],
    variables: ["NO2", "O3"],
    coverage: 0.79,
  },
  {
    id: "flora",
    name: "La Flora",
    zone: "Comuna 2",
    coordinates: [-76.51805771, 3.48822548],
    variables: ["NO2", "SO2", "O3"],
    coverage: 0.88,
  },
  {
    id: "ermita",
    name: "La Ermita",
    zone: "Comuna 3",
    coordinates: [-76.53097834, 3.45551754],
    variables: ["NO2", "SO2"],
    coverage: 0.66,
  },
];

export type PredictionCell = {
  bbox: [number, number, number, number];
  value: number;
  sigma: number;
};

export type PredictionGrid = {
  pollutant: Pollutant;
  horizon: Horizon;
  generatedAt: string;
  modelVersion: string;
  cellsPerDeg: number;
  cells: PredictionCell[];
};
