import { useEffect, useState } from "react";
import { api, type CitizenReport, type CommunityDetail, type CommunityIndex, type CommunityPlace } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";
import { Indicator } from "./Indicator";
import { CitizenReports } from "./CitizenReports";
import "./community.css";

const normalize = (name?: string | null) => (name ?? "").normalize("NFD").replace(/\p{Diacritic}/gu, "").trim().toLowerCase();

export function Community({ onLocate, reports, reportError, reportLayer, onReportLayer, picking, onPick, point, onLocateReport }: {
  onLocate: (place: CommunityPlace) => void; reports?: CitizenReport[]; reportError: boolean;
  reportLayer: boolean; onReportLayer: () => void; picking: boolean; onPick: (value: boolean) => void;
  point?: [number, number]; onLocateReport: (report: CitizenReport) => void;
}) {
  const [index, setIndex] = useState<CommunityIndex | null>();
  const [placeId, setPlaceId] = useState(() => {
    const shared = new URLSearchParams(location.search).get("lugar");
    return shared && /^[a-z0-9-]{1,60}$/.test(shared) ? shared : "huamanga";
  });
  const [province, setProvince] = useState("");
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState<CommunityDetail>();
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const request = new AbortController();
    api.community(request.signal).then(setIndex).catch(() => {
      if (!request.signal.aborted) setError("No se pudo consultar el catálogo de comunidades.");
    });
    return () => request.abort();
  }, [revision]);
  useEffect(() => {
    const request = new AbortController();
    setDetail(undefined);
    setError("");
    api.communityPlace(placeId, request.signal).then(setDetail).catch(() => {
      if (!request.signal.aborted) setError("No se pudo abrir esta ficha. Elige un lugar o vuelve a intentar.");
    });
    return () => request.abort();
  }, [placeId, revision]);

  function select(place: CommunityPlace) {
    setPlaceId(place.id);
    setQuery("");
    const url = new URL(location.href);
    url.searchParams.delete("alert");
    url.searchParams.set("lugar", place.id);
    history.replaceState(null, "", url);
    onLocate(place);
  }
  const provinces = index?.places.filter(place => place.kind === "province") ?? [];
  const selected = index?.places.find(place => place.id === placeId);
  const scope = province || selected?.province || "Huamanga";
  const districts = index?.places.filter(place => place.kind === "district" && place.province === scope) ?? [];
  const found = normalize(query).length >= 2 ? index?.places.filter(place =>
    place.kind === "place" && normalize(place.name).includes(normalize(query))).slice(0, 10) : [];
  return <div className="community">
    <div className="community-controls">
      <label>Provincia<select aria-label="Provincia" disabled={!provinces.length} value={scope} onChange={event => {
        const place = provinces.find(option => option.name === event.target.value);
        if (place) { setProvince(place.name); select(place); }
      }}>{provinces.map(place => <option key={place.id}>{place.name}</option>)}</select></label>
      {!!districts.length && <label>Distrito<select value={selected?.kind === "district" ? selected.id : ""} onChange={event => {
        const place = districts.find(option => option.id === event.target.value) ?? provinces.find(option => option.name === scope);
        if (place) select(place);
      }}><option value="">Toda la provincia</option>{districts.map(place => <option key={place.id} value={place.id}>{place.name}</option>)}</select></label>}
      <label className="community-search">Buscar un centro poblado<input type="search" placeholder="Pucajasa, Macachacra…" value={query}
        onChange={event => setQuery(event.target.value)} disabled={!index} /></label>
      {!!found?.length && <ul className="community-results">{found.map(place => <li key={place.id}><button type="button"
        onClick={() => { setProvince(place.province); select(place); }}>{place.name}<small>{place.province} · {place.center[1].toFixed(3)}, {place.center[0].toFixed(3)}</small></button></li>)}</ul>}
      {normalize(query).length >= 2 && found?.length === 0 && <p className="muted" role="status">No se encontraron centros poblados con ese nombre.</p>}
    </div>
    {index === null ? <p className="empty-inline">Aún no hay fichas publicadas. Genera el cruce comunitario del periodo activo.</p>
      : error ? <p role="status">{error} <button type="button" className="text-button" onClick={() => setRevision(value => value + 1)}>Reintentar</button></p>
      : !detail ? <p className="muted" role="status">Consultando la ficha del lugar…</p>
      : <>
        <div className="community-heading"><div><h3>{detail.name}</h3><p className="muted">{detail.kind === "place" ? `Centro poblado · ${detail.province}` : detail.kind === "district" ? `Distrito · ${detail.province}` : "Provincia · Ayacucho"}</p></div>
          <button type="button" className="text-button" onClick={() => onLocate(detail)}>Ver en el mapa</button></div>
        <Indicator detail={detail} />
        <section className="community-block"><h4>Qué cambió en el terreno</h4>
          {index && <p className="muted">NISAR HV · {formatDate(index.period.a)} – {formatDate(index.period.b)}</p>}
          {detail.impact ? <>
            <p>{number(detail.impact.zones, 0)} zonas delimitadas {detail.kind === "place" ? "a 2 km o menos del centro poblado." : "dentro de la parte observada."}</p>
            <dl className="community-metrics">
              <div><dt>Cultivos</dt><dd>{number(detail.impact.cropland_ha)} <small>ha</small></dd></div>
              <div><dt>Pastizales</dt><dd>{number(detail.impact.grassland_ha)} <small>ha</small></dd></div>
              <div><dt>Bosque</dt><dd>{number(detail.impact.forest_ha)} <small>ha</small></dd></div>
              <div><dt>Población estimada</dt><dd>{number(detail.impact.population, 1)}</dd></div>
            </dl>
            <p className="muted">WorldPop estima la población dentro de las manchas con píxeles válidos ({detail.impact.population_zones} de {detail.impact.zones}).</p>
          </> : <p className="muted">El lugar queda fuera de la cobertura analizada con este par de imágenes.</p>}
          <details className="technical-details"><summary>Fuentes y fechas</summary><ul className="source-list">
            <li><a href="https://nisar-docs.asf.alaska.edu/" target="_blank" rel="noreferrer">NISAR / ASF</a> · GCOV provisional</li>
            {Object.values(index?.sources ?? {}).map(source => <li key={source.name}><a href={source.url} target="_blank" rel="noreferrer">{source.name}</a> · {source.year ?? formatDate(source.date)} · {source.license}</li>)}
            <li><a href="https://www.geoboundaries.org/api.html" target="_blank" rel="noreferrer">geoBoundaries</a> · límites provinciales, referencia 2020</li>
            {index?.district_source && <li><a href={index.district_source.url} target="_blank" rel="noreferrer">{index.district_source.name}</a> · {formatDate(index.district_source.date)} · {index.district_source.license}</li>}
          </ul><ul className="granule-list">{index?.granules.map(granule => <li key={granule}>{granule}</li>)}</ul></details>
        </section>
        <section className="community-block"><h4>Observaciones recientes</h4>
          <dl className="community-metrics">
            <div><dt>Focos · 24 horas</dt><dd>{detail.fire.status === "unavailable" ? "—" : detail.fires_today}</dd></div>
            <div><dt>Focos · 7 días</dt><dd>{detail.fire.status === "unavailable" ? "—" : detail.fire.events.length}</dd></div>
            <div><dt>Sismos · 30 días</dt><dd>{detail.quakes.status === "unavailable" ? "—" : detail.quakes.events.length}</dd></div>
          </dl>
          <p className="muted">NASA FIRMS · hasta {detail.fire.radius_km} km · {formatDate(detail.fire.updated_at)}{detail.fire.status === "cached" && " · copia guardada"}</p>
          {detail.fire.events[0] && <p>Último foco · {formatDate(detail.fire.events[0].date)} · {number(detail.fire.events[0].km)} km</p>}
          <p className="muted">USGS · hasta {detail.quakes.radius_km} km · {formatDate(detail.quakes.updated_at)}{detail.quakes.status === "cached" && " · copia guardada"}</p>
          {detail.quakes.events[0] && <p>Último sismo · M {number(detail.quakes.events[0].magnitude, 1)} · {formatDate(detail.quakes.events[0].date)}</p>}
        </section>
        <section className="community-block"><h4>Qué investigar en las chacras</h4>
          <p>En el área estudiada, {number(index?.region.cropland_ha)} ha de cultivo coinciden con manchas HV. La cosecha y la preparación del terreno podrían explicar parte de la caída de señal.</p>
          <p className="muted">Contrasta esa hipótesis con el calendario de siembra, registros locales y observaciones ópticas. Lluvia, humedad e incendios también pueden modificar el eco radar.</p>
        </section>
      </>}
      <CitizenReports reports={reports} error={reportError} active={reportLayer} onLayer={onReportLayer}
        picking={picking} onPick={onPick} point={point} onLocate={onLocateReport} />
  </div>;
}
