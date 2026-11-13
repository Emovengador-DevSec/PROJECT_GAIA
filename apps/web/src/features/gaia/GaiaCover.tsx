import { useCallback, useEffect, useRef, useState } from "react";
import { useAmbientSound } from "./useAmbientSound";
import "./gaia.css";

/**
 * Portada "PROJECT GAIA": video renderizado en Blender (intro de 6 s + bucle de 10 s)
 * a pantalla completa. La entrada se revela después de que asoma el Sol.
 *
 * - El póster final se usa si falla el video o se solicita movimiento reducido.
 * - En pantallas verticales se usa la versión 1080x1920.
 * - Con prefers-reduced-motion solo se muestra el póster, sin animación.
 */

const MEDIA = "/media";
const FILM_VERSION = "?v=4";
const PORTRAIT = "(orientation: portrait) and (max-width: 900px)";
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
const ENTRY_CUE_SECONDS = 4.5;
type EntryState = "waiting" | "reveal" | "ready";
const FACTS = [
  { label: "Radar NISAR", value: "L", description: "El proyecto usa datos del radar NISAR en banda L" },
  { label: "Longitud de onda", value: "24", unit: "cm", description: "Longitud de onda de aproximadamente 24 cm del radar NISAR en banda L" },
  { label: "Repetición", value: "12", unit: "días", description: "NISAR repite su trayectoria cada 12 días para observar cambios en la superficie" },
] as const;

type Props = {
  /** La persona pulsó el título «PROJECT GAIA». */
  onEnter: () => void;
  /** El amanecer de la intro permite empezar a precargar el globo. */
  onReady?: () => void;
};

export function GaiaCover({ onEnter, onReady }: Props) {
  const [reduce, setReduce] = useState(() => window.matchMedia(REDUCED_MOTION).matches);
  const [portrait, setPortrait] = useState(() => window.matchMedia(PORTRAIT).matches);
  const [entry, setEntry] = useState<EntryState>(reduce ? "ready" : "waiting");
  const [introDone, setIntroDone] = useState(reduce);
  const [looping, setLooping] = useState(false);
  const [leaving, setLeaving] = useState(false);
  /** El video no pudo reproducirse: se deja a la vista el póster (composición final). */
  const [failed, setFailed] = useState(false);
  const intro = useRef<HTMLVideoElement>(null);
  const loop = useRef<HTMLVideoElement>(null);
  const cta = useRef<HTMLButtonElement>(null);
  const credits = useRef<HTMLDetailsElement>(null);
  const loopUnavailable = useRef(false);
  const titleStyle = new URLSearchParams(window.location.search).get("portada") === "editorial"
    ? "editorial" : "orbital";
  const suffix = portrait ? "-v" : "";
  const sound = useAmbientSound(`${MEDIA}/gaia-ambient`);

  const showPoster = useCallback(() => {
    setEntry("ready");
    setFailed(true);
    setIntroDone(true);
    setLooping(false);
    onReady?.();
  }, [onReady]);

  useEffect(() => {
    const media = window.matchMedia(PORTRAIT);
    const motion = window.matchMedia(REDUCED_MOTION);
    const reframe = () => {
      setPortrait(media.matches);
      setReduce(motion.matches);
      setEntry(motion.matches ? "ready" : "waiting");
      setIntroDone(motion.matches);
      loopUnavailable.current = false;
      setLooping(false);
      setFailed(false);
    };
    media.addEventListener("change", reframe);
    motion.addEventListener("change", reframe);
    return () => {
      media.removeEventListener("change", reframe);
      motion.removeEventListener("change", reframe);
    };
  }, []);

  // Ambas señales siguen el tiempo del video, también cuando tarda en cargar.
  useEffect(() => {
    if (reduce) { onReady?.(); return; }
    const v = intro.current;
    if (!v) return;
    let active = true;
    let warmed = false;
    const sync = () => {
      if (!warmed && v.currentTime >= 3.3) {
        warmed = true;
        onReady?.();
      }
      if (v.currentTime >= ENTRY_CUE_SECONDS) {
        setEntry(current => current === "waiting" ? "reveal" : current);
        v.removeEventListener("timeupdate", sync);
      }
    };
    const fail = () => {
      if (active) showPoster();
    };
    const start = () => {
      if (document.hidden) return;
      document.removeEventListener("visibilitychange", start);
      v.play().catch(fail);
    };
    v.addEventListener("error", fail);
    v.addEventListener("timeupdate", sync);
    document.addEventListener("visibilitychange", start);
    start();
    return () => {
      active = false;
      v.removeEventListener("error", fail);
      v.removeEventListener("timeupdate", sync);
      document.removeEventListener("visibilitychange", start);
    };
  }, [reduce, portrait, onReady, showPoster]);

  useEffect(() => {
    const dismiss = (event: PointerEvent) => {
      if (credits.current?.open && !credits.current.contains(event.target as Node)) credits.current.open = false;
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);

  const onIntroEnded = useCallback(() => {
    setEntry(current => current === "waiting" ? "ready" : current);
    setIntroDone(true);
    onReady?.();
    const clip = loop.current;
    if (loopUnavailable.current) { showPoster(); return; }
    clip?.play().then(() => {
      if (loop.current === clip) setLooping(true);
    }).catch(() => { if (loop.current === clip) showPoster(); });
  }, [onReady, showPoster]);

  const skip = () => {
    intro.current?.pause();
    setEntry("ready");
    onIntroEnded();
    requestAnimationFrame(() => cta.current?.focus({ preventScroll: true }));
  };

  const enter = () => {
    if (leaving) return;
    sound.stop(0.7);
    if (reduce) { onEnter(); return; }
    setLeaving(true);
    window.setTimeout(onEnter, 750);
  };

  return (
    <div className="gaia" data-title={titleStyle} data-leaving={leaving || undefined}
      data-portrait={portrait || undefined} role="region" aria-label="Portada de Project Gaia">
      <div className="gaia-backdrop" aria-hidden
        style={reduce || (failed && !looping) ? { backgroundImage: `url("${MEDIA}/gaia-poster${suffix}.jpg${FILM_VERSION}")` } : undefined}>
        {!reduce && <>
          <video key={`intro${suffix}`} ref={intro} className="gaia-video" muted playsInline preload="auto" onEnded={onIntroEnded}
            style={{ opacity: looping || failed ? 0 : 1 }}>
            <source src={`${MEDIA}/gaia-intro${suffix}.webm${FILM_VERSION}`} type="video/webm" />
            <source src={`${MEDIA}/gaia-intro${suffix}.mp4${FILM_VERSION}`} type="video/mp4" onError={showPoster} />
          </video>
          <video key={`loop${suffix}`} ref={loop} className="gaia-video" muted playsInline loop preload="auto" onError={looping ? showPoster : undefined}
            style={{ opacity: looping ? 1 : 0 }}>
            <source src={`${MEDIA}/gaia-loop${suffix}.webm${FILM_VERSION}`} type="video/webm" />
            <source src={`${MEDIA}/gaia-loop${suffix}.mp4${FILM_VERSION}`} type="video/mp4" onError={() => {
              loopUnavailable.current = true;
              if (introDone) showPoster();
            }} />
          </video>
        </>}
      </div>
      <section className="gaia-purpose" hidden={entry === "waiting"} data-entry={entry} aria-label="Sobre Project Gaia">
        <h2>Sudamérica bajo observación.</h2>
        <p className="gaia-purpose-lead">Desde Ayacucho, exploramos cómo los sismos, la erosión y los incendios forestales
          transforman el territorio.</p>
      </section>
      <header className="gaia-head" hidden={entry === "waiting"} data-entry={entry}>
        <h1 className="gaia-title">
          <button ref={cta} type="button" className="gaia-cta" onClick={enter}>
            <span className="gaia-cta-nebula" aria-hidden="true" />
            <svg className="gaia-cta-progress" aria-hidden="true" fill="none">
              <rect x="1" y="1" rx="999" pathLength="100" />
            </svg>
            <span className="gaia-title-main">PROJECT GAIA</span>
            <svg className="gaia-arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 12h15m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </h1>
        <ul className="gaia-facts" aria-label="Radar NISAR">
          {FACTS.map((fact) => (
            <li key={fact.label} className="gaia-fact" title={fact.description}>
              <svg className="gaia-fact-orbit" viewBox="0 0 100 100" fill="none" aria-hidden="true">
                <circle cx="50" cy="50" r="48.5" pathLength="100" stroke="currentColor" strokeWidth="1.2" strokeDasharray="64 10 16 10" />
              </svg>
              <span className="gaia-sr">{fact.description}</span>
              <span className="gaia-fact-value" aria-hidden="true">
                {fact.value}{"unit" in fact && <small> {fact.unit}</small>}
              </span>
              <span className="gaia-fact-label" aria-hidden="true">{fact.label}</span>
            </li>
          ))}
        </ul>
      </header>
      <div className="gaia-tools">
        <button type="button" className="gaia-tool" aria-label={sound.playing ? "Silenciar" : "Activar sonido"}
          title={sound.playing ? "Silenciar" : "Activar sonido"}
          aria-pressed={sound.playing} onClick={sound.toggle}>
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden>
            <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
            {sound.playing
              ? <path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              : <path d="m16.5 9.5 5 5m0-5-5 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />}
          </svg>
        </button>
        {!introDone && (
          <button type="button" className="gaia-tool gaia-skip" aria-label="Saltar intro" title="Saltar intro" onClick={skip}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" aria-hidden="true">
              <path d="m6 5 9 7-9 7zM18 5v14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
      </div>
      <details className="gaia-credits" ref={credits} onKeyDown={(event) => {
        if (event.key === "Escape" && event.currentTarget.open) {
          event.currentTarget.open = false;
          event.currentTarget.querySelector("summary")?.focus();
        }
      }}>
        <summary className="gaia-tool" aria-label="Créditos de la escena" title="Créditos de la escena">
          <svg viewBox="0 0 24 24" width="19" height="19" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="8.3" stroke="currentColor" strokeWidth="1.5" />
            <path d="M12 11v5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            <circle cx="12" cy="8" r="1" fill="currentColor" />
          </svg>
        </summary>
        <p><strong>Escena ilustrativa</strong>Imágenes de la Tierra de NASA Blue Marble y Black Marble. Datos de NISAR (NASA–ISRO).</p>
      </details>
    </div>
  );
}
