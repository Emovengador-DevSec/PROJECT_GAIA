# Plan de construcción y prompts para el agente

El orden de trabajo, con criterios de aceptación y los textos para pegar al agente de código.

## Calendario

| Tramo | Fechas | Objetivo |
|---|---|---|
| Pre-evento | Ahora hasta el 13 de nov de 2026 | Repositorio, acceso a datos reales, pipeline base y esqueleto de la app |
| Evento | 14 y 15 de nov de 2026 | Caso estrella completo, pestañas P0 y P1, demostración |
| Después | Tras el evento | Pulido, publicación, hoja de ruta |

Recuerda revisar las reglas oficiales de Space Apps sobre qué se puede preparar antes y declarar cualquier código de terceros. Los enunciados completos con recursos se publican el **28 de octubre**.

## Prompt maestro (pegar al iniciar)

```text
Lee AGENTS.md y todos los archivos de docs/agent-pack/ antes de escribir código.
Trabajaremos por fases (F0 a F7), una a la vez. En cada fase:
1. Resume en cinco líneas lo que vas a hacer.
2. Implementa solo esa fase.
3. Ejecuta lint, tipos y pruebas, y muéstrame la salida.
4. Verifica los criterios de aceptación de la fase uno por uno.
5. Actualiza CHANGELOG.md y docs/data-notes.md.
Usa solo datos NISAR reales; si falta algo, muestra un estado vacío honesto.
Si hay una duda que cambia la arquitectura, pregúntame antes de seguir.
Empieza con F0.
```

## Fases

### F0. Base del repositorio

Prioridad P0. Estructura de carpetas, gestores (`pnpm`, `uv`), lint, tipos, pruebas, `.env.example`, `.gitignore` con `/data` y `.env`, CI básica con escaneo de secretos y auditoría de dependencias.

**Aceptación:** `pnpm install` y `uv sync` funcionan; lint, tipos y pruebas corren en limpio; la CI pasa en un cambio vacío.

### F1. Acceso real a datos

Prioridad P0. Cuenta y token de Earthdata en entorno, módulo de búsqueda en el catálogo, descarga con suma de comprobación, script de exploración HDF5.

**Aceptación:** una consulta real sobre Madre de Dios devuelve gránulos; un gránulo se descarga y verifica; `docs/data-notes.md` lista las capas reales, unidades y tamaños; no hay nombres de capa inventados.

Prompt:
```text
Implementa F1. Crea services/pipeline/search.py usando asf_search para consultar
NISAR por zona y fechas (desde el 17 de junio de 2026), y download.py con
verificación de integridad. Crea inspect_h5.py que recorra un archivo y escriba
las rutas de capas, formas y tipos en docs/data-notes.md. Confirma en la
documentación de asf_search el nombre correcto del dataset NISAR antes de
usarlo. Muéstrame la salida de una consulta real.
```

### F2. Pipeline base

Prioridad P0. Leer capas de GCOV y GUNW, recortar a la zona, convertir a dB y centímetros, enmascarar por coherencia, escribir COG y manifiesto.

**Aceptación:** de un gránulo real salen COG válidos con manifiesto completo (procedencia, calidad, rango); pruebas unitarias de conversión y máscara; el porcentaje de área útil se calcula y se guarda.

Prompt:
```text
Implementa F2. Lee las capas reales registradas en data-notes.md. Convierte
retrodispersión a dB, fase a desplazamiento en cm (la fórmula y el signo se
confirman en la documentación del producto), aplica máscara por coherencia
(umbral inicial 0,3, configurable) y escribe COG con rio-cogeo. Genera el
manifiesto de capa del archivo 03. Agrega pruebas con fixtures sintéticos
marcados como tales; la interfaz jamás los usa.
```

### F3. API y teselas

Prioridad P0. FastAPI con `/catalog`, `/jobs`, `/layers`, teselas vía TiTiler, validación de entradas, límites de tasa y CORS.

**Aceptación:** un trabajo recorre las etapas con porcentaje real; una tesela se sirve en menos de 2 segundos con capa ya calculada; entradas inválidas devuelven errores claros; pruebas de contrato pasan.

### F4. Esqueleto de la app y diseño

Prioridad P0. Riel, lienzo, inspector, línea de tiempo, tokens de diseño, tipografía, pestañas **Casos**, **Explorar**, **Cambios**, **Calidad y procedencia**, estados vacío, cargando y error, animación "despertar de franjas".

**Aceptación:** una capa real se ve en el mapa con su leyenda y su ficha de procedencia; todos los filtros activos aparecen como etiquetas y viven en la URL; funciona en móvil; foco visible y movimiento reducido respetados.

Prompt:
```text
Implementa F4 siguiendo 01 y 02. Usa los tokens de diseño tal cual. Construye el
lienzo con MapLibre, el inspector plegable y la línea de tiempo con pasadas
reales del catálogo. Aplica la paleta correcta por variable según la tabla del
archivo 02. Implementa una sola animación orquestada (despertar de franjas) y
las que respondan a acciones. Captura pantallas en escritorio y móvil y
revísalas antes de darlo por terminado.
```

### F5. Deformación, series y 3D

Prioridad P1. Pestañas **Deformación**, **Series de tiempo** y **Relieve 3D**, con perfil trazable, punto de referencia, banda de incertidumbre y exageración vertical.

**Aceptación:** el perfil devuelve valores reales en cm; la serie muestra incertidumbre y marcas de pasadas; el 3D corre con la capa encima y exageración ajustable; aparece siempre el aviso de "línea de visión".

### F6. Detección y alertas

Prioridad P1. Detector de cambio con umbral estadístico, reglas por tipo de fenómeno, severidad y confianza, pestaña **Alertas**, exportación GeoJSON, GeoTIFF y PDF.

**Aceptación:** las alertas salen de datos reales, cada una con evidencia y confianza; el histograma permite mover el umbral y las zonas se actualizan; la exportación abre en un SIG; se documenta la validación contra una fuente independiente (OPERA, USGS u otra).

### F7. Analista IA, catálogo y pulido

Prioridad P1 y P2. Pestaña **Analista** según `04`, pestaña **Catálogo**, **Ajustes**, modo historia del caso estrella, informe PDF, revisión de accesibilidad y rendimiento.

**Aceptación:** el conjunto de 20 preguntas de evaluación pasa sin cifras inventadas; el verificador bloquea una cifra falsa de prueba; el modo historia recorre los 5 pasos con filtros reales; auditoría de seguridad sin hallazgos críticos.

Prompt:
```text
Implementa F7 según 04. Crea las herramientas del agente con validación de
argumentos y un verificador que bloquee cualquier cifra que no esté en los
resultados de herramientas. Escribe el conjunto de evaluación de 20 preguntas,
incluidas 4 con instrucciones trampa dentro del texto de datos. Ejecútalo y
muéstrame los resultados.
```

## Puntos de control durante el evento

| Hora | Debe existir |
|---|---|
| H4 | Zona elegida con datos reales y una capa en el mapa |
| H12 | Pipeline completo del caso estrella con calidad visible |
| H20 | Cambios, Calidad y Alertas funcionando |
| H28 | Deformación, Series y 3D. **Congelar funciones** |
| H36 | Analista, exportación y modo historia |
| H42 | Video de demostración, README y despliegue estable |

## Lista de verificación final

- [ ] Todo lo visible viene de datos reales, con procedencia.
- [ ] El aviso de producto provisional aparece donde corresponde.
- [ ] Lo complementario (OPERA, FIRMS, USGS) está etiquetado como tal.
- [ ] No hay secretos en el repositorio ni en el navegador.
- [ ] Auditorías de dependencias sin hallazgos críticos.
- [ ] Lint, tipos y pruebas en verde.
- [ ] `README` con arranque en un comando y capturas.
- [ ] Respaldo local del caso estrella y video grabado.
- [ ] Fuentes y código de terceros citados con su licencia.

## Riesgos del agente de código

| Riesgo | Mitigación |
|---|---|
| Inventar nombres de capas o parámetros de librerías | Obligarlo a leer `data-notes.md` y la documentación vigente; revisar su salida |
| Dar por hecho que algo funciona | Exigir comandos y su salida en cada fase |
| Añadir funciones sin pedirlo | Regla de "solo la fase actual" en `AGENTS.md` |
| Usar datos de relleno en la interfaz | Prohibido en `AGENTS.md`; revisar cada pantalla contra la regla 1 |
| Cambiar la pila sin avisar | Debe proponer y esperar aprobación |
