# contracts

El esquema de una observación está en `alert.schema.json`. Los tipos del navegador están en `apps/web/src/lib/api.ts`. FastAPI publica la descripción de rutas en `/openapi.json`.

`GET /api/alerts?include_live=true` devuelve una colección GeoJSON en EPSG:4326. Cada observación conserva `id`, `kind`, `source`, `source_kind`, `date`, `level`, `confidence`, `metrics` y `granules`. Las detecciones USGS y FIRMS llevan puntos, y los cambios NISAR pueden llevar polígonos. `exposure` contiene métricas y fuentes cuando existe un cruce territorial. `sources` recoge el estado, la fecha de actualización y la disponibilidad de cada fuente complementaria.

`GET /api/layers` incluye `comparison` cuando se publican ambas observaciones. Las teselas de `/api/tiles/{layer_id}/{stage}/{z}/{x}/{y}.png` resuelven el archivo desde el manifiesto local. `stage` admite `change`, `before` y `after`.
