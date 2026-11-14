// PROJECT GAIA · verificación visual de la portada con Chrome sin interfaz.
// Requiere `npm i puppeteer-core` (en una carpeta aparte) y el servidor web en :5173.
//   node tools/verify/verificar_portada.mjs art/verificacion
// NODE_PATH puede apuntar a esa carpeta/node_modules. --titulos compara las dos propuestas.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const puppeteer = createRequire(import.meta.url)("puppeteer-core");
const URL = process.env.GAIA_URL || "http://127.0.0.1:5173/";
const OUT = process.argv[2];
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true,
  args: ["--autoplay-policy=no-user-gesture-required", "--hide-scrollbars"],
});

const observers = () => {
  window.__entrada = [];
  const introTime = () => +(document.querySelector("video")?.currentTime ?? 0).toFixed(3);
  new MutationObserver(changes => {
    for (const { target } of changes) {
      if (target.matches('.gaia-head[data-entry="reveal"]'))
        window.__entrada.push({ evento: "revelar", video: introTime() });
    }
  }).observe(document, { subtree: true, attributes: true, attributeFilter: ["data-entry"] });
  document.addEventListener("animationstart", e => {
    if (e.target.closest(".gaia-head"))
      window.__entrada.push({ evento: e.animationName, video: introTime() });
  });
  window.__cls = 0;
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
    .observe({ type: "layout-shift", buffered: true });
  window.__lcp = null;
  new PerformanceObserver((l) => { const e = l.getEntries().pop(); window.__lcp = { ms: Math.round(e.startTime), url: (e.url || "").split("/").pop(), el: e.element?.className }; })
    .observe({ type: "largest-contentful-paint", buffered: true });
};

const state = () => {
  const vs = [...document.querySelectorAll("video")];
  const cta = document.querySelector(".gaia-cta");
  return {
    entrada_visible: !!cta?.getClientRects().length,
    intro: vs[0] ? +vs[0].currentTime.toFixed(2) : null,
    loop: vs[1] ? +vs[1].currentTime.toFixed(2) : null,
    looping: vs[1]?.style.opacity === "1",
    src: vs[0]?.currentSrc.split("/").pop(),
  };
};

// Contraste del texto contra el video, compuesto con el fondo de su botón o indicador.
const contrast = () => {
  const W = innerWidth, H = innerHeight;
  const v = [...document.querySelectorAll("video")].find((x) => x.style.opacity === "1");
  const c = document.createElement("canvas"); c.width = W; c.height = H;
  const g = c.getContext("2d", { willReadFrequently: true });
  const s = Math.max(W / v.videoWidth, H / v.videoHeight);
  const [fx, fy] = getComputedStyle(v).objectPosition.split(" ").map(p => parseFloat(p) / 100);
  g.drawImage(v, (W - v.videoWidth * s) * fx, (H - v.videoHeight * s) * fy, v.videoWidth * s, v.videoHeight * s);
  const lin = (u) => { u /= 255; return u <= .03928 ? u / 12.92 : ((u + .055) / 1.055) ** 2.4; };
  const lum = (r, gg, b) => .2126 * lin(r) + .7152 * lin(gg) + .0722 * lin(b);
  const out = {};
  const rgb = (color) => color.match(/[\d.]+/g).map(Number);
  for (const sel of [".gaia-title-main", ".gaia-fact-value", ".gaia-fact-value small", ".gaia-fact-label"]) {
    for (const el of document.querySelectorAll(sel)) {
      const surface = rgb(getComputedStyle(el.closest(".gaia-cta, .gaia-fact")).backgroundColor);
      const alpha = surface[3] ?? 1;
      const r = el.getBoundingClientRect();
      if (!r.width || getComputedStyle(el).display === "none") continue;
      const x0 = Math.max(0, r.left | 0), y0 = Math.max(0, r.top | 0);
      const w = Math.min(W - x0, r.width | 0), h = Math.min(H - y0, r.height | 0);
      const d = g.getImageData(x0, y0, w, h).data, ls = [];
      for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {
        const i = (y * w + x) * 4;
        ls.push(lum(surface[0] * alpha + d[i] * (1 - alpha),
          surface[1] * alpha + d[i + 1] * (1 - alpha),
          surface[2] * alpha + d[i + 2] * (1 - alpha)));
      }
      ls.sort((a, b) => a - b);
      const bg = ls[Math.floor(ls.length * .95)];
      const m = rgb(getComputedStyle(el).color);
      const a = m[3] ?? 1;
      const fg = a * lum(m[0], m[1], m[2]) + (1 - a) * bg;
      const ratio = +((Math.max(fg, bg) + .05) / (Math.min(fg, bg) + .05)).toFixed(1);
      out[sel] = Math.min(out[sel] ?? 99, ratio);
    }
  }
  return out;
};

// El cine ocupa la ventana entera y el rótulo y sus círculos forman el único bloque de entrada.
const checkLayout = () => {
  const root = document.querySelector(".gaia");
  const backdrop = root.querySelector(".gaia-backdrop");
  const cta = root.querySelector("h1 button");
  const button = cta.getBoundingClientRect();
  const textRange = document.createRange();
  textRange.selectNodeContents(cta.querySelector(".gaia-title-main"));
  const label = textRange.getBoundingClientRect();
  const arrow = cta.querySelector(".gaia-arrow").getBoundingClientRect();
  const oneLine = textRange.getClientRects().length === 1 && label.right <= arrow.left &&
    label.left > button.left && arrow.right < button.right && arrow.top < label.bottom && arrow.bottom > label.top;
  const style = getComputedStyle(cta);
  const capsule = style.backgroundColor === "rgba(0, 0, 0, 0)" && style.backgroundImage === "none" &&
    style.borderColor === "rgb(255, 255, 255)" && style.borderStyle === "solid" && parseFloat(style.borderWidth) >= 1 &&
    parseFloat(style.borderRadius) >= button.height / 2 && button.height >= 44;
  const facts = root.querySelector(".gaia-facts").getBoundingClientRect();
  const full = [...root.querySelectorAll(".gaia-backdrop, video")].every(el => {
    const r = el.getBoundingClientRect();
    return r.x === 0 && r.y === 0 && r.width === innerWidth && r.height === innerHeight;
  });
  const video = root.querySelector("video");
  const animated = !!video;
  const framing = !animated || (getComputedStyle(video).objectFit === "cover" &&
    getComputedStyle(video).objectPosition === (root.hasAttribute("data-portrait") ? "22% 50%" : "50% 50%"));
  const besideFacts = button.left > facts.right && Math.abs(button.top + button.height / 2 - facts.top - facts.height / 2) < 1;
  const belowFacts = button.top > facts.bottom && Math.abs(facts.left - button.left) < 1;
  const aboveFacts = button.bottom < facts.top && Math.abs(facts.left - button.left) < 1;
  const lowerLeft = facts.left < innerWidth * .15 && button.y > innerHeight * .55 &&
    (besideFacts || belowFacts || aboveFacts) && innerHeight - Math.max(facts.bottom, button.bottom) < innerHeight * .13;
  const clean = getComputedStyle(root).backgroundImage === "none" && getComputedStyle(backdrop).maskImage === "none";
  if (!full || !framing || !lowerLeft || !clean || !oneLine || !capsule || cta.textContent.trim() !== "PROJECT GAIA" ||
      root.querySelectorAll(".gaia-facts li").length !== 3 ||
      /Bailando con los SARs|NASA Space Apps 2026|El radar NISAR ve|Entrar a la Tierra/i.test(root.innerText)) {
    throw new Error(JSON.stringify({ full, framing, lowerLeft, clean, oneLine, capsule, title: cta.innerText }));
  }
  if (animated && (video.hasAttribute("poster") || getComputedStyle(backdrop).backgroundImage !== "none")) {
    throw new Error("Una imagen se interpone durante el video");
  }
  return { video_a_pantalla_completa: full, capsula_transparente: capsule, boton: [Math.round(button.x), Math.round(button.y)], nombre: cta.textContent.trim() };
};

// Las dos propuestas se fotografían sobre el mismo póster, una vez cargadas las
// fuentes y el fondo. El parámetro de vista previa también funciona en la portada animada.
async function compareTitles() {
  for (const [name, width, height] of [["1440x900", 1440, 900], ["390x844", 390, 844]]) {
    const page = await browser.newPage();
    await page.setViewport({ width, height, deviceScaleFactor: 1 });
    await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
    for (const title of ["orbital", "editorial"]) {
      await page.goto(URL + "?portada=" + title, { waitUntil: "domcontentloaded" });
      await page.waitForSelector('.gaia-cta', { visible: true });
      await page.evaluate(checkLayout);
      const check = await page.evaluate(async () => {
        await document.fonts.ready;
        const frame = document.querySelector(".gaia-backdrop");
        const poster = new Image();
        poster.src = getComputedStyle(frame).backgroundImage.slice(5, -2);
        await poster.decode();
        return {
          title: document.querySelector(".gaia").dataset.title,
          font: getComputedStyle(document.querySelector(".gaia-title-main")).fontFamily,
          poster: [poster.naturalWidth, poster.naturalHeight],
          videos: document.querySelectorAll("video").length,
          overflow: document.querySelector(".gaia").scrollWidth > innerWidth,
          facts: document.querySelectorAll(".gaia-fact").length,
          entries: document.querySelectorAll('h1 button.gaia-cta').length,
        };
      });
      if (check.title !== title || check.videos || check.overflow || check.facts !== 3 || check.entries !== 1)
        throw new Error(JSON.stringify(check));
      const file = `titulo_${title}_${name}.png`;
      await page.screenshot({ path: path.join(OUT, file) });
      console.log(file, JSON.stringify(check));
    }
    await page.close();
  }
}
if (process.argv.includes("--titulos")) {
  try { await compareTitles(); } finally { await browser.close(); }
  process.exit(0);
}

const report = {};
for (const [name, width, height] of [["2560x1440", 2560, 1440], ["1440x900", 1440, 900], ["390x844", 390, 844]]) {
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
  if (r.capturas.some(s => s.entrada_visible)) throw new Error("La entrada apareció antes del amanecer");
  await until(() => document.querySelector(".gaia-head").dataset.entry === "reveal");
  await shot("entrada");
  await until(() => document.querySelectorAll("video")[1]?.style.opacity === "1"); await shot("6s");
  r.secuencia = await page.evaluate(() => window.__entrada);
  const cue = r.secuencia.find(s => s.evento === "revelar")?.video;
  if (!(cue >= 4.5 && cue < 6) || !r.secuencia.some(s => s.evento === "gaia-label-in") ||
      r.secuencia.filter(s => s.evento === "gaia-settle").length !== 4) throw new Error(JSON.stringify(r.secuencia));
  r.encuadre = await page.evaluate(checkLayout);
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
  for (let i = 0; i < 4; i++) {
    if (await page.evaluate(() => document.activeElement?.classList.contains("gaia-cta"))) break;
    await page.keyboard.press("Tab");
  }
  r.foco = await page.evaluate(() => { const a = document.activeElement; const c = getComputedStyle(a); return { el: a.className, outline: `${c.outlineWidth} ${c.outlineStyle}` }; });
  if (!r.foco.el.includes("gaia-cta")) throw new Error("El teclado no alcanzó PROJECT GAIA");
  await page.keyboard.press("Enter");
  await sleep(4000);
  r.tras_entrar = await page.evaluate(() => ({ portada: !!document.querySelector(".gaia"), lienzo_globo: document.querySelectorAll("canvas").length, menu: !!document.querySelector(".rail") }));
  await page.screenshot({ path: path.join(OUT, `portada_${name}_globo.png`) });
  r.errores_js = errors;
  if (errors.length || r.desborde_horizontal || r.tras_entrar.portada ||
      !r.tras_entrar.lienzo_globo || !r.tras_entrar.menu) throw new Error(JSON.stringify(r));
  await page.close();
}

// movimiento reducido: solo póster, todo visible, sin video
{
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await page.goto(URL, { waitUntil: "networkidle2" });
  await sleep(500);
  report.movimiento_reducido = await page.evaluate(() => ({ videos: document.querySelectorAll("video").length,
    entrada: document.querySelector(".gaia-head").dataset.entry,
    animaciones: document.querySelector(".gaia-head").getAnimations({ subtree: true }).length,
    poster: getComputedStyle(document.querySelector(".gaia-backdrop")).backgroundImage.includes("gaia-poster"),
    titulo_opacidad: getComputedStyle(document.querySelector(".gaia-title")).opacity }));
  if (!report.movimiento_reducido.poster || report.movimiento_reducido.videos ||
      report.movimiento_reducido.titulo_opacidad !== "1" || report.movimiento_reducido.entrada !== "ready" ||
      report.movimiento_reducido.animaciones) throw new Error("Portada estática incompleta");
  await page.screenshot({ path: path.join(OUT, "portada_1440x900_movimiento_reducido.png") });
  await page.close();
}
{
  const page = await browser.newPage();
  await page.goto(URL);
  await page.click(".gaia-skip");
  await page.waitForFunction(() => document.querySelectorAll("video")[1].currentTime > 0.2);
  report.saltar_intro = await page.evaluate(() => ({
    intro_pausada: document.querySelector("video").paused,
    foco_entrada: document.activeElement.classList.contains("gaia-cta"),
    salto_oculto: !document.querySelector(".gaia-skip"),
    entrada_inmediata: document.querySelector(".gaia-head").dataset.entry === "ready",
  }));
  if (!report.saltar_intro.intro_pausada || !report.saltar_intro.foco_entrada ||
      !report.saltar_intro.salto_oculto || !report.saltar_intro.entrada_inmediata)
    throw new Error("Saltar intro no completó el paso al bucle");
  await page.close();
}
await browser.close();
fs.writeFileSync(path.join(OUT, "informe.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
