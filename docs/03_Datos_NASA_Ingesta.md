# Datos NASA: cómo son, cómo se buscan y cómo entran

Verificado en la documentación de ASF DAAC y el NISAR Cookbook el 11 de noviembre de 2026.

## Cómo son
- **Formato:** HDF5 (`.h5`), todo bajo `/science/LSAR/<PRODUCTO>/`.
- **Nombre de archivo** (ejemplo real de la documentación):
  `NISAR_L2_PR_GCOV_005_172_A_008_2005_DHDH_A_20251122T024618_20251122T024652_X05007_N_F_J_001.h5`
  Incluye nivel, producto, track, dirección (A/D), polarizaciones y fechas de inicio y fin.
- **Madurez:** `PROVISIONAL` (calibrado) o `BETA` (precalibración). Por defecto usamos PROVISIONAL.
- **Tamaño:** cada capa completa puede ocupar varios GB. Nunca se carga entera.

## Productos útiles

| Producto | Nivel | Para qué | En el MVP |
|---|---|---|---|
| **GCOV** | L2 | Retrodispersión HH y HV: deforestación, minería, huaicos, inundación | Sí |
| **GUNW** | L2 | Interferograma desenvuelto y coherencia: deformación | P1 |
| **GOFF** | L2 | Desplazamientos por correlación: glaciares, deslizamientos grandes | Hoja de ruta |
| **SME2** | L3 | Humedad de suelo | Hoja de ruta |

## Capas del GCOV (verificadas)
```
/science/LSAR/GCOV/grids/frequencyA/
    HHHH  HVHV            potencia lineal (float32)
    mask  numberOfLooks   calidad
    rtcGammaToSigmaFactor de gamma0 a sigma0
    xCoordinates  yCoordinates   centros de píxel (metros)
    projection            attrs['epsg_code'] → EPSG de la rejilla
```
Las rutas del GUNW **no están verificadas** en este paquete: ejecuta `sarlab inspect` sobre un GUNW real y regístralas en `docs/data-notes.md`.

## Búsqueda (Python)
```python
import asf_search as asf
r = asf.search(dataset="NISAR", processingLevel="GCOV", dataMaturity="PROVISIONAL",
               intersectsWith=WKT, start="2025-10-01", end="2026-11-11")
```
Alternativa con earthaccess: `short_name="NISAR_L2_GCOV_PROVISIONAL_V1"`.
Las búsquedas devuelven también archivos `QA_STATS`; `sources/nisar.py` se queda solo con los `.h5`.

## Acceso
1. Crea una cuenta en Earthdata Login y genera un token.
2. Ponlo en `.env` como `EARTHDATA_TOKEN`.
3. `make doctor` confirma que existe sin mostrarlo.

Lectura en la nube sin descargar: S3 con credenciales de `https://nisar.asf.earthdatacloud.nasa.gov/s3credentials` (más rápido si el servidor corre en AWS us-west-2). Es una mejora posterior; el MVP descarga.

## Ingesta
```
data/00_inbox/*.h5 ──sarlab ingest──▶ nombre válido? se abre? tiene /science/LSAR/<producto>?
        │ sí                                   │ no
        ▼                                      ▼
data/01_raw/nisar/<producto>/<año>/<mes>/   data/99_quarantine/ + <archivo>.motivo.json
+ data/catalog/catalog.json + raw_checksums.json
```
`make doctor` compara las sumas guardadas para detectar cualquier alteración en `01_raw`.

## Cómo elegir dos fechas para comparar
- **Mismo track y misma dirección** (A con A o D con D): la rejilla coincide.
- Separación suficiente para que el cambio exista (semanas o meses).
- Para huaicos, una fecha antes y otra después del evento.

## Recursos oficiales
- Documentación NISAR de ASF: https://nisar-docs.asf.alaska.edu
- NISAR Cookbook (cuadernos de ejemplo): https://asfopensarlab.github.io/NISAR_Cookbook
- Curso ARSET "Harnessing NISAR" (con sesiones en español): earthdata.nasa.gov
