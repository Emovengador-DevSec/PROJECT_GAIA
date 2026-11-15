# F6 · Quitar ruido de la ficha

Verificado el 15 de noviembre de 2026, hora de Lima. Solo F6 del plan 25.

- El botón dice «Descargar constancia (PDF)». Se conservan el endpoint y la aclaración de que no es un certificado oficial.
- El bloque de radios solo se renderiza cuando la lista publicada contiene emisoras; no aparece una lista vacía ni un recuento cero.
- Yachaq sale de la ficha. Se conserva como hoja de ruta en la sección 4.4 del documento 23 y en `config/nbs/minka.yaml`; no se presenta como servicio disponible.
- Sin una grabación publicada, el botón dice «Quechua · borrador sin grabar», sin duración estimada. Al seleccionarlo se mantiene el aviso de grabación y revisión pendientes, y no aparece reproductor. Si se publica una grabación de hablante autorizada por el backend, la etiqueta pasa a «Quechua · grabación de hablante», también sin atribuirle la duración estimada del borrador.

## Verificación ejecutada

```text
uv run pytest -q
141 passed, 5 warnings in 20.14s

uv run ruff check services
All checks passed!

npm --prefix apps/web run typecheck
Salida 0, sin errores

npm --prefix apps/web test
5 archivos · 15 pruebas aprobadas

npm --prefix apps/web run build
✓ built in 1m

node tools/verify/sheet-cleanup.mjs
1366×768: PDF correcto, borrador sin duración, radios vacías ocultas, Yachaq oculto, sin reproductor quechua, errors=[]
375×812: mismas comprobaciones, errors=[]
```

La revisión usa la zona 014 y el boletín real de la API, cuya lista de radios está vacía y cuya URL de audio quechua es nula. La prueba comprueba las etiquetas, la ausencia de bloques vacíos y el cambio real al seleccionar el borrador. No se reprodujo ni generó audio quechua, ni se enviaron mensajes. Se mantienen los avisos conocidos de Rasterio y tamaño de Cesium.

Capturas revisadas en `deploy/verificacion-f6`: `ficha-1366.png`, `ficha-375.png`, `quechua-1366.png` y `quechua-375.png`.

No fue necesario regenerar datos: este paso solo cambia la presentación de estados publicados. F7 sigue pendiente; la ficha aún conserva su estructura larga. Los cambios visuales anteriores quedan fuera del commit de F6.
