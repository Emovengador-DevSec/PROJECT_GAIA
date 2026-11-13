# Hallazgos del dato real

Cada entrada con fecha, archivo de origen y comando usado. Solo rutas vistas en archivos reales o en documentación oficial.

## Fuentes públicas verificadas el 13 de noviembre de 2026

- CelesTrak devolvió NISAR, NORAD 65053, con época `2026-11-13T17:08:21.411744` UTC.
  La propagación SGP4 con satellite.js 6.0.2 produjo alturas de 754–758 km en las
  comprobaciones y un desplazamiento superficial de unos 405–407 km en 60 segundos.
  El primer acceso geométrico calculado al centro de Ayacucho cae el 15 de noviembre
  de 2026 a las 10:42 UTC. No confirma una adquisición programada.
  La franja de 240 km usa una aproximación esférica y apuntamiento a la izquierda.
  El contraste con las trayectorias ASF 54, 75 y 147 usa el ciclo nominal de 12 días
  y no asigna una trayectoria oficial a los elementos GP. El ensayo repetido sitúa
  sus centros a unos 46, 134 y 94 km del centro del área de estudio. Son aproximaciones,
  no efemérides precisas. La órbita se oculta al reproducir fechas históricas.
  [Elementos públicos CelesTrak](https://celestrak.org/NORAD/elements/gp.php?NAME=NISAR&FORMAT=json)
  · [Geometría oficial NISAR](https://science.nasa.gov/mission/nisar/mission-overview/)

- Se amplió el archivo público de FIRMS a `J1_VIIRS_C2_South_America_7d.csv`.
  La consulta devolvió 1 143 detecciones dentro de Perú. La secuencia muestra 30 días
  de USGS y siete de FIRMS, indicando ambas coberturas. Un intervalo sin archivo FIRMS
  no se interpreta como ausencia de incendios. La colección de puntos usa primitivas
  de Cesium al superar 1 000 detecciones, conservando cada hora y procedencia.

- El CSV público VIIRS NOAA-20 de 24 horas devolvió 309 detecciones dentro de la frontera
  de Perú en la consulta de las 20:46 UTC. Cada foco conserva fecha, confianza y potencia
  radiativa en MW. La clave FIRMS amplía la consulta a siete días. La copia se guarda en
  `data/catalog/live/fires.json`.
  [Descargas oficiales FIRMS](https://firms.modaps.eosdis.nasa.gov/active_fire/)
- NASA GIBS publica el mosaico diario `NISAR_L2_Geocoded_Polarimetric_Covariance`.
  Se guardaron recortes de Ayacucho del 17 de junio y 15 de octubre de 2026. El catálogo
  ASF confirma HH/HV, trayectoria 54 descendente y marco 95 para ambas fechas.
  Los mosaicos visuales de GIBS tienen una descomposición RGB de NASA. Los cálculos de
  cambio y la composición propia HH/HV siguen usando los dos HDF5 autorizados de la
  trayectoria 75, pendientes de Earthdata.
  [Visualización NISAR y colores del mosaico](https://nisar-docs.asf.alaska.edu/worldview/)
- Se guardaron imágenes OPERA DIST-ALERT-HLS de Ayacucho del 8 de octubre de 2026 y
  Madre de Dios del 5 de octubre. Son capas visuales de estado de perturbación. La
  concordancia espacial usa los GeoTIFF originales `VEG-DIST-STATUS` y
  `VEG-DIST-DATE`, con acceso Earthdata. El cálculo limita la comparación a la cobertura
  común, perturbaciones confirmadas y fecha inicial dentro del intervalo NISAR.
  [Especificación OPERA DIST-HLS](https://lpdaac.usgs.gov/documents/1766/OPERA_DIST_HLS_Product_Specification_V1.pdf)
- La capa IMERG de GIBS sitúa la precipitación del 25 de febrero de 2026 en Chosica.
  INDECI reportó escorrentía superficial ese día. El acumulado de los tres días previos
  usa productos originales diarios IMERG del 22 al 24. El cálculo exige variables
  inspeccionadas y unidades mm/día, tres fechas consecutivas y píxeles válidos en los
  tres días. Los archivos de NASA respondieron HTTP 401 sin Earthdata.
  Una copia pública NOAA de 2025 presentó numerosos valores faltantes y se descartó para
  publicar un acumulado del caso de 2026.
  [Episodio documentado por INDECI](https://www.gob.pe/institucion/indeci/noticias/1359263-indeci-realizo-visita-tecnica-en-lurigancho-chosica-y-coordino-acciones-de-preparacion-ante-lluvias-intensas)
- El catálogo abierto EODMS devolvió escenas RADARSAT-1 con cobertura de las cuatro
  zonas. Se publicaron recortes visuales de Madre de Dios del 4 de abril de 1998
  (escena `8d7424dd-0a1c-5281-8127-2f43e48c7d33`) y Sabancaya del 3 de septiembre
  de 2001 (`3b6acb74-fe6c-506d-84bc-b953698bc3bb`). Los COG originales tienen cuatro
  puntos de control en EPSG 4326 y amplitud HH uint8. Se reproyectaron a la caja del
  caso para inspección visual. La geometría radar y el relieve limitan su precisión.
  Se conserva la Licencia de Gobierno Abierto de Canadá. La consulta pública de
  RCMImageProducts devolvió cero escenas en las cajas estudiadas.
  [Catálogo EODMS](https://www.eodms-sgdot.nrcan-rncan.gc.ca/search)
- ASF devolvió 27 SME2 provisionales de Ayacucho y 58 GCOV provisionales de Chosica.
  Los catálogos están guardados en `config/catalog/`. La inspección interna de SME2
  y la lectura de humedad siguen pendientes de archivos originales.

`scripts/cache_complementary.py` regenera los siete PNG publicados en
`data/04_published/context/`. Las escenas de RADARSAT-1 se leen por rangos y se
reducen antes de reproyectar.

```powershell
.venv/Scripts/python scripts/cache_complementary.py
.venv/Scripts/sarlab validate-opera --help
.venv/Scripts/sarlab rainfall --help
```

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
