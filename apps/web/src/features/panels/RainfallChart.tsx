import type { Rainfall } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";

export function RainfallChart({ data }: { data: Rainfall }) {
  const rows = data.daily?.filter(row => row.mean_mm != null) ?? [];
  if (!rows.length) return null;
  const maximum = Math.max(1, ...rows.map(row => row.mean_mm!));
  return <figure className="rainfall-chart">
    <svg viewBox="0 0 320 180" role="img" aria-label="Precipitación diaria estimada por GPM IMERG en Chosica, en milímetros">
      <text x="8" y="16" fill="currentColor" fontSize="13">mm por día UTC</text>
      <path d="M12 142H308" stroke="#65798b" />
      {rows.map((row, index) => {
        const height = row.mean_mm! / maximum * 94;
        const x = 42 + index * 98;
        return <g key={row.date}>
          <rect x={x} y={142 - height} width="42" height={height} rx="2" fill="#70d7ed" />
          <text x={x + 21} y={132 - height} textAnchor="middle" fill="currentColor" fontSize="14">{number(row.mean_mm, 1)}</text>
          <text x={x + 21} y="165" textAnchor="middle" fill="currentColor" fontSize="13">{new Date(row.date + "T00:00:00Z").toLocaleDateString("es-PE", { day: "numeric", month: "short", timeZone: "UTC" })}</text>
        </g>;
      })}
    </svg>
    <figcaption>Media espacial de la zona de Chosica · producto IMERG Late V07B. Estimación satelital, complementaria a NISAR.</figcaption>
  </figure>;
}
