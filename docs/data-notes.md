# Hallazgos del dato real

Cada entrada con fecha, archivo de origen y comando usado. Solo rutas vistas en archivos reales o en documentación oficial.

## GCOV (documentación ASF, 2026-11-11)
- Grupo: `/science/LSAR/GCOV/grids/frequencyA` (puede existir `frequencyB`).
- Capas: `HHHH`, `HVHV`, `mask`, `numberOfLooks`, `rtcGammaToSigmaFactor`, `xCoordinates`, `yCoordinates`, `projection` (`attrs['epsg_code']`).
- Pendiente: confirmar con `sarlab inspect` sobre un archivo descargado (fase M1).

## GUNW
- Pendiente: rutas no verificadas.

## Catálogo ASF consultado el 13 de noviembre de 2026

La búsqueda pública en `api.daac.asf.alaska.edu/services/search/param` se ejecutó con
`dataset=NISAR`, `processingLevel=GCOV|GUNW`, `dataMaturity=PROVISIONAL`, fechas
`2025-10-01` a `2026-11-13` y las cajas configuradas para cada zona. Los catálogos completos
están en `data/catalog/nisar_ayacucho-huanta_gcov.json` y
`data/catalog/nisar_sabancaya_gunw.json`, con fecha de consulta, nombres, URLs y tamaños.
La consulta devolvió 29 GCOV de Ayacucho entre el 17 de junio y el 17 de octubre de 2026,
y 53 GUNW de Sabancaya entre el 1 de noviembre de 2025 y el 8 de octubre de 2026.
Estos resultados sustituyen las cantidades estimadas del plan para esta ejecución.
[Manual de búsqueda ASF](https://docs.asf.alaska.edu/api/keywords/)

### Dos fechas de Ayacucho autorizadas para antes y después

Ambas observaciones pertenecen a la trayectoria 75 ascendente, marco ASF 171,
configuración `2005_DHDH_A` y polarizaciones principales HH/HV.

| Adquisición UTC | Tamaño del HDF5 | Identificador |
|---|---|---|
| 2026-06-19 10:50:10 | 1 954 545 664 bytes | `NISAR_L2_PR_GCOV_023_075_A_171_2005_DHDH_A_20260619T105010_20260619T105045_P05023_N_F_J_001` |
| 2026-10-05 10:50:07 | 1 908 408 320 bytes | `NISAR_L2_PR_GCOV_032_075_A_171_2005_DHDH_A_20261005T105007_20261005T105041_P05023_N_F_J_001` |

El usuario autorizó estas dos fechas, aproximadamente 3,86 GB en total. La selección se
comprobó mediante el comando siguiente, que consulta metadatos y conserva la misma geometría.

```powershell
.venv/Scripts/sarlab search --aoi ayacucho-huanta --start 2026-06-01 --end 2026-11-13 --track 75 --frame 171 --direction ASCENDING --dates 2026-06-19 2026-10-05
```

Para descargar las dos observaciones seleccionadas se añaden `--download --limit 2`.
El proceso carga `EARTHDATA_TOKEN` desde el entorno normal de la aplicación. Se comprueba
su presencia sin imprimir su valor. Después se ejecutan `sarlab ingest` y `sarlab inspect`
sobre los archivos reales antes de procesarlos.

La observación del 23 de septiembre usa `SHSH` y carece de HV, por lo que se excluyó de la
comparación de vegetación. Dos fechas permiten antes y después. La proyección de tendencia
permanece pendiente hasta disponer de al menos cuatro fechas compatibles.

### Acceso por rangos y Sabancaya

ASF documenta lectura por rangos HTTPS con `fsspec` y `h5netcdf`, que también exige
autenticación Earthdata. Se verificó la documentación, pero todavía no se ha inspeccionado
un archivo GUNW real en esta ejecución. Sus rutas y su conversión a desplazamiento siguen
pendientes de `sarlab inspect` y de la especificación del producto. Los GUNW de la trayectoria
46 ascendente y marco 170 de agosto a octubre de 2026 pesan aproximadamente 2,55 GB por par.
[Acceso y streaming oficiales de NISAR](https://nisar-docs.asf.alaska.edu/asf-search/)

### Publicación y exposición territorial

El flujo GCOV publica la geometría de alertas en EPSG 4326, el área en hectáreas, el número
de píxeles y los gránulos de origen. La confianza permanece `por_validar`. La cortina obtiene
los COG anteriores y posteriores del campo `comparison` y comparte un rango calculado con
los percentiles 2 y 98 de ambas observaciones.

El comando `sarlab exposure` calcula exposición con archivos locales reales. WorldPop debe
declarar `--population-unit people_per_pixel` y su fecha. WorldCover aporta las clases 40
(cultivos) y 10 (árboles), con áreas geodésicas si la rejilla está en lon/lat. Los puntos OSM
se cuentan dentro del área de cambio y a 2 km a su alrededor. Se exige la fecha de cada
fuente suministrada. Sin una fuente, su métrica permanece nula. El resultado se guarda en
`data/04_published/exposure/<zona>.json`. La exposición aproximada no confirma daños.
[Población WorldPop](https://hub.worldpop.org/project/categories?id=3),
[ESA WorldCover](https://esa-worldcover.org/en/data-access)

```powershell
.venv/Scripts/sarlab exposure --aoi ayacucho-huanta --population data/02_interim/worldpop.tif --population-unit people_per_pixel --population-date 2025-01-01 --landcover data/02_interim/worldcover.tif --landcover-date 2021-01-01 --places data/02_interim/places.geojson --places-date 2026-11-13
```

Las fechas de cada entrada corresponden a su capa. Se guardaron los recortes de WorldPop
Global2 R2025A para 2025 (100 m, personas por píxel) y ESA WorldCover 2021 v200 (10 m) en
`data/02_interim/ayacucho-huanta/`. El archivo `sources.json` registra sus URLs y fechas.
El script `scripts/cache_ayacucho_exposure.py` regenera ambos recortes. El conjunto local de
cuatro localidades OSM del globo sirve como referencia visual. Una estimación completa de
centros poblados requiere un inventario que cubra la zona de estudio y su entorno.

`scripts/process_ayacucho.py` comprueba el token en tiempo de ejecución, selecciona las dos fechas
autorizadas, ingiere, guarda el inventario HDF5 en `data/catalog/ayacucho-huanta-inspect.txt` y
procesa HH, HV y la exposición disponible. La ejecución se detuvo al faltar Earthdata.
