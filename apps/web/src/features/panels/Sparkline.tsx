import type { TimeSeries, Trend } from "../../lib/api";

type Point = { date: string; value: number | null };

/** Observaciones por fecha real. Los intervalos sin datos interrumpen el trazo. */
export function Sparkline({ ts, trend, polarization = "HVHV" }: { ts: TimeSeries; trend?: Trend; polarization?: string }) {
  const rows = [...ts.samples].filter(sample => Number.isFinite(Date.parse(sample.date)))
    .sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  const series = (key: "HHHH" | "HVHV"): Point[] => rows.map(sample => ({
    date: sample.date, value: Number.isFinite(sample[key]?.median_db) ? sample[key]!.median_db : null,
  }));
  const values = [...series("HHHH"), ...series("HVHV")].flatMap(point => point.value === null ? [] : [point.value]);
  if (new Set(rows.map(row => row.date)).size < 2 || values.length < 2) {
    return <p className="empty-inline">Se necesitan dos fechas distintas con mediciones válidas para dibujar la serie.</p>;
  }
  const projected = trend?.status === "ok" ? trend.projection.filter(point =>
    [point.value, point.low, point.high, Date.parse(point.date)].every(Number.isFinite)) : [];
  const extent = [...values, ...projected.flatMap(point => [point.low, point.high])];
  const lo = Math.min(...extent) - 1;
  const hi = Math.max(...extent) + 1;
  const first = Date.parse(rows[0].date);
  const last = Math.max(Date.parse(rows.at(-1)!.date), ...projected.map(point => Date.parse(point.date)));
  const W = 360, H = 190, LEFT = 44, RIGHT = 12, TOP = 16, BOTTOM = 30;
  const x = (date: string) => LEFT + ((Date.parse(date) - first) / Math.max(1, last - first)) * (W - LEFT - RIGHT);
  const y = (value: number) => H - BOTTOM - ((value - lo) / (hi - lo)) * (H - TOP - BOTTOM);
  const path = (points: Point[]) => {
    let drawing = false;
    return points.map(point => {
      if (point.value === null) { drawing = false; return ""; }
      const command = drawing ? "L" : "M";
      drawing = true;
      return `${command}${x(point.date)},${y(point.value)}`;
    }).join(" ");
  };
  const band = projected.length ? [
    ...projected.map(point => `${x(point.date)},${y(point.high)}`),
    ...[...projected].reverse().map(point => `${x(point.date)},${y(point.low)}`),
  ].join(" ") : "";
  const dateLabel = (value: string) => new Intl.DateTimeFormat("es-PE", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(value));

  return <figure className="signal-chart">
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Retrodispersión mediana en dB de HH y HV por fecha de observación NISAR">
      {[lo, (lo + hi) / 2, hi].map(tick => <g key={tick}><line x1={LEFT} y1={y(tick)} x2={W - RIGHT} y2={y(tick)} stroke="currentColor" opacity=".12" /><text x={LEFT - 7} y={y(tick) + 4} textAnchor="end" fill="currentColor" fontSize="11">{tick.toFixed(0)}</text></g>)}
      <text x="6" y="12" fill="currentColor" fontSize="10">dB</text>
      {!!band && <polygon points={band} fill="#fbbf24" opacity=".13" />}
      <path d={path(series("HHHH"))} fill="none" stroke="#f4f7fb" strokeWidth="2" />
      <path d={path(series("HVHV"))} fill="none" stroke="#22d3ee" strokeWidth="2" />
      {(["HHHH", "HVHV"] as const).map(key => series(key).map((point, index) => point.value !== null &&
        <circle key={`${key}-${index}`} cx={x(point.date)} cy={y(point.value)} r="3" fill={key === "HHHH" ? "#f4f7fb" : "#22d3ee"}><title>{point.date} · {key.slice(0, 2)} · {point.value.toFixed(2)} dB</title></circle>))}
      {!!projected.length && <path d={path(projected.map(point => ({ date: point.date, value: point.value })))} fill="none" stroke="#fbbf24" strokeWidth="2" strokeDasharray="5 4" />}
      <text x={LEFT} y={H - 8} fill="currentColor" fontSize="11">{dateLabel(rows[0].date)}</text>
      <text x={W - RIGHT} y={H - 8} textAnchor="end" fill="currentColor" fontSize="11">{dateLabel(projected.at(-1)?.date ?? rows.at(-1)!.date)}</text>
    </svg>
    <figcaption><span className="hh-key">HH · superficie y agua</span><span className="hv-key">HV · vegetación</span>
      {!!projected.length && <span className="trend-key">Proyección {polarization.slice(0, 2)} con incertidumbre</span>}</figcaption>
    {!!projected.length && <p className="status-message">{trend!.label}</p>}
    <div className="series-table"><table><caption className="sr-only">Medianas observadas por fecha</caption><thead><tr><th>Fecha</th><th>HH · dB</th><th>HV · dB</th></tr></thead>
      <tbody>{rows.map(sample => <tr key={sample.granule}><th scope="row">{sample.date}</th><td>{sample.HHHH?.median_db.toFixed(2) ?? "—"}</td><td>{sample.HVHV?.median_db.toFixed(2) ?? "—"}</td></tr>)}</tbody>
    </table></div>
  </figure>;
}
