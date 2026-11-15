import { useEffect, useState } from "react";
import { api, type AlertFeature, type Climate } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";
import { formatDate } from "../../lib/formatDate";
import { climateSummary } from "./actionSummaryModel";

export function exposureSummary(feature: AlertFeature) {
  const e = feature.properties.exposure;
  if (!e) return "Exposición sin publicar para esta mancha";
  return [e.grassland_ha != null ? `Pastizal ${number(e.grassland_ha)} ha` : null,
    e.crop_ha != null && e.crop_ha > 0 ? `Cultivo ${number(e.crop_ha)} ha` : null,
    e.people != null ? `${number(e.people, 0)} personas estimadas` : "Población sin dato válido",
    e.settlements != null ? `${number(e.settlements, 0)} poblados${e.settlement_buffer_m != null
      ? ` a ≤ ${number(e.settlement_buffer_m / 1000)} km` : " cercanos (radio sin publicar)"}` : null,
  ].filter(Boolean).join(" · ");
}

export function ZoneDiagnosis({ feature }: { feature: AlertFeature }) {
  const rem = feature.properties.remediation!;
  const names: Record<string, string> = { slope_deg: "pendiente", soil_moisture_m3m3: "humedad del suelo",
    crop_ha: "cultivo expuesto", heat_count: "focos cercanos", quake_magnitude: "sismo", rain_mm_7d: "lluvia" };
  const evidence = (rem.cause_factor_ids ?? []).map(id => names[id]).filter(Boolean);
  return <div className="zone-diagnosis-brief">
    <p>{!rem.cause_factor_ids ? "Evidencia de atribución sin publicar. Consulta Ver más." : evidence.length ? `Base de la evaluación: ${evidence.join(" y ")}. La causa requiere verificación en campo.`
      : "Sin evidencia suficiente para atribuir una causa. Verificar en campo."}</p>
    <p><strong>¿A quién afecta?</strong> {exposureSummary(feature)}</p>
    <p className="zone-sheet-provenance">NISAR · provisional · {rem.sources_nisar.dates?.join(" → ") || feature.properties.date.slice(0, 10)}
      {" "}· {feature.properties.exposure ? "contexto: WorldCover / poblados OSM" : "exposición sin publicar"}</p>
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
  return <div className="zone-climate">
    <h4>Clima estacional</h4>
    <p className="muted">Contexto regional del territorio, no una medición de esta mancha.</p>
    {climate ? <>
      <p className="status-message">{climateSummary(climate)}</p>
      {season && <><p>{season.season_name}</p><dl className="zone-climate-values">
        <div><dt>Máxima típica</dt><dd>{number(season.typical_tmax_c, 1)} °C</dd></div>
        <div><dt>Mínima típica</dt><dd>{number(season.typical_tmin_c, 1)} °C</dd></div>
        <div><dt>Lluvia mensual típica</dt><dd>{number(season.typical_rain_mm, 1)} mm</dd></div>
      </dl></>}
      <p className="muted">Complementario · {climate.source} · {formatDate(climate.fetched_at)}</p>
      {climate.forecast && <p className="muted">{climate.forecast.source} · {formatDate(climate.forecast.fetched_at)}</p>}
      {climate.agricultural_calendar && <details><summary>Calendario agrícola regional</summary>
        <p>{climate.agricultural_calendar.promoter_note}</p>
        {climate.agricultural_calendar.crops.map(crop => <p key={crop.id}><strong>{crop.name}:</strong> {crop.guidance}</p>)}
      </details>}
    </> : <p role="status">{error ? "No se pudo cargar el clima. Reabre Clima para reintentar." : climate === null
      ? `Clima sin publicar. Ejecuta sarlab climate --aoi ${aoi}.` : "Consultando clima publicado…"}</p>}
  </div>;
}
