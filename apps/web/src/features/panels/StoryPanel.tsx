import { useEffect, useRef } from "react";
import type { AOI, Audience, ContextLayer, LayerManifest, Rainfall, Story } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";
import { AgriculturalCalendar, AgricultureEvidence, AgricultureSources, useAgriculturalClimate, useStoryAgriculture } from "../community/AgricultureEvidence";
import { RadarGlossary, sensorBasicsLink } from "../workspace/RadarGlossary";
import { ApplicationReference, applicationLink, LearnMore } from "../workspace/Resources";
import { ContextLayers, ContextLayerSources } from "./ContextLayers";
import { RainfallChart } from "./RainfallChart";
import "./story-panel.css";

type Props = {
  story: Story; current?: AOI; step: number; onStep: (step: number) => void;
  audience: Audience; onAudience: (audience: Audience) => void;
  layer?: LayerManifest; layers: LayerManifest[]; context: ContextLayer[]; activeContext?: ContextLayer;
  onContext: (id: string | null) => void; rainfall?: Rainfall; onResources: () => void;
  onNavigate: (action: NonNullable<Story["steps"][number]["action"]>) => void;
};

const hypothesisStatus: Record<string, string> = {
  por_verificar: "Por verificar", confirmada: "Confirmada", descartada: "Descartada",
};

const ayacuchoHighlights = [
  { id: "opera", title: "Cambios de vegetación", source: "OPERA · observación complementaria" },
  { id: "hls-optical", title: "Cultivos", source: "Imagen óptica HLS · complementaria" },
  { id: "nisar-gcov", title: "Mosaico NISAR", source: "GCOV provisional · falso color" },
];

function StoryHighlights({ items, active, onSelect }: {
  items: ContextLayer[]; active?: ContextLayer; onSelect: (id: string | null) => void;
}) {
  const cards = ayacuchoHighlights.flatMap(highlight => {
    const item = items.find(context => context.id === highlight.id);
    return item ? [{ ...highlight, item }] : [];
  });
  if (!cards.length) return null;

  return <div className="story-highlights" role="group" aria-label="Observaciones principales">
    {cards.map(({ id, title, source, item }) => {
      const shown = active?.id === id;
      return <button key={id} type="button" className="story-highlight" data-layer={id} aria-pressed={shown}
        disabled={!item.available} onClick={() => onSelect(shown ? null : id)}>
        <span className="story-highlight-copy">
          <strong>{title}</strong>
          <small>{source}</small>
          <small>{item.before && <><time dateTime={item.before}>{formatDate(item.before)}</time> → </>}
            <time dateTime={item.date}>{formatDate(item.date)}</time></small>
          {!item.available && <small>Imagen sin publicar</small>}
        </span>
        {item.available && <span className="story-highlight-indicator" aria-hidden="true">{shown ? "✓" : "→"}</span>}
      </button>;
    })}
  </div>;
}

function goTo(id: string) {
  const target = document.getElementById(id);
  target?.scrollIntoView({ block: "start" });
  target?.focus({ preventScroll: true });
}

export function StoryPanel({ story, current, step, onStep, audience, onAudience, layer, layers,
  context, activeContext, onContext, rainfall, onResources, onNavigate }: Props) {
  const isAyacucho = story.aoi === "ayacucho-huanta";
  const { data: agriculture, error: agricultureError } = useStoryAgriculture(isAyacucho);
  const { climate, error: climateError } = useAgriculturalClimate(isAyacucho);
  const currentStep = story.steps[step];
  const previousStep = useRef(step);
  const walkthrough = useRef<HTMLElement>(null);
  useEffect(() => {
    if (previousStep.current === step) return;
    previousStep.current = step;
    const scroller = walkthrough.current?.closest(".inspector-content");
    if (scroller && walkthrough.current) scroller.scrollTo({
      top: scroller.scrollTop + walkthrough.current.getBoundingClientRect().top - scroller.getBoundingClientRect().top - 12,
      behavior: "instant",
    });
  }, [step]);
  const comparisonStep = story.steps.findIndex(item => item.layer.startsWith("diff_") && layers.some(manifest =>
    item.layer === `diff_${String(manifest.provenance.layer).toLowerCase()}` && manifest.comparison));
  const otherLayers = isAyacucho ? context.filter(item => !ayacuchoHighlights.some(highlight => highlight.id === item.id)) : context;
  const previews = otherLayers.filter(item => item.kind === "nisar-preview");
  const complementary = otherLayers.filter(item => item.kind !== "nisar-preview");
  const links = [
    applicationLink(undefined, story.aoi), sensorBasicsLink,
    ...(rainfall ? [{ name: rainfall.source, href: rainfall.source_url }] : []),
    ...(agriculture?.calendar.map(item => ({ name: `${item.source} · ${formatDate(item.date)}`, href: item.url })) ?? []),
  ];

  return <article className="story-panel">
    <header className="story-header">
      <h3 className="story-title">{story.title}</h3>
      {isAyacucho && <p className="story-meta story-scope"><strong>Causas por verificar.</strong> {story.audience_summary.publico}</p>}
      {isAyacucho && <details className="story-calendar">
        <summary className="story-highlight">
          <span className="story-highlight-copy">
            <strong>Calendario agrícola y ganado</strong>
            {climate?.agricultural_calendar && <small>{climate.agricultural_calendar.season}</small>}
          </span>
          <span className="story-highlight-indicator" aria-hidden="true">⌄</span>
        </summary>
        {climate?.agricultural_calendar ? <AgriculturalCalendar climate={climate} compact />
          : <p className="story-meta" role="status">{climateError ? "No se pudo cargar el calendario."
            : climate === undefined ? "Consultando el calendario…" : "Calendario sin publicar."}</p>}
      </details>}
      {isAyacucho && <StoryHighlights items={context} active={activeContext} onSelect={onContext} />}
      {(comparisonStep >= 0 || !!otherLayers.length || isAyacucho) && <div className="story-access" role="group" aria-label="Accesos rápidos">
        {comparisonStep >= 0 && <button type="button" className="secondary-action" data-story-action="radar" onClick={() => onStep(comparisonStep)}>Comparar NISAR</button>}
        {!!otherLayers.length && <button type="button" className="secondary-action" onClick={() => goTo("story-layers")}>Capas del globo</button>}
        {isAyacucho && <button type="button" className="secondary-action" data-story-action="agriculture" onClick={() => goTo("story-agriculture")}>Cultivos y clima</button>}
      </div>}
      {(!isAyacucho || audience === "tecnico") && <p className="story-meta">{story.audience_summary[audience]}</p>}
    </header>

    <section ref={walkthrough} className="story-current" aria-label="Recorrido">
      <div className="story-progress" role="group" aria-label={`Paso ${step + 1} de ${story.steps.length}`}>
        {story.steps.map((item, index) => <button type="button" key={item.title}
          aria-label={`Paso ${index + 1}, ${item.title}`} aria-current={step === index ? "step" : undefined}
          onClick={() => onStep(index)}>{index + 1}</button>)}
      </div>
      <div aria-live="polite">
        <h4>{currentStep.title}</h4>
        <ul className="story-points">{[currentStep.text, ...(currentStep.points ?? [])].map(point => <li key={point}>{point}</li>)}</ul>
        {currentStep.layer !== "none" && !layer && <p className="status-message">Observaciones NISAR procesadas pendientes para este paso.</p>}
      </div>
      <div className="story-actions">
        <button type="button" className="secondary-action" disabled={step === 0} onClick={() => onStep(step - 1)}>Anterior</button>
        <span className="story-step-count">{step + 1} de {story.steps.length}</span>
        <button type="button" className="primary-action" disabled={step === story.steps.length - 1} onClick={() => onStep(step + 1)}>Siguiente</button>
      </div>
      {currentStep.action && <button type="button" className="text-button story-step-link" onClick={() => {
        if (currentStep.action === "agriculture") goTo("story-agriculture");
        else onNavigate(currentStep.action!);
      }}>{({
        changes: "Abrir la comparación radar", action: "Abrir diagnóstico de la zona prioritaria",
        quality: "Ver calidad y contraste OPERA", series: "Consultar la serie de fechas",
        agriculture: "Ver cultivos y clima",
      })[currentStep.action]} →</button>}
    </section>

    {!!otherLayers.length && <section className="story-section">
      <h3 id="story-layers" tabIndex={-1}>Capas del globo</h3>
      <ContextLayers items={previews} active={activeContext} onSelect={onContext} title="NISAR · vista visual provisional" compact />
      <ContextLayers items={complementary} active={activeContext} onSelect={onContext} title="Observaciones complementarias" compact />
    </section>}

    {isAyacucho && <section className="story-section">
      <h3 id="story-agriculture" tabIndex={-1}>Cultivos y clima</h3>
      {agriculture ? <AgricultureEvidence data={agriculture} compact climate={climate} /> : <p className="story-meta" role="status">
        {agricultureError ? "No se pudo consultar la pendiente agrícola." : agriculture === null ? "Cruce de cultivos y pendiente sin publicar." : "Consultando cultivos y pendiente…"}
      </p>}
    </section>}

    {story.aoi === "chosica-rimac" && <details className="story-disclosure" open={!!rainfall}>
      <summary>Lluvia acumulada de tres días</summary>
      {rainfall ? <>
        <RainfallChart data={rainfall} />
        <p className="story-meta">{formatDate(rainfall.dates[0])} → {formatDate(rainfall.dates.at(-1))} · {rainfall.source}</p>
        <ul className="story-points">
          <li>{rainfall.mean_mm === null ? "Sin píxeles válidos en los tres días" : `${number(rainfall.mean_mm, 1)} mm de media en el área de estudio`}</li>
          <li>{number(rainfall.valid_area_pct, 1)} % de cobertura común</li>
        </ul>
      </> : <p className="story-meta">Acumulado pendiente de los tres productos IMERG originales del 22 al 24 de febrero de 2026.</p>}
    </details>}

    <details className="story-disclosure"><summary>Hipótesis y evidencia</summary>
      <ul className="story-points">{story.hypotheses.map(item => <li key={item.id}>
        <strong>{hypothesisStatus[item.status] ?? item.status}</strong> · {item.text}
        <small>{item.test}</small>
      </li>)}</ul>
    </details>
    <details className="story-disclosure"><summary>Por qué lo ve el radar</summary>
      <ul className="story-points"><li>{story.physics}</li><li>{story.human_factors}</li></ul>
      <RadarGlossary showLinks={false} />
    </details>
    <details className="story-disclosure"><summary>Aplicaciones futuras</summary>
      <p>{story.future}</p><ApplicationReference aoi={story.aoi} showLink={false} />
    </details>

    <div className="audience-switch" role="group" aria-label="Nivel de detalle">
      {(["publico", "tecnico"] as const).map(mode => <button key={mode} type="button" aria-pressed={audience === mode}
        onClick={() => onAudience(mode)}>{mode === "publico" ? "Público" : "Técnico"}</button>)}
    </div>

    <LearnMore title="Fuentes y metodología" aoi={current} date={activeContext?.date ?? layer?.dates.b}
      onResources={onResources} extraLinks={links}>
      {context.map(item => <details className="story-disclosure" key={item.id}>
        <summary>{item.name}</summary><p>{item.note}</p><ContextLayerSources item={item} />
      </details>)}
      {agriculture && <details className="story-disclosure"><summary>Fuente y método de pendiente</summary>
        <AgricultureSources data={agriculture} />
      </details>}
      {rainfall && <details className="story-disclosure"><summary>Cobertura y gránulos IMERG</summary>
        <p>{rainfall.note}</p>
        <ul className="granule-list">{rainfall.granules.map(granule => <li key={granule}>{granule}</li>)}</ul>
      </details>}
    </LearnMore>
  </article>;
}
