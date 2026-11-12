# Día del evento: datos y recursos

## Qué está disponible ya y qué puede llegar el sábado
- **Ya disponible:** el archivo NISAR de ASF DAAC (GCOV, GUNW, GOFF, GSLC, SME2), público con cuenta de Earthdata. Se puede buscar y descargar **hoy**.
- **Puede cambiar hasta el sábado:** la pestaña *Recursos* del reto, que el propio enunciado dice que puede ampliarse antes del hackathon.

No esperes al sábado para descargar el caso estrella. Si el sábado aparecen recursos nuevos, el software los acepta sin cambios de código.

## Antes del sábado (hoy y mañana)
1. Cuenta y token de Earthdata en `.env`; `make doctor`.
2. `uv run sarlab search --aoi madre-de-dios-la-pampa --start 2025-10-01`.
3. Descargar 2 a 4 gránulos GCOV del mismo track y dirección; `sarlab ingest`.
4. `sarlab change` y `sarlab timeseries` sobre esos archivos. Si algo falla, se arregla antes del evento.
5. Hacer lo mismo con una segunda zona como respaldo.

## El sábado, cuando se publiquen los recursos (primera hora)

| Lo que publiquen | Qué hacer |
|---|---|
| Enlaces a búsquedas o colecciones NISAR | `sarlab search` con la zona o descarga directa a `data/00_inbox` |
| Archivos `.h5` concretos | Soltarlos en `data/00_inbox` y `sarlab ingest` |
| Un producto que aún no leemos (GUNW, GOFF, SME2) | `sarlab inspect`, anotar rutas en `docs/data-notes.md`, crear lector con `geo-data-engineer` |
| Datos sobre otra zona del mundo | Crear `config/aois/<zona>.yaml` y `config/stories/<zona>.yaml` |
| Datos complementarios (óptico, SIG) | Registrar en `config/sources.yaml` como complementarios y etiquetarlos en pantalla |
| Nada nuevo | Seguir con lo descargado; ya cumple el reto |

Prompt para Claude Code ese día:
```text
Se publicaron estos recursos del reto: <pegar enlaces o texto>. Con la skill datos-nisar,
dime cuáles son NISAR, cuáles complementarios, y qué cambio mínimo necesita el software
para usarlos. No descargues nada sin confirmarme el tamaño.
```
