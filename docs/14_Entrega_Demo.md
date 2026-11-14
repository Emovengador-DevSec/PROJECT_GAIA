# Entrega y recorrido de GAIA

Revisión del 13 de noviembre de 2026 en Perú.

## Datos preparados

La comparación activa usa dos GCOV de la trayectoria 147 ascendente, marco 171, del
24 de junio y el 10 de octubre de 2026. La máscara conserva el 99,91 % de la caja del
caso Huanta y La Mar. HV registra 3.607 ha con caída de señal. El tamaño mínimo de
una hectárea delimita 498 manchas que suman 938,28 ha. OPERA coincide en 21,08 ha,
el 2,25 % de estas manchas. La hipótesis de incendio sigue pendiente de verificación.

Las fichas cruzan WorldPop 2025, ESA WorldCover 2021 y 1.192 localidades OSM con cada
mancha. WorldCover cubre todas las manchas. WorldPop ofrece una estimación parcial,
con 243 de 498 manchas HV sin píxeles válidos de población. Cada ficha conserva el
estado de sus fuentes y sus licencias.

## Guion de 2–3 minutos

| Momento | Acción | Relato |
|---|---|---|
| 0–15 s | Portada PROJECT GAIA y entrada | Desde Ayacucho estudiamos cómo cambia el territorio con observaciones radar. |
| 15–35 s | Globo, sismos, focos y órbita | USGS aporta sismos observados y FIRMS aporta detecciones térmicas con hora y fuente. |
| 35–50 s | Reproducir la secuencia y pulsar Ver todo | El tiempo permite ver cuándo aparecen las observaciones disponibles. Cada fuente conserva su período de cobertura. |
| 50–75 s | Lugares → Huanta y La Mar → Cambios | Comparamos dos fechas NISAR sobre el 99,91 % de la caja. La cortina conserva una escala compartida para HH/HV. |
| 75–100 s | Calidad → Contraste cuantitativo | Detectamos 3.607 ha con caída HV. Las manchas delimitadas reúnen 938,28 ha. OPERA coincide con el 2,25 % de esas manchas y la atribución sigue abierta. |
| 100–125 s | Alertas → NISAR → ¿A quién afecta? | Cada mancha muestra cultivos, bosque, pastizal y pueblos a menos de 2 km. WorldPop tiene cobertura parcial. Son estimaciones de exposición. |
| 125–145 s | Historia y Fuentes | El proyecto conserva hipótesis, procedencia y recursos para explicar el radar a comunidades, gestores y estudiantes. |
| 145–155 s | Cierre sobre el globo | Las próximas observaciones y la verificación local permitirán investigar causas y seguir la recuperación. |

En una demostración oral se puede explicar que el radar observa el eco de microondas,
FIRMS registra calor y USGS registra sismos. La recuperación requiere más fechas.
El nivel de actividad y las alertas de un volcán requieren la fuente oficial competente.

El video local `art/verificacion/gaia-alerta-demo.mp4` dura 157,9 segundos, usa H.264 a
1440×900 y ocupa 9,46 MB. Se grabó la app real sin conexión y se editó al 133 % de
velocidad de reproducción, con una duración acorde al guion. El archivo conserva la
imagen de la interfaz y permite acompañarlo con explicación oral. Las capturas y los
informes de PC y teléfono están en `art/verificacion/final/`. Para repetir la comprobación
se inicia `scripts/run_demo.py --offline --port 8093` y se ejecuta
`node tools/verify/final.mjs --record`. El script genera la versión comprimida y elimina
su grabación intermedia al completarla.

## Texto de proyecto en inglés para revisar antes de enviar

**Project name**

GAIA Alerta

**Summary**

GAIA Alerta makes real NISAR radar observations accessible through an interactive 3D
globe. Our Huanta and La Mar case in Ayacucho, Peru, compares compatible acquisitions
from June 24 and October 10, 2026, with 99.91% common valid coverage of the study box.
Users explore HH/HV changes, compare dates, inspect independent OPERA evidence and
review population, land cover and nearby settlements for each mapped change polygon.

**Scientific findings and uncertainty**

HV backscatter decreases exceed a robust statistical threshold across 3,607 hectares.
A minimum mapping unit of one hectare yields 498 polygons covering 938.28 hectares.
OPERA confirmed vegetation disturbance overlaps 21.08 hectares of those polygons,
or 2.25%, with intersection-over-union of 0.80%. The low agreement keeps wildfire
attribution under investigation. WorldPop estimates are partial because 243 polygons
contain no valid population pixels. Exposure estimates describe potential territorial
overlap and require local verification.

**NASA data**

NISAR L2 GCOV provisional, HH/HV, track 147 ascending, frame 171, processing CRID P05023.
OPERA DIST-ALERT-HLS original status and onset-date rasters from October 13, 2026,
tiles T18LWL and T18LXL. NASA FIRMS thermal detections provide complementary context.
NASA Blue Marble, Black Marble and GIBS provide contextual imagery. The app records
granule identifiers, observation dates, quality information and resource links.
[NISAR](https://nisar-docs.asf.alaska.edu/gcov/),
[OPERA](https://doi.org/10.5067/SNWG/OPERA_L3_DIST-ALERT-HLS_V1.001),
[FIRMS](https://firms.modaps.eosdis.nasa.gov/)

**Partner and other data**

RADARSAT-1 historical imagery provides context for the additional study cases. USGS
provides observed earthquakes. ESA WorldCover 2021 supplies land-cover classes,
WorldPop Global2 R2025A supplies 2025 population estimates, and OpenStreetMap supplies
settlements. Cesium World Terrain and the cached regional terrain provide elevation.
Each layer retains its own attribution and usage terms. The SAOCOM and RCM comparisons
remain dependent on access and compatible observations.

**Use of AI tools**

The team used Codex for implementation, debugging, data-processing scripts and checks.
Claude assisted with planning and review. The team must review and complete this
statement with every AI tool it used and describe any additional generated media.
The implementation uses official observations and preserves their provenance.

## Verificación de entrega

La página oficial de 2026 confirma apertura el 14 de noviembre a las 09.00 y cierre
el 15 de noviembre a las 23.59, hora local. La organización anunció la guía de entrega
para el 13 de noviembre. En esta revisión, la página Resources devolvió 502 o un fallo
de cadena TLS desde las herramientas disponibles. Queda pendiente leer esa guía y
verificar sus campos, idioma y duración exacta antes del envío. El guion extenso de
este documento sirve para la demostración local.
[Calendario oficial](https://www.spaceappschallenge.org/2026/),
[Anuncio del equipo organizador](https://github.com/nasa/spaceapps/discussions/1839)

La persona del equipo crea el repositorio público y envía el proyecto desde su cuenta.
El código y la documentación están preparados localmente. El directorio `data` se
distribuye con la copia local de la demo o mediante un alojamiento preparado para
los productos procesados. Los HDF5 originales se conservan como archivo local.

La auditoría Python terminó sin vulnerabilidades conocidas. npm detectó problemas en
Vitest y sus dependencias. La actualización a 4.1.12 dejó el informe de npm en cero.
El escaneo de los archivos versionados y los bundles buscó asignaciones de secretos del
servidor, claves privadas y claves AWS y devolvió cero candidatos. `.env`, `apps/web/.env`
y `data` siguen ignorados por Git. El token de Cesium se entrega al navegador según el
diseño del servicio y sus restricciones por dominio deben revisarse en Cesium ion para
el dominio público elegido. La revisión independiente del subagente de seguridad falló
por límite de uso y se completó una revisión local de código y dependencias.

La suite terminó con 41 pruebas aprobadas. Las cinco advertencias de Rasterio proceden
de imágenes PNG usadas en pruebas. La compilación TypeScript/Vite pasó y Ruff aprobó
los archivos Python modificados. Vitest arranca correctamente y el proyecto carece de
pruebas unitarias web. `doctor.py` terminó con cero errores y cero avisos, verificando
también los SHA-256 de los originales. Chrome verificó 1440×900 y 390×844 con y sin
conexión, dos fechas NISAR servidas como teselas reales, fichas de exposición y ausencia
de errores JavaScript/Cesium. La consulta local de 2.144 observaciones tardó 0,325 s
después de cargar la exposición una vez por zona. La API habitual en el puerto 8000
se reinició y sirve el período activo a la web de `localhost:5173`.

G5 necesita cuatro fechas compatibles, frente al límite vigente de dos descargas GCOV.
G6 permanece pendiente de la selección, descarga e inspección GUNW y de la fuente
volcánica oficial. Las fases G1, G2, G3 y G4 conservan los resultados descritos arriba.
