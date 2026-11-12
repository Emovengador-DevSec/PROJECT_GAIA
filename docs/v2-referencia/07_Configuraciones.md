# Configuraciones

Todo lo ajustable del proyecto vive en archivos de configuración, no en el código. Así se cambia una zona, un umbral o una paleta sin tocar ni una línea de lógica. Los archivos reales están en `bailando-sars/config/`.

## Principios

1. **Configuración declarativa:** archivos YAML legibles, uno por cosa (una zona, un fenómeno, un producto).
2. **Validación al arrancar:** el servidor y el pipeline comprueban cada archivo contra un esquema y se niegan a iniciar si algo está mal, diciendo cuál archivo y cuál campo.
3. **Sin secretos en archivos de configuración.** Las claves van solo en variables de entorno.
4. **Valores iniciales marcados.** Todo número que sea un punto de partida lleva `initial: true` y se ajusta con datos reales.
5. **La interfaz recibe una copia pública** de la configuración mediante `/api/config`, sin secretos.

## Orden de prioridad

De menor a mayor: **valores por defecto del código → archivos de `config/` → variables de entorno → parámetros de línea de comandos.** Lo último que se indica gana.

## Mapa de configuraciones

| Archivo | Qué controla | Ejemplo |
|---|---|---|
| `config/app.yaml` | Nombre, perfil activo, límites generales, idioma | Área máxima por trabajo |
| `config/sources.yaml` | Fuentes de datos y cómo conectarse | NISAR vía ASF, OPERA, FIRMS, USGS |
| `config/products/*.yaml` | Un producto de datos: capas, unidades, escala | GCOV, GUNW |
| `config/aois/*.yaml` | Una zona: nombre, caja, fenómenos, estado | Madre de Dios, Chosica, Sabancaya |
| `config/phenomena/*.yaml` | Un fenómeno: señales, reglas, severidad | Deforestación, deslizamiento |
| `config/thresholds.yaml` | Umbrales de calidad y de cambio | Coherencia mínima |
| `config/colormaps.yaml` | Paleta por tipo de variable | Divergente para dB |
| `config/features.yaml` | Interruptores de funciones y pestañas | Activar o no el Analista |
| `.env` | Secretos y direcciones | Token de Earthdata |

## Perfiles de ejecución

Se elige con `APP_PROFILE`.

| Perfil | Para qué | Diferencias |
|---|---|---|
| `dev` | Desarrollo local | Registros detallados, caché local, límites bajos de zona |
| `demo` | La presentación del evento | Datos locales precargados, sin llamadas lentas, Analista con respaldo |
| `prod` | Publicación en línea | Límites de tasa estrictos, CORS cerrado, registros sin datos personales |

## Esquema de una zona

```yaml
id: madre-de-dios-la-pampa      # igual al nombre del archivo
name: Madre de Dios (La Pampa)
role: flagship                  # flagship | support | optional
status: approximate             # approximate | confirmed
bbox: [-70.9, -13.3, -69.9, -12.5]   # oeste, sur, este, norte
phenomena: [deforestation]
notes: Ajustar la caja con las huellas reales de NISAR.
```

## Esquema de un fenómeno

```yaml
id: deforestation
name: Deforestación y minería
signals: [hv_backscatter_drop, coherence_drop]
products: [nisar_gcov]
method: threshold_rules_v1
severity:
  initial: true
  levels: { low: 0.33, medium: 0.66, high: 1.0 }
validation_sources: [opera_dist, geobosques]
```

## Esquema de un producto

```yaml
id: nisar_gcov
source: nisar
level: L2
format: hdf5
layers: {}        # Se completa con docs/data-notes.md después de F1.
unit_conversions:
  backscatter: db_from_linear
```

El campo `layers` queda vacío **a propósito**: se llena con las rutas que realmente se encuentren en el archivo, nunca de memoria.

## Umbrales y calidad

Todos en `config/thresholds.yaml`, marcados como iniciales hasta validarlos con datos reales.

| Umbral | Valor inicial | Se ajusta con |
|---|---|---|
| Coherencia mínima | 0,3 | Histograma de coherencia de la zona |
| Cambio de retrodispersión | Estadístico (k veces la desviación) | Histograma de diferencia y validación independiente |
| Área útil mínima para publicar | A definir con el equipo | Primeras pruebas reales |
| Confianza mínima para una alerta | A definir con el equipo | Validación contra OPERA, USGS u otras |

## Configuración de la interfaz

Valores por defecto del usuario (editables en **Ajustes**, guardados en el navegador):

| Ajuste | Valor por defecto |
|---|---|
| Idioma | Español |
| Unidad de desplazamiento | Centímetros |
| Paleta de divergentes | Estándar (modo daltónico opcional) |
| Reducir movimiento | Sigue la preferencia del sistema |
| Exageración vertical en 3D | 2 veces |
| Calidad de teselas | Automática |

## Interruptores de funciones

`config/features.yaml` activa o desactiva piezas completas sin borrar código. Útil para congelar funciones en el evento.

| Interruptor | Controla |
|---|---|
| `tab_analyst` | Pestaña del Analista |
| `tab_3d` | Relieve 3D |
| `tab_catalog` | Catálogo |
| `layer_opera` | Capa complementaria OPERA |
| `layer_firms` | Capa complementaria FIRMS |
| `layer_usgs` | Capa complementaria USGS |
| `export_pdf` | Informe en PDF |
| `story_mode` | Modo historia |

## Variables de entorno

Solo nombres. Los valores van en `.env` (ignorado por Git).

| Variable | Uso |
|---|---|
| `APP_PROFILE` | `dev`, `demo` o `prod` |
| `EARTHDATA_TOKEN` | Acceso a descargas de la NASA |
| `FIRMS_MAP_KEY` | Clave gratuita de NASA FIRMS (capa complementaria) |
| `ANALYST_API_KEY` | Clave del asistente de IA (solo servidor) |
| `ANALYST_MODEL` | Modelo del asistente |
| `STORAGE_URL`, `STORAGE_KEY`, `STORAGE_SECRET` | Almacén de objetos |
| `DATA_DIR` | Ruta de la carpeta `data/` |
| `CACHE_DIR` | Caché de descargas |
| `MAX_AOI_KM2` | Área máxima por trabajo |
| `ALLOWED_ORIGIN` | Dominio permitido por CORS |
| `LOG_LEVEL` | Nivel de registros |

## Cómo comprobar la configuración

```bash
make doctor
```

El comando `doctor` (`scripts/doctor.py`) revisa: versiones de herramientas, que `.env` tenga las variables necesarias, que cada archivo YAML se lea y tenga los campos obligatorios, que el `id` coincida con el nombre del archivo, que las zonas, fenómenos y productos se referencien entre sí sin huecos, que cada caja geográfica esté bien ordenada, que existan las carpetas de datos y que `data/01_raw/` no haya sido modificado (comparando con las sumas guardadas en `data/catalog/raw_checksums.json`). En CI se ejecuta con `--config-only`.

## Reglas para el agente

- Si necesitas un número que afecta resultados, ponlo en `config/` con `initial: true` y no en el código.
- No agregues un campo sin documentarlo aquí.
- No escribas valores de capas HDF5 en configuración antes de verlos en un archivo real.
- Cualquier configuración nueva debe validarse al arrancar y fallar con un mensaje claro.
