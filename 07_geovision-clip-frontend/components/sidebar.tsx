"use client";

import { Segmented } from "@/components/ui/segmented";
import { ToggleRow } from "@/components/ui/toggle-row";
import { Separator } from "@/components/ui/separator";
import { PollutantIcon } from "@/components/brand/pollutant-icon";
import { usePanelStore } from "@/lib/store";
import {
  HORIZONS,
  HORIZON_META,
  POLLUTANTS,
  POLLUTANT_META,
  DAGMA_STATIONS,
  type Horizon,
  type Pollutant,
} from "@/lib/domain";
import { Activity, Layers3, MapPin } from "lucide-react";

export function Sidebar() {
  const pollutant = usePanelStore((s) => s.pollutant);
  const horizon = usePanelStore((s) => s.horizon);
  const showUncertainty = usePanelStore((s) => s.showUncertainty);
  const showStations = usePanelStore((s) => s.showStations);
  const showComunas = usePanelStore((s) => s.showComunas);
  const setPollutant = usePanelStore((s) => s.setPollutant);
  const setHorizon = usePanelStore((s) => s.setHorizon);
  const toggleUncertainty = usePanelStore((s) => s.toggleUncertainty);
  const toggleStations = usePanelStore((s) => s.toggleStations);
  const toggleComunas = usePanelStore((s) => s.toggleComunas);

  const pollutantItems = POLLUTANTS.map((p) => ({
    value: p,
    label: POLLUTANT_META[p].label,
    description: POLLUTANT_META[p].fullName,
    icon: <PollutantIcon pollutant={p} className="h-3.5 w-3.5" />,
  }));

  const horizonItems = HORIZONS.map((h) => ({
    value: h,
    label: HORIZON_META[h].label,
    description: HORIZON_META[h].description,
  }));

  const stationsForPollutant = DAGMA_STATIONS.filter((s) =>
    s.variables.includes(pollutant),
  );

  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-[var(--border-subtle)] bg-[var(--surface-1)]">
      <div className="flex flex-col gap-4 px-4 py-4">
        <SectionLabel>Contaminante</SectionLabel>
        <Segmented<Pollutant>
          ariaLabel="Contaminante"
          items={pollutantItems}
          value={pollutant}
          onChange={setPollutant}
          fullWidth
        />
        <p className="font-mono text-[11px] leading-relaxed text-[var(--muted)]">
          {POLLUTANT_META[pollutant].fullName}
          <span className="ml-2 text-[var(--muted)]/70">
            unidad {POLLUTANT_META[pollutant].unit}
          </span>
        </p>
      </div>

      <Separator />

      <div className="flex flex-col gap-3 px-4 py-4">
        <SectionLabel>Horizonte</SectionLabel>
        <Segmented<Horizon>
          ariaLabel="Horizonte"
          items={horizonItems}
          value={horizon}
          onChange={setHorizon}
          fullWidth
        />
        <p className="font-mono text-[11px] leading-relaxed text-[var(--muted)]">
          {HORIZON_META[horizon].description}
        </p>
      </div>

      <Separator />

      <div className="flex flex-col gap-1 px-3 py-3">
        <SectionLabel className="px-1.5">Capas</SectionLabel>
        <ToggleRow
          label="Capa de prediccion"
          description="Grid coloreado por valor"
          checked
          onChange={() => {}}
          icon={<Layers3 size={14} strokeWidth={1.6} />}
        />
        <ToggleRow
          label="Incertidumbre"
          description="Opacidad inversa a σ"
          checked={showUncertainty}
          onChange={toggleUncertainty}
          icon={<Activity size={14} strokeWidth={1.6} />}
        />
        <ToggleRow
          label="Estaciones DAGMA"
          description="Puntos de validacion"
          checked={showStations}
          onChange={toggleStations}
          icon={<MapPin size={14} strokeWidth={1.6} />}
        />
        <ToggleRow
          label="Comunas IDESC"
          description="Limites administrativos"
          checked={showComunas}
          onChange={toggleComunas}
        />
      </div>

      <Separator />

      <div className="flex flex-col gap-2 px-4 py-4">
        <SectionLabel>Estaciones con {POLLUTANT_META[pollutant].label}</SectionLabel>
        <ul className="flex flex-col gap-1">
          {stationsForPollutant.map((station) => (
            <li
              key={station.id}
              className="flex items-baseline justify-between gap-3 font-mono text-[11px]"
            >
              <span className="truncate text-[var(--foreground)]">{station.name}</span>
              <span className="shrink-0 tabular-nums text-[var(--muted)]">
                {(station.coverage * 100).toFixed(0)}%
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-1 font-mono text-[10px] text-[var(--muted)]/80">
          Cobertura DAGMA historica 2020-2024
        </p>
      </div>

      <div className="mt-auto" />

      <div className="border-t border-[var(--border-subtle)] px-4 py-3">
        <div className="flex items-center justify-between font-mono text-[10px] text-[var(--muted)]">
          <span>Modelo</span>
          <span className="text-[var(--foreground)]">mvp-0.1-mock</span>
        </div>
        <div className="mt-1 flex items-center justify-between font-mono text-[10px] text-[var(--muted)]">
          <span>BBox EPSG:4326</span>
          <span className="text-[var(--foreground)]">-76.60,3.30,-76.40,3.55</span>
        </div>
      </div>
    </aside>
  );
}

function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h2
      className={`text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--muted)] ${className ?? ""}`}
    >
      {children}
    </h2>
  );
}
