import type { CommunityDetail } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";

const indeci = "https://www.gob.pe/institucion/indeci/campa%C3%B1as/1582-preparados-ante-incendios-forestales";
const plan = "https://www.gob.pe/10165";
const rainGuide = "https://www.gob.pe/37201-recomendaciones-para-protegerte-de-las-lluvias-intensas";
const official = [
  ["SENAMHI · avisos meteorológicos", "https://www.senamhi.gob.pe/?p=avisos-meteorologicos"],
  ["INDECI · preparación", plan],
  ["IGP · sismos recientes", "https://ultimosismo.igp.gob.pe/"],
  ["OVI–INGEMMET · vigilancia volcánica", "http://ovi.ingemmet.gob.pe/panelview/index.html"],
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
  const observedAt = mainReason?.[3] ?? detail.as_of;
  const intro = `GAIA · ${detail.name}. ${labels[level]}. ${mainReason?.[1] ?? "FIRMS / USGS"} · ${formatDate(observedAt)}${observedAt.length === 10 ? " (día UTC)" : ""}. Indicador informativo.`;
  const share = `${intro.slice(0, Math.max(0, 499 - link.href.length))} ${link.href}`;
  const fire = reasons.some(reason => reason[1] === "NASA FIRMS");
  const excessRain = reasons.some(reason => reason[2].includes("huaicos"));
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
        <li>Naranja · foco dentro de ese radio en 7 días, sismo M ≥ {number(detail.rules.quake_magnitude)} a {detail.rules.quake_radius_km} km o menos en 24 h, {detail.rules.heat_days} días consecutivos de calor extremo o lluvia de 30 días ≥ {number(detail.rules.rain_excess_ratio)} veces la climatología de 1991–2020.</li>
        <li>Amarillo · lluvia de 30 días por debajo del {number(detail.rules.rain_ratio * 100)} % de la climatología. La posible exposición de suelo agrícola requiere evidencia adicional.</li>
        <li>Verde · fuentes recientes disponibles y ningún umbral observado.</li>
      </ul>
      <p>El umbral de lluvia es una regla inicial de seguimiento de GAIA. La celda regional no mide cada quebrada y el acumulado no predice un huaico. Revisa los avisos oficiales de SENAMHI y las indicaciones de Defensa Civil.</p>
    </details>
    <p><strong>Qué hacer.</strong> {fire ? <>Evita acercarte al fuego. Si observas un incendio, avisa a Defensa Civil o llama a <a href="tel:116">Bomberos (116)</a>.</> :
      excessRain ? <>Identifica las zonas vulnerables de tu comunidad y acuerda rutas hacia zonas seguras con tu familia.</> :
      <>Identifica una zona segura y acuerda una ruta de evacuación con tu familia.</>}
      {" "}<a href={fire ? indeci : excessRain ? rainGuide : plan} target="_blank" rel="noreferrer">Guía de INDECI</a></p>
    <details className="technical-details"><summary>Fuentes oficiales en Perú</summary><ul className="source-list">
      {official.map(([text, url]) => <li key={url}><a href={url} target="_blank" rel="noreferrer">{text}</a></li>)}
    </ul></details>
    <div className="detail-actions">
      <a className="primary-action" href={`https://wa.me/?text=${encodeURIComponent(share)}`} target="_blank" rel="noreferrer">Compartir por WhatsApp</a>
      <button type="button" className="secondary-action" onClick={() => window.print()}>Imprimir ficha</button>
    </div>
  </section>;
}
