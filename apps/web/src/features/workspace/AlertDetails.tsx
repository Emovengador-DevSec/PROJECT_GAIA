import type { AlertFeature } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";
import { ApplicationReference, LearnMore } from "./Resources";
import { CountUp } from "./CountUp";


const httpsUrl = (value?: string) => value?.startsWith("https://") ? value : undefined;

function ExposureMetric({ label, value, unit }: { label: string; value?: number | null; unit?: string }) {
  return <div><dt>{label}</dt><dd>{number(value)} {value != null && unit && <small>{unit}</small>}</dd></div>;
}

export function AlertDetails({ feature, onBack, onResources }: { feature: AlertFeature; onBack: () => void; onResources: () => void }) {
  const p = feature.properties;
  const source = p.source_kind === "primary" ? "NISAR · fuente principal" : `${p.source} · complementario`;
  const shareUrl = new URL(window.location.href);
  shareUrl.searchParams.set("alert", p.id);
  const message = ["GAIA Alerta", p.title, p.place, formatDate(p.date), source, p.note, shareUrl.href].join("\n");
  const external = httpsUrl(p.source_url);
  const exposure = p.exposure;
  const exposureSources = Object.values(exposure?.sources ?? {});
  return <article className="alert-detail" data-kind={p.kind}>
    <button type="button" className="text-button detail-back" onClick={onBack}>Volver a las observaciones</button>
    <div className="source-row"><span className="source-label">{source}</span><span className="alert-level" data-level={p.level}>Prioridad {p.level}</span></div>
    <h3>{p.title}</h3>
    <p className="alert-place">{p.place}</p>
    <p className="muted">{formatDate(p.date)}</p>
    {p.comparison_summary && <p className="muted">
      La zona de estudio registra {number(p.comparison_summary.loss_area_ha)} ha con caída de señal HV.
      {" "}{p.comparison_summary.alerts} manchas delimitadas reúnen {number(p.comparison_summary.mapped_loss_area_ha)} ha.
      {" "}El total incluye fragmentos menores que el tamaño mínimo de delimitación. Esta ficha corresponde a una mancha.
    </p>}
    <dl className="observation-metrics">
      {p.metrics.magnitude !== undefined && <div><dt>Magnitud</dt><dd><CountUp value={p.metrics.magnitude} decimals={1} /> <small>{p.metrics.magnitude_type ?? "M"}</small></dd></div>}
      {p.metrics.depth_km !== undefined && <div><dt>Profundidad</dt><dd><CountUp value={p.metrics.depth_km} decimals={1} /> <small>km</small></dd></div>}
      {p.metrics.frp_mw !== undefined && <div><dt>Potencia radiativa</dt><dd><CountUp value={p.metrics.frp_mw} decimals={1} /> <small>MW</small></dd></div>}
      {p.metrics.count !== undefined && <div><dt>Detecciones en la celda</dt><dd><CountUp value={p.metrics.count} /> <small>focos</small></dd></div>}
      {p.metrics.area_ha != null && <div><dt>Área de esta mancha</dt><dd><CountUp value={p.metrics.area_ha} decimals={2} /> <small>ha</small></dd></div>}
    </dl>
    <p className="observation-note">{p.note}</p>
    <p className="muted">Confianza o revisión · {p.confidence}</p>
    {p.provisional && <p className="badge-provisional">Producto NISAR provisional · calibración sujeta a revisión.</p>}

    <section className="exposure-section">
      <h4>¿A quién afecta?</h4>
      {exposure ? <>
        <dl className="exposure-metrics">
          <ExposureMetric label="Personas estimadas" value={exposure.people} />
          <ExposureMetric label="Cultivo" value={exposure.crop_ha} unit="ha" />
          <ExposureMetric label="Bosque" value={exposure.forest_ha} unit="ha" />
          <ExposureMetric label="Pastizal" value={exposure.grassland_ha} unit="ha" />
          {exposure.other_landcover_ha != null &&
            <ExposureMetric label="Otra cobertura" value={exposure.other_landcover_ha} unit="ha" />}
          <ExposureMetric label="Centros poblados cercanos" value={exposure.settlements} />
        </dl>
        {exposure.landcover_coverage_pct != null && <p className="muted">
          WorldCover clasifica el {number(exposure.landcover_coverage_pct)} % de la mancha.
          {!!exposure.landcover_unmapped_ha && ` Superficie sin clasificar: ${number(exposure.landcover_unmapped_ha)} ha.`}
        </p>}
        {exposure.nearby_places && (exposure.nearby_places.length > 0
          ? <ul className="source-list" aria-label="Distancia de cada centro poblado a la mancha">{exposure.nearby_places.map((place, index) => {
            const link = httpsUrl(place.url);
            return <li key={link ?? `${place.name}-${index}`}>
              {link ? <a href={link} target="_blank" rel="noopener noreferrer">{place.name}</a> : place.name}
              {` · ${number(place.distance_m)} m`}
            </li>;
          })}</ul>
          : <p className="muted">OpenStreetMap no registra centros poblados a {number(exposure.settlement_buffer_m ?? 2000)} m o menos.</p>)}
        <p className="muted">{exposure.note ?? "Estimación de exposición basada en la ubicación y las fuentes disponibles."}</p>
        {!!exposure.issues?.length && <ul className="source-list">{exposure.issues.map(issue =>
          <li key={issue}>{issue}</li>,
        )}</ul>}
        {!!exposureSources.length && <ul className="source-list">{exposureSources.map((value, index) => {
          if (typeof value === "string") return <li key={index}>{value}</li>;
          const sourceLink = httpsUrl(value.url);
          const licenseLink = httpsUrl(value.license_url);
          const year = value.year ?? value.date?.slice(0, 4);
          return <li key={value.name}>
            {sourceLink ? <a href={sourceLink} target="_blank" rel="noopener noreferrer">{value.name}</a> : value.name}
            {year && ` · ${year}`}
            {value.license && <> · {licenseLink
              ? <a href={licenseLink} target="_blank" rel="noopener noreferrer">{value.license}</a> : value.license}</>}
            {value.attribution && <small className="muted"> {value.attribution}</small>}
          </li>;
        })}</ul>}
      </> : <p className="empty-inline">La exposición aún no está calculada. Se necesitan capas de población, cobertura del suelo y centros poblados para estimar personas y cultivos.</p>}
    </section>

    {p.remediation && (
      <section className="remediation-section">
        <div className="source-row">
          <span className="source-label">Solución basada en la naturaleza (SbN)</span>
          <span className="alert-level" data-level={p.remediation.level} style={{ borderColor: p.remediation.color_hex, color: p.remediation.color_hex }}>
            Riesgo {p.remediation.level} · {(p.remediation.index * 100).toFixed(0)}%
          </span>
        </div>
        <h4>Qué pasa y diagnóstico</h4>
        <p><strong>{p.remediation.risk_name}</strong></p>
        <p className="observation-note">{p.remediation.risk_description}</p>

        <h4>Por qué · factores ponderados</h4>
        <ul className="source-list">
          {p.remediation.factor_details.map((factor, i) => (
            <li key={i}>{factor}</li>
          ))}
        </ul>

        {p.remediation.recipe && (
          <div className="remediation-recipe">
            <h4>Receta recomendada</h4>
            <p className="muted">Condición física: <code>{p.remediation.recipe.condition}</code></p>
            {p.remediation.recipe.disclaimer && (
              <p className="status-message">{p.remediation.recipe.disclaimer}</p>
            )}
            {p.remediation.recipe.species_primary?.length > 0 && (
              <div>
                <strong>Especies nativas recomendadas:</strong>
                <ul className="source-list">
                  {p.remediation.recipe.species_primary.map((sp, idx) => (
                    <li key={idx}>{sp}</li>
                  ))}
                </ul>
              </div>
            )}
            {p.remediation.soil?.wrb_name && (
              <p className="muted">
                Suelo (SoilGrids): {p.remediation.soil.wrb_name}
                {p.remediation.soil.clay_pct != null && ` · Arcilla: ${p.remediation.soil.clay_pct}%`}
                {p.remediation.soil.sand_pct != null && ` · Arena: ${p.remediation.soil.sand_pct}%`}
              </p>
            )}
          </div>
        )}

        <h4>Presupuesto estimado de intervención</h4>
        {p.remediation.budget?.length > 0 ? (
          <div className="budget-table-wrap">
            <table className="budget-table" style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse", marginTop: "0.5rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border, #333)", textAlign: "left" }}>
                  <th style={{ padding: "4px" }}>Técnica</th>
                  <th style={{ padding: "4px" }}>Temporada</th>
                  <th style={{ padding: "4px" }}>Unidad</th>
                  <th style={{ padding: "4px" }}>Presupuesto</th>
                </tr>
              </thead>
              <tbody>
                {p.remediation.budget.map((b) => (
                  <tr key={b.intervention_id} style={{ borderBottom: "1px solid var(--border-subtle, #222)" }}>
                    <td style={{ padding: "6px 4px" }}>
                      <strong>{b.name}</strong>
                      <br />
                      <small className="muted">{b.notes}</small>
                      {b.source && (
                        <div>
                          <small className="muted">Fuente: {b.source}</small>
                        </div>
                      )}
                      {b.minka_discount_pct && (
                        <div>
                          <small className="badge-provisional">
                            Minka comunal: hasta {b.minka_discount_pct}% menos en efectivo
                          </small>
                        </div>
                      )}
                    </td>
                    <td style={{ padding: "6px 4px" }}><small>{b.timing}</small></td>
                    <td style={{ padding: "6px 4px" }}><small>{b.unit}</small></td>
                    <td style={{ padding: "6px 4px" }}>
                      <strong>{b.cost_label}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-inline">Sin intervenciones presupuestadas.</p>
        )}

        <details className="technical-details">
          <summary>Procedencia y fuentes de remediación</summary>
          <ul className="source-list">
            <li>
              <strong>NISAR (fuente principal):</strong> {p.remediation.sources_nisar.product}
              <br />
              <small className="muted">
                Fechas: {p.remediation.sources_nisar.dates?.join(" → ")}
              </small>
            </li>
            {p.remediation.sources_complementary?.map((s, idx) => (
              <li key={idx}>
                <strong>Complementario:</strong> {s.source}
                {s.license && ` · ${s.license}`}
                {s.url && (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-link">
                    ↗
                  </a>
                )}
              </li>
            ))}
          </ul>
        </details>

        <p className="status-message" style={{ marginTop: "1rem" }}>
          {p.remediation.disclaimer}
        </p>

        <div className="printable-qr" style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "1rem" }}>
          <img
            src={`https://api.qrserver.com/v1/create-qr-code/?size=96x96&data=${encodeURIComponent(shareUrl.href)}`}
            alt="Código QR de la ficha"
            width="96"
            height="96"
            style={{ borderRadius: "4px", background: "#fff", padding: "4px" }}
          />
          <div>
            <p style={{ margin: 0, fontWeight: "bold" }}>Acceso digital a la ficha</p>
            <p className="muted" style={{ margin: 0, fontSize: "0.8rem" }}>Escanea el código QR para consultar las coordenadas y las capas de monitoreo en vivo.</p>
          </div>
        </div>
      </section>
    )}

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
