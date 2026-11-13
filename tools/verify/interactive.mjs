import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const moment = process.argv[2] ?? "W8";
const output = path.resolve("art/verificacion/interactiva", moment);
await mkdir(output, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
try {
  for (const [width, height] of [[1440, 900], [2560, 1440], [390, 844]]) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => { errors.push(error.message); console.log(error.stack); });
    page.on("console", message => {
      if (message.type() === "error" && /model|nisar|draco/i.test(message.text())) console.log(message.text());
    });
    await page.setViewport({ width, height });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
    await page.locator(".gaia-cta").click();
    if (width < 720) await page.locator(".panel-reopen").click();
    await page.waitForSelector(".featured-observation");
    await page.waitForFunction(() => !document.querySelector(".loading-state"));
    if (moment !== "W8") {
      await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "no-preference" }]);
    }
    await new Promise(resolve => setTimeout(resolve, ["W1", "W3"].includes(moment) ? 4400 : 900));
    if (moment === "W3" && width === 1440) {
      // Stop the idle rotation while checking five actual geographic markers.
      await page.mouse.click(450, 400);
      const found = new Set();
      for (let y = 165; y < 670 && found.size < 5; y += 15) {
        for (let x = 520; x < 760 && found.size < 5; x += 15) {
          await page.mouse.move(x, y);
          await new Promise(resolve => setTimeout(resolve, 60));
          const id = await page.$eval("body", () => document.querySelector(".map-tooltip")?.getAttribute("data-observation"));
          if (id) found.add(id);
        }
      }
      if (found.size < 5) throw new Error(`Only ${found.size} geographic markers responded to the cursor`);
      console.log(JSON.stringify({ moment, hoverResponded: [...found] }));
    }
    if (moment === "W5") {
      const actual = await page.evaluate(async () => (await (await fetch("/api/alerts?include_live=true")).json()).features);
      const cutoff = await page.$eval("#event-date", element => Number(element.max) - 5 * 86_400_000);
      await page.$eval("#event-date", (element, value) => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(element, value);
        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));
      }, cutoff);
      await new Promise(resolve => setTimeout(resolve, 350));
      const expected = actual.filter(item => Date.parse(item.properties.date) <= cutoff).length;
      const count = await page.$eval(".result-count", element => Number(element.textContent.match(/\d+/)[0]));
      if (count !== expected) throw new Error(JSON.stringify({ cutoff, count, expected }));
      const playFrom = cutoff - 20 * 86_400_000;
      await page.$eval("#event-date", (element, value) => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(element, value);
        element.dispatchEvent(new Event("input", { bubbles: true }));
      }, playFrom);
      await page.locator('[aria-label="Reproducir 30 días"]').click();
      await new Promise(resolve => setTimeout(resolve, 2100));
      await page.locator('[aria-label="Pausar secuencia"]').click();
      const later = await page.$eval("#event-date", element => Number(element.value));
      if (later <= playFrom) throw new Error("The timeline did not advance");
      console.log(JSON.stringify({ moment, width, expectedAtCutoff: expected, advancedHours: (later - playFrom) / 3_600_000 }));
    }
    if (moment === "W4") {
      await page.locator('.featured-observation[data-kind="quake"]').click();
      await page.waitForSelector(".camera-tour");
      await page.keyboard.press("Escape");
      await page.waitForFunction(() => !document.querySelector(".camera-tour"));
      await page.locator(".detail-back").click();
      await page.locator('.featured-observation[data-kind="fire"]').click();
      await page.waitForSelector(".camera-tour");
      console.log(JSON.stringify({ moment, width, immersion: "quake and fire", escapeStopsOrbit: true }));
    }
    if (moment === "W6") {
      await page.waitForSelector(".orbit-dot[data-active]");
      if (width < 720) {
        await page.locator('[aria-label="Cerrar panel y explorar el mapa"]').click();
        await page.locator(".orbit-card > summary").click();
      }
      await page.locator(".orbit-actions button:last-child").click();
      if (width < 720) await page.locator(".orbit-card > summary").click();
      await new Promise(resolve => setTimeout(resolve, 3400));
      console.log(JSON.stringify({ moment, width, orbitSource: await page.$eval(".orbit-card a", element => element.textContent) }));
    }
    if (moment === "W7") {
      await page.locator(".rail button:nth-child(2)").click();
      await page.locator(".case:first-child").click();
      await page.locator(".rail button:nth-child(3)").click();
      await page.waitForFunction(() => document.querySelector(".empty-state h3")?.textContent === "Falta procesar NISAR");
      const health = await page.evaluate(async () => (await (await fetch("/api/health")).json()));
      if (health.layers !== 0 || health.credentials.earthdata) throw new Error("The pending-data scenario changed");
      await new Promise(resolve => setTimeout(resolve, 3200));
      console.log(JSON.stringify({ moment, width, state: "Waiting for Earthdata and processed NISAR", layers: health.layers }));
    }
    const layoutSelector = width < 720 && moment === "W6" ? ".panel-reopen" : ".inspector";
    await page.waitForFunction(selector => {
      const element = document.querySelector(selector);
      if (!element) return false;
      const transform = getComputedStyle(element).transform;
      return transform === "none" || Math.abs(new DOMMatrixReadOnly(transform).m41) < .05;
    }, {}, layoutSelector);
    const layout = await page.$eval(layoutSelector, element => {
      const rect = element.getBoundingClientRect();
      return { left: rect.left, right: rect.right, scroll: element.scrollWidth, width: element.clientWidth };
    });
    if (layout.left < 0 || layout.right > width || layout.scroll > layout.width) {
      throw new Error(JSON.stringify({ moment, width, layout }));
    }
    if (errors.length) throw new Error(errors.join("\n"));
    const renderError = await page.$(".cesium-widget-errorPanel");
    if (renderError) throw new Error(await renderError.evaluate(element => element.textContent));
    await page.screenshot({ path: path.join(output, `${width}x${height}.jpg`), type: "jpeg", quality: 85 });
    console.log(JSON.stringify({ moment, width, layout, errors }));
    await page.close();
  }
} finally { await browser.close(); }
