# 08 · Portada PROJECT GAIA

Portada que se muestra antes del globo: un video renderizado en Blender (dirección de arte
«Amanecer orbital») con la interfaz encima. Al pulsar «Entrar a la Tierra» se abre el globo Cesium.

## Dónde está cada cosa
| Ruta | Contenido |
|---|---|
| `apps/web/src/features/gaia/GaiaCover.tsx` · `gaia.css` | Componente y estilos de la portada |
| `apps/web/src/app/App.tsx` | Monta la portada; precarga el globo (trozo aparte) y lo revela al entrar |
| `apps/web/public/media/` | `gaia-intro` (6 s) y `gaia-loop` (10 s) en `.webm` y `.mp4`, versiones `-v` verticales y pósteres `.jpg` |
| `apps/web/public/models/` | `nisar.glb` y `astronauta.glb` (Draco), listos para una capa 3D interactiva |
| `art/blender/gaia.blend` | Escena de Blender con la animación horneada |
| `art/frames/` | Cuadros clave aprobados (A: portada, B: haz sobre Perú) |
| `art/verificacion/` | Capturas e `informe.json` de la verificación |
| `art/CREDITOS.md` | Fuente, licencia y tamaño de cada recurso |
| `art/textures/`, `art/render/` | Texturas y cuadros renderizados (fuera de Git) |
| `tools/blender/` | Scripts reproducibles (ver abajo) |

## Cómo regenerar todo
Con Blender 5.x abierto y el servidor MCP conectado, o desde su consola de Python:

```python
exec(open(r"tools/blender/build_gaia_scene.py", encoding="utf-8").read())   # escena y materiales
exec(open(r"tools/blender/animate_gaia.py", encoding="utf-8").read())       # intro + bucle
build(); animate()                                                           # luego guardar gaia.blend
exec(open(r"tools/blender/export_gaia_asset.py", encoding="utf-8").read())
export_asset("NISAR", "nisar.glb"); export_asset("Astronauta", "astronauta.glb")
```

Render por lotes y codificación (480 cuadros por formato, unos minutos en EEVEE):

```bash
blender -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- h
blender -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- v
bash tools/blender/encode_gaia.sh
```

Las texturas se descargan de las direcciones de `art/CREDITOS.md` a `art/textures/`.

## Línea de tiempo (30 fps)
| Tramo | Qué pasa |
|---|---|
| 0 – 3 s | Estrellas; la cámara gira hacia la Tierra de noche |
| 3,3 s | El sol asoma por el limbo y entra el título |
| 4,2 · 4,9 · 5,5 s | Subtítulo, insignias y botón «Entrar a la Tierra» |
| 2,2 – 5 s | NISAR baja a su posición; el haz se despliega de 4,5 a 5,6 s |
| Bucle de 10 s | Deriva de cámara, el sol «respira» y el haz barre la costa; sin corte |

Los tiempos de la interfaz están en `CUES` (`GaiaCover.tsx`) y se leen del tiempo real del video.

## Comportamiento
- **Carga**: el póster se pinta primero; el video carga después. Cesium va en un trozo aparte.
- **Móvil**: en vertical (ancho ≤ 900 px) usa los videos `-v` y el título va arriba.
- **Movimiento reducido**: solo el póster, sin video ni animación, con todo el texto visible.
- **Si el video falla** o el navegador bloquea la reproducción: póster e interfaz completa.
- **Teclado**: «Saltar intro» durante la intro; el foco pasa al botón principal cuando aparece.
- **Créditos**: «Datos: misión NISAR (NASA-ISRO)». Sin logotipo ni insignia de la NASA.

## Verificación (Chrome sin interfaz, servidor de desarrollo local)
| Comprobación | 1440×900 | 390×844 |
|---|---|---|
| Capturas a 0,5 s, 3 s, 6 s y en bucle | `art/verificacion/portada_1440x900_*.png` | `art/verificacion/portada_390x844_*.png` |
| Contraste mínimo del texto sobre el video (objetivo ≥ 4,5:1) | 6,3:1 (etiquetas de insignias) | 7,2:1 (etiquetas de insignias) |
| Saltos de diseño (CLS, bueno < 0,1) | 0,003 | 0,005 |
| Cuadros de video perdidos en el bucle | 2 de ~540 | 0 de ~530 |
| Desborde horizontal | No | No |
| Foco visible en el botón | 3 px sólido | 3 px sólido |
| «Entrar a la Tierra» abre el globo | Sí | Sí |
| Errores de JavaScript | 0 | 0 |

Con movimiento reducido: 0 videos en la página y título visible desde el primer cuadro.

### Límites de esta verificación
- El contraste se calcula sobre el cuadro del video con el velo aplicado, no con una herramienta de auditoría.
- Los 60 fps no se pudieron medir sin pantalla real (sin interfaz, el navegador no limita los cuadros). El video es de 30 fps.
- El tiempo del póster (menos de 0,1 s) es en local; falta medirlo en la red del evento.
- Las tipografías vienen de Google Fonts: sin internet, el título usa la fuente de respaldo.

## Pendientes conocidos
- Nubes procedurales (el mapa de nubes de la NASA no se pudo descargar).
- El astronauta de la NASA viene en pose rígida; en vertical se ocultó.
- Capa interactiva three.js con los `.glb`: no construida; el paralaje actual es por CSS.
