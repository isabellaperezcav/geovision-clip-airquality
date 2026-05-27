"use client";

import { useEffect, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { Header } from "@/components/header";
import { Sidebar } from "@/components/sidebar";
import { CaliMapDynamic } from "@/components/map/cali-map-dynamic";
import { Legend } from "@/components/legend";
import { StatusBar } from "@/components/status-bar";
import { CommandPalette } from "@/components/command-palette";
import { ValidationPanel } from "@/components/validation-panel";
import { usePanelStore } from "@/lib/store";
import { getMetadata, type MetadataResponse } from "@/lib/api";

type Metadata = MetadataResponse;

export function Dashboard() {
  const pollutant = usePanelStore((s) => s.pollutant);
  const horizon = usePanelStore((s) => s.horizon);
  const [commandOpen, setCommandOpen] = useState(false);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [tab, setTab] = useState<"prediction" | "validation">("prediction");

  useEffect(() => {
    getMetadata()
      .then(setMetadata)
      .catch(() => {});
  }, []);

  const currentRange = metadata?.files.find(
    (f) => f.pollutant === pollutant && f.horizon === horizon,
  )?.valueRange ?? ([0, 1] as [number, number]);

  return (
    <div className="flex h-svh w-svw flex-col bg-[var(--background)] text-[var(--foreground)]">
      <Header onOpenCommand={() => setCommandOpen(true)} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex flex-1 flex-col overflow-hidden">
          <Tabs.Root
            value={tab}
            onValueChange={(v) => setTab(v as "prediction" | "validation")}
            className="flex flex-1 flex-col overflow-hidden"
          >
            <div className="flex h-10 items-center gap-1 border-b border-[var(--border-subtle)] bg-[var(--background)] px-4">
              <Tabs.List className="flex items-center gap-0.5">
                <TabTrigger value="prediction">Predicción</TabTrigger>
                <TabTrigger value="validation">Validación</TabTrigger>
              </Tabs.List>
              <div className="ml-auto flex items-center gap-3 font-mono text-[11px] text-[var(--muted)]">
                <span>{metadata?.modelVersion ?? "..."}</span>
              </div>
            </div>

            <Tabs.Content value="prediction" className="relative flex-1 outline-none">
              <CaliMapDynamic pollutant={pollutant} horizon={horizon} />
              <div className="pointer-events-none absolute left-4 top-4">
                <Legend pollutant={pollutant} valueRange={currentRange} />
              </div>
            </Tabs.Content>

            <Tabs.Content value="validation" className="flex-1 overflow-hidden outline-none">
              <ValidationPanel />
            </Tabs.Content>
          </Tabs.Root>

          <StatusBar
            generatedAt={
              metadata?.generatedAt
                ? new Date(metadata.generatedAt).toISOString().slice(0, 16).replace("T", " ")
                : null
            }
          />
        </main>
      </div>

      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}

function TabTrigger({ value, children }: { value: string; children: React.ReactNode }) {
  return (
    <Tabs.Trigger
      value={value}
      className="relative inline-flex h-10 items-center px-3 text-[13px] font-medium text-[var(--muted)] outline-none transition-colors hover:text-[var(--foreground)] data-[state=active]:text-[var(--foreground)] data-[state=active]:after:absolute data-[state=active]:after:bottom-[-1px] data-[state=active]:after:left-3 data-[state=active]:after:right-3 data-[state=active]:after:h-px data-[state=active]:after:bg-[var(--foreground)]"
    >
      {children}
    </Tabs.Trigger>
  );
}
