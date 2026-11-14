# 11 · Experiencia interactiva: que GAIA Alerta asombre

Escrito el 13 de noviembre de 2026 tras revisar la versión de Codex (commit `301b107`).
Complementa `10_Plan_GAIA_Alerta_Codex.md`. Las reglas de `CLAUDE.md` siguen vigentes: todo lo que se anima son **datos reales con su hora real**.

## Diagnóstico: por qué se siente estática

| Lo que pasa | Causa en el código |
|---|---|
| Nada se mueve al abrir | El globo no gira, no hay vuelo de llegada y ninguna entidad está animada: no se usa `CallbackProperty` ni el reloj de Cesium |
| Los marcadores son cuadritos amarillos con números | Agrupación (`clustering`) por defecto; todos los tipos se ven iguales |
| Pasar el ratón no hace nada | Solo hay evento `LEFT_CLICK`; no hay `MOUSE_MOVE` ni resaltado ni tooltip |
| La lista de alertas es un muro | 420 filas casi idénticas («Foco de calor VIIRS · Perú · Media») sin agrupar ni priorizar |
| El tiempo no existe | Sismos y focos de 30 días se muestran todos a la vez; no hay forma de verlos ocurrir |
| La estrella del reto no aparece | No hay capa NISAR procesada (falta `EARTHDATA_TOKEN`); solo se ven USGS y FIRMS, que son complementarios |
| Imagen borrosa al acercarse | Sin token de Cesium ion usa NASA GIBS Blue Marble, que llega solo al nivel 8 (~600 m por píxel) |
| Letra diminuta en pantallas grandes | Tamaños fijos de 11–14 px en `tokens.css` y en los paneles |
| Borde punteado blanco en el limbo izquierdo | Por investigar (atmósfera o borde de teselas) |

## Los 8 momentos que deben existir

Cada uno con lo que ve la persona, cómo se hace y cómo se comprueba. **Antes de usar cualquier API de Cesium, confirmarla en la documentación oficial (Context7 o cesium.com/docs).**

### W1 · Llegada: la Tierra está viva (sin tocar nada)
- **Se ve:** el globo gira lento sobre el espacio; en 3–4 s la cámara se acerca a Sudamérica; los contadores de arriba cuentan hacia arriba («109 sismos · 420 focos · 2 cambios NISAR»); las alertas aparecen una a una con una onda.
- **Cómo:** rotación por `scene.preRender` o `clock.onTick` que se detiene al primer gesto y vuelve tras 20 s sin uso; `camera.flyTo` con `EasingFunction`; contador animado en React (framer-motion ya está instalado).
- **Prueba:** abrir la app sin tocar nada durante 10 s: algo se mueve todo el tiempo y al final se entiende dónde está pasando algo.

### W2 · Marcadores vivos, distintos por tipo
- **Sismos:** anillos que se expanden como ondas sísmicas, radio según magnitud, se desvanecen y repiten; los más recientes laten más rápido. (`ellipse` con `semiMajorAxis` y color en `CallbackProperty`.)
- **Fuego (FIRMS):** **no 420 alfileres**. Agrupar en celdas hexagonales de ~10 km en la API y dibujarlas como **columnas 3D extruidas** (altura = número de focos, color = cuán reciente). Sobre los Andes se ve como un mapa de calor en 3D. (`polygon.extrudedHeight`.) Al acercarse, se ven los focos individuales con un brillo que titila.
- **NISAR:** la mancha real del cambio pegada al relieve, con un borde que respira.
- Iconos con forma distinta además del color (paleta de la sección 4 del plan 10).
- **Prueba:** captura de Sudamérica donde se distinguen los tres tipos sin leer la leyenda.

### W3 · Respuesta al pasar el ratón
- **Se ve:** el marcador bajo el cursor crece y brilla; aparece una tarjetita junto al cursor con qué, dónde, cuándo y fuente; el cursor cambia a mano.
- **Cómo:** `ScreenSpaceEventType.MOUSE_MOVE` con `scene.pick`, limitado a 1 consulta cada 50 ms.
- **Prueba:** recorrer 5 marcadores con el ratón: los 5 responden en menos de 100 ms.

### W4 · Clic: inmersión en el lugar
- **Se ve:** la cámara vuela al punto, se inclina para mostrar el relieve y gira despacio alrededor; el panel entra deslizando con la cifra grande que cuenta hacia arriba (hectáreas, magnitud, focos), «¿a quién afecta?» y botón Compartir.
- **Cómo:** `camera.flyTo` y luego `camera.lookAt` con giro lento del rumbo; `Esc` o arrastrar devuelve el control.
- **Prueba:** clic en un sismo de Perú y en la alerta de Ayacucho: en ambos se ve el relieve en 3D y la cifra principal.

### W5 · La danza: línea de tiempo con reproducción
Es el centro de la idea: el reto se llama *Dancing with the SARs* y pide «animaciones de series de tiempo».
- **Se ve:** barra abajo con los últimos 30 días, un histograma de eventos por día encima y un botón ▶. Al reproducir, sismos y focos aparecen en su hora real (1 día por segundo); se puede arrastrar para ir a cualquier fecha. Las capas NISAR aparecen en su fecha de pasada.
- **Cómo:** reloj de Cesium (`clock.startTime`, `stopTime`, `multiplier`) y `availability` de cada entidad, o filtrado por fecha en React. Verificar cuál rinde mejor con 500 entidades.
- **Prueba:** reproducir septiembre de 2026 sobre Ayacucho y ver aparecer los focos en orden; la fecha visible coincide con la del dato.

### W6 · NISAR en órbita
- **Se ve:** el modelo `apps/web/public/models/nisar.glb` recorre su órbita real alrededor del globo, con la línea de su recorrido sobre el suelo y la franja de ~240 km que observa barriendo la superficie. Tarjeta: «Próxima pasada sobre Ayacucho: fecha y hora».
- **Cómo:** elementos orbitales (TLE) públicos de CelesTrak buscados por el nombre «NISAR» (no copiar números de memoria); propagación con `satellite.js` (dependencia nueva: pedir permiso); entidad con `SampledPositionProperty` y `model`.
- **Rótulo obligatorio:** «Órbita calculada con elementos públicos de CelesTrak (fecha)». La franja es aproximada.
- **Prueba:** la traza sobre Perú cae sobre las trayectorias 75, 147 o 54 que aparecen en el catálogo de ASF.

### W7 · Revelado del radar
- **Se ve:** al abrir Cambios en Ayacucho, una línea de barrido cruza la zona como si pasara el satélite y destapa la imagen NISAR en falso color (estilo UAVSAR); después la cortina antes/después queda libre para arrastrar.
- **Cómo:** animar `scene.splitPosition` de 0 a 0,5 con `SplitDirection` en las dos capas.
- **Prueba:** solo con datos reales procesados; sin ellos, estado vacío que diga «falta procesar NISAR (EARTHDATA_TOKEN)».

### W8 · Paneles que se leen y priorizan
- **Lista de alertas:** arriba, «Lo más importante ahora» (3 tarjetas grandes); debajo, grupos por tipo y lugar («Ayacucho · 37 focos en 24 h») que se despliegan; nunca 420 filas planas.
- **Escala de letra:** mínimo 16 px en texto, crece con la pantalla hasta ~20 px a 2560 px; cifras principales de 40 px o más con su unidad.
- **Movimiento de interfaz:** paneles que entran deslizando, cambios de cifra animados, estados al pulsar; todo apagado con `prefers-reduced-motion`.
- **Prueba:** a 2560×1440 se lee todo a un metro de distancia.

## Imagen del globo
- Con `VITE_CESIUM_ION_TOKEN`: imagen aérea de Cesium ion y relieve mundial (ya está programado; falta el token).
- Capa de luces nocturnas (NASA GIBS VIIRS, nombre de capa a confirmar en GIBS) que solo se ve en el lado de noche (`nightAlpha`, `dayAlpha`).
- Revisar el borde punteado del limbo.

## Orden de trabajo

1. **W8 y W2** (paneles legibles y marcadores vivos): lo que más cambia la sensación con menos riesgo.
2. **W1 y W3** (llegada y respuesta al ratón).
3. **W5** (línea de tiempo): el corazón de la historia.
4. **W4** (inmersión).
5. **W6** (órbita de NISAR): pedir permiso para `satellite.js`.
6. **W7** cuando existan los datos NISAR reales.

Rendimiento: con animaciones activas, `requestRenderMode` debe quedar en `false` o pedir cuadros explícitamente; usar `PointPrimitiveCollection` si hay más de 1000 puntos; meta de 60 fps al girar en la máquina de la demo.

## Prompt para Codex

```text
Lee CLAUDE.md, AGENTS.md, docs/10_Plan_GAIA_Alerta_Codex.md y docs/11_Experiencia_Interactiva_Codex.md.
La app funciona pero se siente estática. Implementa los momentos W8, W2, W1, W3, W5 y W4 en ese orden,
uno por commit. Antes de usar cada API de Cesium, confírmala en la documentación oficial.
Todo lo animado debe ser dato real con su hora real; nada inventado.
Respeta prefers-reduced-motion. Después de cada momento: npm run build, las pruebas, un video corto
o 3 capturas (1440x900, 2560x1440 y 390x844) y una línea en CHANGELOG.md.
Para W6 pide permiso antes de instalar satellite.js. W7 solo cuando haya datos NISAR procesados.
```
