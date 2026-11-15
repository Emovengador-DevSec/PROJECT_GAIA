# Requisitos del reto y cómo los cumple el software

Texto de referencia del reto *Dancing with the SARs* (NASA Space Apps 2026). Revisión de GAIA Alerta del 13 de noviembre de 2026.

La demo abre el globo con imagen satelital, sismos de USGS y focos de NASA FIRMS. El par activo de Ayacucho corresponde al 24 de junio y el 10 de octubre de 2026, trayectoria 147 ascendente. La cobertura válida común es del 99,91 % de la caja de estudio. OPERA contrasta la misma cobertura con sus rásteres originales.

## Objetivo principal

| Lo que pide el reto | Cómo lo cumple | Dónde | Estado |
|---|---|---|---|
| Aplicación **interactiva** | Globo 3D, pestañas, selector de lugar y polarización, modo público/técnico | `apps/web` | Hecho |
| Usar datos **NISAR** de teledetección radar | Descarga autenticada en ASF y lectura HDF5 de HH y HV con la máscara GCOV | `sources/nisar.py`, `readers/gcov.py` | Verificado con los dos archivos de Ayacucho |
| **Rastrear y visualizar** uno o más tipos de cambio | Cambio de retrodispersión entre fechas: deforestación, huaicos; deformación en P1 | `workflows.py`, `config/phenomena` | Hecho |
| En **diferentes lugares del mundo** | Cada lugar es un archivo; Perú como caso, cualquier zona como producto | `config/aois/*.yaml` | Hecho |

## Pasos que sugiere el reto

| Paso | Cómo | Dónde | Estado |
|---|---|---|---|
| 1. Elegir un **área de estudio** | Pestaña Lugares; tres zonas peruanas configuradas; se agregan más sin código | `config/aois` | Hecho |
| 2. **Descargar NISAR** de la lista de recursos | `sarlab search` y `--download`; o soltar cualquier `.h5` en `data/00_inbox` | CLI | Hecho |
| Datos **complementarios** (óptico, SIG) | Blue Marble y Landsat, límites y localidades, sismos USGS y detecciones VIIRS vía FIRMS | `apps/web/public/globe`, `/api/live/quakes`, `/api/live/fires` | USGS, mapas y acceso a FIRMS verificados. |
| 3. **Presentar** en medio digital interactivo | Pestaña Historia: mapa narrativo con pasos de cámara; video de la demo | `config/stories`, `Inspector.tsx` | Hecho |
| Formular **hipótesis físicas** | Cada relato tiene hipótesis, cómo probarlas y estado (por verificar / confirmada / descartada) | `config/stories/*.yaml` | Hecho (el equipo actualiza el estado con los resultados) |
| ¿Qué **polarizaciones** resaltan los cambios? | Cambio en HH y HV por separado, razón HV/HH y `polarizations.json` con la más fuerte | `analysis.py`, selector en Cambios | Hecho |
| ¿Qué **aplicaciones futuras** de NISAR? | Campo `future` en cada relato | `config/stories` | Hecho |

## Consideraciones opcionales

| Consideración | Cómo | Estado |
|---|---|---|
| Distintas **polarizaciones** y **frecuencias** | HH, HV; `--freq frequencyA|frequencyB` | Hecho |
| **Series de tiempo** con varias fechas | `sarlab timeseries` + pestaña Tiempo | Hecho |
| Datos de **contexto** (población, vegetación) | `sarlab exposure` cruza WorldPop 2025, ESA WorldCover 2021 y 1.192 localidades OSM con polígonos NISAR | Publicado para las 608 manchas HH y 498 HV del par activo, con disponibilidad, fechas y licencias. |
| **Factores humanos** (minería, agricultura, ciudad) | Campo `human_factors` en cada relato | Hecho |
| **Contar historias** con visualización | Despertar de franjas, vuelos de cámara, relato por pasos | Hecho |
| **Conocimiento local** | Casos peruanos; el equipo aporta contexto en los relatos | Hecho, a enriquecer |
| Resumen **interactivo** (mapas web, carruseles) | La app misma es el resumen interactivo | Hecho |

## Calidad de la solución

| Atributo pedido | Cómo | Estado |
|---|---|---|
| **Código abierto** | Licencia MIT y dependencias abiertas | Código preparado. Publicación del repositorio pendiente del equipo. |
| **Fácil de usar** | Modo público con lenguaje llano; estados vacíos que dicen qué hacer | Hecho |
| Para **científicos, gestores, educadores, decisores y público** | Modo técnico con método y umbral, modo público, fichas para imprimir y compartir, recursos del reto | Contraste real OPERA publicado. La coincidencia limitada mantiene pendiente la atribución del cambio a incendios. |

## Lo que el equipo debe completar con los datos reales
1. Cambiar el `status` de cada hipótesis a `confirmada` o `descartada`, con la evidencia.
2. Ayacucho tiene caja y cobertura confirmadas. Verificar las demás zonas antes de activarlas como casos cuantitativos.
3. Escribir en `docs/science/` los hallazgos y las limitaciones.


## Evidencia visual complementaria (doc 27, R1–R5)

- La ficha de cada mancha conserva Diagnóstico, Clima, Futuro y costos, y Voz y Minka. Añade **Ver el lugar**: imágenes ópticas georreferenciadas, plantas de las recetas, observaciones cercanas, comunidad y suelo estimado.
- Las imágenes HLS son complementarias; sus fechas ópticas son distintas del par NISAR. Cada recorte conserva la solicitud WMS, CRS, extensión, resolución y escena o lista de escenas. El contorno procede de la geometría publicada de la mancha.
- Las observaciones iNaturalist son de grado de investigación, con licencia abierta y coordenadas públicas; se excluyen posiciones ocultas/privadas y precisión peor que 100 m. La distancia se mide al polígono NISAR. Las fotos de especies propuestas se identifican como referencias, no como vegetación presente en la mancha.
- Los pines de fotografías usan las coordenadas de la fuente. Un índice accesible permite abrirlas con teclado y ajustar el mapa a sus ubicaciones.
- Los escenarios siguen siendo supuestos. No muestran ganancias numéricas mientras la cita no esté verificada. Ninguna foto representa el futuro de esta ladera; las técnicas en otro lugar requieren revisión de autor, fecha, licencia y localización.
- Las fotos se sirven desde archivos del servidor. Wikimedia puede rechazar la descarga automática: los bloques sin imágenes publicadas informan de la ausencia; no se rellenan con fotografías regionales ni imágenes generadas. El mapa radar, los relatos, las hipótesis, HH/HV, las series y la calidad conservan sus ubicaciones y cálculos.
