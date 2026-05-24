"use client";

import {
  Map,
  Source,
  Layer,
  NavigationControl,
  ScaleControl,
  Popup,
  type MapLayerMouseEvent,
} from "react-map-gl/maplibre";
import { useTheme } from "next-themes";
import { useEffect, useMemo, useState } from "react";
import { BASEMAP_STYLE } from "@/lib/map-style";
import {
  BBOX,
  CALI_CENTER,
  POLLUTANT_META,
  type Horizon,
  type Pollutant,
} from "@/lib/domain";
import {
  colorStopsForPollutant,
  hatchOpacityStops,
  sigmaOpacityStops,
} from "@/lib/colors";
import { usePanelStore } from "@/lib/store";
import { formatPlusMinus } from "@/lib/utils";

type GridProps = {
  bbox: [number, number, number, number];
  valueRange: [number, number];
  sigmaRange: [number, number];
};

type GridFeatureCollection = GeoJSON.FeatureCollection<GeoJSON.Polygon, { value: number; sigma: number }> & {
  properties?: { valueMin: number; valueMax: number; sigmaMin: number; sigmaMax: number };
};

const HOVER_LAYER_IDS = ["prediction-fill"];

export function CaliMap({ pollutant, horizon }: { pollutant: Pollutant; horizon: Horizon }) {
  const { resolvedTheme } = useTheme();
  const showUncertainty = usePanelStore((s) => s.showUncertainty);
  const showStations = usePanelStore((s) => s.showStations);
  const showComunas = usePanelStore((s) => s.showComunas);
  const setHoveredCell = usePanelStore((s) => s.setHoveredCell);
  const setHoveredStation = usePanelStore((s) => s.setHoveredStation);

  const [grid, setGrid] = useState<GridFeatureCollection | null>(null);
  const [stations, setStations] = useState<GeoJSON.FeatureCollection | null>(null);
  const [comunas, setComunas] = useState<GeoJSON.FeatureCollection | null>(null);
  const [popup, setPopup] = useState<
    | {
        lon: number;
        lat: number;
        title: string;
        body: string;
        muted?: string;
      }
    | null
  >(null);

  const styleUrl = resolvedTheme === "dark" ? BASEMAP_STYLE.dark : BASEMAP_STYLE.light;

  useEffect(() => {
    let abort = false;
    setPopup(null);
    setGrid(null);
    const slug = `grid_${pollutant.toLowerCase()}_${horizon.replace("+", "").toLowerCase()}.geojson`;
    fetch(`/mock/${slug}`)
      .then((r) => r.json())
      .then((data: GridFeatureCollection) => {
        if (!abort) setGrid(data);
      })
      .catch(() => {});
    return () => {
      abort = true;
    };
  }, [pollutant, horizon]);

  useEffect(() => {
    fetch("/geo/dagma-stations-wfs.geojson")
      .then((r) => r.json())
      .then((data) => setStations(data))
      .catch(() => {});
    fetch("/geo/comunas-cali.geojson")
      .then((r) => r.json())
      .then((data) => setComunas(data))
      .catch(() => {});
  }, []);

  const valueRange: [number, number] = useMemo(() => {
    if (grid?.properties) return [grid.properties.valueMin, grid.properties.valueMax];
    return [0, 1];
  }, [grid]);

  const sigmaRange: [number, number] = useMemo(() => {
    if (grid?.properties) return [grid.properties.sigmaMin, grid.properties.sigmaMax];
    return [0, 1];
  }, [grid]);

  const handleMouseMove = (event: MapLayerMouseEvent) => {
    const features = event.features ?? [];
    if (!features.length) {
      setHoveredCell(null);
      setPopup(null);
      return;
    }
    const feat = features[0];
    if (feat.layer.id === "prediction-fill") {
      const { value, sigma } = feat.properties as { value: number; sigma: number };
      setHoveredCell({ value, sigma, lon: event.lngLat.lng, lat: event.lngLat.lat });
      setPopup({
        lon: event.lngLat.lng,
        lat: event.lngLat.lat,
        title: `${POLLUTANT_META[pollutant].label} · ${horizon}`,
        body: `${formatPlusMinus(value, sigma, pollutant === "SO2" ? 3 : 2)} ${POLLUTANT_META[pollutant].unit}`,
        muted: `lon ${event.lngLat.lng.toFixed(4)} · lat ${event.lngLat.lat.toFixed(4)}`,
      });
    } else if (feat.layer.id === "stations-circle") {
      const props = feat.properties as { nombre?: string; cod?: string; comuna?: string; barrio?: string };
      setHoveredStation((props.cod ?? null) as string | null);
      setPopup({
        lon: event.lngLat.lng,
        lat: event.lngLat.lat,
        title: props.nombre ?? "Estacion DAGMA",
        body: `Codigo ${props.cod ?? "?"} · Comuna ${props.comuna ?? "?"}`,
        muted: props.barrio ? `Barrio ${props.barrio}` : undefined,
      });
    }
  };

  const colorStops = useMemo(
    () => colorStopsForPollutant(pollutant, valueRange),
    [pollutant, valueRange],
  );
  const opacityStops = useMemo(() => sigmaOpacityStops(sigmaRange), [sigmaRange]);
  const hatchStops = useMemo(() => hatchOpacityStops(sigmaRange), [sigmaRange]);

  return (
    <Map
      initialViewState={{
        longitude: CALI_CENTER[0],
        latitude: CALI_CENTER[1],
        zoom: 11.2,
        bearing: 0,
        pitch: 0,
      }}
      maxBounds={[
        [BBOX.xmin - 0.05, BBOX.ymin - 0.05],
        [BBOX.xmax + 0.05, BBOX.ymax + 0.05],
      ]}
      mapStyle={styleUrl}
      interactiveLayerIds={[...HOVER_LAYER_IDS, "stations-circle"]}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => {
        setHoveredCell(null);
        setHoveredStation(null);
        setPopup(null);
      }}
      attributionControl={{ compact: true }}
      style={{ position: "absolute", inset: 0 }}
    >
      <NavigationControl position="bottom-right" visualizePitch={false} showCompass={false} />
      <ScaleControl position="bottom-right" maxWidth={120} unit="metric" />

      {showComunas && comunas && (
        <Source id="comunas" type="geojson" data={comunas}>
          <Layer
            id="comunas-line"
            type="line"
            paint={{
              "line-color": resolvedTheme === "dark" ? "rgba(255,255,255,0.18)" : "rgba(10,10,10,0.18)",
              "line-width": 0.6,
            }}
          />
        </Source>
      )}

      {grid && (
        <Source id="prediction" type="geojson" data={grid}>
          <Layer
            id="prediction-fill"
            type="fill"
            paint={{
              "fill-color": [
                "interpolate",
                ["linear"],
                ["get", "value"],
                ...colorStops,
              ] as unknown as never,
              "fill-opacity": showUncertainty
                ? [
                    "interpolate",
                    ["linear"],
                    ["get", "sigma"],
                    ...opacityStops,
                  ] as unknown as never
                : 0.78,
              "fill-antialias": false,
            }}
          />
          {showUncertainty && (
            <Layer
              id="prediction-hatch"
              type="fill"
              paint={{
                "fill-color": resolvedTheme === "dark" ? "#0a0a0a" : "#fafafa",
                "fill-pattern": "",
                "fill-opacity": [
                  "interpolate",
                  ["linear"],
                  ["get", "sigma"],
                  ...hatchStops,
                ] as unknown as never,
              }}
            />
          )}
          <Layer
            id="prediction-line"
            type="line"
            paint={{
              "line-color": resolvedTheme === "dark" ? "rgba(255,255,255,0.04)" : "rgba(10,10,10,0.04)",
              "line-width": 0.3,
            }}
          />
        </Source>
      )}

      {showStations && stations && (
        <Source id="stations" type="geojson" data={stations}>
          <Layer
            id="stations-halo"
            type="circle"
            paint={{
              "circle-radius": 11,
              "circle-color": resolvedTheme === "dark" ? "#0a0a0a" : "#ffffff",
              "circle-opacity": 0.85,
              "circle-stroke-color": resolvedTheme === "dark" ? "rgba(255,255,255,0.25)" : "rgba(10,10,10,0.25)",
              "circle-stroke-width": 1,
            }}
          />
          <Layer
            id="stations-circle"
            type="circle"
            paint={{
              "circle-radius": 4,
              "circle-color": resolvedTheme === "dark" ? "#fafafa" : "#0a0a0a",
            }}
          />
          <Layer
            id="stations-label"
            type="symbol"
            layout={{
              "text-field": ["get", "cod"],
              "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
              "text-size": 10,
              "text-offset": [0, 1.4],
              "text-anchor": "top",
              "text-allow-overlap": false,
            }}
            paint={{
              "text-color": resolvedTheme === "dark" ? "rgba(255,255,255,0.78)" : "rgba(10,10,10,0.78)",
              "text-halo-color": resolvedTheme === "dark" ? "rgba(10,10,10,0.7)" : "rgba(255,255,255,0.85)",
              "text-halo-width": 1.2,
            }}
          />
        </Source>
      )}

      {popup && (
        <Popup
          longitude={popup.lon}
          latitude={popup.lat}
          closeButton={false}
          closeOnClick={false}
          offset={12}
          anchor="bottom"
          maxWidth="280px"
        >
          <div className="space-y-0.5">
            <div className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
              {popup.title}
            </div>
            <div className="font-mono text-[13px] font-semibold tabular-nums text-[var(--foreground)]">
              {popup.body}
            </div>
            {popup.muted && (
              <div className="font-mono text-[10px] text-[var(--muted)]">{popup.muted}</div>
            )}
          </div>
        </Popup>
      )}
    </Map>
  );
}
