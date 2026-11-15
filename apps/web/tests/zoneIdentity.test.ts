import { readFileSync, existsSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { AlertFeature, RemediationData } from "../src/lib/api";
import { groupZones, leadingFactors, nearestPlace, ZoneIdentity } from "../src/features/workspace/ZoneIdentity";

const path = new URL("../../../data/04_published/remediation/ayacucho-huanta.json", import.meta.url);
describe.skipIf(!existsSync(path))("F2 with real published zones", () => {
  const data: RemediationData = existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : null;
  const geo = existsSync(path) ? JSON.parse(readFileSync(new URL(`../../../data/03_processed/ayacucho-huanta/gcov/${data.period}/alerts_hvhv.geojson`, import.meta.url), "utf8")) : null;
  const features: AlertFeature[] = data?.alerts.map(rem => {
    const original = geo.features.find((f: AlertFeature) => f.properties.id === rem.alert_id);
    return { ...original, properties: { ...original.properties, remediation: rem } };
  }) ?? [];
  it("keeps every evaluated zone once and orders each cause by index", () => {
    const groups = groupZones(features);
    expect(groups.flatMap(group => group.items)).toHaveLength(data.alerts.length);
    for (const group of groups) {
      expect(group.items.every(feature => feature.properties.remediation!.risk_id === group.id)).toBe(true);
      const scores = group.items.map(feature => feature.properties.remediation!.index);
      expect(scores).toEqual([...scores].sort((a, b) => b - a));
    }
  });
  it("shows measured factors, units and area without recipe or budget on a card", () => {
    for (const feature of features.slice(0, 20)) {
      const html = renderToStaticMarkup(createElement(ZoneIdentity, { feature, compact: true }));
      expect(html).toContain("ha");
      expect(html).not.toContain("Receta:");
      expect(html).not.toContain("Presupuesto:");
      expect(leadingFactors(feature.properties.remediation!)).toHaveLength(Math.min(3,
        feature.properties.remediation!.summary_factor_ids!.length));
    }
  });
  it("does not infer a nearest settlement or distance without the published exposure", () => {
    expect(nearestPlace(features[0])).toBe("Poblado cercano sin publicar");
  });
});
