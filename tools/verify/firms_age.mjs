import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = process.env.GAIA_VERIFY_URL ?? "http://127.0.0.1:7860";
const output = path.resolve(process.env.GAIA_VERIFY_OUTPUT ?? "deploy/verificacion-firms");
await mkdir(output, { recursive: true });
const observations = await fetch(base + "/api/alerts?include_live=true&active_only=true").then(r => r.json());
const fires = observations.features.filter(item => item.properties.kind === "fire");
assert(fires.length > 0, "Se requieren observaciones reales de FIRMS para esta verificación");
const old = fires.find(item => Date.now() - Date.parse(item.properties.date) >= 86400000) ?? fires[0];
const report = [];
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
try {
  for (const [width, height, reduced] of [[1440, 900, true], [1440, 900, false], [390, 844, true]]) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setViewport({ width, height });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: reduced ? "reduce" : "no-preference" }]);
    await page.goto(base, { waitUntil: "domcontentloaded" });
    await page.locator(".gaia-cta").click();
    await page.waitForSelector("#event-date");
    await page.waitForFunction(() => document.querySelector("#event-date")?.disabled === false);
    const viewer = await page.evaluateHandle(() => {
      const host = document.querySelector(".globe");
      let fiber = host[Object.keys(host).find(key => key.startsWith("__reactFiber$"))];
      while (fiber) {
        let hook = fiber.memoizedState;
        while (hook) {
          const value = hook.memoizedState?.current;
          if (value?.dataSources && value?.scene?.globe) return value;
          hook = hook.next;
        }
        fiber = fiber.return;
      }
      throw new Error("No se encontró el visor React/Cesium para la inspección de solo lectura");
    });
    await page.waitForFunction(v => Array.from({ length: v.dataSources.length }, (_, i) => v.dataSources.get(i))
      .some(source => source.name === "Alertas con fuente" && source.entities.values.some(entity => entity.polygon)),
    { timeout: 60000 }, viewer);
    const live = await viewer.evaluate(v => {
      const source = Array.from({ length: v.dataSources.length }, (_, i) => v.dataSources.get(i))
        .find(item => item.name === "Alertas con fuente");
      return source?.entities.values.filter(entity => entity.polygon && entity.properties?.alert)
        .map(entity => ({ date: entity.properties.alert.getValue(v.clock.currentTime).properties.date,
          color: entity.polygon.material.color.getValue(v.clock.currentTime).toCssHexString() })) ?? [];
    });
    assert(live.length > 0, "Las celdas térmicas deben estar cargadas");
    const legend = await page.$eval(".fire-age", el => el.getAttribute("aria-label"));
    assert(legend.includes("24 horas") && legend.includes("1 a 3") && legend.includes("4 a 7"));
    const replay = Date.parse(old.properties.date) + 3600000;
    await page.$eval("#event-date", (input, value) => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }, replay);
    await page.waitForFunction(() => document.querySelector(".timeline-heading strong")?.textContent === "Hasta esta fecha");
    await viewer.evaluate((v, coords) => {
      v.camera.cancelFlight();
      v.camera.setView({ destination: v.scene.globe.ellipsoid.cartographicToCartesian({
        longitude: coords[0] * Math.PI / 180, latitude: coords[1] * Math.PI / 180, height: 180000 }),
        orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 } });
    }, old.geometry.coordinates);
    await page.waitForSelector('.globe[aria-busy="false"]', { timeout: 60000 });
    const observed = await viewer.evaluate((v, id) => {
      const source = Array.from({ length: v.dataSources.length }, (_, i) => v.dataSources.get(i))
        .find(item => item.name === "Alertas con fuente");
      const entity = source.entities.getById(id);
      if (entity?.billboard) return { mode: "billboard", image: decodeURIComponent(entity.billboard.image.getValue(v.clock.currentTime)) };
      for (let i = 0; i < v.scene.primitives.length; i++) {
        const collection = v.scene.primitives.get(i);
        if (!collection.get || typeof collection.length !== "number") continue;
        for (let j = 0; j < collection.length; j++) {
          const point = collection.get(j);
          if (point.id?.id === id && point.color) return { mode: "point", color: point.color.toCssHexString() };
        }
      }
      throw new Error("No se encontró el foco observado en la escena");
    }, old.properties.id);
    assert(observed.mode === "billboard" ? observed.image.includes("#ff2d2d") : observed.color === "#ff2d2d",
      "Al reproducir una hora después de la observación, el foco debe ser rojo");
    await page.screenshot({ path: path.join(output, `fuego-${width}-${reduced ? "reducido" : "animado"}.jpg`), type: "jpeg", quality: 86 });
    assert.deepEqual(errors, []);
    report.push({ width, height, reduced, cells: live.length, mode: observed.mode, replayRed: true, errors });
    console.log(JSON.stringify(report.at(-1)));
    await page.close();
  }
} finally { await browser.close(); }
await writeFile(path.join(output, "informe.json"), JSON.stringify(report, null, 2));
