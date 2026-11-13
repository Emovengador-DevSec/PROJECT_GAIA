# 09 · Relevo: portada PROJECT GAIA (para continuar con otro agente)

Estado al 12 de noviembre de 2026. Lee antes `docs/08_Portada_Project_Gaia.md` (cómo está hecha) y `CLAUDE.md` / `AGENTS.md` (reglas del proyecto).

## Estado que entregó la versión 2
- La **versión 2** de la portada está completa y funcionando en `http://localhost:5173` (servidor: `npm --prefix apps/web run dev`).
- **Git**: rama `feat/portada-gaia`. El único commit (`c0b1d37`) contiene la versión 1. **Toda la versión 2 está sin confirmar** en el árbol de trabajo.
- Blender 5.2 tiene abierta `art/blender/gaia.blend` con la animación horneada. Complemento MCP en `127.0.0.1:9876`; el servidor para Codex ya existe en `C:\Users\USUARIO\.codex\integrations\blender-mcp\`.
- ffmpeg y Chrome están instalados. Los cuadros renderizados están en `art/render/h` y `art/render/v` (480 por formato, fuera de Git).

## Observaciones recibidas sobre la versión 2

La revisión se completó en la versión 3. La composición elegida utiliza Bricolage Grotesque. La escena vigente y las capturas se describen en [la guía de la portada](08_Portada_Project_Gaia.md#portada-actual).

Los cinco puntos originales se conservan como referencia histórica.
1. **Franja arcoíris sobre la Tierra**: no le gusta. Quitarla o cambiarla por algo sobrio (una franja cian tenue con líneas de barrido). Es el objeto `Franja` y el material `M_Franja` en `build_beam()` de `tools/blender/build_gaia_scene.py`.
2. **Luz naranja muy fuerte**: el resplandor cálido alrededor del sol. En `build_sky()` el disco `M_Sol` usa color `(1.0, 0.86, 0.66)`; en `build_compositor()` el resplandor tiene `Saturation = 1.25`. Probar sol blanco neutro, saturación 1.0 y menos fuerza. Revisar también el naranja del terreno (saturación 1.35 en `build_earth()`) y el tono cálido del halo cerca del terminador.
3. **Títulos**: no le gustan. Rediseñar tipografía y composición en `apps/web/src/features/gaia/gaia.css` y `GaiaCover.tsx` (hoy: Big Shoulders Display, «PROJECT» en contorno y «GAIA» sólido, acento ámbar). Proponerle 2 opciones con captura antes de dar una por buena. Considerar cambiar el acento ámbar por un cian frío.
4. **Astronauta sin animación**: hoy solo deriva y gira unos grados. Quiere que se note vivo. El modelo (`art/models/nasa_emu/EMU.glb`) no tiene esqueleto. Ver «Notas del astronauta» abajo.
5. **Todo borroso**: sigue viéndolo blando. Ver «Nitidez» abajo.

## Notas del astronauta (análisis ya hecho, sin cambios aplicados)
- Objeto `Astronauta_Malla`, 442 172 vértices, hijo del vacío `Astronauta`. En coordenadas locales de la malla: **arriba = +Y** (pies en y ≈ −1,61, casco hasta y ≈ 0,40), **frente = −Z**, derecha/izquierda = ±X.
- La malla son **70 islas sueltas** (piezas no conectadas), así que se pueden girar piezas rígidas sin romper nada. Islas útiles (centro aproximado en local):
  - Brazos (material de traje): centros `(−0,39, −0,27, −0,10)` y `(0,39, −0,27, 0,11)`, unos 13 600 vértices cada uno.
  - Guantes/antebrazos: centros `(−0,27, −0,43, −0,41)` y `(0,43, −0,43, −0,22)`, unos 7 500 vértices cada uno.
  - Piernas y botas: una sola isla de 35 661 vértices.
  - Cascos/visor: dos islas de ~130 000 vértices cerca de y ≈ 0,3.
- Idea más barata: claves de forma (shape keys) que giren las islas de un brazo alrededor del hombro (≈ `(±0,25, −0,05, 0)`) y animarlas con la curva `_breath()` de `animate_gaia.py`. Además, subir mucho la deriva y el giro del cuerpo en el bloque «astronauta» de `animate()`.
- El modelo no es simétrico (los brazos descansan sobre los mandos de la mochila); al mover un brazo se separa del mando. Revisar con `look` antes de renderizar.

## Nitidez (hipótesis, por probar)
- El WebM se codifica con `crf 33` (bucle) para quedar bajo 8 MB. Subir calidad en `tools/blender/encode_gaia.sh` (por ejemplo x264 `crf 20`, VP9 `crf 28`) aunque supere 8 MB, y decírselo al usuario.
- En `gaia.css`, `.gaia-backdrop` tiene `inset: -1.5%` y un `translate3d` de paralaje: eso reescala el video. Probar `inset: 0` y sin transformar el fondo.
- Las cámaras tienen profundidad de campo (`aperture_fstop = 8`): probar a desactivarla. El filtro de película está en `filter_size = 1.1`.
- La pantalla del usuario mide unos 2000 px CSS de ancho; el video es de 2560×1440.

## Cómo rehacer el ciclo completo
```python
# dentro de Blender (MCP execute_blender_code); cada llamada pierde el espacio de nombres
exec(open(r"C:\Users\USUARIO\Desktop\GAIA\tools\blender\build_gaia_scene.py", encoding="utf-8").read(), globals())
exec(open(r"C:\Users\USUARIO\Desktop\GAIA\tools\blender\animate_gaia.py", encoding="utf-8").read(), globals())
build(); animate()
render_still(r"<ruta>.png", 50, 32)      # prueba rápida al 50 %
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\USUARIO\Desktop\GAIA\art\blender\gaia.blend")
```
```bash
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
"$BL" -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- h   # ~17 min, 2560x1440
"$BL" -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- v   # 1080x1920, sin astronauta
bash tools/blender/encode_gaia.sh        # MP4 + WebM + pósteres a apps/web/public/media
bash tools/audio/make_gaia_ambient.sh    # solo si se cambia el sonido
npm --prefix apps/web run build
```
Verificación con Chrome sin interfaz: `tools/verify/verificar_portada.mjs` (necesita `npm i puppeteer-core` en una carpeta aparte y el servidor en :5173). Comprueba el encuadre del video, la posición y el contraste de la entrada y el acceso al globo.

## Trampas ya conocidas
- **Sombras**: la Tierra y las nubes no deben proyectar sombra (`visible_shadow = False`); si no, cada cuadro pasa de 1 s a 18 s.
- **Video en rango completo** rompe el VP9 en Chromium; `encode_gaia.sh` ya convierte a rango de video.
- **Luces de área** llevan `cutoff_distance = 7` para no iluminar la Tierra.
- **Rangos invertidos** en nodos Map Range con interpolación suave no funcionan bien; se invierte el valor antes.
- El servidor `eoimages.gsfc.nasa.gov` no responde desde esta red; las texturas salen de `assets.science.nasa.gov` (rutas en `art/CREDITOS.md`).
- El panel de navegador integrado a veces no dibuja (ventana tapada); por eso la verificación usa Chrome sin interfaz.
- No usar logotipo ni insignia de la NASA. Los parches de bandera y emblema del traje se quitan en `build_astronaut()`.

## Sin comprobar
- Nadie ha escuchado el sonido ambiente (`gaia-ambient.ogg`); solo se verificó que se decodifica y que el botón cambia de estado.
- 60 fps en pantalla real y el tiempo del póster en la red del evento.
