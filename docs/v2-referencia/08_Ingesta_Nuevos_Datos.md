# Ingesta de datos nuevos

Cómo entra un archivo nuevo al proyecto, qué se valida y cómo se agregan fuentes, productos, zonas o fenómenos sin reescribir nada. NISAR sigue publicando datos (el registro completo se espera para fines de 2026), así que **este flujo se usará una y otra vez**.

## Idea central

Todo dato nuevo entra por **un solo lugar**, `data/00_inbox/`, y un comando lo revisa, lo registra y lo coloca. Nadie mueve archivos a mano.

```
 00_inbox ──ingest──▶ 01_raw ──process──▶ 03_processed ──publish──▶ 04_published
                │                                                       │
                └──falla──▶ 99_quarantine (con motivo)           catalog (índice)
```

## Flujo de ingesta

| Paso | Qué ocurre | Si falla |
|---|---|---|
| 1. Detectar | Lee cada archivo de `00_inbox` y reconoce la fuente y el producto por nombre y metadatos | Cuarentena: "producto no reconocido" |
| 2. Integridad | Calcula la suma de comprobación y la compara con la de la fuente cuando existe | Cuarentena: "suma no coincide" |
| 3. Formato | Abre el archivo y comprueba que se pueda leer y que tenga las capas esperadas | Cuarentena: "archivo ilegible o incompleto" |
| 4. Metadatos | Extrae fechas, órbita, dirección, polarización, versión de proceso y huella geográfica | Cuarentena: "faltan metadatos" |
| 5. Duplicado | Comprueba si ya existe el mismo archivo o una versión más nueva | Se omite o se registra como nueva versión |
| 6. Registrar | Mueve a `01_raw/<fuente>/<producto>/<año>/<mes>/` y anota en el catálogo | Se revierte el movimiento |
| 7. Avisar | Informa qué entró, qué se omitió y qué quedó en cuarentena | |

Cada archivo en cuarentena lleva al lado un `.motivo.json` con el paso que falló y el texto del error.

## Comandos

| Comando | Qué hace |
|---|---|
| `make ingest` | Procesa todo lo que haya en `00_inbox` |
| `make verify` | Revisa que `01_raw` coincida con el catálogo y con las sumas guardadas |
| `make process AOI=<zona>` | Procesa una zona con lo que ya existe en `01_raw` |
| `make publish AOI=<zona>` | Publica los resultados en `04_published` |
| `make doctor` | Revisa herramientas, entorno y configuración |

## Catálogo

Un índice liviano en `data/catalog/` (archivo de base de datos local, más un catálogo STAC para exponer capas). Se puede **reconstruir completo desde `01_raw`** si se pierde.

Qué guarda cada registro:

| Campo | Descripción |
|---|---|
| `id` | Identificador del archivo |
| `source`, `product`, `level` | Fuente, producto y nivel |
| `acquired_at` | Fecha de adquisición |
| `orbit`, `direction`, `polarization` | Geometría de la pasada |
| `footprint` | Polígono de cobertura |
| `version` | Versión de procesamiento de la fuente |
| `sha256` | Suma de comprobación del archivo |
| `path` | Ubicación en `01_raw` |
| `ingested_at` | Cuándo entró |
| `quality_flags` | Avisos (por ejemplo, producto provisional) |

## Versiones y reprocesado

- Cuando la fuente publica una **versión nueva** del mismo producto, se conserva la anterior y se marca cuál es la vigente.
- Los resultados procesados guardan con qué versión del dato y del código se hicieron.
- Si cambia el código o un umbral, `process` reconoce que el resultado está **obsoleto** y lo recalcula, sin tocar `01_raw`.
- Los resultados publicados llevan versión; la interfaz muestra la que está activa.

## Recetas para ampliar el proyecto

### Agregar una zona nueva
1. Crea `config/aois/<id>.yaml` con nombre, caja y fenómenos.
2. Ejecuta `make doctor`.
3. Ejecuta `make process AOI=<id>` y `make publish AOI=<id>`.
4. La zona aparece sola en la app.

### Agregar un producto NISAR nuevo (por ejemplo, otro nivel L2 o L3)
1. Descarga una muestra real y explórala con el script de inspección.
2. Anota las capas reales en `docs/data-notes.md`.
3. Crea `config/products/<id>.yaml` con esas capas y sus unidades.
4. Si el formato ya se lee (HDF5), no hace falta código nuevo. Si no, agrega un lector en `readers/`.
5. Agrega una prueba con la muestra real.

### Agregar una fuente nueva (otro satélite o servicio)
1. Crea un adaptador en `sources/` que cumpla la interfaz común: `search`, `download`, `identify` y `metadata`.
2. Regístralo en `config/sources.yaml`.
3. Etiqueta sus capas como **complementarias** si no son NISAR.
4. Documenta licencia y condiciones de uso en `docs/science/`.

### Agregar un fenómeno nuevo
1. Crea `config/phenomena/<id>.yaml` con señales, productos y fuentes de validación.
2. Si las reglas por umbral bastan, termina aquí.
3. Si necesita lógica propia, agrega un detector en `detection/` que cumpla la interfaz común.
4. Documenta cómo se validó en `docs/science/`.

### Agregar una paleta o un umbral
Edita `config/colormaps.yaml` o `config/thresholds.yaml`. No requiere código.

## Interfaz común de un adaptador de fuente

Todos los adaptadores responden las mismas cuatro preguntas, así el resto del sistema no sabe de dónde viene el dato:

| Operación | Entrada | Salida |
|---|---|---|
| `search` | zona, fechas, producto | Lista de elementos disponibles |
| `download` | elemento | Archivo en `00_inbox` con suma de comprobación |
| `identify` | archivo | Fuente, producto, nivel |
| `metadata` | archivo | Campos del catálogo |

## Entrega sin conexión para la demostración

Antes del evento se prepara un **paquete local** para no depender de la red:

1. Elige las pasadas del caso estrella y de los casos de apoyo.
2. Ingierelas con `make ingest` y procésalas.
3. Ejecuta `make publish` y copia `04_published` y `catalog` a un disco o carpeta de respaldo.
4. En el perfil `demo`, la app lee solo de ahí.

## Qué hacer cuando llegan datos que no esperabas

| Situación | Acción |
|---|---|
| Producto desconocido | Cuarentena, explorar con el script de inspección, decidir si merece soporte |
| Capas con nombres distintos a los registrados | No tocar la configuración al azar: revisar el archivo real y actualizar `data-notes.md` |
| Archivo mucho más grande de lo previsto | Recortar a la zona durante `extract` y avisar del tamaño |
| Pasadas sobre una zona sin configurar | El catálogo las guarda; se publican cuando se cree la zona |
| Dato con aviso de calidad | Se ingiere con el aviso en `quality_flags` y la interfaz lo muestra |

## Reglas para el agente

- Nunca copies datos a mano a `01_raw`: pasa siempre por `make ingest`.
- No elimines nada de `99_quarantine` sin revisar su motivo.
- Una fuente nueva se agrega con adaptador y configuración, no con código suelto dentro del pipeline.
- Cada receta de este documento termina con una prueba y una línea en `CHANGELOG.md`.
