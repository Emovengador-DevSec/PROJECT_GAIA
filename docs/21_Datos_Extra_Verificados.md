# Datos extra de Ayacucho · D1–D4

14 de noviembre de 2026. Continúa el plan 18 después del commit `4d33332`, que cerró las correcciones de la revisión 19. La publicación en internet está aplazada por indicación del usuario; la entrega de esta fase se prueba en la PC y en Docker.

## D1 · Cultivos y pendiente

El relieve local de la vista 3D tenía 641 muestras a lo largo de 3,5° de longitud: aproximadamente 600 m entre muestras. Para el cálculo se descargaron **63 GeoTIFF originales de Mapzen**, zoom 12, **9,97 MB** en total. Se inspeccionaron su CRS EPSG:3857, banda única, 512×512 muestras, resolución de unos 19 m en esa proyección y valor nulo −32768. Son un DEM compuesto; no tienen una única fecha de observación. [Fuente](https://registry.opendata.aws/terrain-tiles/) · [Atribuciones](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).

Los archivos entraron por `00_inbox` y `sarlab ingest` los archivó con SHA-256. El procesamiento incorpora margen alrededor de la zona, reproyecta las alturas a UTM 18S con píxeles de 30 m y calcula la pendiente por diferencias finitas. Excluye los bordes y conserva valores desconocidos cuando no hay elevación válida. El umbral exploratorio es **15°**, aproximadamente 26,8 %; no es un umbral oficial de peligro.

Cada píxel de cultivo WorldCover 2021 se pondera por su fracción de intersección con una mancha HV activa. Se muestrea la pendiente en su centro. Las clases se reparten con una precisión de 0,001 ha conservando el total original de cultivo por mancha. El cruce del periodo activo da:

| Clase | Cultivos con cambio HV |
|---|---:|
| Hasta 15° | 460,314 ha |
| Más de 15° | 58,046 ha |
| Pendiente desconocida | 0,000 ha |
| Total | 518,360 ha |

Las fichas provinciales y distritales recortan los polígonos antes de recalcular las clases. La clasificación no convierte la caída de HV en suelo desnudo ni mide erosión. La [FAO](https://www.fao.org/soils-portal/soil-degradation-restoration/evaluacion-de-los-indicadores-globales-de-la-salud-del-suelo/salud-del-suelo-fisica/es/) explica que lluvia, suelo, cobertura y pendiente intervienen en la erosión hídrica. Se presenta como condición para investigar, no como daño observado.

## D2 · Comparación óptica HLS

Se confirmó `HLS_S30_Nadir_BRDF_Adjusted_Reflectance` en las capacidades WMS de GIBS y en sus [metadatos oficiales](https://gibs.earthdata.nasa.gov/layer-metadata/v1.0/HLS_S30_Nadir_BRDF_Adjusted_Reflectance.json). Corresponde a HLSS30 v2.0 de LPCLOUD, resolución nominal 30 m. CMR confirma escenas de las teselas T18LWL y T18LXL del **22-jun y 8-oct de 2026**, dos días antes de cada observación NISAR. Los cuatro identificadores aparecen en la interfaz.

Los dos recortes usan la misma caja y dimensiones, 1536×1843, y ocupan 15,28 MB. Tienen más del 99,99 % de píxeles con alfa válido. **Esto no equivale a porcentaje libre de nubes**: no se aplicó una máscara cuantitativa de nubes. La inspección visual conserva las nubes y los huecos y la ficha explica esa limitación. Son imágenes ópticas complementarias, separadas de NISAR. La cortina mantiene las fechas originales.

## D3 · Evidencia agrícola oficial

- [SENAMHI, maíz al 10-jun-2026](https://www.senamhi.gob.pe/load/file/02950SENA-300.pdf): cosecha observada en Chilcayoc y Paucaray, Ayacucho.
- [SENAMHI, segunda década de octubre de 2025](https://www.senamhi.gob.pe/load/file/02950SENA-277.pdf): siembra y crecimiento inicial del maíz en Pauza, Chilcayoc y Lampa, Ayacucho. La fecha 20-oct corresponde al cierre de la década observada.

Se presentan como contexto estacional de otras localidades y campañas. No se generaliza un calendario idéntico a cada parcela de Huamanga, Huanta o La Mar en 2026. La hipótesis de cosecha requiere contraste local y óptico.

## D4 · Archivo de focos MODIS

El descargador consulta la colección **MODIS_SP** de NASA FIRMS en la caja NISAR, en ventanas de hasta cinco días. La API de disponibilidad confirmó cobertura del producto desde 1-nov-2000 hasta 31-ago-2026. No se mezclan VIIRS NRT y MODIS histórico.

Cada intento reserva de antemano sus días consultados en `data/catalog/firms-transactions.json`, bajo bloqueo y escritura atómica. También cuentan los fallos y reintentos. Como el coste real de NASA puede superar los días pedidos, antes de **cada** descarga se consulta también el contador oficial de la cuenta. El descargador espera si ya hay 3500 transacciones usadas, dejando margen respecto del límite de 5000. Si no puede verificarlo, se detiene sin publicar una serie parcial. Se conservan las consultas sin detecciones con su cabecera original. Una consulta ausente nunca se convierte en cero.

La publicación exige originales para **9131 días**, del 1-ene-2001 al 31-dic-2025. Elimina duplicados exactos de fecha, hora, satélite y coordenadas y comprueba que los totales anuales y mensuales coincidan. Los focos no equivalen a incendios únicos ni a área quemada. La incorporación de Aqua en 2002, las nubes y la cobertura de observación limitan las comparaciones entre años. [API oficial](https://firms.modaps.eosdis.nasa.gov/api/area).

El archivo completo publicado contiene **1827 CSV originales**, **9131 días consultados** y **914 detecciones**. La suma anual coincide con la mensual. Agosto acumula 305 detecciones en los 25 años, el mayor recuento mensual. Las consultas sin detecciones se conservan como CSV con cabecera; no representan una afirmación de ausencia de incendios en el terreno.

## Reproducción

```powershell
uv run python scripts/download_agricultural_terrain.py
uv run sarlab ingest
uv run python scripts/publish_agriculture.py
uv run python scripts/publish_community.py --districts deploy/community-source/hdx-districts.zip
uv run python scripts/cache_complementary.py --aoi ayacucho-huanta --layer hls-optical
uv run python scripts/download_fire_history.py
uv run sarlab ingest
uv run sarlab fire-history --aoi ayacucho-huanta
```

El descargador reanuda ventanas pendientes y el de publicación rechaza huecos. Las credenciales se consumen en el servidor y no se registran en los CSV, metadatos, interfaz ni commit. Los paquetes de ejecución incluyen solo los resultados publicados y los recortes visuales; los originales permanecen fuera de la imagen Docker.

## Comprobaciones

Pendiente física de un plano, conservación de superficies con valores nulos, rechazo de días ausentes, eliminación de duplicados y persistencia de las reservas se cubren con pruebas aisladas. La revisión independiente de seguridad no dejó hallazgos bloqueantes; se corrigieron la contabilización de intentos FIRMS y la escritura atómica del resumen agrícola. Las auditorías Python y npm de producción devolvieron cero vulnerabilidades conocidas.

```text
pytest: 61 passed, 5 warnings in 2.61s
ruff: All checks passed!
typecheck: sin errores
Docker build: aprobado, 2100 módulos web
SHA-256: 1893 originales complementarios verificados, 90,73 MB
```

Las cinco advertencias de Rasterio proceden de imágenes sintéticas de prueba. Vite conserva la advertencia conocida sobre el tamaño del módulo Cesium. `doctor.py` terminó sin errores y tres avisos de la sesión: `uv` fuera de PATH y las dos credenciales ausentes del entorno de esa consola; el diagnóstico no abre `.env`. La API normal y Docker verificaron ambas credenciales activas sin imprimirlas.

La imagen final `gaia-alerta:datos-extra` sirve el proyecto en vivo en `http://127.0.0.1:7860`, con 33 archivos de ejecución y 275,26 MB de datos. No contiene archivos `.env` ni originales `.h5`, `.nc4` o `.csv`. Los reportes conservan el volumen local persistente. Se conserva el contenedor de revisión 19 como respaldo detenido.

Chrome verificó la pendiente, las dos imágenes ópticas y el historial completo a 1440×900 y 390×844: `slope=true`, `opticalImages=2`, `modis=true`, `errors=[]` en ambos casos. Al abrir Tiempo se cierra la cortina para dejar espacio al gráfico en el teléfono. Las capturas finales están en `deploy/verificacion-datos-extra-docker`, con tres evidencias elegidas en `art/verificacion/datos-extra` para el README.

El recorrido comunitario del contenedor final pasó también a 1440×900, 1600×900 y 390×844: `community=true`, `printPages=1`, `errors=[]`. Incluye Chosica, cambio de localidad y serie NISAR. Las capturas quedan en `deploy/verificacion-comunidad-final`.

Tras completar el archivo, USGS y NASA FIRMS respondieron `status=ok`, `stale=false` en el contenedor, con actualizaciones del 14-nov-2026 a las 08:49:45 y 08:49:47 UTC. La ingesta histórica no sustituye esas observaciones actuales.
