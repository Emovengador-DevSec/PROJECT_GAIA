import type { Climate, RemediationAlert, RemediationData } from "../../lib/api";
import { formatNumber } from "../../lib/formatNumber";

export function priorityZone(data?: RemediationData | null): RemediationAlert | undefined {
  return data?.alerts.filter(zone => zone.recipe && zone.risk_id !== "causa_por_verificar" && Number.isFinite(zone.index))
    .sort((a, b) => b.index - a.index || a.alert_id.localeCompare(b.alert_id))[0];
}

export function riskSummary(data?: RemediationData | null) {
  if (!data) return "Análisis sin publicar · abre Acción";
  const erosion = data.alerts.filter(zone => zone.risk_id === "erosion_huaico").length;
  const { high, medium, low } = data.summary;
  const level = high ? `${formatNumber(high, 0)} en nivel alto` : medium
    ? `${formatNumber(medium, 0)} en nivel medio` : `${formatNumber(low, 0)} en nivel bajo`;
  return `${level} · ${formatNumber(erosion, 0)} con riesgo de erosión`;
}

export function climateSummary(climate?: Climate | null, today = new Date().toISOString().slice(0, 10)) {
  if (!climate?.forecast?.daily?.time.length) return "Pronóstico sin publicar · abre Clima";
  const dates = climate.forecast.daily.time;
  if (dates[0] > today || dates.at(-1)! < today || climate.forecast.status === "unavailable") {
    return "Pronóstico desactualizado · abre Clima";
  }
  if (!climate.anomalies) return "Anomalías sin evaluar · abre Clima";
  const levels = { alto: 3, medio: 2, bajo: 1 };
  const anomaly = climate.anomalies.filter(item => item.date.slice(0, 10) >= today)
    .sort((a, b) => levels[b.level] - levels[a.level] || a.date.localeCompare(b.date))[0];
  return anomaly ? `${anomaly.title} · ${anomaly.date.slice(0, 10)}` : "Sin anomalías en el pronóstico publicado";
}
