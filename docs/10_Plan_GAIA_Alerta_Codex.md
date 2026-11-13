# 10 · GAIA Alerta: plan por fases para Codex

Escrito el 13 de noviembre de 2026, un día antes del hackathon (14 y 15 de noviembre).
Manda sobre `05_Plan_MVP_72h.md` donde haya diferencia. Las reglas de `CLAUDE.md` y `AGENTS.md` siguen vigentes.

---

## 1. Diagnóstico: por qué hoy se ve mal y «nada funciona»

| Lo que se ve | Causa real | Dónde |
|---|---|---|
| Globo blanco y verde opaco, sin relieve | No hay token de Cesium ion, así que usa el mapa de calles de OpenStreetMap (claro) sobre una esfera lisa sin relieve | `apps/web/src/features/globe/Globe.tsx`, líneas 19–31 |
| Todo pixelado y borroso | Cesium dibuja a la resolución CSS, no a la de la pantalla (`resolutionScale` por defecto), y sin antialiasing | mismo archivo, al crear el `Viewer` |
| Espacio negro sin estrellas visibles | Cielo por defecto de Cesium, de baja resolución | mismo archivo |
| Pestañas Cambios, Tiempo, Calidad y Alertas vacías | **Nunca se descargó ni procesó un dato NISAR.** `data/` está vacía, no hay `.venv`, no hay `.env` con token de Earthdata. Las pestañas muestran a propósito su estado vacío (regla de oro 1) | fases M0 y M1 de `05_Plan` sin hacer |
| No hay nombres de ciudades ni pueblos al acercarse | El mapa base no tiene capa de etiquetas ni límites | `Globe.tsx` |

## 2. Datos NISAR que existen hoy (comprobado en el catálogo público de ASF, 13-nov-2026)

| Zona | Producto | Gránulos desde oct-2025 | Lo que permite |
|---|---|---|---|
| **Ayacucho** (Huanta y La Mar, caja −74,4/−73,9 · −13,4/−12,8) | GCOV | 53 en 3 trayectorias; trayectoria 75 ascendente con 19 fechas (22-oct-2025 → 29-oct-2026) | Serie de un año entero, **temporada de incendios jul–oct 2026 incluida** |
| Ayacucho | GUNW | 42 | Deformación del terreno (deslizamientos) |
| **Sabancaya** (Arequipa) | GUNW | 59; trayectoria 46 con 26 fechas | Serie de deformación del volcán (inflado/desinflado) |

Cada GCOV pesa **unos 2 GB**. Cuatro fechas son unos 8 GB: según `CLAUDE.md`, Codex debe pedir permiso antes de pasar de 5 GB.

## 2b. Todos los recursos oficiales del reto y para qué sirve cada uno

Lista leída de la pestaña «Resources» del reto el 13-nov-2026. Usar todos suma en *validez* y *relevancia*; cada uno tiene su lugar concreto en la app.

### NASA

| Recurso | Para qué lo usa GAIA | Fase |
|---|---|---|
| **ASF Data Search Vertex** (`search.asf.alaska.edu`) | Buscar y elegir a mano las fechas NISAR de Ayacucho y Sabancaya; el pipeline usa la misma API (`asf_search`) | F1 |
| **NISAR Data User Guide** (`nisar-docs.asf.alaska.edu`) | Fuente de verdad de rutas HDF5, productos y madurez; enlazado en la pestaña Calidad | F1 |
| **NASA Earthdata Search** (`search.earthdata.nasa.gov`) | Datos complementarios: OPERA DIST (pérdida de vegetación) para validar el área quemada, FIRMS para fuego activo, lluvia GPM para explicar deslizamientos | F2, F3 |
| **Intro to SAR** (Earthdata) | Glosario en lenguaje llano en el modo público: retrodispersión, polarización HH/HV, por qué el agua se ve oscura | F5 |
| **Intro to Remote Sensing** (Earthdata) | Explicar «activo frente a pasivo»: por qué el radar ve de noche y con nubes, y el óptico no | F5 |
| **NASA ARSET** (cursos en inglés y **español**) | Enlace «Aprende más» en español para docentes y autoridades; método citado en el modo técnico | F5 |
| **NISAR StoryMaps** (inundaciones, incendios, subsidencia, derrames, glaciares) | Modelo de narrativa para el modo historia; enlace por tipo de alerta | F5 |
| **NISAR Applications White Papers** | Cada tipo de alerta cita su hoja de beneficio social (incendios, deslizamientos, volcanes, agricultura): responde «¿qué aplicaciones futuras tiene NISAR?» | F3, F5 |
| **UAVSAR Postcards** (compuestos en falso color) | Compuesto RGB con R = HH, G = HV y B = HH/HV. La cortina conserva la misma escala entre fechas. Para identificar cobertura o atribuir cambios se requiere evidencia complementaria. | F1, F4 |

### Agencias socias

| Recurso | Para qué lo usa GAIA | Fase |
|---|---|---|
| **CONAE · SAOCOM** (Argentina, catálogo y registro ONE CLICK) | **El plus sudamericano más fuerte:** SAOCOM también es **banda L**, como NISAR. Comparar NISAR con SAOCOM sobre la misma zona es una validación cruzada con un satélite de la región. Requiere registro previo y aprobación; empezar hoy | F3 (plus) |
| **CONAE · [registro del catálogo SAOCOM](https://www.argentina.gob.ar/noticias/la-informacion-saocom-cada-vez-mas-accesible)** | Protocolo oficial para habilitar una cuenta ONE CLICK y consultar las condiciones de acceso | F3 (plus) |
| **CSA · RADARSAT Constellation Mission** (banda C) | Comparar cómo responden la banda L de NISAR y la banda C de RCM a la vegetación y a la superficie en observaciones compatibles. | F5 (plus) |
| **CSA · RADARSAT-1** (1995–2013) | Archivo histórico: «cómo era esta zona hace 20 años», si hay cobertura de Ayacucho o Sabancaya | F5 (plus, solo si hay cobertura) |
| **CSA · tutorial de SAR en Python** | Referencia para el lector de RCM/RADARSAT y para la calibración | F3, F5 |

Reglas al usarlos: NISAR siempre etiquetado aparte; cada capa externa con su agencia, fecha y licencia en pantalla; respetar los términos de uso de cada sitio no estadounidense (lo exige la página del reto). Si una fuente necesita registro (SAOCOM, RCM), la persona crea la cuenta; Codex no.

### Pantalla «Fuentes del reto»
Agregar al panel lateral una sección **Fuentes** con los 14 recursos agrupados (Datos NISAR · Datos complementarios · Otras agencias · Aprende), cada uno con una frase de para qué lo usa GAIA y su estado: *en uso*, *validación* o *para aprender*. Demuestra al jurado que se usó el material oficial completo.

Estado de implementación del 13 de noviembre. La pestaña Fuentes muestra los 14 enlaces
oficiales y el detalle de su función, uso y fases. Historia integra el glosario, ARSET en
español, documentos temáticos y capas reales de contexto. Ayacucho tiene cortina visual de
mosaicos NISAR de junio y octubre. FIRMS usa el CSV público de 24 horas. Madre de Dios y
Sabancaya tienen recortes históricos RADARSAT-1. OPERA e IMERG cuantitativos requieren sus
archivos originales autenticados. SAOCOM requiere registro y cobertura compatible. Las
pruebas de los análisis numéricos usan únicamente datos sintéticos en el directorio de
pruebas. El cierre científico de F1 sigue pendiente de procesar los HDF5 autorizados.

## 3. La idea plus: «GAIA Alerta — el radar que avisa»

Un globo tipo Google Earth, oscuro y nítido, donde Sudamérica tiene **alertas vivas sobre el relieve 3D**. Cada alerta dice qué pasa, dónde, desde cuándo, con qué dato, **a quién afecta** y cómo avisar a la comunidad.

La clave para ganar: **tres velocidades de información, cada una con su fuente honesta.**

| Velocidad | Fuente | Retraso real | Qué aporta |
|---|---|---|---|
| **Minutos** | Sismos: USGS (sin clave) | ~5–20 min | Dónde tembló y con qué magnitud |
| **Horas** | Fuego activo: NASA FIRMS (VIIRS/MODIS, clave gratuita) | ~3 h | Dónde hay calor de incendio ahora |
| **Días** | **NISAR** (radar) | pasa cada 12 días; el producto tarda días | **Lo que nadie más ve:** área quemada bajo el humo y las nubes, terreno que se mueve, suelo que se seca, agua que sube; de día, de noche y con nubes |

NISAR es la estrella y se etiqueta aparte (regla 4); USGS y FIRMS son complementarios.

### Lo que hace que tenga impacto
1. **«¿A quién afecta?»**: cada alerta cruza su área con población (WorldPop), cultivos (ESA WorldCover) y centros poblados (OpenStreetMap): «≈ 1 200 personas, 340 ha de cultivo y 3 centros poblados a menos de 2 km».
2. **Antes / después / tendencia** sobre el relieve: cortina deslizable entre dos fechas reales y una proyección de tendencia con su incertidumbre.
3. **Aviso a la comunidad**: botón «Compartir alerta» que abre WhatsApp con el texto ya escrito (qué, dónde, fuente, enlace) y una ficha imprimible en lenguaje llano. Opcional: versión en quechua revisada por una persona hablante.
4. **Modo historia por caso**: Ayacucho (incendios 2026), Sabancaya (volcán que se infla), Chosica (huaicos), Madre de Dios (deforestación).

### Lo que NO se puede prometer (y conviene decirlo al jurado)
- **Predecir terremotos: imposible**, con ningún dato. Sí se puede mostrar la deformación del suelo después de un sismo y dónde el terreno se mueve.
- **Ver fuego con radar: no.** El radar no mide calor. El fuego activo viene de FIRMS; NISAR muestra lo quemado aunque haya humo o nubes, y el suelo seco antes de la temporada.
- **Aviso instantáneo con NISAR: no.** Pasa cada 12 días. El aviso rápido viene de USGS y FIRMS; NISAR confirma la extensión y el daño.
- **«Futuro»** = proyección de tendencia («si sigue igual que en los últimos meses…») con banda de incertidumbre, nunca predicción. Solo con 4 fechas o más. Nunca para sismos.
- **Volcanes**: el inflado del suelo es una señal previa conocida, pero el nivel de alerta oficial lo da el Observatorio Vulcanológico (INGEMMET/IGP). GAIA lo muestra citando la fuente y la fecha, no lo inventa.

## 4. Cómo debe verse

- **Paleta**: negro profundo `#05070a`, blanco `#f4f7fb`, acentos vivos con significado y forma propia (para quien no distingue colores):
  - rojo `#ff3b3b` y llama · fuego activo (FIRMS)
  - naranja `#ff8a00` y hexágono · área quemada (NISAR)
  - violeta `#a855f7` y rombo · terreno que se mueve (NISAR GUNW)
  - cian `#22d3ee` y gota · agua o humedad (NISAR)
  - ámbar `#fbbf24` y círculo con ondas · sismo (USGS)
- **Globo**: imagen satelital real de día, luces de ciudades de noche, atmósfera azul, relieve real con exageración ×2 en los Andes, estrellas nítidas, nombres de países, regiones, ciudades y pueblos al acercarse.
- **Alertas**: marcadores que laten sobre el relieve; al acercarse se vuelven la mancha real del cambio (polígono o tesela) pintada sobre el terreno.
- **Paneles**: vidrio oscuro con desenfoque, bordes finos, cifras grandes con unidades (ha, cm, dB, personas), una sola acción principal por panel.
- **Movimiento**: vuelo de cámara al elegir alerta, cortina antes/después con arrastre, entrada escalonada de tarjetas; todo se apaga con `prefers-reduced-motion`.

---

## 5. Fases para Codex

Cada fase termina con: `npm --prefix apps/web run build` sin errores, captura del resultado, una línea en `CHANGELOG.md` y un commit en la rama `feat/gaia-alerta`. **No pasar a la siguiente fase sin mostrar la salida.**

### Lo que debe hacer la persona (no Codex) antes de empezar
1. Crear cuenta gratuita en **NASA Earthdata** y un token; ponerlo en `.env` como `EARTHDATA_TOKEN=`.
2. Crear cuenta gratuita en **Cesium ion** y un token limitado a `localhost` y al dominio de la demo; ponerlo en `apps/web/.env` como `VITE_CESIUM_ION_TOKEN=`. Es un token pensado para el navegador; el límite por dominio evita abusos.
3. Pedir la clave gratuita **FIRMS MAP_KEY** y ponerla en `.env` como `FIRMS_MAP_KEY=`.
4. Instalar `uv` (gestor de Python) si `make setup` lo pide.
5. **Registrarse hoy en el catálogo SAOCOM de CONAE** (perfil ONE CLICK): la aprobación puede tardar. Opcional: cuenta en el portal de datos de la CSA para RCM.

Codex **no lee `.env`** ni pide tokens por el chat.

---

### F0 · Globo premium (3–4 h) — lo que más se nota

**Objetivo:** que el globo se vea como Google Earth en negro: nítido, con relieve, satélite real y nombres.

Tareas:
- `Globe.tsx`: `useBrowserRecommendedResolution = false` y `resolutionScale = devicePixelRatio`; antialiasing MSAA ×4; `scene.highDynamicRange`; atmósfera del cielo y del suelo; niebla suave.
- Con token: relieve mundial (`createWorldTerrainAsync`) e imagen satelital de Cesium ion con etiquetas. Sin token: imagen NASA GIBS (Blue Marble) y aviso visible «sin relieve: falta token».
- Capa nocturna (luces de ciudades) que solo se ve en el lado de noche.
- Cielo estrellado de alta resolución (puede reutilizar `art/textures/starmap_2020_4k.exr` convertido a cubo).
- Límites y nombres: regiones y provincias del Perú (geoBoundaries, CC BY) y centros poblados de OpenStreetMap, visibles según la altura de la cámara.
- Exageración del relieve ×2 por defecto, control en la pestaña Relieve 3D.
- Barra de búsqueda de lugar (lista local de `config/aois` + centros poblados) y vuelo de cámara.
- Quitar el panel inferior claro y el aspecto de plantilla; aplicar la paleta de la sección 4.

Aceptación: a 2560×1440 los bordes de costa y los Andes se ven nítidos al acercarse a Ayacucho; se leen «Ayacucho», «Huanta» y «La Mar»; el lado nocturno muestra luces; 0 errores en consola.

```text
Prompt para Codex:
Lee CLAUDE.md, AGENTS.md y docs/10_Plan_GAIA_Alerta_Codex.md. Ejecuta solo la fase F0.
Confirma cada API de Cesium en la documentación oficial antes de usarla (no inventes opciones).
No leas .env: el token llega como VITE_CESIUM_ION_TOKEN; si falta, usa el respaldo NASA GIBS
y muestra el aviso. Termina con npm run build, una captura a 2560x1440 sobre Ayacucho y otra
de Sudamérica completa, una línea en CHANGELOG.md y un commit en feat/gaia-alerta.
```

---

### F1 · Datos NISAR reales de Ayacucho y Sabancaya (medio día, sobre todo descarga)

**Objetivo:** que las pestañas dejen de estar vacías con datos reales.

Tareas:
- `make setup`, `make doctor`, `make test` (fase M0).
- Crear `config/aois/ayacucho-huanta.yaml` (caja de la sección 2, fenómeno `wildfire`) y su relato en `config/stories/` con hipótesis: «el área quemada baja la señal HV por pérdida de vegetación; con lluvias la señal se recupera».
- `sarlab search --aoi ayacucho-huanta --start 2026-06-01` y elegir **4 fechas de la trayectoria 75 ascendente**: una antes de la temporada (junio), dos durante (agosto–septiembre) y una después (octubre). **Pedir permiso: son ~8 GB.**
- Ingerir, `sarlab inspect` (anotar rutas reales en `docs/data-notes.md`), `sarlab change` entre junio y octubre, `sarlab timeseries` con las 4 fechas.
- Sabancaya: 3–4 GUNW de la trayectoria 46 (si el lector GUNW no existe, crear uno nuevo confirmando las rutas con `sarlab inspect` primero).
- Si la descarga es lenta: leer solo la ventana de la zona por HTTPS con el token (lectura por rangos), en vez de bajar el archivo entero.

Aceptación: `/api/layers?aoi=ayacucho-huanta` devuelve capas con gránulos y fechas reales; Cambios, Tiempo y Calidad muestran datos; hectáreas de caída de HV en Ayacucho con el umbral en dB.

```text
Prompt para Codex:
Fase F1 de docs/10_Plan_GAIA_Alerta_Codex.md. Usa el subagente o la guía datos-nisar.
Crea la zona ayacucho-huanta, busca GCOV desde 2026-06-01, propón 4 fechas de la misma
trayectoria y dirección y ESPERA mi confirmación antes de descargar (son unos 8 GB).
Nunca inventes rutas HDF5: confírmalas con sarlab inspect y anótalas en docs/data-notes.md.
Muestra la salida de sarlab change y sarlab timeseries.
```

---

### F2 · Capas rápidas: sismos y fuego activo (3 h)

**Objetivo:** alertas en minutos y horas, etiquetadas como complementarias.

Tareas:
- API: `GET /api/live/quakes` (USGS, Sudamérica, magnitud ≥ 4, últimos 30 días) y `GET /api/live/fires` (FIRMS VIIRS, caja de Perú, últimos 7 días). La clave FIRMS se usa solo en el servidor. Caché de 10 min en disco; si no hay red, sirve la última copia con su fecha.
- Validar entradas, limitar tamaño de respuesta y tiempo de espera.
- Web: marcadores ámbar (sismos, tamaño por magnitud) y rojos (fuego) sobre el globo, con fuente, hora y retraso.
- Confirmar cada URL y parámetro en la documentación oficial de USGS y FIRMS antes de programar.

Aceptación: con red, se ven los sismos reales del último mes en los Andes y los focos de calor recientes en Perú; cada marcador dice «USGS» o «NASA FIRMS (complementario)» y la hora.

```text
Prompt para Codex:
Fase F2 de docs/10_Plan_GAIA_Alerta_Codex.md. Agrega /api/live/quakes y /api/live/fires en
services/api con caché, validación y tiempo de espera; la clave FIRMS sale de la variable de
entorno del servidor, nunca al navegador. Verifica las URLs en la documentación oficial.
Agrega pruebas en services/api/tests. Pinta los marcadores en el globo con la paleta del plan.
```

---

### F3 · Alertas unificadas y «¿a quién afecta?» (4 h)

**Objetivo:** una lista de alertas clara, con impacto humano.

Tareas:
- Formato único de alerta (en `packages/contracts`): tipo, nivel (bajo/medio/alto), lugar, fecha, fuente, retraso, confianza, geometría, cifras, gránulos.
- `GET /api/alerts` fusiona: NISAR (manchas de cambio de F1), FIRMS y USGS.
- Exposición: cruzar cada mancha con WorldPop (personas), ESA WorldCover (cultivo, bosque) y centros poblados OSM. Precalcular para las zonas configuradas (no en vivo).
- Pestaña Alertas: lista ordenada por nivel, filtro por tipo, tarjeta con cifras grandes y «¿a quién afecta?».
- Al elegir una alerta: vuelo de cámara y la mancha pintada sobre el relieve.
- Botón «Compartir alerta»: enlace de WhatsApp con texto prellenado (sin datos personales) y ficha imprimible.

Aceptación: elegir la alerta de Ayacucho vuela a la zona, pinta el área quemada y muestra hectáreas, personas y cultivos expuestos con sus fuentes.

---

### F4 · Antes, después y tendencia (3 h)

**Objetivo:** ver el cambio con los propios ojos y su tendencia.

Tareas:
- Cortina deslizable sobre el relieve con dos capas reales (fecha A y B), con las fechas visibles a cada lado.
- Pestaña Tiempo: serie con un punto por fecha y el momento del cambio marcado.
- Proyección de tendencia: ajuste robusto (Theil–Sen) sobre 4 fechas o más; banda de incertidumbre; etiqueta fija «Proyección si la tendencia sigue igual — no es una predicción». Desactivada para sismos y con menos de 4 fechas.

Aceptación: la cortina funciona con arrastre y teclado; la proyección muestra método, número de fechas y banda.

---

### F5 · Modo historia y casos (3 h)

- Historia de 5 pasos por caso, con cámara guiada y una frase por paso:
  1. Sudamérica de noche y las alertas vivas.
  2. Ayacucho: los focos de FIRMS en septiembre.
  3. NISAR ve el área quemada a través del humo (cortina antes/después).
  4. ¿A quién afecta? personas, cultivos, pueblos.
  5. Qué viene: recuperación con las lluvias (tendencia) y aplicaciones futuras.
- Repetir para Sabancaya (deformación) si hay datos de F1.
- Responder en pantalla las preguntas del reto: hipótesis física, qué polarización resalta el cambio (HH o HV) y aplicaciones futuras.

---

### F6 · Portada y pulido (3 h)

- Resolver los 5 pendientes de la portada en `docs/09_Relevo_Portada_Gaia.md` (franja arcoíris, luz naranja, títulos, astronauta, nitidez).
- Transición portada → globo sin corte (mismo negro, mismo sonido que se apaga).
- Rendimiento: 60 fps al girar el globo en la máquina de la demo; carga inicial < 3 s en local.

### F7 · Cierre (2 h)

- Skill `revision-demo` y subagente `security-reviewer`.
- Actualizar `06_Requisitos_del_Reto.md` con dónde se cumple cada punto.
- README con capturas; grabar el video de respaldo; copia local que funcione sin internet (datos procesados y caché de USGS/FIRMS).

---

## 6. Si no alcanza el tiempo

Orden de prioridad: **F0 → F1 → F3 (solo NISAR) → F4 (cortina) → F2 → F5 → F6 → F7**.
Sin F1 no hay proyecto: es la única fase con datos NISAR reales, que es lo que pide el reto.

## 7. Reglas para Codex (resumen)
- Datos reales siempre; estado vacío que diga qué hacer cuando falten.
- NISAR etiquetado aparte de USGS y FIRMS.
- No leer `.env`; claves solo en el servidor (salvo el token de Cesium, limitado por dominio).
- Pedir permiso antes de descargas de más de 5 GB o de cambiar la arquitectura.
- Confirmar rutas HDF5 con `sarlab inspect` y cada API externa en su documentación oficial.
- Antes de decir «funciona», ejecutarlo y mostrar la salida.
- Unidades siempre visibles; respetar `prefers-reduced-motion`; interfaz en español.
