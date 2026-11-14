const BASE = import.meta.env.VITE_API_BASE ?? "/api";
import type { OMMJsonObject } from "satellite.js";

export type OrbitData = { status: string; source_url: string; message: string;
  fetched_at?: string; elements?: OMMJsonObject };

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
  coverage_bbox?: AOI["bbox"];
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
  nisar_confirmed_pct?: number | null; radar_coverage_pct?: number;
  granules?: { name: string; date: string }[];
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
export type ExposureSource = {
  name: string; date?: string; year?: number; license?: string; license_url?: string; url?: string; attribution?: string;
};
export type Exposure = {
  people?: number | null; crop_ha?: number | null; forest_ha?: number | null; grassland_ha?: number | null;
  other_landcover_ha?: number | null; landcover_unmapped_ha?: number | null; landcover_coverage_pct?: number | null;
  settlements?: number | null; settlement_buffer_m?: number; places?: string[] | null;
  nearby_places?: { name: string; distance_m: number; url?: string }[] | null;
  sources?: (ExposureSource | string)[] | Record<string, ExposureSource>; note?: string; issues?: string[];
};
export type AlertFeature = {
  type: "Feature"; id?: string;
  geometry: { type: string; coordinates: unknown };
  properties: {
    id: string; kind: AlertKind; source: string; source_kind: "primary" | "complementary";
    title: string; place: string; date: string; level: "alto" | "medio" | "bajo"; confidence: string;
    note: string; source_url: string; aoi_id?: string; granules?: string[]; provisional?: boolean; polarization?: string | null;
    center?: [number, number]; members?: { id: string; date: string }[]; first_date?: string;
    comparison_summary?: { loss_area_ha: number; mapped_loss_area_ha: number; alerts: number } | null;
    metrics: { magnitude?: number; magnitude_type?: string; depth_km?: number; frp_mw?: number; area_ha?: number | null; count?: number };
    exposure?: Exposure | null;
  };
};
export type FeedStatus = { source: string; status: string; last_updated: string | null; stale: boolean; message?: string; latency: string; coverage_days?: number };
export type AlertCollection = { type: "FeatureCollection"; features: AlertFeature[]; sources: FeedStatus[]; fire_cells?: AlertFeature[] };
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

type CommunitySource = { name: string; url: string; year?: number; date?: string; license?: string };
type CommunityImpact = { zones: number; cropland_ha: number | null; grassland_ha: number | null;
  forest_ha: number | null; population: number | null; population_zones: number };
export type CommunityPlace = { id: string; name: string; kind: "province" | "district" | "place";
  province: string; center: [number, number]; url?: string };
export type CommunityIndex = { period: { a: string; b: string }; granules: string[]; coverage_pct: number;
  region: CommunityImpact; sources: Record<string, CommunitySource>; district_source?: CommunitySource;
  places: CommunityPlace[] };
type NearbyEvents = { status: string; updated_at: string | null; radius_km: number;
  events: { date: string; km: number; magnitude?: number }[] };
export type Climate = { source: string; version: string; source_url: string; fetched_at: string;
  coordinates: [number, number]; trend_per_decade: number;
  annual: { year: number; temperature: number; rain_mm: number }[];
  projection: { year: number; temperature: number; low: number; high: number }[];
  current: { date: string; max_c: number; min_c: number | null; heat_days: number; hot_last_year: number;
    rain_mm: number | null; normal_rain_mm: number | null; rain_ratio: number | null } };
export type CommunityDetail = CommunityPlace & { impact: CommunityImpact | null; as_of: string;
  fire: NearbyEvents; quakes: NearbyEvents; fires_today: number;
  indicator: { level: "red" | "orange" | "yellow" | "green" | "unavailable";
    reasons: [string, string, string, string][]; live_complete: boolean; weather_at: string | null };
  rules: { fire_radius_km: number; quake_radius_km: number; quake_magnitude: number; heat_days: number; rain_ratio: number } };
export type ReportKind = "fire" | "landslide" | "dry_water" | "crop_damage";
export type CitizenReport = { id: string; kind: ReportKind; lon: number; lat: number; observed_at: string;
  firms_match: boolean; nisar_overlap: boolean };

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { signal });
  if (!r.ok) throw new Error(`La API respondió ${r.status} en ${path}`);
  return r.json() as Promise<T>;
}

export const api = {
  reports: (signal?: AbortSignal) => get<CitizenReport[]>("/reports", signal),
  submitReport: async (report: Pick<CitizenReport, "kind" | "lon" | "lat" | "observed_at"> & { note: string }) => {
    const response = await fetch(`${BASE}/reports`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report) });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(typeof payload?.detail === "string" ? payload.detail : "No se pudo enviar el reporte.");
    }
  },
  climate: (aoi: string, signal?: AbortSignal) => get<Climate | null>(`/climate/${encodeURIComponent(aoi)}`, signal),
  community: (signal?: AbortSignal) => get<CommunityIndex | null>("/community", signal),
  communityPlace: (id: string, signal?: AbortSignal) => get<CommunityDetail>(`/community/${encodeURIComponent(id)}`, signal),
  orbit: () => get<OrbitData>("/orbit"),
  aois: () => get<AOI[]>("/aois"),
  health: () => get<Health>("/health"),
  catalog: (aoi: string, product = aoi === "sabancaya" ? "GUNW" : "GCOV") =>
    get<Catalog>(`/catalog?aoi=${encodeURIComponent(aoi)}&product=${encodeURIComponent(product)}`),
  context: (aoi: string) => get<ContextLayer[]>(`/context/${encodeURIComponent(aoi)}`),
  contextImage: (aoi: string, item: ContextLayer, date = item.date) =>
    `${BASE}/context/${encodeURIComponent(aoi)}/${encodeURIComponent(item.id)}/${encodeURIComponent(date)}.png`,
  validation: (id: string) => get<Validation | null>(`/validation/${encodeURIComponent(id)}`),
  rainfall: (aoi: string) => get<Rainfall | null>(`/rainfall/${encodeURIComponent(aoi)}`),
  alerts: () => get<AlertCollection>("/alerts?include_live=true&active_only=true"),
  trend: (aoi: string, pol: string) => get<Trend>(`/trend?aoi=${encodeURIComponent(aoi)}&pol=${encodeURIComponent(pol)}`),
  layers: (aoi: string) => get<LayerManifest[]>(`/layers?aoi=${encodeURIComponent(aoi)}&active_only=true`),
  polarizations: (aoi: string) => get<PolarizationSummary[]>(`/polarizations?aoi=${encodeURIComponent(aoi)}&active_only=true`),
  story: (aoi: string) => get<Story>(`/stories/${encodeURIComponent(aoi)}`),
  timeseries: (aoi: string) => get<TimeSeries>(`/timeseries?aoi=${encodeURIComponent(aoi)}&allow_empty=true`),
  /** Teselas por identificador de capa publicada. */
  tileUrl: (m: LayerManifest, stage: "change" | "before" | "after" = "change", rgb = false) =>
    `${BASE}/tiles/${encodeURIComponent(m.id)}/${stage}/{z}/{x}/{y}.png${rgb ? "?palette=rgb" : ""}`,
};
