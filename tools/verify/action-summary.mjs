import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = "http://localhost:5173";
const data = await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r => r.json());
const priority = data.alerts.filter(zone => zone.recipe && zone.risk_id !== "causa_por_verificar")
  .sort((a, b) => b.index - a.index || a.alert_id.localeCompare(b.alert_id))[0];
const erosion = data.alerts.filter(zone => zone.risk_id === "erosion_huaico").length;
const out = "deploy/verificacion-p1";
await mkdir(out, { recursive: true });
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
try {
  for (const [width, height] of [[1366, 768], [375, 812]]) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setViewport({ width, height });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
    await page.goto(base, { waitUntil: "domcontentloaded" });
    await page.locator(".gaia-cta").click();
    await page.waitForSelector('.action-summary-row[data-phase="voice"]:not(:disabled)', { timeout: 60000 });
    const risk = await page.$eval('[data-phase="risk"]', el => el.textContent);
    assert(risk.includes(String(data.summary.medium)) && risk.includes(String(erosion)), risk);
    const layout = await page.evaluate(() => {
      const rect = selector => { const r = document.querySelector(selector).getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }; };
      const panel = rect(".map-context");
      const rows = [...document.querySelectorAll(".action-summary-row")].map(el => el.getBoundingClientRect());
      return { panel, rail: rect(".rail"), rows: rows.map(row => ({ top: row.top, bottom: row.bottom })), rowsVisible: rows.every(row => row.top >= panel.top && row.bottom <= panel.bottom), overflow: document.documentElement.scrollWidth > innerWidth };
    });
    await page.screenshot({ path: `${out}/entrada-${width}.png` });
    assert(layout.rowsVisible, JSON.stringify(layout));
    assert(!layout.overflow, "Horizontal overflow");
    assert(layout.panel.bottom <= layout.rail.top, "Context overlaps navigation");
    const obscured = await page.$eval('[data-phase="voice"]', el => {
      const r = el.getBoundingClientRect();
      return !el.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
    });
    assert(!obscured, "Voice entry point is covered by another control");
    for (const phase of ["risk", "climate", "action"]) {
      await page.locator(`[data-phase="${phase}"]`).click();
      await page.waitForSelector(phase === "climate" ? ".climate-arcs" : ".action-panel");
      if (phase === "climate") {
        await page.waitForFunction(() => document.querySelector(".climate-arcs .status-message")?.textContent.includes("2026-")
          || document.querySelector(".climate-arcs .status-message")?.textContent.includes("publicado"));
      }
      await page.locator(".inspector-heading .icon-button").click();
    }
    await page.locator('[data-phase="voice"]').click();
    await page.waitForFunction(() => document.activeElement?.classList.contains("last-mile-section"), { timeout: 60000 });
    const detail = await page.$eval(".alert-detail", el => el.textContent);
    assert(detail.includes("Boletín radial"));
    const selected = await page.$eval(".alert-detail", el => el.textContent);
    assert(selected.includes("Verificar en campo"));
    assert(await page.$$eval('.alert-detail a[href]', (links, id) => links.some(link => link.href.includes(encodeURIComponent(id))), priority.alert_id));
    if (width < 721) assert(await page.$eval(".event-timeline", el => getComputedStyle(el).display === "none"));
    await page.screenshot({ path: `${out}/voz-${width}.png` });
    console.log(JSON.stringify({ width, height, summary: data.summary, erosion, priority: priority.alert_id, layout, errors }));
    assert.deepEqual(errors, []);
    await page.close();
  }
} finally { await browser.close(); }
