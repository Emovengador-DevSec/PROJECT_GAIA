import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
const require = createRequire(new URL("../../art/render/v3/qa/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");
const base = "http://localhost:5173";
const data = await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r=>r.json());
assert(data.alerts.every(zone=>zone.optical_context === null));
await mkdir("deploy/verificacion-f3",{recursive:true});
const browser = await puppeteer.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless:true,args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try {
  for (const [width,height,index] of [[1366,768,0],[375,812,14]]) {
    const page=await browser.newPage(); const errors=[];
    page.on("pageerror",e=>errors.push(e.message));
    await page.setViewport({width,height});
    await page.emulateMediaFeatures([{name:"prefers-reduced-motion",value:"reduce"}]);
    await page.goto(`${base}/?alert=${encodeURIComponent(data.alerts[index].alert_id)}`);
    await page.locator(".gaia-cta").click();
    await page.waitForSelector(".zone-optical-unavailable",{timeout:60000});
    assert.equal(await page.$$eval(".alert-detail img[src*='hls-optical']",els=>els.length),0);
    await page.$eval(".zone-optical-unavailable",el=>el.scrollIntoView({block:"start",behavior:"instant"}));
    await page.screenshot({path:`deploy/verificacion-f3/ficha-${width}.png`});
    await page.locator(".zone-optical-unavailable button").click();
    await page.waitForFunction(()=>document.querySelector(".inspector-heading h2")?.textContent==="Cambios");
    await page.waitForFunction(()=>document.querySelector(".inspector-content")?.textContent.includes("HLS"));
    await page.screenshot({path:`deploy/verificacion-f3/cambios-${width}.png`});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({width,zone:data.alerts[index].alert_id,zonePhotos:0,regionalHlsInChanges:true,errors}));
    await page.close();
  }
} finally {await browser.close();}
