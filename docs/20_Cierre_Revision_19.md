# Cierre de la revisión 19

14 de noviembre de 2026. Revisión sobre la aplicación en vivo y los originales locales.

## Correcciones

- Reiniciadas la API de desarrollo en 8000 y Vite en 5173. Comunidad, clima y reportes responden 200 en ambos puertos.
- El semáforo incorpora lluvia de 30 días ≥ 2 veces la climatología 1991–2020. Es una regla inicial de GAIA, configurable en `thresholds.yaml`, sin validación como umbral de huaicos. Los datos antiguos no activan la regla ni permiten mostrar verde.
- Huamanga muestra naranja: NASA POWER observa una razón de 4,03, con último día disponible 12-nov-2026. La recomendación preventiva enlaza las [indicaciones de INDECI publicadas por SENAMHI](https://www.gob.pe/37201-recomendaciones-para-protegerte-de-las-lluvias-intensas). No se infiere la ocurrencia de un deslizamiento a partir de un acumulado regional.
- Descargados, inspeccionados e ingeridos los tres originales IMERG Late V07B del 22–24 de febrero. La aplicación muestra el gráfico de 4,99 / 2,84 / 5,79 mm diarios y 13,62 mm acumulados, cobertura común 100 %. La ingesta conserva los nombres y verifica SHA-256. Los detalles están en `data-notes.md`.
- Mi comunidad activa `ayacucho-huanta`, selecciona HV y vuela al lugar, también al abrir un enlace compartido. Tiempo carga las dos observaciones radar reales.
- La ficha explica las **20,439 ha de cultivo fuera de las tres provincias**. Se calcularon recortando las manchas con la unión de sus límites, conservando el método de exposición. Las manchas que cruzan un límite pueden aparecer en más de una ficha, por lo que sus recuentos no son aditivos.
- OVI enlaza su [panel público](http://ovi.ingemmet.gob.pe/panelview/index.html), identificado por el [comunicado oficial de INGEMMET](https://www.gob.pe/institucion/ingemmet/noticias/608521-ingemmet-pone-a-disposicion-su-plataforma-de-monitoreo-volcanico-en-tiempo-real-para-el-coer-arequipa). El acceso al servidor externo puede depender de su disponibilidad.
- El panel orbital tiene una superficie oscura legible sobre el globo. Las capturas esperan a que carguen las teselas. En Mi comunidad, el mapa satelital conserva las zonas delimitadas NISAR encima.
- Retirado `tsconfig.tsbuildinfo` del índice Git y añadido a `.gitignore`. Eliminados los dos modelos EMU sin uso (5,99 MB), con la referencia original conservada en créditos.

## Validación

```text
pytest -q: 56 passed, 5 warnings in 2.37s
ruff check: All checks passed!
npm --prefix apps/web run typecheck: sin errores
npm --prefix apps/web run build: 2098 módulos, compilación aprobada
```

Las advertencias de Rasterio corresponden a imágenes sintéticas de las pruebas. Vite mantiene la advertencia conocida por el tamaño del módulo Cesium.

Imagen reconstruida: `gaia-alerta:review19`. Aplicación completa en `http://127.0.0.1:7860`, con Earthdata y FIRMS activos, dos capas NISAR y respuestas comprimidas. El contenedor anterior queda detenido como `gaia-validacion-antes19`. Los reportes se preservan en `deploy/reports-runtime`, montado en el contenedor nuevo y excluido de Git.

El verificador `tools/verify/community.mjs` comprueba el total HV contra exposición, el área fuera de provincias, el acumulado IMERG, la serie radar desde una comunidad, la ficha impresa y el gráfico de Chosica. Guarda capturas de 1440×900, 1600×900 y 390×844 en `deploy/verificacion-19-docker`.

```text
1440×900: community=true, printPages=1, errors=[]
1600×900: community=true, printPages=1, errors=[]
390×844:  community=true, printPages=1, errors=[]
```

## Archivos anteriores y diseño

El commit de esta revisión conserva el trabajo previo de Blender y las capturas de portada en el árbol de trabajo. No se incluyen como si hubieran sido validados en esta revisión. Los planes 18 y 19 quedan versionados para conservar el relevo.

Se conserva `.impeccable/config.json`, con las dos excepciones existentes limitadas a valores y archivos: Instrument Serif en la variante editorial opcional y el aviso de calibración provisional. No se añadieron supresiones. El panel orbital se corrigió con el diseño vigente; las fuentes de la portada permanecen como las eligió el usuario.

La publicación pública y la restricción del token Cesium al dominio definitivo continúan siendo pasos de entrega. Las ampliaciones D1–D4 pertenecen al plan 18.
