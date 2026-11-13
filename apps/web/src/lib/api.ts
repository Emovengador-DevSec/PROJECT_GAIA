const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type AOI = {
  id: string; name: string; role: "flagship" | "support" | "optional";
  status: "approximate" | "confirmed"; bbox: [number, number, number, number];
  phenomena: string[]; notes?: string;
  camera?: { heading_deg?: number; pitch_deg?: number };
};

export type LayerManifest = {
  id: string; kind: string; title: string; unit: string; colormap: string;
  range: { min: number | null; max: number | null }; cog_path: string; aoi_id: string;
  dates: { a: string; b: string };
  provenance: { source: string; granules: string[] } & Record<string, unknown>;
  quality: { provisional: boolean; valid_area_pct: number };
  comparison?: { before_cog_path: string; after_cog_path: string; range: { min: number; max: number } };
};

export type Audience = "publico" | "tecnico";
export type CameraMode = "overview" | "zone" | "oblique";

export type Story = {
  aoi: string; title: string; question: string;
  audience_summary: Record<Audience, string>;
  hypotheses: { id: string; text: string; test: string; status: string }[];
  physics: string; human_factors: string; complementary: string[]; future: string;
  steps: { title: string; layer: string; camera: CameraMode; text: string; context?: string }[];
};

export type ContextLayer = {
  id: string; name: string; product: string; source: string; date: string;
  note: string; href: string; report?: string; scene?: string; scenes?: string[];
  kind?: "nisar-preview"; before?: string; license?: string; legend?: string; available: boolean;
};

export type Validation = {
  source: string; source_url: string; granule: string; date: string; note: string;
  common_ha: number; nisar_loss_ha: number; opera_disturbance_ha: number; overlap_ha: number; agreement_pct: number | null;
};
export type Rainfall = {
  source: string; source_url: string; note: string; dates: string[]; granules: string[];
  mean_mm: number | null; valid_area_pct: number;
};

export type PolStats = { median_db: number; p10_db: number; p90_db: number; valid_pct: number } | null;
export type TimeSeries = {
  aoi_id: string; samples: { date: string; granule: string; HHHH: PolStats; HVHV: PolStats; HV_HH_ratio_db?: number }[];
};

export type AlertKind = "quake" | "fire" | "surface_change" | "deformation";
export type AlertFeature = {
  type: "Feature"; id?: string;
  geometry: { type: string; coordinates: unknown };
  properties: {
    id: string; kind: AlertKind; source: string; source_kind: "primary" | "complementary";
    title: string; place: string; date: string; level: "alto" | "medio" | "bajo"; confidence: string;
    note: string; source_url: string; aoi_id?: string; granules?: string[]; provisional?: boolean;
    metrics: { magnitude?: number; depth_km?: number; frp_mw?: number; area_ha?: number | null; count?: number };
    exposure?: { people?: number | null; crop_ha?: number | null; forest_ha?: number | null;
      settlements?: number | null; sources?: string[]; note?: string } | null;
  };
};
export type FeedStatus = { source: string; status: string; last_updated: string | null; stale: boolean; message?: string; latency: string };
export type AlertCollection = { type: "FeatureCollection"; features: AlertFeature[]; sources: FeedStatus[] };
export type Health = { status: string; tiles: boolean; layers: number; offline?: boolean; credentials: { earthdata: boolean; firms: boolean } };
export type GlobeStatus = { terrain: "loading" | "ready" | "regional" | "unavailable"; imagery: string; regionalImagery?: string };
export type Trend = { status: string; label: string; method: string; dates: number; message?: string;
  uncertainty?: string; projection: { date: string; value: number; low: number; high: number }[] };
export type Catalog = { aoi_id: string; product: string; source: string; queried_at?: string;
  granules: { name: string; start: string; direction: string; track: number; frame: number;
    size_mb: number | null; polarizations: string[] }[] };
export type PolarizationSummary = {
  strongest?: "HHHH" | "HVHV";
  HHHH?: { loss_area_ha: number; alerts: number };
  HVHV?: { loss_area_ha: number; alerts: number };
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`La API respondió ${r.status} en ${path}`);
  return r.json() as Promise<T>;
}

export const api = {
  aois: () => get<AOI[]>("/aois"),
  health: () => get<Health>("/health"),
  catalog: (aoi: string, product = aoi === "sabancaya" ? "GUNW" : "GCOV") =>
    get<Catalog>(`/catalog?aoi=${encodeURIComponent(aoi)}&product=${encodeURIComponent(product)}`),
  context: (aoi: string) => get<ContextLayer[]>(`/context/${encodeURIComponent(aoi)}`),
  contextImage: (aoi: string, item: ContextLayer, date = item.date) =>
    `${BASE}/context/${encodeURIComponent(aoi)}/${encodeURIComponent(item.id)}/${encodeURIComponent(date)}.png`,
  validation: (id: string) => get<Validation | null>(`/validation/${encodeURIComponent(id)}`),
  rainfall: (aoi: string) => get<Rainfall | null>(`/rainfall/${encodeURIComponent(aoi)}`),
  alerts: () => get<AlertCollection>("/alerts?include_live=true"),
  trend: (aoi: string, pol: string) => get<Trend>(`/trend?aoi=${encodeURIComponent(aoi)}&pol=${encodeURIComponent(pol)}`),
  layers: (aoi: string) => get<LayerManifest[]>(`/layers?aoi=${encodeURIComponent(aoi)}`),
  polarizations: (aoi: string) => get<PolarizationSummary[]>(`/polarizations?aoi=${encodeURIComponent(aoi)}`),
  story: (aoi: string) => get<Story>(`/stories/${encodeURIComponent(aoi)}`),
  timeseries: (aoi: string) => get<TimeSeries>(`/timeseries?aoi=${encodeURIComponent(aoi)}&allow_empty=true`),
  /** Teselas por identificador de capa publicada. */
  tileUrl: (m: LayerManifest, stage: "change" | "before" | "after" = "change", rgb = false) =>
    `${BASE}/tiles/${encodeURIComponent(m.id)}/${stage}/{z}/{x}/{y}.png${rgb ? "?palette=rgb" : ""}`,
};
