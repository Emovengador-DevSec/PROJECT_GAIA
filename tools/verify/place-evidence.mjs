import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const require=createRequire(new URL('../../art/render/v3/qa/package.json',import.meta.url));const puppeteer=require('puppeteer-core');
const base='http://localhost:5173';const dir='deploy/verificacion-r27';await mkdir(dir,{recursive:true});
const rem=JSON.parse(await readFile('data/04_published/remediation/ayacucho-huanta.json','utf8'));
const photos=JSON.parse(await readFile('data/04_published/photos/ayacucho-huanta.json','utf8'));
const zones=['incendio_sequia','erosion_huaico','estres_hidrico_agricola'].map(cause=>rem.alerts.find(z=>z.risk_id===cause && photos.zones[z.alert_id]?.nearby.length)??rem.alerts.find(z=>z.risk_id===cause));
const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{const page=await browser.newPage();await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);const errors=[],remote=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/naturalist|wikimedia|flickr/.test(r.url()))remote.push(r.url());});const records=[];
for(const zone of zones){await page.setViewport({width:1366,height:768});await page.goto(`${base}/?alert=${zone.alert_id}`);await page.locator('.gaia-cta').click();await page.waitForSelector('#zone-tab-place',{timeout:60000});await page.locator('#zone-tab-place').click();await page.waitForSelector('.place-timeline',{timeout:60000});
 await page.waitForFunction(()=>[...document.querySelectorAll('.place-evidence img')].some(img=>img.complete&&img.naturalWidth));
 await page.screenshot({path:`${dir}/${zone.risk_id}-1366.png`});
 const evidence=await fetch(`${base}/api/remediation/ayacucho-huanta/${zone.alert_id}/place`).then(r=>r.json());
 const images=await page.$$eval('.place-evidence img',imgs=>imgs.map(img=>({src:img.getAttribute('src'),loaded:img.complete&&img.naturalWidth>0})));
 await page.$$eval('.place-timeline button',buttons=>buttons.at(-1).click());await page.waitForSelector('.place-future');
 const future=await page.$eval('.place-future',el=>el.innerText);if(/NDVI:.*\d/.test(future))throw Error('Unverified scenario numbers visible');
 await page.screenshot({path:`${dir}/${zone.risk_id}-futuro.png`});
 let popup=false;if(evidence.pins.length){await page.locator('.map-photo-index summary').click();await page.locator('.map-photo-index button[data-photo-id]').click();await page.waitForSelector('.map-photo-popup');await page.screenshot({path:`${dir}/${zone.risk_id}-pin.png`});await page.keyboard.press('Escape');await page.waitForSelector('.map-photo-popup',{hidden:true});popup=true;}
 records.push({zone:zone.alert_id,cause:zone.risk_id,images,pins:evidence.pins.length,popup,tabCount:await page.$$eval('.zone-sheet-tabs button',els=>els.length)});
 await writeFile(`${dir}/checks.json`,JSON.stringify({records,errors,remote},null,2));
}
await page.setViewport({width:375,height:812});await page.locator('#zone-tab-place').click();await page.waitForSelector('.place-timeline');await page.screenshot({path:`${dir}/mobile.png`});
const overflow=await page.$eval('.inspector-content',el=>({width:el.clientWidth,scrollWidth:el.scrollWidth}));if(overflow.scrollWidth>overflow.width+1)throw Error('Mobile content overflow');
await page.locator('#zone-tab-diagnosis').click();await page.focus('#zone-tab-diagnosis');await page.keyboard.press('End');const keyboard=await page.$eval('#zone-tab-place',el=>el.getAttribute('aria-selected')==='true'&&document.activeElement===el);if(!keyboard)throw Error('End did not select place tab');
await writeFile(`${dir}/checks.json`,JSON.stringify({records,errors,remote,overflow,keyboard},null,2));console.log(JSON.stringify({records,errors,remote,overflow,keyboard}));
if(errors.length||remote.length)throw Error('Browser errors or external photo calls');
}finally{await browser.close();}
