import {useEffect, useRef, useState} from "react";
import {api, type AlertFeature, type PlaceEvidence, type RealPhoto} from "../../lib/api";
import {formatNumber as number} from "../../lib/formatNumber";
import "./place-evidence.css";

export const FIELD_VIEW = "gaia:field-view";
export type FieldViewRequest = {zoneId: string; design: boolean};

export function usePlaceEvidence(feature?: AlertFeature) {
  const aoi = feature?.properties.aoi_id;
  const zone = feature?.properties.remediation?.alert_id;
  const key = `${aoi}/${zone}`;
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{key: string; data?: PlaceEvidence; error?: boolean}>();
  useEffect(() => {
    if (!aoi || !zone) return;
    const request = new AbortController();
    setState({key});
    api.placeEvidence(aoi, zone, request.signal).then(data => {if (!request.signal.aborted) setState({key, data});})
      .catch(() => {if (!request.signal.aborted) setState({key, error: true});});
    return () => request.abort();
  }, [aoi, zone, attempt]);
  return {...(state?.key === key ? state : undefined), retry: () => setAttempt(value => value + 1)};
}

export function PhotoFigure({photo}: {photo: RealPhoto}) {
  const source = photo.source_url.startsWith("/api/") ? api.localPhoto(photo.source_url) : photo.source_url;
  return <figure className="real-photo" data-photo-id={photo.id}>
    <a href={source} target="_blank" rel="noopener noreferrer" aria-label={`Ver fuente de ${photo.title}`}>
      <img src={api.localPhoto(photo.image_url)} alt={photo.title} loading="lazy" decoding="async" width={photo.width ?? 800} height={photo.height ?? 600} />
    </a>
    <figcaption><strong>{photo.title}</strong><span>{photo.location_label}</span>
      {photo.caption && <span>{photo.caption}</span>}
      <span>{photo.taken_at} · {photo.author_role ? `${photo.author_role}: ` : ""}{photo.author} · <a href={photo.license_url} target="_blank" rel="noopener noreferrer">{photo.license}</a></span>
      {photo.page && <a href={source} target="_blank" rel="noopener noreferrer">Ver informe · pág. PDF {photo.page}</a>}
    </figcaption>
  </figure>;
}

export function PhotoPopup({photo, onClose}: {photo: RealPhoto; onClose: () => void}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {close.current?.focus();}, [photo.id]);
  return <aside className="map-photo-popup" role="dialog" aria-label="Foto real del mapa" onKeyDown={event => {if (event.key === "Escape") onClose();}}>
    <button type="button" className="secondary-action" ref={close} onClick={onClose}>Cerrar foto</button>
    <PhotoFigure photo={photo} />
    {photo.accuracy_m != null && <small>Precisión declarada: {number(photo.accuracy_m, 0)} m</small>}
  </aside>;
}

const MONTHS = Array.from({length: 12}, (_, i) =>
  new Intl.DateTimeFormat("es-PE", {month: "long", timeZone: "UTC"}).format(Date.UTC(2020, i)));
const signed = new Intl.NumberFormat("es-PE", {maximumFractionDigits: 2, signDisplay: "exceptZero"});

function ClimateProjection({data}: {data: PlaceEvidence["future_climate"]}) {
  const [month, setMonth] = useState("11");
  return <section className="place-block">
    <h4>Clima hacia 2050</h4>
    {data?.models.length ? <>
      <p className="place-note">Proyección de modelos climáticos CMIP6, no es un pronóstico. Cambio promedio mensual de {data.future.join("–")} frente a {data.reference.join("–")} en la celda de cada modelo.</p>
      <label>Mes <select value={month} onChange={event => setMonth(event.target.value)}>
        {MONTHS.map((name, index) => <option key={name} value={index + 1}>{name}</option>)}
      </select></label>
      <dl className="climate-projection">{data.models.map(model => {
        const values = model.months[month];
        return <div key={model.model}><dt>{model.model} · celda a {number(model.cell.elevation, 0)} m</dt><dd>
          Mínima {signed.format(values.min_c)} °C · lluvia {values.rain_pct == null ? "sin referencia suficiente" : `${signed.format(values.rain_pct)} %`}
        </dd></div>;
      })}</dl>
      <a href="https://open-meteo.com/en/docs/climate-api" target="_blank" rel="noopener noreferrer">Open-Meteo · modelos y metodología ↗</a>
    </> : <p className="place-empty">Proyección climática pendiente de publicación para este territorio.</p>}
  </section>;
}

function Greenness({data}: {data: PlaceEvidence["greenness"]}) {
  return <details className="place-block">
    <summary>Verdor histórico del territorio</summary>
    {data?.years.length ? <>
      <p className="place-note">{data.product} · píxel de referencia de {data.resolution_m} m en {number(data.center.latitude, 3)}, {number(data.center.longitude, 3)}. Medianas del {data.season} con compuestos de buena calidad.</p>
      <table className="greenness-series"><thead><tr><th>Año</th><th>NDVI</th><th>Compuestos</th></tr></thead>
        <tbody>{data.years.map(year => <tr key={year.year}><th scope="row">{year.year}</th><td>{number(year.median, 3)}</td><td>{year.count}</td></tr>)}</tbody>
      </table>
      {!!data.incomplete_years.length && <p className="place-note">Años sin observaciones suficientes en la temporada publicada · {data.incomplete_years.join(", ")}.</p>}
      <a href={data.source_url} target="_blank" rel="noopener noreferrer">NASA · producto y metodología ↗</a>
    </> : <p className="place-empty">No hay una serie histórica de verdor publicada para este territorio.</p>}
  </details>;
}

function StreetView({aoi, zone}: {aoi: string; zone: string}) {
  const [status, setStatus] = useState<"idle" | "loading" | "missing" | "error">("idle");
  const [view, setView] = useState<Awaited<ReturnType<typeof api.streetView>>>();
  if (status === "missing") return null;
  if (view) return <a href={view.url} target="_blank" rel="noopener noreferrer">
    Ver el camino en Google Street View · {view.date} · {number(view.distance_km, 2)} km ↗
  </a>;
  return <div><button type="button" className="secondary-action" disabled={status === "loading"} onClick={async () => {
    setStatus("loading");
    try {
      const panorama = await api.streetView(aoi, zone);
      if (panorama) setView(panorama);
      else setStatus("missing");
    } catch {setStatus("error");}
  }}>{status === "loading" ? "Consultando panorámicas…" : "Buscar vista a ras de suelo"}</button>
  {status === "error" && <p role="status">No se pudo consultar Google Street View.</p>}</div>;
}

export function PlaceEvidencePanel({feature}: {feature: AlertFeature}) {
  const {data, error, retry} = usePlaceEvidence(feature);
  const [moment, setMoment] = useState<"past" | "before" | "after" | "future">("after");
  const rem = feature.properties.remediation!;
  const scenario = rem.recovery_scenario;
  const verified = scenario?.citation_status === "verificado" && scenario.citation_url?.startsWith("https://")
    && !!scenario.citation && !/por[_ ]verificar/i.test(scenario.citation);
  const image = moment !== "future" ? data?.imagery[moment] : undefined;
  if (error) return <p role="alert">No se pudo cargar la evidencia de esta mancha. <button type="button" className="text-button" onClick={retry}>Reintentar</button></p>;
  if (!data) return <p role="status">Consultando fotos e imágenes publicadas…</p>;
  const exposure = feature.properties.exposure;
  const viewField = (design = false) => window.dispatchEvent(new CustomEvent<FieldViewRequest>(
    FIELD_VIEW, {detail: {zoneId: rem.alert_id, design}},
  ));
  const hasInfiltration = rem.budget?.some(line => line.intervention_id === "zanjas_infiltracion");
  return <div className="place-evidence">
    <h4>Ver el lugar</h4>
    {!!data.field_photos?.length && <details className="place-block" open>
      <summary>Fotos de campo cercanas · {data.field_photos.length}</summary>
      <p className="place-note">Fotos de informes técnicos de lugares cercanos, en el año del informe.</p>
      {data.field_photos.map(photo => <PhotoFigure key={photo.id} photo={photo} />)}
    </details>}
    <button type="button" className="primary-action" onClick={() => viewField()}>Ver la chacra desde arriba</button>
    <p className="place-note">{data.field_aerial
      ? <>{data.field_aerial.source} · {data.field_aerial.date} · {data.field_aerial.resolution_m} m · <a href={data.field_aerial.license_url} target="_blank" rel="noopener noreferrer">Condiciones de uso</a></>
      : "Imagen del globo · proveedor en la atribución del mapa · fecha variable según proveedor."}</p>
    {data.street_view_enabled && <StreetView key={rem.alert_id} aoi={data.aoi_id} zone={rem.alert_id} />}
    {!!data.field_references?.length && <details className="place-block">
      <summary>Informes con ubicación sin confirmar</summary>
      {data.field_references.map(ref => <p key={ref.source_url}><a href={ref.source_url} target="_blank" rel="noopener noreferrer">{ref.place} · {ref.author}, {ref.taken_at} · pág. PDF {ref.page} ↗</a></p>)}
    </details>}
    {!data.available && <p className="status-message">Catálogo fotográfico sin publicar. Ejecuta el recolector de fotos para este territorio.</p>}
    <div className="place-timeline" role="group" aria-label="Momento del lugar">
      {([["past", "Pasado · 2016–2018"], ["before", "Antes del radar"], ["after", "Después del radar"], ["future", "Futuro · escenario"]] as const).map(([id, label]) =>
        <button type="button" key={id} aria-pressed={moment === id} onClick={() => setMoment(id)}>{label}</button>)}
    </div>
    {moment !== "future" ? <section className="place-satellite" aria-live="polite">
      {image?.available && image.image_url ? <figure className="real-photo">
        <a href={api.localPhoto(image.image_url)} target="_blank" rel="noopener noreferrer"><img src={api.localPhoto(image.image_url)} alt={`Imagen óptica de la mancha, ${image.date}; contorno NISAR en amarillo`} loading="lazy" width="600" height="600" /></a>
        <figcaption><strong>{image.date} · {image.resolution_m} m</strong><span>{image.source}</span>{image.scene_metadata && <span>Nubes en la escena: {number(image.scene_metadata.cloud_cover_pct, 0)} %. No asegura cielo despejado en cada píxel.</span>}<span>{image.note}</span>
          <span>{image.author} · <a href={image.license_url} target="_blank" rel="noopener noreferrer">Condiciones de uso</a></span>
        </figcaption>
      </figure> : <p className="place-empty">{image?.reason ?? "No hay recorte georreferenciado publicado para este momento. Publica la imagen verificada del territorio."}</p>}
    </section> : <section className="place-future">
      <ClimateProjection data={data.future_climate} />
      <h4>Escenario con supuestos</h4>
      <div className="future-stages"><span>Hoy</span><span>→ 3 años</span><span>→ 5 años</span></div>
      {hasInfiltration && <button type="button" className="secondary-action" onClick={() => viewField(true)}>Ver diseño propuesto sobre el terreno</button>}
      <p>Las referencias muestran técnicas existentes en otros lugares; nunca imágenes del futuro de esta zona ni una garantía de recuperación.</p>
      {verified && scenario ? <><p>Ganancia relativa supuesta de NDVI: {number(scenario.projected.year_3?.gain_ndvi, 2)} a 3 años · {number(scenario.projected.year_5?.gain_ndvi, 2)} a 5 años.</p><a href={scenario.citation_url!} target="_blank" rel="noopener noreferrer">Fuente del escenario</a></>
        : <p className="place-empty">Las cifras del escenario permanecen ocultas hasta verificar su fuente.</p>}
      {data.techniques.length ? data.techniques.map(technique => <section key={technique.id} className="place-block"><h4>{technique.name}</h4><p>{technique.note}</p>
        {technique.photos.length ? technique.photos.map(photo => <PhotoFigure key={photo.id} photo={photo} />) : <p className="place-empty">No hay fotografías de esta técnica publicadas en el servidor.</p>}
      </section>) : <p className="place-empty">Esta mancha no tiene una técnica con fotografías verificadas.</p>}
    </section>}
    <Greenness data={data.greenness} />
    <details className="place-block" open><summary>Plantas de la receta y del suelo</summary>
      <p className="place-note">Fotos de referencia de cada especie.</p>
      {data.species.map(species => <section key={species.scientific}><h4>{species.name} <em>{species.scientific}</em></h4><p>{species.function}</p>
        {species.photo ? <PhotoFigure photo={species.photo} /> : <p className="place-empty">Foto con autor, fecha y licencia aún no disponible.</p>}
      </section>)}
    </details>
    <details className="place-block"><summary>Plantas observadas cerca · hasta 5 km</summary>
      <p className="place-note">Observaciones iNaturalist de grado de investigación, con coordenadas públicas y precisión declarada ≤ 100 m.</p>
      {data.nearby.length ? data.nearby.map(photo => <PhotoFigure photo={photo} key={photo.id} />) : <p className="place-empty">No hay observaciones verificadas publicadas dentro de 5 km de esta mancha.</p>}
    </details>
    <details className="place-block"><summary>Comunidad y exposición</summary>
      <p>{data.community?.name ?? "Poblado cercano sin coordenadas publicadas"}</p>
      {(rem.nearby_places ?? []).map((place, i) => <p key={`${place.name}-${i}`}>{place.name} · {number(place.distance_m / 1000, 2)} km de la mancha</p>)}
      <p>Población estimada dentro de la mancha: {exposure?.people != null ? `${number(exposure.people, 0)} personas` : "sin cobertura válida publicada"}.</p>
      {exposure?.crop_ha != null && <p>Cultivo expuesto: {number(exposure.crop_ha, 2)} ha · WorldCover.</p>}
      <p className="place-note">WorldPop estima exposición; no es un censo del poblado.</p>
      {data.community_photos.length ? data.community_photos.map(photo => <PhotoFigure key={photo.id} photo={photo} />) : <p className="place-empty">No hay fotos geolocalizadas del poblado con autor, fecha y licencia verificados.</p>}
      {!!data.community_reports?.length && <>
        <h4>Fotos aportadas por la comunidad</h4>
        {data.community_reports.map(photo => <PhotoFigure key={photo.id} photo={photo} />)}
      </>}
      <p className="place-note">Para aportar una foto propia, abre «Mi comunidad» y elige «Enviar un reporte».</p>
    </details>
    <details className="place-block"><summary>Suelo estimado</summary>
      {data.soil ? <><p>{data.soil.wrb_name}{data.soil.wrb_probability_pct != null && ` · probabilidad publicada ${number(data.soil.wrb_probability_pct, 0)} %`}.</p><p className="place-note">{data.soil.source} · {data.soil.source_date}. Clasificación estimada, no una muestra tomada en campo.</p></> : <p className="place-empty">Clase de suelo sin publicar.</p>}
      {data.soil_photo ? <><p>Ejemplo de este tipo de suelo, fotografiado en otro lugar.</p><PhotoFigure photo={data.soil_photo} /></> : <p className="place-empty">Foto de referencia del suelo con licencia verificada aún no disponible.</p>}
    </details>
  </div>;
}
