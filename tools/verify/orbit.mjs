import { readFile } from "node:fs/promises";
import { createPropagator, distanceKm, nextAccess, swathCenter } from "../../apps/web/src/features/globe/orbitMath.ts";

const response = await fetch("http://127.0.0.1:8000/api/orbit");
const data = await response.json();
if (!data.elements) throw new Error(data.message);
const at = createPropagator(data.elements);
const now = Date.now();
const a = at(now), b = at(now + 60_000);
if (!a || !b || a.height < 600_000 || a.height > 900_000 || distanceKm(a, b) < 300) {
  throw new Error("The public elements did not produce a plausible moving low Earth orbit");
}
const pass = nextAccess(data.elements, now);
if (!pass || pass.distance > 120) throw new Error("No geometric access found in the supported window");
const catalog = JSON.parse(await readFile("config/catalog/nisar_ayacucho-huanta_gcov.json", "utf8"));
const tracks = [54, 75, 147].map(track => {
  const observed = catalog.granules.filter(item => item.track === track).at(-1);
  const observedTime = Date.parse(observed.start);
  const repeated = observedTime + Math.round((now - observedTime) / (12 * 86_400_000)) * 12 * 86_400_000;
  const p = at(repeated + 17_000), q = at(repeated + 22_000);
  return { track, reference: observed.start, repeatCheck: new Date(repeated).toISOString(),
    distanceToAyacuchoKm: p && q ? distanceKm(swathCenter(p, q), { lon: -74.15, lat: -13.1 }) : null };
});
console.log(JSON.stringify({ epoch: data.elements.EPOCH, altitudeKm: a.height / 1000,
  movedIn60sKm: distanceKm(a, b), nextGeometricAccess: new Date(pass.time).toISOString(),
  centerDistanceKm: pass.distance, tracks, note: "Repeat-cycle check is approximate and does not confirm an acquisition." }, null, 2));
