import { useMemo, useState } from "react";
import type { AlertFeature, AlertKind } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";
import { CountUp } from "./CountUp";

export const kindLabels: Record<AlertKind, string> = {
  quake: "Sismos", fire: "Focos de calor", surface_change: "Cambios de superficie", deformation: "Deformación",
};

export function AlertSymbol({ kind }: { kind: AlertKind }) {
  return <svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    {kind === "quake" ? <><circle cx="12" cy="12" r="3" /><circle cx="12" cy="12" r="8" /></>
      : kind === "fire" ? <path d="M13 2c4 7-2 8 2 12l3-4c6 9 1 12-6 12S3 15 7 10c0 4 3 4 3 4-2-7 2-9 3-12Z" />
      : kind === "deformation" ? <path d="m12 2 10 10-10 10L2 12Z" />
      : <path d="m12 3 8 5v8l-8 5-8-5V8Z" />}
  </svg>;
}

export function observationMetric(feature: AlertFeature) {
  const m = feature.properties.metrics;
  if (m.magnitude != null) return { value: m.magnitude, unit: m.magnitude_type ?? "M", label: "Magnitud", decimals: 1 };
  if (m.count != null) return { value: m.count, unit: "focos", label: "Detecciones en la celda", decimals: 0 };
  if (m.area_ha != null) return { value: m.area_ha, unit: "ha", label: "Área con cambio", decimals: 1 };
  if (m.frp_mw != null) return { value: m.frp_mw, unit: "MW", label: "Potencia radiativa", decimals: 1 };
  return { value: null, unit: "", label: "Cifra sin publicar", decimals: 0 };
}

function AlertRow({ feature, onSelect }: { feature: AlertFeature; onSelect: (item: AlertFeature) => void }) {
  const a = feature.properties;
  return <button type="button" className="alert-row" data-kind={a.kind} onClick={() => onSelect(feature)}>
    <span className="alert-symbol"><AlertSymbol kind={a.kind} /></span>
    <span className="alert-row-content"><strong>{a.title}</strong><span>{a.place}</span>
      <small>{a.source} · {a.source_kind === "primary" ? "NISAR" : "complementario"}</small>
      <time dateTime={a.date}>{formatDate(a.date)}</time></span>
    <span className="alert-level" data-level={a.level}>{a.level === "alto" ? "Alta" : a.level === "medio" ? "Media" : "Baja"}</span>
  </button>;
}

function AlertGroup({ name, items, onSelect }: { name: string; items: AlertFeature[]; onSelect: (item: AlertFeature) => void }) {
  const [limit, setLimit] = useState(20);
  return <details className="alert-group">
    <summary><span>{name}<small>{items[0].properties.place}</small></span><strong>{items.length}</strong></summary>
    <div className="alert-list">{items.slice(0, limit).map(item => <AlertRow key={item.properties.id} feature={item} onSelect={onSelect} />)}</div>
    {items.length > limit && <button type="button" className="text-button" onClick={() => setLimit(value => value + 20)}>Ver 20 observaciones más</button>}
  </details>;
}

export function AlertFeed({ alerts, onSelect }: { alerts: AlertFeature[]; onSelect: (item: AlertFeature) => void }) {
  const { featured, groups } = useMemo(() => {
    const kinds: AlertKind[] = ["surface_change", "deformation", "quake", "fire"];
    const featured = kinds.map(kind => {
      const candidates = alerts.filter(item => item.properties.kind === kind);
      if (kind === "surface_change") {
        const comparable = candidates.filter(item => item.properties.comparison_summary);
        if (comparable.length) return comparable.sort((a, b) =>
          (b.properties.comparison_summary?.loss_area_ha ?? 0) - (a.properties.comparison_summary?.loss_area_ha ?? 0) ||
          (b.properties.metrics.area_ha ?? 0) - (a.properties.metrics.area_ha ?? 0))[0];
      }
      return candidates.sort((a, b) => (observationMetric(b).value ?? -Infinity) - (observationMetric(a).value ?? -Infinity))[0];
    }).filter((item): item is AlertFeature => !!item).slice(0, 3);
    const recent = alerts.find(item => !featured.includes(item) &&
      !featured.some(chosen => chosen.properties.place === item.properties.place));
    if (recent && featured.length < 3) featured.push(recent);
    const groups = new Map<string, AlertFeature[]>();
    for (const feature of alerts) {
      const key = `${feature.properties.kind}|${feature.properties.place}`;
      groups.set(key, [...(groups.get(key) ?? []), feature]);
    }
    return { featured, groups: [...groups.entries()] };
  }, [alerts]);
  if (!alerts.length) return null;
  return <>
    <section className="featured-observations" aria-labelledby="featured-heading">
      <h3 id="featured-heading">Lo más importante ahora</h3>
      {featured.map(feature => {
        const a = feature.properties;
        const summary = a.comparison_summary;
        const metric = summary ? { value: summary.loss_area_ha, unit: "ha", decimals: 2 } : observationMetric(feature);
        return <button key={a.id} type="button" className="featured-observation" data-kind={a.kind} onClick={() => onSelect(feature)}>
          <span className="featured-source"><span className="alert-symbol"><AlertSymbol kind={a.kind} /></span>{a.source}</span>
          <span className="featured-metric">{metric.value == null ? "—" : <CountUp value={metric.value} decimals={metric.decimals} />}<small>{metric.unit}</small></span>
          {summary && <><span>Caída de señal HV</span><span>{summary.alerts} zonas delimitadas · {summary.mapped_loss_area_ha.toLocaleString("es-PE")} ha</span></>}
          <strong>{a.place}</strong><time dateTime={a.date}>{formatDate(a.date)}</time>
        </button>;
      })}
    </section>
    <section className="observation-groups" aria-label="Observaciones por tipo y lugar">
      <p className="result-count">{alerts.length} observaciones con fuente y fecha</p>
      {groups.map(([key, items]) => <AlertGroup key={key} name={kindLabels[items[0].properties.kind]} items={items} onSelect={onSelect} />)}
    </section>
  </>;
}
