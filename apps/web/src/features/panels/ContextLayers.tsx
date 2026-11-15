import type { ContextLayer } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { vertexGranule } from "../workspace/RadarGlossary";

function ContextLayerProvenance({ item }: { item: ContextLayer }) {
  return <>
    {item.scene && <p className="muted">Escena · <span className="granule-id">{item.scene}</span></p>}
    {!!item.scenes?.length && <details className="technical-details"><summary>Gránulos de estas fechas</summary>
      <ul className="granule-list">{item.scenes.map(scene => <li key={scene}>{scene.startsWith("NISAR_") ? <a className="source-link granule-id"
        href={vertexGranule(scene)} target="_blank" rel="noopener noreferrer">{scene} ↗</a> : <span className="granule-id">{scene}</span>}</li>)}</ul>
    </details>}
    {item.license && <p className="muted">{item.license}</p>}
  </>;
}

function ContextLayerLinks({ item }: { item: ContextLayer }) {
  return <>
    <a className="source-link" href={item.href} target="_blank" rel="noopener noreferrer">Datos y metodología ↗</a>
    {item.legend && <a className="source-link" href={item.legend} target="_blank" rel="noopener noreferrer">Leyenda de la capa ↗</a>}
    {item.report && <a className="source-link" href={item.report} target="_blank" rel="noopener noreferrer">Informe de INDECI ↗</a>}
  </>;
}

export function ContextLayerSources({ item }: { item: ContextLayer }) {
  return <><ContextLayerProvenance item={item} /><ContextLayerLinks item={item} /></>;
}

const shortNames: Record<string, string> = {
  "nisar-gcov": "Mosaicos NISAR · falso color",
  "hls-optical": "Cultivos · imagen óptica HLS",
  opera: "Cambios de vegetación · OPERA",
};

export function ContextLayers({ items, active, onSelect, title = "Observaciones complementarias", compact = false }: {
  items: ContextLayer[]; active?: ContextLayer; onSelect: (id: string | null) => void; title?: string; compact?: boolean;
}) {
  if (!items.length) return null;
  return <section className={compact ? "story-layer-group" : "context-layers"}>
    <h4>{title}</h4>
    {items.map(item => {
      const shown = active?.id === item.id;
      const name = compact ? shortNames[item.id] ?? item.name : item.name;
      const activate = item.before ? compact ? "Activar cortina" : "Activar cortina visual" : "Mostrar en el globo";
      const action = shown ? "Quitar del globo" : activate;
      return <div key={item.id} className={compact ? "story-layer-row" : undefined}>
        {compact ? <div>
          <strong>{name}</strong>
          <small>{item.product} · {item.source}</small>
          <small>{item.before && <><time dateTime={item.before}>{formatDate(item.before)}</time> → </>}
            <time dateTime={item.date}>{formatDate(item.date)}</time></small>
        </div> : <>
          <p><strong>{name}</strong><small>{item.product} · {item.source} · {item.before && `${item.before} → `}<time dateTime={item.date}>{item.date}</time></small></p>
          <p className="muted">{item.note}</p>
          <ContextLayerProvenance item={item} />
        </>}
        {item.available ? <button type="button" className="secondary-action" aria-pressed={shown}
          aria-label={compact ? `${action} · ${name}` : undefined} onClick={() => onSelect(shown ? null : item.id)}>
          {action}
        </button> : <p className="empty-inline">{compact ? "Imagen sin publicar" : "Imagen sin publicar para la fecha seleccionada. Consulta la fuente original."}</p>}
        {!compact && <ContextLayerLinks item={item} />}
      </div>;
    })}
  </section>;
}
