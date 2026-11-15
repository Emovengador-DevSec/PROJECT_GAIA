import { useEffect, useState } from "react";
import { api, type AlertFeature, type Climate } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";
import { formatDate } from "../../lib/formatDate";
import { climateSummary } from "./actionSummaryModel";

const km = (m: number) => `${number(m / 1000)} km`;
const shortDate = (iso?: string | null) => iso
  ? new Date(`${iso.slice(0, 10)}T12:00:00Z`).toLocaleDateString("es-PE", { day: "numeric", month: "short", year: "numeric" })
  : "";

/** Exposure in one line, only with measured values. */
export function exposureSummary(feature: AlertFeature) {
  const e = feature.properties.exposure;
  if (!e) return "Exposición sin publicar para esta mancha";
  return [e.crop_ha != null && e.crop_ha > 0 ? `Cultivo ${number(e.crop_ha)} ha` : null,
    e.grassland_ha != null && e.grassland_ha > 0 ? `Pastizal ${number(e.grassland_ha)} ha` : null,
    e.people != null ? `${number(e.people, 0)} personas estimadas (WorldPop)` : null,
  ].filter(Boolean).join(" · ");
}

/** Measured evidence behind the cause, with values and units. */
function evidenceText(feature: AlertFeature) {
  const rem = feature.properties.remediation!;
  const f = rem.factors;
  const parts: Record<string, string | null> = {
    slope_deg: f.slope_deg != null ? `ladera de ${number(f.slope_deg, 1)}° (DEM 30 m)` : null,
    soil_moisture_m3m3: f.soil_moisture_m3m3 != null ? `suelo con ${f.soil_moisture_m3m3.toFixed(3).replace(".", ",")} m³/m³ de humedad (NISAR SME2)` : null,
    crop_ha: f.crop_ha ? `${number(f.crop_ha)} ha de cultivo (WorldCover)` : null,
    heat_count: (f.heat_score ?? 0) > 0 ? "focos de calor a < 2 km (FIRMS)" : null,
    quake_magnitude: (f.quake_score ?? 0) > 0 ? "sismo a < 50 km (USGS)" : null,
    rain_mm_7d: f.rain_mm_7d != null ? `${number(f.rain_mm_7d, 1)} mm de lluvia en 7 días` : null,
  };
  return (rem.cause_factor_ids ?? []).map(id => parts[id]).filter(Boolean).join(" y ");
}

export function ZoneDiagnosis({ feature }: { feature: AlertFeature }) {
  const rem = feature.properties.remediation!;
  const evidence = evidenceText(feature);
  const places = (rem.nearby_places ?? []).slice(0, 3);
  const dates = rem.sources_nisar.dates?.length === 2 ? rem.sources_nisar.dates : null;
  return <div className="zone-diagnosis-brief">
    <p><strong>Por qué:</strong> {!rem.cause_factor_ids ? "evidencia sin publicar." : evidence
      ? `${evidence}. Confirmar en campo.` : "ningún dato medido apunta a una causa. Confirmar en campo."}</p>
    <p><strong>Afecta:</strong> {exposureSummary(feature)}</p>
    {places.length > 0 && <p><strong>Poblados cercanos:</strong> {places.map(pl => `${pl.name} ${km(pl.distance_m)}`).join(" · ")}</p>}
    <p className="zone-sheet-provenance">Radar NISAR (provisional) · {dates
      ? `${shortDate(dates[0])} → ${shortDate(dates[1])}` : feature.properties.date.slice(0, 10)}
      {" "}· cobertura ESA WorldCover 2021 · poblados OpenStreetMap</p>
  </div>;
}

export function ZoneClimate({ aoi }: { aoi: string }) {
  const [climate, setClimate] = useState<Climate | null>();
  const [error, setError] = useState(false);
  useEffect(() => {
    const request = new AbortController();
    setClimate(undefined); setError(false);
    api.climate(aoi, request.signal).then(data => { if (!request.signal.aborted) setClimate(data); })
      .catch(() => { if (!request.signal.aborted) setError(true); });
    return () => request.abort();
  }, [aoi]);
  const season = climate?.typical_season;
  const alert = climate ? climateSummary(climate)
    .replace(/(\d+)\.(\d)/g, "$1,$2")
    .replace(/\d{4}-\d{2}-\d{2}/, d => shortDate(d)) : "";
  const frost = /helada/i.test(alert);
  const updated = climate?.forecast?.fetched_at ?? climate?.fetched_at;
  return <div className="zone-climate">
    <h4>Clima de la zona</h4>
    {climate ? <>
      <p className="zone-climate-alert" data-kind={frost ? "frost" : /calor/i.test(alert) ? "heat" : /lluvia/i.test(alert) ? "rain" : "none"}>{alert}</p>
      {season && <><p className="zone-climate-season">{season.season_name.replace("septiembre", "sep").replace("noviembre", "nov")
        .replace("diciembre", "dic").replace("febrero", "feb").replace("marzo", "mar").replace("mayo", "may").replace("junio", "jun").replace("agosto", "ago")} · valores típicos</p>
      <dl className="zone-climate-values">
        <div data-v="max"><dt>Máxima</dt><dd>{number(season.typical_tmax_c, 1)} °C</dd></div>
        <div data-v="min"><dt>Mínima</dt><dd>{number(season.typical_tmin_c, 1)} °C</dd></div>
        <div data-v="rain"><dt>Lluvia/mes</dt><dd>{number(season.typical_rain_mm, 0)} mm</dd></div>
      </dl></>}
      <p className="zone-sheet-provenance">Promedio regional, no de esta mancha · NASA POWER{climate.forecast ? " · pronóstico Open-Meteo" : ""}{updated ? ` · ${shortDate(updated)}` : ""}</p>
      {climate.agricultural_calendar && <AgriCalendar cal={climate.agricultural_calendar} />}
    </> : <p role="status">{error ? "No se pudo cargar el clima. Reabre Clima para reintentar." : climate === null
      ? `Clima sin publicar. Ejecuta sarlab climate --aoi ${aoi}.` : "Consultando clima publicado…"}</p>}
  </div>;
}

/** Three direct steps for the field, built only from this zone's published data. */
export function ZoneActions({ feature, onVoice }: { feature: AlertFeature; onVoice: () => void }) {
  const rem = feature.properties.remediation;
  if (!rem) return null;
  const f = rem.factors;
  const place = rem.nearby_places?.[0];
  const where = place ? `${place.name} (${(place.distance_m / 1000).toFixed(1).replace(".", ",")} km)` : "la comunidad más cercana";
  const look = ["pérdida de vegetación"];
  if ((f.heat_score ?? 0) > 0) look.push("restos de quema");
  if (f.slope_deg != null && f.slope_deg >= 15) look.push("grietas o tierra removida en la ladera");
  if (f.soil_moisture_m3m3 != null && f.soil_moisture_m3m3 <= 0.15) look.push("suelo seco o cultivo marchito");
  if ((f.crop_ha ?? 0) > 0) look.push("daño en la chacra");
  const technique = rem.budget?.[0];
  const named = rem.recipe?.species_primary?.slice(0, 2).map(s => s.split(" (")[0]) ?? [];
  // Skip species already named in the technique (e.g. "Agroforestería con tara y aliso").
  const species = named.filter(n => !technique?.name?.toLowerCase().includes(n.split(" /")[0].toLowerCase()));
  const who = rem.recipe?.executor?.[0];
  return <><h4 className="zone-actions-title">Ruta para sanar la zona</h4><ol className="zone-actions">
    <li data-step="check"><strong>Verificar en campo</strong>
      <span className="zone-step-who">Promotor o autoridad de {where}</span>
      <ul>{look.map(item => <li key={item}>{item}</li>)}</ul></li>
    <li data-step="heal"><strong>Sanar con la naturaleza</strong>
      {rem.recipe && technique ? <ul className="zone-solutions">
        <li><b>Técnica</b> {technique.name}</li>
        {species.length > 0 && <li><b>Especies</b> {species.join(" · ")}</li>}
        {technique.timing && <li><b>Cuándo</b> {technique.timing}</li>}
        {who && <li><b>Quién</b> {who}</li>}
      </ul> : <span className="zone-step-who">La receta se elige al confirmar la causa en campo.</span>}</li>
    <li data-step="tell"><strong>Alertas por radio</strong>
      <ul><li>Boletín para radio comunal</li><li>Convocatoria minka</li></ul>
      <button type="button" className="text-button" onClick={onVoice}>Ver boletín</button></li>
  </ol></>;
}

const months = (text?: string) => {
  const list = (text ?? "").split(",").map(m => m.trim().slice(0, 3)).filter(Boolean);
  return list.length > 1 ? `${list[0]}–${list[list.length - 1]}` : list[0] ?? "";
};
const dec = (text: string) => text.replace(/(\d+)\.(\d)/g, "$1,$2")
  .replace(/^Condiciones favorables para siembra entre el (\d+) y el (.+)\.$/, "Ventana de siembra: $1 al $2.")
  .replace(/^Temperatura mínima \(([^)]+)\) inferior a la requerida \(([^)]+)\)\.$/, "Mínima $1; necesita $2.");
const statusLabel: Record<string, string> = { favorable: "Sembrar", precaucion: "Esperar", desfavorable: "No sembrar", normal: "Normal" };

/** Regional sowing calendar as coloured cards with bullet facts. */
function AgriCalendar({ cal }: { cal: NonNullable<Climate["agricultural_calendar"]> }) {
  const f = cal.crops[0]?.factors;
  return <section className="agri-calendar">
    <h4>Calendario agrícola · próximos {cal.outlook_days} días</h4>
    {f && <p className="agri-outlook">Mín. {number(f.avg_tmin_c, 1)} °C · Máx. {number(f.avg_tmax_c, 1)} °C · Lluvia {number(f.rain_7d_mm, 1)} mm</p>}
    <ul className="agri-cards">
      {cal.crops.map(crop => <li key={crop.id} data-status={crop.status}>
        <div><strong>{crop.name.split(" / ")[0]}</strong><span>{statusLabel[crop.status] ?? crop.status}</span></div>
        <ul>
          <li>{dec(crop.guidance)}</li>
          <li>Siembra: {months(crop.sowing_season_months)}</li>
          <li>Altura: {number(crop.altitude_m[0], 0)}–{number(crop.altitude_m[1], 0)} m</li>
        </ul>
      </li>)}
      {cal.livestock && <li data-status={cal.livestock.status}>
        <div><strong>Ganado en puna</strong><span>{statusLabel[cal.livestock.status] ?? cal.livestock.status}</span></div>
        <ul><li>{cal.livestock.guidance}</li>
          <li>Altura: {number(cal.livestock.altitude_m[0], 0)}–{number(cal.livestock.altitude_m[1], 0)} m</li></ul>
      </li>}
    </ul>
    <p className="zone-sheet-provenance">Sugerencia regional · la fecha tradicional de cada comunidad manda.</p>
  </section>;
}
