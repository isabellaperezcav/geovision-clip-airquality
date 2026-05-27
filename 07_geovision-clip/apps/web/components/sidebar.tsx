"use client";

import { useState } from "react";
import { Segmented } from "@/components/ui/segmented";
import { ToggleRow } from "@/components/ui/toggle-row";
import { Separator } from "@/components/ui/separator";
import { PollutantIcon } from "@/components/brand/pollutant-icon";
import { usePanelStore } from "@/lib/store";
import {
  BBOX,
  HORIZONS,
  HORIZON_META,
  POLLUTANTS,
  POLLUTANT_META,
  DAGMA_STATIONS,
  type Horizon,
  type Pollutant,
} from "@/lib/domain";
import { Activity, Cpu, Layers3, MapPin, Circle } from "lucide-react";

export function Sidebar() {
  const pollutant = usePanelStore((s) => s.pollutant);
  const horizon = usePanelStore((s) => s.horizon);
  const showUncertainty = usePanelStore((s) => s.showUncertainty);
  const showStations = usePanelStore((s) => s.showStations);
  const showComunas = usePanelStore((s) => s.showComunas);
  const showModelPattern = usePanelStore((s) => s.showModelPattern);
  const setPollutant = usePanelStore((s) => s.setPollutant);
  const setHorizon = usePanelStore((s) => s.setHorizon);
  const toggleUncertainty = usePanelStore((s) => s.toggleUncertainty);
  const toggleStations = usePanelStore((s) => s.toggleStations);
  const toggleComunas = usePanelStore((s) => s.toggleComunas);
  const toggleModelPattern = usePanelStore((s) => s.toggleModelPattern);
  const queryRadius = usePanelStore((s) => s.queryRadius);
  const queryPoint = usePanelStore((s) => s.queryPoint);
  const queryResult = usePanelStore((s) => s.queryResult);
  const queryLoading = usePanelStore((s) => s.queryLoading);
  const setQueryRadius = usePanelStore((s) => s.setQueryRadius);
  const queryAt = usePanelStore((s) => s.queryAt);
  const setFlyToTarget = usePanelStore((s) => s.setFlyToTarget);

  const [latInput, setLatInput] = useState("");
  const [lonInput, setLonInput] = useState("");
  const [coordError, setCoordError] = useState<string | null>(null);

  const submitCoords = (e: React.FormEvent) => {
    e.preventDefault();
    const lat = parseFloat(latInput.replace(",", "."));
    const lon = parseFloat(lonInput.replace(",", "."));
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      setCoordError("Coordenadas invalidas");
      return;
    }
    if (lat < BBOX.ymin || lat > BBOX.ymax || lon < BBOX.xmin || lon > BBOX.xmax) {
      setCoordError(`Fuera del area: lat ${BBOX.ymin} a ${BBOX.ymax}, lon ${BBOX.xmin} a ${BBOX.xmax}`);
      return;
    }
    setCoordError(null);
    void queryAt(lat, lon);
    setFlyToTarget({ lat, lon });
  };

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
        <ToggleRow
          label="Patrón modelo v11"
          description="Textura del CLIP+GRU profundo"
          checked={showModelPattern}
          onChange={toggleModelPattern}
          icon={<Cpu size={14} strokeWidth={1.6} />}
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

      <Separator />

      <div className="flex flex-col gap-3 px-4 py-4">
        <SectionLabel className="flex items-center gap-1">
          <Circle size={10} strokeWidth={1.5} />
          Consulta puntual
        </SectionLabel>

        <form onSubmit={submitCoords} className="flex flex-col gap-2">
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[9px] uppercase tracking-[0.06em] text-[var(--muted)]">
                Latitud
              </span>
              <input
                inputMode="decimal"
                value={latInput}
                onChange={(e) => setLatInput(e.target.value)}
                placeholder="3.4516"
                className="w-full rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface-2)] px-2 py-1.5 font-mono text-[12px] tabular-nums text-[var(--foreground)] outline-none focus:border-[var(--border-strong)]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[9px] uppercase tracking-[0.06em] text-[var(--muted)]">
                Longitud
              </span>
              <input
                inputMode="decimal"
                value={lonInput}
                onChange={(e) => setLonInput(e.target.value)}
                placeholder="-76.5320"
                className="w-full rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface-2)] px-2 py-1.5 font-mono text-[12px] tabular-nums text-[var(--foreground)] outline-none focus:border-[var(--border-strong)]"
              />
            </label>
          </div>
          <button
            type="submit"
            className="rounded-[6px] bg-[var(--foreground)] px-3 py-1.5 text-[12px] font-medium text-[var(--background)] transition-opacity hover:opacity-90"
          >
            Consultar coordenadas
          </button>
          {coordError && (
            <p className="font-mono text-[10px] text-[var(--warning)]">{coordError}</p>
          )}
        </form>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.06em] text-[var(--muted)]">
            Radio
          </span>
          <input
            type="range"
            min={1}
            max={10}
            step={0.5}
            value={queryRadius}
            onChange={(e) => setQueryRadius(parseFloat(e.target.value))}
            className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-[var(--border-subtle)] accent-[var(--foreground)]"
          />
          <span className="w-12 text-right font-mono text-[11px] tabular-nums text-[var(--foreground)]">
            {queryRadius.toFixed(1)} km
          </span>
        </div>

        <div className="rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface-2)] p-3">
          {queryLoading ? (
            <p className="font-mono text-[10px] text-[var(--muted)]">Consultando...</p>
          ) : queryResult?.point ? (
            <div className="flex flex-col gap-1.5">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[10px] text-[var(--muted)]">
                  {queryResult.query.lat.toFixed(4)}, {queryResult.query.lon.toFixed(4)}
                </span>
                <span className="font-mono text-[10px] text-[var(--muted)]">
                  {queryResult.n_celdas} celdas
                </span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="font-mono text-[15px] font-semibold tabular-nums text-[var(--foreground)]">
                  {queryResult.point.value.toFixed(1)}
                </span>
                <span className="font-mono text-[10px] text-[var(--muted)]">
                  ± {queryResult.point.sigma.toFixed(1)} {POLLUTANT_META[pollutant].unit}
                </span>
              </div>
              <div className="font-mono text-[10px] text-[var(--muted)]">
                {queryResult.pollutant} · {queryResult.horizon} · celda a {queryResult.point.dist_km.toFixed(2)} km
              </div>
            </div>
          ) : queryPoint ? (
            <p className="font-mono text-[10px] text-[var(--muted)]">
              Sin datos en este punto
            </p>
          ) : (
            <p className="font-mono text-[10px] text-[var(--muted)]">
              Haz clic en el mapa o escribe coordenadas para consultar un punto
            </p>
          )}
        </div>
      </div>

      <div className="mt-auto" />

      <div className="border-t border-[var(--border-subtle)] px-4 py-3">
        <div className="flex items-center justify-between font-mono text-[10px] text-[var(--muted)]">
          <span>Modelo</span>
          <span className="text-[var(--foreground)]">v11 + ST-Kriging</span>
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
