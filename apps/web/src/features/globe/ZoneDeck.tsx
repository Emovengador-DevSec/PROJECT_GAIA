import { useEffect, useRef, useState } from "react";
import { api, type PlaceEvidence, type RealPhoto } from "../../lib/api";
import { FIELD_VIEW, type FieldViewRequest } from "../workspace/PlaceEvidence";

type Gallery = { title: string; items: { photo: RealPhoto; heading?: string; text?: string }[] };

/** Floating dock on the map for the selected zone: satellite view and big photo galleries. */
export function ZoneDeck({ data, zoneId, fieldOn, onShowPins }: {
  data: PlaceEvidence; zoneId: string; fieldOn: boolean; onShowPins: () => void;
}) {
  const [gallery, setGallery] = useState<Gallery>();
  const [index, setIndex] = useState(0);
  const field = data.field_photos ?? [];
  const plants = data.species.filter(s => s.photo);
  const nearby = data.nearby ?? [];
  const open = (g: Gallery) => { setGallery(g); setIndex(0); };
  const satellite = () => window.dispatchEvent(new CustomEvent<FieldViewRequest>(FIELD_VIEW, { detail: { zoneId, design: false } }));
  return <>
    <nav className="zone-deck" aria-label="Explorar esta zona">
      <button type="button" data-tone="sat" aria-pressed={fieldOn} onClick={satellite}>
        <span aria-hidden="true">🛰</span> Mirada satelital
      </button>
      {!!field.length && <button type="button" data-tone="field" onClick={() => open({
        title: "Fotos de campo de la zona", items: field.map(photo => ({ photo })),
      })}><span aria-hidden="true">📷</span> Fotos de campo <b>{field.length}</b></button>}
      {!!plants.length && <button type="button" data-tone="plant" onClick={() => open({
        title: "Plantas nativas que sanan esta zona",
        items: plants.map(s => ({ photo: s.photo!, heading: `${s.name} · ${s.scientific}`, text: s.benefit ?? s.function })),
      })}><span aria-hidden="true">🌱</span> Plantas nativas <b>{plants.length}</b></button>}
      {!!nearby.length && <button type="button" data-tone="life" onClick={() => open({
        title: "Vida observada cerca · hasta 5 km", items: nearby.map(photo => ({ photo })),
      })}><span aria-hidden="true">🔎</span> Vida cercana <b>{nearby.length}</b></button>}
      {!!data.pins.length && <button type="button" data-tone="pin" onClick={onShowPins}>
        <span aria-hidden="true">📍</span> Ubicar fotos
      </button>}
    </nav>
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
