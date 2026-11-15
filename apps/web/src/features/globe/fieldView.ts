import * as Cesium from "cesium";
import {api} from "../../lib/api";

type Coordinate = [number, number];
type Plot = Coordinate[][];
type Vertex = {point: Coordinate; height: number};

const localData = new Map<string, ReturnType<typeof api.fieldElevation>>();

function localElevation(aoi: string) {
  let pending = localData.get(aoi);
  if (!pending) {
    pending = api.fieldElevation(aoi).catch(error => {
      localData.delete(aoi);
      throw error;
    });
    localData.set(aoi, pending);
  }
  return pending;
}

export async function fieldHeights(aoi: string, points: Coordinate[]) {
  const {bbox, width, height, grid} = await localElevation(aoi);
  const [west, south, east, north] = bbox;
  if (grid.byteLength !== 2 * width * height) throw new Error("Relieve incompleto.");
  return points.map(([lon, lat]) => {
    if (lon < west || lon > east || lat < south || lat > north) return NaN;
    const x = Cesium.Math.clamp((lon - west) / (east - west) * width - .5, 0, width - 1);
    const y = Cesium.Math.clamp((north - lat) / (north - south) * height - .5, 0, height - 1);
    const left = Math.floor(x), top = Math.floor(y);
    const right = Math.min(left + 1, width - 1), bottom = Math.min(top + 1, height - 1);
    const at = (column: number, row: number) => grid.getInt16((row * width + column) * 2, true);
    return Cesium.Math.lerp(Cesium.Math.lerp(at(left, top), at(right, top), x - left),
      Cesium.Math.lerp(at(left, bottom), at(right, bottom), x - left), y - top);
  });
}

export async function sampleFieldSurface(
  terrain: Cesium.TerrainProvider, samples: Cesium.Cartographic[],
) {
  samples.forEach(sample => {sample.height = NaN;});
  if (terrain.availability) {
    await Cesium.sampleTerrainMostDetailed(terrain, samples).catch(() => undefined);
  } else if (!(terrain instanceof Cesium.EllipsoidTerrainProvider)) {
    await Cesium.sampleTerrain(terrain, 12, samples).catch(() => undefined);
  }
}

function inside(point: Coordinate, ring: Coordinate[]) {
  let crosses = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x, y] = ring[i], [previousX, previousY] = ring[j];
    if ((y > point[1]) !== (previousY > point[1]) &&
        point[0] < x + (previousX - x) * (point[1] - y) / (previousY - y)) crosses = !crosses;
  }
  return crosses;
}

function contourIntersections(vertices: Vertex[], elevation: number): Coordinate[] {
  return vertices.flatMap((a, i) => {
    const b = vertices[(i + 1) % vertices.length];
    if ((a.height < elevation) === (b.height < elevation)) return [];
    const fraction = (elevation - a.height) / (b.height - a.height);
    return [[
      a.point[0] + fraction * (b.point[0] - a.point[0]),
      a.point[1] + fraction * (b.point[1] - a.point[1]),
    ] as Coordinate];
  });
}

function crossesBoundary(a: Coordinate, b: Coordinate, ring: Coordinate[]) {
  const side = (origin: Coordinate, end: Coordinate, point: Coordinate) =>
    (end[0] - origin[0]) * (point[1] - origin[1]) - (end[1] - origin[1]) * (point[0] - origin[0]);
  return ring.some((c, index) => {
    const d = ring[(index + 1) % ring.length];
    return side(a, b, c) * side(a, b, d) < 0 && side(c, d, a) * side(c, d, b) < 0;
  });
}

/** Sample small plots at 25 m, then sketch 25 m contours strictly within the selected polygon. */
export async function fieldContours(
  aoi: string, plots: Plot[], exaggeration: number,
): Promise<Cesium.Cartesian3[][]> {
  const points = plots.flatMap(plot => plot[0]);
  if (!points.length) return [];
  const west = Math.min(...points.map(p => p[0])), east = Math.max(...points.map(p => p[0]));
  const south = Math.min(...points.map(p => p[1])), north = Math.max(...points.map(p => p[1]));
  const columns = Math.max(3, Math.ceil((east - west) * 111_320 * Math.cos(Cesium.Math.toRadians(south)) / 25));
  const rows = Math.max(3, Math.ceil((north - south) * 111_320 / 25));
  if ((columns + 1) * (rows + 1) > 2500) return [];

  const grid = Array.from({length: columns + 1}, (_, x) =>
    Array.from({length: rows + 1}, (_, y): Coordinate =>
      [west + (east - west) * x / columns, south + (north - south) * y / rows]));
  const elevations = await fieldHeights(aoi, grid.flat());
  if (!elevations.every(Number.isFinite)) return [];

  const heights = (x: number, y: number): Vertex =>
    ({point: grid[x][y], height: elevations[x * (rows + 1) + y]});
  const result: Cesium.Cartesian3[][] = [];
  for (const plot of plots) {
    const contains = (point: Coordinate) => inside(point, plot[0]) && !plot.slice(1).some(hole => inside(point, hole));
    for (let x = 0; x < columns; x++) {
      for (let y = 0; y < rows; y++) {
        const a = heights(x, y), b = heights(x + 1, y), c = heights(x + 1, y + 1), d = heights(x, y + 1);
        for (const triangle of [[a, b, c], [a, c, d]]) {
          if (!triangle.every(vertex => Number.isFinite(vertex.height))) continue;
          const low = Math.min(...triangle.map(vertex => vertex.height));
          const high = Math.max(...triangle.map(vertex => vertex.height));
          for (let elevation = Math.ceil(low / 25) * 25; elevation < high; elevation += 25) {
            const line = contourIntersections(triangle, elevation);
            if (line.length !== 2) continue;
            const [start, end] = line;
            if (!contains(start) || !contains(end) || plot.some(ring => crossesBoundary(start, end, ring))) continue;
            result.push(line.map(([lon, lat]) => Cesium.Cartesian3.fromDegrees(lon, lat, elevation * exaggeration + 3)));
          }
        }
      }
    }
  }
  return result;
}
