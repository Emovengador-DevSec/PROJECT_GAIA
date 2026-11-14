import { useEffect, useState } from "react";
import { api, type Agriculture } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";
import { formatDate } from "../../lib/formatDate";

type Classes = { cropland_low_slope_ha?: number | null; cropland_steep_ha?: number | null; cropland_slope_unknown_ha?: number | null };

export function AgricultureEvidence({ data, impact }: { data: Agriculture; impact?: Classes | null }) {
  const classes = impact ?? data.region;
  const [climate, setClimate] = useState<import("../../lib/api").Climate | null>();
  const [promoterLog, setPromoterLog] = useState<{ community: string; crop: string; date: string; sign: string }>(() => {
    try {
      const saved = localStorage.getItem("gaia_promoter_log");
      return saved ? JSON.parse(saved) : { community: "", crop: "Papa nativa", date: "", sign: "" };
    } catch {
      return { community: "", crop: "Papa nativa", date: "", sign: "" };
    }
  });
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    const request = new AbortController();
    api.climate("ayacucho-huanta", request.signal).then(setClimate).catch(() => undefined);
    return () => request.abort();
  }, []);

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
  const calendarEval = climate?.agricultural_calendar;

  return <section className="community-block agriculture-evidence">
    <h4>Cultivos y pendiente</h4>
    <p><strong>{number(classes.cropland_steep_ha)} ha</strong> de cultivos con cambio HV en laderas de más de {data.threshold_deg}°{impact ? " en este lugar." : " en la zona NISAR de Ayacucho."}</p>
    <dl className="community-metrics">
      <div><dt>Hasta {data.threshold_deg}°</dt><dd>{number(classes.cropland_low_slope_ha)} <small>ha</small></dd></div>
      <div><dt>Sin pendiente válida</dt><dd>{number(classes.cropland_slope_unknown_ha)} <small>ha</small></dd></div>
    </dl>
    <p className="muted">Una ladera con menor cobertura vegetal podría ser más sensible a la erosión durante las lluvias. El radar y la pendiente no confirman suelo desnudo ni pérdida de suelo.</p>
    <details className="technical-details"><summary>Fuente y método de pendiente</summary>
      <p className="muted">{data.note}</p>
      {data.erosion_reference && <p><a href={data.erosion_reference.url} target="_blank" rel="noreferrer">{data.erosion_reference.name}</a>. También influyen la intensidad de lluvia, el suelo y su cobertura.</p>}
      <p className="muted"><a href={data.source_url} target="_blank" rel="noreferrer">{data.source}</a> · rejilla de {data.grid_m} m · archivado el {formatDate(data.retrieved_at)}. DEM compuesto sin una fecha única de observación. <a href={data.attribution_url} target="_blank" rel="noreferrer">Atribuciones y licencias</a>.</p>
    </details>

    {typical && (
      <div className="seasonal-normals-box" style={{ margin: "1rem 0", padding: "0.75rem", background: "var(--surface-subtle, #1a1a1a)", borderRadius: "6px" }}>
        <h4 style={{ margin: "0 0 0.5rem" }}>Clima estacional de referencia</h4>
        <p style={{ margin: 0, fontSize: "0.9rem" }}>{typical.description}</p>
        <dl className="community-metrics" style={{ marginTop: "0.5rem" }}>
          <div><dt>Máxima típica</dt><dd>{typical.typical_tmax_c} <small>°C</small></dd></div>
          <div><dt>Mínima típica</dt><dd>{typical.typical_tmin_c} <small>°C</small></dd></div>
          <div><dt>Lluvia mensual</dt><dd>{typical.typical_rain_mm} <small>mm</small></dd></div>
          <div><dt>Umbral P90 calor</dt><dd>{typical.p90_tmax_c} <small>°C</small></dd></div>
        </dl>
      </div>
    )}

    {calendarEval && (
      <div className="smart-calendar-box" style={{ margin: "1rem 0" }}>
        <div className="source-row">
          <span className="source-label">Calendario agrícola inteligente</span>
          <span className="badge-provisional">Pronóstico Open-Meteo & NASA POWER</span>
        </div>
        <h4>Ventanas de siembra recomendadas ({calendarEval.season})</h4>
        <p className="muted">
          Cruce del calendario fenológico, humedad del suelo (0–10 cm) y pronóstico a {calendarEval.outlook_days} días.
        </p>

        <div className="case-list" style={{ marginTop: "0.75rem", gap: "8px" }}>
          {calendarEval.crops.map(crop => {
            const statusColor = crop.status === "favorable" ? "#4CAF50" : crop.status === "precaucion" ? "#FF9800" : "#9E9E9E";
            const statusLabel = crop.status === "favorable" ? "Favorable" : crop.status === "precaucion" ? "Precaución" : "Fuera de época";
            return (
              <div key={crop.id} className="case" style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
                  <strong>{crop.name} <small className="muted">({crop.scientific})</small></strong>
                  <span className="alert-level" style={{ borderColor: statusColor, color: statusColor }}>
                    {statusLabel}
                  </span>
                </div>
                <p style={{ margin: "2px 0", fontSize: "0.85rem" }}>{crop.guidance}</p>
                <small className="muted">
                  Ventana tradicional: {crop.sowing_season_months} · Altitud: {crop.altitude_m[0]} a {crop.altitude_m[1]} m
                </small>
                {crop.factors.soil_moisture_m3m3 != null && (
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
            <p style={{ margin: "2px 0", fontSize: "0.85rem" }}>{calendarEval.livestock.guidance}</p>
            <small className="muted">Altitud: {calendarEval.livestock.altitude_m[0]} a {calendarEval.livestock.altitude_m[1]} m</small>
          </div>
        )}
      </div>
    )}

    <div className="promoter-log-section" style={{ margin: "1rem 0", padding: "0.75rem", background: "var(--surface-subtle, #1a1a1a)", borderRadius: "6px" }}>
      <h4 style={{ margin: "0 0 0.25rem" }}>Registro de saber tradicional de la comunidad</h4>
      <p className="muted" style={{ margin: "0 0 0.5rem", fontSize: "0.85rem" }}>
        El saber local manda. El promotor agrario o comunero puede registrar aquí la fecha tradicional y señas de la naturaleza de su comunidad.
      </p>
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

    <div className="agricultural-context"><h4>Contexto histórico SENAMHI</h4>
    <ol className="agricultural-calendar">{data.calendar.map(item => <li key={item.url}><strong>{item.label}</strong>
      <p>{item.text}</p><a href={item.url} target="_blank" rel="noreferrer">{item.source} · {formatDate(item.date)}</a></li>)}</ol>
    <p className="muted">{data.calendar_note}</p>
    <p className="muted">La cosecha y la preparación del terreno son hipótesis para contrastar con HLS, registros locales, humedad y focos de calor.</p></div>
    <p className="agricultural-print-source">Pendiente: <a href={data.source_url}>{data.source}</a>, rejilla de {data.grid_m} m. Contexto estacional de otras localidades y campañas: {data.calendar.map((item, index) => <span key={item.url}>{index > 0 && " · "}<a href={item.url}>{item.label}</a></span>)}. Cosecha y erosión por verificar.</p>
  </section>;
}

export function AgricultureStory() {
  const [data, setData] = useState<Agriculture | null>();
  const [error, setError] = useState(false);
  useEffect(() => {
    const request = new AbortController();
    api.agriculture(request.signal).then(setData).catch(() => { if (!request.signal.aborted) setError(true); });
    return () => request.abort();
  }, []);
  return data ? <AgricultureEvidence data={data} /> : <p className="muted" role="status">{error ? "No se pudo consultar la pendiente agrícola." : data === null ? "Aún no hay un cruce de cultivos y pendiente publicado." : "Consultando cultivos y pendiente…"}</p>;
}
