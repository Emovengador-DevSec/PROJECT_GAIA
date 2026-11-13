import { eciToGeodetic, gstime, json2satrec, propagate, type OMMJsonObject } from "satellite.js";

const RADIUS = 6371;
const RAD = Math.PI / 180;
export type OrbitPoint = { time: number; lon: number; lat: number; height: number };

export function createPropagator(elements: OMMJsonObject) {
  const record = json2satrec(elements);
  const epoch = Date.parse(elements.EPOCH.endsWith("Z") ? elements.EPOCH : elements.EPOCH + "Z");
  return (time: number): OrbitPoint | undefined => {
    if (Math.abs(time - epoch) > 7 * 86_400_000) return undefined;
    const date = new Date(time);
    const state = propagate(record, date);
    if (!state) return undefined;
    const p = eciToGeodetic(state.position, gstime(date));
    if (![p.longitude, p.latitude, p.height].every(Number.isFinite)) return undefined;
    return { time, lon: p.longitude / RAD, lat: p.latitude / RAD, height: p.height * 1000 };
  };
}

export function distanceKm(a: Pick<OrbitPoint, "lon" | "lat">, b: Pick<OrbitPoint, "lon" | "lat">) {
  const dlat = (b.lat - a.lat) * RAD;
  const dlon = (b.lon - a.lon) * RAD;
  const h = Math.sin(dlat / 2) ** 2 + Math.cos(a.lat * RAD) * Math.cos(b.lat * RAD) * Math.sin(dlon / 2) ** 2;
  return 2 * RADIUS * Math.asin(Math.sqrt(Math.min(1, h)));
}

/** Left-looking approximation using a 35.3° off-nadir angle and a spherical Earth.
 * NASA specifies left looking, incidence 33–47°, and a nominal 240 km swath.
 * This computes geometric access, never an acquisition commitment or a relative track ID.
 */
export function swathCenter(point: OrbitPoint, following: OrbitPoint): OrbitPoint {
  const lat = point.lat * RAD;
  const nextLat = following.lat * RAD;
  const dlon = (following.lon - point.lon) * RAD;
  const bearing = Math.atan2(Math.sin(dlon) * Math.cos(nextLat),
    Math.cos(lat) * Math.sin(nextLat) - Math.sin(lat) * Math.cos(nextLat) * Math.cos(dlon)) - Math.PI / 2;
  const look = 35.3 * RAD;
  const arc = Math.asin(Math.min(1, (RADIUS + point.height / 1000) / RADIUS * Math.sin(look))) - look;
  const destLat = Math.asin(Math.sin(lat) * Math.cos(arc) + Math.cos(lat) * Math.sin(arc) * Math.cos(bearing));
  const destLon = point.lon * RAD + Math.atan2(Math.sin(bearing) * Math.sin(arc) * Math.cos(lat),
    Math.cos(arc) - Math.sin(lat) * Math.sin(destLat));
  return { time: point.time, lon: ((destLon / RAD + 540) % 360) - 180, lat: destLat / RAD, height: 0 };
}

export function nextAccess(elements: OMMJsonObject, start: number, target = { lon: -74.15, lat: -13.1 }) {
  const at = createPropagator(elements);
  // Five days remain inside the supported seven-day window for current daily GP elements.
  for (let time = start; time < start + 5 * 86_400_000; time += 20_000) {
    const p = at(time);
    const next = at(time + 5000);
    if (!p || !next) break;
    const center = swathCenter(p, next);
    if (distanceKm(center, target) > 120) continue;
    let best = { time, distance: distanceKm(center, target) };
    for (let scan = time - 20_000; scan <= time + 90_000; scan += 1000) {
      const a = at(scan), b = at(scan + 5000);
      if (!a || !b) continue;
      const distance = distanceKm(swathCenter(a, b), target);
      if (distance < best.distance) best = { time: scan, distance };
    }
    return best;
  }
  return undefined;
}
