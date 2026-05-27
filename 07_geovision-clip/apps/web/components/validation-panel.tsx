"use client";

import { POLLUTANT_META } from "@/lib/domain";
import { usePanelStore } from "@/lib/store";
import { formatNumber } from "@/lib/utils";
import { getValidation, type ValidationResponse, type ValidationKpis, type KpiGrade } from "@/lib/api";
import { useEffect, useState } from "react";

export function ValidationPanel() {
  const pollutant = usePanelStore((s) => s.pollutant);
  const meta = POLLUTANT_META[pollutant];
  const digits = 2;

  const [data, setData] = useState<ValidationResponse | null>(null);

  useEffect(() => {
    getValidation()
      .then(setData)
      .catch(() => {});
  }, []);

  const rows = (data?.stations ?? [])
    .filter((s) => s.metrics[pollutant])
    .map((s) => ({ station: s, m: s.metrics[pollutant] }));

  const summary = data?.summary?.[pollutant] ?? null;
  const metodo = summary?.metodo ?? "leave-one-out";

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <header className="flex items-baseline justify-between">
        <h2 className="text-[13px] font-semibold text-[var(--foreground)]">
          Validación LOO-CV · {meta.label}
        </h2>
        <span className="font-mono text-[10px] text-[var(--muted)]">
          {data ? metodo : "cargando..."}
        </span>
      </header>

      <p className="font-mono text-[11px] leading-relaxed text-[var(--muted)]">
        Cada estación se deja fuera y se predice con las demás (leave-one-out espacial sobre la
        red DAGMA). RMSE, MAE y bias en {meta.unit}; R² adimensional. Validación contra mediciones
        reales en la franja de paso satelital.
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
                <td className="px-3 py-2 text-right text-[var(--foreground)]">{fmt(m.rmse, digits)}</td>
                <td className="px-3 py-2 text-right text-[var(--foreground)]">{fmt(m.mae, digits)}</td>
                <td className="px-3 py-2 text-right">
                  <R2Badge value={m.r2} />
                </td>
                <td className="px-3 py-2 text-right text-[var(--foreground)]">{fmtSigned(m.bias, digits)}</td>
                <td className="px-3 py-2 text-right text-[var(--muted)]">{m.n ?? "—"}</td>
              </tr>
            ))}
            {summary && (
              <tr className="border-t border-[var(--border-strong)] bg-[var(--surface-2)]/60">
                <td className="px-3 py-2 font-sans text-[12px] font-semibold text-[var(--foreground)]">
                  Global (LOO-CV)
                </td>
                <td className="px-3 py-2 text-right font-semibold text-[var(--foreground)]">
                  {fmt(summary.rmse, digits)}
                </td>
                <td className="px-3 py-2 text-right font-semibold text-[var(--foreground)]">
                  {fmt(summary.mae, digits)}
                </td>
                <td className="px-3 py-2 text-right">
                  <R2Badge value={summary.r2} />
                </td>
                <td className="px-3 py-2 text-right font-semibold text-[var(--foreground)]">
                  {fmtSigned(summary.bias, digits)}
                </td>
                <td className="px-3 py-2 text-right text-[var(--muted)]">{summary.n ?? "—"}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="font-mono text-[10px] text-[var(--muted)]/80">
        {pollutant === "NO2"
          ? "NO₂ solo tiene una estación con datos (Univalle), así que su validación es temporal (persistencia), no espacial. La textura intraurbana del mapa la aporta el modelo profundo v11."
          : "R² negativo indica que la red DAGMA es demasiado dispersa para que el Kriging supere a la media; es el caso donde el downscaling del modelo profundo aporta resolución intraurbana."}
      </p>

      {data?.kpis && <KpiSection kpis={data.kpis} />}
    </div>
  );
}

function fmt(v: number | null, d: number) {
  return v === null || v === undefined ? "—" : formatNumber(v, d);
}

function fmtSigned(v: number | null, d: number) {
  if (v === null || v === undefined) return "—";
  return (v >= 0 ? "+" : "") + formatNumber(v, d);
}

function R2Badge({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-[var(--muted)]">n/d</span>;
  }
  const level = value >= 0.55 ? "good" : value >= 0 ? "ok" : "low";
  const styles = {
    good: "text-[var(--success)]",
    ok: "text-[var(--foreground)]",
    low: "text-[var(--warning)]",
  }[level];
  return <span className={styles}>{value.toFixed(3)}</span>;
}

// ---------------------------------------------------------------------------
// KPIs Situacion 3
// ---------------------------------------------------------------------------

const GRADE_STYLES: Record<KpiGrade, string> = {
  EXCELENTE:    "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  CUMPLE:       "bg-sky-500/15 text-sky-600 dark:text-sky-400",
  NO_CUMPLE:    "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  NO_EVALUABLE: "bg-[var(--surface-2)] text-[var(--muted)]",
};

const GRADE_LABELS: Record<KpiGrade, string> = {
  EXCELENTE:    "EXCELENTE",
  CUMPLE:       "CUMPLE",
  NO_CUMPLE:    "NO CUMPLE",
  NO_EVALUABLE: "NO EVALUABLE",
};

function GradeBadge({ grade }: { grade: KpiGrade }) {
  return (
    <span
      className={`inline-flex items-center rounded-[4px] px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.06em] ${GRADE_STYLES[grade]}`}
    >
      {GRADE_LABELS[grade]}
    </span>
  );
}

function KpiRow({
  label,
  grade,
  value,
  detail,
}: {
  label: string;
  grade: KpiGrade;
  value?: string;
  detail?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface-2)]/40 px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-sans text-[11px] text-[var(--foreground)]">{label}</span>
        <GradeBadge grade={grade} />
      </div>
      {value && (
        <span className="font-mono text-[10px] tabular-nums text-[var(--foreground)]">{value}</span>
      )}
      {detail && (
        <span className="font-mono text-[10px] leading-relaxed text-[var(--muted)]">{detail}</span>
      )}
    </div>
  );
}

function KpiSection({ kpis }: { kpis: ValidationKpis }) {
  const rows: Array<{ label: string; grade: KpiGrade; value?: string; detail?: string }> = [];

  if (kpis.r2_loo_avg) {
    const k = kpis.r2_loo_avg;
    rows.push({
      label: "R² LOO-CV promedio gases evaluables",
      grade: k.grade,
      value: k.value !== null ? k.value.toFixed(4) : undefined,
      detail: `min >= ${k.thresholds?.min} / exc >= ${k.thresholds?.exc} · Calculado sobre ${(k.gases_evaluables ?? []).join("+") || "ninguno"}; excluidos: ${(k.gases_excluidos ?? []).join(", ") || "ninguno"}`,
    });
  }

  if (kpis.moran_i) {
    const k = kpis.moran_i;
    rows.push({
      label: "Índice Moran I predicciones",
      grade: k.grade,
      value: k.min_I !== null ? `min I=${k.min_I.toFixed(3)}; max p=${k.max_p?.toFixed(3) ?? "?"}; ${k.n_pass}/${k.n_total} mapas` : undefined,
      detail: `min: I > ${k.thresholds?.min_I} (p < 0,05) / exc: I > ${k.thresholds?.exc_I} (p < 0,05)`,
    });
  }

  if (kpis.degradacion_ratio) {
    const k = kpis.degradacion_ratio;
    const pct = k.value !== null ? (k.value * 100).toFixed(1) + "%" : undefined;
    rows.push({
      label: "Degradación T+1 a T+7",
      grade: k.grade,
      value: pct,
      detail: `Incremento de sigma mediana T+7/T+1 sobre ${(k.gases ?? []).join("+")} · min: < 60% / exc: < 30%`,
    });
  }

  for (const gas of ["SO2", "O3", "NO2"]) {
    const entry = kpis.rmse_t1?.[gas];
    if (!entry) continue;
    const label = `RMSE LOO-CV ${gas === "NO2" ? "NO₂" : gas === "SO2" ? "SO₂" : "O₃"} T+1`;
    if (entry.grade === "NO_EVALUABLE") {
      rows.push({ label, grade: "NO_EVALUABLE", detail: (entry.reason as string | undefined) ?? `${gas}: no evaluable con la red actual` });
    } else {
      rows.push({
        label,
        grade: entry.grade,
        value: entry.value !== null ? `${entry.value?.toFixed(2)} µg/m³` : undefined,
        detail: `min <= ${entry.thresholds?.min} µg/m³ / exc <= ${entry.thresholds?.exc} µg/m³`,
      });
    }
  }

  if (!rows.length) return null;

  return (
    <div className="flex flex-col gap-2 border-t border-[var(--border-subtle)] pt-3">
      <h3 className="text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--muted)]">
        KPIs Situación 3
      </h3>
      <div className="flex flex-col gap-1.5">
        {rows.map((r) => (
          <KpiRow key={r.label} {...r} />
        ))}
      </div>
    </div>
  );
}
