import { POLLUTANT_META, type Pollutant } from "./domain";

// MapLibre exige que los pares de "interpolate" tengan inputs en orden estrictamente
// ascendente. Cuando un campo es constante (p. ej. SO2 sale como nugget puro, o el
// sigma es uniforme) el rango es degenerado (min == max) y los inputs se repiten, lo
// que rompe la expresion. ensureSpan garantiza max > min con un margen minimo.
function ensureSpan(min: number, max: number, fallback = 1): [number, number] {
  if (Number.isFinite(min) && Number.isFinite(max) && max > min) return [min, max];
  const base = Number.isFinite(min) ? min : 0;
  return [base, base + fallback];
}

export function colorStopsForPollutant(
  pollutant: Pollutant,
  valueRange: [number, number],
): Array<number | string> {
  const scale = POLLUTANT_META[pollutant].colorScale;
  const [vmin, vmax] = ensureSpan(valueRange[0], valueRange[1]);
  const span = vmax - vmin;
  const stops: Array<number | string> = [];
  for (let i = 0; i < scale.length; i++) {
    const t = i / (scale.length - 1);
    stops.push(vmin + t * span);
    stops.push(scale[i]);
  }
  return stops;
}

export function sigmaOpacityStops(
  sigmaRange: [number, number],
  minOpacity = 0.18,
  maxOpacity = 0.95,
): Array<number> {
  // Mas sigma => menor opacidad (mas transparente).
  const [smin, smax] = ensureSpan(sigmaRange[0], sigmaRange[1]);
  return [smin, maxOpacity, smax, minOpacity];
}

export function hatchOpacityStops(
  sigmaRange: [number, number],
  threshold = 0.55,
): Array<number> {
  const [smin, smax] = ensureSpan(sigmaRange[0], sigmaRange[1]);
  const cutoff = smin + (smax - smin) * threshold;
  return [smin, 0, cutoff, 0.12, smax, 0.42];
}
