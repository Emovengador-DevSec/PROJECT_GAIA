import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir} from "node:fs/promises";
const require=createRequire(new URL("../../art/render/v3/qa/package.json",import.meta.url));
const puppeteer=require("puppeteer-core");
const base="http://localhost:5173";
const data=await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r=>r.json());
const zone=data.alerts.find(zone=>zone.alert_id.endsWith("_014"));
for(const zone of data.alerts) if(zone.recovery_scenario) {
  assert(!("baseline_ndvi" in zone.recovery_scenario));
  assert(Object.values(zone.recovery_scenario.projected).every(item=>!("ndvi" in item)));
}
await mkdir("deploy/verificacion-f4",{recursive:true});
const browser=await puppeteer.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",
headless:true,args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try {
  for(const [width,height] of [[1366,768],[375,812]]) {
    const page=await browser.newPage();const errors=[];page.on("pageerror",e=>errors.push(e.message));
    await page.setViewport({width,height});
    await page.emulateMediaFeatures([{name:"prefers-reduced-motion",value:"reduce"}]);
    await page.goto(`${base}/?alert=${encodeURIComponent(zone.alert_id)}`);
    await page.locator(".gaia-cta").click();
    await page.waitForSelector("details.recovery-scenario-box",{timeout:60000});
    assert(await page.$eval("details.recovery-scenario-box",el=>!el.open));
    assert(!(await page.$eval(".alert-detail",el=>el.textContent)).includes("Año 0"));
    await page.$eval("details.recovery-scenario-box",el=>el.scrollIntoView({block:"start",behavior:"instant"}));
    await page.screenshot({path:`deploy/verificacion-f4/cerrado-${width}.png`});
    await page.locator("details.recovery-scenario-box summary").click();
    const text=await page.$eval("details.recovery-scenario-box",el=>el.textContent);
    assert(text.includes("+0,24"));assert(text.includes("Fuente pendiente de verificación"));
    await page.screenshot({path:`deploy/verificacion-f4/supuestos-${width}.png`});
    assert.deepEqual(errors,[]);console.log(JSON.stringify({width,closedByDefault:true,relativeOnly:true,errors}));
    await page.close();
  }
} finally {await browser.close();}
