import {createRequire} from 'node:module';
const require=createRequire(new URL('../../art/render/v3/qa/package.json',import.meta.url));const puppeteer=require('puppeteer-core');
const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{const page=await browser.newPage();await page.setViewport({width:375,height:812});await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://localhost:5173/?alert=alr_ayacucho-huanta_2026-06-24__2026-10-10_hvhv_080');await page.locator('.gaia-cta').click();await page.waitForSelector('#zone-tab-place',{timeout:60000});await page.locator('#zone-tab-place').click();await page.waitForSelector('.place-timeline');
if(!await page.$eval('.map-photo-index',el=>getComputedStyle(el).display==='none'))throw Error('Map menu overlays mobile sheet');
await page.screenshot({path:'deploy/verificacion-r27/mobile.png'});
await page.locator('.inspector-heading .icon-button').click();await page.locator('.map-photo-index summary').click();await page.locator('.map-photo-index button').click();
await page.screenshot({path:'deploy/verificacion-r27/mobile-map-pins.png'});
await page.locator('.map-photo-index button[data-photo-id]').click();await page.waitForSelector('.map-photo-popup');await page.screenshot({path:'deploy/verificacion-r27/mobile-photo.png'});await page.keyboard.press('Escape');await page.waitForSelector('.map-photo-popup',{hidden:true});
await page.setViewport({width:1366,height:768});await page.locator('.panel-reopen').click();await page.locator('#zone-tab-place').click();
await page.waitForSelector('.place-block .real-photo',{timeout:60000});await page.$eval('.place-block .real-photo',el=>el.scrollIntoView({block:'center'}));await page.waitForFunction(()=>{const img=document.querySelector('.place-block .real-photo img');return img?.complete&&img.naturalWidth>0;});await page.screenshot({path:'deploy/verificacion-r27/plants-and-credits.png'});
console.log(JSON.stringify({mobileMenuAvoidsSheet:true,mobilePopup:true,plantPhotoLoaded:true,errors}));if(errors.length)throw Error(errors.join('\n'));
}finally{await browser.close();}
