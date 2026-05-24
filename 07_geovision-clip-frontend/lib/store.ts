"use client";

import { create } from "zustand";
import type { Horizon, Pollutant } from "./domain";

type PanelState = {
  pollutant: Pollutant;
  horizon: Horizon;
  showUncertainty: boolean;
  showStations: boolean;
  showComunas: boolean;
  hoveredCell: { value: number; sigma: number; lon: number; lat: number } | null;
  hoveredStation: string | null;

  setPollutant: (p: Pollutant) => void;
  setHorizon: (h: Horizon) => void;
  toggleUncertainty: () => void;
  toggleStations: () => void;
  toggleComunas: () => void;
  setHoveredCell: (cell: PanelState["hoveredCell"]) => void;
  setHoveredStation: (id: string | null) => void;
};

export const usePanelStore = create<PanelState>((set) => ({
  pollutant: "NO2",
  horizon: "T+1",
  showUncertainty: true,
  showStations: true,
  showComunas: true,
  hoveredCell: null,
  hoveredStation: null,

  setPollutant: (pollutant) => set({ pollutant }),
  setHorizon: (horizon) => set({ horizon }),
  toggleUncertainty: () => set((s) => ({ showUncertainty: !s.showUncertainty })),
  toggleStations: () => set((s) => ({ showStations: !s.showStations })),
  toggleComunas: () => set((s) => ({ showComunas: !s.showComunas })),
  setHoveredCell: (hoveredCell) => set({ hoveredCell }),
  setHoveredStation: (hoveredStation) => set({ hoveredStation }),
}));
