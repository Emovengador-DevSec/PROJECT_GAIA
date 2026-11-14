# GAIA Alerta

Detecta, mide y explica cambios de la superficie terrestre con **datos radar NISAR reales** (NASA-ISRO), sobre un **globo 3D**. Proyecto para el NASA Space Apps Challenge 2026, reto *Dancing with the SARs*.

## Arranque local

Instala las dependencias con `uv sync` y `npm --prefix apps/web ci`. Configura `EARTHDATA_TOKEN` y `FIRMS_MAP_KEY` en `.env` para acceder a los gránulos NISAR y los focos de calor. Configura `VITE_CESIUM_ION_TOKEN` en `apps/web/.env` antes de compilar para activar el relieve mundial.

```powershell
npm --prefix apps/web run build
uv run python scripts/run_demo.py
```

Abre [GAIA Alerta](http://127.0.0.1:8000/). Para la demo sin internet usa `uv run python scripts/run_demo.py --offline --port 8088`. La demo sirve el mapa NASA y el relieve local de Ayacucho junto con las últimas observaciones guardadas. Cada fuente muestra la fecha de su caché. Los archivos de datos bajo `data/` se conservan localmente.

## Caso Ayacucho

Busca «Huanta» para abrir el recorrido de Ayacucho. La comparación activa usa los GCOV del **24 de junio y 10 de octubre de 2026**, trayectoria 147 ascendente, marco 171, con HH/HV y la misma versión de procesamiento. Suman **4,16 GB**. La cobertura válida común es del **99,91 %** de la caja de estudio.

Con Earthdata configurado, ejecuta `uv run python tools/download_approved.py` y después `uv run python scripts/process_ayacucho.py`. La ingesta registra los originales con SHA-256. El procesamiento inspecciona HDF5, publica HH/HV y activa el período completo cuando supera el 80 % de cobertura válida. El período anterior se conserva en el archivo local. La proyección de tendencia requiere cuatro fechas compatibles.

HV presenta **3.607 ha con caída de señal**. Las **498 manchas delimitadas** reúnen **938,28 ha** y el resto son fragmentos inferiores al mínimo de 25 píxeles. OPERA del 13 de octubre coincide en **21,08 ha**, el **2,25 %** de esas manchas, con intersección/unión del **0,80 %**. La atribución a incendios continúa por verificar. Cada ficha muestra exposición con WorldPop, WorldCover y localidades OSM, con las fechas, licencias y disponibilidad de cada fuente. El [registro de datos](docs/data-notes.md) detalla el método y sus límites.

El globo abre con **Siempre de día**. El selector de la barra permite explorar la iluminación solar en **Hora real**.

![Comparación NISAR activa en Ayacucho](art/verificacion/final/radar-1440.jpg)

[Ver exposición territorial](art/verificacion/final/exposicion-1440.jpg) · [Video de respaldo de 2 min 38 s](art/verificacion/gaia-alerta-demo.mp4)

## Cumplimiento del reto
Cada punto del enunciado oficial y dónde se cumple: `docs/06_Requisitos_del_Reto.md`.

## Licencia
MIT (código abierto, como pide el reto).
