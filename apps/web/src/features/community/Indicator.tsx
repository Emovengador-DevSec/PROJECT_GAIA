import type { CommunityDetail } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";

const indeci = "https://www.gob.pe/institucion/indeci/campa%C3%B1as/1582-preparados-ante-incendios-forestales";
const plan = "https://www.gob.pe/10165";
const official = [
  ["SENAMHI · avisos meteorológicos", "https://www.senamhi.gob.pe/?p=avisos-meteorologicos"],
  ["INDECI · preparación", plan],
  ["IGP · sismos recientes", "https://ultimosismo.igp.gob.pe/"],
  ["OVI–INGEMMET · peligros volcánicos", "https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/SERV_OVI/MapServer"],
];
const labels = {
  red: "Rojo · foco térmico reciente", orange: "Naranja · seguimiento cercano",
  yellow: "Amarillo · revisar condiciones", green: "Verde · sin señales en las fuentes consultadas",
  unavailable: "Gris · datos insuficientes",
};

export function Indicator({ detail }: { detail: CommunityDetail }) {
  const { level, reasons, live_complete, weather_at } = detail.indicator;
  const mainReason = reasons[0];
  const link = new URL(location.pathname, location.origin);
  link.searchParams.set("lugar", detail.id);
  const intro = `GAIA · ${detail.name}. ${labels[level]}. ${mainReason?.[1] ?? "FIRMS / USGS"} · ${formatDate(mainReason?.[3] ?? detail.as_of)}. Indicador informativo.`;
  const share = `${intro.slice(0, Math.max(0, 499 - link.href.length))} ${link.href}`;
  const fire = reasons.some(reason => reason[1] === "NASA FIRMS");
  return <section className="community-block community-indicator">
    <h4>Semáforo comunitario</h4>
    <p className="community-status" data-level={level}>{labels[level]}</p>
    <p className="muted">Indicador informativo de GAIA, no es una alerta oficial.</p>
    {reasons.length > 0 && <ul>{reasons.map(([, source, reason, date]) =>
      <li key={reason}>{reason} · {source} · <time dateTime={date}>{formatDate(date)}</time></li>)}</ul>}
    {!live_complete && <p className="muted">Alguna fuente en vivo está retrasada o no disponible.</p>}
    {!weather_at && <p className="muted">Las reglas de calor y lluvia requieren datos recientes de NASA POWER.</p>}
    {weather_at && <p className="muted">El calor y la lluvia se estiman en la celda regional de Ayacucho · {formatDate(weather_at)}.</p>}
    <details className="technical-details"><summary>¿Por qué este color?</summary>
      <ul>
        <li>Rojo · foco FIRMS a {detail.rules.fire_radius_km} km o menos en 24 h.</li>
        <li>Naranja · foco dentro de ese radio en 7 días, sismo M ≥ {number(detail.rules.quake_magnitude)} a {detail.rules.quake_radius_km} km o menos en 24 h, o {detail.rules.heat_days} días consecutivos de calor extremo.</li>
        <li>Amarillo · lluvia de 30 días por debajo del {number(detail.rules.rain_ratio * 100)} % de la climatología. La posible exposición de suelo agrícola requiere evidencia adicional.</li>
        <li>Verde · fuentes recientes disponibles y ningún umbral observado.</li>
      </ul>
    </details>
    <p><strong>Qué hacer.</strong> {fire ? <>Evita acercarte al fuego. Si observas un incendio, avisa a Defensa Civil o llama a <a href="tel:116">Bomberos (116)</a>.</> :
      <>Identifica una zona segura y acuerda una ruta de evacuación con tu familia.</>}
      {" "}<a href={fire ? indeci : plan} target="_blank" rel="noreferrer">Guía de INDECI</a></p>
    <details className="technical-details"><summary>Fuentes oficiales en Perú</summary><ul className="source-list">
      {official.map(([text, url]) => <li key={url}><a href={url} target="_blank" rel="noreferrer">{text}</a></li>)}
    </ul></details>
    <div className="detail-actions">
      <a className="primary-action" href={`https://wa.me/?text=${encodeURIComponent(share)}`} target="_blank" rel="noreferrer">Compartir por WhatsApp</a>
      <button type="button" className="secondary-action" onClick={() => window.print()}>Imprimir ficha</button>
    </div>
  </section>;
}
