import {useEffect, useRef, useState} from "react";
import {api, type AlertFeature, type PlaceEvidence, type RealPhoto} from "../../lib/api";
import {formatNumber as number} from "../../lib/formatNumber";
import "./place-evidence.css";

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
  return <figure className="real-photo" data-photo-id={photo.id}>
    <a href={photo.source_url} target="_blank" rel="noopener noreferrer" aria-label={`Ver fuente de ${photo.title}`}>
      <img src={api.localPhoto(photo.image_url)} alt={photo.title} loading="lazy" decoding="async" width={photo.width ?? 800} height={photo.height ?? 600} />
    </a>
    <figcaption><strong>{photo.title}</strong><span>{photo.location_label}</span>
      <span>{photo.taken_at} · {photo.author_role ? `${photo.author_role}: ` : ""}{photo.author} · <a href={photo.license_url} target="_blank" rel="noopener noreferrer">{photo.license}</a></span>
      <small>{photo.modifications}</small>
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
  return <div className="place-evidence">
    <h4>Ver el lugar</h4>
    <p className="place-note">Fotos reales y observaciones complementarias de esta mancha. Cada pie indica su procedencia.</p>
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
          <details><summary>Escena y solicitud original</summary><p>{image.scene ?? image.scenes?.join(" · ")}</p><a href={image.source_url} target="_blank" rel="noopener noreferrer">Fuente NASA GIBS ↗</a></details>
        </figcaption>
      </figure> : <p className="place-empty">{image?.reason ?? "No hay recorte georreferenciado publicado para este momento. Publica la imagen verificada del territorio."}</p>}
      <small>Las fechas ópticas pueden diferir de las del radar. No confirman la causa del cambio.</small>
    </section> : <section className="place-future">
      <h4>Escenario con supuestos</h4>
      <div className="future-stages"><span>Hoy</span><span>→ 3 años</span><span>→ 5 años</span></div>
      <p>Las referencias muestran técnicas existentes en otros lugares; nunca imágenes del futuro de esta zona ni una garantía de recuperación.</p>
      {verified && scenario ? <><p>Ganancia relativa supuesta de NDVI: {number(scenario.projected.year_3?.gain_ndvi, 2)} a 3 años · {number(scenario.projected.year_5?.gain_ndvi, 2)} a 5 años.</p><a href={scenario.citation_url!} target="_blank" rel="noopener noreferrer">Fuente del escenario</a></>
        : <p className="place-empty">Las cifras del escenario permanecen ocultas hasta verificar su fuente.</p>}
      {data.techniques.length ? data.techniques.map(technique => <section key={technique.id} className="place-block"><h4>{technique.name}</h4><p>{technique.note}</p>
        {technique.photos.length ? technique.photos.map(photo => <PhotoFigure key={photo.id} photo={photo} />) : <p className="place-empty">No hay fotografías de esta técnica publicadas en el servidor.</p>}
      </section>) : <p className="place-empty">Esta mancha no tiene una técnica con fotografías verificadas.</p>}
    </section>}
    <details className="place-block" open><summary>Plantas de la receta y del suelo</summary>
      <p className="place-note">Referencias de las especies propuestas; no prueban que crezcan en esta mancha ni que la restauren.</p>
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
    </details>
    <details className="place-block"><summary>Suelo estimado</summary>
      {data.soil ? <><p>{data.soil.wrb_name}{data.soil.wrb_probability_pct != null && ` · probabilidad publicada ${number(data.soil.wrb_probability_pct, 0)} %`}.</p><p className="place-note">{data.soil.source} · {data.soil.source_date}. Clasificación estimada, no una muestra tomada en campo.</p></> : <p className="place-empty">Clase de suelo sin publicar.</p>}
      {data.soil_photo ? <><p>Ejemplo de este tipo de suelo, fotografiado en otro lugar.</p><PhotoFigure photo={data.soil_photo} /></> : <p className="place-empty">Foto de referencia del suelo con licencia verificada aún no disponible.</p>}
    </details>
    {!!data.warnings.length && <details className="place-block"><summary>Disponibilidad de las fuentes</summary>{data.warnings.map(warning => <p key={warning}>{warning}</p>)}</details>}
  </div>;
}
