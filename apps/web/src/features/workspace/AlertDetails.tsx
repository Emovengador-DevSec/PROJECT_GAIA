import type { AlertFeature } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { ApplicationReference, LearnMore } from "./Resources";
import { CountUp } from "./CountUp";

const number = (value?: number | null) => typeof value === "number" && Number.isFinite(value)
  ? new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(value) : "Sin dato";

export function AlertDetails({ feature, onBack, onResources }: { feature: AlertFeature; onBack: () => void; onResources: () => void }) {
  const p = feature.properties;
  const source = p.source_kind === "primary" ? "NISAR · fuente principal" : `${p.source} · complementario`;
  const shareUrl = new URL(window.location.href);
  shareUrl.searchParams.set("alert", p.id);
  const message = ["GAIA Alerta", p.title, p.place, formatDate(p.date), source, p.note, shareUrl.href].join("\n");
  const external = p.source_url?.startsWith("https://") ? p.source_url : undefined;
  const exposure = p.exposure;
  const rawSources: unknown = exposure?.sources;
  const exposureSources: unknown[] = Array.isArray(rawSources) ? rawSources
    : rawSources && typeof rawSources === "object" ? Object.values(rawSources) : [];
  return <article className="alert-detail" data-kind={p.kind}>
    <button type="button" className="text-button detail-back" onClick={onBack}>Volver a las observaciones</button>
    <div className="source-row"><span className="source-label">{source}</span><span className="alert-level" data-level={p.level}>Prioridad {p.level}</span></div>
    <h3>{p.title}</h3>
    <p className="alert-place">{p.place}</p>
    <p className="muted">{formatDate(p.date)}</p>
    <dl className="observation-metrics">
      {p.metrics.magnitude !== undefined && <div><dt>Magnitud</dt><dd><CountUp value={p.metrics.magnitude} decimals={1} /></dd></div>}
      {p.metrics.depth_km !== undefined && <div><dt>Profundidad</dt><dd><CountUp value={p.metrics.depth_km} decimals={1} /> <small>km</small></dd></div>}
      {p.metrics.frp_mw !== undefined && <div><dt>Potencia radiativa</dt><dd><CountUp value={p.metrics.frp_mw} decimals={1} /> <small>MW</small></dd></div>}
      {p.metrics.count !== undefined && <div><dt>Detecciones en la celda</dt><dd><CountUp value={p.metrics.count} /> <small>focos</small></dd></div>}
      {p.metrics.area_ha != null && <div><dt>Área con cambio</dt><dd><CountUp value={p.metrics.area_ha} decimals={1} /> <small>ha</small></dd></div>}
    </dl>
    <p className="observation-note">{p.note}</p>
    <p className="muted">Confianza o revisión · {p.confidence}</p>
    {p.provisional && <p className="badge-provisional">Producto NISAR provisional · calibración sujeta a revisión.</p>}

    <section className="exposure-section">
      <h4>¿A quién afecta?</h4>
      {exposure ? <>
        <dl className="exposure-metrics">
          <div><dt>Personas expuestas</dt><dd>{number(exposure.people)}</dd></div>
          <div><dt>Cultivos expuestos</dt><dd>{number(exposure.crop_ha)} <small>ha</small></dd></div>
          <div><dt>Bosque expuesto</dt><dd>{number(exposure.forest_ha)} <small>ha</small></dd></div>
          <div><dt>Centros poblados cercanos</dt><dd>{number(exposure.settlements)}</dd></div>
        </dl>
        <p className="muted">{exposure.note ?? "Estimación de exposición basada en la ubicación y las fuentes disponibles."}</p>
        {!!exposureSources.length && <ul className="source-list">{exposureSources.map((value, index) => {
          const text = typeof value === "string" ? value : value && typeof value === "object" && ("source" in value || "name" in value)
            ? String("source" in value ? value.source : "name" in value ? value.name : "Fuente de exposición") + ("date" in value ? ` · ${String(value.date)}` : "") : "Fuente de exposición";
          return <li key={index}>{text}</li>;
        })}</ul>}
      </> : <p className="empty-inline">La exposición aún no está calculada. Se necesitan capas de población, cobertura del suelo y centros poblados para estimar personas y cultivos.</p>}
    </section>

    {!!p.granules?.length && <details className="technical-details"><summary>Gránulos de origen</summary><ul className="granule-list">{p.granules.map(granule => <li key={granule}>{granule}</li>)}</ul></details>}
    <div className="detail-actions">
      <a className="primary-action" href={`https://wa.me/?text=${encodeURIComponent(message)}`} target="_blank" rel="noopener noreferrer">Compartir alerta</a>
      <button type="button" className="secondary-action" onClick={() => window.print()}>Imprimir ficha</button>
    </div>
    {external && <a className="source-link" href={external} target="_blank" rel="noopener noreferrer">Consultar la observación original ↗</a>}
    <ApplicationReference kind={p.kind} aoi={p.aoi_id} />
    <LearnMore kind={p.kind} onResources={onResources} />
  </article>;
}
