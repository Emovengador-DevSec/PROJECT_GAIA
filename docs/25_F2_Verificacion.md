# F2 · Identidad de cada mancha

Verificado el 14 de noviembre de 2026, hora de Lima. Solo F2 del plan 25.

La cabecera de las fichas NISAR evaluadas muestra cuatro filas: causa y nivel, área e identificador de zona, hasta tres factores medidos con unidades, y el poblado cercano con distancia. Los factores se ordenan por sus puntuaciones normalizadas; no se inventan factores para completar tres. Las mediciones válidas de valor cero siguen siendo distintas de datos ausentes. El poblado se elige por la menor distancia de `exposure.nearby_places`; cuando no existe esa publicación se muestra un estado vacío.

La lista Acción conserva las 498 zonas, agrupadas en cuatro causas publicadas. Cada grupo lleva su recuento y ordena sus manchas por índice descendente, con desempate por identificador. Los grupos también se ordenan por su índice máximo. Las tarjetas muestran área, factor principal y poblado, sin especies ni presupuesto. Las funciones de recetas permanecen en la ficha.

## Verificaciones

```text
uv run pytest -q: 130 passed, 5 warnings in 11.48s
uv run ruff check services: All checks passed!
npm --prefix apps/web test: 3 archivos, 13 pruebas aprobadas
npm --prefix apps/web run typecheck: salida 0, sin errores
npm --prefix apps/web run build: aprobado
Impeccable detect: []
```

Las pruebas nuevas leen las manchas publicadas reales y comprueban agrupación, orden, cabecera, ausencia de especies/presupuesto en tarjetas y ausencia de poblados inventados. No hubo pruebas omitidas. Se mantienen los avisos conocidos de Rasterio y del tamaño de Cesium.

```text
node tools/verify/zone-identity.mjs
1366×768: 498 zonas únicas, 4 grupos, cabecera 106,75 px, errors=[]
375×812: 498 zonas únicas, 4 grupos, cabecera 106,75 px, errors=[]

node tools/verify/zone-diagnosis.mjs --identity
Zonas 014, 000 y 037: cabeceras visibles, tres causas distintas, errors=[]
```

El contraste visual muestra, por ejemplo, Apucancha a 0,74 km en la zona 238, según la exposición publicada. Las capturas están en `deploy/verificacion-f2`: `lista-1366.png`, `lista-375.png`, `ficha-1366.png`, `ficha-375.png`, `incendio_sequia-1366.png`, `erosion_huaico-1366.png` y `estres_hidrico_agricola-1366.png`.

No fue necesario regenerar el pipeline: F2 reorganiza datos que ya publica la API. F3–F7 siguen pendientes; la ficha completa conserva sus secciones largas hasta F7. Los cambios visuales anteriores y los planes sin commit se mantienen separados del commit de F2.
