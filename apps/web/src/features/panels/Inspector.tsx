import { motion, useReducedMotion } from "framer-motion";
import type { AOI, AlertFeature, AlertKind, Audience, Catalog, FeedStatus, GlobeStatus, Health, LayerManifest, PolarizationSummary, Story, TimeSeries, Trend } from "../../lib/api";
import { TABS, type TabId } from "../../config/tabs";
import { AlertDetails, formatDate } from "../workspace/AlertDetails";
import { Resources } from "../workspace/Resources";
import { Sparkline } from "./Sparkline";

type Props = {
  tab: TabId; aois: AOI[]; current?: AOI; layers: LayerManifest[]; layer?: LayerManifest;
  story?: Story; ts?: TimeSeries; trend?: Trend; catalog?: Catalog; step: number; setStep: (value: number) => void;
  polarizationSummary?: PolarizationSummary;
  audience: Audience; setAudience: (value: Audience) => void; pol: string; setPol: (value: string) => void;
  error?: string; contextLoading: boolean; onPick: (aoi: AOI) => void;
  exaggeration: number; setExaggeration: (value: number) => void;
  alerts: AlertFeature[]; alertsLoading: boolean; alertsError?: string; sources: FeedStatus[];
  selected?: AlertFeature; onSelectAlert: (alert: AlertFeature) => void; onClearAlert: () => void; onRefresh: () => void;
  alertKind: AlertKind | "all"; setAlertKind: (value: AlertKind | "all") => void;
  alertLevel: string; setAlertLevel: (value: string) => void;
  health?: Health; mapStatus: GlobeStatus; compare: boolean; setCompare: (value: boolean) => void; onClose: () => void;
};

const PHENOMENA: Record<string, string> = {
  wildfire: "Incendios y vegetación", deformation: "Deformación del terreno", deforestation: "Pérdida de bosque",
  landslide: "Deslizamientos y huaicos", flooding: "Agua e inundación",
};
function EmptyState({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="empty-state"><h3>{title}</h3><p>{children}</p></div>;
}
function CatalogSummary({ catalog }: { catalog?: Catalog }) {
  if (!catalog?.granules.length) return null;
  return <div className="catalog-summary"><p><strong>{catalog.granules.length} observaciones en el catálogo de ASF</strong></p>
    <p>Disponibles para seleccionar y procesar. Una observación catalogada aún no equivale a una capa analizada.</p>
    <details><summary>Consultar fechas y trayectorias</summary><ul className="catalog-list">{catalog.granules.map(granule =>
      <li key={granule.name}><span>{granule.start?.slice(0, 10)}</span><small>Trayectoria {granule.track} · {granule.direction} · {granule.polarizations?.join(" / ")}</small>
        <details><summary>Identificador y tamaño</summary><p className="granule-id">{granule.name}</p><p>{granule.size_mb === null ? "Tamaño sin informar" : `${(granule.size_mb / 1000).toFixed(2)} GB`}</p></details></li>)}</ul></details>
    {catalog.queried_at && <small>Consulta · {formatDate(catalog.queried_at)}</small>}
  </div>;
}

export function Inspector(p: Props) {
  const reduce = useReducedMotion();
  const { tab, layer, story } = p;
  const storyStep = story?.steps[p.step];
  const polarizations = [...new Set(p.layers.map(item => String(item.provenance.layer)))];
  const title = TABS.find(item => item.id === tab)?.label;
  return <motion.aside className="inspector" aria-label={title} initial={reduce ? false : { opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }} transition={{ duration: .2, ease: "easeOut" }}>
    <div className="inspector-heading"><h2>{title}</h2><button type="button" className="icon-button" onClick={p.onClose} aria-label="Cerrar panel y explorar el mapa">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
    </button></div>
    <div className="inspector-content">
      {p.error && <p className="status-message" role="alert">{p.error}</p>}
      {p.contextLoading && tab !== "alerts" && tab !== "cases" && <p className="loading-state" role="status">Consultando las observaciones del lugar…</p>}

      {tab === "cases" && <>
        <p className="panel-introduction">Cuatro territorios, distintas huellas. Elige un caso para situar las observaciones sobre el mapa.</p>
        <div className="case-list">{p.aois.map(aoi => <button key={aoi.id} type="button" className="case" aria-pressed={p.current?.id === aoi.id} onClick={() => p.onPick(aoi)}>
          <span><strong>{aoi.name}</strong><small>{aoi.phenomena.map(item => PHENOMENA[item] ?? item).join(" · ")}</small></span>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5" /></svg>
        </button>)}</div>
        {!p.aois.length && <EmptyState title="Lugares sin cargar">Comprueba la conexión con el servidor y vuelve a abrir la aplicación.</EmptyState>}
        {p.current?.notes && <p className="muted aoi-notes">{p.current.notes}</p>}
      </>}

      {tab === "alerts" && <>
        {p.selected ? <AlertDetails feature={p.selected} onBack={p.onClearAlert} /> : <>
          <div className="panel-subheading"><p>Observaciones con fuente y fecha</p><button type="button" className="text-button" disabled={p.alertsLoading} onClick={p.onRefresh}>{p.alertsLoading ? "Actualizando…" : "Actualizar"}</button></div>
          <div className="alert-filters">
            <label>Observación<select value={p.alertKind} onChange={event => p.setAlertKind(event.target.value as AlertKind | "all")}>
              <option value="all">Todas las fuentes</option><option value="surface_change">NISAR · cambio de señal</option>
              <option value="deformation">NISAR · deformación</option><option value="quake">USGS · sismos</option><option value="fire">FIRMS · focos de calor</option>
            </select></label>
            <label>Prioridad<select value={p.alertLevel} onChange={event => p.setAlertLevel(event.target.value)}>
              <option value="all">Todas</option><option value="alto">Alta</option><option value="medio">Media</option><option value="bajo">Baja</option>
            </select></label>
          </div>
          {p.alertsError && <p className="status-message" role="alert">{p.alertsError}</p>}
          {p.alertsLoading && !p.alerts.length && <p className="loading-state" role="status">Consultando los catálogos oficiales de Sudamérica…</p>}
          {!p.alertsLoading && !p.alerts.length && <EmptyState title="Sin observaciones para este filtro">Prueba otra fuente o actualiza la consulta. Las capas NISAR aparecerán cuando se procesen las fechas de una zona.</EmptyState>}
          {!!p.alerts.length && <p className="result-count">{p.alerts.length} observaciones · elige una para localizarla</p>}
          <div className="alert-list">{p.alerts.slice(0, 200).map(feature => {
            const a = feature.properties;
            return <button key={a.id} type="button" className="alert-row" data-kind={a.kind} onClick={() => p.onSelectAlert(feature)}>
              <span className="alert-symbol" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                {a.kind === "quake" ? <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /></> : a.kind === "fire"
                  ? <path d="M13 2c4 7-2 8 2 12l3-4c6 9 1 12-6 12S3 15 7 10c0 4 3 4 3 4-2-7 2-9 3-12Z" />
                  : <path d="m12 3 8 5v8l-8 5-8-5V8Z" />}
              </svg></span>
              <span className="alert-row-content"><strong>{a.title}</strong><span>{a.place}</span><small>{a.source} · {a.source_kind === "primary" ? "NISAR" : "complementario"}</small><time dateTime={a.date}>{formatDate(a.date)}</time></span>
              <span className="alert-level" data-level={a.level}>{a.level === "alto" ? "Alta" : a.level === "medio" ? "Media" : "Baja"}</span>
            </button>;
          })}</div>
          {p.alerts.length > 200 && <p className="muted">La lista muestra las primeras 200 observaciones. Usa los filtros para concretar la consulta.</p>}
        </>}
        <details className="source-health"><summary>Estado de las fuentes</summary>
          <div className="feed-status"><strong>NISAR · principal</strong><span>{p.health?.layers ? `${p.health.layers} capas procesadas` : "Procesamiento pendiente"}</span><p>Observaciones separadas aproximadamente 12 días. La entrega del producto añade su propia demora.</p></div>
          {p.sources.map(source => <div key={source.source} className="feed-status"><strong>{source.source} · complementario</strong>
            <span>{source.stale ? "Copia guardada" : source.status === "ok" ? "Actualizado" : "Sin conexión activa"} · {source.latency}</span>
            {source.last_updated && <time dateTime={source.last_updated}>{formatDate(source.last_updated)}</time>}
            {source.message && <p>{source.message}</p>}
          </div>)}
        </details>
      </>}

      {tab === "story" && (!story || !storyStep ? <EmptyState title="Elige un territorio">Abre Lugares para comenzar la historia de Ayacucho, Sabancaya, Chosica o Madre de Dios.</EmptyState> : <>
        <div className="audience-switch" role="group" aria-label="Nivel de detalle">{(["publico", "tecnico"] as Audience[]).map(value =>
          <button key={value} type="button" aria-pressed={p.audience === value} onClick={() => p.setAudience(value)}>{value === "publico" ? "Público" : "Técnico"}</button>)}</div>
        <h3 className="story-title">{story.title}</h3><p className="panel-introduction">{story.audience_summary[p.audience]}</p>
        <section className="story-current"><div className="story-progress" aria-label={`Paso ${p.step + 1} de ${story.steps.length}`}>
          {story.steps.map((item, index) => <button type="button" key={item.title} aria-label={`Paso ${index + 1}, ${item.title}`} aria-current={p.step === index ? "step" : undefined} onClick={() => p.setStep(index)} />)}
        </div><h4>{storyStep.title}</h4><p>{storyStep.text}</p>
          {storyStep.layer !== "none" && !layer && <p className="status-message">Este paso requiere observaciones NISAR procesadas de la zona.</p>}
          <div className="story-actions"><button type="button" className="secondary-action" disabled={p.step === 0} onClick={() => p.setStep(p.step - 1)}>Anterior</button><button type="button" className="primary-action" disabled={p.step === story.steps.length - 1} onClick={() => p.setStep(p.step + 1)}>Siguiente</button></div>
        </section>
        <details className="technical-details"><summary>Hipótesis y evidencia</summary>{story.hypotheses.map(hypothesis => <div className="hypothesis" key={hypothesis.id}><p>{hypothesis.text}</p><small>{hypothesis.status === "por_verificar" ? "Por verificar con datos" : hypothesis.status}</small><p className="muted">{hypothesis.test}</p></div>)}</details>
        <details className="technical-details"><summary>Por qué lo ve el radar</summary><p>{story.physics}</p><p>{story.human_factors}</p></details>
        <details className="technical-details"><summary>Aplicaciones futuras</summary><p>{story.future}</p></details>
        <a className="source-link" href="https://science.nasa.gov/mission/nisar/get-to-know-sar/" target="_blank" rel="noopener noreferrer">Aprende cómo funciona el radar · NASA ↗</a>
      </>)}

      {tab === "changes" && <>
        {!p.current ? <EmptyState title="Selecciona un lugar">Elige un territorio en Lugares para consultar su comparación NISAR.</EmptyState> : <>
          <p className="current-place">{p.current.name}</p>
          {!p.layers.length && !p.contextLoading && <EmptyState title="Comparación pendiente de procesar">Se necesitan dos observaciones reales de la misma trayectoria y dirección para mostrar el cambio.</EmptyState>}
          <CatalogSummary catalog={p.catalog} />
          {!!p.layers.length && <>
            <label className="field-label" htmlFor="pol">Polarización<select id="pol" value={p.pol} onChange={event => p.setPol(event.target.value)}>
              {polarizations.map(value => <option key={value} value={value}>{value === "HVHV" ? "HV · vegetación" : value === "HHHH" ? "HH · superficie y agua" : value}</option>)}
            </select></label>
            {layer && <><h3>{layer.title}</h3><p className="date-comparison"><time>{layer.dates.a}</time><span aria-hidden="true">→</span><time>{layer.dates.b}</time></p>
              <div className="data-legend"><span>{layer.range.min?.toFixed(1) ?? "—"} {layer.unit}</span><div className="color-scale" /><span>{layer.range.max?.toFixed(1) ?? "—"} {layer.unit}</span></div>
              <p className="muted">Área válida · {layer.quality.valid_area_pct.toFixed(1)} %</p>
              {p.polarizationSummary?.strongest && p.polarizationSummary.HHHH && p.polarizationSummary.HVHV &&
                <p className="muted">Mayor área con caída de señal en {p.polarizationSummary.strongest.slice(0, 2)}.
                  HH · {p.polarizationSummary.HHHH.loss_area_ha} ha. HV · {p.polarizationSummary.HVHV.loss_area_ha} ha.</p>}
              <label className="comparison-toggle"><input type="checkbox" checked={p.compare} disabled={!layer.comparison || !p.health?.tiles} onChange={event => p.setCompare(event.target.checked)} /><span>Comparar antes y después</span></label>
              {p.compare && <p className="muted">Arrastra la cortina del mapa o utiliza las flechas del teclado para recorrer ambas fechas.</p>}
              {!layer.comparison && <p className="muted">Esta capa conserva el cambio calculado. La cortina estará disponible al publicar también las dos observaciones de origen.</p>}
              {p.health && !p.health.tiles && <p className="status-message">El servidor de teselas aún no está disponible. Actívalo para ver estas capas sobre el terreno.</p>}
              {layer.quality.provisional && <p className="badge-provisional">NISAR provisional · interpretación pendiente de contraste.</p>}
            </>}
          </>}
        </>}
      </>}

      {tab === "series" && <>
        <p className="panel-introduction">La evolución de la señal radar por fecha ayuda a estudiar qué cambia y qué permanece.</p>
        {p.ts ? <Sparkline ts={p.ts} trend={p.trend} polarization={p.pol} /> : !p.contextLoading && <EmptyState title="Sin serie procesada">Elige un lugar y procesa sus observaciones compatibles para seguir la evolución de HH y HV.</EmptyState>}
        <section className="trend-explanation"><h3>Proyección de tendencia</h3>
          {p.trend?.status === "ok" ? <><p className="status-message">{p.trend.label}</p><p className="muted">{p.trend.method} · {p.trend.dates} fechas · horizonte de 12 días</p><p className="muted">{p.trend.uncertainty}</p></>
            : <p className="empty-inline">{p.trend?.message ?? "Se requieren cuatro fechas NISAR distintas con datos válidos para calcular una proyección con incertidumbre."}</p>}
          <p className="muted">Esta proyección describe la señal radar de una zona. Los sismos se muestran como eventos observados.</p>
        </section>
      </>}

      {tab === "quality" && <>
        {layer ? <><p className="source-label">NISAR · fuente principal</p><h3>{layer.title}</h3>
          <p className="date-comparison"><span>{layer.dates.a}</span><span>→</span><span>{layer.dates.b}</span></p>
          <dl className="quality-facts"><div><dt>Unidad</dt><dd>{layer.unit}</dd></div><div><dt>Área válida</dt><dd>{layer.quality.valid_area_pct.toFixed(1)} %</dd></div><div><dt>Polarización</dt><dd>{String(layer.provenance.layer ?? "Sin informar")}</dd></div><div><dt>Umbral de cambio</dt><dd>{typeof layer.provenance.threshold_db === "number" ? `${layer.provenance.threshold_db.toFixed(2)} dB` : "Sin informar"}</dd></div></dl>
          <p className="muted">Método · {String(layer.provenance.method ?? "Sin informar")}</p>
          {layer.quality.provisional && <p className="badge-provisional">Producto provisional. Las mediciones pueden revisarse durante la calibración.</p>}
          <details className="technical-details"><summary>Gránulos de origen</summary><ul className="granule-list">{layer.provenance.granules.map(granule => <li key={granule}>{granule}</li>)}</ul></details>
        </> : <><EmptyState title="Procedencia sin capa seleccionada">Selecciona una capa NISAR procesada para consultar sus fechas, gránulos y calidad.</EmptyState><CatalogSummary catalog={p.catalog} /></>}
        <Resources />
      </>}

      {tab === "terrain" && <>
        <p className="panel-introduction">El relieve sitúa las observaciones en los valles y laderas de los Andes.</p>
        <dl className="quality-facts"><div><dt>Imagen</dt><dd>{p.current?.id === "ayacucho-huanta" ? p.mapStatus.regionalImagery ?? p.mapStatus.imagery : p.mapStatus.imagery}</dd></div><div><dt>Relieve</dt><dd>{p.mapStatus.terrain === "ready" ? "Cesium World Terrain" : p.mapStatus.terrain === "regional" ? "Mapzen · Ayacucho" : p.mapStatus.terrain === "loading" ? "Conectando" : "Sin relieve disponible"}</dd></div></dl>
        <label className="field-label" htmlFor="ex">Exageración vertical <strong>{p.exaggeration}×</strong><input id="ex" type="range" min="1" max="10" step="1" value={p.exaggeration} onChange={event => p.setExaggeration(Number(event.target.value))} /></label>
        <p className="muted">Aumentar la escala vertical resalta el relieve para explorarlo. Las mediciones de los datos conservan sus unidades originales.</p>
        {p.mapStatus.terrain === "unavailable" && <p className="status-message">Configura el acceso de Cesium ion para cargar elevaciones reales. La imagen NASA permanece disponible como referencia satelital.</p>}
        {p.mapStatus.terrain === "regional" && <p className="muted">El modelo de elevación local cubre Ayacucho. Activa Cesium ion para ampliar el relieve al resto del globo.</p>}
      </>}
    </div>
  </motion.aside>;
}
