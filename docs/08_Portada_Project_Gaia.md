# 08 · Portada PROJECT GAIA

La portada reproduce «Amanecer orbital», un video renderizado en Blender. Después del amanecer aparece «PROJECT GAIA», el botón que abre el globo Cesium.

El 13 de noviembre se eliminaron las secuencias intermedias de 480 fotogramas por formato de las versiones anteriores y de la versión 4, junto con tres grabaciones de prueba, para liberar 6,41 GB. Los videos publicados siguen en `apps/web/public/media/`. Para volver a codificarlos desde PNG, primero hay que regenerar los fotogramas con `render_gaia.py` y después ejecutar `encode_gaia.sh`.

## Dónde está cada cosa
| Ruta | Contenido |
|---|---|
| `apps/web/src/features/gaia/GaiaCover.tsx` · `gaia.css` | Componente y estilos de la portada |
| `apps/web/src/app/App.tsx` | Monta la portada; precarga el globo (trozo aparte) y lo revela al entrar |
| `apps/web/public/media/` | `gaia-intro` (6 s) y `gaia-loop` (10 s) en `.webm` y `.mp4`, versiones `-v` verticales y pósteres `.jpg` |
| `apps/web/public/models/nisar.glb` | Modelo Draco del satélite NISAR |
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
export_asset("NISAR", "nisar.glb")
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
| 0 – 3 s | La cámara gira desde las estrellas hacia la Tierra de noche |
| 3,3 s | El Sol asoma por el horizonte y empieza la precarga del globo |
| 4,5 s | La cápsula asciende suavemente, se revela el nombre «PROJECT GAIA» y entran los tres indicadores en secuencia |
| 2,2 – 5 s | NISAR baja a su posición; el haz se despliega de 4,5 a 5,6 s |
| Bucle de 10 s | Deriva de cámara, el sol «respira» y el haz barre la costa; sin corte |

## Comportamiento
- La introducción ocupa toda la ventana con el encuadre centrado en horizontal. En pantallas verticales de hasta 900 px se usa el archivo `-v` y su encuadre original.
- «PROJECT GAIA» y los tres indicadores están en la esquina inferior izquierda. El nombre completo, en una línea, es el botón de entrada. La aparición sigue el tiempo de reproducción de la introducción y se ejecuta una sola vez. Con «Saltar intro» la entrada queda visible y recibe el foco de inmediato.
- La vista estática muestra el póster y la entrada al instante si se solicita movimiento reducido o falla la reproducción. Los créditos se consultan desde el botón de información.

## Verificación de la primera versión
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

## Pendientes registrados en la primera versión
- Nubes procedurales (el mapa de nubes de la NASA no se pudo descargar).
- El astronauta de la NASA viene en pose rígida; en vertical se ocultó.
- Capa interactiva three.js con los `.glb`: no construida; el paralaje actual es por CSS.

## Versión 2 (rehecha tras la revisión visual)
Sustituye a lo descrito arriba donde haya diferencia.

- **Tierra**: media luna de día (océano azul, nubes) y lado nocturno con luces de ciudades. El disco del sol se ve en el limbo, pero la Tierra se ilumina desde un ángulo más abierto (`EARTH_SUN_DIR`): es un truco de cine para tener color.
- **Atmósfera**: bruma y halo azules sin línea dura en el borde.
- **Haz de radar**: cono translúcido con frentes de onda que viajan al suelo (nodo `FASE`) y una franja de interferometría de unos 240 km sobre la costa del Perú (nodos `CABEZA` y `VISIBLE`).
- **Astronauta**: traje EMU de NASA 3D Resources, de frente, sin parches de bandera ni emblema. En vertical sigue oculto.
- **Rocas y meteoros**: 7 rocas que giran vueltas enteras por bucle y 3 meteoros sobre el lado nocturno.
- **Render**: 2560×1440 (horizontal) y 1080×1920 (vertical), 64 muestras, unos 2 s por cuadro con dos procesos a la vez.
- **Sonido**: `gaia-ambient.ogg` / `.m4a`, bucle de 32 s sintetizado con `tools/audio/make_gaia_ambient.sh`. Lo reproduce `useAmbientSound.ts` con Web Audio; arranca con el primer clic o tecla (los navegadores lo exigen) y se silencia con el botón de arriba a la derecha. Se apaga al entrar al globo.
- **Interfaz**: los tamaños crecen con la pantalla (probado a 2560×1440).

### Verificación de la versión 2
| Comprobación | 2560×1440 | 1440×900 | 390×844 |
|---|---|---|---|
| Contraste mínimo del texto (objetivo ≥ 4,5:1) | 5,3:1 | 4,5:1 | 7,9:1 |
| Saltos de diseño (CLS) | 0,001 | 0,004 | 0,012 |
| Cuadros de video perdidos en el bucle | 3 | 0 | 0 |
| «Entrar a la Tierra» abre el globo | Sí | Sí | Sí |
| Errores de JavaScript | 0 | 0 | 0 |

El sonido se comprobó solo en estado (el archivo se decodifica, dura 32 s y el botón cambia a «Silenciar»); nadie lo ha escuchado todavía.

## Versión 3

La versión 3 conserva las cámaras y los tiempos de la versión 2. El haz ilustra el barrido sobre Perú con pulsos cian. La costa queda visible bajo una luz solar neutra. La textura diurna se deriva del Blue Marble original a 16384 × 8192 px. Las dos cámaras mantienen en foco el primer plano y la Tierra. El fondo ocupa el tamaño de la ventana con el recorte necesario para su proporción.

En horizontal, el astronauta giraba el casco, levantaba la mano derecha hacia el visor y volvía al mando. El reposo en el cuadro 181 y el alcance en el 331 se conservan en `art/render/v3/gaia.blend`. La cámara vertical reservaba el encuadre para NISAR y Sudamérica. Los PNG de `art/render/v3/{h,v}` son los originales de esa versión.

El título elegido es «Gaia» en Bricolage Grotesque, con «Project» en una línea pequeña. La propuesta en Instrument Serif sigue disponible en `/?portada=editorial`. Las capturas `art/verificacion/titulo_*.png` permiten comparar ambas sobre el mismo fotograma. Las fuentes se sirven con el proyecto.

La codificación usa CRF 19 para H.264 y CRF 26 para VP9. El bucle horizontal pesa 11,94 MB en MP4 y 10,71 MB en WebM. La comparación del cuadro 331 contra el PNG original dio SSIM 0,990 en horizontal y 0,992 en vertical para VP9.

### Verificación del 12 de noviembre

Chrome reprodujo los videos nuevos y abrió el globo mediante teclado en 2560 × 1440, 1440 × 900 y 390 × 844. El informe registró cero errores de JavaScript, foco visible y ausencia de desbordamiento horizontal en los tres tamaños. El contraste más bajo de las muestras del bucle fue 6,3 a 1. La compilación de producción terminó correctamente.

Los ocho archivos de video contienen 180 cuadros de introducción o 300 de bucle a 30 fps. La verificación adicional cubrió el modo de movimiento reducido, el póster cuando falla la descarga de video, MP4 y seis tamaños desde 320 × 568 hasta 1024 × 600. Los resultados completos están en `art/verificacion/informe.json`, `videos.json` y `comprobaciones_adicionales.json`.

La API local responde con cero capas publicadas y teselas desactivadas. La entrada al globo muestra los estados vacíos que corresponden a ese catálogo.

## Portada actual

El satélite NISAR y Sudamérica ocupan los dos encuadres de la versión 4. Se retiraron el astronauta, su animación y sus luces del archivo de Blender. La textura Blue Marble en 16K recibe luz lateral sobre el continente. Una capa exterior del 1,8 % del radio terrestre delimita la atmósfera. Un pase exclusivo del Sol genera los seis rayos del destello cuando asoma tras el planeta.

El video de la intro y el bucle cubren la ventana de borde a borde. El fondo animado procede de los PNG de `art/render/v4/{h,v}`. Después del amanecer aparece una cápsula transparente con borde blanco en la esquina inferior izquierda. «PROJECT GAIA» y la flecha comparten una línea dentro del botón ampliado. A la izquierda del botón figuran tres círculos separados con el radar NISAR en banda L, su longitud de onda aproximada de 24 cm y su repetición de 12 días. Los aros blancos exteriores giran una vuelta cada 14 s mientras el contenido permanece fijo. Con movimiento reducido los aros se muestran estáticos.

El botón se sitúa a la derecha de los tres círculos, centrado verticalmente con ellos. En teléfonos verticales, el botón ocupa todo el ancho disponible y los tres círculos, más compactos, se centran debajo. El icono de información tiene su propio espacio sobre el grupo. En otros formatos estrechos, el botón pasa debajo de los indicadores cuando la fila necesita ajustarse.

El verificador de Chrome registra el instante de aparición, la secuencia de animaciones, el contraste y el acceso con teclado en 2560 × 1440, 1440 × 900 y 390 × 844. También comprueba el movimiento reducido y el salto de la introducción. Las medidas están en `art/verificacion/informe.json`.
