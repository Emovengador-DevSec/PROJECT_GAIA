# 13 · Plan final: de prototipo a demo ganadora

Escrito el 13 de noviembre de 2026 (noche), tras revisar el commit `85881fd`. Manda sobre los planes 10 y 11 donde haya diferencia.
Estado: las tres claves (Earthdata, Cesium ion, FIRMS) están configuradas; los momentos W1–W8 están hechos.

### Ejecución de Codex del 13 de noviembre

- G1 publicado con trayectoria 147, 24-jun y 10-oct, 4,16 GB y cobertura válida común del 99,91 %. Se eligió 10-oct para conservar P05023 en ambas fechas. El 22-oct existe en la colección validada con otra versión de procesamiento.
- G4 implementado y verificado en Chrome a 2560, 390 y 320 px. El valor inicial es Siempre de día y el selector permite Hora real.
- G2 publicado para las 1.106 manchas activas con WorldPop, WorldCover y 1.192 localidades OSM. Las categorías WorldCover reconcilian el área de cada mancha y WorldPop conserva su cobertura parcial.
- G3 publicado con total HV del manifiesto, área delimitada aparte y contraste OPERA original. Coinciden 21,08 ha, el 2,25 % de las manchas HV, con intersección/unión del 0,80 %. La atribución a incendios continúa por verificar.
- G7 tiene guion, relato actualizado y video de respaldo de 2 min 38 s en `art/verificacion/gaia-alerta-demo.mp4`. El modo sin conexión pasó la verificación con el par nuevo en PC y teléfono.
- G9 implementado y verificado en PC y teléfono con la API apagada. La foto incluye 2.840 teselas y conserva 2.145 observaciones con fuente y fecha. La compilación contiene 3.276 archivos y 342,3 MB, dentro de los límites revisados de Pages. Las cuatro zonas y la cortina pasaron con cero llamadas a `/api`, errores JavaScript y respuestas 404. El modo live también pasó la comprobación. La guía está en `docs/14_Publicacion.md`.
- G8 tiene texto de entrega y auditoría local. Quedan pendientes verificar la guía oficial 2026, accesible desde Resources, y la publicación del repositorio/envío desde la cuenta del equipo. El detalle está en `docs/14_Entrega_Demo.md`.
- G5 requiere cuatro fechas y continúa sujeto al límite vigente de dos descargas GCOV. G6 sigue pendiente de la selección e inspección GUNW.

La revisión independiente de seguridad de G9 terminó sin hallazgos bloqueantes. Los JSON
y sus hashes se comprobaron contra el manifiesto. El bundle estático excluye el token
Cesium del usuario y conserva el token público predeterminado de la propia dependencia.
npm y pip-audit informaron cero vulnerabilidades conocidas. La suite completa terminó
con 52 pruebas aprobadas. El repositorio todavía carece de remoto configurado, por lo
que la conexión a GitHub y la cuenta de alojamiento siguen pendientes de la persona del equipo.

## Lo que se revisó y lo que falla

| Hallazgo | Evidencia | Gravedad |
|---|---|---|
| **El análisis NISAR de Ayacucho cubre casi nada** | `timeseries.json`: `valid_pct` 1,7 %. La trayectoria 75, cuadro 171, solo toca el 14–16 % de la caja de estudio | **Crítica**: el número principal (52,76 ha) sale de menos del 2 % de la zona |
| Hay datos que cubren la zona entera | Catálogo ASF (consultado hoy): trayectoria **147 ascendente, cuadro 171** y trayectoria **54 descendente, cuadro 95** cubren el **100 %** de la caja, con 11 fechas cada una entre junio y noviembre de 2026 | Solución lista |
| «¿A quién afecta?» está vacío | `data/04_published/exposure/ayacucho-huanta.json` tiene `sources: {}` y `alerts: {}`, aunque `worldpop.tif` y `worldcover.tif` ya están descargados | Alta |
| La cifra destacada confunde | La tarjeta «Lo más importante» de NISAR muestra **2,0 ha** (la mancha más grande); el total con caída de HV es **52,76 ha** en 5 manchas | Media |
| Serie de tiempo con 2 fechas | La tendencia sigue desactivada (necesita 4) | Media |
| **Sudamérica se ve de noche** | La iluminación usa la hora real: en la demo, según la hora, Perú queda en el lado oscuro y la imagen satelital no se ve | Alta para la presentación |
| Sabancaya sin deformación | No hay GUNW procesado; la historia del volcán está incompleta | Media |
| Cambios sin confirmar en Git | `astronauta.glb` borrado y `nisar.glb` y `gaia.blend` modificados fuera de un commit | Revisar si es intencional |

## Fases

Cada fase termina con `npm --prefix apps/web run build`, las pruebas, capturas y un commit propio.

### G1 · Datos NISAR que cubran Ayacucho (prioridad máxima)
- Cambiar el caso a la **trayectoria 147 ascendente, cuadro 171**. Las fechas disponibles son: 24-jun, 06-jul, 18-jul, 11-ago, 23-ago, 04-sep, 16-sep, 28-sep, 10-oct, 22-oct y 03-nov de 2026.
- Elegir **4 fechas**:
  - **24-jun:** antes de la temporada de incendios.
  - **23-ago y 16-sep:** durante la temporada.
  - **22-oct:** después.

  Antes de decidir, mirar los focos FIRMS de esos meses en la zona y mover las fechas para que una caiga justo después del pico de incendios.
- Son ~8 GB: **pedir permiso** (regla de 5 GB). Como mínimo, 2 fechas (24-jun y 22-oct), ~4 GB.
- Proponer borrar los dos GCOV de la trayectoria 75 (~3,9 GB) para liberar espacio; **no borrar sin permiso**.
- `sarlab change` entre la primera y la última fecha; `sarlab timeseries` con las 4.
- Si la trayectoria 54 descendente tiene fechas mejores, también vale; **nunca mezclar trayectorias en una comparación**.
- **Aceptación:** `valid_pct` ≥ 80 % en `timeseries.json`; hectáreas recalculadas; manifiesto con los gránulos nuevos; `docs/data-notes.md` actualizado con lo aprendido (que el cuadro 171 de la trayectoria 75 casi no cubre la zona).

### G2 · «¿A quién afecta?» con números reales
- Calcular la exposición de cada mancha NISAR con `worldpop.tif` (personas), `worldcover.tif` (cultivo, bosque, pastizal) y centros poblados de OpenStreetMap a menos de 2 km.
- Guardar en `exposure/ayacucho-huanta.json` con la fuente, el año y la licencia de cada capa.
- Mostrar en la tarjeta: personas, hectáreas por tipo de cobertura y pueblos cercanos con su distancia.
- **Aceptación:** el JSON deja de estar vacío; una prueba verifica que la suma de hectáreas por cobertura coincide con el área de la mancha.

### G3 · Cifras coherentes y validación
- La tarjeta destacada de NISAR muestra el **total** de la zona («52,76 ha con caída de HV en 5 zonas»); el detalle de cada mancha va dentro.
- Una sola fuente de verdad para cada número (manifiesto → API → interfaz); prueba que compare lo que muestra la interfaz con el manifiesto.
- Concordancia con **OPERA DIST**: porcentaje del área NISAR que OPERA también marca como pérdida de vegetación, con fechas de ambas fuentes.
- Si SAOCOM ya dio acceso y tiene fechas compatibles: misma comparación. Si no, dejar el estado «requiere registro».
- **Aceptación:** en Calidad se ven el área válida, el umbral en dB, el método y la concordancia con OPERA en porcentaje.

### G4 · Luz para la demo
- Interruptor **«Luz: hora real / siempre de día»** en la barra superior. Por defecto, en la demo, «siempre de día» sobre la zona elegida (sol fijo sobre Sudamérica). Con «hora real», el terminador actual.
- Las luces nocturnas se siguen viendo cuando el lado de noche es visible.
- **Aceptación:** a cualquier hora del día se ven los Andes con imagen satelital al abrir la demo.

### G5 · Tendencia (solo si G1 trae 4 fechas)
- Activar la proyección Theil–Sen con su banda y la etiqueta «Proyección si la tendencia sigue igual — no es una predicción».
- **Aceptación:** con 4 fechas válidas se ve la línea, la banda y el método; con menos, sigue desactivada y lo dice.

### G6 · Sabancaya: el volcán que se mueve
- Buscar GUNW de la trayectoria 46 ascendente (26 fechas en el catálogo); **ver el tamaño antes de descargar** y pedir permiso si pasa de 5 GB.
- Confirmar las rutas del GUNW con `sarlab inspect` y anotarlas; crear el lector solo con rutas confirmadas.
- Mostrar el desplazamiento en la línea de visión (cm) sobre el relieve, con su escala.
- Nivel de alerta volcánica oficial citado con fuente y fecha (Observatorio Vulcanológico), nunca calculado por GAIA.
- **Aceptación:** mapa de deformación del volcán en cm con fechas y gránulos.

### G7 · Historia final y guion de la demo (2–3 min)
Guion recomendado:
1. **0:00:** portada y sonido. «Un radar que ve a través de nubes y humo.»
2. **0:15:** el globo vivo: sismos que laten, columnas de calor y NISAR en órbita.
3. **0:35:** ▶ la danza: 30 días de sismos y fuego en su hora real.
4. **0:55:** vuelo a Ayacucho; el barrido revela el radar; cortina antes/después en falso color.
5. **1:20:** la cifra: hectáreas, porcentaje de área válida, concordancia con OPERA.
6. **1:40:** ¿a quién afecta?: personas, cultivos, pueblos; «Compartir alerta».
7. **2:00:** Sabancaya: el suelo del volcán se mueve (si G6 está lista).
8. **2:20:** cierre: lo que NISAR no puede hacer (no predice sismos, no ve fuego) y sus aplicaciones futuras.

Tareas:
- Ajustar la historia de Ayacucho a ese orden.
- Grabar el video de respaldo.
- Comprobar el modo sin conexión con los datos nuevos.

### G8 · Entrega
- Leer la **guía oficial de entrega de Space Apps 2026** (formato del video o de las diapositivas, campos del proyecto, enlace al repositorio) y cumplirla exactamente; no suponer el formato.
- README con capturas, cómo ejecutar, fuentes y licencias; `06_Requisitos_del_Reto.md` actualizado punto por punto.
- Skill `revision-demo` y subagente `security-reviewer`: sin secretos en el repositorio ni en el bundle (salvo el token de Cesium, limitado por dominio).
- Repositorio público en GitHub (lo crea la persona; Codex prepara el contenido).
- Si se publica una web: limitar el token de Cesium a ese dominio y servir los datos procesados estáticos.

### G9 · Publicación: un enlace que el jurado abre al instante
Decisión: **sitio estático con una foto fija de los datos** en Cloudflare Pages o Vercel. Sin servidor que se duerma, sin claves fuera de la PC, gratis y con HTTPS. Se hace **después de G1** para que la foto lleve los datos NISAR que cubren la zona.

Por qué no un servidor ahora: la API usa rasterio, titiler y GDAL (exige Docker), no hay Dockerfile, y los planes gratuitos (Render) se duermen a los 15 min y tardan ~50 s en despertar. Queda como opción futura.

Tareas:
1. **Script de foto** `tools/snapshot_static.py`. Con la API local encendida:
   - Guarda en `apps/web/public/snapshot/` las respuestas de `/api/health`, `/api/config`, `/api/aois`, `/api/layers`, `/api/alerts`, `/api/stories/{zona}`, `/api/timeseries` y `/api/polarizations`, en JSON y por zona.
   - Pre-genera como PNG las teselas de `/api/cog` que necesita cada capa NISAR, solo dentro de la caja de la zona y en los niveles de zoom que usa la interfaz.
   - Escribe `snapshot/manifest.json` con la fecha y hora de la foto, la lista de archivos y su tamaño total.
   - No copia `.env` ni ningún secreto. Falla si algún JSON contiene `token`, `key` o `MAP_KEY` con valor.
2. **Modo estático en la web**:
   - Con `VITE_DATA_MODE=static`, `apps/web/src/lib/api.ts` lee de `/snapshot/...` en vez de `/api/...`. Con `live` (por defecto en local) no cambia nada.
   - Mostrar siempre «Datos actualizados al <fecha y hora> · foto estática» en la barra superior y en Calidad.
3. **Despliegue**:
   - Se construye con `npm --prefix apps/web run build` en modo estático. Los pasos para conectar Cloudflare Pages o Vercel al repositorio (directorio `apps/web`, salida `dist`) van en `docs/14_Publicacion.md`.
   - La cuenta y la conexión las hace la persona; Codex no crea cuentas.
4. **Seguridad**:
   - Token de Cesium limitado al dominio final (por ejemplo `*.pages.dev`), anotado en el documento.
   - `security-reviewer` revisa `dist/` y busca claves en el bundle.
5. **Tamaño**: comprobar que `dist/` cabe en el límite del servicio elegido (consultar el límite oficial, no suponerlo); si un video pesa demasiado, servir solo la versión MP4.

**Aceptación:**
- Con la API apagada, `npx vite preview` en modo estático muestra el globo, las alertas, la historia de Ayacucho con la cortina NISAR y la fecha de la foto.
- No hay ningún error 404 en la consola de la página.
- La búsqueda de secretos en `dist/` da cero resultados.
- La demo en vivo sigue funcionando en modo `live`.

## Orden si falta tiempo
**G1 → G4 → G2 → G3 → G7 → G9 → G8**; G5 y G6 son extras. G9 va antes de G8 porque la entrega pide el enlace.
Sin G1 el número principal no se puede defender ante el jurado.

## Prompt para Codex

```text
Lee CLAUDE.md, AGENTS.md y docs/13_Plan_Final_Codex.md. Empieza por G1: el análisis actual de Ayacucho
usa la trayectoria 75, que cubre solo el 15 % de la caja (valid_pct 1,7 %). Cambia a la trayectoria 147
ascendente, cuadro 171, que la cubre al 100 %. Revisa los focos FIRMS para elegir 4 fechas, muéstrame
la lista con tamaños y ESPERA mi permiso antes de descargar. No borres los archivos de la trayectoria 75
sin preguntarme. Después sigue con G4, G2, G3, G7, G9 (sitio estático con foto de datos, sin
servidor ni secretos) y G8, un commit por fase, mostrando build, pruebas y capturas. Antes de empezar, dime si borrar astronauta.glb fue intencional.
```
