import { NextResponse } from "next/server";
import { DAGMA_STATIONS, POLLUTANTS, POLLUTANT_META } from "@/lib/domain";

// MVP stub: metricas LOO-CV sinteticas.
// Reemplazar por backend FastAPI /validate cuando el modelo este entrenado y validado.

export const dynamic = "force-dynamic";

function pseudoRandom(seed: string) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return () => {
    h ^= h << 13;
    h ^= h >>> 17;
    h ^= h << 5;
    return ((h >>> 0) % 1_000_000) / 1_000_000;
  };
}

export async function GET() {
  const stations = DAGMA_STATIONS.map((station) => {
    const rng = pseudoRandom(`${station.id}-67`);
    const metrics: Record<string, unknown> = {};
    for (const pollutant of POLLUTANTS) {
      if (!station.variables.includes(pollutant)) continue;
      const baseline = POLLUTANT_META[pollutant].safeThreshold;
      const rmse = baseline * (0.06 + rng() * 0.12);
      const mae = rmse * (0.65 + rng() * 0.15);
      const r2 = 0.6 + rng() * 0.32;
      const bias = baseline * (rng() - 0.5) * 0.05;
      const n = 280 + Math.floor(rng() * 90);
      metrics[pollutant] = {
        rmse: round(rmse, 4),
        mae: round(mae, 4),
        r2: round(r2, 4),
        bias: round(bias, 4),
        n,
      };
    }
    return { id: station.id, name: station.name, zone: station.zone, metrics };
  });

  return NextResponse.json({
    method: "LOO-CV",
    modelVersion: "mvp-0.1-mock",
    generatedAt: new Date().toISOString(),
    stations,
  });
}

function round(x: number, digits: number) {
  const p = 10 ** digits;
  return Math.round(x * p) / p;
}
