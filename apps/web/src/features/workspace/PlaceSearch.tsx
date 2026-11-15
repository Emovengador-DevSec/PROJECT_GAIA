import { useEffect, useId, useRef, useState } from "react";
import type { AOI } from "../../lib/api";
import { SectionIcon } from "./SectionIcon";
import "./place-search.css";

function searchable(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es").trim();
}

export function PlaceSearch({ places, current, onSelect }: {
  places: AOI[]; current?: AOI; onSelect: (place: AOI) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const form = useRef<HTMLFormElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const term = searchable(query);
  const results = places.filter(place => searchable(`${place.name} ${place.id}`).includes(term));
  const activeOption = results[activeIndex];

  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !form.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);

  const showPlaces = () => {
    setQuery("");
    setActiveIndex(-1);
    setOpen(true);
  };
  const select = (place: AOI) => {
    onSelect(place);
    setOpen(false);
    setQuery("");
    setActiveIndex(-1);
  };

  return <form ref={form} className="place-search" role="search" aria-label="Cambiar territorio"
    onBlur={event => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}
    onSubmit={event => {
      event.preventDefault();
      if (!open || (!term && !activeOption)) {
        input.current?.focus();
        showPlaces();
        return;
      }
      const match = activeOption ?? results.find(place => searchable(place.name) === term) ?? results[0];
      if (match) select(match);
    }}>
    <SectionIcon id="cases" />
    <input ref={input} className="place-search-input" type="text" role="combobox"
      aria-label="Buscar o cambiar un lugar" aria-expanded={open} aria-controls={listId} aria-autocomplete="list"
      aria-activedescendant={open && activeOption ? `${listId}-${activeOption.id}` : undefined}
      autoComplete="off" spellCheck={false} placeholder="Buscar un lugar"
      title={current?.name} value={open ? query : current?.name ?? ""}
      onFocus={showPlaces} onClick={() => { if (!open) showPlaces(); }}
      onChange={event => { setQuery(event.target.value); setActiveIndex(-1); setOpen(true); }}
      onKeyDown={event => {
        if (event.key === "Escape") {
          event.preventDefault();
          setOpen(false);
          return;
        }
        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
        event.preventDefault();
        if (!open) {
          showPlaces();
          setActiveIndex(event.key === "ArrowDown" ? 0 : places.length - 1);
          return;
        }
        if (!results.length) return;
        setActiveIndex(index => event.key === "ArrowDown" ? (index + 1) % results.length
          : (index <= 0 ? results.length : index) - 1);
      }} />
    <button type="button" className="place-search-toggle" aria-label={open ? "Cerrar lugares" : "Mostrar todos los lugares"}
      aria-expanded={open} aria-controls={listId}
      onClick={() => {
        if (open) setOpen(false);
        else { input.current?.focus(); showPlaces(); }
      }}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
        aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
    </button>
    <button type="submit" className="place-search-submit" aria-label="Buscar lugar">
      <span>Buscar</span>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
        aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg>
    </button>
    {open && <div className="place-search-menu">
      <ul id={listId} role="listbox" aria-label="Lugares disponibles">
        {results.map((place, index) => <li key={place.id} id={`${listId}-${place.id}`} role="option"
          aria-selected={place.id === current?.id} data-active={index === activeIndex || undefined}
          onPointerDown={event => event.preventDefault()} onClick={() => select(place)}>
          <span>{place.name}
            {place.availability && <small className="place-search-availability" data-ready={place.availability.comparison}>
              {place.availability.comparison ? "Radar procesado" : "Historia y contexto · sin radar procesado"}
            </small>}
          </span>
          {place.id === current?.id && <span className="place-search-check" aria-hidden="true">✓</span>}
        </li>)}
      </ul>
      {!results.length && <p role="status">{places.length ? "Sin coincidencias. Prueba con otro nombre." : "Lugares aún sin cargar."}</p>}
    </div>}
  </form>;
}
