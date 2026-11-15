# 27 · Verificación de fotos reales (R1–R5)

15 de noviembre de 2026. Se implementaron los cinco pasos autorizados juntos. La incorporación es a la ficha existente; no cambia la navegación principal ni los cálculos NISAR.

## Implementación

- **R1:** `photos.py` y `sarlab photos --aoi ayacucho-huanta`. Especies desde recetas y suelos; resolución taxonómica explícita antes de consultar iNaturalist. Se aceptan CC BY, CC BY-SA y CC0 con fecha y crédito. Las observaciones cercanas son de grado de investigación, solo plantas, coordenadas públicas y precisión declarada ≤ 100 m. Las consultas se agrupan a 0,05°, cubriendo la celda y filtrando después a ≤ 5 km del polígono real. Máximo seis especies por celda. El catálogo distingue crédito de la fotografía de usuario de la observación.
- **R2:** `place_imagery.py` y `sarlab place-imagery --aoi ayacucho-huanta`. Se descargan imágenes nuevas de NASA GIBS con solicitudes WMS archivadas, EPSG:4326, extensión, dimensiones, fecha y resolución objetivo de 30 m. Se recorta la mancha + 300 m en proyección métrica y se dibuja su contorno. No se atribuye una georreferencia a los PNG antiguos. La cobertura se comprueba antes de dibujar el contorno para evitar que una línea amarilla haga pasar una imagen vacía por válida.
- **R3:** nueva pestaña **Ver el lugar**. Línea temporal, especies propuestas, observaciones cercanas, comunidad/exposición y suelo estimado; fotos diferidas con crédito y enlace original. Pestañas accesibles con flechas, Inicio y Fin. Plantas de referencia no equivalen a presencia en la mancha, y WorldPop no se presenta como censo del pueblo.
- **R4:** escenario a 3 y 5 años, rotulado como supuesto. Las cifras quedan ocultas mientras la referencia no esté verificada, también en el componente de escenario anterior. Se prepararon dos referencias reales de andenería existente en otro lugar; no se presentan como un ensayo de restauración. Se omiten fotografías sin archivo local verificado.
- **R5:** miniaturas georreferenciadas sobre el mapa al seleccionar la mancha. Índice accesible, ajuste del mapa a las ubicaciones y vista de la foto con crédito y distancia; Escape cierra y devuelve el foco. En móvil el índice no tapa el panel abierto: se utiliza al explorar el mapa.

## Datos efectivamente publicados y límites

```text
sarlab photos --aoi ayacucho-huanta
species_with_photo=9 / 9
nearby_observations=64
licensed_photos=73
community_photos=0
technique_photos=0

sarlab place-imagery --aoi ayacucho-huanta
zones=498 images=1418 missing=76
past=422 before=498 after=498
```

**No todas las fotografías previstas están disponibles.** Wikimedia responde HTTP 403 con su política de robots, tanto en la API como en los archivos y miniaturas oficiales. No se eludió esa restricción. El catálogo conserva la advertencia; comunidad, referencia de suelo y fotografías de técnicas muestran ausencia explícita. Mapillary es opcional y no se activó ni se solicitaron credenciales. Las nueve especies se obtuvieron de iNaturalist, con nombres científicos contrastados (incluidos los sinónimos aceptados Jarava ichu y Tara spinosa).

**El pasado no se declara libre de nubes por píxel.** La búsqueda encontró nueve gránulos HLS L30 de 2016–2018 con nubosidad de escena ≤ 5 %. Se selecciona el más antiguo consultado que cubre el recorte; la nubosidad y la escena quedan visibles. Esto reemplaza la pretensión de asegurar «sin nubes» a partir de una visualización RGB. Las 76 manchas que no cumplen cobertura y calidad histórica conservan estado vacío. Ejemplo publicado: 25-ene-2016, 5 % de nubosidad en la escena. Los ópticos del presente son 22-jun y 8-oct-2026, distintos de las adquisiciones radar 24-jun y 10-oct; la ficha lo advierte.

No se inventaron fotos de comunidades, clases de suelo observadas, participantes, resultados de restauración ni imágenes futuras. No se generaron imágenes con IA. Los archivos locales y las cachés de respuestas ocupan aproximadamente 208 MB, dentro de `data/04_published`; no se escribió en `data/01_raw`. Los datos publicados siguen fuera de Git y deben copiarse al desplegar.

## Verificación

```text
uv run pytest -q
164 passed, 5 warnings (avisos conocidos de Rasterio)

uv run ruff check services
All checks passed!

npm --prefix apps/web run typecheck
Sin errores

npm --prefix apps/web test
6 archivos · 16 pruebas aprobadas

npm --prefix apps/web run build
Aprobado; aviso conocido del tamaño de Cesium

Impeccable detect: []

uv run python tools/verify/place-photo-publication.py
73 fotografías con crédito/licencia/archivo local
9 especies; 498 manchas
3 atribuciones «esta zona» contrastadas con distancia + incertidumbre < 500 m
422 imágenes históricas, 498 antes y 498 después
Tres recortes de causas distintas: hashes distintos
```

Los 23 casos nuevos de Python prueban licencias rechazadas, créditos, privacidad, precisión, distancia al polígono, caché, rechazo remoto, almacenamiento local, límites de descarga, recortes, filtro de nubes y endpoints seguros. Los datos sintéticos están exclusivamente en `services/pipeline/tests`.

```text
node tools/verify/place-evidence.mjs
1366×768: incendio/sequía (014), erosión (004), estrés hídrico (080)
5 pestañas por ficha; 5, 4 y 4 pines; apertura y cierre de foto comprobados
errors=[]; llamadas del navegador a proveedores de fotos=[]
375×812: clientWidth=349, scrollWidth=349; teclado End selecciona Ver el lugar
```

Las imágenes fuera del área visible permanecen sin cargar por diseño (`loading=lazy`). Los archivos y miniaturas se auditaron por separado. Capturas en `deploy/verificacion-r27`: las tres causas, su escenario sin cifras, los pines y la ficha móvil. El control móvil adicional está en `tools/verify/place-photos-mobile.mjs`.

Fuentes técnicas consultadas: [Imageinfo](https://www.mediawiki.org/wiki/API:Imageinfo), [Geosearch](https://www.mediawiki.org/wiki/API:Geosearch), [buenas prácticas iNaturalist](https://www.inaturalist.org/pages/api+recommended+practices), [transformación geométrica Shapely](https://shapely.readthedocs.io/en/stable/reference/shapely.transform.html). Las dos referencias de andenería con metadatos comprobados son [Cabanaconde, Pethrus, 2009](https://commons.wikimedia.org/wiki/File:Agricultural_terraces,_Cabanaconde,_Peru.jpg) y [Písac, Unukorno, 2013](https://commons.wikimedia.org/wiki/File:Pisac_Peru_Incan_Terraces.jpg); sus imágenes no pudieron descargarse.


```text
node tools/verify/place-photos-mobile.mjs
mobileMenuAvoidsSheet=true mobilePopup=true plantPhotoLoaded=true errors=[]
```

Se revisaron las capturas finales `mobile.png`, `mobile-map-pins.png`, `mobile-photo.png` y `plants-and-credits.png`: el menú no tapa la ficha móvil, los créditos permanecen legibles y el mapa puede encuadrar las ubicaciones reales.

También se exportó el frontend preparado para el commit a `deploy/r27-review-web` y se ejecutó TypeScript sobre esa copia: salida 0. Así se comprobó que las incorporaciones compilan sin depender de los ajustes previos que siguen fuera del índice.
