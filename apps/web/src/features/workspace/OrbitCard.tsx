import { useMemo } from "react";
import type { OrbitData } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { nextAccess } from "../globe/orbitMath";

export function OrbitCard({ data, visible, historical, onToggle, onFocus, onRefresh }: {
  data?: OrbitData; visible: boolean; historical: boolean; onToggle: () => void; onFocus: () => void; onRefresh: () => void;
}) {
  const pass = useMemo(() => data?.elements ? nextAccess(data.elements, Date.now()) : undefined, [data]);
  return <details className="orbit-card" open={window.innerWidth > 720}>
    <summary><span className="orbit-dot" data-active={!!data?.elements && visible && !historical || undefined} />NISAR en órbita</summary>
    {data?.elements ? <div>
      <span>Próxima pasada posible · Ayacucho</span>
      <strong>{pass ? formatDate(new Date(pass.time).toISOString()) : "Sin acceso calculado en los próximos cinco días"}</strong>
      <p>Acceso geométrico estimado. La adquisición depende del plan de la misión.</p>
      <p>Franja lateral aproximada de 240 km.</p>
      {historical ? <p>Vuelve a «Ver todo» para mostrar la órbita actual.</p> : <div className="orbit-actions">
        <button type="button" aria-pressed={visible} onClick={onToggle}>{visible ? "Ocultar órbita" : "Mostrar órbita"}</button>
        <button type="button" onClick={onFocus} disabled={!visible}>Ver satélite ↗</button>
      </div>}
      <a href={data.source_url} target="_blank" rel="noopener noreferrer">Órbita calculada con elementos públicos de CelesTrak · {formatDate(data.elements.EPOCH + "Z")}</a>
    </div> : <div><p>{data?.message ?? "Consultando elementos orbitales públicos…"}</p>
      {data && <button type="button" onClick={onRefresh}>Reintentar órbita</button>}</div>}
  </details>;
}
