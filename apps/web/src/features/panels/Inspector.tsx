import { motion } from "framer-motion";
import { useReducedMotion } from "../../lib/useMotionPreference";
import type { AOI, AlertFeature, AlertKind, Audience, Catalog, ContextLayer, FeedStatus, GlobeStatus, Health, LayerManifest, PolarizationSummary, Rainfall, Story, TimeSeries, Trend, Validation } from "../../lib/api";
import { TABS, type TabId } from "../../config/tabs";
import { formatDate } from "../../lib/formatDate";
import { AlertDetails } from "../workspace/AlertDetails";
import { ApplicationReference, LearnMore, Resources, nisarGuide, training, uavsarPostcards } from "../workspace/Resources";
import { RadarGlossary, vertexGranule } from "../workspace/RadarGlossary";
import { AlertFeed } from "../workspace/AlertFeed";
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
  health?: Health; mapStatus: GlobeStatus; compare: boolean; setCompare: (value: boolean) => void;
  canUseFalseColor: boolean; falseColor: boolean; setFalseColor: (value: boolean) => void;
  context: ContextLayer[]; activeContext?: ContextLayer; onContext: (id: string | null) => void; moistureCatalog?: Catalog;
  validation?: Validation;
  rainfall?: Rainfall;
  snapshotLabel?: string;
  onClose: () => void; onResources: () => void;
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
  return <div className="catalog-summary"><p><strong>{catalog.granules.length} observaciones {catalog.product} en ASF</strong></p>
    <p>Disponibles para seleccionar y procesar. Una observación catalogada aún no equivale a una capa analizada.</p>
    <details><summary>Consultar fechas y trayectorias</summary><ul className="catalog-list">{catalog.granules.map(granule =>
      <li key={granule.name}><span>{granule.start?.slice(0, 10)}</span><small>Trayectoria {granule.track} · {granule.direction} · {granule.polarizations?.join(" / ")}</small>
        <details><summary>Identificador y tamaño</summary><p className="granule-id">{granule.name}</p><p>{granule.size_mb === null ? "Tamaño sin informar" : `${(granule.size_mb / 1000).toFixed(2)} GB`}</p>
          <a className="source-link" href={vertexGranule(granule.name)} target="_blank" rel="noopener noreferrer">Consultar en Vertex ↗</a>
        </details></li>)}</ul></details>
    {catalog.queried_at && <small>Consulta · {formatDate(catalog.queried_at)}</small>}
  </div>;
}

function ContextLayers({ items, active, onSelect, title = "Observaciones complementarias" }: {
  items: ContextLayer[]; active?: ContextLayer; onSelect: (id: string | null) => void; title?: string;
}) {
  if (!items.length) return null;
  return <section className="context-layers">
    <h4>{title}</h4>
    {items.map(item => <div key={item.id}>
      <p><strong>{item.name}</strong><small>{item.product} · {item.source} · {item.before && `${item.before} → `}<time dateTime={item.date}>{item.date}</time></small></p>
      <p className="muted">{item.note}</p>
      {item.scene && <p className="muted">Escena · <span className="granule-id">{item.scene}</span></p>}
      {item.scenes && <details className="technical-details"><summary>Gránulos ASF de estas fechas</summary>
        <ul className="granule-list">{item.scenes.map(scene => <li key={scene}><a className="source-link granule-id"
          href={vertexGranule(scene)} target="_blank" rel="noopener noreferrer">{scene} ↗</a></li>)}</ul>
      </details>}
      {item.license && <p className="muted">{item.license}</p>}
      {item.available ? <button type="button" className="secondary-action" aria-pressed={active?.id === item.id}
        onClick={() => onSelect(active?.id === item.id ? null : item.id)}>{active?.id === item.id ? "Quitar del globo" : item.before ? "Activar cortina visual" : "Mostrar en el globo"}</button>
        : <p className="empty-inline">Imagen sin publicar para la fecha seleccionada. Consulta la fuente original.</p>}
      <a className="source-link" href={item.href} target="_blank" rel="noopener noreferrer">Datos y metodología ↗</a>
      {item.legend && <a className="source-link" href={item.legend} target="_blank" rel="noopener noreferrer">Leyenda de la capa ↗</a>}
      {item.report && <a className="source-link" href={item.report} target="_blank" rel="noopener noreferrer">Informe de INDECI ↗</a>}
    </div>)}
  </section>;
}

function OperaValidation({ result }: { result?: Validation }) {
  const number = (value: number) => new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(value);
  return <details className="technical-details"><summary>Contraste cuantitativo con OPERA</summary>
    {result ? <>
      <p>{result.source} · <time dateTime={result.date}>{result.date}</time></p>
      <dl className="quality-facts">
        <div><dt>Cobertura común</dt><dd>{number(result.common_ha)} ha</dd></div>
        <div><dt>Caída NISAR HV</dt><dd>{number(result.nisar_loss_ha)} ha</dd></div>
        <div><dt>Perturbación OPERA</dt><dd>{number(result.opera_disturbance_ha)} ha</dd></div>
        <div><dt>Intersección</dt><dd>{number(result.overlap_ha)} ha</dd></div>
        <div><dt>Coincidencia sobre las manchas NISAR</dt><dd>{result.nisar_confirmed_pct == null ? "Sin publicar" : `${number(result.nisar_confirmed_pct)} %`}</dd></div>
        <div><dt>Intersección / unión</dt><dd>{result.agreement_pct === null ? "Muestra insuficiente" : `${number(result.agreement_pct)} %`}</dd></div>
        {result.radar_coverage_pct != null && <div><dt>Cobertura del contraste</dt><dd>{number(result.radar_coverage_pct)} % del radar válido</dd></div>}
      </dl>
      <p className="muted">{result.note}</p>
      {(result.granules ?? [{ name: result.granule, date: result.date }]).map(item =>
        <p key={item.name} className="granule-id">{item.name}</p>)}
      <a className="source-link" href={result.source_url} target="_blank" rel="noopener noreferrer">Consultar producto OPERA ↗</a>
    </> : <p className="empty-inline">El porcentaje requiere la capa NISAR HV procesada y los rásteres originales de estado y fecha OPERA para el mismo intervalo.</p>}
  </details>;
}

export function Inspector(p: Props) {
  const reduce = useReducedMotion();
  const { tab, layer, story } = p;
  const storyStep = story?.steps[p.step];
  const previews = p.context.filter(item => item.kind === "nisar-preview");
  const complementary = p.context.filter(item => item.kind !== "nisar-preview");
  const polarizations = [...new Set(p.layers.map(item => String(item.provenance.layer)))];
  const title = tab === "resources" ? "Fuentes del reto" : TABS.find(item => item.id === tab)?.label;
  return <motion.aside key={p.selected?.properties.id ?? tab} className="inspector" aria-label={title} initial={reduce ? false : { opacity: .5, transform: "translateX(18px)" }}
    animate={{ opacity: 1, transform: "translateX(0)" }} transition={{ duration: .25, ease: [.23, 1, .32, 1] }}>
    <div className="inspector-heading"><h2 id={tab === "resources" ? "challenge-resources-title" : undefined}>{title}</h2><button type="button" className="icon-button" onClick={p.onClose} aria-label="Cerrar panel y explorar el mapa">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
    </button></div>
    <div className="inspector-content" key={tab}>
      {p.error && tab !== "resources" && <p className="status-message" role="alert">{p.error}</p>}
      {p.contextLoading && tab !== "alerts" && tab !== "cases" && tab !== "resources" && <p className="loading-state" role="status">Consultando las observaciones del lugar…</p>}

      {tab === "resources" && <Resources sources={p.sources} health={p.health} />}

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
        {p.selected ? <AlertDetails feature={p.selected} onBack={p.onClearAlert} onResources={p.onResources} /> : <>
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
          <AlertFeed alerts={p.alerts} onSelect={p.onSelectAlert} />
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
        <details className="technical-details"><summary>Por qué lo ve el radar</summary><p>{story.physics}</p><p>{story.human_factors}</p>
          <RadarGlossary /></details>
        <details className="technical-details"><summary>Aplicaciones futuras</summary><p>{story.future}</p>
          <ApplicationReference aoi={p.current?.id} />
        </details>
        {p.audience === "tecnico" && <a className="source-link" href={training.href} target="_blank" rel="noopener noreferrer">Fundamentos del método · NASA ARSET en español ↗</a>}
        <ContextLayers items={previews} active={p.activeContext} onSelect={p.onContext} title="Vista visual NISAR" />
        <ContextLayers items={complementary} active={p.activeContext} onSelect={p.onContext} />
        {p.current?.id === "chosica-rimac" && <details className="technical-details">
          <summary>Lluvia acumulada de tres días</summary>
          {p.rainfall ? <>
            <p>{p.rainfall.dates[0]} → {p.rainfall.dates.at(-1)}</p>
            <p>{p.rainfall.mean_mm === null ? "Sin píxeles válidos en los tres días" : `${p.rainfall.mean_mm.toFixed(1)} mm de media en el área de estudio`}</p>
            <p className="muted">Cobertura común · {p.rainfall.valid_area_pct.toFixed(1)} %</p>
            <p className="muted">{p.rainfall.note}</p>
            <ul className="granule-list">{p.rainfall.granules.map(granule => <li key={granule}>{granule}</li>)}</ul>
          </> : <p className="empty-inline">Para calcular el acumulado se necesitan los tres productos diarios IMERG originales del 22 al 24 de febrero de 2026. El acceso exige una cuenta Earthdata.</p>}
        </details>}
        <LearnMore aoi={p.current} date={p.activeContext?.date ?? layer?.dates.b} onResources={p.onResources} />
      </>)}

      {tab === "changes" && <>
        {!p.current ? <EmptyState title="Selecciona un lugar">Elige un territorio en Lugares para consultar su comparación NISAR.</EmptyState> : <>
          <p className="current-place">{p.current.name}</p>
          {!p.layers.length && !p.contextLoading && <>
            <EmptyState title="Falta procesar NISAR">Se necesitan dos observaciones reales de la misma trayectoria y dirección para mostrar el cambio.
              {p.health && !p.health.credentials.earthdata && " El acceso Earthdata aún no está configurado en el servidor."}
            </EmptyState>
            <details className="technical-details"><summary>Preparar la comparación real</summary>
              <p>Configura EARTHDATA_TOKEN en el servidor. Para Ayacucho, descarga e ingiere los gránulos seleccionados para procesar HH y HV.</p>
              <p>El revelado del radar se habilitará cuando estén publicadas las capas procesadas.</p>
            </details>
          </>}
          {!!p.layers.length && <>
            <label className="field-label" htmlFor="pol">Polarización<select id="pol" value={p.pol} onChange={event => p.setPol(event.target.value)}>
              {polarizations.map(value => <option key={value} value={value}>{value === "HVHV" ? "HV · vegetación" : value === "HHHH" ? "HH · superficie y agua" : value}</option>)}
            </select></label>
            {layer && <><h3>{layer.title}</h3><p className="date-comparison"><time>{layer.dates.a}</time><span aria-hidden="true">→</span><time>{layer.dates.b}</time></p>
              {!p.compare && <div className="data-legend"><span>{layer.range.min?.toFixed(1) ?? "—"} {layer.unit}</span><div className="color-scale" /><span>{layer.range.max?.toFixed(1) ?? "—"} {layer.unit}</span></div>}
              <p className="muted">Cobertura válida en ambas fechas · {layer.quality.valid_area_pct.toLocaleString("es-PE", { maximumFractionDigits: 2 })} % de la zona de estudio</p>
              {layer.kind === "backscatter_diff_db" && <RadarGlossary terms={["hh", "hv", "retrodispersion"]} />}
              {p.polarizationSummary?.strongest && p.polarizationSummary.HHHH && p.polarizationSummary.HVHV &&
                <p className="muted">Mayor área con caída de señal en {p.polarizationSummary.strongest.slice(0, 2)} dentro de la cobertura común.
                  HH · {p.polarizationSummary.HHHH.loss_area_ha} ha. HV · {p.polarizationSummary.HVHV.loss_area_ha} ha.</p>}
              <label className="comparison-toggle"><input type="checkbox" checked={p.compare} disabled={!layer.comparison || !p.health?.tiles} onChange={event => p.setCompare(event.target.checked)} /><span>Comparar antes y después</span></label>
              {p.compare && <>
                <p className="muted">Arrastra la cortina del mapa o utiliza las flechas del teclado para recorrer ambas fechas.</p>
                {layer.kind === "backscatter_diff_db" && <label className="comparison-toggle">
                  <input type="checkbox" checked={p.falseColor} disabled={!p.canUseFalseColor || !p.health?.tiles}
                    onChange={event => p.setFalseColor(event.target.checked)} /><span>Falso color HH/HV</span>
                </label>}
                {p.falseColor && <p className="muted">Rojo: HH. Verde: HV. Azul: relación HH/HV. Ambas fechas usan la misma escala en dB. Los colores describen la señal radar.</p>}
                {layer.kind === "backscatter_diff_db" && !p.canUseFalseColor && <p className="muted">Para el falso color se necesitan HH y HV de los mismos dos gránulos.</p>}
                {p.falseColor && <a className="source-link" href={uavsarPostcards} target="_blank" rel="noopener noreferrer">Ejemplos de falso color · NASA/JPL ↗</a>}
              </>}
              {!layer.comparison && <p className="muted">Esta capa conserva el cambio calculado. La cortina estará disponible al publicar también las dos observaciones de origen.</p>}
              {p.health && !p.health.tiles && <p className="status-message">El servidor de teselas aún no está disponible. Actívalo para ver estas capas sobre el terreno.</p>}
              {layer.quality.provisional && <p className="badge-provisional">NISAR provisional · interpretación pendiente de contraste.</p>}
            </>}
          </>}
          <CatalogSummary catalog={p.catalog} />
          <ContextLayers items={previews} active={p.activeContext} onSelect={p.onContext} title="Mosaicos oficiales NISAR" />
          {p.current.id === "ayacucho-huanta" && <OperaValidation result={p.validation} />}
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
        {p.snapshotLabel && <p className="snapshot-quality">{p.snapshotLabel}</p>}
        {layer ? <><p className="source-label">NISAR · fuente principal</p><h3>{layer.title}</h3>
          <p className="date-comparison"><span>{layer.dates.a}</span><span>→</span><span>{layer.dates.b}</span></p>
          <dl className="quality-facts"><div><dt>Unidad</dt><dd>{layer.unit}</dd></div><div><dt>Área válida</dt><dd>{layer.quality.valid_area_pct.toFixed(1)} %</dd></div><div><dt>Polarización</dt><dd>{String(layer.provenance.layer ?? "Sin informar")}</dd></div><div><dt>Umbral de cambio</dt><dd>{typeof layer.provenance.threshold_db === "number" ? `${layer.provenance.threshold_db.toFixed(2)} dB` : "Sin informar"}</dd></div></dl>
          <p className="muted">Método · {String(layer.provenance.method ?? "Sin informar")}</p>
          {layer.quality.provisional && <p className="badge-provisional">Producto provisional. Las mediciones pueden revisarse.
            {" "}<a href={`${nisarGuide}products-overview/#nisar-maturity-levels`} target="_blank" rel="noopener noreferrer">Niveles de madurez de ASF ↗</a></p>}
          <details className="technical-details"><summary>Gránulos de origen</summary><ul className="granule-list">{layer.provenance.granules.map(granule =>
            <li key={granule}><span>{granule}</span><br /><a className="source-link" href={vertexGranule(granule)} target="_blank" rel="noopener noreferrer">Consultar en Vertex ↗</a></li>)}</ul></details>
        </> : <><EmptyState title="Procedencia sin capa seleccionada">Selecciona una capa NISAR procesada para consultar sus fechas, gránulos y calidad.</EmptyState><CatalogSummary catalog={p.catalog} /></>}
        <RadarGlossary terms={["provisional", "gcov", "gunw", "sme2"]} />
        {p.current?.id === "ayacucho-huanta" && layer?.provenance.layer === "HVHV" && <OperaValidation result={p.validation} />}
        {p.moistureCatalog && <CatalogSummary catalog={p.moistureCatalog} />}
        <a className="source-link" href={nisarGuide} target="_blank" rel="noopener noreferrer">Consultar la guía de datos NISAR ↗</a>
        <button type="button" className="text-button" onClick={p.onResources}>Ver fuentes del reto</button>
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
