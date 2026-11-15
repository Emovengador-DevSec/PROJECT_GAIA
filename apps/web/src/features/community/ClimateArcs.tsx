import { useEffect, useState } from "react";
import { api, type AlertFeature, type Climate, type FeedStatus, type Rainfall } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";
import { FireHistory } from "./FireHistory";
import { climateSummary } from "../workspace/actionSummaryModel";

type Period = "past" | "present" | "future";
const periods: [Period, string][] = [["past", "Pasado"], ["present", "Presente"], ["future", "Futuro"]];

function ClimatePlot({ climate, projected }: { climate: Climate; projected: boolean }) {
  const history = climate.annual;
  const future = projected ? climate.projection : [];
  const temperatures = [...history.map(row => row.temperature), ...future.flatMap(row => [row.low, row.high])];
  const min = Math.min(...temperatures) - .25;
  const max = Math.max(...temperatures) + .25;
  const year0 = history[0].year;
  const year1 = future.at(-1)?.year ?? history.at(-1)!.year;
  const xy = (year: number, temperature: number) => `${33 + 307 * (year - year0) / (year1 - year0)},${103 - 86 * (temperature - min) / (max - min)}`;
  return <svg className="community-climate-plot" viewBox="0 0 355 127" role="img"
    aria-label={`Temperatura de ${year0} a ${year1} en grados Celsius${projected ? " con una extrapolación y su banda" : ""}`}>
    <path d="M32 12v94h308" fill="none" stroke="currentColor" opacity=".35" />
    {[min, max].map(value => <text key={value} x="2" y={value === min ? 105 : 19}>{number(value, 1)}°</text>)}
    {future.length > 0 && <><polygon points={[...future.map(row => xy(row.year, row.low)),
      ...[...future].reverse().map(row => xy(row.year, row.high))].join(" ")} fill="#a786e7" opacity=".23" />
      <polyline points={future.map(row => xy(row.year, row.temperature)).join(" ")} fill="none" stroke="#d1b6ff" strokeWidth="2" strokeDasharray="5 4" /></>}
    <polyline points={history.map(row => xy(row.year, row.temperature)).join(" ")} fill="none" stroke="#ffba83" strokeWidth="2" />
    <text x="33" y="123">{year0}</text><text x="339" y="123" textAnchor="end">{year1}</text>
  </svg>;
}

export function ClimateArcs({ alerts, sources, rainfall, aoiId = "ayacucho-huanta" }: { alerts: AlertFeature[]; sources: FeedStatus[]; rainfall?: Rainfall; aoiId?: string }) {
  const [period, setPeriod] = useState<Period>("past");
  const [climate, setClimate] = useState<Climate | null>();
  const [error, setError] = useState(false);
  useEffect(() => {
    const request = new AbortController();
    setClimate(undefined);
    setError(false);
    api.climate(aoiId, request.signal).then(value => { if (!request.signal.aborted) setClimate(value); }).catch(() => {
      if (!request.signal.aborted) setError(true);
    });
    return () => request.abort();
  }, [aoiId]);
  const current = climate?.current;
  const history = climate?.annual ?? [];
  const latest = history.at(-1);
  const fire = sources.find(source => source.source === "NASA FIRMS");
  const quake = sources.find(source => source.source === "USGS");
  return <section className="community-block climate-arcs">
    <h3>Calor, tierra y agua</h3>
    <p className="muted">Clima de {aoiId} y observaciones recientes de las fuentes del globo.</p>
    <p className="status-message">{climateSummary(climate)}</p>
    {climate?.typical_season && <p>{climate.typical_season.description}</p>}
    <div className="climate-periods" role="group" aria-label="Periodo de los arcos">{periods.map(([id, name]) =>
      <button type="button" key={id} aria-pressed={period === id} onClick={() => setPeriod(id)}>{name}</button>)}</div>
    <section className="climate-lane"><h4>Calor y aire</h4>
      {climate && period !== "present" && <>
        <ClimatePlot climate={climate} projected={period === "future"} />
        <p><strong>{number(climate.trend_per_decade, 2)} °C por década</strong> · tendencia Theil–Sen de {history.length} años completos.</p>
        {period === "future" && <p className="muted">Hasta 2035, si la tendencia sigue igual. La banda refleja el intervalo del 95 % de la pendiente. Es una extrapolación estadística, no una predicción.</p>}
      </>}
      {period === "present" && <>
        {current && <p>Máxima de <strong>{number(current.max_c)} °C</strong> el {formatDate(current.date)}. {current.hot_last_year} días dentro de episodios de calor en los 365 días previos al último dato.</p>}
        <p className="muted">FIRMS · {fire && fire.status !== "unavailable" ? `${alerts.filter(event => event.properties.kind === "fire").length} focos en Perú · ${formatDate(fire.last_updated)}` : "fuente sin actualizar"}</p>
      </>}
      {period === "past" && <FireHistory />}
    </section>
    <section className="climate-lane"><h4>Tierra y agua</h4>
      {period === "past" && latest && <p><strong>{number(latest.rain_mm, 1)} mm</strong> acumulados en {latest.year} en el punto de estudio.</p>}
      {period === "present" && <>
        {current && <p>Lluvia de 30 días · <strong>{number(current.rain_mm, 1)} mm</strong> · normal comparable {number(current.normal_rain_mm, 1)} mm.</p>}
        <p className="muted">USGS · {quake && quake.status !== "unavailable" ? `${alerts.filter(event => event.properties.kind === "quake").length} sismos del catálogo de Sudamérica · ${formatDate(quake.last_updated)}` : "fuente sin actualizar"}</p>
        <p className="muted">NISAR · consulta Cambios para abrir el par radar procesado de Ayacucho.</p>
        {rainfall?.mean_mm != null && <p className="muted">NASA GPM · {number(rainfall.mean_mm, 1)} mm en el episodio publicado de la zona seleccionada.</p>}
      </>}
      {period === "future" && <p className="muted">Aquí se muestran las mediciones históricas de lluvia y los eventos observados en sus periodos correspondientes.</p>}
    </section>
    {!climate && <p role="status" className="muted">{error ? "No se pudo cargar el clima." : climate === null ? `Falta publicar la serie NASA POWER: sarlab climate --aoi ${aoiId}.` : "Cargando la serie diaria…"}</p>}
    {climate && <p className="muted"><a href={climate.source_url} target="_blank" rel="noreferrer">{climate.source}</a> · {climate.version} · {formatDate(climate.fetched_at)}. Estimación regional en una celda de reanálisis. Climatología 1991–2020.</p>}
  </section>;
}
