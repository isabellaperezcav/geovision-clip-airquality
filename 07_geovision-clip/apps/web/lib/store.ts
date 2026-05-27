"use client";

import { create } from "zustand";
import type { Horizon, Pollutant } from "./domain";
import { postPredict, type PointQueryResult } from "./api";

type PanelState = {
  pollutant: Pollutant;
  horizon: Horizon;
  showUncertainty: boolean;
  showStations: boolean;
  showComunas: boolean;
  showModelPattern: boolean;
  hoveredCell: { value: number; sigma: number; lon: number; lat: number } | null;
  hoveredStation: string | null;
  queryRadius: number;
  queryPoint: { lat: number; lon: number } | null;
  queryResult: PointQueryResult | null;
  queryLoading: boolean;
  flyToTarget: { lat: number; lon: number } | null;

  setPollutant: (p: Pollutant) => void;
  setHorizon: (h: Horizon) => void;
  toggleUncertainty: () => void;
  toggleStations: () => void;
  toggleComunas: () => void;
  toggleModelPattern: () => void;
  setHoveredCell: (cell: PanelState["hoveredCell"]) => void;
  setHoveredStation: (id: string | null) => void;
  setQueryRadius: (r: number) => void;
  setFlyToTarget: (t: { lat: number; lon: number } | null) => void;
  // Consulta puntual centralizada: lee pollutant/horizon/queryRadius del estado y
  // ejecuta postPredict. La usan tanto el click en el mapa como el campo de coordenadas.
  queryAt: (lat: number, lon: number) => Promise<void>;
};

export const usePanelStore = create<PanelState>((set, get) => ({
  pollutant: "NO2",
  horizon: "T+1",
  showUncertainty: true,
  showStations: true,
  showComunas: true,
  showModelPattern: false,
  hoveredCell: null,
  hoveredStation: null,
  queryRadius: 2.0,
  queryPoint: null,
  queryResult: null,
  queryLoading: false,
  flyToTarget: null,

  setPollutant: (pollutant) => set({ pollutant }),
  setHorizon: (horizon) => set({ horizon }),
  toggleUncertainty: () => set((s) => ({ showUncertainty: !s.showUncertainty })),
  toggleStations: () => set((s) => ({ showStations: !s.showStations })),
  toggleComunas: () => set((s) => ({ showComunas: !s.showComunas })),
  toggleModelPattern: () => set((s) => ({ showModelPattern: !s.showModelPattern })),
  setHoveredCell: (hoveredCell) => set({ hoveredCell }),
  setHoveredStation: (hoveredStation) => set({ hoveredStation }),
  setQueryRadius: (queryRadius) => set({ queryRadius }),
  setFlyToTarget: (flyToTarget) => set({ flyToTarget }),

  queryAt: async (lat, lon) => {
    const { pollutant, horizon, queryRadius } = get();
    set({ queryPoint: { lat, lon }, queryResult: null, queryLoading: true });
    const res = await postPredict(lat, lon, queryRadius, pollutant, horizon);
    set({ queryResult: res, queryLoading: false });
  },
}));
