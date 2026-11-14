import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = process.env.GAIA_VERIFY_URL ?? "http://127.0.0.1:5173";
const output = path.resolve(process.env.GAIA_VERIFY_OUTPUT ?? "deploy/verificacion-agricultura");
await mkdir(output, { recursive: true });
const get = async url => {
  const response = await fetch(base + url);
  assert.equal(response.status, 200);
  return response.json();
};
const data = await get("/api/agriculture/ayacucho-huanta");
const index = await get("/api/community");
assert(Math.abs(Object.values(data.region).reduce((a, b) => a + b, 0) - index.region.cropland_ha) < .001);
assert(data.region.cropland_steep_ha > 0 && data.grid_m === 30);
const history = await get("/api/fire-history/ayacucho-huanta");
if (process.env.GAIA_VERIFY_HISTORY === "1") assert(history, "El archivo MODIS debe estar publicado");
if (history) {
  assert.equal(history.covered_days, 9131);
  assert.equal(history.annual.length, 25);
  assert.equal(history.count, history.annual.reduce((total, row) => total + row.count, 0));
  assert.equal(history.count, history.monthly.reduce((total, row) => total + row.total, 0));
}
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
try {
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    const page = await browser.newPage();
    const errors = [], optical = new Set();
    page.on("pageerror", error => errors.push(error.message));
    page.on("response", response => {
      if (response.url().includes("/hls-optical/") && response.status() === 200) optical.add(response.url());
      if (new URL(response.url()).origin === base && response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    });
    await page.setViewport({ width, height });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
    await page.goto(base + "/?lugar=huamanga", { waitUntil: "domcontentloaded" });
    await page.locator(".gaia-cta").click();
    await page.waitForSelector(".agriculture-evidence");
    assert((await page.$eval(".agriculture-evidence", el => el.textContent)).includes("no confirman suelo desnudo"));
    await page.$eval(".agriculture-evidence", el => el.scrollIntoView({ block: "start" }));
    await page.screenshot({ path: path.join(output, `pendiente-${width}.jpg`), type: "jpeg", quality: 86 });
    await page.locator(".rail button:first-child").click();
    await page.waitForSelector(".agriculture-evidence");
    await page.$$eval(".context-layers > div", rows => {
      const row = rows.find(row => row.textContent.includes("HLS S30"));
      if (!row) throw new Error("Falta la comparación óptica HLS");
      row.querySelector("button").click();
    });
    await page.waitForSelector(".comparison-control");
    await page.waitForFunction(() => document.querySelector(".comparison-control")?.textContent.includes("2026-06-22"));
    assert((await page.$eval(".map-context-source", el => el.textContent)).includes("Complementario"));
    await page.locator(".inspector-heading button").click();
    await page.waitForSelector('.globe[aria-busy="false"]', { timeout: 60_000 });
    assert.equal(optical.size, 2);
    await page.screenshot({ path: path.join(output, `hls-${width}.jpg`), type: "jpeg", quality: 88 });
    if (history) {
      await page.locator(".rail button:nth-child(4)").click();
      await page.waitForSelector(".fire-history svg");
      assert.equal(await page.$(".comparison-control"), null);
      if (width === 390) assert(await page.$eval(".inspector", el => el.getBoundingClientRect().height > 500));
      await page.$eval(".fire-history", el => el.scrollIntoView({ block: "start" }));
      await page.screenshot({ path: path.join(output, `modis-${width}.jpg`), type: "jpeg", quality: 86 });
    }
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ width, height, slope: true, opticalImages: optical.size, modis: !!history, errors }));
    await page.close();
  }
} finally { await browser.close(); }
