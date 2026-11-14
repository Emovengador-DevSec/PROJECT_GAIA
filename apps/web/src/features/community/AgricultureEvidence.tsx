import { useEffect, useState } from "react";
import { api, type Agriculture } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";
import { formatDate } from "../../lib/formatDate";

type Classes = { cropland_low_slope_ha?: number | null; cropland_steep_ha?: number | null; cropland_slope_unknown_ha?: number | null };

export function AgricultureEvidence({ data, impact }: { data: Agriculture; impact?: Classes | null }) {
  const classes = impact ?? data.region;
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
    <div className="agricultural-context"><h4>Contexto agrícola de Ayacucho</h4>
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
