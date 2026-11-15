import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = "http://localhost:5173";
const data = await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r => r.json());
await mkdir("deploy/verificacion-f2", { recursive: true });
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
try {
  for (const [width, height] of [[1366,768], [375,812]]) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    await page.setViewport({width,height});
    await page.emulateMediaFeatures([{name:"prefers-reduced-motion",value:"reduce"}]);
    await page.goto(base);
    await page.locator(".gaia-cta").click();
    await page.waitForSelector('[data-phase="action"]:not(:disabled)');
    await page.locator('[data-phase="action"]').click();
    await page.waitForSelector(".zone-cause-group .case");
    const ids = await page.$$eval(".zone-cause-group .zone-identity", nodes => nodes.map(el => el.dataset.zoneId));
    assert.equal(ids.length, data.alerts.length);
    assert.equal(new Set(ids).size, ids.length);
    const groups = await page.$$eval(".zone-cause-group", nodes => nodes.map(el => ({
      ids:[...el.querySelectorAll(".zone-identity")].map(n => n.dataset.zoneId), text:el.textContent })));
    for (const group of groups) {
      const zones=group.ids.map(id=>data.alerts.find(zone=>zone.alert_id===id));
      assert.equal(new Set(zones.map(zone=>zone.risk_id)).size,1);
      assert(zones.every((zone,i)=>i===0 || zone.index<=zones[i-1].index));
      assert(!group.text.includes("Receta:"));
      assert(!group.text.includes("Presupuesto:"));
    }
    await page.screenshot({path:`deploy/verificacion-f2/lista-${width}.png`});
    await page.locator(".zone-cause-group:first-child button.case:first-of-type").click();
    await page.waitForSelector(".alert-detail > .zone-identity");
    const header=await page.$eval(".alert-detail > .zone-identity",el=>({text:el.textContent,height:el.getBoundingClientRect().height}));
    assert(header.text.includes("ha"));
    await page.screenshot({path:`deploy/verificacion-f2/ficha-${width}.png`});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({width,zones:ids.length,groups:groups.length,header,errors}));
    await page.close();
  }
} finally { await browser.close(); }
