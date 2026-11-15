# F4 · Escenarios relativos y fuentes pendientes

Verificado el 14 de noviembre de 2026, hora de Lima. Solo F4 del plan 25.

Se retiraron de la configuración y de la publicación `baseline_ndvi`, los valores absolutos `ndvi` y las tasas anuales supuestas. El pipeline publica únicamente ganancias relativas, con `basis=relative_gain_assumption` y estado explícito de la cita. Una causa sin escenario propio devuelve `None`; no se le copia el escenario de erosión.

Todas las referencias actuales siguen pendientes de verificación. La ficha muestra «Ver supuestos · escenario sin fuente verificada», cerrado por defecto. Al abrirlo, explica que no hay NDVI medido de la mancha, que las ganancias no están calibradas para ese terreno y que no son observaciones ni promesas. Solo muestra ganancias relativas a 3 y 5 años, referencia propuesta y limitaciones. No muestra valores absolutos ni «Año 0 (actual)», tampoco si recibe un objeto antiguo que todavía contenga esos campos.

El PDF omite las cifras mientras la cita no esté verificada. Cuando una fuente se marque explícitamente verificada, seguirá usando únicamente ganancias relativas y la etiqueta de escenario. Este paso no declara verificadas las referencias ni calcula NDVI a partir de bandas ópticas.

## Verificaciones ejecutadas

```text
uv run sarlab remediation --aoi ayacucho-huanta
498 manchas · alto=0 medio=61 bajo=437

uv run pytest -q
138 passed, 5 warnings in 6.12s

uv run ruff check services
All checks passed!

npm --prefix apps/web run typecheck
Salida 0, sin errores

npm --prefix apps/web test
4 archivos · 14 pruebas aprobadas

npm --prefix apps/web run build
✓ built in 35.69s

Impeccable detect: []

node tools/verify/relative-recovery.mjs
1366×768: closedByDefault=true, relativeOnly=true, errors=[]
375×812: closedByDefault=true, relativeOnly=true, errors=[]
```

Las pruebas cubren la ausencia de NDVI absoluto en todas las manchas publicadas, causas sin escenario propio, publicación de ganancias relativas, desplegable cerrado y omisión de cifras en un PDF generado con datos publicados reales. No hubo pruebas omitidas; se mantienen los avisos conocidos de Rasterio y tamaño de Cesium.

Capturas revisadas en `deploy/verificacion-f4`: `cerrado-1366.png`, `cerrado-375.png`, `supuestos-1366.png` y `supuestos-375.png`.

F5–F7 siguen pendientes. Los cambios visuales anteriores quedan separados de este commit.
