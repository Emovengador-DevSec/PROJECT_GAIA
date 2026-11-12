# Plan MVP de 72 horas

El código base ya existe y está probado (pipeline, API, web). Las fases convierten ese esqueleto en una demo con datos reales.

## Alcance del MVP
- **Un caso estrella con datos NISAR reales:** cambio de retrodispersión HV en Madre de Dios entre dos fechas.
- **Globo 3D** con despertar de franjas, vuelo y capa radar.
- **Pestañas:** Historia, Lugares, Cambios (HH y HV), Tiempo, Calidad, Relieve 3D, Alertas.
- **Hipótesis físicas** por lugar, actualizadas con los resultados reales.
- **Fuera del MVP:** GUNW/deformación y Analista IA (hoja de ruta).

## Fases

| Fase | Cuándo | Entregable | Criterios de aceptación |
|---|---|---|---|
| **M0 Arranque** | Hoy | Repo instalado | `make setup`, `make doctor` y `make test` sin errores |
| **M1 Datos reales** | Hoy | 2 gránulos GCOV del caso estrella en `01_raw` | `sarlab search` lista gránulos reales; `sarlab ingest` los cataloga; `sarlab inspect` confirma HVHV en `data-notes.md` |
| **M2 Cambio real** | Día 1 | Capas, alertas y serie reales | `sarlab change` produce HH y HV con manifiestos y alertas; `sarlab timeseries` con 3 o más fechas; hipótesis actualizadas en `config/stories` |
| **M3 Teselas** | Día 1 | Capa en el globo | `/api/cog/tiles/...` devuelve PNG; la web muestra la capa sobre la zona |
| **M4 Experiencia** | Día 2 (evento) | Demo navegable | Franjas → vuelo → capa → Calidad con gránulos y aviso provisional; ángulo de cámara desde config; **grabar video** |
| **M5 Plus** | Día 2 | 1 o 2 plus de `01_Valor_para_Ganar.md` | Cortina antes/después y alertas clicables; validación cruzada si hay tiempo |
| **M6 Cierre** | Final | Entrega | Skill `revision-demo` sin fallos; README con capturas; despliegue o copia local lista |

Si el caso estrella no tiene dos fechas útiles, pasa a la siguiente zona de `config/aois` sin cambiar código.

## Prompts para Claude Code

**Inicio**
```text
Lee CLAUDE.md y docs/05_Plan_MVP_72h.md. Ejecuta la fase M0 con la skill `fase`.
Muéstrame la salida de make doctor y make test.
```

**M1** (usa la skill `datos-nisar`)
```text
Fase M1 para madre-de-dios-la-pampa desde 2025-10-01. Propón dos gránulos GCOV del mismo
track y dirección y espera mi confirmación antes de descargar.
```

**M2**
```text
Fase M2: ejecuta sarlab change con los dos gránulos ingeridos. Si falla, depura con
geo-data-engineer sin inventar rutas HDF5. Resume hectáreas, alertas y área válida.
```

**M3 y M4**
```text
Fase M3 y luego M4 con frontend-3d. La capa debe venir de /api/layers; usa el ángulo de
cámara de la zona; respeta movimiento reducido. Termina con npm run build.
```

**Cierre**
```text
Ejecuta la skill revision-demo y pide a security-reviewer un informe. No corrijas nada sin preguntarme.
```

## Riesgos del evento

| Riesgo | Plan |
|---|---|
| Descarga lenta o archivos enormes | Descargar hoy; probar recorte con `sarlab change` antes del evento |
| Zona sin dos fechas del mismo track | Cambiar a otra zona configurada; usar BETA si PROVISIONAL no cubre |
| Teselas lentas | Precalcular PNG o reducir nivel máximo |
| Cesium sin token | El globo funciona sin relieve; pedir token gratuito hoy |
| Sin internet en la presentación | Perfil demo con datos procesados locales y video grabado |
