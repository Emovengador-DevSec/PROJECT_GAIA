# Bailando con los SARs

Detecta, mide y explica cambios de la superficie terrestre con **datos radar NISAR reales** (NASA-ISRO), sobre un **globo 3D**. Proyecto para el NASA Space Apps Challenge 2026, reto *Dancing with the SARs*.

## Arranque
```bash
cp .env.example .env              # pon tu EARTHDATA_TOKEN
make setup && make doctor
make dev-api                      # terminal 1 → http://localhost:8000/docs
make dev-web                      # terminal 2 → http://localhost:5173
```

## Datos reales en 4 comandos
```bash
uv run sarlab search --aoi madre-de-dios-la-pampa --start 2025-10-01
make download AOI=madre-de-dios-la-pampa      # 2 gránulos GCOV a data/00_inbox
uv run sarlab ingest                          # valida y mueve a data/01_raw
uv run sarlab change --aoi madre-de-dios-la-pampa --before <a.h5> --after <b.h5>   # HH y HV
uv run sarlab timeseries --aoi madre-de-dios-la-pampa <a.h5> <b.h5> <c.h5>
```

## Construir con Claude Code
Abre la carpeta con Claude Code y escribe: *"Lee CLAUDE.md y ejecuta la fase M0"*. Detalle en `docs/05_Plan_MVP_72h.md`.

## Estado verificado
- 13 pruebas en verde: lectura GCOV por ventana, dB, umbral robusto, COG, alertas, ingesta y cuarentena, comparación HH/HV, series de tiempo, relatos y bloqueo de rutas maliciosas.
- Web: compila con TypeScript estricto y Vite.
- **No probado aún contra un archivo NISAR real** (requiere tu cuenta de Earthdata): es la fase M1.

## Cumplimiento del reto
Cada punto del enunciado oficial y dónde se cumple: `docs/06_Requisitos_del_Reto.md`.

## Licencia
MIT (código abierto, como pide el reto).
