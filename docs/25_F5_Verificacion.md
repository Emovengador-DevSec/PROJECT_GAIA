# F5 · Presupuesto y Minka respaldados

Verificado el 15 de noviembre de 2026, hora de Lima. Solo F5 del plan 25.

## Cambios

- Los costos requieren estado `verificado`, fuente no provisional, fecha y precio unitario para publicar importes. En los demás casos, la publicación elimina importes, fuente, nota de fuente, fecha y porcentaje de descuento. La ficha muestra una línea por técnica: nombre y «costo por confirmar». El componente también filtra datos antiguos no verificados.
- Cada registro de remediación conserva hasta tres centros poblados cercanos, ordenados por distancia, procedentes de la coincidencia exacta del identificador de la mancha en la exposición publicada. No se heredan localidades mediante la coincidencia de sufijos entre periodos o polarizaciones. Se conserva la atribución de OpenStreetMap en las fuentes complementarias.
- Minka muestra técnicas, temporadas, herramientas sugeridas y poblados cercanos. No calcula metas de trabajadores, días, suministros cuantificados, apoyo logístico ni ahorros a partir de valores por defecto. Los campos heredados de trabajadores, días y ahorro quedan nulos. Las respuestas no representan convocatorias enviadas.
- El boletín usa los nombres publicados. Si faltan, se refiere al área satelital analizada sin inventar una localidad. El SMS solo se genera cuando hay un poblado identificado; no se trunca el aviso obligatorio para aparentar un límite de 160 caracteres. Se muestra como vista previa con su recuento real de caracteres.
- Los formularios de compromisos ya no rellenan un número de voluntarios ni herramientas supuestas. La cantidad se debe introducir explícitamente.
- La caché de audio incorpora el hash del guion: una corrección de localidades no reutiliza un WAV anterior. No fue necesario borrar los audios antiguos ni sintetizar voz quechua.

## Verificaciones

```text
uv run sarlab remediation --aoi ayacucho-huanta
498 manchas · alto=0 medio=61 bajo=437

uv run pytest -q
141 passed, 5 warnings in 33.09s

uv run ruff check services
All checks passed!

npm --prefix apps/web test
5 archivos · 15 pruebas aprobadas

npm --prefix apps/web run typecheck
Salida 0, sin errores

npm --prefix apps/web run build
✓ built in 16.43s

Impeccable detect: []
```

Las pruebas recorren los presupuestos y boletines de las 498 manchas reales, contrastan sus poblados con los registros publicados y cubren el caso sin poblados, la ausencia de cuadrillas y ahorros supuestos y la supresión de datos de costos no verificados. Los datos sintéticos adicionales están limitados a `services/pipeline/tests`. No hubo pruebas omitidas. Se mantienen los avisos conocidos de Rasterio y tamaño de Cesium.

```text
node tools/verify/minka-evidence.mjs
1366×768 · zona 014: Chucllayoc (1041 m), Acopampa (1366 m), Huaylacucho (1658 m), errors=[]
375×812 · zona 014: mismos poblados publicados, errors=[]
1366×768 · zona 058: sin poblados, SMS nulo, errors=[]
```

En las tres fichas verificadas no aparece `por_verificar`, `S/ Sin dato` ni «en .». Las capturas de presupuesto y Minka están en `deploy/verificacion-f5`, con sufijos de ancho (`1366`, `375`) y cantidad de poblados (`3`, `0`). Se revisó visualmente el resultado. No se enviaron SMS ni mensajes de WhatsApp, ni se registraron compromisos durante la prueba.

F6 y F7 siguen pendientes. Los bloques de hoja de ruta y las duraciones del borrador quechua pertenecen a F6; esta verificación no los da por corregidos. Los cambios visuales anteriores quedan fuera del commit de F5.
