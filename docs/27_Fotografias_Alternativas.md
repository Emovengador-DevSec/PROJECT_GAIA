# Fotografías alternativas incorporadas

15 de noviembre de 2026. Continuación del plan 27 a petición del usuario: buscar en otras fuentes las fotografías que no se pudieron descargar de Wikimedia.

Se publicaron **seis fotografías nuevas**, sumando **79 archivos fotográficos con crédito y licencia** en el catálogo de Ayacucho:

| Uso | Fotografía y lugar | Autor | Captura | Licencia |
|---|---|---|---|---|
| Técnica | Andenería existente en Moray, Cusco | McKay Savage | 14-abr-2012 | CC BY 2.0 |
| Técnica | Andenería existente en Písac, Cusco | McKay Savage | 6-jul-2012 | CC BY 2.0 |
| Suelo | Cambisol, Alemania | Peter Schad | 3-oct-2013 | CC BY |
| Suelo | Andosol, México | Peter Schad | 6-oct-2016 | CC BY |
| Suelo | Luvisol, Hungría | Peter Schad | 17-sep-2009 | CC BY |
| Comunidad | Tejados de Quinua, Ayacucho | Randal Sheppard (-Chupacabras-) | 19-may-2012 | CC BY-SA 2.0 |

Las copias de las fotografías Flickr se obtuvieron del servicio público de miniaturas Openverse, conservando el enlace al original y su licencia. Sus fechas y lugares se contrastaron con los archivos fotográficos de Commons correspondientes a los mismos identificadores de Flickr. No se usó la fecha de indexación de Openverse como fecha de captura.

Los perfiles de suelo se descargaron de la [galería WRB/ISRIC](https://wrb.isric.org/picture-gallery.html), que declara licencia Creative Commons Attribution sin indicar versión. El nombre Peter Schad está visible en las imágenes y las fechas proceden del campo EXIF `DateTimeOriginal`. Se rotulan explícitamente como ejemplos de otros países, fuera de los Andes; no son muestras de suelo de las manchas NISAR.

La foto de Quinua tiene coordenadas publicadas (-13,048675; -74,138194). Solo se asocia a seis comunidades cuyos centros publicados están a ≤ 2 km de esa cámara: Chectapampa, Ojerumi, Apucancha, Ccerayocc, Perezuela y Sancapata. Sigue titulada como Quinua, con la distancia real a la mancha: no se presenta como seis fotos distintas ni se le atribuye otro pueblo. No se declara precisión métrica que la fuente no proporciona.

## Integración y reproducción

Las referencias revisadas están en `config/nbs/photo_references.yaml`. El recolector acepta únicamente los proveedores nuevos explícitamente autorizados y mantiene la validación de autor, fecha, licencia, límites de tamaño y nombres de archivo. Las fotografías se publican con:

```text
uv run sarlab photos --aoi ayacucho-huanta
```

Los endpoints y la ficha existentes las incorporan automáticamente. Los archivos publicados permanecen en `data/04_published/photos/`, fuera de Git. No se cambiaron los componentes ni la navegación de la interfaz en esta continuación.

## Verificación

```text
uv run ruff check services
All checks passed!

uv run pytest -q services/pipeline/tests/test_place_photos.py
24 passed

uv run python tools/verify/place-photo-publication.py
79 fotografías con crédito, fecha, licencia y archivo local
9 especies; 498 manchas; distancias y recortes comprobados

node deploy/alt-verify.mjs
techniquePhotos=2 soilPhoto=true communityPhoto=true externalPhotoRequests=[]
```

Revisión visual de las seis imágenes y capturas de la interfaz en `deploy/alternative-photos`: `terraces.png`, `soil.png`, `community.png`. Se añadió una prueba de proveedores de referencia aceptados y rechazo de dominios ajenos.

## Lo que sigue sin fotografía verificable

Todavía faltan referencias andinas descargables con metadatos completos para zanjas de infiltración, qochas, cortafuegos vivos, agroforestería y bioingeniería con ichu. Las imágenes de noticias oficiales encontradas no tenían una licencia fotográfica de reutilización suficientemente explícita. El perfil Leptosol del catálogo consultado carece de una fecha de captura válida; no se publicó. Los demás pueblos no reciben fotos de Quinua si están fuera del radio comprobado. La limitación histórica de 76 manchas no cambió.

Fuentes de contraste de las fotografías: [Moray](https://commons.wikimedia.org/wiki/File:Peru_-_Cusco_Sacred_Valley_%26_Incan_Ruins_045_-_Moray_(7094833217).jpg), [Písac](https://commons.wikimedia.org/wiki/File:Peru_-_Sacred_Valley_%26_Incan_Ruins_191_-_Pisac_(8114559846).jpg), [Quinua](https://commons.wikimedia.org/wiki/File:Rooftops_of_Quinua,_Ayacucho,_Peru_(7271081812).jpg). Las URLs de descarga y los identificadores Openverse exactos constan en la configuración.

Batería completa tras la incorporación: uv run pytest -q → 165 passed, 5 avisos conocidos de Rasterio.
