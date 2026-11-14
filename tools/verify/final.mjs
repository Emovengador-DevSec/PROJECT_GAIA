import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import path from "node:path";

const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = process.env.GAIA_VERIFY_URL ?? "http://127.0.0.1:8093";
const record = process.argv.includes("--record");
const output = path.resolve(process.env.GAIA_VERIFY_OUTPUT ?? "art/verificacion/final");
await mkdir(output, { recursive: true });
const api = async route => {
  const response = await fetch(base + "/api" + route);
  assert(response.ok, route);
  return response.json();
};
const [health, layers, series, observations] = await Promise.all([
  api("/health"), api("/layers?aoi=ayacucho-huanta&active_only=true"),
  api("/timeseries?aoi=ayacucho-huanta"), api("/alerts?include_live=true&active_only=true"),
]);
assert.equal(layers.length, 2);
assert(layers.every(layer => layer.quality.valid_area_pct >= 80
  && layer.dates.a === "2026-06-24" && layer.dates.b === "2026-10-10"));
assert.equal(series.samples.length, 2);
const hv = layers.find(layer => layer.provenance.layer === "HVHV");
const manifest = JSON.parse(await readFile("data/03_processed/ayacucho-huanta/gcov/2026-06-24__2026-10-10/manifest_hvhv.json", "utf8"));
assert.deepEqual(hv.change_summary, manifest.change_summary);
const validation = await api("/validation/" + hv.id);
assert.equal(validation.nisar_confirmed_pct, 2.25);
const primary = observations.features.filter(item => item.properties.source_kind === "primary");
const hvZones = primary.filter(item => item.properties.polarization === "HVHV");
assert.equal(hvZones.length, manifest.change_summary.alerts);
assert(hvZones.every(item => item.properties.comparison_summary?.alerts === manifest.change_summary.alerts));
assert(primary.every(item => item.properties.exposure?.sources?.landcover));
assert(primary.every(item => item.properties.date === "2026-10-10T10:41:47+00:00"));
const results = { offline: health.offline, coverage: hv.quality.valid_area_pct,
  summary: hv.change_summary, agreement: validation.nisar_confirmed_pct, sizes: [] };
const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
try {
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    const page = await browser.newPage();
    const errors = [];
    const radarTiles = new Set();
    page.on("pageerror", error => errors.push(error.message));
    page.on("response", response => {
      const url = new URL(response.url());
      if (response.ok() && url.pathname.startsWith(`/api/tiles/${hv.id}/`)
          && url.searchParams.get("palette") === "rgb") {
        radarTiles.add(url.pathname.split("/")[4]);
      }
    });
    await page.setViewport({ width, height });
    const recording = record && width === 1440;
    const pause = ms => new Promise(resolve => setTimeout(resolve, recording ? ms : Math.min(ms, 700)));
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: recording ? "no-preference" : "reduce" }]);
    await page.goto(base, { waitUntil: "domcontentloaded" });
    const recorder = recording ? await page.screencast({
      path: path.join(output, "gaia-recorrido.mp4"), format: "mp4", fps: 20, quality: 23,
    }) : undefined;
    try {
      await pause(recording ? 8000 : 400);
      if (!recording) await page.screenshot({ path: path.join(output, `portada-${width}.jpg`), type: "jpeg", quality: 85 });
      await page.locator(".gaia-cta").click();
      if (width < 720) await page.locator(".panel-reopen").click();
      await page.waitForSelector('.featured-observation[data-kind="surface_change"]');
      await page.waitForFunction(() => !document.querySelector(".loading-state"));
      await pause(12000);
      const number = value => String(value).replace(".", ",");
      const card = '.featured-observation[data-kind="surface_change"]';
      const summary = '.live-totals button[data-kind="surface_change"]';
      await page.waitForFunction((selector, expected) => document.querySelector(selector)?.textContent.trim() === expected,
        {}, `${summary} strong`, number(manifest.change_summary.alerts));
      const text = await page.$eval(card, el => el.textContent);
      for (const value of [manifest.change_summary.loss_area_ha, manifest.change_summary.mapped_loss_area_ha, manifest.change_summary.alerts]) {
        assert(text.includes(number(value)));
      }
      assert(text.includes("10:41 UTC"));
      if (width < 720) await page.$eval(card, el => el.scrollIntoView({ block: "center" }));
      await page.screenshot({ path: path.join(output, `observaciones-${width}.jpg`), type: "jpeg", quality: 85 });
      assert.equal(await page.$eval(".workspace-light select", el => el.value), "day");
      await page.select(".workspace-light select", "real");
      await pause(1000);
      await page.select(".workspace-light select", "day");
      if (recording) {
        await pause(12000);
        await page.locator('[aria-label="Reproducir 30 días"]').click();
        await pause(15000);
        await page.locator('[aria-label="Pausar secuencia"]').click();
        await page.locator(".timeline-heading button").click();
      }
      await page.locator(".rail button:nth-child(2)").click();
      await page.locator(".case:first-child").click();
      await page.locator(".rail button:nth-child(3)").click();
      await page.waitForSelector("#comparison-split");
      await page.waitForFunction(() => document.querySelector(".date-comparison")?.textContent.includes("2026-06-24"));
      await pause(15000);
      const slider = await page.$("#comparison-split");
      await slider.focus();
      await page.keyboard.press("ArrowRight");
      await page.keyboard.press("ArrowLeft");
      await pause(10000);
      for (let attempt = 0; radarTiles.size < 2 && attempt < 100; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      assert(radarTiles.has("before") && radarTiles.has("after"), "Ambas fechas deben servir teselas reales");
      await new Promise(resolve => setTimeout(resolve, 3000));
      await page.screenshot({ path: path.join(output, `radar-${width}.jpg`), type: "jpeg", quality: 88 });
      await page.locator(".rail button:nth-child(5)").click();
      await page.waitForFunction(() => document.querySelector(".quality-facts")?.textContent.includes("99,91"));
      await page.evaluate(() => {
        for (const details of document.querySelectorAll("details")) {
          if (details.querySelector("summary")?.textContent.includes("Contraste cuantitativo")) details.open = true;
        }
        document.querySelector(".technical-details:last-of-type")?.scrollIntoView({ block: "center" });
      });
      await pause(15000);
      assert((await page.$eval(".inspector", el => el.textContent)).includes("2,25"));
      await page.screenshot({ path: path.join(output, `calidad-${width}.jpg`), type: "jpeg", quality: 88 });
      await page.locator(".rail button:nth-child(7)").click();
      await page.locator('.featured-observation[data-kind="surface_change"]').click();
      await page.waitForSelector(".exposure-section");
      await pause(7000);
      await page.$eval(".exposure-section", el => el.scrollIntoView({ block: "start" }));
      await pause(18000);
      const exposureText = await page.$eval(".exposure-section", el => el.textContent);
      assert(exposureText.includes("Pastizal") && exposureText.includes("WorldCover"));
      await page.screenshot({ path: path.join(output, `exposicion-${width}.jpg`), type: "jpeg", quality: 88 });
      const layout = await page.$eval(".inspector", el => {
        const rect = el.getBoundingClientRect();
        return { left: rect.left, right: rect.right, scroll: el.scrollWidth, width: el.clientWidth };
      });
      assert(layout.left >= 0 && layout.right <= width && layout.scroll <= layout.width, JSON.stringify(layout));
      if (recording) {
        await page.locator(".rail button:nth-child(1)").click();
        await pause(8000);
        await page.locator(".rail button:nth-child(8)").click();
        await pause(12000);
        await page.locator('[aria-label="Cerrar panel y explorar el mapa"]').click();
        await pause(10000);
      }
      assert.equal(await page.$(".cesium-widget-errorPanel"), null);
      assert.deepEqual(errors, []);
      results.sizes.push({ width, height, layout, errors });
      console.log(JSON.stringify({ width, coverage: hv.quality.valid_area_pct, errors, layout }));
    } catch (error) {
      await page.screenshot({ path: path.join(output, `error-${width}.jpg`), type: "jpeg" });
      console.log(JSON.stringify({ width, errors,
        screen: await page.$eval("body", el => el.innerText.slice(0, 1600)) }));
      throw error;
    } finally {
      if (recorder) await recorder.stop();
      await page.close();
    }
  }
} finally {
  await browser.close();
  await writeFile(path.join(output, "informe.json"), JSON.stringify(results, null, 2));
}
if (record) {
  const original = path.join(output, "gaia-recorrido.mp4");
  execFileSync("ffmpeg", ["-hide_banner", "-loglevel", "warning", "-y", "-i", original,
    "-vf", "setpts=0.75*PTS", "-r", "20", "-c:v", "libx264", "-preset", "fast", "-crf", "24",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", path.resolve("art/verificacion/gaia-alerta-demo.mp4")],
  { stdio: "inherit" });
  await unlink(original);
}
