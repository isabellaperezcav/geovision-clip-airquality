"use client";

import dynamic from "next/dynamic";
import type { Horizon, Pollutant } from "@/lib/domain";

const CaliMap = dynamic(() => import("./cali-map").then((m) => m.CaliMap), {
  ssr: false,
  loading: () => <MapSkeleton />,
});

export function CaliMapDynamic({
  pollutant,
  horizon,
}: {
  pollutant: Pollutant;
  horizon: Horizon;
}) {
  return <CaliMap pollutant={pollutant} horizon={horizon} />;
}

function MapSkeleton() {
  return (
    <div className="absolute inset-0 bg-[var(--surface-1)]">
      <div className="absolute inset-0 grid grid-cols-12 grid-rows-12 gap-px opacity-30">
        {Array.from({ length: 144 }).map((_, i) => (
          <div key={i} className="bg-[var(--surface-2)]" />
        ))}
      </div>
      <div className="absolute bottom-4 left-4 font-mono text-[11px] text-[var(--muted)]">
        cargando basemap...
      </div>
    </div>
  );
}
