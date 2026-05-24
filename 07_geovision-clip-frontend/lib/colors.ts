import { POLLUTANT_META, type Pollutant } from "./domain";

export function colorStopsForPollutant(
  pollutant: Pollutant,
  valueRange: [number, number],
): Array<number | string> {
  const scale = POLLUTANT_META[pollutant].colorScale;
  const [vmin, vmax] = valueRange;
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
  const [smin, smax] = sigmaRange;
  return [smin, maxOpacity, smax, minOpacity];
}

export function hatchOpacityStops(
  sigmaRange: [number, number],
  threshold = 0.55,
): Array<number> {
  const [smin, smax] = sigmaRange;
  const cutoff = smin + (smax - smin) * threshold;
  return [smin, 0, cutoff, 0.12, smax, 0.42];
}
