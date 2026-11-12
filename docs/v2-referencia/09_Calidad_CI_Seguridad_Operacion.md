# Calidad, integración continua, seguridad y operación

Cómo se mantiene el proyecto ordenado, seguro y publicable. Los archivos reales (`ci.yml`, `.pre-commit-config.yaml`, `dependabot.yml`) están en `bailando-sars/`.

## Flujo de trabajo en Git

| Elemento | Regla |
|---|---|
| Rama principal | `main`, siempre desplegable |
| Ramas de trabajo | `tipo/descripcion-corta` (`feat`, `fix`, `docs`, `chore`) |
| Commits | `tipo(ámbito): resumen`, en presente, una idea por commit |
| Revisión | Todo cambio entra por una solicitud de cambios con la plantilla |
| Historia | Se hace *squash* al integrar para mantener `main` legible |
| Etiquetas | `v0.1.0`, `v0.2.0`... una por entrega relevante |

## Revisiones automáticas antes de guardar (pre-commit)

- Formato y estilo de Python (Ruff) y de TypeScript (ESLint y Prettier).
- Detección de secretos.
- Bloqueo de archivos grandes y de datos (`.h5`, `.tif` grandes) en el commit.
- Validación de los archivos YAML de `config/`.
- Espacios finales y fin de línea.

## Integración continua

Se ejecuta en cada solicitud de cambios.

| Trabajo | Qué hace | Bloquea si... |
|---|---|---|
| `python` | Instala con `uv`, estilo con Ruff, pruebas con `pytest`, auditoría con `pip-audit` | Algo falla |
| `web` | Instala con `pnpm`, lint, tipos, pruebas, `pnpm audit` | Algo falla |
| `config` | Valida todos los YAML contra su esquema | Un campo falta o es inválido |
| `secrets` | Escanea el historial en busca de claves | Encuentra una |
| `contracts` | Comprueba que los tipos generados coincidan con los esquemas | Hay diferencia |

Mejora para producción: fijar cada acción de GitHub por su **huella de commit** y no por etiqueta, y dar a cada trabajo permisos mínimos.

## Pirámide de pruebas

| Nivel | Cantidad | Qué cubre |
|---|---|---|
| Unitarias | Muchas | Conversiones, máscaras, umbrales, utilidades |
| De contrato | Algunas | Manifiestos, alertas y respuestas de la API cumplen su esquema |
| De integración | Pocas | Un archivo real (o muestra oficial) recorre el pipeline entero |
| De extremo a extremo | Muy pocas | Abrir una zona, ver una capa, cambiar de fecha, exportar |
| Visuales | Las pestañas clave | Capturas en escritorio y móvil |
| De accesibilidad | Las pestañas clave | Foco, contraste, movimiento reducido |
| De evaluación del Analista | 20 preguntas | Fidelidad de cifras y resistencia a instrucciones trampa |

Los datos sintéticos solo existen en pruebas unitarias y viven en `tests/fixtures/synthetic/`.

## Modelo de amenazas

| Activo | Amenaza | Medida |
|---|---|---|
| Token de Earthdata | Fuga en el repositorio o el navegador | Solo en variables de entorno del servidor; escaneo de secretos; el navegador nunca lo ve |
| Clave de IA | Fuga o abuso de costo | Solo servidor, límite de mensajes y de contexto por sesión |
| API | Entradas enormes o malformadas | Validación de zona, fechas y tamaños; límite de área |
| API | Abuso o saturación | Límites de tasa por origen; tiempo máximo por trabajo |
| Archivos descargados | Corrupción o alteración | Suma de comprobación y cuarentena |
| Metadatos y catálogos | Texto con instrucciones ocultas | Todo texto externo es dato; se escapa y nunca llega al Analista como orden |
| Dependencias | Paquetes vulnerables o maliciosos | Versiones fijadas, auditorías, actualizaciones revisadas, versiones con al menos dos semanas de antigüedad |
| Interfaz | Inyección de contenido (XSS) | Escape de todo texto de datos; política de contenido restrictiva |
| Datos de usuarios | Guardar zonas o consultas personales | Sin cuentas en el MVP; no se registra contenido personal |
| Despliegue | Configuración abierta por error | Perfil `prod` con CORS cerrado y revisión previa a publicar |

## Lista de seguridad antes de publicar

- [ ] `make doctor` sin avisos en el perfil `prod`.
- [ ] Ninguna clave en el historial de Git.
- [ ] `pip-audit` y `pnpm audit` sin hallazgos críticos.
- [ ] CORS limitado al dominio de la app.
- [ ] Límites de tasa activos.
- [ ] Encabezados de seguridad configurados.
- [ ] El Analista pasa el conjunto de evaluación, incluidas las preguntas trampa.
- [ ] Lista de componentes de software (SBOM) generada y guardada.
- [ ] Respaldo del paquete de demostración verificado.

## Observabilidad

| Qué | Cómo |
|---|---|
| Registros | Estructurados, con nivel y sin datos personales |
| Trabajos | Etapa, duración y resultado de cada trabajo |
| Salud | Ruta `/api/health` con estado del almacén, catálogo y fuentes |
| Rendimiento | Tiempos de teselas, de series y del Analista contra los objetivos del archivo `03` |
| Errores | Mensaje legible para la persona y detalle técnico en el registro |

## Respaldo y recuperación

| Qué | Frecuencia | Cómo se recupera |
|---|---|---|
| Código y configuración | Cada commit | Git |
| `01_raw` | Tras ingerir | Se vuelve a descargar de la fuente, o del respaldo local |
| `03_processed` y `04_published` | No necesitan respaldo | Se regeneran desde `01_raw` |
| Paquete de demostración | Antes del evento y tras cada cambio | Copia en dos lugares distintos |
| Catálogo | Se reconstruye | Desde `01_raw` |

## Entrega e historial de cambios

- Cada entrega lleva etiqueta, nota de cambios y la versión de datos usada.
- `CHANGELOG.md` registra una línea por cambio: qué cambió y por qué importa.
- Las decisiones de arquitectura se escriben en `docs/decisions/` (ver archivo `10`).

## Documentación mínima que no puede faltar

| Documento | Contenido |
|---|---|
| `README.md` | Qué es, requisitos, arranque en un comando, capturas |
| `docs/data-notes.md` | Hallazgos del dato real |
| `docs/runbooks/` | Cómo ingerir, procesar, publicar y restaurar |
| `docs/science/` | Método, validación y limitaciones |
| `docs/decisions/` | Decisiones y sus motivos |

## Reglas para el agente

- Antes de dar algo por terminado, ejecuta lint, tipos y pruebas y muestra la salida.
- Nunca desactives una verificación para que pase la integración continua. Arregla la causa o pregunta.
- Si añades una dependencia, justifícala en una línea y confirma que está mantenida y con licencia compatible.
- No publiques en `main` sin pasar la revisión automática.
