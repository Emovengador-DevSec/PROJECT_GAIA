// PROJECT GAIA · verificación visual de la portada con Chrome sin interfaz.
// Requiere `npm i puppeteer-core` (en una carpeta aparte) y el servidor web en :5173.
//   node tools/verify/verificar_portada.mjs art/verificacion
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";

const URL = "http://localhost:5173/";
const OUT = process.argv[2];
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true,
  args: ["--autoplay-policy=no-user-gesture-required", "--hide-scrollbars"],
});

const observers = () => {
  window.__cls = 0;
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
    .observe({ type: "layout-shift", buffered: true });
  window.__lcp = null;
  new PerformanceObserver((l) => { const e = l.getEntries().pop(); window.__lcp = { ms: Math.round(e.startTime), url: (e.url || "").split("/").pop(), el: e.element?.className }; })
    .observe({ type: "largest-contentful-paint", buffered: true });
};

const state = () => {
  const vs = [...document.querySelectorAll("video")];
  return {
    stage: document.querySelector(".gaia")?.dataset.stage,
    intro: vs[0] ? +vs[0].currentTime.toFixed(2) : null,
    loop: vs[1] ? +vs[1].currentTime.toFixed(2) : null,
    looping: vs[1]?.style.opacity === "1",
    src: vs[0]?.currentSrc.split("/").pop(),
  };
};

// contraste del texto contra el cuadro actual del video ya oscurecido por el velo
const contrast = () => {
  const W = innerWidth, H = innerHeight;
  const v = [...document.querySelectorAll("video")].find((x) => x.style.opacity === "1");
  const c = document.createElement("canvas"); c.width = W; c.height = H;
  const g = c.getContext("2d", { willReadFrequently: true });
  const s = Math.max(W / v.videoWidth, H / v.videoHeight);
  g.drawImage(v, (W - v.videoWidth * s) / 2, (H - v.videoHeight * s) / 2, v.videoWidth * s, v.videoHeight * s);
  const lerp = (stops, x) => { for (let i = 1; i < stops.length; i++) if (x <= stops[i][0]) { const [a, b] = [stops[i - 1], stops[i]]; return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]); } return 0; };
  const portrait = matchMedia("(orientation: portrait), (max-width: 760px)").matches;
  const veil = (x, y) => portrait
    ? (1 - lerp([[0, .8], [.3, .55], [.46, 0]], y / H)) * (1 - lerp([[0, .85], [.3, .4], [.46, 0]], 1 - y / H))
    : (1 - lerp([[0, .74], [.34, .4], [.58, 0]], x / W)) * (1 - lerp([[0, .9], [.16, .62], [.46, 0]], 1 - y / H));
  const lin = (u) => { u /= 255; return u <= .03928 ? u / 12.92 : ((u + .055) / 1.055) ** 2.4; };
  const lum = (r, gg, b) => .2126 * lin(r) + .7152 * lin(gg) + .0722 * lin(b);
  const out = {};
  for (const sel of [".gaia-kicker", ".gaia-title-main", ".gaia-sub", ".gaia-lead", ".gaia-fact-label", ".gaia-credit"]) {
    for (const el of document.querySelectorAll(sel)) {
      const r = el.getBoundingClientRect();
      if (!r.width || getComputedStyle(el).display === "none") continue;
      const x0 = Math.max(0, r.left | 0), y0 = Math.max(0, r.top | 0);
      const w = Math.min(W - x0, r.width | 0), h = Math.min(H - y0, r.height | 0);
      const d = g.getImageData(x0, y0, w, h).data, ls = [];
      for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {
        const i = (y * w + x) * 4, k = veil(x0 + x, y0 + y);
        ls.push(lum(d[i] * k, d[i + 1] * k, d[i + 2] * k));
      }
      ls.sort((a, b) => a - b);
      const bg = ls[Math.floor(ls.length * .95)];
      const m = getComputedStyle(el).color.match(/[\d.]+/g).map(Number);
      const a = m[3] ?? 1;
      const fg = a * lum(m[0], m[1], m[2]) + (1 - a) * bg;
      const ratio = +((fg + .05) / (bg + .05)).toFixed(1);
      out[sel] = Math.min(out[sel] ?? 99, ratio);
    }
  }
  return out;
};

const report = {};
for (const [name, width, height] of [["1440x900", 1440, 900], ["390x844", 390, 844]]) {
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1, isMobile: width < 500, hasTouch: width < 500 });
  await page.evaluateOnNewDocument(observers);
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(URL, { waitUntil: "domcontentloaded" });
  const r = (report[name] = { capturas: [] });
  const shot = async (label) => {
    const st = await page.evaluate(state);
    const file = `portada_${name}_${label}.png`;
    await page.screenshot({ path: path.join(OUT, file) });
    r.capturas.push({ label, file, ...st });
  };
  const until = async (fn, arg) => { for (let i = 0; i < 400; i++) { if (await page.evaluate(fn, arg)) return; await sleep(25); } throw new Error("timeout " + arg); };
  const introAt = (t) => document.querySelector("video")?.currentTime >= t;
  await until(introAt, 0.5); await shot("0.5s");
  await until(introAt, 3.0); await shot("3s");
  await until(() => document.querySelectorAll("video")[1]?.style.opacity === "1"); await shot("6s");
  await until(() => document.querySelectorAll("video")[1]?.currentTime >= 5); await shot("bucle");
  // contraste en varios momentos del bucle (el haz y el sol se mueven)
  const cs = [];
  for (let i = 0; i < 5; i++) { cs.push(await page.evaluate(contrast)); await sleep(1900); }
  r.contraste_min = Object.fromEntries(Object.keys(cs[0]).map((k) => [k, Math.min(...cs.map((c) => c[k]))]));
  r.fps = await page.evaluate(() => new Promise((res) => { let n = 0; const t0 = performance.now(); const f = () => { n++; performance.now() - t0 < 3000 ? requestAnimationFrame(f) : res(Math.round(n / 3)); }; requestAnimationFrame(f); }));
  r.video = await page.evaluate(() => { const q = document.querySelectorAll("video")[1].getVideoPlaybackQuality(); return { cuadros: q.totalVideoFrames, perdidos: q.droppedVideoFrames }; });
  r.cls = await page.evaluate(() => +window.__cls.toFixed(4));
  r.lcp = await page.evaluate(() => window.__lcp);
  r.poster_ms = await page.evaluate(() => { const e = performance.getEntriesByType("resource").find((x) => x.name.includes("gaia-poster")); return e ? Math.round(e.responseEnd) : null; });
  r.desborde_horizontal = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  // foco visible y paso al globo
  r.foco = await page.evaluate(() => { const a = document.activeElement; const c = getComputedStyle(a); return { el: a.className, outline: `${c.outlineWidth} ${c.outlineStyle}` }; });
  await page.keyboard.press("Enter");
  await sleep(4000);
  r.tras_entrar = await page.evaluate(() => ({ portada: !!document.querySelector(".gaia"), lienzo_globo: document.querySelectorAll("canvas").length, menu: !!document.querySelector(".rail") }));
  await page.screenshot({ path: path.join(OUT, `portada_${name}_globo.png`) });
  r.errores_js = errors;
  await page.close();
}

// movimiento reducido: solo póster, todo visible, sin video
{
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await page.goto(URL, { waitUntil: "networkidle2" });
  await sleep(500);
  report.movimiento_reducido = await page.evaluate(() => ({ stage: document.querySelector(".gaia").dataset.stage, videos: document.querySelectorAll("video").length, titulo_opacidad: getComputedStyle(document.querySelector(".gaia-title")).opacity }));
  await page.screenshot({ path: path.join(OUT, "portada_1440x900_movimiento_reducido.png") });
  await page.close();
}
await browser.close();
fs.writeFileSync(path.join(OUT, "informe.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
