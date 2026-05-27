"use client";

import { POLLUTANT_META, type Pollutant } from "@/lib/domain";
import { formatNumber } from "@/lib/utils";

export function Legend({
  pollutant,
  valueRange,
}: {
  pollutant: Pollutant;
  valueRange: [number, number];
}) {
  const meta = POLLUTANT_META[pollutant];
  const [vmin, vmax] = valueRange;
  const digits = 1;
  return (
    <div className="pointer-events-auto inline-flex flex-col gap-1.5 rounded-[8px] border border-[var(--border-strong)] bg-[var(--surface-1)] px-3 py-2.5 shadow-[var(--shadow-elevation-2)] backdrop-blur-md">
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--foreground)]">
          {meta.fullName}
        </span>
        <span className="font-mono text-[10px] text-[var(--muted-foreground)]">{meta.unit}</span>
      </div>
      <div
        className="h-2 w-44 rounded-[3px] ring-1 ring-[var(--border-subtle)]"
        style={{
          background: `linear-gradient(to right, ${meta.colorScale.join(", ")})`,
        }}
      />
      <div className="flex items-baseline justify-between font-mono text-[10px] font-semibold tabular-nums text-[var(--foreground)]">
        <span>{formatNumber(vmin, digits)}</span>
        <span className="text-[var(--muted-foreground)]">{formatNumber((vmin + vmax) / 2, digits)}</span>
        <span>{formatNumber(vmax, digits)}</span>
      </div>
    </div>
  );
}
