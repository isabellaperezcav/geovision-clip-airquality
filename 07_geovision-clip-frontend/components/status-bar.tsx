"use client";

import { usePanelStore } from "@/lib/store";
import { POLLUTANT_META } from "@/lib/domain";
import { formatNumber } from "@/lib/utils";

export function StatusBar({ generatedAt }: { generatedAt: string | null }) {
  const hoveredCell = usePanelStore((s) => s.hoveredCell);
  const pollutant = usePanelStore((s) => s.pollutant);
  const horizon = usePanelStore((s) => s.horizon);
  const meta = POLLUTANT_META[pollutant];
  const digits = pollutant === "SO2" ? 3 : 2;

  return (
    <div className="flex h-9 shrink-0 items-center justify-between gap-4 border-t border-[var(--border-subtle)] bg-[var(--surface-1)] px-4 font-mono text-[11px] tabular-nums text-[var(--muted)]">
      <div className="flex items-center gap-4">
        <span>
          <span className="text-[var(--muted)]/70">contaminante </span>
          <span className="text-[var(--foreground)]">{meta.label}</span>
        </span>
        <span>
          <span className="text-[var(--muted)]/70">horizonte </span>
          <span className="text-[var(--foreground)]">{horizon}</span>
        </span>
        {hoveredCell && (
          <>
            <span>
              <span className="text-[var(--muted)]/70">lon </span>
              <span className="text-[var(--foreground)]">{hoveredCell.lon.toFixed(4)}</span>
            </span>
            <span>
              <span className="text-[var(--muted)]/70">lat </span>
              <span className="text-[var(--foreground)]">{hoveredCell.lat.toFixed(4)}</span>
            </span>
            <span>
              <span className="text-[var(--muted)]/70">valor </span>
              <span className="text-[var(--foreground)]">
                {formatNumber(hoveredCell.value, digits)}
              </span>
            </span>
            <span>
              <span className="text-[var(--muted)]/70">σ </span>
              <span className="text-[var(--foreground)]">
                {formatNumber(hoveredCell.sigma, digits)}
              </span>
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-3">
        {generatedAt && (
          <span>
            <span className="text-[var(--muted)]/70">corrida </span>
            <span className="text-[var(--foreground)]">{generatedAt}</span>
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
          <span>API mock</span>
        </span>
      </div>
    </div>
  );
}
