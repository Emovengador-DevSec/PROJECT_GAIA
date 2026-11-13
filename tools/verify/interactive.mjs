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
    page.on("pageerror", error => errors.push(error.message));
    await page.setViewport({ width, height });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
    await page.locator(".gaia-cta").click();
    await page.waitForSelector(".featured-observation");
    await page.waitForFunction(() => !document.querySelector(".loading-state"));
    await new Promise(resolve => setTimeout(resolve, 900));
    const layout = await page.$eval(".inspector", element => {
      const rect = element.getBoundingClientRect();
      return { left: rect.left, right: rect.right, scroll: element.scrollWidth, width: element.clientWidth };
    });
    if (layout.left < 0 || layout.right > width || layout.scroll > layout.width) {
      throw new Error(JSON.stringify({ moment, width, layout }));
    }
    if (errors.length) throw new Error(errors.join("\n"));
    await page.screenshot({ path: path.join(output, `${width}x${height}.jpg`), type: "jpeg", quality: 85 });
    console.log(JSON.stringify({ moment, width, layout, errors }));
    await page.close();
  }
} finally { await browser.close(); }
