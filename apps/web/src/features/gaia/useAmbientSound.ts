import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Sonido ambiente de la portada: un bucle de 32 s sin corte (Web Audio, para que el empalme
 * no haga clic como pasa con <audio loop>).
 *
 * Los navegadores no dejan sonar nada hasta que la persona interactúa, así que el sonido
 * arranca con el primer clic o tecla, y siempre se puede silenciar con `toggle`.
 */
const VOLUME = 0.5;

export function useAmbientSound(base: string) {
  const [wanted, setWanted] = useState(true);     // preferencia de la persona
  const [playing, setPlaying] = useState(false);  // está sonando de verdad
  const ctx = useRef<AudioContext | null>(null);
  const gain = useRef<GainNode | null>(null);
  const loading = useRef(false);

  const fadeTo = useCallback((value: number, seconds: number) => {
    const c = ctx.current, g = gain.current;
    if (!c || !g) return;
    g.gain.cancelScheduledValues(c.currentTime);
    g.gain.setValueAtTime(g.gain.value, c.currentTime);
    g.gain.linearRampToValueAtTime(value, c.currentTime + seconds);
  }, []);

  const start = useCallback(async () => {
    if (ctx.current) {
      await ctx.current.resume();
      fadeTo(VOLUME, 1.2);
      setPlaying(true);
      return;
    }
    if (loading.current) return;
    loading.current = true;
    try {
      const c = new AudioContext();
      const ogg = new Audio().canPlayType('audio/ogg; codecs="opus"') !== "";
      const data = await (await fetch(`${base}.${ogg ? "ogg" : "m4a"}`)).arrayBuffer();
      const buffer = await c.decodeAudioData(data);
      const src = c.createBufferSource();
      src.buffer = buffer;
      src.loop = true;
      const g = c.createGain();
      g.gain.value = 0;
      src.connect(g).connect(c.destination);
      src.start();
      ctx.current = c;
      gain.current = g;
      await c.resume();
      fadeTo(VOLUME, 3);
      setPlaying(true);
    } catch {
      setPlaying(false);       // sin sonido la portada sigue funcionando igual
    } finally {
      loading.current = false;
    }
  }, [base, fadeTo]);

  const stop = useCallback((seconds = 0.8) => {
    fadeTo(0, seconds);
    setPlaying(false);
    const c = ctx.current;
    if (c) window.setTimeout(() => { if (gain.current && gain.current.gain.value < 0.01) void c.suspend(); }, seconds * 1000 + 80);
  }, [fadeTo]);

  // Primer gesto de la persona en cualquier parte de la página.
  useEffect(() => {
    if (!wanted || playing) return;
    const go = () => void start();
    window.addEventListener("pointerdown", go, { once: true });
    window.addEventListener("keydown", go, { once: true });
    return () => { window.removeEventListener("pointerdown", go); window.removeEventListener("keydown", go); };
  }, [wanted, playing, start]);

  useEffect(() => () => { void ctx.current?.close(); }, []);

  const toggle = useCallback(() => {
    if (playing) { setWanted(false); stop(); } else { setWanted(true); void start(); }
  }, [playing, start, stop]);

  return { playing, toggle, stop };
}
