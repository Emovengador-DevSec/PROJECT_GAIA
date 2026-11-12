const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type AOI = {
  id: string; name: string; role: "flagship" | "support" | "optional";
  status: "approximate" | "confirmed"; bbox: [number, number, number, number];
  phenomena: string[]; notes?: string;
};

export type LayerManifest = {
  id: string; kind: string; title: string; unit: string; colormap: string;
  range: { min: number | null; max: number | null }; cog_path: string; aoi_id: string;
  dates: { a: string; b: string };
  provenance: { source: string; granules: string[] } & Record<string, unknown>;
  quality: { provisional: boolean; valid_area_pct: number };
};

export type Audience = "publico" | "tecnico";
export type CameraMode = "overview" | "zone" | "oblique";

export type Story = {
  aoi: string; title: string; question: string;
  audience_summary: Record<Audience, string>;
  hypotheses: { id: string; text: string; test: string; status: string }[];
  physics: string; human_factors: string; complementary: string[]; future: string;
  steps: { title: string; layer: string; camera: CameraMode; text: string }[];
};

export type PolStats = { median_db: number; p10_db: number; p90_db: number; valid_pct: number } | null;
export type TimeSeries = {
  aoi_id: string; samples: { date: string; granule: string; HHHH: PolStats; HVHV: PolStats; HV_HH_ratio_db?: number }[];
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`La API respondió ${r.status} en ${path}`);
  return r.json() as Promise<T>;
}

export const api = {
  aois: () => get<AOI[]>("/aois"),
  layers: (aoi: string) => get<LayerManifest[]>(`/layers?aoi=${encodeURIComponent(aoi)}`),
  story: (aoi: string) => get<Story>(`/stories/${encodeURIComponent(aoi)}`),
  timeseries: (aoi: string) => get<TimeSeries>(`/timeseries?aoi=${encodeURIComponent(aoi)}`),
  /** Plantilla de teselas de TiTiler para una capa COG (rango y paleta del manifiesto). */
  tileUrl: (m: LayerManifest) => {
    const p = new URLSearchParams({ url: m.cog_path, colormap_name: m.colormap.toLowerCase(),
      rescale: `${m.range.min ?? -10},${m.range.max ?? 10}` });
    return `${BASE}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?${p}`;
  },
};
