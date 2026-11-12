# Arquitectura, datos y API

Cómo fluyen los datos desde el archivo NISAR hasta la pantalla, y qué contratos unen cada pieza. La ciencia (qué es GCOV, GUNW, coherencia) está en el *Manual Técnico v2.0*.

## Vista general

```
 ASF DAAC / Earthdata          Pipeline (Python)                 Almacén           API (FastAPI)          Web
┌──────────────────┐   ┌──────────────────────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────┐
│ Catálogo y .h5   │──▶│ buscar → descargar → leer →  │──▶│ COG + JSON   │──▶│ catálogo, jobs │──▶│ MapLibre │
│ (HDF5, NISAR)    │   │ recortar → convertir → mask  │   │ + manifiestos│   │ teselas, series│   │ deck.gl  │
└──────────────────┘   │ → cambio → alertas           │   └──────────────┘   │ alertas, IA    │   │ Cesium   │
                       └──────────────────────────────┘                      └────────────────┘   └──────────┘
```

Principios:

- **El navegador nunca habla con ASF ni con la API de IA.** Todo pasa por el backend.
- **Todo resultado es un artefacto con manifiesto**: capa, procedencia y calidad viajan juntas.
- **El pipeline es idempotente.** Mismos parámetros, mismo resultado, y se reutiliza lo ya calculado.

## Servicios

| Servicio | Responsabilidad | Tecnología |
|---|---|---|
| `pipeline` | Buscar, descargar, leer HDF5, recortar, convertir a COG, calcular cambio, generar alertas | Python y librerías geoespaciales |
| `api` | Exponer catálogo, trabajos, teselas, series, alertas y el analista | FastAPI |
| `tiles` | Servir teselas desde COG | TiTiler |
| `web` | Interfaz | React y Vite |
| `storage` | COG, GeoJSON, manifiestos | S3 o R2 (carpeta local en desarrollo) |

## Pipeline: etapas de un trabajo

| Etapa | Qué hace | Salida |
|---|---|---|
| `search` | Consulta el catálogo con zona, fechas y producto | Lista de gránulos con metadatos |
| `download` | Descarga o lee en la nube, verifica suma de comprobación | Archivos `.h5` en caché |
| `inspect` | Recorre la estructura HDF5 y registra capas encontradas | `data-notes` con rutas reales |
| `extract` | Lee las capas necesarias y recorta a la zona | Matrices con coordenadas |
| `convert` | Retrodispersión a dB, fase a cm, coherencia 0 a 1 | Matrices en unidades físicas |
| `mask` | Aplica el umbral de coherencia y registra el área útil | Máscara y estadística de calidad |
| `detect` | Diferencia entre fechas, umbral estadístico, zonas | Ráster de cambio y polígonos |
| `classify` | Reglas por umbral; modelo entrenado solo si hay etiquetas | Tipo, severidad y confianza |
| `publish` | Escribe COG, GeoJSON y manifiestos | Artefactos listos para la API |

Estados de un trabajo: `queued`, `running` (con etapa actual y porcentaje real), `succeeded`, `failed` (con motivo legible), `empty` (no hay datos para esa zona).

## Contratos de datos

Los esquemas viven en `packages/contracts` y generan los tipos de TypeScript y de Python.

### Manifiesto de capa

```json
{
  "id": "lyr_madre-de-dios_gcov_diff_hv_2026-08-02_2026-10-01",
  "kind": "backscatter_diff_db",
  "title": "Cambio de retrodispersión HV",
  "unit": "dB",
  "colormap": "RdBu",
  "range": { "min": -12.0, "max": 12.0, "center": 0 },
  "cog_url": "https://…/lyr_….tif",
  "aoi": { "type": "Polygon", "coordinates": [] },
  "dates": { "a": "2026-08-02", "b": "2026-10-01" },
  "provenance": {
    "source": "NISAR",
    "products": ["GCOV"],
    "granules": ["<nombre real del archivo>"],
    "orbit_direction": "ascending",
    "polarization": "HV",
    "processing_version": "<según metadatos del archivo>",
    "retrieved_at": "<fecha de descarga>"
  },
  "quality": {
    "provisional": true,
    "coherence_threshold": 0.3,
    "valid_area_pct": 0.0,
    "notes": ["Producto provisional de NISAR."]
  }
}
```

Todos los valores de ejemplo se **rellenan con datos reales** del archivo. Nada se escribe a mano.

### Alerta (GeoJSON Feature)

```json
{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [] },
  "properties": {
    "id": "alr_…",
    "phenomenon": "deforestation",
    "severity": "high",
    "confidence": 0.0,
    "area_ha": 0.0,
    "date_range": ["2026-08-02", "2026-10-01"],
    "evidence": ["hv_drop_db", "coherence_drop"],
    "layer_ids": ["lyr_…"],
    "method": "threshold_rules_v1"
  }
}
```

### Serie temporal de un punto

```json
{
  "point": { "lon": -70.4, "lat": -12.9 },
  "layer_kind": "los_displacement_cm",
  "reference": { "lon": 0, "lat": 0, "note": "zona estable elegida por el usuario" },
  "samples": [
    { "date": "2026-07-01", "value": 0.0, "sigma": 0.0, "coherence": 0.0 }
  ],
  "trend": { "rate_mm_per_year": 0.0, "sigma": 0.0 },
  "events": [{ "date": "2026-08-14", "type": "jump", "magnitude_cm": 0.0 }]
}
```

## API

Prefijo `/api`. Respuestas en JSON, errores con `code` y `message` en español legible.

| Método y ruta | Parámetros | Devuelve |
|---|---|---|
| `GET /catalog` | `bbox`, `start`, `end`, `product` | Pasadas y gránulos disponibles |
| `POST /jobs` | zona, fechas, producto, umbrales | `job_id` |
| `GET /jobs/{id}` | | Estado, etapa y porcentaje |
| `GET /layers` | `job_id` | Lista de manifiestos |
| `GET /layers/{id}` | | Manifiesto de capa |
| `GET /tiles/{layer_id}/{z}/{x}/{y}` | `colormap`, `rescale` | Tesela PNG (delegada a TiTiler) |
| `GET /timeseries` | `lon`, `lat`, `layer_kind`, `start`, `end` | Serie con incertidumbre |
| `GET /profile` | línea (GeoJSON), `layer_id` | Perfil de desplazamiento |
| `GET /alerts` | zona, fechas, filtros | Alertas en GeoJSON |
| `POST /export` | `format`, `alert_ids` | Archivo GeoJSON, GeoTIFF o PDF |
| `POST /analyst` | mensaje, contexto de pestaña | Respuesta con fuentes (ver `04`) |

Las rutas exactas de TiTiler cambian entre versiones: consulta su documentación y aísla ese detalle detrás de `/tiles`.

## Almacenamiento y caché

- Clave de artefacto: `{aoi_hash}/{product}/{date_a}_{date_b}/{kind}.tif`.
- Si existe el artefacto y su manifiesto, **no se recalcula**.
- Caché de descargas con verificación de suma de comprobación y limpieza desde **Ajustes**.

## Rendimiento

| Objetivo | Meta |
|---|---|
| Primera tesela visible tras abrir una zona con capas ya calculadas | Menos de 2 segundos |
| Cambio de fecha en la línea de tiempo | Menos de 500 ms |
| Respuesta del analista (primera palabra) | Menos de 3 segundos |
| Tamaño máximo de zona por trabajo | Definido por variable de entorno |

Si la descarga es lenta, el pipeline corre cerca del dato (región de nube de ASF) y recorta antes de convertir.

## Variables de entorno (solo nombres)

`EARTHDATA_TOKEN`, `FIRMS_MAP_KEY`, `ANALYST_API_KEY`, `ANALYST_MODEL`, `STORAGE_URL`, `STORAGE_KEY`, `STORAGE_SECRET`, `MAX_AOI_KM2`, `ALLOWED_ORIGIN`, `CACHE_DIR`. Con archivo `.env.example` sin valores y `.env` en `.gitignore`.

## Seguridad del backend

| Riesgo | Medida |
|---|---|
| Entradas maliciosas o enormes | Validación de zona, fechas y tamaño; límite de área |
| Abuso de la API | Límites de tasa por origen |
| Fuga de secretos | Solo variables de entorno, escaneo de secretos en CI |
| Archivos corruptos o alterados | Suma de comprobación y rechazo al fallar |
| Contenido de metadatos tratado como instrucción | Todo texto externo es dato y se escapa; nunca llega al analista como orden |
| Dependencias vulnerables | Versiones fijadas, `pip-audit` y `pnpm audit` en CI |
| Datos de usuario | No se guardan zonas personales sin consentimiento; sin cuentas en el MVP |

## Pruebas

| Tipo | Qué cubre |
|---|---|
| Unitarias | Conversión a dB, fase a cm, máscara por coherencia, umbrales |
| Contrato | Los manifiestos y alertas cumplen el esquema |
| Integración | Un gránulo real (o muestra oficial) recorre el pipeline completo |
| Visual | Capturas de las pestañas clave en escritorio y móvil |
| Accesibilidad | Foco, contraste y movimiento reducido |

Los fixtures sintéticos viven aparte y nunca llegan a la interfaz (ver `AGENTS.md`).

## Registro de hallazgos de datos

Mantén `docs/data-notes.md` con lo que el script de exploración encuentre: rutas reales de capas, unidades, tamaños de píxel, tamaño de archivo y artefactos conocidos. Es la memoria del proyecto sobre el dato real.
