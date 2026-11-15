# 27 · Ver la zona con fotos reales: pasado, presente y futuro (plan para Codex)

Escrito el 15 de noviembre de 2026. Hoy la ficha de cada zona dice **qué hacer**, pero no **muestra** el lugar. Faltan fotos del suelo, de las plantas que se recomiendan, de la comunidad cercana, y una línea de tiempo pasado → presente → futuro.

## 0. Reglas (no se negocian)

1. **Solo fotos reales con autor, fecha y licencia.** Nada generado con IA, ni «la zona restaurada» inventada (regla 1 de `CLAUDE.md` y regla 4 del doc 23).
2. Cada foto dice **qué es y de dónde es**:
   - «esta zona» solo si está georreferenciada dentro de la mancha o a < 500 m;
   - «a X km de la zona» si es de un lugar cercano;
   - «ejemplo de la técnica en otro lugar» para las fotos de referencia.
3. El **futuro** es un escenario con supuestos, nunca una foto del futuro. Se muestra con fotos reales de **la misma técnica ya aplicada en otro lugar andino**, rotuladas como tal.
4. Las fotos se descargan una vez, en el servidor, a `data/04_published/photos/` (con su licencia). El navegador no llama a servicios de terceros.
5. **Sin claves nuevas**, salvo Mapillary, que es opcional (sección 3).

## 1. Qué se muestra y de dónde sale

| Bloque | Qué ve el usuario | Fuente real | Clave |
|---|---|---|---|
| **Pasado** | Imagen satelital de la zona en 2016–2018, la fecha más antigua sin nubes | Sentinel-2 L2A o Landsat 8 por GIBS/HLS (Earthdata, ya configurado) | Ya la tienes |
| **Presente** | Imagen antes y después del radar (24 jun → 10 oct 2026), recortada a la mancha con su contorno | HLS S30 ya publicado (docs 21 y 25 F3) | Ya la tienes |
| **Futuro** | Escenario de 3 y 5 años como texto, más 2–3 fotos reales de la técnica recomendada aplicada en otro lugar | Wikimedia Commons (licencias CC) | No |
| **Plantas de la receta** | Foto, nombre común y científico de cada especie (molle, tara, ichu, queñua, maguey…) | Wikimedia Commons por nombre científico; respaldo: iNaturalist (observaciones con licencia CC) | No |
| **Plantas observadas cerca** | Especies registradas por personas a < 5 km de la zona, con foto, fecha y distancia | iNaturalist API, observaciones «research grade» con licencia CC | No |
| **Suelo** | Clase SoilGrids de la zona y una foto de referencia de ese tipo de suelo andino | SoilGrids (ya publicado) + Wikimedia Commons | No |
| **Comunidad** | Fotos geolocalizadas del poblado más cercano y del paisaje a < 2 km | Wikimedia Commons geosearch; Mapillary (fotos a nivel de calle), opcional | Mapillary: sí |
| **Población** | Personas estimadas en la mancha (solo si WorldPop tiene dato) y poblados con distancia | WorldPop y OSM, ya publicados | No |

## 2. Pasos para Codex

### R1 · Recolector de fotos (pipeline)
- Nuevo módulo `services/pipeline/src/sarlab_pipeline/photos.py` y el comando `uv run sarlab photos --aoi ayacucho-huanta`.
- **Especies:** toma los nombres científicos de `config/nbs/recipes.yaml` y `soils.yaml`, busca en Wikimedia Commons (API `action=query&generator=search`, archivos con `extmetadata` de licencia CC BY, CC BY-SA o CC0) y guarda 1 foto por especie, a 800 px.
- **Plantas cercanas:** consulta iNaturalist `GET /v1/observations?lat&lng&radius=5&quality_grade=research&photo_license=cc-by,cc-by-sa,cc0` por zona (agrupando zonas a 0,05°). Guarda hasta 6 especies por celda con su foto, autor, fecha y distancia.
- **Comunidad:** Wikimedia Commons `list=geosearch` con radio de 2 km alrededor del poblado más cercano; hasta 3 fotos.
- **Técnicas:** una lista curada en `config/nbs/technique_photos.yaml` con 2–3 archivos de Commons por técnica (zanjas de infiltración, andenes, qochas, cortafuegos vivos, agroforestería), cada uno con el lugar real. El equipo los revisa a mano.
- Todo se guarda en `data/04_published/photos/<aoi>.json` más las imágenes, con `author`, `license`, `license_url`, `source_url`, `taken_at`, `lat`, `lon` y `distance_km`. Si una foto no tiene licencia clara, se descarta.
- El ritmo y el User-Agent siguen las normas de cada API, con un nombre de cliente genérico (sin datos personales).
- Pruebas con respuestas sintéticas **solo en `services/pipeline/tests`**: descarta fotos sin licencia y calcula bien la distancia.

### R2 · Pasado y presente recortados a la zona
- Recortar en el servidor el HLS antes/después (y una escena antigua sin nubes de 2016–2018) al rectángulo de la mancha + 300 m, con la georreferencia de GIBS, y dibujar el contorno.
- Endpoint `/api/remediation/{aoi}/{zone}/imagery/{past|before|after}.png` más los metadatos (fecha, escena y resolución).
- Si no hay recorte confiable, no se muestra (como en doc 25 F3).

### R3 · Pestaña nueva en la ficha: «Ver el lugar»
Una franja de tiempo con tres columnas y fotos debajo:

```
[ PASADO 2017 ]  [ ANTES jun 2026 ]  [ DESPUÉS oct 2026 ]  [ FUTURO · escenario ]
   satélite         satélite            satélite             texto + fotos de la técnica en otro lugar
```

- **Plantas que sanarán esta zona:** tarjetas con foto, nombre común y científico, y para qué sirve (de `recipes.yaml`).
- **Plantas vistas cerca:** fotos de iNaturalist con «a 2,3 km · 2024».
- **La comunidad:** fotos del poblado cercano con su distancia, más población y cultivo de la zona.
- **Suelo:** clase SoilGrids y foto de referencia rotulada «ejemplo de este tipo de suelo».
- Cada foto lleva un pie con autor y licencia, y abre la fuente original.
- Estilo: el de la ficha (bloques de color, viñetas y textos cortos). Las imágenes se cargan de forma diferida.

### R4 · Futuro honesto
- Barra «hoy → 3 años → 5 años» con la ganancia relativa del escenario y su etiqueta fija «Escenario con supuestos».
- Debajo: «Así se ve esta técnica aplicada en [lugar real]», con 2–3 fotos de `technique_photos.yaml`.
- Mientras la cita del escenario siga «por verificar», se muestran las fotos de la técnica, pero no los números.

### R5 · En el mapa
- Al elegir una zona, aparecen sobre el relieve unos pines pequeños con miniaturas de las fotos de la comunidad y de las plantas observadas, en su ubicación real. Al tocar uno se abre la foto con su crédito.

## 3. Credenciales

| Servicio | ¿Clave? | Para qué |
|---|---|---|
| Wikimedia Commons | No | Plantas, técnicas, suelo y poblados |
| iNaturalist | No (solo lectura) | Plantas observadas cerca |
| NASA GIBS / HLS / Earthdata | Ya la tienes | Pasado y presente satelital |
| Mapillary | **Opcional**: token gratuito en mapillary.com/dashboard/developers → `MAPILLARY_TOKEN` en `.env` | Fotos a nivel de calle de los poblados; sin token se omite |

## 3b. APIs que dan el plus (probadas el 15-nov-2026 desde esta PC)

| API | Qué aporta | Clave | Probado |
|---|---|---|---|
| **Open-Meteo Climate API** (`climate-api.open-meteo.com/v1/climate`) | **Predicción real a futuro:** temperatura y lluvia diarias hasta 2050 con modelos CMIP6 de alta resolución | No | Sí: devuelve noviembre de 2050 para Ayacucho |
| **iNaturalist** (`api.inaturalist.org/v1/observations`) | Plantas y fauna observadas con foto, fecha y lugar | No | Sí: 453 observaciones con foto a < 5 km |
| **GBIF** (`api.gbif.org/v1/occurrence/search`) | Registros científicos con foto de cada especie de la receta en Perú | No | Sí: 487 registros con imagen de *Schinus molle* |
| Wikimedia Commons | Fotos con licencia de especies, técnicas y poblados | No | — |
| **Planet NICFI** (planet.com/nicfi) | Mosaicos satelitales **mensuales de 4,7 m desde 2015**: un pasado mucho más nítido que HLS | Sí: cuenta gratuita con aprobación (días) | — |
| NASA AppEEARS (appeears.earthdatacloud.nasa.gov) | Serie NDVI MODIS 2000–hoy de la zona: cuánto verdor tenía antes | Ya la tienes (Earthdata) | — |

### Cobertura real de fotos (medida el 15-nov-2026)

- **Plantas:** abundante. iNaturalist tiene **128 especies con foto** a < 5 km de una zona de Huanta, entre ellas molle (*Schinus molle*, 7 observaciones).
- **Ciudades:** Wikimedia Commons tiene más de 50 fotos a < 10 km de Huamanga (templos, mercado, artesanía), 11 cerca de Huanta y 7 cerca de San Miguel.
- **Comunidades rurales:** casi no hay fotos abiertas de los poblados pequeños. Lo que aparece son **fotos de astronautas de la ISS (NASA, dominio público)** que muestran la zona desde el espacio. Se usan como bloque «Visto desde la Estación Espacial», no como foto del pueblo.
- **Personas:** no se publican fotos de personas identificables sin su consentimiento.

> **Decisión del equipo (15-nov):** no mostrar ciudades, templos ni artesanía. GAIA es para las comunidades del campo afectadas. Las fotos deben mostrar **cómo está el lugar**: la chacra, la ladera, el camino y el poblado rural.

### Publicación y procedencia

- `uv run sarlab field-photos --aoi ayacucho-huanta` publica los originales de los informes curados en `config/field_sources.yaml`. La ficha de ALICIA del informe regional de 2014 indica CC BY-NC-SA 4.0. Las fichas de Challhuamayo Alta (2020) y Pacchancca (2024) indican CC BY-NC-ND 4.0. Cada foto conserva su leyenda y página. Las coordenadas muestran la ubicación aproximada del lugar documentado.
- `uv run sarlab climate-future --aoi ayacucho-huanta` compara 1991–2020 con 2041–2050 por mes y modelo. `uv run sarlab greenness --aoi ayacucho-huanta` obtiene medianas estacionales del píxel MODIS de referencia desde la copia pública de Planetary Computer, con filtro de calidad y años faltantes explícitos.
- `uv run sarlab field-aerial --aoi ayacucho-huanta` recorta las escenas abiertas Sentinel-2 de 10 m. `uv run python scripts/cache_ayacucho_terrain.py --field-design` publica el relieve Mapzen de referencia para el trazado orientativo de curvas de nivel.
- El moderador consulta la foto pendiente con `GET /api/reports/moderation/{id}/photo` usando el acceso de moderación de C4. La aprobación publica la versión sin EXIF, con autor y licencia CC BY 4.0. El rechazo borra la foto.
- Street View usa `GOOGLE_MAPS_KEY` del servidor y consulta las panorámicas al pulsar el botón. Ofrece un enlace a Google si hay cobertura verificada a menos de 2 km. `GAIA_COMMERCIAL=1` desactiva las fotos de informe sujetas a licencia no comercial.

### R8 · Vista aérea real de la chacra (prioridad sobre R1 para comunidades)
- Vista cenital a unos 600–900 m sobre la zona, usando la imagen satelital del globo que ya está licenciada con Cesium ion (alrededor de 1 m por píxel). Muestra las chacras, los caminos, los árboles y las casas reales.
- Comprobado el 15-nov con la zona 359 (Lucas Pata): a esa escala se distinguen parcelas, senderos y arboledas.
- Botón «Ver la chacra desde arriba» en la ficha. Cambia la cámara a vista cenital, conserva el contorno amarillo y muestra los poblados cercanos con su nombre.
- En el pie de imagen: proveedor de la imagen (atribución de Cesium ion) y «fecha de la imagen: variable según proveedor».

### R9 · Vista a ras de suelo (opcional, con clave)
- Google Street View tiene recorridos en algunas carreteras rurales de Ayacucho. Con `GOOGLE_MAPS_KEY` (cuenta de Google Cloud con crédito gratuito mensual), mostrar la panorámica más cercana a la zona, solo si está a < 2 km, con su fecha y distancia.
- Sin clave o sin cobertura cercana, no se muestra nada.

### R10 · Fotos de campo de informes técnicos oficiales (el plus para las comunidades)
Hay fotos reales de las comunidades y laderas afectadas en informes técnicos públicos. Ejemplo: INGEMMET (2014), *Zonas críticas por peligros geológicos en la región Ayacucho*, con fotos de los deslizamientos en Acoylla, Santa Lucía y la quebrada Pamparque.
<https://repositorio.ingemmet.gob.pe/bitstream/20.500.12544/2029/1/2014-Zonas_cr%C3%ADticas_peligros_geol%C3%B3gicos_Ayacucho.pdf>

- **Licencia del informe de 2014:** la ficha de metadatos indica **CC BY-NC-SA 4.0**. Se muestra con crédito y con la imagen original.
- **Fuentes a recorrer:**
  - INGEMMET (repositorio.ingemmet.gob.pe): informes de peligros geológicos y evaluaciones técnicas por distrito de Huamanga, Huanta y La Mar;
  - INDECI / SINPAD y CENEPRED (SIGRID): informes de emergencia y evaluaciones de riesgo;
  - SENAMHI y ANA: informes de heladas, sequía y huaicos.
  Revisar la licencia de **cada** documento; sin licencia clara, solo enlazar el documento sin mostrar la foto.
- **Comando** `uv run sarlab field-photos --aoi ayacucho-huanta`:
  1. lista curada de documentos en `config/field_sources.yaml` (URL, institución, año y licencia, revisada por el equipo);
  2. descarga cada PDF a `data/00_inbox` y extrae las imágenes con su **leyenda original** («Foto 16: …») y su número de página (PyMuPDF);
  3. obtiene de la leyenda el nombre de la comunidad o quebrada y lo ubica con los poblados de OSM ya publicados. Si no lo encuentra con seguridad, queda «ubicación no confirmada» y no se pone en el mapa;
  4. publica `data/04_published/field-photos/<aoi>.json` con imagen, leyenda, institución, año, licencia, URL del documento, página, comunidad, coordenada aproximada y distancia a cada zona NISAR.
- **Las imágenes no se suben a Git** (licencia ND/NC): viven en `data/`, que está fuera del repositorio, y se regeneran con el comando.
- **En la ficha** («Ver el lugar»): «Fotos de campo cercanas», solo si la comunidad está a < 10 km de la zona. Cada foto lleva la leyenda original, la institución, el año, la distancia y «Ver informe (pág. N)». Rótulo: «Foto de un informe técnico de [año]; muestra la zona cercana, no necesariamente esta mancha».
- **En el mapa:** pin con la miniatura en la comunidad del informe.
- **Pruebas:** con un PDF sintético de una página, solo en `services/pipeline/tests`. Comprobar que se descarta lo que no tiene licencia y que no se ubica nada sin coincidencia de nombre.

### R7 · Fotos de la comunidad aportadas en campo
- Ampliar los reportes ciudadanos (C4) para adjuntar **una foto** con ubicación y fecha, consentimiento explícito y autor. Las fotos pasan por moderación y se publican con licencia CC BY elegida por quien la sube.
- Es la única fuente real para los poblados rurales. El equipo o los promotores pueden cargar las primeras fotos en el evento, siempre que sean propias.

### R6 · Predicción climática 2050 (el plus)
- Comando `sarlab climate-future --aoi <zona>`: descarga de Open-Meteo Climate API los años 1991–2020 y 2041–2050 para 2 o 3 modelos CMIP6, y publica `data/04_published/climate-future/<aoi>.json`.
- **Se muestra como cambio, no como valor absoluto:** la celda del modelo está a 2559 m y las zonas a unos 3500 m, así que se compara el futuro con el pasado del **mismo modelo**. Por ejemplo: «noviembre 2041–2050: mínima +1,4 °C y lluvia −12 % frente a 1991–2020 (rango entre modelos)».
- En «Ver el lugar», la columna FUTURO muestra esa proyección real más las fotos de la técnica.
- Etiqueta fija: «Proyección de modelos climáticos CMIP6; no es un pronóstico».

## 4. Verificación (Codex pega la salida)

1. `uv run pytest -q`, `uv run ruff check services`, `npm --prefix apps/web run typecheck` y `npm --prefix apps/web test`.
2. Ejecutar `uv run sarlab photos --aoi ayacucho-huanta` y mostrar el resumen: cuántas especies tienen foto, cuántas observaciones cercanas y cuántas fotos de comunidad, **todas con licencia**.
3. Script de control: ninguna foto sin `license` ni `source_url`; toda foto rotulada «esta zona» está a < 500 m.
4. Capturas a 1366×768 de «Ver el lugar» en tres zonas de causas distintas.
5. Revisar la sección 0 del doc 23 y la sección 0 de este documento.

## 5. Prompt para Codex

```text
Eres el ingeniero de GAIA Alerta (NASA Space Apps 2026). Trabajas en D:\GAIA, rama feat/gaia-alerta,
todo en http://localhost:5173.

Lee primero: CLAUDE.md, AGENTS.md (no leas .env), la sección 0 de docs/23, docs/25 y
docs/27_Fotos_Reales_Pasado_Futuro_Codex.md.

Construye SOLO el paso R<N> del doc 27. Solo fotos reales con autor, fecha y licencia; nada generado
con IA; cada foto dice si es de esta zona, de cerca (con distancia) o de otro lugar. Las fotos se
descargan en el servidor; el navegador no llama a servicios externos.
Al terminar: ejecuta la sección 4 del doc 27, pega la salida y las capturas, agrega una línea a
CHANGELOG.md, haz commit y detente para que Claude Code revise.
```
