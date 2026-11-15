import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RecoveryScenario } from "../src/features/workspace/RecoveryScenario";
import type { RemediationData } from "../src/lib/api";
const path = new URL("../../../data/04_published/remediation/ayacucho-huanta.json", import.meta.url);
describe.skipIf(!existsSync(path))("F4 actual published assumptions", () => {
  it("keeps unverified scenarios closed and never renders an absolute baseline", () => {
    const data: RemediationData = JSON.parse(readFileSync(path, "utf8"));
    for (const zone of data.alerts.filter(zone => zone.recovery_scenario)) {
      const html = renderToStaticMarkup(createElement(RecoveryScenario, { scenario: zone.recovery_scenario! }));
      expect(html).toContain("<details");
      expect(html).not.toMatch(/<details[^>]*\bopen/);
      expect(html).toContain("Supuestos del escenario");
      expect(html).not.toContain("Año 0");
      expect(html).not.toContain("NDVI esperado");
      if (zone.recovery_scenario!.citation_status !== "verificado") expect(html).not.toContain("de NDVI relativo (supuesto)");
      expect(html).toContain("no una estimación calibrada");
    }
  });
});
