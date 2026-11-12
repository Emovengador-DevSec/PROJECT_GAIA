# Arquitectura y tecnologías

## Flujo
```
 ASF DAAC (NISAR .h5) ──search/download──▶ data/00_inbox ──ingest──▶ data/01_raw (inmutable) + catalog
                                                                         │
                                       readers/gcov.read_window (solo la ventana de la zona)
                                                                         │
                               processing (dB, speckle) → detection (MAD k·σ) → publish (COG + manifiesto + alertas)
                                                                         │
                                                       data/03_processed/<zona>/gcov/<A>__<B>/
                                                                         │
                         FastAPI /api/* + TiTiler /api/cog/tiles ──▶ React + CesiumJS (globo 3D)
```

## Módulos

| Módulo | Archivo | Responsabilidad | Estado |
|---|---|---|---|
| Configuración | `sarlab_pipeline/config.py` | Lee y valida zonas y umbrales (Pydantic) | Probado |
| Fuente NISAR | `sources/nisar.py` | Búsqueda con `asf_search`, filtro de .h5, descarga autenticada | Escrito, falta prueba real (M1) |
| Inspección | `readers/hdf5_inspect.py` | Lista todas las capas de un .h5 | Probado |
| Lector GCOV | `readers/gcov.py` | Lee solo la ventana de la zona, EPSG del producto | Probado con estructura documentada |
| Procesado | `processing/backscatter.py`, `quality.py` | dB, diferencia, reducción de moteado, máscaras | Probado |
| Detección | `detection/change.py` | Umbral robusto (mediana + MAD), polígonos | Probado |
| Publicación | `publish/cog.py`, `manifest.py` | COG y manifiesto con procedencia | Probado |
| Ingesta | `ingest.py` | Valida, mueve a 01_raw, catálogo, sumas, cuarentena | Probado |
| Flujo | `workflows.py` | Cambio entre dos fechas de una zona | Probado de extremo a extremo |
| CLI | `cli.py` | `sarlab search|inspect|ingest|change` | Escrito |
| API | `services/api/app/main.py` | Rutas de lectura + teselas TiTiler | Probado |
| Web | `apps/web/src` | Globo Cesium, vuelo, shader, paneles | Compila |

## Pila tecnológica

| Capa | Tecnología | Motivo |
|---|---|---|
| Lenguaje de datos | **Python 3.11+** con **uv** | Estándar geoespacial; uv instala en segundos |
| Acceso NASA | **asf_search**, **earthaccess** | Herramientas oficiales de ASF y NASA para NISAR |
| Lectura | **h5py**, **xarray + h5netcdf** | NISAR se distribuye en HDF5 |
| Ráster | **rasterio**, **rioxarray**, **numpy**, **scipy** | Proyección, COG, etiquetado de manchas |
| Validación | **Pydantic** | Configuración tipada que falla con mensajes claros |
| API | **FastAPI** | Rápida, documentación automática en `/docs` |
| Teselas | **TiTiler** | Teselas al vuelo desde COG sin preprocesar |
| Interfaz | **React 19 + TypeScript + Vite** | Rápido de construir y verificar |
| 3D | **CesiumJS** | Globo real, relieve mundial, atmósfera, iluminación solar, vuelos de cámara |
| Animación UI | **Framer Motion** | Transiciones de paneles |
| Efecto de marca | **Shader WebGL propio** | Franjas interferométricas sin librerías extra |
| Calidad | **pytest**, **ruff**, **pip-audit**, **npm audit**, **gitleaks** | Pruebas y seguridad en CI |

Fase P1 opcional: **deck.gl** para millones de puntos (series de tiempo) y **API de Claude** para el Analista.

## Decisiones clave
- **Leer por ventana, no el archivo entero.** Cada capa GCOV completa puede pesar varios GB; el lector recorta por índices de coordenadas.
- **Mismo track y dirección para comparar fechas.** Si el EPSG o la rejilla no coinciden, el flujo se detiene con un mensaje claro.
- **GCOV primero, GUNW después.** GCOV responde deforestación y huaicos con menos riesgo; la deformación (GUNW) es P1.
- **Sin base de datos en el MVP.** Catálogo y manifiestos en JSON; se migra a STAC o base de datos cuando haga falta.
