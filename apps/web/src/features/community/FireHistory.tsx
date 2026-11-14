import { useEffect, useState } from "react";
import { api, type FireHistory as History } from "../../lib/api";
import { formatNumber as number } from "../../lib/formatNumber";
import { formatDate } from "../../lib/formatDate";

const month = (value: number) => new Date(Date.UTC(2025, value - 1, 1)).toLocaleDateString("es-PE", { month: "long", timeZone: "UTC" });

export function FireHistory() {
  const [data, setData] = useState<History | null>();
  const [error, setError] = useState(false);
  useEffect(() => {
    const request = new AbortController();
    api.fireHistory(request.signal).then(setData).catch(() => { if (!request.signal.aborted) setError(true); });
    return () => request.abort();
  }, []);
  if (!data) return <p className="muted" role="status">{error ? "No se pudo consultar el archivo MODIS." : data === null ? "El archivo histórico MODIS de Ayacucho aún no está publicado." : "Consultando el archivo MODIS…"}</p>;
  const max = Math.max(1, ...data.annual.map(row => row.count));
  const peak = [...data.monthly].sort((a, b) => b.total - a.total)[0];
  return <section className="fire-history">
    <h4>Focos en Ayacucho · 2001–2025</h4>
    <p><strong>{number(data.count, 0)} detecciones térmicas</strong> en la zona de estudio durante 25 años.</p>
    <svg viewBox="0 0 355 145" role="img" aria-label="Número de detecciones térmicas MODIS por año, de 2001 a 2025">
      <path d="M34 12v100h310" fill="none" stroke="#7e91a0" />
      <text x="2" y="18">{number(max, 0)}</text><text x="18" y="113">0</text>
      {data.annual.map((row, index) => <rect key={row.year} x={39 + index * 12} y={111 - row.count / max * 94}
        width="8" height={row.count / max * 94} fill="#ffba83"><title>{row.year}: {number(row.count, 0)} detecciones</title></rect>)}
      <text x="38" y="137">2001</text><text x="182" y="137" textAnchor="middle">2013</text><text x="335" y="137" textAnchor="end">2025</text>
    </svg>
    {data.count > 0 && <p>El mayor número de detecciones se acumuló en <strong>{month(peak.month)}</strong>: {number(peak.total, 0)} focos entre todos los años.</p>}
    <details className="technical-details"><summary>Estacionalidad y procedencia</summary>
      <table><caption>Detecciones por mes en 2001–2025</caption><thead><tr><th>Mes</th><th>Total</th><th>Media anual</th></tr></thead>
        <tbody>{data.monthly.map(row => <tr key={row.month}><th scope="row">{month(row.month)}</th><td>{number(row.total, 0)}</td><td>{number(row.mean, 1)}</td></tr>)}</tbody></table>
      <p className="muted">{number(data.covered_days, 0)} días consultados en {number(data.originals, 0)} originales. Versiones: {data.versions.join(", ")}.</p>
    </details>
    <p className="muted">{data.note}</p>
    <p className="muted"><a href={data.source_url} target="_blank" rel="noreferrer">{data.source}</a> · consultado el {formatDate(data.retrieved_at)}. Datos complementarios a NISAR.</p>
  </section>;
}
