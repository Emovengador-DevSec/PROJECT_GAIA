# 13 · Plan final: de prototipo a demo ganadora

Escrito el 13 de noviembre de 2026 (noche), tras revisar el commit `85881fd`. Manda sobre los planes 10 y 11 donde haya diferencia.
Estado: las tres claves (Earthdata, Cesium ion, FIRMS) están configuradas; los momentos W1–W8 están hechos.

### Ejecución de Codex del 13 de noviembre

- G1 publicado con trayectoria 147, 24-jun y 10-oct, 4,16 GB y cobertura válida común del 99,91 %. Se eligió 10-oct para conservar P05023 en ambas fechas. El 22-oct existe en la colección validada con otra versión de procesamiento.
- G4 implementado y verificado en Chrome a 2560, 390 y 320 px. El valor inicial es Siempre de día y el selector permite Hora real.
- G2 publicado para las 1.106 manchas activas con WorldPop, WorldCover y 1.192 localidades OSM. Las categorías WorldCover reconcilian el área de cada mancha y WorldPop conserva su cobertura parcial.
- G3 publicado con total HV del manifiesto, área delimitada aparte y contraste OPERA original. Coinciden 21,08 ha, el 2,25 % de las manchas HV, con intersección/unión del 0,80 %. La atribución a incendios continúa por verificar.
- G7 tiene guion, relato actualizado y video de respaldo de 2 min 38 s en `art/verificacion/gaia-alerta-demo.mp4`. El modo sin conexión pasó la verificación con el par nuevo en PC y teléfono.
- G8 tiene texto de entrega y auditoría local. Quedan pendientes verificar la guía oficial 2026, accesible desde Resources, y la publicación del repositorio/envío desde la cuenta del equipo. El detalle está en `docs/14_Entrega_Demo.md`.
- G5 requiere cuatro fechas y continúa sujeto al límite vigente de dos descargas GCOV. G6 sigue pendiente de la selección e inspección GUNW.

## Lo que se revisó y lo que falla

| Hallazgo | Evidencia | Gravedad |
|---|---|---|
| **El análisis NISAR de Ayacucho cubre casi nada** | `timeseries.json`: `valid_pct` 1,7 %. La trayectoria 75, cuadro 171, solo toca el 14–16 % de la caja de estudio | **Crítica**: el número principal (52,76 ha) sale de menos del 2 % de la zona |
| Hay datos que cubren la zona entera | Catálogo ASF (consultado hoy): trayectoria **147 ascendente, cuadro 171** y trayectoria **54 descendente, cuadro 95** cubren el **100 %** de la caja, con 11 fechas cada una entre junio y noviembre de 2026 | Solución lista |
| «¿A quién afecta?» está vacío | `data/04_published/exposure/ayacucho-huanta.json` tiene `sources: {}` y `alerts: {}`, aunque `worldpop.tif` y `worldcover.tif` ya están descargados | Alta |
| La cifra destacada confunde | La tarjeta «Lo más importante» de NISAR muestra **2,0 ha** (la mancha más grande); el total con caída de HV es **52,76 ha** en 5 manchas | Media |
| Serie de tiempo con 2 fechas | La tendencia sigue desactivada (necesita 4) | Media |
| **Sudamérica se ve de noche** | La iluminación usa la hora real: en la demo, según la hora, Perú queda en el lado oscuro y la imagen satelital no se ve | Alta para la presentación |
| Sabancaya sin deformación | No hay GUNW procesado; la historia del volcán está incompleta | Media |
| Cambios sin confirmar en Git | `astronauta.glb` borrado y `nisar.glb` y `gaia.blend` modificados fuera de un commit | Revisar si es intencional |

## Fases

Cada fase termina con `npm --prefix apps/web run build`, las pruebas, capturas y un commit propio.

### G1 · Datos NISAR que cubran Ayacucho (prioridad máxima)
- Cambiar el caso a la **trayectoria 147 ascendente, cuadro 171**. Las fechas disponibles son: 24-jun, 06-jul, 18-jul, 11-ago, 23-ago, 04-sep, 16-sep, 28-sep, 10-oct, 22-oct y 03-nov de 2026.
- Elegir **4 fechas**:
  - **24-jun:** antes de la temporada de incendios.
  - **23-ago y 16-sep:** durante la temporada.
  - **22-oct:** después.

  Antes de decidir, mirar los focos FIRMS de esos meses en la zona y mover las fechas para que una caiga justo después del pico de incendios.
- Son ~8 GB: **pedir permiso** (regla de 5 GB). Como mínimo, 2 fechas (24-jun y 22-oct), ~4 GB.
- Proponer borrar los dos GCOV de la trayectoria 75 (~3,9 GB) para liberar espacio; **no borrar sin permiso**.
- `sarlab change` entre la primera y la última fecha; `sarlab timeseries` con las 4.
- Si la trayectoria 54 descendente tiene fechas mejores, también vale; **nunca mezclar trayectorias en una comparación**.
- **Aceptación:** `valid_pct` ≥ 80 % en `timeseries.json`; hectáreas recalculadas; manifiesto con los gránulos nuevos; `docs/data-notes.md` actualizado con lo aprendido (que el cuadro 171 de la trayectoria 75 casi no cubre la zona).

### G2 · «¿A quién afecta?» con números reales
- Calcular la exposición de cada mancha NISAR con `worldpop.tif` (personas), `worldcover.tif` (cultivo, bosque, pastizal) y centros poblados de OpenStreetMap a menos de 2 km.
- Guardar en `exposure/ayacucho-huanta.json` con la fuente, el año y la licencia de cada capa.
- Mostrar en la tarjeta: personas, hectáreas por tipo de cobertura y pueblos cercanos con su distancia.
- **Aceptación:** el JSON deja de estar vacío; una prueba verifica que la suma de hectáreas por cobertura coincide con el área de la mancha.

### G3 · Cifras coherentes y validación
- La tarjeta destacada de NISAR muestra el **total** de la zona («52,76 ha con caída de HV en 5 zonas»); el detalle de cada mancha va dentro.
- Una sola fuente de verdad para cada número (manifiesto → API → interfaz); prueba que compare lo que muestra la interfaz con el manifiesto.
- Concordancia con **OPERA DIST**: porcentaje del área NISAR que OPERA también marca como pérdida de vegetación, con fechas de ambas fuentes.
- Si SAOCOM ya dio acceso y tiene fechas compatibles: misma comparación. Si no, dejar el estado «requiere registro».
- **Aceptación:** en Calidad se ven el área válida, el umbral en dB, el método y la concordancia con OPERA en porcentaje.

### G4 · Luz para la demo
- Interruptor **«Luz: hora real / siempre de día»** en la barra superior. Por defecto, en la demo, «siempre de día» sobre la zona elegida (sol fijo sobre Sudamérica). Con «hora real», el terminador actual.
- Las luces nocturnas se siguen viendo cuando el lado de noche es visible.
- **Aceptación:** a cualquier hora del día se ven los Andes con imagen satelital al abrir la demo.

### G5 · Tendencia (solo si G1 trae 4 fechas)
- Activar la proyección Theil–Sen con su banda y la etiqueta «Proyección si la tendencia sigue igual — no es una predicción».
- **Aceptación:** con 4 fechas válidas se ve la línea, la banda y el método; con menos, sigue desactivada y lo dice.

### G6 · Sabancaya: el volcán que se mueve
- Buscar GUNW de la trayectoria 46 ascendente (26 fechas en el catálogo); **ver el tamaño antes de descargar** y pedir permiso si pasa de 5 GB.
- Confirmar las rutas del GUNW con `sarlab inspect` y anotarlas; crear el lector solo con rutas confirmadas.
- Mostrar el desplazamiento en la línea de visión (cm) sobre el relieve, con su escala.
- Nivel de alerta volcánica oficial citado con fuente y fecha (Observatorio Vulcanológico), nunca calculado por GAIA.
- **Aceptación:** mapa de deformación del volcán en cm con fechas y gránulos.

### G7 · Historia final y guion de la demo (2–3 min)
Guion recomendado:
1. **0:00:** portada y sonido. «Un radar que ve a través de nubes y humo.»
2. **0:15:** el globo vivo: sismos que laten, columnas de calor y NISAR en órbita.
3. **0:35:** ▶ la danza: 30 días de sismos y fuego en su hora real.
4. **0:55:** vuelo a Ayacucho; el barrido revela el radar; cortina antes/después en falso color.
5. **1:20:** la cifra: hectáreas, porcentaje de área válida, concordancia con OPERA.
6. **1:40:** ¿a quién afecta?: personas, cultivos, pueblos; «Compartir alerta».
7. **2:00:** Sabancaya: el suelo del volcán se mueve (si G6 está lista).
8. **2:20:** cierre: lo que NISAR no puede hacer (no predice sismos, no ve fuego) y sus aplicaciones futuras.

Tareas:
- Ajustar la historia de Ayacucho a ese orden.
- Grabar el video de respaldo.
- Comprobar el modo sin conexión con los datos nuevos.

### G8 · Entrega
- Leer la **guía oficial de entrega de Space Apps 2026** (formato del video o de las diapositivas, campos del proyecto, enlace al repositorio) y cumplirla exactamente; no suponer el formato.
- README con capturas, cómo ejecutar, fuentes y licencias; `06_Requisitos_del_Reto.md` actualizado punto por punto.
- Skill `revision-demo` y subagente `security-reviewer`: sin secretos en el repositorio ni en el bundle (salvo el token de Cesium, limitado por dominio).
- Repositorio público en GitHub (lo crea la persona; Codex prepara el contenido).
- Si se publica una web: limitar el token de Cesium a ese dominio y generar las teselas NISAR desde la API.

### G10 · Publicar la app completa y en vivo (decisión del equipo, 14-nov)
El equipo quiere publicar **la misma app que corre en la PC**, completa y funcional: API FastAPI con datos en vivo (USGS, FIRMS), teselas NISAR generadas al momento, portada, globo y todo lo demás.

Punto de partida (ya existe, no rehacer):
- `services/api/app/main.py` ya sirve la web compilada desde `/` cuando existe `apps/web/dist` (`StaticFiles`, línea ~403). Por eso **un solo contenedor** sirve web y API en el mismo dominio, sin CORS.
- La web llama a `/api` por defecto (`VITE_API_BASE`).
- Rutas configurables: `SARLAB_ROOT` y `DATA_DIR`.
- `data/` está fuera de Git: hay que llevar los datos al contenedor de otra forma.

Alojamiento por elegir con el equipo. Hugging Face exige un plan de pago para crear un Space Docker. Render dispone de un servicio Docker gratuito que se suspende tras 15 minutos. Consulta los requisitos vigentes y los pasos de cada destino en [la guía de despliegue](15_Despliegue_Completo.md).

Tareas:
1. **`Dockerfile` multietapa** en la raíz.
   - Etapa Node: `npm ci` y `npm run build` de `apps/web`.
   - Etapa Python: instala la API y el pipeline con `uv` desde el lockfile. Las ruedas de rasterio traen GDAL; comprobarlo antes de añadir paquetes del sistema.
   - Al final: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}`.
   - Usuario sin privilegios y `.dockerignore` que excluya `.env*`, `data/00_inbox`, `data/01_raw`, `data/99_quarantine`, `art/`, `.mcp.json` y `node_modules`.
2. **Datos dentro de la imagen**:
   - Copiar solo lo que la API lee: `config/`, `data/04_published/`, `data/catalog/` y, de `data/03_processed/`, los COG y JSON que referencian los manifiestos (hoy son ~245 MB, Ayacucho). Un script `tools/deploy/collect_runtime_data.py` arma `deploy/data/` desde los manifiestos y falla si falta algún archivo referenciado.
   - Nunca se copian los `.h5` crudos.
   - Si el servicio limita el tamaño, subir los datos con Git LFS/Xet del propio Space o como dataset aparte; preguntar a la persona antes de subir más de 500 MB.
3. **Secretos**:
   - `EARTHDATA_TOKEN` y `FIRMS_MAP_KEY` van como secretos del servicio, en tiempo de ejecución; nunca en la imagen ni en el repositorio.
   - `VITE_CESIUM_ION_TOKEN` se necesita en la compilación: usar el mecanismo oficial de secretos de compilación del servicio (en Docker, `RUN --mount=type=secret`) y restringir el token al dominio final en cesium.com.
   - `/api/health` solo dice si cada clave está presente (ya lo hace), nunca su valor.
4. **Robustez en vivo**:
   - Caché en memoria de USGS y FIRMS (por ejemplo 10 min) para no agotar la cuota de FIRMS con muchas visitas.
   - Si una fuente externa falla, se muestra el último dato con su hora y el aviso «fuente no disponible»; nunca datos inventados.
   - Límite de peticiones por IP en `/api/tiles` y validación de `z/x/y` y de la capa.
5. **Comprobación local**: `docker build` y `docker run -p 7860:7860 --env-file .env` (la persona ejecuta el `--env-file`; Codex no lee `.env`). Se recorren portada, globo, alertas, Ayacucho con barrido y cortina, exposición, calidad y zona de Sabancaya.
6. **Publicación**:
   - Pasos exactos en `docs/15_Despliegue_Completo.md`, con capturas.
   - La cuenta del servicio, los secretos y el repositorio público los crea la persona; Codex prepara los archivos y los comandos.
7. **Seguridad**: `security-reviewer` revisa la imagen (`docker history`, buscar claves en capas y en `dist/`), las dependencias (`npm audit`, `pip-audit`) y las cabeceras.

**Aceptación:**
- La URL pública abre la portada y el globo en PC y teléfono.
- `/api/health` dice `earthdata: true` y `firms: true`.
- Las alertas USGS y FIRMS son de hoy, con su hora.
- La cortina NISAR de Ayacucho carga teselas reales generadas por el servidor.
- Hay cero errores 404 y de JavaScript.
- Tras 30 min sin uso, la primera carga tarda menos de 10 s, o se documenta el tiempo real.
- La búsqueda de secretos en la imagen y en el bundle da cero resultados.

## Orden si falta tiempo
**G1 → G4 → G2 → G3 → G7 → G10 → G8**. G5 y G6 son extras. G10 va antes de G8 para preparar el enlace de entrega.
Sin G1 el número principal no se puede defender ante el jurado.

## Prompt para Codex (G10, despliegue completo)

```text
Lee CLAUDE.md, AGENTS.md y la fase G10 de docs/13_Plan_Final_Codex.md. Queremos publicar la app
COMPLETA y en vivo (la misma que corre en local: API FastAPI + web + datos NISAR + USGS/FIRMS en
vivo). La API ya sirve apps/web/dist desde "/", así que haz un solo contenedor.
Confirma en la documentación oficial de Hugging Face Spaces (Docker) RAM, puerto, suspensión y
límite de tamaño; si no sirve, propónme Render u otra opción y ESPERA mi elección. Crea Dockerfile,
.dockerignore, el script que reúne solo los datos que leen los manifiestos, caché y límite de
peticiones, y docs/15_Despliegue_Completo.md. No leas .env; yo ejecuto docker run con --env-file.
Prueba con docker build y docker run, recorre toda la app y muéstrame capturas. Pídeme permiso antes
de subir más de 500 MB. Un commit al final con la línea en CHANGELOG.md.
```

## Prompt anterior (G1–G8)

```text
Lee CLAUDE.md, AGENTS.md y docs/13_Plan_Final_Codex.md. Empieza por G1: el análisis actual de Ayacucho
usa la trayectoria 75, que cubre solo el 15 % de la caja (valid_pct 1,7 %). Cambia a la trayectoria 147
ascendente, cuadro 171, que la cubre al 100 %. Revisa los focos FIRMS para elegir 4 fechas, muéstrame
la lista con tamaños y ESPERA mi permiso antes de descargar. No borres los archivos de la trayectoria 75
sin preguntarme. Después sigue con G4, G2, G3, G7 y G8, un commit por fase, mostrando build, pruebas y capturas. Antes de empezar, dime si borrar astronauta.glb fue intencional.
```
