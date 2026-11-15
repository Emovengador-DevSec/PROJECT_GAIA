import type { AlertFeature, RemediationAlert } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";
import "./zone-identity.css";

export function leadingFactors(rem: RemediationAlert, limit = 3) {
  const f = rem.factors;
  return [
    { score: f.hv_score, value: f.hv_drop_db, label: "HV", unit: "dB", decimals: 1 },
    { score: f.slope_score, value: f.slope_deg, label: "Ladera", unit: "°", decimals: 1 },
    { score: f.soil_moisture_score, value: f.soil_moisture_m3m3, label: "Suelo", unit: "m³/m³", decimals: 3 },
    { score: f.heat_score, value: f.heat_count, label: "Focos cercanos", unit: "focos", decimals: 0 },
    { score: f.quake_score, value: f.quake_magnitude, label: "Sismo", unit: "M", decimals: 1 },
    { score: f.rain_score, value: f.rain_mm_7d, label: "Lluvia 7 días", unit: "mm", decimals: 1 },
    { score: f.crop_score, value: f.crop_ha, label: "Cultivo", unit: "ha", decimals: 2 },
  ].filter(item => item.value != null && Number.isFinite(item.value) && item.score != null && item.score >= 0
      && (!(item.unit === "focos" || item.unit === "M") || item.value > 0))
    .sort((a, b) => b.score! - a.score!)
    .slice(0, limit).map(item => `${item.label} ${item.decimals === 3
      ? item.value!.toFixed(3).replace(".", ",")
      : number(item.value!, item.decimals)} ${item.unit}`);
}

export function nearestPlace(feature: AlertFeature) {
  const place = feature.properties.exposure?.nearby_places?.filter(item => item.name.trim()
    && Number.isFinite(item.distance_m) && item.distance_m >= 0)
    .slice().sort((a, b) => a.distance_m - b.distance_m)[0];
  return place ? `${place.name} · ${number(place.distance_m / 1000, 2)} km` : "Poblado cercano sin publicar";
}

export function groupZones(alerts: AlertFeature[]) {
  const groups = new Map<string, AlertFeature[]>();
  for (const feature of alerts) {
    const rem = feature.properties.remediation;
    if (rem) groups.set(rem.risk_id, [...(groups.get(rem.risk_id) ?? []), feature]);
  }
  return [...groups.entries()].map(([id, items]) => ({ id, name: items[0].properties.remediation!.risk_name,
    items: items.sort((a, b) => b.properties.remediation!.index - a.properties.remediation!.index
      || a.properties.id.localeCompare(b.properties.id)) }))
    .sort((a, b) => b.items[0].properties.remediation!.index - a.items[0].properties.remediation!.index
      || a.id.localeCompare(b.id));
}

export function ZoneIdentity({ feature, compact = false }: { feature: AlertFeature; compact?: boolean }) {
  const rem = feature.properties.remediation!;
  const factors = leadingFactors(rem, compact ? 1 : 3);
  return <div className="zone-identity" data-zone-id={feature.properties.id} data-risk={rem.risk_id}>
    <div className="zone-identity-title"><strong>{rem.risk_name}</strong>
      <span className="alert-level" data-level={rem.level}>Riesgo {rem.level}</span></div>
    <span>{number(rem.area_ha, 2)} ha · zona {feature.properties.id.split("_").at(-1)}</span>
    <span className="zone-identity-factors">{factors.length ? factors.join(" · ") : "Factores medidos sin publicar"}</span>
    <span className="zone-identity-place">{nearestPlace(feature)}</span>
  </div>;
}
