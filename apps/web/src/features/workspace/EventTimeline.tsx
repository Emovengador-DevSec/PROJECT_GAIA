import { useEffect, useMemo, useRef, useState } from "react";
import { useReducedMotion } from "../../lib/useMotionPreference";
import type { AlertFeature, FeedStatus } from "../../lib/api";

const DAY = 86_400_000;
const stamp = (value: number) => new Intl.DateTimeFormat("es-PE", {
  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "UTC", hourCycle: "h23",
}).format(value) + " UTC";

export function EventTimeline({ alerts, sources, cutoff, onChange }: {
  alerts: AlertFeature[]; sources: FeedStatus[]; cutoff?: number; onChange: (value?: number) => void;
}) {
  const reduce = useReducedMotion();
  const [playing, setPlaying] = useState(false);
  const end = useMemo(() => Date.now(), [alerts]);
  const start = end - 30 * DAY;
  const cursor = cutoff ?? end;
  const cursorRef = useRef(cursor);
  const changeRef = useRef(onChange);
  cursorRef.current = cursor;
  changeRef.current = onChange;
  const bins = useMemo(() => {
    const values = Array.from({ length: 30 }, () => ({ quake: 0, fire: 0, radar: 0 }));
    for (const item of alerts) {
      const time = Date.parse(item.properties.date);
      const i = Math.floor((time - start) / DAY);
      if (i < 0 || i > 29) continue;
      const kind = item.properties.kind === "quake" ? "quake" : item.properties.kind === "fire" ? "fire" : "radar";
      values[i][kind]++;
    }
    return values;
  }, [alerts, start]);
  const maximum = Math.max(1, ...bins.map(bin => bin.quake + bin.fire + bin.radar));
  const thermal = sources.find(source => source.source === "NASA FIRMS");
  const primary = alerts.some(item => item.properties.source_kind === "primary");
  useEffect(() => {
    if (!playing || reduce) return;
    let frame = 0;
    let last = performance.now();
    let lastPublish = last;
    let position = cursorRef.current;
    const tick = (now: number) => {
      position = Math.min(end, position + (now - last) * DAY / 1000);
      last = now;
      if (now - lastPublish >= 150 || position >= end) {
        changeRef.current(position >= end ? undefined : position);
        lastPublish = now;
      }
      if (position >= end) setPlaying(false);
      else frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, reduce, end]);
  useEffect(() => { if (reduce) setPlaying(false); }, [reduce]);
  const toggle = () => {
    if (playing) { setPlaying(false); return; }
    if (cursor >= end - 1000) { cursorRef.current = start; onChange(start); }
    setPlaying(true);
  };
  return <section className="event-timeline" aria-label="Reproducción de observaciones por fecha" data-playing={playing || undefined}>
    <button type="button" className="timeline-play" onClick={toggle} disabled={!!reduce || !alerts.length}
      aria-label={playing ? "Pausar secuencia" : "Reproducir 30 días"}
      title={reduce ? "El movimiento reducido está activado. Elige una fecha con la barra." : "Un día por segundo"}>
      <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
        {playing ? <path d="M6 4h4v16H6zm8 0h4v16h-4z" /> : <path d="m7 3 15 9-15 9z" />}
      </svg>
    </button>
    <div className="timeline-track">
      <div className="timeline-heading"><strong>{cutoff == null ? "Últimos 30 días" : "Hasta esta fecha"}</strong>
        <time dateTime={new Date(cursor).toISOString()}>{stamp(cursor)}</time>
        <button type="button" onClick={() => { setPlaying(false); onChange(undefined); }} disabled={cutoff == null}>Ver todo</button></div>
      <div className="timeline-histogram" aria-hidden="true">
        {bins.map((bin, i) => <span key={i} data-past={start + i * DAY <= cursor || undefined}>
          <i data-kind="quake" style={{ height: `${bin.quake / maximum * 100}%` }} />
          <i data-kind="fire" style={{ height: `${bin.fire / maximum * 100}%` }} />
          <i data-kind="surface_change" style={{ height: `${bin.radar / maximum * 100}%` }} />
        </span>)}
      </div>
      <label className="sr-only" htmlFor="event-date">Mostrar observaciones ocurridas hasta esta fecha</label>
      <input id="event-date" type="range" min={start} max={end} step={60_000} value={cursor}
        aria-valuetext={stamp(cursor)} onChange={event => { setPlaying(false); onChange(Number(event.target.value)); }} />
      <div className="timeline-coverage"><span>USGS · 30 días</span><span title={thermal?.message}>FIRMS · {thermal?.coverage_days ?? "según archivo"}{thermal?.coverage_days ? " días" : ""}</span>
        <span>{primary ? "NISAR · según pasada" : "NISAR · pendiente de procesar"}</span><span>1 día / s</span></div>
    </div>
  </section>;
}
