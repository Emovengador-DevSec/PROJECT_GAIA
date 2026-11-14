import { useState } from "react";
import { api, type CitizenReport, type ReportKind } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";

export const reportLabels: Record<ReportKind, string> = {
  fire: "Humo o fuego", landslide: "Grieta o deslizamiento",
  dry_water: "Fuente de agua seca", crop_damage: "Cosecha dañada",
};

export function CitizenReports({ reports, error, active, onLayer, onPick, picking, point, onLocate }: {
  reports?: CitizenReport[];
  error: boolean;
  active: boolean;
  onLayer: () => void;
  onPick: (value: boolean) => void;
  picking: boolean;
  point?: [number, number];
  onLocate: (report: CitizenReport) => void;
}) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<ReportKind>("fire");
  const [observed, setObserved] = useState("");
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState("");
  return <section className="community-block citizen-reports">
    <h4>Reportes ciudadanos · sin verificar</h4>
    <p className="muted">Se publican tras revisión. La ubicación compartida se redondea a una cuadrícula de unos 500 m. El alojamiento puede perder reportes al reiniciar si el disco es temporal.</p>
    {(error || !reports) ? <p role="status">{error ? "No se pudo cargar la capa de reportes." : "Consultando reportes…"}</p>
      : reports.length ? <ul className="community-report-list">{reports.map(report => <li key={report.id}>
        <button type="button" className="text-button" onClick={() => onLocate(report)}>{reportLabels[report.kind]} · {formatDate(report.observed_at)}</button>
        {report.firms_match && <p className="muted">Coincide en lugar y tiempo con un foco FIRMS.</p>}
        {report.nisar_overlap && <p className="muted">Se ubica en una zona HV del par histórico de Ayacucho.</p>}
      </li>)}</ul> : <p>Aún no hay reportes.</p>}
    <div className="detail-actions">
      <button type="button" className="secondary-action" aria-pressed={active} onClick={onLayer}>{active ? "Ocultar capa" : "Mostrar capa"}</button>
      <button type="button" className="secondary-action" aria-expanded={open} onClick={() => {
        if (open) onPick(false);
        setOpen(!open);
      }}>{open ? "Cerrar formulario" : "Enviar un reporte"}</button>
    </div>
    {open && <form className="community-controls report-form" onSubmit={async event => {
      event.preventDefault();
      if (!point || !observed || sending) return;
      setStatus("");
      setSending(true);
      try {
        await api.submitReport({ kind, lon: point[0], lat: point[1], observed_at: new Date(observed).toISOString(), note });
        setStatus("Reporte recibido. Queda pendiente de revisión.");
        setOpen(false);
        setNote("");
        setObserved("");
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "No se pudo enviar el reporte.");
      } finally {
        setSending(false);
      }
    }}>
      <label>Observación<select value={kind} onChange={event => setKind(event.target.value as ReportKind)}>
        {Object.entries(reportLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <label>Fecha y hora local<input type="datetime-local" required value={observed} onChange={event => setObserved(event.target.value)} /></label>
      <button type="button" className="secondary-action community-search" aria-pressed={picking} onClick={() => onPick(!picking)}>
        {picking ? "Cancela la selección en el mapa" : point ? "Cambiar punto en el mapa" : "Elegir punto en el mapa"}
      </button>
      <p className="community-search muted" role="status">{picking ? "Toca el terreno en la zona de Ayacucho." :
        point ? `Punto seleccionado · ${point.map(value => value.toFixed(3)).join(", ")}` : "Selecciona una ubicación en Ayacucho."}</p>
      <label className="community-search">Nota privada para revisión. Omite nombres y direcciones.<textarea maxLength={280} rows={3} value={note}
        onChange={event => setNote(event.target.value)} /></label>
      <button type="submit" className="primary-action community-search" disabled={!point || !observed || sending}>
        {sending ? "Enviando…" : "Enviar a revisión"}
      </button>
    </form>}
    {status && <p role="status">{status}</p>}
  </section>;
}
