import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { GaiaCover } from "../features/gaia/GaiaCover";
import { FringeIntro } from "../features/intro/FringeIntro";
import { Inspector } from "../features/panels/Inspector";
import { api, type AOI, type Audience, type LayerManifest, type Story, type TimeSeries } from "../lib/api";
import { TABS, type TabId } from "../config/tabs";

// Cesium pesa varios MB: va en un trozo aparte para que la portada pinte de inmediato.
const Globe = lazy(() => import("../features/globe/Globe").then((m) => ({ default: m.Globe })));

export function App() {
  const [tab, setTab] = useState<TabId>("cases");
  const [aois, setAois] = useState<AOI[]>([]);
  const [current, setCurrent] = useState<AOI>();
  const [layers, setLayers] = useState<LayerManifest[]>([]);
  const [story, setStory] = useState<Story>();
  const [ts, setTs] = useState<TimeSeries>();
  const [step, setStep] = useState(0);
  const [pol, setPol] = useState("HVHV");
  const [audience, setAudience] = useState<Audience>("publico");
  const [error, setError] = useState<string>();
  const [exaggeration, setExaggeration] = useState(2);
  const [ready, setReady] = useState(false);
  const onIntroDone = useCallback(() => setReady(true), []);
  // Portada PROJECT GAIA: el globo se precarga cuando la portada ya mostró todo y
  // se revela (con el despertar de franjas) al pulsar «Entrar a la Tierra».
  const [warm, setWarm] = useState(false);
  const [entered, setEntered] = useState(false);
  const onCoverReady = useCallback(() => setWarm(true), []);
  const onEnter = useCallback(() => { setWarm(true); setEntered(true); }, []);

  useEffect(() => {
    api.aois().then(setAois).catch(() => setError("No se pudieron cargar los lugares. ¿Está corriendo la API? (make dev-api)"));
  }, []);

  useEffect(() => {
    if (!current) return;
    setStep(0);
    api.layers(current.id).then(setLayers).catch(() => setLayers([]));
    api.story(current.id).then(setStory).catch(() => setStory(undefined));
    api.timeseries(current.id).then(setTs).catch(() => setTs(undefined));
  }, [current]);

  const storyStep = tab === "story" ? story?.steps[step] : undefined;
  const layer = useMemo(() => {
    const want = storyStep?.layer && storyStep.layer !== "none" ? storyStep.layer.split("_")[1]?.toUpperCase() : pol;
    if (storyStep?.layer === "none") return undefined;
    return layers.find((l) => String(l.provenance.layer) === want) ?? layers[0];
  }, [layers, pol, storyStep]);

  const pick = (a: AOI) => { setCurrent(a); setTab("story"); };

  return (
    <div className="shell">
      {warm && <Suspense fallback={null}>
        <Globe aoi={current} exaggeration={exaggeration} camera={storyStep?.camera ?? "oblique"}
          tileUrl={layer ? api.tileUrl(layer) : undefined} />
      </Suspense>}
      {entered ? <FringeIntro onDone={onIntroDone} /> : <GaiaCover onEnter={onEnter} onReady={onCoverReady} />}
      {ready && <>
        <nav className="rail" aria-label="Secciones">
          {TABS.map((t) => (
            <button key={t.id} aria-current={tab === t.id ? "page" : undefined} onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </nav>
        <Inspector tab={tab} aois={aois} current={current} layers={layers} layer={layer} story={story} ts={ts}
          step={step} setStep={setStep} audience={audience} setAudience={setAudience} pol={pol} setPol={setPol}
          error={error} onPick={pick} exaggeration={exaggeration} setExaggeration={setExaggeration} />
        <footer className="timeline">
          <h1 style={{ fontSize: 20 }}>Bailando con los SARs</h1>
          <span className="muted">{current ? `${current.name}${layer ? ` · ${layer.dates.a} → ${layer.dates.b}` : ""}` : "Radar NISAR · NASA-ISRO · código abierto"}</span>
        </footer>
      </>}
    </div>
  );
}
