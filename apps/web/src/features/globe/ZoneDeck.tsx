import { useEffect, useRef, useState } from "react";
import { api, type AlertFeature, type PlaceEvidence, type RealPhoto } from "../../lib/api";
import { FIELD_VIEW, type FieldViewRequest } from "../workspace/PlaceEvidence";

type Gallery = { title: string; items: { photo: RealPhoto; heading?: string; text?: string }[] };

/** Floating dock on the map for the selected zone: satellite view and big photo galleries. */
export function ZoneDeck({ data, zoneId, fieldOn, onShowPins, feature }: {
  data: PlaceEvidence; zoneId: string; fieldOn: boolean; onShowPins: () => void; feature: AlertFeature;
}) {
  const [gallery, setGallery] = useState<Gallery>();
  const [study, setStudy] = useState(false);
  const [index, setIndex] = useState(0);
  const field = data.field_photos ?? [];
  const plants = data.species.filter(s => s.photo);
  const nearby = data.nearby ?? [];
  const open = (g: Gallery) => { setGallery(g); setIndex(0); };
  const satellite = () => window.dispatchEvent(new CustomEvent<FieldViewRequest>(FIELD_VIEW, { detail: { zoneId, design: false } }));
  return <>
    <nav className="zone-deck" aria-label="Explorar esta zona">
      <div className="study-strip">
        <button type="button" data-tone="study" onClick={() => setStudy(true)}>
          <span aria-hidden="true">🟫</span> Estudio del suelo
        </button>
        {data.soil_photo && <figure className="plant-thumb study-thumb-mini soil-thumb" tabIndex={0}
          aria-label={`Suelo ${feature.properties.remediation?.soil?.wrb_name ?? ""}`} onClick={() => setStudy(true)}>
          <img src={api.localPhoto(data.soil_photo.image_url)} alt="" loading="lazy" />
          <figcaption>
            <img src={api.localPhoto(data.soil_photo.image_url)} alt="" loading="lazy" />
            <strong>Suelo · {(feature.properties.remediation?.soil?.wrb_name ?? "sin dato").replace(/s$/, "")}</strong>
            <span>Ejemplo de este tipo de suelo · {data.soil_photo.location_label}</span>
            <small>Clic para abrir el estudio del suelo</small>
          </figcaption>
        </figure>}
        {(["after"] as const).map(id => {
          const img = data.imagery[id];
          if (!img?.available || !img.image_url) return null;
          const label = { past: "Pasado", before: "Antes", after: "Después" }[id];
          return <figure key={id} className="plant-thumb study-thumb-mini" tabIndex={0} aria-label={`${label}: ${img.date}`}
            onClick={() => setStudy(true)}>
            <img src={api.localPhoto(img.image_url)} alt="" loading="lazy" />
            <figcaption>
              <img src={api.localPhoto(img.image_url)} alt="" loading="lazy" />
              <strong>{label} · {img.date}</strong>
              <span>Satélite {img.resolution_m} m · contorno amarillo = zona NISAR</span>
              <small>Clic para abrir el estudio del suelo</small>
            </figcaption>
          </figure>;
        })}
      </div>
      <button type="button" data-tone="sat" aria-pressed={fieldOn} onClick={satellite} title="Mirada satelital">
        <span aria-hidden="true">🛰</span> Mirada satelital
      </button>
      {!!field.length && <button type="button" data-tone="field" onClick={() => open({
        title: "Fotos de campo de la zona", items: field.map(photo => ({ photo })),
      })} title="Fotos de campo"><span aria-hidden="true">📷</span> Fotos de campo <b>{field.length}</b></button>}
      {!!plants.length && <div className="plant-strip" role="list" aria-label="Plantas que curan la tierra">
        <span className="plant-strip-label" title="Plantas que curan la tierra"><span aria-hidden="true">🌱</span> Plantas que curan la tierra</span>
        {plants.slice(0, 3).map(s => <figure key={s.scientific} className="plant-thumb" role="listitem" tabIndex={0}
          aria-label={`${s.name}: ${s.benefit ?? s.function ?? ""}`}>
          <img src={api.localPhoto(s.photo!.thumbnail_url || s.photo!.image_url)} alt="" loading="lazy" />
          <figcaption>
            <img src={api.localPhoto(s.photo!.image_url)} alt="" loading="lazy" />
            <strong>{s.name}</strong> <em>{s.scientific}</em>
            <span>{s.benefit ?? s.function}</span>
            <small>{s.photo!.location_label} · {s.photo!.author} · {s.photo!.license}</small>
          </figcaption>
        </figure>)}
        {plants.length > 3 && <button type="button" className="plant-more" title="Ver todas las plantas" onClick={() => open({
          title: "Plantas nativas que curan la tierra",
          items: plants.map(sp => ({ photo: sp.photo!, heading: `${sp.name} · ${sp.scientific}`, text: sp.benefit ?? sp.function })),
        })}>+{plants.length - 3}</button>}
      </div>}
      {!!nearby.length && <button type="button" data-tone="life" onClick={() => open({
        title: "Vida observada cerca · hasta 5 km", items: nearby.map(photo => ({ photo })),
      })} title="Vida observada cerca · hasta 5 km"><span aria-hidden="true">🔎</span> Vida cercana <b>{nearby.length}</b></button>}
      {!!data.pins.length && <button type="button" data-tone="pin" onClick={onShowPins} title="Ubicar fotos en el mapa" aria-label="Ubicar fotos en el mapa">
        <span aria-hidden="true">📍</span>
      </button>}
    </nav>
    {study && <ZoneStudy feature={feature} data={data} onClose={() => setStudy(false)} />}
    {gallery && <PhotoGallery gallery={gallery} index={index} setIndex={setIndex} onClose={() => setGallery(undefined)} />}
  </>;
}

function PhotoGallery({ gallery, index, setIndex, onClose }: {
  gallery: Gallery; index: number; setIndex: (i: number) => void; onClose: () => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  const total = gallery.items.length;
  const item = gallery.items[index];
  const go = (step: number) => setIndex((index + step + total) % total);
  useEffect(() => { close.current?.focus(); }, []);
  const src = item.photo.source_url.startsWith("/api/") ? api.localPhoto(item.photo.source_url) : item.photo.source_url;
  return <div className="zone-gallery" role="dialog" aria-modal="true" aria-label={gallery.title}
    onKeyDown={e => { if (e.key === "Escape") onClose(); if (e.key === "ArrowRight") go(1); if (e.key === "ArrowLeft") go(-1); }}>
    <div className="zone-gallery-box">
      <header><strong>{gallery.title}</strong><span>{index + 1} / {total}</span>
        <button ref={close} type="button" onClick={onClose} aria-label="Cerrar galería">✕</button></header>
      <div className="zone-gallery-stage">
        {total > 1 && <button type="button" className="nav" onClick={() => go(-1)} aria-label="Foto anterior">‹</button>}
        <img src={api.localPhoto(item.photo.image_url)} alt={item.heading ?? item.photo.title} />
        {total > 1 && <button type="button" className="nav" onClick={() => go(1)} aria-label="Foto siguiente">›</button>}
      </div>
      <div className="zone-gallery-caption">
        <strong>{item.heading ?? item.photo.title}</strong>
        {item.text && <p className="zone-gallery-text">{item.text}</p>}
        {item.photo.caption && <p>{item.photo.caption}</p>}
        <small>{item.photo.location_label} · {item.photo.taken_at} · {item.photo.author} ·{" "}
          <a href={item.photo.license_url} target="_blank" rel="noopener noreferrer">{item.photo.license}</a> ·{" "}
          <a href={src} target="_blank" rel="noopener noreferrer">{item.photo.page ? `Ver informe · pág. ${item.photo.page}` : "Ver fuente"}</a></small>
      </div>
      {total > 1 && <div className="zone-gallery-thumbs">{gallery.items.map((it, i) =>
        <button key={it.photo.id} type="button" aria-label={`Ver foto ${i + 1}`} aria-current={i === index || undefined} onClick={() => setIndex(i)}>
          <img src={api.localPhoto(it.photo.thumbnail_url || it.photo.image_url)} alt="" loading="lazy" />
        </button>)}</div>}
    </div>
  </div>;
}

const SOIL_PLAIN: Record<string, string> = {
  Cambisols: "Suelo joven, en formación; se erosiona fácil en ladera",
  Leptosols: "Suelo delgado y pedregoso; retiene poca agua",
  Luvisols: "Suelo con arcilla acumulada; fértil pero se compacta",
  Andosols: "Suelo volcánico; guarda mucha agua",
  Phaeozems: "Suelo oscuro y fértil",
  Kastanozems: "Suelo oscuro de zonas secas",
  Regosols: "Suelo suelto y poco desarrollado",
};
const n1 = (v: number) => v.toFixed(1).replace(".", ",");
const n2 = (v: number) => v.toFixed(2).replace(".", ",");
const MOMENTS = [["past", "Pasado"], ["before", "Antes"], ["after", "Después"]] as const;

/** Study dashboard on the main screen: everything visible at once, in short bullet points. */
function ZoneStudy({ feature, data, onClose }: { feature: AlertFeature; data: PlaceEvidence; onClose: () => void }) {
  const close = useRef<HTMLButtonElement>(null);
  const [moment, setMoment] = useState<"past" | "before" | "after">("after");
  useEffect(() => { close.current?.focus(); }, []);
  const rem = feature.properties.remediation!;
  const exp = feature.properties.exposure;
  const img = data.imagery[moment];
  const years = data.greenness?.years ?? [];
  const avg = years.length ? years.reduce((t, y) => t + y.median, 0) / years.length : null;
  const last = years.at(-1);
  const soil = rem.soil;
  const clay = soil?.clay_pct ?? null;
  const sand = soil?.sand_pct ?? null;
  const texture = clay == null || sand == null ? null
    : clay >= 35 ? "arcillosa" : sand >= 55 ? "arenosa" : "franca (mezcla equilibrada)";
  const nov = (data.future_climate?.models ?? []).map(m => m.months["11"]).filter(Boolean);
  const dMin = nov.length ? nov.reduce((t, m) => t + m.min_c, 0) / nov.length : null;
  const rains = nov.map(m => m.rain_pct).filter((v): v is number => v != null);
  const dRain = rains.length ? rains.reduce((t, v) => t + v, 0) / rains.length : null;
  const place = rem.nearby_places?.[0];
  const soilName = soil?.wrb_name && !/sin datos|no disponible/i.test(soil.wrb_name) ? soil.wrb_name : null;
  return <div className="zone-gallery zone-study" role="dialog" aria-modal="true" aria-label="Estudio del suelo"
    onKeyDown={e => { if (e.key === "Escape") onClose(); }}>
    <div className="zone-gallery-box zone-study-box">
      <header>
        <strong>Estudio del suelo · zona {rem.alert_id.slice(-3)}</strong>
        <span data-risk={rem.risk_id} className="study-cause">{rem.risk_name}</span>
        <span>{n1(rem.area_ha)} ha{place ? ` · ${place.name} a ${n1(place.distance_m / 1000)} km` : ""}</span>
        <button ref={close} type="button" onClick={onClose} aria-label="Cerrar estudio">✕</button>
      </header>
      <div className="study-grid">
        <section className="study-image">
          <div className="study-moments">{MOMENTS.map(([id, label]) =>
            <button key={id} type="button" aria-pressed={moment === id} onClick={() => setMoment(id)}>{label}</button>)}</div>
          {img?.available && img.image_url
            ? <img src={api.localPhoto(img.image_url)} alt={`Zona ${rem.alert_id.slice(-3)}, ${img.date}`} />
            : <p className="study-empty">{img?.reason ?? "Sin imagen para este momento"}</p>}
          <small>{img?.date ?? "—"} · satélite {img?.resolution_m ?? "—"} m · contorno amarillo = zona NISAR</small>
        </section>
        <section className="study-card" data-tone="soil">
          <h5>🟫 Suelo</h5>
          <ul>
            <li><b>Tipo:</b> {soilName ? soilName.replace(/s$/, "") : "sin dato"} (SoilGrids)</li>
            {soilName && SOIL_PLAIN[soilName] && <li>{SOIL_PLAIN[soilName]}</li>}
            {texture && <li><b>Textura:</b> {texture} · arcilla {n1(clay!)} % · arena {n1(sand!)} %</li>}
            {rem.factors.slope_deg != null && <li><b>Pendiente:</b> {n1(rem.factors.slope_deg)}°</li>}
            {rem.factors.soil_moisture_m3m3 != null && <li><b>Humedad:</b> {rem.factors.soil_moisture_m3m3.toFixed(3).replace(".", ",")} m³/m³ (NISAR)</li>}
          </ul>
          {data.soil_photo && <figure className="soil-photo">
            <img src={api.localPhoto(data.soil_photo.image_url)} alt={`Perfil de suelo ${soilName ?? ""}`} />
            <figcaption>Ejemplo de este tipo de suelo · {data.soil_photo.location_label} · {data.soil_photo.author} · {data.soil_photo.license}</figcaption>
          </figure>}
        </section>
        <section className="study-card" data-tone="green">
          <h5>🌿 Verdor 2000–{last?.year ?? "—"}</h5>
          {years.length && avg != null && last ? <>
            <div className="greenness-bars small">{years.map(y =>
              <span key={y.year} title={`${y.year}: ${n2(y.median)}`} style={{ height: `${Math.max(4, Math.min(1, y.median / 0.7) * 100)}%` }} />)}</div>
            <ul><li><b>Promedio:</b> {n2(avg)} NDVI</li><li><b>{last.year}:</b> {n2(last.median)} NDVI</li></ul>
          </> : <p className="study-empty">Sin serie publicada</p>}
        </section>
        <section className="study-card" data-tone="people">
          <h5>🏘 Comunidad</h5>
          <ul>
            {(rem.nearby_places ?? []).slice(0, 3).map(pl => <li key={pl.name}><b>{pl.name}</b> · {n1(pl.distance_m / 1000)} km</li>)}
            {exp?.crop_ha ? <li><b>Cultivo:</b> {n1(exp.crop_ha)} ha</li> : null}
            {exp?.people != null && <li><b>Personas:</b> {Math.round(exp.people)} estimadas</li>}
          </ul>
        </section>
        <section className="study-card" data-tone="climate">
          <h5>🌡 Clima hacia 2050 · noviembre</h5>
          {dMin != null ? <ul>
            <li><b>Mínima:</b> {dMin >= 0 ? "+" : ""}{n1(dMin)} °C</li>
            {dRain != null && <li><b>Lluvia:</b> {dRain >= 0 ? "+" : ""}{Math.round(dRain)} %</li>}
            <li>frente a 1991–2020 · modelos CMIP6</li>
          </ul> : <p className="study-empty">Sin proyección publicada</p>}
        </section>
        <section className="study-card" data-tone="life">
          <h5>🔎 Vida cercana · 5 km</h5>
          {data.nearby.length ? <div className="study-thumbs">{data.nearby.slice(0, 6).map(ph =>
            <img key={ph.id} src={api.localPhoto(ph.thumbnail_url || ph.image_url)} alt={ph.title} title={`${ph.title} · ${ph.location_label}`} />)}</div>
            : <p className="study-empty">Sin observaciones a menos de 5 km</p>}
        </section>
      </div>
    </div>
  </div>;
}
