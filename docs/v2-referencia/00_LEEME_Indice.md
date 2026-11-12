# Bailando con los SARs: paquete de especificaciones para el agente de IA

Este paquete es la **hoja de ruta que lee un agente de código (Claude Code, Codex u otro)** para construir la plataforma. Cada archivo responde una pregunta distinta y el agente puede leerlos en orden.

> **Fuente de verdad científica:** el documento *Manual Técnico v2.0* (qué es NISAR, qué productos usar, cómo se interpretan GCOV y GUNW). Este paquete no lo repite: lo convierte en tareas construibles.

## Cómo usarlo

1. Crea el repositorio y copia esta carpeta dentro de `/docs/agent-pack/`.
2. Copia `AGENTS.md` a la **raíz** del repositorio. Codex lee `AGENTS.md`. Para Claude Code, copia el mismo archivo como `CLAUDE.md` (o crea un enlace simbólico).
3. Abre el agente en la raíz y pega el **prompt maestro** del archivo `05`.
4. Trabaja por fases. Al terminar cada una, pide al agente que verifique los criterios de aceptación antes de seguir.

## Mapa de archivos

| Archivo | Responde a | Lo usa el agente para |
|---|---|---|
| `AGENTS.md` | ¿Cuáles son las reglas del proyecto? | Saber qué nunca hacer, cómo ejecutar y cuándo está algo terminado |
| `01_Producto_Pestanas_Filtros.md` | ¿Qué pantallas, filtros y ajustes tiene la app? | Construir la navegación y los controles |
| `02_Diseno_Animaciones_Visualizaciones.md` | ¿Cómo se ve y se mueve? | Aplicar colores, tipografía, animaciones y gráficos |
| `03_Arquitectura_Datos_API.md` | ¿Cómo fluyen los datos y qué contratos hay? | Crear backend, pipeline y esquemas |
| `04_Analista_IA_Agente.md` | ¿Cómo funciona el asistente de IA dentro de la app? | Implementar el agente analista con herramientas y límites |
| `05_Plan_Construccion_Prompts.md` | ¿En qué orden se construye? | Ejecutar fases con criterios de aceptación |
| `06_Estructura_Carpeta_Principal.md` | ¿Cómo se organiza el repositorio sin caos? | Saber dónde va cada archivo y cómo nombrarlo |
| `07_Configuraciones.md` | ¿Qué se puede ajustar y dónde? | Poner zonas, umbrales y paletas en `config/` y no en el código |
| `08_Ingesta_Nuevos_Datos.md` | ¿Cómo entra un dato nuevo? | Ingerir archivos y ampliar fuentes, productos, zonas y fenómenos |
| `09_Calidad_CI_Seguridad_Operacion.md` | ¿Cómo se mantiene sano y seguro? | Configurar revisiones, pruebas, seguridad y respaldos |
| `10_Glosario_y_Decisiones.md` | ¿Qué significan los términos y qué se decidió? | Usar el mismo vocabulario y registrar decisiones |

## Esqueleto del repositorio

La carpeta `bailando-sars/` es el **repositorio ya armado**: estructura de carpetas, archivos de configuración, `Makefile`, CI, `.gitignore` y el comando `doctor`. Cópiala como punto de partida y el agente continúa desde ahí.

## Prioridades

- **P0:** sin esto no hay proyecto. Datos reales NISAR leídos, una capa en el mapa, un caso estrella completo, panel de calidad.
- **P1:** lo que sube la nota. 3D, series temporales, alertas, analista IA, comparación antes/después.
- **P2:** pulido. Exportación a PDF, modo historia animado, capas complementarias, ajustes avanzados.

## Estado de los datos (consultado el 9 de octubre de 2026)

- Los datos NISAR de banda L son públicos desde el 20 de julio de 2026, con observaciones desde el 17 de junio de 2026.
- Los productos son **provisionales** y pueden tener artefactos.
- El hackathon es el 14 y 15 de noviembre de 2026. Los enunciados completos con recursos salen el 28 de octubre.

Si algo de esto cambia, actualiza `AGENTS.md` primero, porque es el archivo que el agente lee siempre.

## Nota de interpretación

Entendí que el "agente de IA como Claude o Codex" es **la herramienta que construye el software**, y que además la app incluye su propio **asistente analista** (archivo `04`). Si querías solo una de las dos cosas, puedes ignorar la otra sin romper el resto.
