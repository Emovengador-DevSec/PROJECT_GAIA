# Requisitos del reto y cómo los cumple el software

Texto de referencia del reto *Dancing with the SARs* (NASA Space Apps 2026). Revisión de GAIA Alerta del 13 de noviembre de 2026.

La demo abre el globo con imagen de NASA, la historia de Ayacucho y sismos reales de USGS. El catálogo público de ASF lista las observaciones NISAR. Los resultados de cambio de Ayacucho requieren descargar y procesar los dos GCOV seleccionados con Earthdata.

## Objetivo principal

| Lo que pide el reto | Cómo lo cumple | Dónde | Estado |
|---|---|---|---|
| Aplicación **interactiva** | Globo 3D, pestañas, selector de lugar y polarización, modo público/técnico | `apps/web` | Hecho |
| Usar datos **NISAR** de teledetección radar | Búsqueda y descarga oficial con `asf_search`; lectura HDF5 del GCOV | `sources/nisar.py`, `readers/gcov.py` | Hecho (falta prueba con archivo real) |
| **Rastrear y visualizar** uno o más tipos de cambio | Cambio de retrodispersión entre fechas: deforestación, huaicos; deformación en P1 | `workflows.py`, `config/phenomena` | Hecho |
| En **diferentes lugares del mundo** | Cada lugar es un archivo; Perú como caso, cualquier zona como producto | `config/aois/*.yaml` | Hecho |

## Pasos que sugiere el reto

| Paso | Cómo | Dónde | Estado |
|---|---|---|---|
| 1. Elegir un **área de estudio** | Pestaña Lugares; tres zonas peruanas configuradas; se agregan más sin código | `config/aois` | Hecho |
| 2. **Descargar NISAR** de la lista de recursos | `sarlab search` y `--download`; o soltar cualquier `.h5` en `data/00_inbox` | CLI | Hecho |
| Datos **complementarios** (óptico, SIG) | Blue Marble y Landsat, límites y localidades, sismos USGS y detecciones VIIRS vía FIRMS | `apps/web/public/globe`, `/api/live/quakes`, `/api/live/fires` | USGS y mapas verificados. FIRMS requiere clave. |
| 3. **Presentar** en medio digital interactivo | Pestaña Historia: mapa narrativo con pasos de cámara; video de la demo | `config/stories`, `Inspector.tsx` | Hecho |
| Formular **hipótesis físicas** | Cada relato tiene hipótesis, cómo probarlas y estado (por verificar / confirmada / descartada) | `config/stories/*.yaml` | Hecho (el equipo actualiza el estado con los resultados) |
| ¿Qué **polarizaciones** resaltan los cambios? | Cambio en HH y HV por separado, razón HV/HH y `polarizations.json` con la más fuerte | `analysis.py`, selector en Cambios | Hecho |
| ¿Qué **aplicaciones futuras** de NISAR? | Campo `future` en cada relato | `config/stories` | Hecho |

## Consideraciones opcionales

| Consideración | Cómo | Estado |
|---|---|---|
| Distintas **polarizaciones** y **frecuencias** | HH, HV; `--freq frequencyA|frequencyB` | Hecho |
| **Series de tiempo** con varias fechas | `sarlab timeseries` + pestaña Tiempo | Hecho |
| Datos de **contexto** (población, vegetación) | `sarlab exposure` cruza WorldPop, ESA WorldCover y localidades con polígonos NISAR | Integrado. Cálculo pendiente de los polígonos reales. |
| **Factores humanos** (minería, agricultura, ciudad) | Campo `human_factors` en cada relato | Hecho |
| **Contar historias** con visualización | Despertar de franjas, vuelos de cámara, relato por pasos | Hecho |
| **Conocimiento local** | Casos peruanos; el equipo aporta contexto en los relatos | Hecho, a enriquecer |
| Resumen **interactivo** (mapas web, carruseles) | La app misma es el resumen interactivo | Hecho |

## Calidad de la solución

| Atributo pedido | Cómo | Estado |
|---|---|---|
| **Código abierto** | Licencia MIT, repositorio público, dependencias abiertas | Hecho (cámbiala si el equipo prefiere otra) |
| **Fácil de usar** | Modo público con lenguaje llano; estados vacíos que dicen qué hacer | Hecho |
| Para **científicos, gestores, educadores, decisores y público** | Modo técnico con método y umbral, modo público, fichas para imprimir y compartir, recursos del reto | Interfaz verificada. Validación científica pendiente de datos NISAR reales. |

## Lo que el equipo debe completar con los datos reales
1. Cambiar el `status` de cada hipótesis a `confirmada` o `descartada`, con la evidencia.
2. Ajustar las cajas de las zonas a las huellas reales y marcar `status: confirmed`.
3. Escribir en `docs/science/` los hallazgos y las limitaciones.
