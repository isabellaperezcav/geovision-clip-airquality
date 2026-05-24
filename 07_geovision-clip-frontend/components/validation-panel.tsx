"use client";

import { DAGMA_STATIONS, POLLUTANT_META, POLLUTANTS } from "@/lib/domain";
import { usePanelStore } from "@/lib/store";
import { formatNumber } from "@/lib/utils";
import { useMemo } from "react";

type StationMetric = {
  rmse: number;
  mae: number;
  r2: number;
  bias: number;
  n: number;
};

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

function buildMockMetrics(): Record<string, Record<string, StationMetric>> {
  const out: Record<string, Record<string, StationMetric>> = {};
  for (const station of DAGMA_STATIONS) {
    out[station.id] = {};
    const rng = pseudoRandom(`${station.id}-67`);
    for (const pollutant of POLLUTANTS) {
      if (!station.variables.includes(pollutant)) continue;
      const baseline = POLLUTANT_META[pollutant].safeThreshold;
      const rmse = baseline * (0.06 + rng() * 0.12);
      const mae = rmse * (0.65 + rng() * 0.15);
      const r2 = 0.6 + rng() * 0.32;
      const bias = baseline * (rng() - 0.5) * 0.05;
      const n = 280 + Math.floor(rng() * 90);
      out[station.id][pollutant] = { rmse, mae, r2, bias, n };
    }
  }
  return out;
}

export function ValidationPanel() {
  const pollutant = usePanelStore((s) => s.pollutant);
  const meta = POLLUTANT_META[pollutant];
  const metrics = useMemo(buildMockMetrics, []);
  const digits = pollutant === "SO2" ? 3 : 2;

  const rows = DAGMA_STATIONS.filter((s) => s.variables.includes(pollutant)).map(
    (station) => {
      const m = metrics[station.id]?.[pollutant];
      return { station, m };
    },
  );

  const aggregated = rows.reduce(
    (acc, { m }) => {
      if (!m) return acc;
      acc.rmse += m.rmse;
      acc.mae += m.mae;
      acc.r2 += m.r2;
      acc.bias += m.bias;
      acc.n += 1;
      return acc;
    },
    { rmse: 0, mae: 0, r2: 0, bias: 0, n: 0 },
  );

  if (aggregated.n > 0) {
    aggregated.rmse /= aggregated.n;
    aggregated.mae /= aggregated.n;
    aggregated.r2 /= aggregated.n;
    aggregated.bias /= aggregated.n;
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <header className="flex items-baseline justify-between">
        <h2 className="text-[13px] font-semibold text-[var(--foreground)]">
          Validación LOO-CV · {meta.label}
        </h2>
        <span className="font-mono text-[10px] text-[var(--muted)]">
          mock · reemplazar por /api/validate
        </span>
      </header>

      <p className="font-mono text-[11px] leading-relaxed text-[var(--muted)]">
        Métricas por estación dejada fuera (leave-one-out). RMSE y MAE en {meta.unit}; R² adimensional.
      </p>

      <div className="overflow-hidden rounded-[8px] border border-[var(--border-subtle)]">
        <table className="w-full text-left font-mono text-[12px] tabular-nums">
          <thead className="bg-[var(--surface-2)] text-[10px] uppercase tracking-[0.06em] text-[var(--muted)]">
            <tr>
              <th className="px-3 py-2 font-medium">Estación</th>
              <th className="px-3 py-2 text-right font-medium">RMSE</th>
              <th className="px-3 py-2 text-right font-medium">MAE</th>
              <th className="px-3 py-2 text-right font-medium">R²</th>
              <th className="px-3 py-2 text-right font-medium">Bias</th>
              <th className="px-3 py-2 text-right font-medium">N</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ station, m }) => (
              <tr
                key={station.id}
                className="border-t border-[var(--border-subtle)] hover:bg-[var(--surface-2)]/50"
              >
                <td className="px-3 py-2">
                  <div className="font-sans text-[12px] text-[var(--foreground)]">
                    {station.name}
                  </div>
                  <div className="text-[10px] text-[var(--muted)]">{station.zone}</div>
                </td>
                <td className="px-3 py-2 text-right text-[var(--foreground)]">
                  {m ? formatNumber(m.rmse, digits) : "—"}
                </td>
                <td className="px-3 py-2 text-right text-[var(--foreground)]">
                  {m ? formatNumber(m.mae, digits) : "—"}
                </td>
                <td className="px-3 py-2 text-right">
                  {m ? <R2Badge value={m.r2} /> : "—"}
                </td>
                <td className="px-3 py-2 text-right text-[var(--foreground)]">
                  {m ? (m.bias >= 0 ? "+" : "") + formatNumber(m.bias, digits) : "—"}
                </td>
                <td className="px-3 py-2 text-right text-[var(--muted)]">{m?.n ?? "—"}</td>
              </tr>
            ))}
            {aggregated.n > 0 && (
              <tr className="border-t border-[var(--border-strong)] bg-[var(--surface-2)]/60">
                <td className="px-3 py-2 font-sans text-[12px] font-semibold text-[var(--foreground)]">
                  Promedio
                </td>
                <td className="px-3 py-2 text-right font-semibold text-[var(--foreground)]">
                  {formatNumber(aggregated.rmse, digits)}
                </td>
                <td className="px-3 py-2 text-right font-semibold text-[var(--foreground)]">
                  {formatNumber(aggregated.mae, digits)}
                </td>
                <td className="px-3 py-2 text-right">
                  <R2Badge value={aggregated.r2} />
                </td>
                <td className="px-3 py-2 text-right font-semibold text-[var(--foreground)]">
                  {(aggregated.bias >= 0 ? "+" : "") + formatNumber(aggregated.bias, digits)}
                </td>
                <td className="px-3 py-2 text-right text-[var(--muted)]">
                  {DAGMA_STATIONS.filter((s) => s.variables.includes(pollutant)).length}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="font-mono text-[10px] text-[var(--muted)]/80">
        Las métricas se actualizan cuando el endpoint /api/validate retorne la corrida del modelo real.
      </p>
    </div>
  );
}

function R2Badge({ value }: { value: number }) {
  const level =
    value >= 0.85 ? "good" : value >= 0.7 ? "ok" : "low";
  const styles = {
    good: "text-[var(--success)]",
    ok: "text-[var(--foreground)]",
    low: "text-[var(--warning)]",
  }[level];
  return <span className={styles}>{value.toFixed(3)}</span>;
}
