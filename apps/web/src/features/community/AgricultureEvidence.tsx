import { useEffect, useState } from "react";
import { api, type Agriculture, type Climate } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";
import { formatDate } from "../../lib/formatDate";

type Classes = { cropland_low_slope_ha?: number | null; cropland_steep_ha?: number | null; cropland_slope_unknown_ha?: number | null };

export function AgricultureSources({ data }: { data: Agriculture }) {
  return <>
    <p className="muted">{data.note}</p>
    {data.erosion_reference && <p><a href={data.erosion_reference.url} target="_blank" rel="noreferrer">{data.erosion_reference.name}</a>. También influyen la intensidad de lluvia, el suelo y su cobertura.</p>}
    <p className="muted"><a href={data.source_url} target="_blank" rel="noreferrer">{data.source}</a> · rejilla de {data.grid_m} m · archivado el {formatDate(data.retrieved_at)}. DEM compuesto sin una fecha única de observación. <a href={data.attribution_url} target="_blank" rel="noreferrer">Atribuciones y licencias</a>.</p>
  </>;
}

function AgricultureSection({ compact, title, children }: { compact: boolean; title: string; children: React.ReactNode }) {
  return compact ? <details className="story-disclosure"><summary>{title}</summary>{children}</details> : <>{children}</>;
}

const cropStatus = {
  favorable: { label: "Favorable", color: "#4CAF50" },
  precaucion: { label: "Precaución", color: "#FF9800" },
  fuera_de_temporada: { label: "Fuera de época", color: "#9E9E9E" },
};

export function AgriculturalCalendar({ climate, compact = false }: { climate: Climate; compact?: boolean }) {
  const calendarEval = climate.agricultural_calendar;
  if (!calendarEval) return null;
  const cropFactors = calendarEval.crops[0]?.factors;
  const hasOutlook = !!calendarEval.outlook_days;

  return <div className="smart-calendar-box" style={{ margin: "1rem 0" }}>
    {compact ? <>
      <p className="story-meta">{calendarEval.season} · {formatDate(calendarEval.evaluated_at)}</p>
      {hasOutlook && <p className="story-meta">Pronóstico regional{climate.forecast?.source && ` · ${climate.forecast.source}`}</p>}
      {hasOutlook ? <dl className="community-metrics">
        <div><dt>Humedad de suelo (0–10 cm)</dt><dd>{cropFactors?.soil_moisture_m3m3 != null ? `${number(cropFactors.soil_moisture_m3m3 * 100, 1)} %` : "Sin dato"}</dd></div>
        <div><dt>Lluvia en {calendarEval.outlook_days} días</dt><dd>{cropFactors?.rain_7d_mm != null ? `${number(cropFactors.rain_7d_mm, 1)} mm` : "Sin dato"}</dd></div>
      </dl> : <p className="story-meta">Pronóstico sin publicar. Consulta las ventanas tradicionales.</p>}
    </> : <>
      <div className="source-row">
        <span className="source-label">Calendario agrícola inteligente</span>
        <span className="badge-provisional">Pronóstico Open-Meteo & NASA POWER</span>
      </div>
      <h4>Ventanas de siembra recomendadas ({calendarEval.season})</h4>
      <p className="muted">
        Cruce del calendario fenológico, humedad del suelo (0–10 cm) y pronóstico a {calendarEval.outlook_days} días.
      </p>
    </>}

    <div className="case-list" style={{ marginTop: "0.75rem", gap: "8px" }}>
      {calendarEval.crops.map(crop => {
        const { label, color } = cropStatus[crop.status] ?? cropStatus.fuera_de_temporada;
        return (
          <div key={crop.id} className="case" style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
              <strong>{crop.name} <small className="muted">({crop.scientific})</small></strong>
              {(!compact || hasOutlook) && <span className="alert-level" style={{ borderColor: color, color }}>{label}</span>}
            </div>
            {(!compact || hasOutlook) && <p style={{ margin: "2px 0", fontSize: "0.85rem" }}>{crop.guidance}</p>}
            <small className="muted">
              Ventana tradicional: {crop.sowing_season_months} · Altitud: {crop.altitude_m[0]} a {crop.altitude_m[1]} m
            </small>
            {!compact && crop.factors.soil_moisture_m3m3 != null && (
              <small className="muted">
                Humedad de suelo: {(crop.factors.soil_moisture_m3m3 * 100).toFixed(1)}% · Lluvia 7 días: {crop.factors.rain_7d_mm ?? 0} mm
              </small>
            )}
          </div>
        );
      })}
    </div>

    {calendarEval.livestock && (
      <div className="case" style={{ marginTop: "0.75rem", flexDirection: "column", alignItems: "flex-start", gap: "4px", borderLeft: "3px solid #00BCD4" }}>
        <strong>{calendarEval.livestock.name} (Pisos de puna)</strong>
        {(!compact || hasOutlook) && <p style={{ margin: "2px 0", fontSize: "0.85rem" }}>{calendarEval.livestock.guidance}</p>}
        <small className="muted">Altitud: {calendarEval.livestock.altitude_m[0]} a {calendarEval.livestock.altitude_m[1]} m</small>
      </div>
    )}
  </div>;
}

export function useAgriculturalClimate(enabled: boolean) {
  const [climate, setClimate] = useState<Climate | null>();
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    const request = new AbortController();
    api.climate("ayacucho-huanta", request.signal).then(result => {
      if (!request.signal.aborted) setClimate(result);
    }).catch(() => {
      if (!request.signal.aborted) setError(true);
    });
    return () => request.abort();
  }, [enabled]);
  return { climate, error };
}

export function AgricultureEvidence({ data, impact, compact = false, climate: storyClimate }: {
  data: Agriculture; impact?: Classes | null; compact?: boolean; climate?: Climate | null;
}) {
  const classes = impact ?? data.region;
  const { climate: communityClimate } = useAgriculturalClimate(!compact);
  const climate = compact ? storyClimate : communityClimate;
  const [promoterLog, setPromoterLog] = useState<{ community: string; crop: string; date: string; sign: string }>(() => {
    try {
      const saved = localStorage.getItem("gaia_promoter_log");
      return saved ? JSON.parse(saved) : { community: "", crop: "Papa nativa", date: "", sign: "" };
    } catch {
      return { community: "", crop: "Papa nativa", date: "", sign: "" };
    }
  });
  const [savedNotice, setSavedNotice] = useState(false);

  const saveLog = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      localStorage.setItem("gaia_promoter_log", JSON.stringify(promoterLog));
      setSavedNotice(true);
      setTimeout(() => setSavedNotice(false), 3000);
    } catch {
      /* ignore storage errors */
    }
  };

  const typical = climate?.typical_season;
  const area = (value?: number | null) => value == null ? "Sin dato" : <>{number(value)} <small>ha</small></>;

  return <section className="community-block agriculture-evidence">
    {!compact && <h4>Cultivos y pendiente</h4>}
    {compact ? <p className="story-meta">Superficie cultivada dentro de las manchas de cambio HV.</p>
      : <p><strong>{area(classes.cropland_steep_ha)}</strong> de cultivos con cambio HV en laderas de más de {data.threshold_deg}°{impact ? " en este lugar." : " en la zona NISAR de Ayacucho."}</p>}
    <dl className="community-metrics">
      {compact && <div><dt>Más de {data.threshold_deg}°</dt><dd>{area(classes.cropland_steep_ha)}</dd></div>}
      <div><dt>Hasta {data.threshold_deg}°</dt><dd>{area(classes.cropland_low_slope_ha)}</dd></div>
      <div><dt>Sin pendiente válida</dt><dd>{area(classes.cropland_slope_unknown_ha)}</dd></div>
    </dl>
    {compact ? <p className="story-meta">Cobertura agrícola y pendiente estimadas. Erosión y suelo desnudo por verificar.</p> : <>
      <p className="muted">Una ladera con menor cobertura vegetal podría ser más sensible a la erosión durante las lluvias. El radar y la pendiente no confirman suelo desnudo ni pérdida de suelo.</p>
      <details className="technical-details"><summary>Fuente y método de pendiente</summary><AgricultureSources data={data} /></details>
    </>}

    {typical && <AgricultureSection compact={compact} title="Clima estacional">
      <div className="seasonal-normals-box" style={{ margin: "1rem 0", padding: "0.75rem", background: "var(--surface-subtle, #1a1a1a)", borderRadius: "6px" }}>
        <h4 style={{ margin: "0 0 0.5rem" }}>{compact ? typical.season_name : "Clima estacional de referencia"}</h4>
        {compact ? <p className="story-meta">Referencia regional · {climate.source}</p>
          : <p style={{ margin: 0, fontSize: "0.9rem" }}>{typical.description}</p>}
        <dl className="community-metrics" style={{ marginTop: "0.5rem" }}>
          <div><dt>Máxima típica</dt><dd>{typical.typical_tmax_c} <small>°C</small></dd></div>
          <div><dt>Mínima típica</dt><dd>{typical.typical_tmin_c} <small>°C</small></dd></div>
          <div><dt>Lluvia mensual</dt><dd>{typical.typical_rain_mm} <small>mm</small></dd></div>
          <div><dt>Umbral P90 calor</dt><dd>{typical.p90_tmax_c} <small>°C</small></dd></div>
        </dl>
      </div>
    </AgricultureSection>}

    {!compact && climate && <AgriculturalCalendar climate={climate} />}

    <AgricultureSection compact={compact} title="Registrar saber tradicional">
    <div className="promoter-log-section" style={{ margin: "1rem 0", padding: "0.75rem", background: "var(--surface-subtle, #1a1a1a)", borderRadius: "6px" }}>
        {!compact && <><h4 style={{ margin: "0 0 0.25rem" }}>Registro de saber tradicional de la comunidad</h4>
        <p className="muted" style={{ margin: "0 0 0.5rem", fontSize: "0.85rem" }}>
        El saber local manda. El promotor agrario o comunero puede registrar aquí la fecha tradicional y señas de la naturaleza de su comunidad.
        </p></>}
      <form onSubmit={saveLog} style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <label style={{ fontSize: "0.8rem" }}>
            Comunidad / Sector
            <input
              type="text"
              placeholder="Ej. Huanta, Macachacra"
              value={promoterLog.community}
              onChange={e => setPromoterLog({ ...promoterLog, community: e.target.value })}
              style={{ width: "100%", padding: "4px 8px", marginTop: "2px" }}
            />
          </label>
          <label style={{ fontSize: "0.8rem" }}>
            Cultivo tradicional
            <select
              value={promoterLog.crop}
              onChange={e => setPromoterLog({ ...promoterLog, crop: e.target.value })}
              style={{ width: "100%", padding: "4px 8px", marginTop: "2px" }}
            >
              <option value="Papa nativa">Papa nativa</option>
              <option value="Maíz">Maíz</option>
              <option value="Quinua">Quinua</option>
              <option value="Habas">Habas</option>
            </select>
          </label>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <label style={{ fontSize: "0.8rem" }}>
            Fecha acostumbrada de siembra
            <input
              type="text"
              placeholder="Ej. Primera quincena de noviembre"
              value={promoterLog.date}
              onChange={e => setPromoterLog({ ...promoterLog, date: e.target.value })}
              style={{ width: "100%", padding: "4px 8px", marginTop: "2px" }}
            />
          </label>
          <label style={{ fontSize: "0.8rem" }}>
            Seña de la naturaleza observada
            <input
              type="text"
              placeholder="Ej. Floración de sanky, viento del norte"
              value={promoterLog.sign}
              onChange={e => setPromoterLog({ ...promoterLog, sign: e.target.value })}
              style={{ width: "100%", padding: "4px 8px", marginTop: "2px" }}
            />
          </label>
        </div>
        <button type="submit" className="secondary-action" style={{ alignSelf: "flex-start", marginTop: "4px" }}>
          {savedNotice ? "✓ Guardado en tu dispositivo" : "Guardar fecha tradicional"}
        </button>
      </form>
    </div>

    </AgricultureSection>
    <AgricultureSection compact={compact} title="Observaciones históricas de SENAMHI">
    <div className="agricultural-context">{!compact && <h4>Contexto histórico SENAMHI</h4>}
    <ol className="agricultural-calendar">{data.calendar.map(item => <li key={item.url}><strong>{item.label}</strong>
      <p>{item.text}</p>{compact ? <small className="story-meta">{formatDate(item.date)}</small>
        : <a href={item.url} target="_blank" rel="noreferrer">{item.source} · {formatDate(item.date)}</a>}</li>)}</ol>
    <p className="muted">{data.calendar_note}</p>
    {!compact && <p className="muted">La cosecha y la preparación del terreno son hipótesis para contrastar con HLS, registros locales, humedad y focos de calor.</p>}</div>
    </AgricultureSection>
    <p className="agricultural-print-source">Pendiente: <a href={data.source_url}>{data.source}</a>, rejilla de {data.grid_m} m. Contexto estacional de otras localidades y campañas: {data.calendar.map((item, index) => <span key={item.url}>{index > 0 && " · "}<a href={item.url}>{item.label}</a></span>)}. Cosecha y erosión por verificar.</p>
  </section>;
}

export function useStoryAgriculture(enabled: boolean) {
  const [data, setData] = useState<Agriculture | null>();
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    const request = new AbortController();
    api.agriculture(request.signal).then(result => { if (!request.signal.aborted) setData(result); })
      .catch(() => { if (!request.signal.aborted) setError(true); });
    return () => request.abort();
  }, [enabled]);
  return { data, error };
}
