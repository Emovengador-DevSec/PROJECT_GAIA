import type { AOI } from "../../lib/api";
import "./exploration-guide.css";

export type GuideStep = 0 | 1 | 2 | 3 | 4;
export type ZoneFocus = {section: "diagnosis" | "actions" | "voice"; revision: number};
const steps = ["Lugar", "Qué cambió", "Por qué", "Qué hacer", "Avisar"];
const next = ["Ver qué cambió", "Ver por qué", "Ver qué hacer", "Avisar a la comunidad", "Volver a empezar"];

export function ExplorationGuide({ current, activeStep, canAct, onStep, introduction, onDismiss }: {
  current?: AOI; activeStep: GuideStep; canAct: boolean; onStep: (step: GuideStep) => void;
  introduction: boolean; onDismiss: () => void;
}) {
  const available = (step: number) => step === 0 ||
    (step === 1 ? !!current?.availability?.comparison : canAct);
  const nextStep = ((activeStep + 1) % steps.length) as GuideStep;
  return <div className="exploration-guide">
    {introduction && <div className="guide-intro">
      <span>Empieza aquí · elige un lugar</span><button type="button" onClick={onDismiss} aria-label="Cerrar indicación inicial">×</button>
    </div>}
    <nav aria-label="Explorar el terreno">
      {steps.map((label, index) => <button key={label} type="button" aria-current={index === activeStep ? "step" : undefined}
        disabled={!available(index)} onClick={() => onStep(index as GuideStep)} data-guide-step={index}>
        <span>{index + 1}</span>{label}
      </button>)}
    </nav>
    <button type="button" className="guide-next" disabled={!available(nextStep)} onClick={() => onStep(nextStep)}>
      {next[activeStep]} <span aria-hidden="true">→</span>
    </button>
  </div>;
}
