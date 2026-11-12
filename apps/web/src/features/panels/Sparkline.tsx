import type { TimeSeries } from "../../lib/api";

/** Gráfico mínimo de mediana en dB por fecha para HH y HV (sin librerías). */
export function Sparkline({ ts }: { ts: TimeSeries }) {
  const W = 300, H = 140, P = 28;
  const pts = (k: "HHHH" | "HVHV") => ts.samples.map((s) => s[k]?.median_db ?? null);
  const all = [...pts("HHHH"), ...pts("HVHV")].filter((v): v is number => v !== null);
  if (all.length < 2) return <p className="muted">Se necesitan al menos dos fechas.</p>;
  const lo = Math.min(...all) - 1, hi = Math.max(...all) + 1, n = ts.samples.length;
  const x = (i: number) => P + (i * (W - 2 * P)) / Math.max(1, n - 1);
  const y = (v: number) => H - P - ((v - lo) / (hi - lo)) * (H - 2 * P);
  const path = (vals: (number | null)[]) =>
    vals.map((v, i) => (v === null ? "" : `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`)).join(" ");
  return (
    <figure style={{ margin: "12px 0" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Mediana de retrodispersión por fecha, HH y HV">
        <path d={path(pts("HHHH"))} fill="none" stroke="var(--neblina)" strokeWidth={2} />
        <path d={path(pts("HVHV"))} fill="none" stroke="var(--eco)" strokeWidth={2} />
        <text x={P} y={14} fill="var(--escarcha)" fontSize={11}>{hi.toFixed(0)} dB</text>
        <text x={P} y={H - 8} fill="var(--escarcha)" fontSize={11}>{lo.toFixed(0)} dB</text>
      </svg>
      <figcaption className="muted">Blanco: HH (superficie y agua). Celeste: HV (vegetación).</figcaption>
      <table className="muted" style={{ width: "100%", fontSize: 13 }}>
        <thead><tr><th align="left">Fecha</th><th align="right">HH dB</th><th align="right">HV dB</th></tr></thead>
        <tbody>{ts.samples.map((s) => (
          <tr key={s.granule}><td>{s.date}</td><td align="right">{s.HHHH?.median_db ?? "—"}</td><td align="right">{s.HVHV?.median_db ?? "—"}</td></tr>
        ))}</tbody>
      </table>
    </figure>
  );
}
