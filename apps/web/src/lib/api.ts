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
  daily?: { date: string; mean_mm: number | null }[];
};

export type PolStats = { median_db: number; p10_db: number; p90_db: number; valid_pct: number } | null;
export type TimeSeries = {
  aoi_id: string; samples: { date: string; granule: string; HHHH: PolStats; HVHV: PolStats; HV_HH_ratio_db?: number }[];
};

export type AlertKind = "quake" | "fire" | "surface_change" | "deformation" | "climate_anomaly";
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
export type RemediationBudget = {
  intervention_id: string;
  name: string;
  description: string;
  priority: number;
  timing: string;
  notes: string;
  unit: string;
  cost_mid?: number | null;
  cost_min?: number | null;
  cost_max?: number | null;
  cost_total_soles?: number | null;
  cost_label: string;
  minka_discount_pct?: number | null;
  source?: string | null;
  source_note?: string | null;
  retrieved_date?: string | null;
  status: string;
};

export type RemediationSoil = {
  wrb_code: string;
  wrb_name: string;
  clay_pct?: number | null;
  sand_pct?: number | null;
  soc_pct?: number | null;
  species: { name: string; scientific: string; function: string; altitude_m: [number, number]; source: string }[];
  source?: string | null;
  source_date?: string | null;
  license?: string | null;
};

export type RemediationRecipe = {
  risk_id: string;
  risk_name: string;
  condition: string;
  disclaimer: string;
  executor: string[];
  species_primary: string[];
  source: string;
};

export type RemediationCostBenefit = {
  currency: string;
  currency_symbol: string;
  crop_ha_evaluated: number;
  effective_ha: number;
  production_value_per_ha_pen: number;
  valuation_source: string;
  loss_avoided_annual_pen: number;
  loss_avoided_3yr_pen: number;
  loss_avoided_5yr_pen: number;
  intervention_cost_total_pen: number;
  cost_with_minka_pen: number;
  benefit_cost_ratio_3yr: number;
  benefit_cost_ratio_5yr: number;
  benefit_cost_ratio_minka_5yr: number;
  assumptions: string[];
  disclaimer: string;
};

export type RemediationRecoveryScenario = {
  mandatory_label: string;
  risk_id: string;
  risk_name: string;
  basis?: "relative_gain_assumption";
  citation_status?: "verificado" | "por_verificar";
  projected: Partial<Record<"year_1" | "year_3" | "year_5", { gain_ndvi: number }>>;
  citation: string;
  citation_url?: string;
  limiting_factors: string[];
};

export type RemediationOpticalContext = {
  product: string;
  source: string;
  dates: { before: string; after: string };
  scenes: string[];
  image_urls: { before: string; after: string };
  terrain_3d_available: boolean;
};

export type BulletinStation = {
  id: string;
  name: string;
  frequency: string;
  reach: string;
  language: string;
  contact?: string;
};

export type RemediationBulletin = {
  alert_id: string;
  aoi_id: string;
  headline: string;
  script_es: string;
  script_qu: string;
  duration_es_seconds: number;
  duration_qu_seconds: number;
  words_count_es: number;
  words_count_qu: number;
  primary_place: string;
  nearby_places: string;
  stations: BulletinStation[];
  quechua_metadata: {
    variant: string;
    review_status: string;
    disclaimer: string;
  };
  disclaimer_mandatory: string;
};

export type MinkaCommitment = {
  id: string;
  timestamp: string;
  community: string;
  volunteers: number;
  tools: string;
  contact_name?: string;
};

export type RemediationMinka = {
  alert_id: string;
  aoi_id: string;
  title: string;
  primary_place: string;
  target_communities: string[];
  techniques?: { name: string; timing?: string | null }[];
  needed_workers: number | null;
  estimated_days: number | null;
  recommended_tools: string[];
  supplies: string[];
  traditional_support: string;
  savings_estimated_soles: number | null;
  whatsapp: {
    text: string;
    url: string;
  };
  sms_verification: {
    text: string;
    char_count: number;
    mode: string;
    notice: string;
  } | null;
};

export type RemediationBulletinResponse = {
  alert_id: string;
  aoi_id: string;
  bulletin: RemediationBulletin;
  minka: RemediationMinka;
  commitments: MinkaCommitment[];
  audio_url_es: string;
  audio_url_qu: string | null;
  roadmap_yachaq: {
    title: string;
    status: string;
    target_deployment: string;
    description: string;
  };
};

export type RemediationAlert = {
  alert_id: string;
  aoi_id: string;
  area_ha: number;
  risk_id: string;
  risk_name: string;
  risk_description: string;
  nearby_places?: { name: string; distance_m: number; url?: string }[];
  summary?: string;
  cause_explanation?: string;
  summary_factor_ids?: string[];
  cause_factor_ids?: string[];
  level: "alto" | "medio" | "bajo";
  color_hex: string;
  index: number;
  factors: {
    hv_drop_db: number | null;
    hv_score: number;
    slope_deg?: number | null;
    slope_score: number | null;
    heat_score: number;
    heat_count?: number | null;
    quake_score: number;
    quake_magnitude?: number | null;
    quake_distance_km?: number | null;
    rain_score: number | null;
    rain_mm_7d?: number | null;
    soil_moisture_m3m3?: number | null;
    soil_moisture_date?: string | null;
    soil_moisture_score: number | null;
    crop_ha?: number | null;
    crop_score: number;
    index_total: number;
  };
  factor_details: string[];
  soil: RemediationSoil;
  recipe?: RemediationRecipe | null;
  budget: RemediationBudget[];
  cost_benefit?: RemediationCostBenefit | null;
  recovery_scenario?: RemediationRecoveryScenario | null;
  optical_context?: RemediationOpticalContext | null;
  sources_nisar: {
    source: string;
    product: string;
    granules: string[];
    dates: string[];
    url: string;
  };
  sources_complementary: {
    source: string;
    url?: string;
    date?: string;
    license?: string;
  }[];
  soil_moisture_available: boolean;
  disclaimer: string;
  generated_at: string;
};

export type RemediationData = {
  aoi_id: string;
  period: string;
  generated_at: string;
  nisar_revisit_days: number;
  soil_moisture_available: boolean;
  note: string;
  disclaimer: string;
  summary: { total_alerts: number; high: number; medium: number; low: number };
  alerts: RemediationAlert[];
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
    metrics: {
      magnitude?: number;
      magnitude_type?: string;
      depth_km?: number;
      frp_mw?: number;
      area_ha?: number | null;
      count?: number;
      tmin_c?: number | null;
      tmax_c?: number | null;
      rain_mm?: number | null;
      rain_sum_mm?: number | null;
      elevation_m?: number | null;
    };
    exposure?: Exposure | null;
    remediation?: RemediationAlert | null;
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
  cropland_low_slope_ha?: number | null; cropland_steep_ha?: number | null; cropland_slope_unknown_ha?: number | null;
  forest_ha: number | null; population: number | null; population_zones: number };
export type CommunityPlace = { id: string; name: string; kind: "province" | "district" | "place";
  province: string; center: [number, number]; url?: string };
export type CommunityIndex = { period: { a: string; b: string }; granules: string[]; coverage_pct: number;
  agriculture?: Agriculture | null;
  region: CommunityImpact; outside_provinces?: CommunityImpact; sources: Record<string, CommunitySource>; district_source?: CommunitySource;
  places: CommunityPlace[] };
type NearbyEvents = { status: string; updated_at: string | null; radius_km: number;
  events: { date: string; km: number; magnitude?: number }[] };
export type Agriculture = { threshold_deg: number; grid_m: number; source: string; source_url: string;
  attribution_url: string; retrieved_at: string; note: string;
  region: { cropland_low_slope_ha: number; cropland_steep_ha: number; cropland_slope_unknown_ha: number };
  calendar: { label: string; date: string; text: string; source: string; url: string }[]; calendar_note: string;
  erosion_reference?: { name: string; url: string } };
export type FireHistory = { start: string; end: string; count: number; covered_days: number;
  annual: { year: number; count: number }[]; monthly: { month: number; total: number; mean: number }[];
  source: string; source_url: string; retrieved_at: string; versions: string[]; originals: number; note: string };
export type Climate = { source: string; version: string; source_url: string; fetched_at: string;
  coordinates: [number, number]; trend_per_decade: number;
  annual: { year: number; temperature: number; rain_mm: number }[];
  projection: { year: number; temperature: number; low: number; high: number }[];
  current: { date: string; max_c: number; min_c: number | null; heat_days: number; hot_last_year: number;
    rain_mm: number | null; normal_rain_mm: number | null; rain_ratio: number | null };
  seasonal_normals?: Record<string, {
    name: string; tmax_mean: number | null; tmax_p10: number | null; tmax_p90: number | null;
    tmin_mean: number | null; tmin_p10: number | null; tmin_p90: number | null;
    rain_daily_mean: number | null; rain_daily_p90: number | null; rain_mean_monthly_mm: number | null;
  }>;
  typical_season?: {
    season_code: string; season_name: string; typical_tmax_c: number | null;
    typical_tmin_c: number | null; typical_rain_mm: number | null;
    p10_tmin_c: number | null; p90_tmax_c: number | null; p90_rain_daily_mm: number | null;
    units: { temperature: string; rainfall: string }; description: string;
  };
  forecast?: {
    source: string; source_url?: string; fetched_at: string; status?: string;
    daily: {
      time: string[]; temperature_2m_max: number[]; temperature_2m_min: number[];
      precipitation_sum: number[]; soil_moisture_0_to_10cm_mean?: number[];
    };
  } | null;
  anomalies?: {
    id: string; kind: string; source: string; source_kind?: string; title: string;
    place: string; date: string; level: "alto" | "medio" | "bajo"; confidence: string;
    note: string; metrics: { tmin_c?: number; tmax_c?: number; rain_mm?: number; normal_p10_c?: number; normal_p90_c?: number; normal_p90_mm?: number };
    source_url?: string;
  }[];
  agricultural_calendar?: {
    evaluated_at: string; season: string; outlook_days: number;
    crops: {
      id: string; name: string; scientific: string; altitude_m: [number, number];
      status: "favorable" | "precaucion" | "fuera_de_temporada";
      sowing_season_months: string; guidance: string;
      factors: { avg_tmin_c?: number | null; avg_tmax_c?: number | null; rain_7d_mm?: number | null; soil_moisture_m3m3?: number | null };
    }[];
    livestock: { name: string; altitude_m: [number, number]; status: string; guidance: string };
    promoter_note: string;
  };
};
export type CommunityDetail = CommunityPlace & { impact: CommunityImpact | null; as_of: string;
  fire: NearbyEvents; quakes: NearbyEvents; fires_today: number;
  indicator: { level: "red" | "orange" | "yellow" | "green" | "unavailable";
    reasons: [string, string, string, string][]; live_complete: boolean; weather_at: string | null };
  rules: { fire_radius_km: number; quake_radius_km: number; quake_magnitude: number; heat_days: number; rain_ratio: number; rain_excess_ratio: number } };
export type ReportKind = "fire" | "landslide" | "dry_water" | "crop_damage";
export type CitizenReport = { id: string; kind: ReportKind; lon: number; lat: number; observed_at: string;
  photo?: {author: string; license: string; license_url: string; image_url: string};
  firms_match: boolean; nisar_overlap: boolean };

export type RealPhoto = {
  caption?: string; page?: number;
  id: string; title: string; scientific?: string; author: string; author_role?: string; width?: number; height?: number; license: string; license_url: string;
  source_url: string; taken_at: string; lat: number | null; lon: number | null; accuracy_m: number | null;
  role: string; place: string; distance_km: number | null; location_label: string;
  image_url: string; thumbnail_url: string; modifications: string;
};
type FutureClimate = {
  reference: [number, number]; future: [number, number];
  models: {model: string; cell: {latitude: number; longitude: number; elevation: number};
    months: Record<string, {min_c: number; rain_pct: number | null}>}[];
};
type StreetView = {url: string; date: string; distance_km: number};
export type PlaceImage = {available: boolean; reason?: string; image_url?: string; date?: string;
  source: string; source_url?: string; scene?: string; scenes?: string[]; resolution_m?: number;
  scene_metadata?: {cloud_cover_pct: number; metadata_url: string}; author?: string; license?: string; license_url?: string; note?: string};
export type PlaceEvidence = {
  aoi_id: string; zone_id: string; available: boolean; generated_at?: string;
  species: {name: string; scientific: string; function?: string; benefit?: string; helps?: string[]; native?: boolean; altitude_m?: [number, number]; photo: RealPhoto | null}[];
  nearby: RealPhoto[]; community: {name: string; center: [number, number]} | null; community_photos: RealPhoto[];
  soil: {wrb_name: string; wrb_probability_pct?: number; source: string; source_date: string} | null;
  soil_photo: RealPhoto | null; techniques: {id: string; name: string; note: string; photos: RealPhoto[]}[];
  imagery: Partial<Record<"past" | "before" | "after", PlaceImage>>; pins: RealPhoto[]; warnings: string[];
  field_photos?: RealPhoto[]; community_reports?: RealPhoto[];
  nearby_settlements?: {name: string; center: [number, number]; distance_km: number}[];
  field_references?: {source_url: string; page: number; place: string; author: string; taken_at: string}[];
  future_climate?: FutureClimate | null;
  greenness?: {product: string; source_url: string; resolution_m: number;
    center: {latitude: number; longitude: number};
    season: string; incomplete_years: number[];
    years: {year: number; median: number; count: number; months: number}[]} | null;
  field_aerial?: {source: string; date: string; license_url: string; resolution_m: number;
    tiles: {bounds: [number, number, number, number]; image_url: string}[]} | null;
  street_view_enabled?: boolean;
};

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { signal });
  if (!r.ok) throw new Error(`La API respondió ${r.status} en ${path}`);
  return r.json() as Promise<T>;
}

export const api = {
  placeEvidence: (aoi: string, zone: string, signal?: AbortSignal) =>
    get<PlaceEvidence>(`/remediation/${encodeURIComponent(aoi)}/${encodeURIComponent(zone)}/place`, signal),
  streetView: (aoi: string, zone: string) =>
    get<StreetView | null>(`/remediation/${encodeURIComponent(aoi)}/${encodeURIComponent(zone)}/street-view`),
  fieldElevation: async (aoi: string) => {
    const path = `/field-dem/${encodeURIComponent(aoi)}`;
    const metadata = await get<{bbox: [number, number, number, number]; width: number; height: number}>(`${path}/metadata`);
    const response = await fetch(`${BASE}${path}/grid`);
    if (!response.ok) throw new Error("Relieve sin publicar.");
    return {...metadata, grid: new DataView(await response.arrayBuffer())};
  },
  localPhoto: (path: string) => path.startsWith("/api/") ? `${BASE}${path.slice(4)}` : "",

  reports: (signal?: AbortSignal) => get<CitizenReport[]>("/reports", signal),
  submitReport: async (report: Pick<CitizenReport, "kind" | "lon" | "lat" | "observed_at"> & {
    note: string; photo?: {author: string; consent: true; base64: string};
  }) => {
    const response = await fetch(`${BASE}/reports`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report) });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(typeof payload?.detail === "string" ? payload.detail : "No se pudo enviar el reporte.");
    }
  },
  climate: (aoi: string, signal?: AbortSignal) => get<Climate | null>(`/climate/${encodeURIComponent(aoi)}`, signal),
  community: (signal?: AbortSignal) => get<CommunityIndex | null>("/community", signal),
  agriculture: (signal?: AbortSignal) => get<Agriculture | null>("/agriculture/ayacucho-huanta", signal),
  fireHistory: (signal?: AbortSignal) => get<FireHistory | null>("/fire-history/ayacucho-huanta", signal),
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
  remediation: (aoi: string, signal?: AbortSignal) => get<RemediationData | null>(`/remediation/${encodeURIComponent(aoi)}`, signal),
  remediationZone: (aoi: string, zoneId: string, signal?: AbortSignal) => get<RemediationAlert | null>(`/remediation/${encodeURIComponent(aoi)}/${encodeURIComponent(zoneId)}`, signal),
  remediationBulletin: (aoi: string, zoneId: string, signal?: AbortSignal) =>
    get<RemediationBulletinResponse>(`/remediation/${encodeURIComponent(aoi)}/${encodeURIComponent(zoneId)}/bulletin`, signal),
  postMinkaCommitment: async (
    aoi: string,
    zoneId: string,
    payload: { community: string; volunteers: number; tools: string; contact_name?: string }
  ) => {
    const res = await fetch(`${BASE}/remediation/${encodeURIComponent(aoi)}/${encodeURIComponent(zoneId)}/minka/commit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Error al registrar compromiso comunal");
    return res.json() as Promise<MinkaCommitment>;
  },
  /** Teselas por identificador de capa publicada. */
  tileUrl: (m: LayerManifest, stage: "change" | "before" | "after" = "change", rgb = false) =>
    `${BASE}/tiles/${encodeURIComponent(m.id)}/${stage}/{z}/{x}/{y}.png${rgb ? "?palette=rgb" : ""}`,
};
