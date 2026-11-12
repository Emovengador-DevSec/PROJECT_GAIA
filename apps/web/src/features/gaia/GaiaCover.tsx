import { useCallback, useEffect, useRef, useState } from "react";
import "./gaia.css";

/**
 * Portada "PROJECT GAIA": video renderizado en Blender (intro de 6 s + bucle de 10 s)
 * como fondo y la interfaz encima, coreografiada con el amanecer del video.
 *
 * - El póster se pinta primero (CSS); el video carga después.
 * - En pantallas verticales se usa la versión 1080x1920.
 * - Con prefers-reduced-motion solo se muestra el póster, sin animación.
 */

const MEDIA = "/media";
/** Segundos del video de intro en los que entra cada bloque (el sol asoma hacia 3,4 s). */
const CUES = [3.3, 4.2, 4.9, 5.5] as const;
const ALL = CUES.length;

const FACTS = [
  { value: "L", unit: "banda", label: "radar que atraviesa nubes y vegetación" },
  { value: "24", unit: "cm", label: "longitud de onda" },
  { value: "12", unit: "días", label: "entre dos pasadas sobre el mismo lugar" },
] as const;

type Props = {
  /** La persona pulsó «Entrar a la Tierra» y la portada terminó de salir. */
  onEnter: () => void;
  /** La portada ya mostró todo: buen momento para precargar el globo. */
  onReady?: () => void;
};

export function GaiaCover({ onEnter, onReady }: Props) {
  const [reduce] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [portrait] = useState(() => window.matchMedia("(orientation: portrait) and (max-width: 900px)").matches);
  const [stage, setStage] = useState(reduce ? ALL : 0);
  const [looping, setLooping] = useState(false);
  const [leaving, setLeaving] = useState(false);
  /** El video no pudo reproducirse: se deja a la vista el póster (composición final). */
  const [failed, setFailed] = useState(false);
  const intro = useRef<HTMLVideoElement>(null);
  const loop = useRef<HTMLVideoElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const cta = useRef<HTMLButtonElement>(null);
  const suffix = portrait ? "-v" : "";

  // Coreografía: los bloques entran según el tiempo real del video, no un reloj aparte.
  useEffect(() => {
    if (reduce) return;
    const v = intro.current;
    if (!v) return;
    let raf = 0;
    let rescue = 0;
    const sync = () => {
      const t = v.currentTime;
      setStage((s) => Math.max(s, CUES.filter((c) => t >= c).length));
    };
    const tick = () => { sync(); if (!v.ended) raf = requestAnimationFrame(tick); };
    // Si el navegador bloquea la reproducción o el video falla, no se esconde la interfaz.
    const fail = () => { setFailed(true); setStage(ALL); };
    const start = () => {
      document.removeEventListener("visibilitychange", start);
      if (document.hidden) { document.addEventListener("visibilitychange", start); return; }
      raf = requestAnimationFrame(tick);
      rescue = window.setTimeout(() => { if (v.currentTime < 0.2) fail(); }, 2500);
      v.play().catch(fail);
    };
    v.addEventListener("error", fail);
    v.addEventListener("timeupdate", sync);   // respaldo si el navegador frena requestAnimationFrame
    start();   // en una pestaña en segundo plano espera a que se muestre
    return () => {
      cancelAnimationFrame(raf); clearTimeout(rescue);
      v.removeEventListener("error", fail); v.removeEventListener("timeupdate", sync);
      document.removeEventListener("visibilitychange", start);
    };
  }, [reduce]);

  useEffect(() => {
    if (stage < ALL) return;
    onReady?.();
    cta.current?.focus({ preventScroll: true });
  }, [stage, onReady]);

  const onIntroEnded = useCallback(() => {
    setStage(ALL);
    loop.current?.play().then(() => setLooping(true)).catch(() => undefined);
  }, []);

  // Paralaje leve con el ratón (solo punteros finos y con movimiento permitido).
  useEffect(() => {
    if (reduce || !window.matchMedia("(pointer: fine)").matches) return;
    const el = root.current;
    if (!el) return;
    let raf = 0;
    const move = (e: PointerEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        el.style.setProperty("--px", ((e.clientX / window.innerWidth) * 2 - 1).toFixed(3));
        el.style.setProperty("--py", ((e.clientY / window.innerHeight) * 2 - 1).toFixed(3));
      });
    };
    window.addEventListener("pointermove", move);
    return () => { window.removeEventListener("pointermove", move); cancelAnimationFrame(raf); };
  }, [reduce]);

  const enter = () => {
    if (leaving) return;
    if (reduce) { onEnter(); return; }
    setLeaving(true);
    window.setTimeout(onEnter, 750);
  };

  return (
    <div ref={root} className="gaia" data-stage={stage} data-leaving={leaving || undefined}
      data-portrait={portrait || undefined} role="region" aria-label="Portada de Project Gaia">
      <div className="gaia-backdrop" aria-hidden>
        {!reduce && <>
          <video ref={intro} className="gaia-video" muted playsInline preload="auto"
            poster={`${MEDIA}/gaia-poster${suffix}.jpg`} onEnded={onIntroEnded}
            style={{ opacity: looping || failed ? 0 : 1 }}>
            <source src={`${MEDIA}/gaia-intro${suffix}.webm`} type="video/webm" />
            <source src={`${MEDIA}/gaia-intro${suffix}.mp4`} type="video/mp4" />
          </video>
          <video ref={loop} className="gaia-video" muted playsInline loop preload="auto"
            style={{ opacity: looping ? 1 : 0 }}>
            <source src={`${MEDIA}/gaia-loop${suffix}.webm`} type="video/webm" />
            <source src={`${MEDIA}/gaia-loop${suffix}.mp4`} type="video/mp4" />
          </video>
        </>}
      </div>
      <div className="gaia-scrim" aria-hidden />

      {stage < ALL && (
        <button className="gaia-skip" onClick={() => setStage(ALL)}>Saltar intro</button>
      )}

      <div className="gaia-ui">
        <header className="gaia-head">
          <p className="gaia-kicker gaia-in" data-at="1">NASA Space Apps 2026<span className="gaia-kicker-extra"> · Dancing with the SARs</span></p>
          <h1 className="gaia-title gaia-in" data-at="1" aria-label="Project Gaia">
            <span className="gaia-title-top" aria-hidden>Project</span>
            <span className="gaia-title-main" aria-hidden>Gaia</span>
          </h1>
          <p className="gaia-sub gaia-in" data-at="2">Bailando con los SARs</p>
          <p className="gaia-lead gaia-in" data-at="2">
            El radar de NISAR ve la Tierra de día, de noche y a través de las nubes.
            Aquí sus datos reales se convierten en respuestas sobre cómo cambia la superficie.
          </p>
        </header>

        <div className="gaia-foot">
          <ul className="gaia-facts gaia-in" data-at="3" aria-label="Datos del radar NISAR">
            {FACTS.map((f) => (
              <li key={f.unit} className="gaia-fact">
                <span className="gaia-fact-ring" aria-hidden />
                <span className="gaia-fact-value">{f.value}</span>
                <span className="gaia-fact-unit">{f.unit}</span>
                <span className="gaia-fact-label">{f.label}</span>
              </li>
            ))}
          </ul>
          <button ref={cta} className="gaia-cta gaia-in" data-at="4" onClick={enter}>
            Entrar a la Tierra
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden>
              <path d="M4 12h15m-6-6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      <p className="gaia-credit">Datos: misión NISAR (NASA-ISRO) · Imágenes de la Tierra: NASA Blue Marble y Black Marble</p>
    </div>
  );
}
