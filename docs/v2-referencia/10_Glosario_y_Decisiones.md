# Glosario y decisiones

Un vocabulario común para que personas y agentes usen las mismas palabras, y el formato para registrar decisiones importantes.

## Glosario

| Término | Significado |
|---|---|
| **SAR** | Radar de apertura sintética. Mide la superficie con ondas de radio, de día y de noche, y atraviesa nubes |
| **NISAR** | Misión NASA-ISRO con radar de banda L (NASA) y banda S (ISRO) |
| **Banda L** | Longitud de onda de unos 24 cm. Penetra vegetación; buena para deformación y biomasa |
| **ASF DAAC** | Centro de la NASA que distribuye los datos NISAR |
| **Gránulo** | Un archivo de datos de la fuente (una pasada y un producto) |
| **Pasada** | Una observación del satélite sobre una zona en una fecha |
| **HDF5 (.h5)** | Formato de los productos NISAR: matrices más metadatos en un solo archivo |
| **GCOV** | Producto L2 de retrodispersión polarimétrica, ya georreferenciado |
| **GUNW** | Producto L2 de interferograma desenvuelto con coherencia, ya georreferenciado |
| **Retrodispersión** | Cuánta señal del radar vuelve a la antena; se expresa en dB |
| **dB (decibelios)** | Escala logarítmica de la retrodispersión: 10 por el logaritmo en base 10 del valor lineal |
| **HH, HV, VV** | Polarizaciones: cómo se emite y se recibe la onda |
| **Coherencia** | Número de 0 a 1 que dice cuánto se parece la superficie entre dos pasadas. Baja coherencia = poca confianza o cambio |
| **Interferograma** | Diferencia de fase entre dos pasadas. Revela movimiento del suelo |
| **Franja** | Un ciclo de color del interferograma envuelto. En banda L equivale a unos 12 cm de movimiento en la línea de visión |
| **Fase envuelta / desenvuelta** | La fase entre 0 y 2π, o la fase continua tras resolver los ciclos |
| **Línea de visión (LOS)** | Dirección entre el satélite y el suelo. El desplazamiento se mide en esa dirección |
| **Ascendente / descendente** | Sentido de la órbita. Combinarlas permite separar movimiento vertical y horizontal |
| **AOI** | Zona de interés, el área que el usuario analiza |
| **COG** | GeoTIFF optimizado para la nube: se lee por trozos sin descargarlo entero |
| **Teselas** | Pedazos pequeños de un mapa que se piden según el zoom |
| **STAC** | Estándar para describir catálogos de datos geoespaciales |
| **Manifiesto** | Archivo que acompaña a cada capa con su procedencia y calidad |
| **Procedencia** | De dónde viene un resultado: producto, versión, fechas, órbita, archivo |
| **Provisional** | Producto aún en calibración, con posibles artefactos |
| **OPERA** | Productos de la NASA derivados de Sentinel-1 y otros; sirven de respaldo y validación |
| **FIRMS** | Servicio de la NASA con anomalías térmicas (incendios) |
| **Cuarentena** | Carpeta donde queda un archivo que falló la validación, con su motivo |
| **ADR** | Registro de una decisión de arquitectura |

## Cómo registrar una decisión

Cada decisión que cambia cómo se construye el proyecto se escribe en `docs/decisions/NNNN-titulo-corto.md`, con una página como máximo.

```markdown
# NNNN. Título corto de la decisión

- Fecha: AAAA-MM-DD
- Estado: propuesta | aceptada | reemplazada por NNNN

## Contexto
Qué problema o situación obliga a decidir.

## Decisión
Qué se eligió, en una o dos frases.

## Alternativas consideradas
Qué otras opciones había y por qué no se eligieron.

## Consecuencias
Qué se gana, qué se pierde y qué queda por vigilar.
```

## Decisiones iniciales ya tomadas

Estas se transcriben como ADR en cuanto exista el repositorio.

| Nº | Decisión | Motivo |
|---|---|---|
| 0001 | Los datos NISAR se obtienen de ASF DAAC / Earthdata, no de Google Earth Engine | Earth Engine no aloja NISAR |
| 0002 | Se trabaja con productos L2 (GCOV y GUNW) y no se procesa desde L1 en el evento | Productos ya georreferenciados; ahorran tiempo y riesgo |
| 0003 | Frontend en Vercel y backend en contenedor | El procesamiento de ráster excede los límites de funciones sin servidor |
| 0004 | Salida ráster en COG con teselas; vectores en GeoJSON | Cada formato para lo que mejor hace |
| 0005 | Tres fenómenos núcleo: deslizamientos y huaicos, deformación tectónica y volcánica, deforestación y minería | Mayor impacto en Perú y Sudamérica, con señales NISAR distintas |
| 0006 | Caso estrella recomendado: Madre de Dios; apoyo en Chosica y Sabancaya | Cambio persistente, serie temporal corta de NISAR |
| 0007 | Datos reales siempre; sintéticos solo en pruebas unitarias | Requisito del proyecto y de validez ante el jurado |
| 0008 | Toda zona, fenómeno, producto y umbral se define en `config/` | Ampliar sin tocar código |
| 0009 | El Analista de IA solo usa cifras de sus herramientas y pasa por un verificador | Evitar cifras inventadas |

## Preguntas abiertas

Se resuelven y se convierten en decisiones cuando haya información.

| Pregunta | Se resuelve con |
|---|---|
| ¿Qué recursos oficiales trae el enunciado del reto? | Publicación del 28 de octubre |
| ¿Qué pasadas NISAR existen sobre cada zona candidata? | Primera consulta real al catálogo |
| ¿Cuáles son las capas reales de GCOV y GUNW? | Script de exploración (fase F1) |
| ¿Qué umbral de coherencia es útil en cada zona? | Histogramas con datos reales |
| ¿Cómo se validará cada fenómeno de forma independiente? | Revisar fuentes disponibles (OPERA, USGS y otras) |
| ¿Qué reglas del evento limitan lo que se prepara de antemano? | Reglas oficiales de Space Apps |
