---
name: datos-nisar
description: Busca, descarga, ingiere y procesa datos NISAR reales para una zona de config/aois. Úsala cuando el usuario pida traer, actualizar o procesar datos de la NASA.
---
1. Comprueba que EARTHDATA_TOKEN existe con `make doctor` (no leas .env).
2. `uv run sarlab search --aoi <zona> --start <fecha>`; muestra la tabla y propone dos gránulos del MISMO track y dirección, separados en el tiempo.
3. Pide confirmación antes de descargar (los archivos pesan GB). Luego `--download --limit 2`.
4. `uv run sarlab ingest` y revisa la cuarentena si hubo fallos.
5. `uv run sarlab inspect <archivo>` y anota capas nuevas en docs/data-notes.md.
6. `uv run sarlab change --aoi <zona> --before <a.h5> --after <b.h5>` y resume: alertas, hectáreas, área válida, avisos de calidad.
