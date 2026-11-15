import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir} from "node:fs/promises";
const require=createRequire(new URL("../../art/render/v3/qa/package.json",import.meta.url));
const puppeteer=require("puppeteer-core");const base="http://localhost:5173";
const data=await fetch(`${base}/api/remediation/ayacucho-huanta`).then(r=>r.json());
const zones=["incendio_sequia","erosion_huaico","estres_hidrico_agricola"].map(cause=>data.alerts.find(z=>z.risk_id===cause));
await mkdir("deploy/verificacion-f7",{recursive:true});
const browser=await puppeteer.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",
headless:true,args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try{
 const cases=process.argv.includes("--keyboard-only") ? [[1366,768,zones[0]]] : process.argv.includes("--mobile-only")
   ? [[375,812,zones[0]]] : [[1366,768,zones[0]],[1366,768,zones[1]],[1366,768,zones[2]],[375,812,zones[0]]];
 for(const [width,height,zone] of cases){
  const page=await browser.newPage();const errors=[];page.on("pageerror",e=>errors.push(e.message));
  await page.setViewport({width,height});await page.emulateMediaFeatures([{name:"prefers-reduced-motion",value:"reduce"}]);
  await page.goto(`${base}/?alert=${encodeURIComponent(zone.alert_id)}`);await page.locator(".gaia-cta").click();
  await page.waitForSelector(".zone-sheet-tabs",{timeout:60000});
  assert.equal(await page.$$eval('.zone-sheet-tabs [role="tab"]',els=>els.length),4);
  assert.equal(await page.$eval('.zone-sheet-tabs [aria-selected="true"]',el=>el.textContent),"Diagnóstico");
  const sizing=await page.$eval(".inspector-content",el=>({height:el.clientHeight,content:el.scrollHeight}));
  if(width===375) assert(sizing.height>400,"Mobile sheet is still constrained by the old sequence layout");
  await page.screenshot({path:`deploy/verificacion-f7/diagnostico-${zone.risk_id}-${width}.png`});
  if(width===1366) assert(sizing.content<=sizing.height+1,JSON.stringify(sizing));
  if(zone===zones[0]){
   await page.focus("#zone-tab-diagnosis");await page.keyboard.press("ArrowRight");
   assert.equal(await page.$eval('.zone-sheet-tabs [aria-selected="true"]',el=>el.textContent),"Clima");
   await page.keyboard.press("Home");
   assert.equal(await page.$eval('.zone-sheet-tabs [aria-selected="true"]',el=>el.textContent),"Diagnóstico");
   if(process.argv.includes("--keyboard-only")){
    await page.locator('[data-phase="voice"]').click();
    await page.waitForFunction(()=>document.querySelector('#zone-tab-voice')?.getAttribute('aria-selected')==='true');
    await page.waitForFunction(()=>document.activeElement?.classList.contains('last-mile-section'));
    assert.deepEqual(errors,[]);console.log(JSON.stringify({keyboard:true,voiceShortcut:true,errors}));await page.close();continue;
   }
   for(const tab of ["climate","future","voice"]){
    await page.locator(`#zone-tab-${tab}`).click();await page.waitForSelector(`#zone-panel-${tab}`);
    if(tab==="climate") await page.waitForFunction(()=>document.querySelector(".zone-climate")?.textContent.includes("NASA"));
    if(tab==="future") assert.equal(await page.$eval('a[href$="certificate.pdf"]',el=>el.textContent.trim()),"Descargar constancia (PDF)");
    if(tab==="voice") await page.waitForSelector(".last-mile-section");
    await page.screenshot({path:`deploy/verificacion-f7/${tab}-${width}.png`});
   }
   await page.locator("#zone-tab-diagnosis").click();
   await page.locator(".zone-sheet-more summary").click();
   assert(await page.$eval(".zone-sheet-more",el=>el.open));
  }
  assert.deepEqual(errors,[]);console.log(JSON.stringify({width,cause:zone.risk_id,sizing,errors}));await page.close();
 }
}finally{await browser.close();}
