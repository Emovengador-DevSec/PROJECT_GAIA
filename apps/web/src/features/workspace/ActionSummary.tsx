import { useEffect, useState } from "react";
import { api, type AOI, type Climate, type RemediationBulletinResponse, type RemediationData } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { climateSummary, priorityZone, riskSummary } from "./actionSummaryModel";
import { SectionIcon } from "./SectionIcon";
import type { TabId } from "../../config/tabs";
import "./action-summary.css";

export type ActionDestination = "risk" | "climate" | "action" | "voice";
type SummaryState = { aoi: string; loading: boolean; data?: RemediationData | null;
  climate?: Climate | null; bulletin?: RemediationBulletinResponse };

export function ActionSummary({ aoi, onOpen }: {
  aoi?: AOI;
  onOpen: (destination: ActionDestination, aoi: AOI, zoneId?: string) => void;
}) {
  const [state, setState] = useState<SummaryState>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!aoi) return;
    const request = new AbortController();
    setState({ aoi: aoi.id, loading: true });
    Promise.allSettled([api.remediation(aoi.id, request.signal), api.climate(aoi.id, request.signal)])
      .then(async ([remediation, climate]) => {
        if (request.signal.aborted) return;
        const data = remediation.status === "fulfilled" ? remediation.value : undefined;
        const next: SummaryState = { aoi: aoi.id, loading: false, data,
          climate: climate.status === "fulfilled" ? climate.value : undefined };
        setState(next);
        const priority = priorityZone(data);
        if (!priority) return;
        try {
          const bulletin = await api.remediationBulletin(aoi.id, priority.alert_id, request.signal);
          if (!request.signal.aborted) setState({ ...next, bulletin });
        } catch { /* The row remains an explicit unavailable state. */ }
      });
    return () => request.abort();
  }, [aoi?.id, attempt]);
  const current = state?.aoi === aoi?.id ? state : undefined;
  const priority = priorityZone(current?.data);
  const rows: { id: ActionDestination; label: string; icon: TabId; text: string; disabled?: boolean }[] = [
    { id: "risk", label: "Riesgo", icon: "quality", text: riskSummary(current?.data) },
    { id: "climate", label: "Clima", icon: "series", text: climateSummary(current?.climate) },
    { id: "action", label: "Acción", icon: "action", text: priority
      ? "Receta natural · consulta costos y fuentes" : "Recetas sin confirmar · abre Acción" },
    { id: "voice", label: "Voz", icon: "resources", text: current?.bulletin?.bulletin.script_es
      ? "Guion de radio en español listo" : "Boletín no disponible · reintenta", disabled: !current?.bulletin?.bulletin.script_es },
  ];
  return <section className="action-summary" aria-labelledby="action-summary-title" aria-busy={!!current?.loading}>
    <h2 id="action-summary-title">Del radar a la acción</h2>
    <p className="action-summary-place" title={aoi?.name}>{aoi?.name.split(" · ")[0] ?? "Elige un territorio en Lugares"}</p>
    {rows.map(row => <button type="button" key={row.id} className="action-summary-row" data-phase={row.id}
      disabled={!aoi || !current || current.loading || row.disabled}
      onClick={() => aoi && onOpen(row.id, aoi, row.id === "voice" ? priority?.alert_id : undefined)}>
      <SectionIcon id={row.icon} /><span><strong>{row.label}</strong><span>{current?.loading ? "Consultando datos publicados…" : row.text}</span></span>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
    </button>)}
    <details className="action-summary-quality"><summary>NISAR provisional + complementarios · fuentes</summary>
      {current?.data ? <p>NISAR · provisional · {current.data.period.replace("__", " → ")}.
        {" "}Análisis con datos complementarios · {formatDate(current.data.generated_at)}.</p>
        : <p>Publica el análisis: <code>sarlab remediation --aoi {aoi?.id ?? "<zona>"}</code>.</p>}
      {current?.climate?.forecast ? <p>Clima complementario · {current.climate.forecast.source} / NASA POWER.
        {" "}Pronóstico consultado: {formatDate(current.climate.forecast.fetched_at)}.</p>
        : <p>Publica el clima: <code>sarlab climate --aoi {aoi?.id ?? "<zona>"}</code>.</p>}
      <p>{current?.data?.disclaimer ?? "Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. Verificar en campo. NISAR revisita cada ~12 días; no es tiempo real."}</p>
      <button type="button" className="text-button" onClick={() => setAttempt(value => value + 1)}>Actualizar resumen</button>
    </details>
  </section>;
}
