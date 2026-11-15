import { readFileSync, existsSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import type { Climate, RemediationData } from "../src/lib/api";
import { ActionSummary } from "../src/features/workspace/ActionSummary";
import { climateSummary, priorityZone, riskSummary } from "../src/features/workspace/actionSummaryModel";
import { formatNumber } from "../src/lib/formatNumber";

// Use actual published observations; synthetic data stays in pipeline/API tests.
const remediationPath = new URL("../../../data/04_published/remediation/ayacucho-huanta.json", import.meta.url);
const climatePath = new URL("../../../data/04_published/climate/ayacucho-huanta.json", import.meta.url);
describe("ActionSummary unavailable states", () => {
  it("never turns missing inputs into zero risk or a clear forecast", () => {
    expect(priorityZone(null)).toBeUndefined();
    expect(riskSummary(null)).toContain("sin publicar");
    expect(climateSummary(null)).toContain("sin publicar");
  });
  it("keeps all four entry points without claiming a ready bulletin", () => {
    const html = renderToStaticMarkup(createElement(ActionSummary, { onOpen: () => undefined }));
    for (const phase of ["risk", "climate", "action", "voice"]) expect(html).toContain(`data-phase="${phase}"`);
    expect(html).toContain("Elige un territorio");
    expect(html).not.toContain("radio en español listo");
  });
});
describe.skipIf(!existsSync(remediationPath) || !existsSync(climatePath))("actual published P1 evidence", () => {
  const data: RemediationData = existsSync(remediationPath) ? JSON.parse(readFileSync(remediationPath, "utf8")) : null;
  const climate: Climate = existsSync(climatePath) ? JSON.parse(readFileSync(climatePath, "utf8")) : null;
  it("matches published levels and erosion counts", () => {
    const summary = riskSummary(data);
    expect(summary).toContain(`${formatNumber(data.summary.medium, 0)} en nivel medio`);
    expect(summary).toContain(`${formatNumber(data.alerts.filter(zone => zone.risk_id === "erosion_huaico").length, 0)} con riesgo de erosión`);
    expect(data.summary.total_alerts).toBe(data.alerts.length);
  });
  it("chooses the largest index with a recipe, without mutating API order", () => {
    const ids = data.alerts.map(zone => zone.alert_id);
    const priority = priorityZone(data)!;
    expect(priority.recipe).toBeTruthy();
    expect(priority.risk_id).not.toBe("causa_por_verificar");
    expect(data.alerts.filter(zone => zone.recipe).every(zone => zone.index <= priority.index)).toBe(true);
    expect(data.alerts.map(zone => zone.alert_id)).toEqual(ids);
  });
  it("reports the active published climate notice with its date", () => {
    const today = climate.forecast!.daily.time[0];
    const text = climateSummary(climate, today);
    expect(climate.anomalies!.some(anomaly => text.includes(anomaly.title) && text.includes(anomaly.date.slice(0, 10)))).toBe(true);
  });
  it("does not call an expired forecast a week without anomalies", () => {
    const last = new Date(`${climate.forecast!.daily.time.at(-1)}T00:00:00Z`);
    last.setUTCDate(last.getUTCDate() + 1);
    expect(climateSummary(climate, last.toISOString().slice(0, 10))).toContain("desactualizado");
  });
});
