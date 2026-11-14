import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = "http://127.0.0.1:4173";
const output = path.resolve("art/verificacion/G9");
await mkdir(output, { recursive: true });
let apiRunning = false;
try {
  await fetch("http://127.0.0.1:8000/api/health", { signal: AbortSignal.timeout(1500) });
  apiRunning = true;
} catch { /* La comprobación requiere el servidor de la API apagado. */ }
assert.equal(apiRunning, false, "Apaga la API antes de verificar la publicación estática");
const manifest = await (await fetch(base + "/snapshot/manifest.json")).json();
const get = async route => {
  const url = new URL(route, "https://snapshot.invalid");
  url.searchParams.sort();
  const file = manifest.responses[url.pathname + url.search];
  assert(file, route);
  const response = await fetch(base + "/snapshot/" + file);
  assert(response.ok, file);
  return response.json();
};
const [layers, zones, feed] = await Promise.all([
  get("/layers?active_only=true"), get("/aois"), get("/alerts?include_live=true&active_only=true"),
]);
assert.equal(manifest.tiles.maximum_level, 13);
assert.equal(layers.length, 2);
const hv = layers.find(layer => layer.provenance.layer === "HVHV");
assert.equal(hv.quality.valid_area_pct, 99.91);
const report = { api_running: apiRunning, generated_at: manifest.generated_at,
  observations: feed.features.length, source_granules: hv.provenance.granules, sizes: [] };
const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
try {
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    const page = await browser.newPage();
    page.setDefaultTimeout(20_000);
    const errors = [], failed = [], apiRequests = [], tileStages = new Set();
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => {
      const url = new URL(request.url());
      if (url.pathname.startsWith("/api/")) apiRequests.push(url.pathname);
    });
    page.on("response", response => {
      const url = new URL(response.url());
      if (response.status() >= 400) failed.push({ path: url.pathname, status: response.status() });
      if (response.ok() && url.pathname.startsWith(`/snapshot/tiles/${hv.id}/`)) {
        tileStages.add(url.pathname.split("/")[4]);
      }
    });
    try {
      await page.setViewport({ width, height });
      await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
      await page.goto(base, { waitUntil: "domcontentloaded" });
      await page.locator(".gaia-cta").click();
      await page.waitForFunction(() => document.querySelector(".snapshot-status")?.textContent.includes("foto estática"));
      if (width < 720) await page.locator(".panel-reopen").click();
      await page.waitForSelector('.featured-observation[data-kind="surface_change"]');
      const label = await page.$eval(".snapshot-status", element => element.textContent);
      assert.equal(await page.$eval("#event-date", element => Number(element.max)), Date.parse(manifest.generated_at));
      await page.locator('.featured-observation[data-kind="surface_change"]').click();
      await page.waitForSelector(".exposure-section");
      assert((await page.$eval(".exposure-section", element => element.textContent)).includes("WorldCover"));
      await page.locator(".rail button:nth-child(2)").click();
      await page.locator(".case:first-child").click();
      await page.waitForFunction(() => !document.querySelector(".loading-state"));
      await page.locator(".rail button:nth-child(3)").click();
      await page.waitForSelector("#comparison-split");
      for (let attempt = 0; tileStages.size < 2 && attempt < 100; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      assert(tileStages.has("before") && tileStages.has("after"), "Faltan teselas estáticas de alguna fecha");
      await page.$eval("#comparison-split", element => element.focus());
      await page.keyboard.press("ArrowRight");
      assert.equal(await page.$eval("#comparison-split", element => Number(element.value)), 51);
      await new Promise(resolve => setTimeout(resolve, 1500));
      await page.screenshot({ path: path.join(output, `radar-static-${width}.jpg`), type: "jpeg", quality: 88 });
      console.log(JSON.stringify({ width, stage: "cortina real verificada" }));
      await page.locator(".rail button:nth-child(5)").click();
      await page.waitForSelector(".snapshot-quality");
      assert.equal(await page.$eval(".snapshot-quality", element => element.textContent), label);
      assert((await page.$eval(".quality-facts", element => element.textContent)).includes("99.9"));
      for (let index = 0; index < zones.length; index++) {
        await page.locator(".rail button:nth-child(2)").click();
        await page.locator(`.case:nth-child(${index + 1})`).click();
        await page.waitForFunction(() => !document.querySelector(".loading-state"));
        await page.locator(".rail button:nth-child(1)").click();
        await page.locator(".rail button:nth-child(4)").click();
        await page.locator(".rail button:nth-child(8)").click();
        console.log(JSON.stringify({ width, case: zones[index].id }));
      }
      await page.locator(".rail button:nth-child(2)").click();
      await page.locator(".case:first-child").click();
      await page.waitForFunction(() => !document.querySelector(".loading-state"));
      await page.locator(".rail button:nth-child(1)").click();
      const next = page.locator(".story-actions button:last-child");
      for (let index = 0; index < 3; index++) await next.click();
      await page.waitForSelector("#comparison-split");
      await page.locator(".rail button:nth-child(5)").click();
      await page.evaluate(() => {
        const detail = [...document.querySelectorAll("details")].find(element =>
          element.querySelector("summary")?.textContent.includes("Contraste cuantitativo"));
        if (detail) detail.open = true;
      });
      assert((await page.$eval(".inspector", element => element.textContent)).includes("2.25"));
      const layout = await page.$eval(".snapshot-status", element => {
        const rect = element.getBoundingClientRect();
        return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom,
          scroll: element.scrollWidth, width: element.clientWidth };
      });
      assert(layout.left >= 0 && layout.right <= width && layout.top >= 0 && layout.bottom <= height);
      assert(layout.scroll <= layout.width);
      assert.equal(await page.$(".cesium-widget-errorPanel"), null);
      assert.deepEqual(apiRequests, []);
      assert.deepEqual(errors, []);
      assert.deepEqual(failed, []);
      report.sizes.push({ width, height, label, layout, errors, failed, apiRequests, tiles: [...tileStages] });
      console.log(JSON.stringify({ width, height, static: true, apiRequests, errors, failed, tileStages: [...tileStages] }));
    } catch (error) {
      await page.screenshot({ path: path.join(output, `error-${width}.jpg`), type: "jpeg" });
      console.log(JSON.stringify({ width, errors, failed, apiRequests,
        screen: await page.$eval("body", element => element.innerText.slice(0, 1400)) }));
      throw error;
    } finally {
      await page.close();
    }
  }
} finally {
  await browser.close();
  await writeFile(path.join(output, "static-report.json"), JSON.stringify(report, null, 2));
}
