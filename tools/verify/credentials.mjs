import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
try {
  const page = await browser.newPage();
  let errors = 0;
  page.on("pageerror", () => errors++);
  await page.setViewport({ width: 1440, height: 900 });
  await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await page.goto("http://localhost:5173/", { waitUntil: "domcontentloaded" });
  await page.locator(".gaia-cta").click();
  await page.locator(".rail button:nth-child(6)").click();
  await page.waitForFunction(() => document.querySelector(".quality-facts")?.textContent?.includes("Cesium World Terrain")
    || document.querySelector(".quality-facts")?.textContent?.includes("Mapzen"), { timeout: 45_000 });
  const facts = await page.$$eval(".quality-facts dd", elements => elements.map(element => element.textContent));
  const renderError = !!await page.$(".cesium-widget-errorPanel");
  console.log(JSON.stringify({ imagery: facts[0], terrain: facts[1], errors, renderError }));
  if (!renderError && !errors && facts[1] === "Cesium World Terrain") {
    await page.screenshot({ path: path.resolve("art/verificacion/credenciales-cesium-1440.jpg"), type: "jpeg", quality: 85 });
  }
} catch (error) { console.log(JSON.stringify({ verificationError: error.name })); process.exitCode = 1; }
finally { await browser.close(); }
