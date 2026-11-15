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
  cambio y la composición propia HH/HV usan los dos HDF5 autorizados y procesados de la
  trayectoria 75.
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
  Actualización 14-nov-2026: aceptadas las condiciones GES DISC de la cuenta,
  se descargaron los tres originales `3B-DAY-L.MS.MRG.3IMERG.202602{22,23,24}-S000000-E235959.V07B.nc4`
  (80.451.948 bytes) desde las URL de CMR, colección `GPM_3IMERGDL`, versión 07.
  Entraron por `00_inbox` y `sarlab ingest` los archivó con SHA-256 en `01_raw/gpm/imergdl/2026/02`.
  `sarlab inspect` confirmó las variables en la raíz: `precipitation` (1,3600,1800),
  dimensiones `(time,lon,lat)`, unidades `mm/day`; `lat` usa `degrees_north`,
  `lon` usa `degrees_east` y `time` tiene `standard_name=time`.
  El lector reconoce las coordenadas por estos atributos CF, sin asumir su orden.
  `sarlab rainfall --aoi chosica-rimac --variable precipitation <tres originales>`
  publicó 4,99 / 2,84 / 5,79 mm diarios y 13,62 mm acumulados, con 100 % de cobertura común.
  Es IMERG **Late**, una estimación satelital regional de unos 10 km, complementaria a NISAR.
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
- Inspección local del gránulo de Ayacucho del 19 de junio de 2026. `sarlab inspect`
  confirmó las capas anteriores en `frequencyA`, con matriz de 16 200 × 16 632 y
  potencia HH/HV `float32`. Proyección WGS 84 / UTM 18S (`EPSG:32718`), píxel de 20 m.
  `mask` es `uint8`; el atributo del archivo indica `0` para muestras que no se
  enfocaron por completo y `255` para relleno exterior. En el rectángulo proyectado
  de recorte había 1 620 449 valores HV positivos y finitos y 156 574 píxeles de
  subfranja válida antes de recortar el polígono y cruzarlo con octubre. Se aplica
  la máscara del producto y se conserva la cobertura común en el cambio y la cortina.

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

### Resultados con los HDF5 de Ayacucho

Los dos archivos se descargaron por rangos HTTPS autenticados, se verificaron contra
los tamaños publicados en ASF y se registraron con SHA-256 mediante `sarlab ingest`.
`sarlab inspect` confirmó las mismas rutas HH, HV y máscara en ambos HDF5.
La ventana común contiene 151 592 píxeles válidos de 20 m, el 1,69 % de la caja del caso.
Se limita a una franja en el borde occidental. La comparación aplica el recorte de la
zona y conserva esa máscara en ambas imágenes y en la diferencia.

| Polarización | Umbral respecto a la mediana | Caída significativa | Polígonos de al menos 25 píxeles | Área de los polígonos |
|---|---:|---:|---:|---:|
| HH | 2,60 dB | 29,28 ha | 3 | 3,16 ha |
| HV | 3,18 dB | 52,76 ha | 5 | 7,12 ha |

Con 3 veces la dispersión robusta, HV detectó la mayor extensión de caída de señal.
La señal puede responder a varios procesos. La atribución a incendios y la extrapolación
a Huanta y La Mar requieren validación independiente y mayor cobertura.
La serie usa los píxeles válidos de cada adquisición. Las medianas HH y HV fueron
−10,561 y −20,385 dB el 19 de junio, y −10,888 y −20,607 dB el 5 de octubre.
La cobertura individual fue 1,70 % y 1,69 %, respectivamente.

[Máscara y producto GCOV en ASF](https://nisar-docs.asf.alaska.edu/gcov/)

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

## G1 · Comparación activa con cobertura completa

La ejecución del 13 de noviembre local sustituyó el período activo por el 24 de junio y el
10 de octubre de 2026, trayectoria 147 ascendente, marco 171, HH/HV, `P05023` en ambas fechas.
Los tamaños verificados son 2.084.569.088 y 2.080.374.784 bytes, 4.164.943.872 bytes en total.
La selección respeta la autorización de dos fechas. Los originales de la trayectoria 75 se
conservan. Sus huellas tocaban aproximadamente el 15 % de la caja y su máscara reducía la
cobertura útil común al 1,69 %. El catálogo completo se guardó en
`data/catalog/ayacucho-g1-asf.geojson`.

El 22 de octubre sí está publicado en la colección validada `NISAR_L2_GCOV_V1`, con
`P05036` y una versión PGE posterior. Se eligió el 10 de octubre para conservar la misma
versión de procesamiento que junio. El 23 de agosto solo tiene HH y se excluyó del par HH/HV.
Las rutas HDF5 se confirmaron con la inspección real de ambos originales y se registraron
en `data/catalog/ayacucho-huanta-inspect.txt` antes del cálculo.
[Catálogo y madurez NISAR de ASF](https://nisar-docs.asf.alaska.edu/asf-search/)

Las rejillas usan EPSG 32718 y píxeles de 20 m. La máscara conserva subfranjas válidas y
excluye `0` y `255`. Cada fecha tiene el 99,92 % de cobertura válida y la intersección
conserva el 99,91 %, equivalente a 359.375,92 ha. El proceso prepara los resultados en un
directorio temporal y activa el período mediante `active-comparison.json` solo cuando se
completan ambos canales, la serie y la comprobación del 80 % mínimo. La app pide el período
activo a la API. Las capas archivadas siguen consultables por identificador.
[Especificación GCOV](https://nisar-docs.asf.alaska.edu/gcov/)

| Polarización | Umbral robusto | Caída total | Manchas ≥25 píxeles | Área delimitada |
|---|---|---|---|---|
| HH | 2,49 dB | 4.240,44 ha | 608 | 1.560,92 ha |
| HV | 2,63 dB | 3.607,00 ha | 498 | 938,28 ha |

Los totales incluyen fragmentos menores que 25 píxeles, una hectárea en esta rejilla.
La ficha destacada toma el total HV del manifiesto. La ficha de cada mancha muestra su
propia superficie. El suavizado es un promedio de 3×3 en dB, seguido de diferencia entre
fechas y umbral de tres dispersiones robustas respecto a la mediana del cambio.
La diferencia de retrodispersión conserva múltiples interpretaciones físicas.

## G2 · Exposición de las manchas activas

Se cruzaron las 1.106 manchas del par activo con WorldCover 2021 v200 y WorldPop
Global2 R2025A de 2025. Overpass devolvió 1.192 localidades OSM en la caja ampliada a
[-74,43, -13,43, -73,87, -12,77], con fecha de base 14 de noviembre UTC. Cada distancia
se mide desde la localidad hasta la mancha en metros, con un máximo de 2 km.
Los archivos y sus licencias están en el registro `sources` de la exposición publicada.
[WorldPop](https://www.worldpop.org/), [WorldCover](https://esa-worldcover.org/en/data-access),
[OpenStreetMap](https://www.openstreetmap.org/copyright)

La intersección geométrica de cada celda WorldCover y cada mancha permite reconciliar
las categorías con el área geodésica. La diferencia máxima fue 0,00138 ha por mancha.
WorldPop pondera la fracción de cada píxel dentro del polígono. Los valores enmascarados
se conservan como falta de dato. La suma sobre la unión HV da 436,2 personas estimadas
en cobertura disponible, con 243 de 498 manchas sin píxeles válidos WorldPop. Es una
estimación parcial. Las manchas HV incluyen 518,36 ha de cultivo, 19,055 ha de árboles,
384,143 ha de pastizal y 17,282 ha de otras clases. Hay 632 localidades distintas a 2 km.
Auditoría guardada en `data/catalog/ayacucho-g2-verificacion.json`.

## G3 · Contraste cuantitativo con OPERA

CMR devolvió dos teselas OPERA DIST-ALERT-HLS del 13 de octubre de 2026, T18LWL y T18LXL.
Se descargaron con Earthdata los TIFF originales `VEG-DIST-STATUS` y `VEG-DIST-DATE`.
Las etiquetas reales confirman clases 0–8, relleno 255 y fecha en días con nodata −1.
La especificación fija el origen temporal en el 31 de diciembre de 2020.
Los nombres y URLs originales están en `data/catalog/ayacucho-g3-opera.json`.
[Algoritmo oficial OPERA DIST](https://lpdaac.usgs.gov/documents/1835/OPERA_DIST_ATBD__V1.pdf)

Ambas teselas se reproyectaron con vecino más próximo a la rejilla NISAR. La cobertura
común ocupa el 100 % del radar válido. Se tomaron perturbaciones confirmadas de clases
3, 6, 7 y 8 con inicio posterior al 24 de junio y hasta el 10 de octubre. OPERA presenta
1.703,16 ha en ese intervalo y coincide en 21,08 ha con las 938,28 ha de manchas HV
delimitadas. El cociente sobre NISAR es 2,25 % y la intersección/unión es 0,80 %.
Se muestran ambos cocientes y sus denominadores. La coincidencia limitada conserva
la hipótesis de incendios como `por_verificar`. Los datos actuales sostienen un cambio
de señal medido y requieren observaciones independientes para explicar su causa.
## Ampliación agrícola y archivo MODIS · 14-nov-2026

Los originales Mapzen y los CSV de FIRMS también entran por `00_inbox` y `sarlab ingest`.
La ingesta comprueba contenedor, CRS y tamaño de las teselas Mapzen y cabecera, fechas y
coordenadas de los CSV. Conserva SHA-256 y nombres de consulta. La fecha de los GeoTIFF
se identifica como archivado/recuperación, no como fecha de observación del DEM compuesto.

El cruce de 498 manchas HV con cultivos WorldCover produce 460,314 ha hasta 15° y
58,046 ha por encima de 15°, sin cultivos con pendiente desconocida. La suma conserva
518,360 ha. Es una clasificación exploratoria; no es una medición de erosión ni prueba
de suelo desnudo. `docs/21_Datos_Extra_Verificados.md` documenta reproyección y ponderación.

Las capacidades y metadatos GIBS confirman `HLS_S30_Nadir_BRDF_Adjusted_Reflectance`
como HLSS30 v2.0. Los mosaicos del 22-jun y 8-oct de 2026 usan la misma caja y tamaño;
los identificadores CMR T18LWL/T18LXL están en `config/context.yaml` y la interfaz.
Se conserva la imagen con nubes. El alfa válido no se interpreta como máscara de nubes.

MODIS_SP se procesa por fecha y hora originales. La publicación anual exige cobertura
de las consultas de cada día de 2001–2025; los huecos no se convierten en ceros. El
presupuesto FIRMS registra cada intento antes del HTTP, incluidos los reintentos, y
consulta el contador oficial de transacciones antes de descargar, sin almacenar la
clave o una URL que la contenga. Los focos no se convierten en área quemada.

## NISAR L3 SME2 · humedad del suelo (Ayacucho, 14-nov-2026)

Gránulos de la trayectoria 147 ascendente, marco 171, PROVISIONAL, del 24-jun y 16-sep de
2026 (no hay SME2 del 10-oct en esa trayectoria). Rutas confirmadas con `sarlab inspect`:

| Ruta | Tipo | Notas |
|---|---|---|
| `science/LSAR/SME2/grids/soilMoisture` | float32 | m³/m³, `_FillValue` −9999; promedio de recuperaciones recomendadas |
| `science/LSAR/SME2/grids/retrievalQualityFlag` | int16 | bit 0: 0 = recomendada, 1 = no recomendada; bits 1–3: PMI, TSR, DSG |
| `science/LSAR/SME2/grids/soilMoistureUncertainty` | float32 | m³/m³ |
| `science/LSAR/SME2/grids/xCoordinates`, `yCoordinates` | float64 | centros de píxel en metros, 200,18 m |
| `science/LSAR/SME2/grids/projection` | uint32 | atributo `epsg_code` = 6933 (EASE-Grid 2.0) |

`uv run sarlab soil-moisture --aoi ayacucho-huanta <SME2 del 16-sep>` publica
`data/04_published/soil-moisture/ayacucho-huanta.tif` solo con recuperaciones recomendadas:
57,6 % de la caja con dato, mediana 0,175 m³/m³. Hay valor en 337 de las 498 manchas HV
(p10–p90: 0,15–0,22 m³/m³). La fecha (16-sep) es anterior al par de cambio (24-jun → 10-oct)
y así se rotula.

## SoilGrids · clase WRB por mancha

La API `properties/query` no tiene capa `wrb`; la clase sale de `classification/query`
(`wrb_class_name`). Se consulta una vez por celda de 0,05° (~5,5 km) por el límite de uso
justo de ISRIC y se guarda en `data/04_published/soil/ayacucho-huanta.json` (CC BY 4.0).
