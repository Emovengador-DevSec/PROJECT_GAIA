import { AnimatePresence, motion } from "framer-motion";
import type { AOI, Audience, LayerManifest, Story, TimeSeries } from "../../lib/api";
import type { TabId } from "../../config/tabs";
import { Sparkline } from "./Sparkline";

type Props = {
  tab: TabId; aois: AOI[]; current?: AOI; layers: LayerManifest[]; layer?: LayerManifest;
  story?: Story; ts?: TimeSeries; step: number; setStep: (n: number) => void;
  audience: Audience; setAudience: (a: Audience) => void;
  pol: string; setPol: (p: string) => void; error?: string;
  onPick: (a: AOI) => void; exaggeration: number; setExaggeration: (n: number) => void;
};

const empty = (msg: string) => <p className="muted">{msg}</p>;

export function Inspector(p: Props) {
  const { tab, layer, story } = p;
  return (
    <AnimatePresence mode="wait">
      <motion.aside key={tab} className="inspector" initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }} transition={{ duration: 0.2, ease: "easeOut" }}>
        {p.error && <p role="alert">{p.error}</p>}
        <div role="group" aria-label="Nivel de detalle" style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          {(["publico", "tecnico"] as Audience[]).map((a) => (
            <button key={a} className="case" style={{ marginTop: 0, padding: "6px 10px", width: "auto" }}
              aria-pressed={p.audience === a} onClick={() => p.setAudience(a)}>{a === "publico" ? "Público" : "Técnico"}</button>
          ))}
        </div>

        {tab === "story" && (!story ? empty("Elige un lugar en Lugares para ver su historia.") : <>
          <h2>{story.title}</h2>
          <p>{story.audience_summary[p.audience]}</p>
          <h3 style={{ fontSize: 18, marginTop: 16 }}>{p.step + 1}. {story.steps[p.step].title}</h3>
          <p className="muted">{story.steps[p.step].text}</p>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="case" disabled={p.step === 0} onClick={() => p.setStep(p.step - 1)}>Anterior</button>
            <button className="case" disabled={p.step >= story.steps.length - 1} onClick={() => p.setStep(p.step + 1)}>Siguiente</button>
          </div>
          <h3 style={{ fontSize: 18, marginTop: 16 }}>Hipótesis</h3>
          <ul>{story.hypotheses.map((h) => <li key={h.id}>{h.text} <span className="muted">({h.status === "por_verificar" ? "por verificar" : h.status})</span>
            {p.audience === "tecnico" && <div className="muted">Cómo probarla: {h.test}</div>}</li>)}</ul>
          <h3 style={{ fontSize: 18 }}>Por qué lo ve el radar</h3>
          <p className="muted">{story.physics}</p>
          <p className="muted"><strong>Factor humano:</strong> {story.human_factors}</p>
          <p className="muted"><strong>Aplicaciones futuras:</strong> {story.future}</p>
        </>)}

        {tab === "cases" && <>
          <h2>Lugares</h2>
          <p className="muted">Elige un lugar para volar hasta él. Agregar uno nuevo es un archivo en config/aois.</p>
          {p.aois.map((a) => (
            <button key={a.id} className="case" data-role={a.role} onClick={() => p.onPick(a)}>
              <strong>{a.name}</strong>
              <div className="muted">{a.phenomena.join(", ")} · caja {a.status === "approximate" ? "aproximada" : "confirmada"}</div>
            </button>
          ))}
        </>}

        {tab === "changes" && <>
          <h2>Cambios</h2>
          {!p.current ? empty("Aún no hay lugar elegido.") : !p.layers.length
            ? empty(`No hay capas procesadas para ${p.current.name}. Ejecuta sarlab change con dos gránulos reales.`) : <>
            <label className="muted" htmlFor="pol">Polarización</label>
            <select id="pol" value={p.pol} onChange={(e) => p.setPol(e.target.value)} style={{ width: "100%", marginBottom: 12 }}>
              {[...new Set(p.layers.map((l) => String(l.provenance.layer)))].map((x) =>
                <option key={x} value={x}>{x === "HVHV" ? "HV · vegetación" : x === "HHHH" ? "HH · superficie y agua" : x}</option>)}
            </select>
            {layer && <><p>{layer.title}</p>
              <p className="muted">{layer.dates.a} → {layer.dates.b} · {layer.unit} · área válida {layer.quality.valid_area_pct} %</p></>}
          </>}
        </>}

        {tab === "series" && <>
          <h2>Tiempo</h2>
          {p.ts ? <Sparkline ts={p.ts} /> : empty("Sin serie de tiempo. Ejecuta sarlab timeseries con varias fechas del mismo track.")}
        </>}

        {tab === "quality" && <>
          <h2>Calidad y procedencia</h2>
          {layer ? <>
            <p className="muted">Gránulos NISAR de origen:</p>
            <ul>{layer.provenance.granules.map((g) => <li key={g} className="muted" style={{ wordBreak: "break-all" }}>{g}</li>)}</ul>
            {p.audience === "tecnico" && <p className="muted">Método: {String(layer.provenance.method)} · umbral {Number(layer.provenance.threshold_db).toFixed(2)} dB · {String(layer.provenance.frequency)}</p>}
            {layer.quality.provisional && <p className="badge-provisional">Dato NISAR provisional: puede contener errores de calibración.</p>}
          </> : empty("Sin capa seleccionada.")}
        </>}

        {tab === "terrain" && <>
          <h2>Relieve 3D</h2>
          <label className="muted" htmlFor="ex">Exageración vertical: {p.exaggeration}×</label>
          <input id="ex" type="range" min={1} max={10} value={p.exaggeration} onChange={(e) => p.setExaggeration(Number(e.target.value))} style={{ width: "100%" }} />
        </>}

        {tab === "alerts" && <><h2>Alertas</h2>{empty("Zonas con caída de señal, desde /api/alerts, tras procesar el lugar.")}</>}
      </motion.aside>
    </AnimatePresence>
  );
}
