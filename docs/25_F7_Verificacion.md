# F7 · Ficha en cuatro pestañas

Verificado el 15 de noviembre de 2026, hora de Lima. Solo F7 del plan 25.

## Organización

- **Diagnóstico** abre por defecto en las fichas NISAR evaluadas. Conserva la cabecera de F2, resume las evidencias que respaldan la evaluación y presenta la exposición sin convertir datos ausentes en ceros. «Ver más · diagnóstico y exposición» conserva el diagnóstico completo de F1, factores, receta, métricas, poblados, fuentes y limitaciones.
- **Clima** consulta el territorio de la mancha y muestra normales estacionales, el estado del pronóstico y su fecha, y el calendario agrícola desplegable. Se identifica como contexto regional complementario, no como una medición de la mancha.
- **Futuro y costos** conserva el presupuesto depurado de F5, el estado de la imagen óptica de F3, los supuestos relativos de F4, las fuentes, el estado del costo-beneficio y la constancia PDF de F6.
- **Voz y Minka** conserva el boletín, el borrador quechua sin grabar, las propuestas Minka, los compromisos y el estado del SMS. El acceso directo de Voz del panel izquierdo abre esta pestaña y enfoca el boletín.

El QR, los enlaces de compartir, la impresión y las fuentes ampliadas quedan en un desplegable común. El botón «Imprimir esta pestaña» describe la impresión de la vista seleccionada; la constancia completa sigue disponible como PDF en Futuro y costos. El aviso obligatorio permanece visible al pie de cada pestaña. Los avisos USGS/FIRMS sin remediación conservan su ficha anterior.

Las pestañas tienen roles ARIA, foco visible y navegación con flechas, Inicio y Fin del teclado. No añaden animaciones. En móvil, el panel ocupa el espacio entre la cabecera y la navegación inferior; sus controles tienen altura mínima de 44 px y el contenido se desplaza dentro del panel cuando lo necesita.

## Verificaciones

```text
uv run pytest -q
141 passed, 5 warnings in 14.88s

uv run ruff check services
All checks passed!

npm --prefix apps/web run typecheck
Salida 0, sin errores

npm --prefix apps/web test
6 archivos · 16 pruebas aprobadas

npm --prefix apps/web run build
Aprobado

Impeccable detect: []
```

La prueba nueva de exposición lee datos publicados reales y distingue población desconocida de una estimación cero. No hubo pruebas omitidas. Se mantienen los avisos conocidos de Rasterio y tamaño de Cesium.

```text
node tools/verify/zone-sheet-tabs.mjs
1366×768 · incendio/sequía: clientHeight=508, scrollHeight=508, errors=[]
1366×768 · erosión: clientHeight=508, scrollHeight=508, errors=[]
1366×768 · estrés hídrico: clientHeight=508, scrollHeight=508, errors=[]

node tools/verify/zone-sheet-tabs.mjs --mobile-only
375×812 · clientHeight=499, scrollHeight=542, errors=[]
Las cuatro pestañas, el PDF, el boletín y Ver más son accesibles.

node tools/verify/zone-sheet-tabs.mjs --keyboard-only
keyboard=true, voiceShortcut=true, errors=[]
```

Las tres fichas de escritorio abren Diagnóstico sin desplazamiento. La vista móvil admite desplazamiento interno y conserva la navegación inferior libre. Se revisaron visualmente las capturas en `deploy/verificacion-f7`: tres diagnósticos de causas distintas a 1366×768, diagnóstico móvil y las vistas `climate`, `future` y `voice` en ambos tamaños.

No fue necesario regenerar el pipeline: F7 reorganiza datos y funciones existentes. Esto termina los pasos F1–F7 para revisión, incluyendo la alternativa segura de F3; no equivale a haber implementado el plan 26 ni los pasos restantes del plan 24. Los cambios visuales anteriores quedan fuera del commit de F7.
