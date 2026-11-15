import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { animate } from "framer-motion";
import { useReducedMotion } from "../lib/useMotionPreference";
import { GaiaCover } from "../features/gaia/GaiaCover";
import { FringeIntro } from "../features/intro/FringeIntro";
import { Inspector } from "../features/panels/Inspector";
import { SectionIcon } from "../features/workspace/SectionIcon";
import { LiveSummary } from "../features/workspace/LiveSummary";
import { EventTimeline } from "../features/workspace/EventTimeline";
import { OrbitCard } from "../features/workspace/OrbitCard";
import { ActionSummary, type ActionDestination } from "../features/workspace/ActionSummary";
import { api, type AOI, type AlertFeature, type AlertKind, type Audience, type Catalog, type CitizenReport,
  type CommunityPlace, type ContextLayer, type FeedStatus, type GlobeStatus, type Health, type LayerManifest, type OrbitData, type PolarizationSummary, type Rainfall, type Story, type TimeSeries, type Trend, type Validation } from "../lib/api";
import { TABS, type TabId } from "../config/tabs";
import "../features/workspace/workspace.css";

const Globe = lazy(() => import("../features/globe/Globe").then(m => ({ default: m.Globe })));

export function App() {
  const [tab, setTab] = useState<TabId>(() => new URLSearchParams(location.search).has("lugar") ? "community" : "alerts");
  const [communityCenter, setCommunityCenter] = useState<[number, number]>();
  const [reports, setReports] = useState<CitizenReport[]>();
  const [reportError, setReportError] = useState(false);
  const [reportLayer, setReportLayer] = useState(false);
  const [pickingReport, setPickingReport] = useState(false);
  const [reportPoint, setReportPoint] = useState<[number, number]>();
  const [aois, setAois] = useState<AOI[]>([]);
  const [current, setCurrent] = useState<AOI>();
  const [layers, setLayers] = useState<LayerManifest[]>([]);
  const [story, setStory] = useState<Story>();
  const [ts, setTs] = useState<TimeSeries>();
  const [trend, setTrend] = useState<Trend>();
  const [catalog, setCatalog] = useState<Catalog>();
  const [moistureCatalog, setMoistureCatalog] = useState<Catalog>();
  const [contextData, setContext] = useState<{ aoiId: string; items: ContextLayer[] }>();
  const context = contextData?.aoiId === current?.id ? contextData?.items ?? [] : [];
  const [contextChoice, setContextChoice] = useState<string | null>();
  const [validation, setValidation] = useState<Validation>();
  const [rainfall, setRainfall] = useState<Rainfall>();
  const [polarizations, setPolarizations] = useState<PolarizationSummary[]>([]);
  const [step, setStep] = useState(0);
  const [pol, setPol] = useState("HVHV");
  const [audience, setAudience] = useState<Audience>("publico");
  const [error, setError] = useState<string>();
  const [contextLoading, setContextLoading] = useState(false);
  const [exaggeration, setExaggeration] = useState(2);
  const [alerts, setAlerts] = useState<AlertFeature[]>([]);
  const [fireCells, setFireCells] = useState<AlertFeature[]>([]);
  const [sources, setSources] = useState<FeedStatus[]>([]);
  const [selected, setSelected] = useState<AlertFeature>();
  const [focusVoice, setFocusVoice] = useState(false);
  const [alertKind, setAlertKind] = useState<AlertKind | "all">("all");
  const [alertLevel, setAlertLevel] = useState("all");
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertsError, setAlertsError] = useState<string>();
  const [health, setHealth] = useState<Health>();
  const [mapStatus, setMapStatus] = useState<GlobeStatus>({ terrain: "loading", imagery: "Cargando imagen satelital" });
  const [realTimeLighting, setRealTimeLighting] = useState(false);
  const [compare, setCompare] = useState(false);
  const [falseColor, setFalseColor] = useState(false);
  const [split, setSplit] = useState(50);
  const reduceMotion = useReducedMotion();
  const openedRadar = useRef<string | undefined>(undefined);
  const stopSweep = useRef<(() => void) | undefined>(undefined);
  const [sweeping, setSweeping] = useState(false);
  const [panelOpen, setPanelOpen] = useState(() => window.innerWidth > 720 || new URLSearchParams(location.search).has("lugar"));
  const [search, setSearch] = useState("");
  const [searchMessage, setSearchMessage] = useState("");
  const [ready, setReady] = useState(false);
  const [cutoff, setCutoff] = useState<number>();
  const [orbitData, setOrbitData] = useState<OrbitData>();
  const [orbitVisible, setOrbitVisible] = useState(true);
  const [satelliteFocus, setSatelliteFocus] = useState(0);
  const [warm, setWarm] = useState(false);
  const [entered, setEntered] = useState(false);
  useEffect(() => {
    if (!entered || (tab !== "community" && !reportLayer)) return;
    const request = new AbortController();
    const refresh = () => {
      api.reports(request.signal).then(value => { setReports(value); setReportError(false); })
        .catch(() => { if (!request.signal.aborted) setReportError(true); });
    };
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => { request.abort(); clearInterval(timer); };
  }, [entered, tab, reportLayer]);
  const requestId = useRef(0);
  const onIntroDone = useCallback(() => setReady(true), []);
  const onCoverReady = useCallback(() => setWarm(true), []);
  const onEnter = useCallback(() => { setWarm(true); setEntered(true); }, []);
  const refreshOrbit = useCallback(() => {
    api.orbit().then(setOrbitData).catch(() => setOrbitData({ status: "unavailable", source_url: "https://celestrak.org/",
      message: "No se pudieron consultar los elementos orbitales. Reintenta con conexión." }));
  }, []);

  useEffect(() => {
    if (!entered) return;
    refreshOrbit();
    const interval = window.setInterval(refreshOrbit, 3_600_000);
    return () => clearInterval(interval);
  }, [entered, refreshOrbit]);

  useEffect(() => {
    let active = true;
    api.aois().then(result => { if (active) setAois(result); })
      .catch(() => { if (active) setError("No se pudieron cargar los lugares. Revisa la conexión con el servidor y vuelve a intentarlo."); });
    api.health().then(result => { if (active) setHealth(result); }).catch(() => undefined);
    return () => { active = false; };
  }, []);

  const refreshAlerts = useCallback(async () => {
    const id = ++requestId.current;
    setAlertsLoading(true);
    setAlertsError(undefined);
    api.health().then(setHealth).catch(() => setHealth(undefined));
    try {
      const result = await api.alerts();
      if (id !== requestId.current) return;
      setAlerts(result.features.filter(feature => feature.geometry && feature.properties?.id));
      setFireCells(result.fire_cells ?? []);
      setSources(result.sources ?? []);
    } catch {
      if (id === requestId.current) setAlertsError("No se pudo actualizar la actividad. Comprueba la conexión y vuelve a intentarlo.");
    } finally {
      if (id === requestId.current) setAlertsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!entered) return;
    refreshAlerts();
    const timer = window.setInterval(refreshAlerts, 600_000);
    return () => { clearInterval(timer); requestId.current++; };
  }, [entered, refreshAlerts]);

  useEffect(() => {
    let active = true;
    setStep(0);
    setCompare(false);
    setFalseColor(false);
    setLayers([]);
    setStory(undefined);
    setTs(undefined);
    setCatalog(undefined);
    setMoistureCatalog(undefined);
    setRainfall(undefined);
    setContext(undefined);
    setContextChoice(undefined);
    setPolarizations([]);
    setTrend(undefined);
    if (!current) { setContextLoading(false); return; }
    setContextLoading(true);
    Promise.allSettled([
      api.layers(current.id), api.story(current.id), api.timeseries(current.id), api.catalog(current.id),
      api.polarizations(current.id), api.context(current.id),
      current.id === "ayacucho-huanta" ? api.catalog(current.id, "SME2") : Promise.resolve(undefined),
      current.id === "chosica-rimac" ? api.rainfall(current.id) : Promise.resolve(null),
    ]).then(([layerResult, storyResult, timeResult, catalogResult, polResult, contextResult, moistureResult, rainResult]) => {
        if (!active) return;
        if (layerResult.status === "fulfilled") setLayers(layerResult.value);
        if (storyResult.status === "fulfilled") setStory(storyResult.value);
        if (timeResult.status === "fulfilled" && timeResult.value.samples.length) setTs(timeResult.value);
        if (catalogResult.status === "fulfilled") setCatalog(catalogResult.value);
        if (polResult.status === "fulfilled") setPolarizations(polResult.value);
        if (contextResult.status === "fulfilled") setContext({ aoiId: current.id, items: contextResult.value });
        if (moistureResult.status === "fulfilled") setMoistureCatalog(moistureResult.value);
        if (rainResult.status === "fulfilled" && rainResult.value) setRainfall(rainResult.value);
        setError(layerResult.status === "rejected" ? "No se pudieron consultar las capas de este lugar. Vuelve a elegirlo para reintentar." : undefined);
        setContextLoading(false);
      });
    return () => { active = false; };
  }, [current]);

  useEffect(() => {
    let active = true;
    if (!current) return;
    setTrend(undefined);
    api.trend(current.id, pol).then(value => { if (active) setTrend(value); }).catch(() => undefined);
    return () => { active = false; };
  }, [current, pol, ts]);

  const storyStep = tab === "story" ? story?.steps[step] : undefined;
  const activeContext = context.find(item => item.available && item.id === (contextChoice === undefined ? storyStep?.context : contextChoice));
  const layer = useMemo(() => {
    if (storyStep?.layer === "none") return undefined;
    const wanted = storyStep?.layer?.split("_").at(-1)?.toUpperCase() ?? pol;
    return layers.find(item => String(item.provenance.layer) === wanted) ?? layers[0];
  }, [layers, pol, storyStep]);
  useEffect(() => {
    let active = true;
    setValidation(undefined);
    if (layer?.provenance.layer === "HVHV") {
      api.validation(layer.id).then(result => {
        if (active && result) setValidation(result);
      }).catch(() => undefined);
    }
    return () => { active = false; };
  }, [layer?.id, layer?.provenance.layer]);
  const filteredAlerts = useMemo(() => alerts.filter(feature =>
    (alertKind === "all" || feature.properties.kind === alertKind) &&
    (alertLevel === "all" || feature.properties.level === alertLevel)), [alerts, alertKind, alertLevel]);
  const visibleFireCells = useMemo(() => {
    const ids = new Set(filteredAlerts.map(item => item.properties.id));
    return fireCells.filter(cell => cell.properties.members?.some(member => ids.has(member.id)));
  }, [filteredAlerts, fireCells]);
  const timelineAlerts = useMemo(() => cutoff == null ? filteredAlerts : filteredAlerts.filter(item =>
    Date.parse(item.properties.date) <= cutoff), [filteredAlerts, cutoff]);
  const showContext = !!activeContext && (cutoff == null || Date.parse(activeContext.date + "T00:00:00Z") <= cutoff);
  const showRadar = !!layer && (cutoff == null || Date.parse(layer.dates.b) <= cutoff);
  const preview = activeContext?.before ? activeContext : undefined;
  const radarComparison = !!health?.tiles && showRadar && !!layer?.comparison && !activeContext &&
    ((tab === "changes" && compare) || storyStep?.layer?.startsWith("diff_"));
  const comparison = radarComparison || (!!preview && showContext);
  const comparisonDates = preview?.before ? { a: preview.before, b: preview.date } : layer?.dates;
  const canUseFalseColor = !!layer?.comparison && layer.kind === "backscatter_diff_db" &&
    ["HHHH", "HVHV"].every(polarization => layers.some(item =>
      item.comparison && item.kind === layer.kind && item.aoi_id === layer.aoi_id &&
      item.provenance.layer === polarization && item.provenance.frequency === layer.provenance.frequency &&
      item.dates.a === layer.dates.a && item.dates.b === layer.dates.b &&
      item.provenance.granules.length === layer.provenance.granules.length &&
      item.provenance.granules.every((granule, index) => granule === layer.provenance.granules[index])
    ));
  const rgb = tab === "changes" && canUseFalseColor && falseColor;
  const radarBounds = radarComparison && tab === "changes" ? layer?.coverage_bbox : undefined;
  const automaticRadar = tab === "changes" && current?.id === "ayacucho-huanta"
    && !!health?.tiles && canUseFalseColor && !contextLoading;

  useEffect(() => {
    if (!automaticRadar) { openedRadar.current = undefined; return; }
    if (openedRadar.current === current?.id) return;
    openedRadar.current = current?.id;
    setCutoff(undefined);
    setContextChoice(null);
    setCompare(true);
    setFalseColor(true);
    setSplit(reduceMotion ? 50 : 0);
    setSweeping(!reduceMotion);
  }, [automaticRadar, current?.id, reduceMotion]);

  useEffect(() => {
    if (!sweeping || !radarComparison || !rgb) return;
    if (reduceMotion) { setSplit(50); setSweeping(false); return; }
    // Let the camera settle on the measured footprint before the comparison sweeps across it.
    let playback: ReturnType<typeof animate> | undefined;
    const timer = window.setTimeout(() => {
      playback = animate(0, 50, { duration: 1.15, ease: "linear", onUpdate: setSplit,
        onComplete: () => setSweeping(false) });
    }, 2_450);
    const stop = () => { clearTimeout(timer); playback?.stop(); };
    stopSweep.current = stop;
    return () => { stop(); stopSweep.current = undefined; };
  }, [sweeping, radarComparison, rgb, reduceMotion]);

  const cancelSweep = () => { stopSweep.current?.(); setSweeping(false); };
  useEffect(() => { if (tab !== "changes" && sweeping) { setSweeping(false); setSplit(50); } }, [tab, sweeping]);

  const pick = (aoi: AOI) => {
    setCurrent(aoi);
    setSelected(undefined);
    setTab("story");
    setPanelOpen(true);
    setSearchMessage("");
  };
  const pickAlert = useCallback((feature: AlertFeature) => {
    setFocusVoice(false);
    setSelected(feature);
    setContextChoice(null);
    setCompare(false);
    setTab("alerts");
    setPanelOpen(true);
    if (feature.properties.aoi_id) {
      const aoi = aois.find(item => item.id === feature.properties.aoi_id);
      if (aoi) setCurrent(aoi);
    }
  }, [aois]);
  const linkedAlert = useRef(new URLSearchParams(window.location.search).get("alert"));
  useEffect(() => {
    if (!linkedAlert.current || !alerts.length) return;
    const match = alerts.find(feature => feature.properties.id === linkedAlert.current)
      ?? fireCells.find(feature => feature.properties.id === linkedAlert.current);
    if (match) { linkedAlert.current = null; pickAlert(match); }
  }, [alerts, fireCells, pickAlert]);
  const chooseTab = (id: TabId) => {
    setFocusVoice(false);
    if (id === "series") {
      cancelSweep();
      setCompare(false);
      setContextChoice(null);
    }
    setPickingReport(false); setTab(id); setSelected(undefined); setPanelOpen(true);
  };
  const openActionSummary = (destination: ActionDestination, aoi: AOI, zoneId?: string) => {
    setCurrent(aoi);
    setCutoff(undefined);
    setCompare(false);
    setContextChoice(null);
    if (destination === "voice") {
      const feature = alerts.find(item => item.properties.id === zoneId && item.properties.aoi_id === aoi.id);
      if (!feature) { chooseTab("action"); return; }
      pickAlert(feature);
      setFocusVoice(true);
      return;
    }
    chooseTab(destination === "climate" ? "series" : "action");
  };
  const locateCommunity = useCallback((place: CommunityPlace) => {
    const zone = aois.find(item => item.id === "ayacucho-huanta");
    if (!zone) return;
    setCurrent(zone);
    setPol("HVHV");
    setCutoff(undefined);
    setContextChoice(null);
    setCompare(false);
    setSelected(undefined);
    setCommunityCenter([...place.center]);
  }, [aois]);

  return <div className="shell" data-workspace={ready || undefined} data-tab={tab}
    data-report-picking={pickingReport || undefined}
    data-panel-open={panelOpen || undefined} data-comparison={comparison || undefined}
    data-sequence={!comparison && tab !== "community" && tab !== "series" || undefined}>
    {warm && <Suspense fallback={null}>
      <Globe aoi={current} communityCenter={tab === "community" ? communityCenter : undefined} active={ready} exaggeration={exaggeration} camera={activeContext ? "zone" : storyStep?.camera ?? "oblique"}
        reports={reportLayer ? reports : undefined}
        reportPicker={tab === "community" && pickingReport ? point => { setReportPoint(point); setPickingReport(false); } : undefined}
        reportPoint={tab === "community" ? reportPoint : undefined}
        offline={health?.offline} radarBounds={radarBounds} realTimeLighting={realTimeLighting}
        tileUrl={health?.tiles && layer && showRadar && !comparison && !activeContext && tab !== "community" ? api.tileUrl(layer) : undefined}
        beforeUrl={layer && showRadar && radarComparison ? api.tileUrl(layer, "before", rgb) : undefined}
        afterUrl={layer && showRadar && radarComparison ? api.tileUrl(layer, "after", rgb) : undefined}
        contextOverlay={activeContext && current && showContext
          ? { url: api.contextImage(current.id, activeContext), credit: activeContext.source,
            beforeUrl: preview ? api.contextImage(current.id, preview, preview.before) : undefined } : undefined}
        split={split} alerts={filteredAlerts} fireCells={visibleFireCells} cutoff={cutoff}
        orbitData={orbitData} orbitVisible={orbitVisible && cutoff == null} satelliteFocus={satelliteFocus}
        selected={selected} onSelect={pickAlert} onStatus={setMapStatus} />
    </Suspense>}
    {entered ? <FringeIntro onDone={onIntroDone} /> : <GaiaCover onEnter={onEnter} onReady={onCoverReady} />}
    {ready && <>
      <header className="workspace-bar">
        <a className="workspace-brand" href="#mapa" onClick={event => { event.preventDefault(); setPanelOpen(false); }} aria-label="GAIA Alerta, explorar mapa">
          <svg viewBox="0 0 32 32" width="32" height="32" fill="none" aria-hidden="true"><circle cx="16" cy="16" r="13" stroke="currentColor" /><path d="M3 16h26M16 3c-9 7-9 19 0 26 9-7 9-19 0-26Z" stroke="currentColor" /><path d="M8 6c4 3 12 3 16 0M8 26c4-3 12-3 16 0" stroke="currentColor" /></svg>
          <span>GAIA <span>Alerta</span></span>
        </a>
        <form className="place-search" role="search" onSubmit={event => {
          event.preventDefault();
          const term = search.trim().toLocaleLowerCase("es");
          const match = term && aois.find(aoi => aoi.name.toLocaleLowerCase("es").includes(term) || aoi.id.includes(term));
          if (match) pick(match);
          else setSearchMessage("Elige uno de los lugares disponibles en la lista.");
        }}>
          <SectionIcon id="cases" />
          <input type="search" aria-label="Buscar un lugar" placeholder="Buscar un lugar"
            list="gaia-places" value={search} onChange={event => { setSearch(event.target.value); setSearchMessage(""); }} />
          <datalist id="gaia-places">{aois.map(aoi => <option key={aoi.id} value={aoi.name} />)}</datalist>
          <button type="submit" aria-label="Ir al lugar">Ir</button>
          {searchMessage && <p className="search-feedback" role="status">{searchMessage}</p>}
        </form>
        <label className="workspace-light">
          <span>Luz</span>
          <select value={realTimeLighting ? "real" : "day"} onChange={event => setRealTimeLighting(event.target.value === "real")}>
            <option value="day">Siempre de día</option>
            <option value="real">Hora real</option>
          </select>
        </label>
        <button type="button" className="workspace-action" onClick={() => { setCurrent(undefined); setSelected(undefined); setTab("alerts"); setPanelOpen(true); }}>Sudamérica</button>
        <button type="button" className="workspace-action community-entry" onClick={() => chooseTab("community")}>Mi comunidad</button>
      </header>

      <div className="map-context" aria-live="polite">
        <span className="map-zone">{current?.name ?? "Sudamérica"}</span>
        <small>{current?.id === "ayacucho-huanta" ? mapStatus.regionalImagery ?? mapStatus.imagery : mapStatus.imagery}</small>
        {activeContext && <small className="map-context-source">{activeContext.product} · {activeContext.date} · {activeContext.kind === "nisar-preview" ? "Vista visual NISAR" : "Complementario"}</small>}
        {mapStatus.terrain === "unavailable" && <button type="button" onClick={() => chooseTab("terrain")}>Relieve sin activar</button>}
        {mapStatus.terrain === "regional" && <button type="button" onClick={() => chooseTab("terrain")}>Relieve local de Ayacucho</button>}
        {!current && !alertsLoading && !alertsError && <LiveSummary alerts={cutoff == null ? alerts : timelineAlerts} sources={sources} onKind={kind => {
          setAlertKind(kind); setSelected(undefined); chooseTab("alerts");
        }} />}
        <ActionSummary aoi={current ?? aois.find(aoi => aoi.role === "flagship")} onOpen={openActionSummary} />
        {!selected && !radarBounds && <OrbitCard data={orbitData} visible={orbitVisible} historical={cutoff != null}
          onToggle={() => setOrbitVisible(value => !value)} onFocus={() => { setCurrent(undefined); setSatelliteFocus(value => value + 1); }} onRefresh={refreshOrbit} />}
      </div>

      <nav className="rail" aria-label="Secciones">
        {TABS.map(item => <button key={item.id} type="button" aria-current={tab === item.id && panelOpen ? "page" : undefined}
          onClick={() => chooseTab(item.id)}><SectionIcon id={item.id} /><span>{item.label}</span></button>)}
      </nav>

      {panelOpen ? <Inspector tab={tab} aois={aois} current={current} layers={layers} layer={layer} story={story} ts={ts} trend={trend} catalog={catalog}
        polarizationSummary={polarizations.length === 1 ? polarizations[0] : undefined}
        step={step} setStep={value => { setStep(value); setContextChoice(undefined); }} audience={audience} setAudience={setAudience} pol={pol} setPol={setPol}
        context={context} activeContext={activeContext} validation={validation}
        onContext={id => { cancelSweep(); setSplit(50); setCompare(false); setContextChoice(id); }} moistureCatalog={moistureCatalog} rainfall={rainfall}
        error={error} contextLoading={contextLoading} onPick={pick} exaggeration={exaggeration} setExaggeration={setExaggeration}
        alerts={timelineAlerts} alertsLoading={alertsLoading} alertsError={alertsError} sources={sources} selected={selected} focusVoice={focusVoice}
        onSelectAlert={pickAlert} onClearAlert={() => setSelected(undefined)} onRefresh={refreshAlerts} alertKind={alertKind}
        setAlertKind={value => { setAlertKind(value); setSelected(undefined); }} alertLevel={alertLevel}
        setAlertLevel={value => { setAlertLevel(value); setSelected(undefined); }} health={health} mapStatus={mapStatus}
        compare={compare} setCompare={value => { cancelSweep(); setSplit(50); if (value) { setContextChoice(null); setCutoff(undefined); } setCompare(value); }}
        canUseFalseColor={canUseFalseColor} falseColor={rgb} setFalseColor={value => { cancelSweep(); setSplit(50); setFalseColor(value); }}
        onClose={() => { setPanelOpen(false); setPickingReport(false); }} onResources={() => chooseTab("resources")} onChanges={() => chooseTab("changes")}
        communityProps={{ onLocate: locateCommunity,
          reports, reportError, reportLayer, picking: pickingReport, point: reportPoint,
          onReportLayer: () => setReportLayer(value => !value),
          onPick: value => {
            setPickingReport(value);
            if (value) setCommunityCenter(communityCenter ? [...communityCenter] : [-74.15, -13.1]);
          },
          onLocateReport: report => { setReportLayer(true); setCommunityCenter([report.lon, report.lat]); },
        }} />
        : <button type="button" className="panel-reopen" onClick={() => setPanelOpen(true)}><SectionIcon id={tab} />Abrir {TABS.find(item => item.id === tab)?.label.toLocaleLowerCase("es")}</button>}

      {comparison && comparisonDates && <div className="comparison-control">
        <div><span>Antes · {comparisonDates.a}</span><span>Después · {comparisonDates.b}</span></div>
        <label className="sr-only" htmlFor="comparison-split">Posición de la cortina antes y después</label>
        <input id="comparison-split" type="range" min="0" max="100" step="1" value={split}
          aria-valuetext={`${Math.round(split)} % antes, ${100 - Math.round(split)} % después`}
          onPointerDown={cancelSweep} onKeyDown={cancelSweep} onChange={event => { cancelSweep(); setSplit(Number(event.target.value)); }} />
      </div>}
      {comparison && <div className="comparison-divider" data-sweeping={sweeping || undefined} style={{ left: `${split}%` }} aria-hidden="true" />}
      {!comparison && tab !== "community" && tab !== "series" && <EventTimeline alerts={filteredAlerts} sources={sources} cutoff={cutoff}
        onChange={value => { setCutoff(value); setSelected(undefined); }} />}

      <div className="map-legend" aria-label="Fuentes del mapa">
        <span data-kind="surface_change"><i />NISAR · cambios</span>
        <span data-kind="quake"><i />USGS · sismos</span>
        <span data-kind="fire"><i />FIRMS · calor</span>
        <span className="fire-age" aria-label="Antigüedad del foco de calor: rojo, menos de 24 horas; naranja, 1 a 3 días; marrón, 4 a 7 días">
          <b data-age="0" />24 h<b data-age="1" />1–3 días<b data-age="2" />4–7 días
        </span>
      </div>
    </>}
  </div>;
}
