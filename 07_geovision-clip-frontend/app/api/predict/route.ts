import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";
import { POLLUTANTS, HORIZONS, type Horizon, type Pollutant } from "@/lib/domain";

// MVP stub: lee el GeoJSON precalculado y lo devuelve.
// Reemplazar por la llamada al backend FastAPI /predict cuando esté disponible.

const POLLUTANT_SET = new Set<string>(POLLUTANTS);
const HORIZON_SET = new Set<string>(HORIZONS);

export const dynamic = "force-static";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const pollutant = (url.searchParams.get("pollutant") ?? "NO2") as Pollutant;
  const horizon = (url.searchParams.get("horizon") ?? "T+1") as Horizon;

  if (!POLLUTANT_SET.has(pollutant)) {
    return NextResponse.json(
      { error: `pollutant invalido. usar uno de ${[...POLLUTANT_SET].join(", ")}` },
      { status: 400 },
    );
  }
  if (!HORIZON_SET.has(horizon)) {
    return NextResponse.json(
      { error: `horizon invalido. usar uno de ${[...HORIZON_SET].join(", ")}` },
      { status: 400 },
    );
  }

  const slug = `grid_${pollutant.toLowerCase()}_${horizon.replace("+", "").toLowerCase()}.geojson`;
  const filePath = path.join(process.cwd(), "public", "mock", slug);
  try {
    const data = await fs.readFile(filePath, "utf8");
    return new NextResponse(data, {
      headers: {
        "content-type": "application/geo+json",
        "cache-control": "public, max-age=60",
        "x-data-source": "mock",
      },
    });
  } catch {
    return NextResponse.json(
      { error: `no se encontro la prediccion ${slug}` },
      { status: 404 },
    );
  }
}
