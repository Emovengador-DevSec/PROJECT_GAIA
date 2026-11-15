import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir} from "node:fs/promises";
const require=createRequire(new URL("../../art/render/v3/qa/package.json",import.meta.url));
const puppeteer=require("puppeteer-core");
const base="http://localhost:5173";
const data=await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r=>r.json());
const zone=data.alerts.find(zone=>zone.alert_id.endsWith("_014"));
const bulletin=await fetch(`${base}/api/remediation/ayacucho-huanta/${zone.alert_id}/bulletin`).then(r=>r.json());
assert.equal(bulletin.audio_url_qu,null);assert.equal(bulletin.bulletin.stations.length,0);
await mkdir("deploy/verificacion-f6",{recursive:true});
const browser=await puppeteer.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless:true,args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try {
  for(const [width,height] of [[1366,768],[375,812]]) {
    const page=await browser.newPage();const errors=[];page.on("pageerror",e=>errors.push(e.message));
    await page.setViewport({width,height});
    await page.emulateMediaFeatures([{name:"prefers-reduced-motion",value:"reduce"}]);
    await page.goto(`${base}/?alert=${encodeURIComponent(zone.alert_id)}`);
    await page.locator(".gaia-cta").click();await page.waitForSelector(".last-mile-section",{timeout:60000});
    const text=await page.$eval(".alert-detail",el=>el.textContent);
    assert(!text.includes("Yachaq"));assert(!text.includes("Radios locales aliadas"));
    const pdf=await page.$eval('a[href$="certificate.pdf"]',el=>el.textContent.trim());
    assert.equal(pdf,"Descargar constancia (PDF)");
    const qu=await page.$$eval(".last-mile-section button",els=>els.find(el=>el.textContent.includes("Quechua"))?.textContent.trim());
    assert.equal(qu,"Quechua · borrador sin grabar");
    await page.$eval('a[href$="certificate.pdf"]',el=>el.scrollIntoView({block:"start",behavior:"instant"}));
    await page.screenshot({path:`deploy/verificacion-f6/ficha-${width}.png`});
    await page.$$eval(".last-mile-section button",els=>els.find(el=>el.textContent.includes("Quechua")).click());
    await page.waitForFunction(()=>!document.querySelector(".last-mile-section audio"));
    await page.$eval(".last-mile-section",el=>el.scrollIntoView({block:"start",behavior:"instant"}));
    await page.screenshot({path:`deploy/verificacion-f6/quechua-${width}.png`});
    assert.deepEqual(errors,[]);console.log(JSON.stringify({width,pdf,qu,emptyStationsHidden:true,yachaqHidden:true,noQuechuaPlayer:true,errors}));
    await page.close();
  }
}finally{await browser.close();}
