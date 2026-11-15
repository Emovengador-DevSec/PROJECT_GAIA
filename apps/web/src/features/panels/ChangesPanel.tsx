import type { LayerManifest, PolarizationSummary } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";
import { RadarGlossary } from "../workspace/RadarGlossary";
import "./changes-panel.css";

export function ChangesPanel({ layer, layers, pol, onPol, compare, onCompare, falseColor, onFalseColor,
  canUseFalseColor, tiles, summary, tileError, onRetry }: {
  layer: LayerManifest; layers: LayerManifest[]; pol: string; onPol: (pol: string) => void;
  compare: boolean; onCompare: (value: boolean) => void; falseColor: boolean; onFalseColor: (value: boolean) => void;
  canUseFalseColor: boolean; tiles: boolean; summary?: PolarizationSummary; tileError?: string; onRetry: () => void;
}) {
  const polarizations = [...new Set(layers.map(item => String(item.provenance.layer)))];
  const loss = layer.change_summary?.loss_area_ha;
  const threshold = layer.provenance.threshold_db;
  return <section className="changes-panel">
    <h3>Qué cambió en el terreno</h3>
    <p className="changes-dates">NISAR · dos pasadas<br />
      <time dateTime={layer.dates.a}>{formatDate(layer.dates.a)}</time> → <time dateTime={layer.dates.b}>{formatDate(layer.dates.b)}</time>
    </p>
    <p className="changes-hint">Las zonas que se oscurecen pierden señal. La causa requiere contraste.</p>
    {tileError && <div className="radar-error" role="alert"><strong>La imagen radar no está disponible</strong>
      <p>{tileError}</p><button type="button" className="secondary-action" onClick={onRetry}>Reintentar radar</button>
    </div>}
    <dl className="changes-metrics">
      <div><dt>Área con pérdida de señal</dt><dd>{loss == null ? "Sin dato" : <>{number(loss)} <small>ha</small></>}</dd></div>
      <div><dt>Cobertura válida</dt><dd>{number(layer.quality.valid_area_pct)} <small>%</small></dd></div>
      <div><dt>Umbral de pérdida</dt><dd>{typeof threshold === "number" ? <>{number(threshold)} <small>dB</small></> : "Sin dato"}</dd></div>
    </dl>
    <label className="field-label" htmlFor="pol">Qué quieres observar
      <select id="pol" value={pol} onChange={event => onPol(event.target.value)}>
        {polarizations.map(value => <option key={value} value={value}>
          {value === "HVHV" ? "Vegetación (HV)" : value === "HHHH" ? "Superficie y agua (HH)" : value}
        </option>)}
      </select>
    </label>
    <label className="comparison-toggle"><input type="checkbox" checked={compare} disabled={!layer.comparison || !tiles}
      onChange={event => onCompare(event.target.checked)} /><span>Comparar antes y después</span></label>
    {compare && <>
      <p className="changes-dates">↔ Arrastra la cortina del mapa o usa las flechas del teclado.</p>
      {layer.kind === "backscatter_diff_db" && <label className="comparison-toggle"><input type="checkbox" checked={falseColor}
        disabled={!canUseFalseColor || !tiles} onChange={event => onFalseColor(event.target.checked)} /><span>Ver en falso color</span></label>}
      {falseColor && <ul className="radar-colors" aria-label="Leyenda del falso color">
        <li><i className="radar-red" />Rojo · superficie (HH)</li>
        <li><i className="radar-green" />Verde · vegetación (HV)</li>
        <li><i className="radar-blue" />Azul · relación HH/HV</li>
      </ul>}
      {layer.kind === "backscatter_diff_db" && !canUseFalseColor &&
        <p className="muted">El falso color requiere HH y HV de las mismas dos observaciones.</p>}
    </>}
    {!layer.comparison && <p className="status-message">Solo se publicó el cambio calculado. Faltan las imágenes de ambas fechas para la cortina.</p>}
    {!tiles && <p className="status-message">El servicio de imágenes radar está sin activar.</p>}
    {layer.quality.provisional && <p className="changes-dates">NISAR provisional · interpretación por verificar.</p>}
    <details className="technical-details"><summary>Ver detalle del radar</summary>
      <ul className="changes-look">
        <li>Busca zonas que se oscurecen entre las dos fechas.</li>
        <li>La pérdida de señal puede relacionarse con vegetación, humedad o suelo removido. La causa requiere contraste.</li>
      </ul>
      <h4>{layer.title}</h4>
      <p>{layer.provenance.source} · {String(layer.provenance.layer)} · {String(layer.provenance.method ?? "Método sin publicar")}</p>
      {!compare && <div className="data-legend"><span>{number(layer.range.min, 1)} {layer.unit}</span>
        <div className="color-scale" /><span>{number(layer.range.max, 1)} {layer.unit}</span></div>}
      {layer.change_summary && <p>{number(layer.change_summary.mapped_loss_area_ha)} ha agrupadas en {layer.change_summary.alerts} manchas delimitadas.</p>}
      {summary?.strongest && summary.HHHH && summary.HVHV && <p>
        Mayor área de caída en {summary.strongest.slice(0, 2)}. HH · {number(summary.HHHH.loss_area_ha)} ha.
        HV · {number(summary.HVHV.loss_area_ha)} ha.
      </p>}
      {falseColor && <p>Ambas fechas usan la misma escala. El falso color representa la señal radar.</p>}
      <RadarGlossary terms={["hh", "hv", "retrodispersion"]} />
    </details>
  </section>;
}
