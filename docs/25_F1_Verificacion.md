# F1 · Diagnóstico respaldado por cada zona

Verificado el 14 de noviembre de 2026, hora de Lima. Se implementa únicamente F1 del plan 25; se aplaza el avance del plan 24.

## Cambio

El pipeline publica `summary` con las mediciones disponibles de cada mancha, sus unidades y fuentes. La humedad SME2 lleva la fecha real del metadato publicado. Los campos `summary_factor_ids` y `cause_factor_ids` permiten auditar qué factores aparecen en el texto.

`cause_explanation` usa solamente la evidencia que activó la evaluación de esa causa: pendiente para erosión; detecciones térmicas o humedad baja para calor/sequedad; humedad baja y cultivos para estrés agrícola; y el sismo que contribuyó al índice junto con la pendiente para la evaluación sísmica. La redacción mantiene la condición de hipótesis y la verificación en campo. Las frases están en `config/nbs/diagnosis.yaml`.

Un recuento nulo o cero de detecciones no se convierte en una afirmación sobre focos ni en una afirmación de ausencia de incendios. Se omite ese factor del resumen, siguiendo la prueba explícita de F1.

La ficha muestra el resumen y su explicación nueva. Ya no muestra el párrafo fijo de la receta ni `recipe.condition`. El campo heredado `risk_description` conserva compatibilidad con clientes anteriores, pero ahora contiene la explicación generada por zona.

## Publicación y contraste

```text
uv run sarlab remediation --aoi ayacucho-huanta
Remediación publicada: 498 manchas · alto=0 medio=61 bajo=437
-> D:\GAIA\data\04_published\remediation\ayacucho-huanta.json

Comparación con la publicación anterior:
Zone classifications/indices changed: 0
```

Ejemplos contrastados con la API y con la interfaz:

| Zona | Mediciones del resumen | Evidencia de la evaluación |
|---|---|---|
| 014 · incendio o sequía | HV 3,2 dB; pendiente 18,8°; humedad 0,100 m³/m³ del 16-sep-2026 | Humedad baja. No menciona focos ni afirma incendio confirmado. |
| 000 · erosión o huaico | HV 3,3 dB; pendiente 25,0° | Pendiente. No atribuye el cambio a lluvia sin medir. |
| 037 · estrés hídrico agrícola | HV 4,8 dB; pendiente 4,1°; humedad 0,140 m³/m³ del 16-sep-2026; cultivo 5,46 ha | Humedad baja y cultivo expuesto. |

## Verificación ejecutada

```text
uv run pytest -q
130 passed, 5 warnings in 19.50s

uv run ruff check services
All checks passed!

npm --prefix apps/web run typecheck
Código de salida 0; sin errores.

npm --prefix apps/web test
Test Files 2 passed (2)
Tests 10 passed (10)

npm --prefix apps/web run build
✓ built in 1m 15s

node tools/verify/zone-diagnosis.mjs
incendio_sequia / 014: visible=true, errors=[]
erosion_huaico / 000: visible=true, errors=[]
estres_hidrico_agricola / 037: visible=true, errors=[]
```

Las pruebas nuevas cubren factores ausentes, ceros medidos, suelo seco sin focos, focos sin humedad, erosión sin lluvia, cultivos con humedad baja, selección del sismo contribuyente y el umbral de sequedad antes de redondear. Una prueba adicional audita el JSON real de las 498 manchas; no se omitió en esta ejecución. Los datos sintéticos se limitan a `services/pipeline/tests`.

Las cinco advertencias de Rasterio y el aviso de tamaño de Cesium son los conocidos. Se revisaron visualmente las tres capturas a 1366×768, con el panel desplazado hasta el diagnóstico:

- `deploy/verificacion-f1/incendio_sequia-1366.png`
- `deploy/verificacion-f1/erosion_huaico-1366.png`
- `deploy/verificacion-f1/estres_hidrico_agricola-1366.png`

## Alcance pendiente

F2–F7 siguen pendientes: tarjetas distintivas, fotos recortadas por mancha, escenario honesto, presupuesto y Minka, limpieza de bloques y ficha en pestañas. F1 no resuelve ni valida esas secciones. La ficha completa todavía requiere desplazamiento; el diseño de una pantalla corresponde a F7. No se añadieron costos, escenarios ni audio quechua, no se modificaron originales y los cambios visuales previos del árbol de trabajo quedan fuera de este commit.
