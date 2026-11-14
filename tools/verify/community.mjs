import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = process.env.GAIA_VERIFY_URL ?? "http://127.0.0.1:8095";
const out = path.resolve(process.env.GAIA_VERIFY_OUTPUT ?? "deploy/verificacion-comunidad");
await mkdir(out, { recursive: true });
const response = await fetch(base + "/api/community");
assert.equal(response.status, 200);
const index = await response.json();
assert.equal(index.places.filter(place => place.kind === "district").length, 39);
const source = JSON.parse(await readFile("data/04_published/exposure/ayacucho-huanta.json", "utf8"));
const hv = Object.entries(source.alerts).filter(([id]) => id.includes("_hvhv_")
  && id.includes(`${index.period.a}__${index.period.b}`)).map(([, value]) => value);
assert.equal(index.region.zones, hv.length);
const fields = ["cropland_ha", "forest_ha", "grassland_ha", "population"];
for (const field of fields) {
  assert(Math.abs(index.region[field] - hv.reduce((total, row) => total + (row[field] ?? 0), 0)) < .001);
}
assert.deepEqual(await fetch(base + "/api/reports").then(result => result.json()), []);

const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
  headless: true,
});
try {
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("response", res => {
      if (new URL(res.url()).origin === base && res.status() >= 400) errors.push(`${res.status()} ${res.url()}`);
    });
    await page.setViewport({ width, height });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
    await page.goto(base + "/?lugar=huamanga", { waitUntil: "domcontentloaded" });
    await page.locator(".gaia-cta").click();
    await page.waitForSelector(".community-status");
    await page.waitForFunction(() => !document.querySelector(".map-context")?.textContent.includes("Cargando imagen"));
    assert.equal(await page.$eval(".community-heading h3", el => el.textContent), "Huamanga");
    assert.equal(await page.$eval(".community-controls select", el => el.value), "Huamanga");
    if (width === 390) assert(await page.$eval(".inspector", el => el.getBoundingClientRect().height > 500));
    const share = await page.$eval(".community a[href^='https://wa.me/']", el => new URL(el.href).searchParams.get("text"));
    assert(share.length <= 500 && share.includes("?lugar=huamanga") && share.includes("UTC"));
    await page.screenshot({ path: path.join(out, `ficha-${width}.jpg`), type: "jpeg", quality: 87 });
    await page.waitForFunction(() => document.querySelector(".community-search input")?.disabled === false);
    await page.locator(".community-search input").fill("Pucajasa");
    await page.waitForSelector(".community-results button");
    await page.locator(".community-results li:first-child button").click();
    await page.waitForFunction(() => document.querySelector(".community-heading h3")?.textContent === "Pucajasa");
    await page.locator(".citizen-reports .detail-actions button:last-child").click();
    await page.waitForSelector(".report-form");
    assert((await page.$eval(".citizen-reports", el => el.textContent)).includes("Aún no hay reportes."));
    await page.$eval(".report-form", el => el.scrollIntoView({ block: "center" }));
    await page.screenshot({ path: path.join(out, `reportes-${width}.jpg`), type: "jpeg", quality: 87 });
    await page.locator(".rail button:nth-child(4)").click();
    await page.locator(".climate-periods button:nth-child(3)").click();
    await page.waitForSelector(".community-climate-plot polygon");
    assert((await page.$eval(".climate-arcs", el => el.textContent)).includes("45 años completos"));
    await page.screenshot({ path: path.join(out, `clima-${width}.jpg`), type: "jpeg", quality: 87 });
    await page.locator(".rail button:last-child").click();
    await page.waitForSelector(".community-status");
    await page.emulateMediaType("print");
    const css = await page.$eval(".community", el => getComputedStyle(el).display);
    assert.notEqual(css, "none");
    const pdf = Buffer.from(await page.pdf({
      path: path.join(out, `ficha-${width}.pdf`), format: "A4", printBackground: false,
      margin: { top: "10mm", bottom: "10mm", left: "10mm", right: "10mm" },
    }));
    const pages = [...pdf.toString("latin1").matchAll(/\/Type\s*\/Page\b/g)].length;
    assert.equal(pages, 1, "La ficha impresa debe caber en una página");
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ width, height, community: true, printPages: pages, errors }));
    await page.close();
  }
} finally {
  await browser.close();
}
