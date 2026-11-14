# Bailando con los SARs (v3) — instrucciones para Claude Code

Aplicación web que convierte **datos radar NISAR reales** (NASA-ISRO) en respuestas claras sobre cambios de la superficie terrestre, con un globo 3D cinematográfico. NASA Space Apps Challenge 2026, reto "Dancing with the SARs" (14 y 15 de noviembre de 2026).

## Lee primero
0. `docs/22_Arranque_en_otra_PC.md` — estado actual del proyecto, cómo levantarlo y qué falta (manda sobre el plan M0–M6).
1. `docs/00_LEEME.md` — mapa del proyecto.
2. `docs/05_Plan_MVP_72h.md` — qué construir y en qué orden (fases M0 a M6).
3. `docs/06_Requisitos_del_Reto.md` — **todo cambio debe mantener cumplido cada punto del enunciado oficial.**
4. Según la tarea: `docs/03_Datos_NASA_Ingesta.md` (datos) o `docs/04_Experiencia_3D_Premium.md` (interfaz).

## Reglas de oro
1. **Datos reales, nunca simulados en la interfaz.** Si falta un dato: estado vacío que diga qué hacer.
2. **Sintéticos solo en pruebas** (`services/pipeline/tests`).
3. **Procedencia y calidad visibles** en cada capa: gránulos, fechas, aviso de dato provisional.
4. **NISAR separado de lo complementario** (OPERA, FIRMS, USGS), etiquetado en pantalla.
5. **Sin secretos en código ni en el navegador.** Solo `.env` en el servidor. No leas `.env`.
6. **Nunca escribas en `data/01_raw/`.** Lo nuevo entra por `data/00_inbox/` + `sarlab ingest`.
7. **Nunca inventes rutas HDF5.** Confírmalas con `sarlab inspect` y anótalas en `docs/data-notes.md`.
8. **Antes de decir "funciona", ejecútalo** y muestra la salida.
9. **Solo la fase actual.** No agregues funciones fuera de ella sin preguntar.

## Mapa del repositorio
| Ruta | Contenido |
|---|---|
| `services/pipeline/src/sarlab_pipeline/` | Python: `sources/` (ASF), `readers/` (HDF5), `processing/`, `detection/`, `publish/`, `ingest.py`, `workflows.py`, `cli.py` |
| `services/api/app/main.py` | FastAPI: `/api/health`, `/api/config`, `/api/aois`, `/api/layers`, `/api/alerts`, `/api/stories/{zona}`, `/api/timeseries`, `/api/polarizations`, teselas en `/api/cog` |
| `apps/web/src/` | React + CesiumJS: `features/gaia` (portada), `features/globe`, `features/intro`, `features/panels`, `styles/tokens.css` |
| `art/` · `tools/blender/` | Portada PROJECT GAIA: escena de Blender, cuadros, créditos y scripts de render (ver `docs/08_Portada_Project_Gaia.md`) |
| `config/` | Zonas, relatos con hipótesis (`stories/`), fenómenos, productos, umbrales, paletas, interruptores |
| `data/` | Etapas 00_inbox → 01_raw → 03_processed → 04_published, 99_quarantine, catalog (fuera de Git) |
| `docs/` | Guías v3; `docs/v2-referencia/` detalle anterior (v3 manda si hay conflicto) |

## Comandos
| Acción | Comando |
|---|---|
| Instalar | `make setup` |
| API / Web | `make dev-api` · `make dev-web` |
| Pruebas | `make test` |
| Revisión de entorno | `make doctor` |
| Buscar datos | `uv run sarlab search --aoi <zona> --start 2025-10-01` |
| Descargar 2 | `make download AOI=<zona>` |
| Ingerir | `uv run sarlab ingest` |
| Ver capas de un .h5 | `uv run sarlab inspect <archivo>` |
| Cambio HH y HV entre fechas | `uv run sarlab change --aoi <zona> --before <a.h5> --after <b.h5>` |
| Serie de tiempo | `uv run sarlab timeseries --aoi <zona> <a.h5> <b.h5> <c.h5>` |

## Agentes y habilidades del proyecto
- Subagentes en `.claude/agents/`: `geo-data-engineer`, `frontend-3d`, `security-reviewer`.
- Habilidades en `.claude/skills/`: `fase`, `datos-nisar`, `revision-demo`.

## Convenciones
- Interfaz en español, minúscula de oración, verbos claros. Código y comentarios técnicos en inglés o español, coherente por archivo.
- Unidades siempre visibles (dB, cm, ha). Respeta `prefers-reduced-motion`.
- Una línea en `CHANGELOG.md` por cambio relevante.

## Cuándo preguntar
Falta una credencial, una descarga supera 5 GB, no hay datos para la zona, dos documentos se contradicen o una decisión cambia la arquitectura.
