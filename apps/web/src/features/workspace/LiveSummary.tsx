import type { AlertFeature, AlertKind } from "../../lib/api";
import { CountUp } from "./CountUp";

export function LiveSummary({ alerts, onKind }: { alerts: AlertFeature[]; onKind: (kind: AlertKind) => void }) {
  const items = [
    { kind: "quake" as const, label: "Sismos USGS", count: alerts.filter(item => item.properties.kind === "quake").length },
    { kind: "fire" as const, label: "Focos FIRMS", count: alerts.filter(item => item.properties.kind === "fire").length },
    { kind: "surface_change" as const, label: "Cambios NISAR", count: alerts.filter(item => item.properties.source_kind === "primary").length },
  ];
  return <div className="live-totals" aria-label="Observaciones disponibles">
    {items.map(item => <button key={item.kind} type="button" data-kind={item.kind} onClick={() => onKind(item.kind)}>
      <strong><CountUp value={item.count} /></strong><span>{item.label}</span>
    </button>)}
  </div>;
}
