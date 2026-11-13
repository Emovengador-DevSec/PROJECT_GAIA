# Experiencia 3D premium

Objetivo: que el jurado sienta que mira la Tierra desde un satélite, sin sacrificar la lectura del dato.

## Principio
**Un solo momento espectacular, todo lo demás al servicio del dato.** La sorpresa viene de la cámara y de la luz real, no de efectos repartidos por toda la interfaz.

## Momentos de la experiencia

| Momento | Disparador | Técnica | Estado |
|---|---|---|---|
| **Despertar de franjas** | Abrir la app | Shader WebGL de franjas cíclicas que se expanden 1,2 s y se disuelven | Hecho (`FringeIntro.tsx`) |
| **Globo vivo** | Siempre | Cesium con iluminación solar real, atmósfera y niebla | Hecho |
| **Picada orbital** | Elegir una zona | `camera.flyTo` con curva QUINTIC_IN_OUT y ángulo oblicuo por zona (`config/aois/*.yaml → camera`) | Hecho (ángulo aún no leído de config) |
| **Relieve real** | Con token de Cesium ion | Cesium World Terrain + exageración vertical 1–10× | Hecho |
| **Capa radar sobre el relieve** | Capa procesada disponible | Teselas COG locales desde `/api/tiles` | Integrada |
| **Cortina antes/después** | Arrastrar o usar el teclado | Dos capas con `splitDirection` de Cesium | Integrada. Ayacucho requiere las observaciones procesadas. |
| **Pulso de alerta** | Seleccionar alerta | Anillo animado como entidad Cesium | M5 |
| **Órbita del satélite** | Modo historia | Trayectoria NISAR dibujada como polilínea brillante | Plus |
| **Cámara guiada** | Modo historia | Secuencia de `flyTo` encadenados con textos | Plus |

## Paleta y tipografía
- Interfaz oscura (`--abismo #0b1724`) para que el color del dato sea lo más brillante.
- Acento `--eco #5bc0eb`; avisos `--ambar`; alertas `--alerta`.
- Rampa de franjas solo para marca y fase envuelta; **los datos usan paletas científicas** (grises para dB, RdBu para cambio, viridis para coherencia).
- Bricolage Grotesque para títulos, Source Sans 3 para texto, cifras tabulares.

## Rendimiento
| Meta | Cómo |
|---|---|
| 60 fps en portátil medio | Una sola capa radar a la vez, `maximumLevel` 16, sin sombras de terreno |
| Primera vista < 3 s | Cesium se carga con el bundle; dividir con `import()` dinámico si crece |
| Sin red de Cesium ion | El globo funciona sin token (sin relieve) |
| Móvil | Exageración 2×, paneles como hojas inferiores |

## Accesibilidad
- `prefers-reduced-motion`: no hay franjas y los vuelos son instantáneos.
- Foco visible, botones con texto, cifras con unidad.
- Nada depende solo del color: severidad con texto.

## Siguiente pulido recomendado (en orden)
1. Leer `camera.heading_deg/pitch_deg` de cada zona en el vuelo.
2. Cortina antes/después con `ImageryLayer.splitDirection`.
3. Leyenda con mínimo, máximo y cero reales del manifiesto.
4. Postprocesado sutil: `scene.postProcessStages.bloom` solo en entidades de alerta.
