"use client";

import { Command } from "cmdk";
import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  POLLUTANTS,
  POLLUTANT_META,
  HORIZONS,
  HORIZON_META,
  DAGMA_STATIONS,
} from "@/lib/domain";
import { usePanelStore } from "@/lib/store";
import { PollutantIcon } from "@/components/brand/pollutant-icon";

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
}) {
  const setPollutant = usePanelStore((s) => s.setPollutant);
  const setHorizon = usePanelStore((s) => s.setHorizon);
  const toggleUncertainty = usePanelStore((s) => s.toggleUncertainty);
  const toggleStations = usePanelStore((s) => s.toggleStations);
  const [query, setQuery] = useState("");

  useEffect(() => {
    function down(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(true);
      }
    }
    window.addEventListener("keydown", down);
    return () => window.removeEventListener("keydown", down);
  }, [onOpenChange]);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  function close() {
    onOpenChange(false);
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className="fixed left-1/2 top-[18%] z-50 w-full max-w-md -translate-x-1/2 overflow-hidden rounded-[12px] border border-[var(--border-subtle)] bg-[var(--surface-1)] shadow-[var(--shadow-elevation-3)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
          aria-describedby={undefined}
        >
          <Dialog.Title className="sr-only">Paleta de comandos</Dialog.Title>
          <Command label="Paleta de comandos">
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Buscar contaminantes, horizontes, estaciones..."
              className="w-full border-b border-[var(--border-subtle)] bg-transparent px-4 py-3 text-[13px] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none"
              autoFocus
            />
            <Command.List className="max-h-[320px] overflow-y-auto p-1">
              <Command.Empty className="px-3 py-6 text-center font-mono text-[12px] text-[var(--muted)]">
                Sin resultados
              </Command.Empty>

              <Command.Group
                heading="Contaminante"
                className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-[var(--muted)]"
              >
                {POLLUTANTS.map((p) => (
                  <Command.Item
                    key={p}
                    value={`contaminante ${POLLUTANT_META[p].label} ${POLLUTANT_META[p].fullName}`}
                    onSelect={() => {
                      setPollutant(p);
                      close();
                    }}
                    className="flex items-center gap-2.5 rounded-[6px] px-2.5 py-1.5 text-[13px] aria-selected:bg-[var(--surface-2)]"
                  >
                    <PollutantIcon pollutant={p} className="h-4 w-4 text-[var(--muted)]" />
                    <span className="font-medium">{POLLUTANT_META[p].label}</span>
                    <span className="font-mono text-[11px] text-[var(--muted)]">
                      {POLLUTANT_META[p].fullName}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>

              <Command.Group
                heading="Horizonte"
                className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-[var(--muted)]"
              >
                {HORIZONS.map((h) => (
                  <Command.Item
                    key={h}
                    value={`horizonte ${h} ${HORIZON_META[h].description}`}
                    onSelect={() => {
                      setHorizon(h);
                      close();
                    }}
                    className="flex items-center gap-2.5 rounded-[6px] px-2.5 py-1.5 text-[13px] aria-selected:bg-[var(--surface-2)]"
                  >
                    <span className="inline-block min-w-[28px] font-mono text-[11px] text-[var(--muted)]">
                      {h}
                    </span>
                    <span>{HORIZON_META[h].description}</span>
                  </Command.Item>
                ))}
              </Command.Group>

              <Command.Group
                heading="Capas"
                className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-[var(--muted)]"
              >
                <Command.Item
                  value="capa incertidumbre"
                  onSelect={() => {
                    toggleUncertainty();
                    close();
                  }}
                  className="rounded-[6px] px-2.5 py-1.5 text-[13px] aria-selected:bg-[var(--surface-2)]"
                >
                  Alternar capa de incertidumbre
                </Command.Item>
                <Command.Item
                  value="capa estaciones"
                  onSelect={() => {
                    toggleStations();
                    close();
                  }}
                  className="rounded-[6px] px-2.5 py-1.5 text-[13px] aria-selected:bg-[var(--surface-2)]"
                >
                  Alternar estaciones DAGMA
                </Command.Item>
              </Command.Group>

              <Command.Group
                heading="Estaciones"
                className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-[var(--muted)]"
              >
                {DAGMA_STATIONS.map((s) => (
                  <Command.Item
                    key={s.id}
                    value={`estacion ${s.name} ${s.zone}`}
                    onSelect={() => close()}
                    className="flex items-center justify-between gap-2.5 rounded-[6px] px-2.5 py-1.5 text-[13px] aria-selected:bg-[var(--surface-2)]"
                  >
                    <span className="truncate">{s.name}</span>
                    <span className="shrink-0 font-mono text-[10px] text-[var(--muted)]">
                      {s.zone}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>
            <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-3 py-2 font-mono text-[10px] text-[var(--muted)]">
              <span>↑↓ navegar · ↵ seleccionar · esc cerrar</span>
              <span>Ctrl+K para abrir</span>
            </div>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
