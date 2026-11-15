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
        <button type="button" aria-pressed={visible} onClick={onToggle}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><ellipse cx="12" cy="12" rx="10" ry="5" transform="rotate(-35 12 12)" /><circle cx="12" cy="12" r="2" /><circle cx="20" cy="6" r="2" fill="currentColor" stroke="none" /></svg>
          {visible ? "Ocultar órbita" : "Mostrar órbita"}
        </button>
        <button type="button" onClick={onFocus} disabled={!visible}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5" /><circle cx="12" cy="12" r="3" /></svg>
          Ver satélite
        </button>
      </div>}
      <p className="orbit-source">
        Fuente: <a href="https://celestrak.org/satcat/search.php" target="_blank" rel="noopener noreferrer">CelesTrak</a>
        {" "}· elementos del {formatDate(data.elements.EPOCH + "Z")}
      </p>
    </div> : <div><p>{data?.message ?? "Consultando elementos orbitales públicos…"}</p>
      {data && <button type="button" onClick={onRefresh}>Reintentar órbita</button>}</div>}
  </details>;
}
