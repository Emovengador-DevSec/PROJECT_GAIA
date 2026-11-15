import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir} from "node:fs/promises";
const require=createRequire(new URL("../../art/render/v3/qa/package.json",import.meta.url));
const puppeteer=require("puppeteer-core");
const base="http://localhost:5173";
const data=await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r=>r.json());
const zone=data.alerts.find(zone=>zone.alert_id.endsWith("_014"));
const empty=data.alerts.find(zone=>!zone.nearby_places.length);
assert(empty,"A published zone without nearby places is required for the negative check");
for(const z of [zone,empty]) {
  const b=await fetch(`${base}/api/remediation/ayacucho-huanta/${z.alert_id}/bulletin`).then(r=>r.json());
  assert.equal(b.minka.needed_workers,null);assert.equal(b.minka.savings_estimated_soles,null);
  assert.deepEqual(b.minka.target_communities,z.nearby_places.map(p=>p.name));
  if(!z.nearby_places.length) assert.equal(b.minka.sms_verification,null);
  else assert(b.bulletin.script_es.includes(z.nearby_places[0].name));
  assert(!JSON.stringify(b).includes("en ."));
}
await mkdir("deploy/verificacion-f5",{recursive:true});
const browser=await puppeteer.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless:true,args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try {
  for(const [width,height,z] of [[1366,768,zone],[375,812,zone],[1366,768,empty]]) {
    const page=await browser.newPage();const errors=[];page.on("pageerror",e=>errors.push(e.message));
    await page.setViewport({width,height});
    await page.emulateMediaFeatures([{name:"prefers-reduced-motion",value:"reduce"}]);
    await page.goto(`${base}/?alert=${encodeURIComponent(z.alert_id)}`);
    await page.locator(".gaia-cta").click();await page.waitForSelector(".minka-box",{timeout:60000});
    const sheet = await page.$eval(".alert-detail", el => el.textContent);
    assert(!sheet.includes("por_verificar"));
    assert(!sheet.includes("S/ Sin dato"));
    assert(!sheet.includes("en ."));
    const budget=await page.$eval(".budget-summary",el=>el.textContent);
    assert(!budget.includes("Fuente:"));assert(!budget.includes("por_verificar"));assert(!budget.includes("Sin dato"));
    await page.$eval(".budget-summary",el=>el.scrollIntoView({block:"start",behavior:"instant"}));
    await page.screenshot({path:`deploy/verificacion-f5/presupuesto-${width}-${z.nearby_places.length}.png`});
    const text=await page.$eval(".minka-box",el=>el.textContent);
    assert(!text.includes("Meta comunal"));assert(!text.includes("Ahorro Minka"));
    if(z.nearby_places.length) assert(text.includes(z.nearby_places[0].name));
    await page.$eval(".minka-box",el=>el.scrollIntoView({block:"start",behavior:"instant"}));
    await page.screenshot({path:`deploy/verificacion-f5/minka-${width}-${z.nearby_places.length}.png`});
    assert.deepEqual(errors,[]);console.log(JSON.stringify({width,id:z.alert_id,places:z.nearby_places,errors}));
    await page.close();
  }
} finally {await browser.close();}
