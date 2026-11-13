import { CustomHeightmapTerrainProvider, GeographicTilingScheme, Rectangle, Math as CesiumMath } from "cesium";

type TerrainMetadata = { bbox: [number, number, number, number]; width: number; height: number };
const SAMPLE_SIZE = 33;

export async function loadAyacuchoTerrain(): Promise<CustomHeightmapTerrainProvider> {
  const [metadata, grid] = await Promise.all([
    fetch("/globe/ayacucho-terrain.json"), fetch("/globe/ayacucho-terrain.bin"),
  ]);
  if (!metadata.ok || !grid.ok) throw new Error("Relieve local no disponible");
  const { bbox, width, height } = await metadata.json() as TerrainMetadata;
  const heights = new Int16Array(await grid.arrayBuffer());
  if (heights.length !== width * height) throw new Error("Rejilla de elevaciones incompleta");
  const coverage = Rectangle.fromDegrees(...bbox);
  const tilingScheme = new GeographicTilingScheme();

  function sample(longitude: number, latitude: number) {
    const u = (longitude - coverage.west) / coverage.width;
    const v = (coverage.north - latitude) / coverage.height;
    if (u < 0 || u > 1 || v < 0 || v > 1) return 0;
    const x = CesiumMath.clamp(u * width - .5, 0, width - 1);
    const y = CesiumMath.clamp(v * height - .5, 0, height - 1);
    const left = Math.floor(x), top = Math.floor(y);
    const right = Math.min(width - 1, left + 1), bottom = Math.min(height - 1, top + 1);
    const north = CesiumMath.lerp(heights[top * width + left], heights[top * width + right], x - left);
    const south = CesiumMath.lerp(heights[bottom * width + left], heights[bottom * width + right], x - left);
    // Blend the outer edge of the DEM into the ellipsoid away from the study area.
    const edge = Math.min(u, 1 - u, v, 1 - v);
    return CesiumMath.lerp(north, south, y - top) * Math.min(1, edge / .08);
  }

  return new CustomHeightmapTerrainProvider({ width: SAMPLE_SIZE, height: SAMPLE_SIZE, tilingScheme,
    credit: "Mapzen Terrain Tiles · SRTM y fuentes de elevación",
    callback(x, y, level) {
      const result = new Float32Array(SAMPLE_SIZE ** 2);
      const rect = tilingScheme.tileXYToRectangle(x, y, level);
      if (!Rectangle.intersection(rect, coverage)) return result;
      for (let row = 0; row < SAMPLE_SIZE; row++) {
        const latitude = rect.north - rect.height * row / (SAMPLE_SIZE - 1);
        for (let col = 0; col < SAMPLE_SIZE; col++) {
          const longitude = rect.west + rect.width * col / (SAMPLE_SIZE - 1);
          result[row * SAMPLE_SIZE + col] = sample(longitude, latitude);
        }
      }
      return result;
    },
  });
}
