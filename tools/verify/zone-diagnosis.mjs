import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = "http://localhost:5173";
const data = await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r => r.json());
const causes = ["incendio_sequia", "erosion_huaico", "estres_hidrico_agricola"];
const zones = causes.map(cause => data.alerts.find(zone => zone.risk_id === cause && zone.alert_id.endsWith("_014"))
  ?? data.alerts.find(zone => zone.risk_id === cause));
assert(zones.every(Boolean), "Three actual causes must exist in the published dataset");
assert.equal(new Set(zones.map(zone => zone.summary)).size, 3);
const identityMode = process.argv.includes("--identity");
const out = identityMode ? "deploy/verificacion-f2" : "deploy/verificacion-f1";
await mkdir(out, { recursive: true });
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
try {
  for (const zone of zones) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setViewport({ width: 1366, height: 768 });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
    await page.goto(`${base}/?alert=${encodeURIComponent(zone.alert_id)}`, { waitUntil: "domcontentloaded" });
    await page.locator(".gaia-cta").click();
    await page.waitForSelector(".zone-diagnosis-summary", { timeout: 60000 });
    assert.equal(await page.$eval(".zone-diagnosis-summary", el => el.textContent), zone.summary);
    assert.equal(await page.$eval(".zone-diagnosis-cause", el => el.textContent), zone.cause_explanation);
    const text = await page.$eval(".remediation-section", el => el.textContent);
    assert(!text.includes("Condición física:"));
    assert(!text.includes(zone.recipe?.condition?.trim() ?? "NOT_A_CONDITION"));
    if (!zone.factors.heat_count) {
      assert(!zone.summary.toLowerCase().includes("focos"));
      assert(!zone.cause_explanation.toLowerCase().includes("focos"));
    }
    if (!identityMode) await page.$eval(".remediation-section", el => el.scrollIntoView({ block: "start", behavior: "instant" }));
    await page.screenshot({ path: `${out}/${zone.risk_id}-1366.png` });
    const visible = await page.$eval(identityMode ? ".alert-detail > .zone-identity" : ".zone-diagnosis-cause", el => {
      const panel = document.querySelector(".inspector-content").getBoundingClientRect();
      const r = el.getBoundingClientRect();
      return r.top >= panel.top && r.bottom <= panel.bottom;
    });
    assert(visible, "The F1 diagnosis must be visible in the screenshot");
    console.log(JSON.stringify({ cause: zone.risk_id, id: zone.alert_id, summary: zone.summary,
      explanation: zone.cause_explanation, visible, errors }));
    assert.deepEqual(errors, []);
    await page.close();
  }
} finally { await browser.close(); }
