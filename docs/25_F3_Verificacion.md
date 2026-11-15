# F3 · Imágenes regionales fuera de las fichas individuales

Verificado el 14 de noviembre de 2026, hora de Lima. Se aplica la alternativa explícita de F3: sin georreferencia archivada verificable, retirar las fotos de la ficha y conservar el acceso a la imagen regional en Cambios.

## Evidencia y decisión

Los dos PNG HLS de `data/04_published/context/ayacucho-huanta` tienen 1536×1843 píxeles. Rasterio informa `crs=None` y transformación identidad en ambos. La carpeta no contiene manifiestos geográficos ni archivos auxiliares que vinculen los píxeles descargados con la extensión y la consulta originales.

`scripts/cache_complementary.py` documenta cómo se construye una consulta WMS 1.1.1 a GIBS con EPSG:4326 y la caja configurada. El doc 21 identifica las fechas y el uso regional de las imágenes. Esto permite entender la intención de la consulta, pero no aporta un registro geográfico archivado asociado a esos PNG. F3 no presupone esa asociación para dibujar contornos de manchas concretas.

No se generaron recortes, contornos ni endpoints que aparenten servirlos. `_build_optical_context` devuelve `None`, y se regeneró la publicación de las 498 manchas. La ficha retira los dos PNG regionales incluso si recibe datos antiguos que todavía anuncien sus URLs. En su lugar informa de la falta del recorte verificado y ofrece «Ver imagen de toda la zona», que abre Cambios conservando el territorio elegido. Las imágenes originales y sus fechas se mantienen allí.

## Verificaciones

```text
uv run sarlab remediation --aoi ayacucho-huanta
498 manchas · alto=0 medio=61 bajo=437

uv run pytest -q
132 passed, 5 warnings in 13.41s

uv run ruff check services
All checks passed!

npm --prefix apps/web test
3 archivos · 13 pruebas aprobadas

npm --prefix apps/web run typecheck
Salida 0, sin errores

npm --prefix apps/web run build
✓ built in 15.29s

node tools/verify/zone-optical.mjs
1366×768 · zona 000: zonePhotos=0, regionalHlsInChanges=true, errors=[]
375×812 · zona 014: zonePhotos=0, regionalHlsInChanges=true, errors=[]
```

Las nuevas pruebas comprueban que la función no asigna fotos regionales como recortes y que ninguna mancha publicada anuncia un `optical_context` no verificado. La prueba de hashes diferentes entre recortes no corresponde a esta alternativa: no se publican recortes. No hubo pruebas omitidas. Persisten los avisos conocidos de Rasterio y del tamaño de Cesium.

Capturas revisadas en `deploy/verificacion-f3`: `ficha-1366.png`, `ficha-375.png`, `cambios-1366.png` y `cambios-375.png`.

F4–F7 siguen pendientes. F3 no valida ni corrige el escenario NDVI, costos, Minka o el resto de la ficha. Los cambios visuales anteriores permanecen fuera de este commit.
