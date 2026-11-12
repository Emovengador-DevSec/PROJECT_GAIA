# Producto: pestañas, módulos, filtros y ajustes

Define **qué hay en pantalla y qué hace cada control**. El aspecto visual está en el archivo `02`.

## Idea central

Una persona llega con una pregunta ("¿qué pasó aquí?") y la app la guía de la zona al hallazgo: elegir zona y fechas, ver el cambio, entender la causa, confiar (o dudar) del dato y compartirlo.

## Estructura general

```
┌──────┬────────────────────────────────────────────┬─────────────┐
│ Riel │                                            │  Inspector  │
│  de  │              Lienzo (mapa / 3D)            │  (filtros y │
│pesta-│                                            │  detalle)   │
│ ñas  ├────────────────────────────────────────────┴─────────────┤
│      │   Línea de tiempo (pasadas NISAR, reproducir)            │
└──────┴──────────────────────────────────────────────────────────┘
```

- **Riel izquierdo:** pestañas con ícono y nombre.
- **Lienzo:** ocupa todo el espacio central. Es la protagonista.
- **Inspector derecho:** se pliega. Muestra filtros, leyenda y detalle de lo seleccionado.
- **Línea de tiempo inferior:** pasadas disponibles como marcas. Se arrastra y se reproduce.
- En móvil: el riel pasa abajo, el inspector se vuelve una hoja inferior.

## Pestañas

| Prioridad | Pestaña | Para qué sirve | Contenido principal |
|---|---|---|---|
| P0 | **Casos** | Entrada y modo historia | Tres casos guiados (Madre de Dios, Chosica, Sabancaya) con resumen y botón para abrirlos |
| P0 | **Explorar** | Ver cualquier zona | Mapa 2D, selector de zona, capas, línea de tiempo |
| P0 | **Cambios** | Qué cambió entre dos fechas | Deslizador antes/después, diferencia en dB, histograma, zonas detectadas |
| P0 | **Calidad y procedencia** | Cuánto confiar | Coherencia, máscaras, avisos de datos provisionales, ficha de origen |
| P1 | **Deformación** | Cuánto se movió el suelo | Interferograma, desplazamiento en cm, perfil trazable |
| P1 | **Relieve 3D** | Verlo sobre el terreno | Deformación o cambio sobre relieve con exageración ajustable |
| P1 | **Series de tiempo** | Cómo evolucionó un punto | Gráfico por punto, velocidad, saltos y aceleraciones |
| P1 | **Alertas** | Dónde mirar primero | Lista ordenada por severidad y confianza, exportable |
| P1 | **Analista** | Preguntar en lenguaje natural | Asistente de IA (archivo `04`) |
| P1 | **Catálogo** | Qué datos existen | Mapa de huellas NISAR, pasadas por zona, producto, órbita |
| P2 | **Ajustes** | Preferencias | Unidades, paletas, idioma, rendimiento, accesibilidad |

## Módulos por pestaña

### Casos
- Tarjetas de caso con tamaños distintos según importancia (el caso estrella más grande).
- Modo historia: 5 pasos con cámara animada (zona, antes, después, medición, qué significa).
- Cada paso enlaza a la pestaña real con los filtros ya aplicados.

### Explorar
- Buscador de lugar y botón "usar mi ubicación".
- Dibujo de zona (rectángulo o polígono) con límite de área visible.
- Gestor de capas: orden, opacidad, ojo de visibilidad, procedencia.
- Mapa base conmutable (relieve, satélite, oscuro).

### Cambios
- Deslizador de cortina antes/después.
- Selector de dos fechas (solo fechas con pasada disponible).
- Mapa de diferencia con paleta divergente.
- Histograma de la diferencia con el umbral arrastrable.
- Tabla de zonas detectadas (área, severidad, confianza).

### Calidad y procedencia
- Mapa de coherencia con control de umbral de máscara.
- Porcentaje del área útil tras enmascarar.
- Ficha de cada capa: producto, versión, fechas, órbita, dirección, polarización, archivo.
- Avisos fijos de producto provisional.
- Línea de tiempo de procedencia (qué pasadas se usaron para cada resultado).

### Deformación
- Interferograma envuelto (franjas) y desplazamiento en cm.
- Perfil: el usuario traza una línea y ve el corte de desplazamiento.
- Referencia estable: el usuario marca un punto de referencia.
- Aclaración permanente: "movimiento en la línea de visión del satélite".

### Relieve 3D
- Terreno mundial con capa de datos encima.
- Exageración vertical (control deslizante), inclinación y rotación.
- Marcas en 3D de las alertas.
- Captura de imagen.

### Series de tiempo
- Clic en el mapa para elegir un punto o varios.
- Gráfico con banda de incertidumbre y marcas de pasadas.
- Velocidad (mm/año) con su error, saltos bruscos y aceleraciones detectadas.
- Comparación de hasta 3 puntos.

### Alertas
- Lista con severidad, tipo de cambio, área, fecha y confianza.
- Al elegir una alerta, el mapa vuela a ella y el inspector explica la causa.
- Exportar a GeoJSON, GeoTIFF y PDF de informe.

### Analista
- Chat con respuestas que citan capas y fechas reales.
- Botones "ver en el mapa" dentro de cada respuesta.
- Sugerencias iniciales según la pestaña activa.

### Catálogo
- Huellas de pasadas sobre el mapa, coloreadas por número de pasadas.
- Tabla de productos disponibles por zona con enlace al archivo de origen.
- Indicador "datos más recientes" y "datos más antiguos".

## Diccionario de filtros

| Filtro | Control | Valores | Aplica a |
|---|---|---|---|
| Zona (AOI) | Dibujo o buscador | Rectángulo o polígono, área máxima definida | Todas |
| Rango de fechas | Selector de intervalo | Solo fechas con pasada | Todas |
| Fecha A y fecha B | Dos selectores | Pasadas disponibles | Cambios, Deformación |
| Producto | Segmentado | GCOV, GUNW | Explorar, Calidad |
| Polarización | Chips | HH, HV, VV (según exista) | Cambios |
| Dirección de órbita | Segmentado | Ascendente, descendente | Deformación, Catálogo |
| Umbral de coherencia | Deslizador 0 a 1 | Inicial 0,3 (ajustable) | Calidad, Deformación |
| Umbral de cambio | Deslizador en dB | Calculado de forma estadística, ajustable | Cambios |
| Tipo de fenómeno | Chips | Deslizamiento, deformación, deforestación, inundación | Alertas |
| Severidad | Rango | Baja, media, alta | Alertas |
| Confianza | Deslizador | 0 a 100 % | Alertas |
| Capas complementarias | Interruptores | OPERA, FIRMS, USGS | Explorar |
| Unidad de desplazamiento | Segmentado | mm, cm | Deformación, Series |
| Exageración vertical | Deslizador | 1 a 10 veces | Relieve 3D |

Regla: **todo filtro activo se ve como una etiqueta quitable** sobre el lienzo, y el estado de filtros vive en la URL para poder compartirlo.

## Ajustes

| Grupo | Opción |
|---|---|
| Unidades | mm o cm, decibelios, formato de fecha |
| Paletas | Variable por defecto, modo apto para daltonismo |
| Rendimiento | Calidad de teselas, límite de capas simultáneas, 3D reducido |
| Accesibilidad | Reducir movimiento, contraste alto, tamaño de texto |
| Datos | Modo de acceso (descarga o directo), limpiar caché local |
| Analista | Mostrar fuentes siempre, nivel de detalle de las respuestas |
| Idioma | Español (inicial), inglés |

## Estados que toda pantalla debe tener

| Estado | Qué hace la interfaz |
|---|---|
| Vacío | Explica qué falta y ofrece la acción para resolverlo |
| Cargando | Muestra el progreso real (descarga, lectura, conversión), no solo un círculo |
| Error | Dice qué pasó, por qué y qué hacer. No se disculpa |
| Sin datos para la zona | Muestra el catálogo y sugiere zonas con cobertura |
| Dato provisional | Aviso persistente con enlace a la ficha de calidad |

## Historias de uso de referencia

1. Quien evalúa el proyecto abre **Casos**, entra a Madre de Dios, ve el antes/después y entiende en 30 segundos qué cambió.
2. Una técnica de gestión de riesgo dibuja una zona en Chosica, mira la calidad del dato y exporta las alertas.
3. Un investigador pregunta al **Analista** "¿cuánto se movió el volcán entre estas dos fechas?" y recibe cifras con fuente.
