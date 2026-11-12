---
name: fase
description: Ejecuta una fase del plan MVP (M0 a M6) de docs/05_Plan_MVP_72h.md con verificación. Úsala cuando el usuario diga "fase", "siguiente fase" o un código como M2.
---
1. Lee docs/05_Plan_MVP_72h.md y localiza la fase pedida (o la siguiente sin completar en CHANGELOG.md).
2. Resume en 5 líneas lo que harás y qué criterio de aceptación cumplirás.
3. Delega: datos a `geo-data-engineer`, interfaz a `frontend-3d`.
4. Ejecuta `make test` y `cd apps/web && npm run build`. Muestra la salida.
5. Verifica los criterios de aceptación uno por uno, marcando cumple / no cumple.
6. Añade una línea a CHANGELOG.md. No avances a la fase siguiente sin que el usuario lo pida.
