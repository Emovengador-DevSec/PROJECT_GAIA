import { useEffect, useRef, useState } from "react";
import { api, type AlertFeature, type RemediationBulletinResponse } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { formatNumber as number } from "../../lib/formatNumber";
import { ResourceLink, applicationLink } from "./Resources";
import { ZoneActions, ZoneClimate, ZoneDiagnosis } from "./ZoneSheetPanels";
import "./zone-sheet.css";
import { BudgetSummary } from "./BudgetSummary";
import { RecoveryScenario } from "./RecoveryScenario";
import { ZoneIdentity } from "./ZoneIdentity";
import { CountUp } from "./CountUp";
import type { ZoneFocus } from "./ExplorationGuide";


const httpsUrl = (value?: string) => value?.startsWith("https://") ? value : undefined;

function ExposureMetric({ label, value, unit }: { label: string; value?: number | null; unit?: string }) {
  return <div><dt>{label}</dt><dd>{number(value)} {value != null && unit && <small>{unit}</small>}</dd></div>;
}

export function AlertDetails({ feature, onBack, onResources, focusVoice, onChanges, zoneFocus }: {
  feature: AlertFeature; onBack: () => void; onResources: () => void; focusVoice?: boolean;
  onChanges?: () => void; zoneFocus?: ZoneFocus;
}) {
  const p = feature.properties;
  const [sheetTab, setSheetTab] = useState("diagnosis");
  useEffect(() => { if (focusVoice) setSheetTab("voice"); }, [focusVoice]);
  useEffect(() => {
    if (zoneFocus) setSheetTab(zoneFocus.section === "voice" ? "voice" : "diagnosis");
  }, [zoneFocus]);
  useEffect(() => {
    if (!zoneFocus) return;
    const frame = requestAnimationFrame(() => {
      const scroller = document.querySelector(".inspector-content");
      if (zoneFocus.section === "diagnosis") { scroller?.scrollTo(0, 0); return; }
      const selector = zoneFocus.section === "actions" ? ".zone-actions-title"
        : zoneFocus.section === "voice" ? "#zone-panel-voice" : "#zone-panel-diagnosis";
      const target = document.querySelector(selector);
      if (scroller && target) scroller.scrollTo({
        top: scroller.scrollTop + target.getBoundingClientRect().top - scroller.getBoundingClientRect().top - 12,
        behavior: "instant",
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [zoneFocus, sheetTab]);
  const [bulletinData, setBulletinData] = useState<RemediationBulletinResponse | null>(null);
  const voiceSection = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!focusVoice || !bulletinData) return;
    voiceSection.current?.focus({ preventScroll: true });
    voiceSection.current?.scrollIntoView({ block: "start", behavior: "instant" });
  }, [focusVoice, bulletinData, sheetTab]);
  const [bulletinLang, setBulletinLang] = useState<"es" | "qu">("es");
  const [copiedScript, setCopiedScript] = useState(false);
  const [minkaCommunity, setMinkaCommunity] = useState("");
  const [minkaVolunteers, setMinkaVolunteers] = useState<number | "">("");
  const [minkaTools, setMinkaTools] = useState("");
  const [minkaContact, setMinkaContact] = useState("");
  const [commitSuccess, setCommitSuccess] = useState(false);
  const [commitSubmitting, setCommitSubmitting] = useState(false);

  useEffect(() => {
    if (!p.remediation) {
      setBulletinData(null);
      return;
    }
    const aoi = p.aoi_id ?? "ayacucho-huanta";
    const zoneId = p.remediation.alert_id;
    let active = true;
    api.remediationBulletin(aoi, zoneId).then((data) => {
      if (active) setBulletinData(data);
    }).catch(() => {
      // Graceful fallback
    });
    return () => {
      active = false;
    };
  }, [p.remediation, p.aoi_id]);

  const handleCommitmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!p.remediation) return;
    const aoi = p.aoi_id ?? "ayacucho-huanta";
    const zoneId = p.remediation.alert_id;
    setCommitSubmitting(true);
    try {
      const res = await api.postMinkaCommitment(aoi, zoneId, {
        community: minkaCommunity.trim(),
        volunteers: Number(minkaVolunteers),
        tools: minkaTools.trim(),
        contact_name: minkaContact,
      });
      if (bulletinData) {
        setBulletinData({
          ...bulletinData,
          commitments: [...bulletinData.commitments, res],
        });
      }
      setCommitSuccess(true);
      setMinkaCommunity("");
      setMinkaContact("");
      setTimeout(() => setCommitSuccess(false), 4000);
    } catch {
      // Error handling
    } finally {
      setCommitSubmitting(false);
    }
  };


  const source = p.source_kind === "primary" ? "NISAR · fuente principal" : `${p.source} · complementario`;
  const external = httpsUrl(p.source_url);
  const exposure = p.exposure;
  const exposureSources = Object.values(exposure?.sources ?? {});
  const observationDetails = <>
    {p.comparison_summary && <p className="muted">
      La zona de estudio registra {number(p.comparison_summary.loss_area_ha)} ha con caída de señal HV.
      {" "}{p.comparison_summary.alerts} manchas delimitadas reúnen {number(p.comparison_summary.mapped_loss_area_ha)} ha.
      {" "}El total incluye fragmentos menores que el tamaño mínimo de delimitación. Esta ficha corresponde a una mancha.
    </p>}
    <dl className="observation-metrics">
      {p.metrics.magnitude !== undefined && <div><dt>Magnitud</dt><dd><CountUp value={p.metrics.magnitude} decimals={1} /> <small>{p.metrics.magnitude_type ?? "M"}</small></dd></div>}
      {p.metrics.depth_km !== undefined && <div><dt>Profundidad</dt><dd><CountUp value={p.metrics.depth_km} decimals={1} /> <small>km</small></dd></div>}
      {p.metrics.frp_mw !== undefined && <div><dt>Potencia radiativa</dt><dd><CountUp value={p.metrics.frp_mw} decimals={1} /> <small>MW</small></dd></div>}
      {p.metrics.count !== undefined && <div><dt>Detecciones en la celda</dt><dd><CountUp value={p.metrics.count} /> <small>focos</small></dd></div>}
      {p.metrics.area_ha != null && <div><dt>Área de esta mancha</dt><dd><CountUp value={p.metrics.area_ha} decimals={2} /> <small>ha</small></dd></div>}
      {p.metrics.tmax_c != null && <div><dt>Temperatura máxima</dt><dd><CountUp value={p.metrics.tmax_c} decimals={1} /> <small>°C</small></dd></div>}
      {p.metrics.tmin_c != null && <div><dt>Temperatura mínima</dt><dd><CountUp value={p.metrics.tmin_c} decimals={1} /> <small>°C</small></dd></div>}
      {p.metrics.rain_sum_mm != null && <div><dt>Lluvia prevista</dt><dd><CountUp value={p.metrics.rain_sum_mm} decimals={1} /> <small>mm</small></dd></div>}
      {p.metrics.elevation_m != null && <div><dt>Altitud de referencia</dt><dd><CountUp value={p.metrics.elevation_m} decimals={0} /> <small>m s.n.m.</small></dd></div>}
    </dl>
    <p className="observation-note">{p.note}</p>
    <p className="muted">Confianza o revisión · {p.confidence}</p>
    {p.provisional && <p className="badge-provisional">Producto NISAR provisional · calibración sujeta a revisión.</p>}

    <section className="exposure-section">
      <h4>¿A quién afecta?</h4>
      {exposure ? <>
        <dl className="exposure-metrics">
          <ExposureMetric label="Personas estimadas" value={exposure.people} />
          <ExposureMetric label="Cultivo" value={exposure.crop_ha} unit="ha" />
          <ExposureMetric label="Bosque" value={exposure.forest_ha} unit="ha" />
          <ExposureMetric label="Pastizal" value={exposure.grassland_ha} unit="ha" />
          {exposure.other_landcover_ha != null &&
            <ExposureMetric label="Otra cobertura" value={exposure.other_landcover_ha} unit="ha" />}
          <ExposureMetric label="Centros poblados cercanos" value={exposure.settlements} />
        </dl>
        {exposure.landcover_coverage_pct != null && <p className="muted">
          WorldCover clasifica el {number(exposure.landcover_coverage_pct)} % de la mancha.
          {!!exposure.landcover_unmapped_ha && ` Superficie sin clasificar: ${number(exposure.landcover_unmapped_ha)} ha.`}
        </p>}
        {exposure.nearby_places && (exposure.nearby_places.length > 0
          ? <ul className="source-list" aria-label="Distancia de cada centro poblado a la mancha">{exposure.nearby_places.map((place, index) => {
            const link = httpsUrl(place.url);
            return <li key={link ?? `${place.name}-${index}`}>
              {link ? <a href={link} target="_blank" rel="noopener noreferrer">{place.name}</a> : place.name}
              {` · ${number(place.distance_m)} m`}
            </li>;
          })}</ul>
          : <p className="muted">OpenStreetMap no registra centros poblados a {number(exposure.settlement_buffer_m ?? 2000)} m o menos.</p>)}
        <p className="muted">{exposure.note ?? "Estimación de exposición basada en la ubicación y las fuentes disponibles."}</p>
        {!!exposure.issues?.length && <ul className="source-list">{exposure.issues.map(issue =>
          <li key={issue}>{issue}</li>,
        )}</ul>}
        {!!exposureSources.length && <ul className="source-list">{exposureSources.map((value, index) => {
          if (typeof value === "string") return <li key={index}>{value}</li>;
          const sourceLink = httpsUrl(value.url);
          const licenseLink = httpsUrl(value.license_url);
          const year = value.year ?? value.date?.slice(0, 4);
          return <li key={value.name}>
            {sourceLink ? <a href={sourceLink} target="_blank" rel="noopener noreferrer">{value.name}</a> : value.name}
            {year && ` · ${year}`}
            {value.license && <> · {licenseLink
              ? <a href={licenseLink} target="_blank" rel="noopener noreferrer">{value.license}</a> : value.license}</>}
            {value.attribution && <small className="muted"> {value.attribution}</small>}
          </li>;
        })}</ul>}
      </> : <p className="empty-inline">La exposición aún no está calculada. Se necesitan capas de población, cobertura del suelo y centros poblados para estimar personas y cultivos.</p>}
    </section>

  </>;
  return <article className={`alert-detail${p.remediation ? " zone-sheet" : ""}`} data-kind={p.kind}>
    <button type="button" className="text-button detail-back" onClick={onBack}>Volver a las observaciones</button>
    {p.remediation ? <ZoneIdentity feature={feature} /> : <>
    <div className="source-row"><span className="source-label">{source}</span><span className="alert-level" data-level={p.level}>Prioridad {p.level}</span></div>
    <h3>{p.title}</h3>
    <p className="alert-place">{p.place}</p>
    <p className="muted">{formatDate(p.date)}</p>
    </>}
    {!p.remediation && observationDetails}
    {p.remediation && <label className="zone-section-picker">
      <span>Sección de la ficha</span>
      <select className="pulse-select" value={sheetTab} onChange={event => {
        setSheetTab(event.target.value); document.querySelector(".inspector-content")?.scrollTo(0, 0);
      }}>
        <option value="diagnosis">🩺 Diagnóstico</option>
        <option value="climate">🌦 Clima</option>
        <option value="future">💰 Futuro y costos</option>
        <option value="voice">📻 Voz y Minka</option>
      </select>
    </label>}
    {p.remediation && (
      <section className="remediation-section">
        {sheetTab === "diagnosis" && <section id="zone-panel-diagnosis" aria-live="polite">
          <ZoneDiagnosis feature={feature} />
          <ZoneActions feature={feature} onVoice={() => setSheetTab("voice")} />
          <details className="zone-sheet-more"><summary>Ver más · diagnóstico y exposición</summary>
        <div className="source-row">
          <span className="source-label">Solución basada en la naturaleza (SbN)</span>
          <span className="alert-level" data-level={p.remediation.level} style={{ borderColor: p.remediation.color_hex, color: p.remediation.color_hex }}>
            Riesgo {p.remediation.level} · {(p.remediation.index * 100).toFixed(0)}%
          </span>
        </div>
        <h4>Qué pasa y diagnóstico</h4>
        <p><strong>{p.remediation.risk_name}</strong></p>
        <p className="observation-note zone-diagnosis-summary">{p.remediation.summary ?? "Diagnóstico por zona sin publicar. Actualiza el análisis de este territorio."}</p>
        {p.remediation.cause_explanation && <p className="zone-diagnosis-cause">{p.remediation.cause_explanation}</p>}

        <h4>Por qué · factores ponderados</h4>
        <ul className="source-list">
          {p.remediation.factor_details.map((factor, i) => (
            <li key={i}>{factor}</li>
          ))}
        </ul>

        {p.remediation.recipe && (
          <div className="remediation-recipe">
            <h4>Receta recomendada</h4>
            {p.remediation.recipe.disclaimer && (
              <p className="status-message">{p.remediation.recipe.disclaimer}</p>
            )}
            {p.remediation.recipe.species_primary?.length > 0 && (
              <div>
                <strong>Especies nativas recomendadas:</strong>
                <ul className="source-list">
                  {p.remediation.recipe.species_primary.map((sp, idx) => (
                    <li key={idx}>{sp}</li>
                  ))}
                </ul>
              </div>
            )}
            {p.remediation.soil?.wrb_name && (
              <p className="muted">
                Suelo (SoilGrids): {p.remediation.soil.wrb_name}
                {p.remediation.soil.clay_pct != null && ` · Arcilla: ${p.remediation.soil.clay_pct}%`}
                {p.remediation.soil.sand_pct != null && ` · Arena: ${p.remediation.soil.sand_pct}%`}
              </p>
            )}
          </div>
        )}

          {observationDetails}
          </details>
        </section>}
        {sheetTab === "climate" && <section id="zone-panel-climate" aria-live="polite">
          <ZoneClimate aoi={p.aoi_id ?? p.remediation.aoi_id} />
        </section>}
        {sheetTab === "future" && <section id="zone-panel-future" aria-live="polite">
        <BudgetSummary items={p.remediation.budget ?? []} />

        {p.remediation.cost_benefit && (
          <div className="cost-benefit-box" style={{ marginTop: "1rem", padding: "10px", background: "var(--surface-subtle, #141b22)", borderRadius: "6px", border: "1px solid var(--border-subtle, #30363d)" }}>
            <h4>Evaluación costo-beneficio frente a inacción</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", margin: "8px 0" }}>
              <div style={{ background: "rgba(255,255,255,0.03)", padding: "6px", borderRadius: "4px" }}>
                <span className="muted" style={{ fontSize: "0.75rem" }}>Costo total SbN</span>
                <p style={{ margin: 0, fontWeight: "bold" }}>S/ {number(p.remediation.cost_benefit.intervention_cost_total_pen)}</p>
                {p.remediation.cost_benefit.cost_with_minka_pen < p.remediation.cost_benefit.intervention_cost_total_pen && (
                  <small style={{ color: "#81c784" }}>Con Minka: S/ {number(p.remediation.cost_benefit.cost_with_minka_pen)}</small>
                )}
              </div>
              <div style={{ background: "rgba(255,255,255,0.03)", padding: "6px", borderRadius: "4px" }}>
                <span className="muted" style={{ fontSize: "0.75rem" }}>Pérdida anual evitada</span>
                <p style={{ margin: 0, fontWeight: "bold", color: "#64b5f6" }}>S/ {number(p.remediation.cost_benefit.loss_avoided_annual_pen)} / año</p>
                <small className="muted">Acumulada 5 años: S/ {number(p.remediation.cost_benefit.loss_avoided_5yr_pen)}</small>
              </div>
            </div>
            <p style={{ fontSize: "0.85rem", margin: "6px 0" }}>
              <strong>Ratio Beneficio / Costo (5 años):</strong> {p.remediation.cost_benefit.benefit_cost_ratio_5yr.toFixed(2)}x
              {p.remediation.cost_benefit.benefit_cost_ratio_minka_5yr > p.remediation.cost_benefit.benefit_cost_ratio_5yr && (
                <span style={{ color: "#81c784" }}> (hasta {p.remediation.cost_benefit.benefit_cost_ratio_minka_5yr.toFixed(2)}x con faena Minka)</span>
              )}
            </p>
            <p className="muted" style={{ fontSize: "0.78rem" }}>
              Fuente de valor agrícola: {p.remediation.cost_benefit.valuation_source}
            </p>
          </div>
        )}


        <section className="future-block" data-tone="doc">
          <h4>Constancia satelital (PDF)</h4>
          <ul>
            <li>Coordenadas y fechas del radar NISAR</li>
            <li>Factores medidos y técnicas sugeridas</li>
            <li>Huella SHA-256 para comprobar que no se alteró</li>
          </ul>
          <a className="future-button" href={`/api/remediation/${p.aoi_id ?? "ayacucho-huanta"}/${p.remediation.alert_id}/certificate.pdf`}
            target="_blank" rel="noopener noreferrer">Descargar constancia (PDF)</a>
        </section>

        <section className="future-block" data-tone="photo">
          <h4>Imagen de la zona</h4>
          <ul><li>Sin recorte verificado de esta mancha</li><li>Imagen óptica HLS de toda la zona, antes y después</li></ul>
          {onChanges && <button type="button" className="future-button" onClick={onChanges}>Ver imagen de toda la zona</button>}
        </section>

        {p.remediation.recovery_scenario && <RecoveryScenario scenario={p.remediation.recovery_scenario} />}

        <details className="technical-details">
          <summary>Fuentes</summary>
          <ul className="source-list">
            <li>
              <strong>NISAR (fuente principal):</strong> {p.remediation.sources_nisar.product}
              <br />
              <small className="muted">
                Fechas: {p.remediation.sources_nisar.dates?.join(" → ")}
              </small>
            </li>
            {p.remediation.sources_complementary?.map((s, idx) => (
              <li key={idx}>
                <strong>Complementario:</strong> {s.source}
                {s.license && ` · ${s.license}`}
                {s.url && (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-link">
                    ↗
                  </a>
                )}
              </li>
            ))}
          </ul>
        </details>

        </section>}
        {sheetTab === "voice" && <section id="zone-panel-voice" aria-live="polite">
          {!bulletinData && <p role="status">Boletín sin cargar. Reabre la ficha para consultar el guion publicado.</p>}
        {bulletinData && (
          <div className="last-mile-section" ref={voiceSection} tabIndex={-1} aria-label="GAIA Voz y Minka" style={{ marginTop: "1rem", borderTop: "1px solid var(--border-subtle, #30363d)", paddingTop: "1rem" }}>
            <h4 style={{ margin: "0 0 6px 0", color: "#e879f9", display: "flex", alignItems: "center", gap: "6px" }}>
              <span>📻</span> GAIA Voz · Minka comunal
            </h4>
            <p className="muted" style={{ fontSize: "0.8rem", margin: "0 0 10px 0" }}>
              Último kilómetro: información que llega sin internet, por radioemisoras andinas y faena comunal minka.
            </p>

            {/* Selector de idioma */}
            <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
              <button
                type="button"
                className="lang-button" data-lang="es" aria-pressed={bulletinLang === "es"}
                onClick={() => setBulletinLang("es")}
              >
                Español
              </button>
              <button
                type="button"
                className="lang-button" data-lang="qu" aria-pressed={bulletinLang === "qu"}
                onClick={() => setBulletinLang("qu")}
              >
                Quechua
              </button>
            </div>

            {/* Reproductor de audio */}
            {bulletinLang === "qu" && !bulletinData.audio_url_qu ? (
              <p className="status-message">
                Audio en quechua pendiente: debe grabarlo una persona hablante de quechua chanka.
                El texto de abajo es un borrador sin revisar; no lo difundas todavía.
              </p>
            ) : (
            <div style={{ background: "rgba(0,0,0,0.3)", padding: "10px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)" }}>
              <audio
                key={bulletinLang}
                controls
                preload="none"
                style={{ width: "100%", height: "36px", outline: "none" }}
              >
                <source
                  src={bulletinLang === "es" ? bulletinData.audio_url_es : bulletinData.audio_url_qu ?? undefined}
                  type="audio/wav"
                />
                Tu navegador no soporta el reproductor de audio.
              </audio>
            </div>
            )}

            {/* Guion para locutor */}
            <div style={{ marginTop: "8px", padding: "8px", background: "rgba(255,255,255,0.03)", borderRadius: "4px", fontSize: "0.82rem", lineHeight: 1.45 }}>
              <p style={{ margin: "0 0 6px 0", fontStyle: "italic" }}>
                «{bulletinLang === "es" ? bulletinData.bulletin.script_es : bulletinData.bulletin.script_qu}»
              </p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "6px" }}>
                <button
                  type="button"
                  className="text-button"
                  style={{ fontSize: "0.75rem" }}
                  onClick={() => {
                    const txt = bulletinLang === "es" ? bulletinData.bulletin.script_es : bulletinData.bulletin.script_qu;
                    navigator.clipboard?.writeText(txt);
                    setCopiedScript(true);
                    setTimeout(() => setCopiedScript(false), 2000);
                  }}
                >
                  {copiedScript ? "✓ Guion copiado" : "Copiar guion para radio"}
                </button>
                <small className="muted" style={{ fontSize: "0.72rem" }}>
                  {bulletinLang === "es" ? `${bulletinData.bulletin.words_count_es} palabras` : `${bulletinData.bulletin.words_count_qu} palabras`}
                </small>
              </div>
            </div>

            {/* Mostrar emisoras solo cuando existan registros publicados. */}
            {!!bulletinData.bulletin.stations.length && <details style={{ marginTop: "8px", fontSize: "0.78rem" }}>
              <summary style={{ cursor: "pointer", color: "var(--accent, #64b5f6)" }}>
                Radios locales aliadas para emisión ({bulletinData.bulletin.stations.length})
              </summary>
              <ul style={{ margin: "6px 0 0 0", paddingLeft: "1.2rem" }}>
                {bulletinData.bulletin.stations.map((st) => (
                  <li key={st.id} style={{ marginBottom: "3px" }}>
                    <strong>{st.name} ({st.frequency})</strong> · {st.reach}
                  </li>
                ))}
              </ul>
            </details>}

            {/* Minka comunal */}
            <div className="minka-box" style={{ marginTop: "10px", padding: "10px", background: "rgba(76, 175, 80, 0.08)", border: "1px solid rgba(76, 175, 80, 0.3)", borderRadius: "6px" }}>
              <h5 style={{ margin: "0 0 4px 0", color: "#10b981" }}>Minka comunal</h5>
              <dl className="minka-facts">
                {(bulletinData.minka.techniques ?? []).map(item => <div key={item.name}>
                  <dt>Trabajo</dt>
                  <dd>{item.name}{item.timing?.match(/\(([^)]+)\)/) ? ` · ${item.timing.match(/\(([^)]+)\)/)![1]}` : ""}</dd>
                </div>)}
                <div><dt>Convocar a</dt><dd>{p.remediation.nearby_places?.length
                  ? p.remediation.nearby_places.slice(0, 3).map(pl => `${pl.name} ${(pl.distance_m / 1000).toFixed(1).replace(".", ",")} km`).join(" · ")
                  : "Sin poblados cercanos publicados"}</dd></div>
                {!!bulletinData.minka.recommended_tools.length && <div><dt>Llevar</dt>
                  <dd>{[...new Map(bulletinData.minka.recommended_tools.map(t => t.split(/,| o | y | para /)[0].trim())
                    .map(t => [t.split(" ")[0].toLowerCase(), t] as const)).values()].slice(0, 4).join(" · ")}</dd></div>}
              </dl>

              <div style={{ marginTop: "8px", display: "flex", gap: "6px" }}>
                <a
                  className="primary-action"
                  href={bulletinData.minka.whatsapp.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ flex: 1, justifyContent: "center", background: "#2e7d32", textDecoration: "none", fontSize: "0.78rem" }}
                >
                  Convocar por WhatsApp ↗
                </a>
              </div>

              {/* Registro de compromiso */}
              <details style={{ marginTop: "8px", fontSize: "0.78rem" }}>
                <summary style={{ cursor: "pointer", color: "#81c784", fontWeight: "bold" }}>
                  + Sumar cuadrilla o compromiso ({bulletinData.commitments.length})
                </summary>
                <form onSubmit={handleCommitmentSubmit} style={{ marginTop: "6px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "0.72rem" }} className="muted">Comunidad o sector:</label>
                    <input
                      type="text"
                      required
                      placeholder="Ej. Pallja"
                      value={minkaCommunity}
                      onChange={(e) => setMinkaCommunity(e.target.value)}
                      style={{ width: "100%", padding: "4px 8px", background: "var(--surface, #1e242c)", color: "inherit", border: "1px solid var(--border-subtle, #333)", borderRadius: "4px", fontSize: "0.78rem" }}
                    />
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                    <div>
                      <label style={{ display: "block", fontSize: "0.72rem" }} className="muted">Voluntarios:</label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={minkaVolunteers}
                        onChange={(e) => setMinkaVolunteers(e.target.value === "" ? "" : Number(e.target.value))}
                        required
                        style={{ width: "100%", padding: "4px 8px", background: "var(--surface, #1e242c)", color: "inherit", border: "1px solid var(--border-subtle, #333)", borderRadius: "4px", fontSize: "0.78rem" }}
                      />
                    </div>
                    <div>
                      <label style={{ display: "block", fontSize: "0.72rem" }} className="muted">Contacto / Líder:</label>
                      <input
                        type="text"
                        placeholder="Opcional"
                        value={minkaContact}
                        onChange={(e) => setMinkaContact(e.target.value)}
                        style={{ width: "100%", padding: "4px 8px", background: "var(--surface, #1e242c)", color: "inherit", border: "1px solid var(--border-subtle, #333)", borderRadius: "4px", fontSize: "0.78rem" }}
                      />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "0.72rem" }} className="muted">Herramientas comprometidas:</label>
                    <input
                      type="text"
                      placeholder="Ej. Picos y palas"
                      value={minkaTools}
                      onChange={(e) => setMinkaTools(e.target.value)}
                      style={{ width: "100%", padding: "4px 8px", background: "var(--surface, #1e242c)", color: "inherit", border: "1px solid var(--border-subtle, #333)", borderRadius: "4px", fontSize: "0.78rem" }}
                    />
                  </div>
                  <button
                    type="submit"
                    className="secondary-action"
                    disabled={commitSubmitting}
                    style={{ justifyContent: "center", fontSize: "0.78rem", padding: "4px 8px" }}
                  >
                    {commitSubmitting ? "Registrando..." : "Guardar compromiso"}
                  </button>
                  {commitSuccess && <p style={{ color: "#81c784", margin: "2px 0" }}>✓ Compromiso registrado.</p>}
                </form>

                {bulletinData.commitments.length > 0 && (
                  <ul style={{ marginTop: "6px", paddingLeft: "1.2rem" }}>
                    {bulletinData.commitments.map((c) => (
                      <li key={c.id} style={{ marginBottom: "2px" }}>
                        <strong>{c.community}:</strong> {c.volunteers} comuneros con {c.tools}
                      </li>
                    ))}
                  </ul>
                )}
              </details>
            </div>

          </div>
        )}

        </section>}
        <p className="zone-sheet-notice">{p.remediation.disclaimer}</p>
      </section>
    )}

    <details className="zone-sheet-more"><summary>Fuentes</summary>
      <ul className="resource-links">
        <li><ResourceLink {...applicationLink(p.kind, p.aoi_id)} /></li>
        {external && <li><a className="source-link" href={external} target="_blank" rel="noopener noreferrer">Consultar la observación original ↗</a></li>}
      </ul>
    </details>
  </article>;
}
