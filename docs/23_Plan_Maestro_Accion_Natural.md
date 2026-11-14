# 23 · Plan maestro: de detector satelital a acción natural (SbN)

Escrito el 14 de noviembre de 2026 a partir del documento del equipo «Nuevas funciones para mayor impacto…». Zona piloto: **Huamanga, Huanta y La Mar (Ayacucho)**. Lo construye **Antigravity**; Claude Code revisa cada fase antes del commit.

> **Una frase para todo el equipo:** GAIA convierte datos de NISAR en acciones naturales concretas, con costo y en quechua, que llegan a la comunidad por radio, ficha impresa y celular básico.

## 0. Reglas que no cambian (léelas antes de cada fase)

1. Se mantienen todas las reglas de oro de `CLAUDE.md` y `AGENTS.md`: datos reales, NISAR separado de lo complementario, procedencia visible, nada de secretos en el navegador, no escribir en `data/01_raw`, no inventar rutas HDF5.
2. **Apoyo a la decisión, no alerta oficial.** Toda salida (pantalla, PDF, audio, SMS) termina con: «Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. Verificar en campo».
3. **No es tiempo real:** NISAR revisita cada ~12 días. Se dice en pantalla.
4. **Lo que se proyecta no es dato.** El «futuro a 3–5 años» es un *escenario* calculado con supuestos escritos, con la etiqueta «escenario, no observación». **No** se generan fotos con IA del ecosistema restaurado: violaría la regla 1 y resta credibilidad ante el jurado.
5. **Costos con fuente.** Cada precio en soles lleva fuente y fecha en `config/nbs/costs.yaml`. Los rangos del documento del equipo entran con `status: por_verificar` hasta enlazar el documento de SERFOR, Sierra Azul (MIDAGRI) o AGRORURAL. Si no hay fuente, la interfaz muestra «costo por confirmar», no un número.
6. **Quechua revisado por hablante.** Las frases del documento se guardan como borrador (`review: pendiente`). Solo se muestran o se graban las revisadas por un hablante de quechua chanka. No hay TTS quechua confiable: se usan audios grabados por una persona.
7. **Causa por verificar.** Un cambio de radar no prueba incendio, huaico ni sequía. Las recetas dicen «si en campo se confirma X, se recomienda Y».
8. **Una fase a la vez.** Antigravity no empieza la siguiente sin la revisión de Claude Code.

## 1. Lo que ya existe y se reutiliza

| Pieza | Dónde | Uso en este plan |
|---|---|---|
| Manchas NISAR HV (498 zonas, 938,28 ha) | `data/03_processed`, `/api/layers`, `/api/alerts` | Polígonos sobre los que se calcula riesgo y receta |
| Exposición (WorldPop, WorldCover, 1 192 localidades OSM) | `/api/community`, `data/04_published/exposure` | «A quién afecta», cultivos y población |
| Pendiente agrícola (D1) | `data/04_published/agriculture`, `agriculture.py` | Factor pendiente del índice |
| Óptico HLS antes y después (D2) | `data/04_published/context` | Foto real del terreno «presente» |
| Calendario SENAMHI (D3) | `config/agriculture.yaml` | Base del calendario agrícola |
| Focos FIRMS en vivo y MODIS histórico (D4) | `/api/live/fires`, `/api/fire-history` | Factor calor/fuego |
| Sismos USGS | `/api/live/quakes` | Factor sismo reciente |
| Clima NASA POWER, 45 años | `/api/climate`, `climate.py` | Normales por estación y anomalías |
| Lluvia GPM | `/api/rainfall` | Factor lluvia intensa |
| Mi comunidad: semáforo, WhatsApp, ficha imprimible | `features/community` | Se amplía con receta, presupuesto y boletín |
| Reportes ciudadanos con moderación | `/api/reports` | Base de la verificación en campo y de la Minka |
| **NISAR SME2 (humedad del suelo, provisional)** | `config/catalog/nisar_ayacucho-huanta_sme2.json` | Solo catalogado. **Falta descargar, inspeccionar e ingerir** |

## 2. Las 4 fases

Calendario del evento: congelar funciones el **domingo 15 a las 15:00** y enviar antes de las **23:59** (doc 18). **Las fases 1 y 2 entran en la demo.** Las fases 3 y 4 se construyen en la medida en que alcance el tiempo; lo que no esté terminado se presenta como hoja de ruta, nunca como función que «ya funciona».

---

### FASE 1 · Motor de riesgo y «Recetas naturales» (prioridad máxima, entra en la demo)

**Objetivo:** al tocar una zona afectada, GAIA dice qué riesgo hay, por qué, qué solución natural aplicar, con qué especies nativas y cuánto cuesta aproximadamente.

**1.1 Humedad del suelo NISAR SME2** (`geo-data-engineer`)
- Descargar los gránulos SME2 de la trayectoria ya catalogada (~90 MB cada uno) a `data/00_inbox` → `uv run sarlab ingest`.
- `uv run sarlab inspect <archivo>`: anotar en `docs/data-notes.md` las rutas reales de humedad, la máscara de calidad y las unidades. **Prohibido suponer rutas.**
- Nuevo lector `readers/sme2.py` y publicación de un COG de humedad (m³/m³) + resumen por mancha. Etiqueta «NISAR · humedad del suelo · PROVISIONAL».
- Si SME2 no cubre la zona o la calidad no alcanza: estado vacío y el índice funciona sin el factor humedad (lo dice en pantalla).

**1.2 Suelo y relieve** (`geo-data-engineer`)
- **SoilGrids (ISRIC)**, API REST pública sin clave: clase WRB, arcilla/arena y carbono orgánico por mancha. Guardar en caché en `data/04_published/soil/ayacucho-huanta.json` con fecha y licencia (CC-BY 4.0).
- Pendiente: reutilizar D1. Si falta en alguna mancha, Copernicus DEM GLO-30 (AWS Open Data, sin clave).
- Tabla `config/nbs/soils.yaml`: grupo de suelo → combustible/riesgo → especies protectoras (andosoles: queñua y quishuar; litosoles y regosoles: maguey y tuna; kastanozems y phaeozems: tara/guarango, aliso y molle; etc.), con fuente bibliográfica en cada fila.

**1.3 Índice de riesgo ponderado** (`services/pipeline/src/sarlab_pipeline/remediation/risk.py`)
- Factores normalizados de 0 a 1: caída HV, humedad SME2, pendiente, focos de calor (7 y 30 días), sismo reciente (magnitud y distancia), lluvia acumulada, cultivo y población expuestos.
- Pesos y umbrales en `config/nbs/risk.yaml`, no en el código. Cuatro riesgos: **incendio/sequía**, **erosión/huaico**, **ladera inestable tras sismo** y **estrés hídrico agrícola**.
- Salida por mancha: nivel (bajo / medio / alto), factores que lo explican y su contribución («alto porque: pendiente 32°, caída HV 4,1 dB y 3 focos a < 2 km»).
- Comando `uv run sarlab remediation --aoi ayacucho-huanta` → `data/04_published/remediation/ayacucho-huanta.json`.

**1.4 Recetas SbN** (`config/nbs/recipes.yaml`)
- Una receta por riesgo, con condición, técnica, especies nativas, temporada de ejecución, quién la ejecuta (Minka, municipio, AGRORURAL) y fuente:
  - baja humedad + calor → cortafuegos verdes (molle, tara, maguey, tuna) y zanjas de infiltración;
  - erosión + pendiente → bioingeniería (ichu, vetiver) y restauración de andenes;
  - sismo + humedad → reforestación de contención en quebradas y revisión de canales y amunas;
  - estrés hídrico → agroforestería, qochas y amunas (siembra y cosecha de agua).
- `config/nbs/costs.yaml`: costo unitario (S/ por ha, por km o por qocha), rango, fuente, fecha y `status`. Nota de la Minka: hasta 40 % menos en efectivo, **solo si hay fuente**.

**1.5 API y pantalla** (`frontend-3d`)
- `GET /api/remediation/{aoi}` (todas las manchas) y `GET /api/remediation/{aoi}/{zone_id}` (detalle).
- Pestaña nueva **«Acción»** (o sección dentro de Alertas): mapa coloreado por nivel de riesgo; al tocar una mancha aparece una ficha con:
  - qué pasa, en lenguaje llano;
  - por qué (factores, con unidades: dB, °, m³/m³, km);
  - receta natural con especies y temporada;
  - área (ha) × costo unitario = **presupuesto estimado** en soles, con su fuente;
  - fuentes y fechas, separadas: NISAR por un lado y complementarios (SoilGrids, FIRMS, USGS, POWER) por otro.
- La ficha imprimible de «Mi comunidad» incorpora la receta, el presupuesto y un QR al enlace de la zona.

**Criterios de aceptación de la Fase 1**
- `uv run pytest -q` pasa, con pruebas nuevas del índice usando datos sintéticos **solo en `services/pipeline/tests`**.
- Ninguna mancha muestra costo sin fuente ni receta sin condición.
- SME2: rutas anotadas en `docs/data-notes.md` con la salida de `sarlab inspect`.
- Funciona en `localhost:5173` en 1366×768 y en celular.

---

### FASE 2 · Clima, estaciones y calendario agrícola (entra en la demo si da el tiempo)

**Objetivo:** avisar de temperaturas y lluvias fuera de lo normal para cada estación y decir cuándo conviene sembrar o proteger el ganado.

**2.1 Normales por estación** (`climate.py`)
- Con los 45 años de NASA POWER ya descargados: media y percentiles 10/90 de temperatura máxima y mínima, y lluvia, por estación (verano DEF, otoño MAM, invierno JJA, primavera SON) y por mes.
- Mostrar «temperatura típica de esta estación» con unidades (°C, mm).

**2.2 Pronóstico y anomalías**
- **Open-Meteo** (sin clave, uso no comercial): pronóstico a 7–16 días de temperatura, lluvia y humedad del suelo modelada.
- Regla configurable en `config/nbs/climate_alerts.yaml`: si el pronóstico supera el P90 o baja del P10 de la estación, se genera un aviso de **calor anómalo**, **helada** (Tmín < 0 °C en zonas de puna) o **lluvia intensa**.
- Los avisos aparecen en Alertas como fuente «Clima · Open-Meteo / NASA POWER», separados de NISAR.

**2.3 Calendario agrícola inteligente**
- Cruza el calendario SENAMHI (D3), la humedad SME2 (Fase 1) y el pronóstico: ventanas sugeridas para papa, maíz, quinua y habas («condiciones favorables para siembra entre el 18 y el 25 de noviembre»), y avisos de helada para el ganado.
- Siempre como sugerencia con su fundamento; el saber local manda. Agregar un campo para que el promotor agrario registre la fecha tradicional de su comunidad.

**Criterios de aceptación de la Fase 2:** las anomalías se calculan con datos reales y se pueden reproducir con un comando; si Open-Meteo no responde, estado vacío con la hora del último dato.

---

### FASE 3 · Presente vs. escenario futuro, costo-beneficio y constancia de evidencia

**Objetivo:** un estudio que el alcalde o el presidente comunal pueda presentar para pedir fondos o tramitar un seguro.

**3.1 Presente con foto real**
- Antes y después ópticos con **HLS (NASA, Earthdata ya configurado)**: color verdadero y NDVI de la mancha. Opcional: Sentinel-2 de Copernicus Data Space si HLS tiene nubes.
- Relieve 3D de la quebrada con el terreno de Cesium, que ya existe.

**3.2 Escenario a 3 y 5 años (no es dato)**
- Modelo simple y documentado: NDVI actual → NDVI esperado según la receta, con una tasa de recuperación tomada de bibliografía (con cita). Se colorean en verde las zonas que se recuperarían.
- Etiqueta fija: «Escenario con supuestos. No es una observación ni una promesa».

**3.3 Costo-beneficio**
- Costo de la intervención (Fase 1) frente a la pérdida evitada: hectáreas de cultivo expuestas × valor de producción por hectárea (fuente: MIDAGRI/SIEA) × probabilidad del índice. Mostrar ambas cifras y los supuestos.

**3.4 Constancia de evidencia satelital (PDF)**
- Coordenadas, fechas de los gránulos, nivel de cambio, área, foto HLS, fuentes y hash SHA-256 del manifiesto.
- Título honesto: **«Constancia de evidencia satelital para respaldar un trámite»**. No es un certificado oficial ni garantiza el pago del Seguro Agrícola Catastrófico ni de MERESE o bonos de carbono; se presenta como evidencia de apoyo ante la agencia agraria.

**Criterios de aceptación de la Fase 3:** el PDF se genera desde datos publicados, sin claves; cada número del PDF tiene fuente; el escenario nunca aparece sin su etiqueta.

---

### FASE 4 · Último kilómetro: radio, celular básico, Minka digital y Yachaq

**Objetivo:** que la información llegue sin internet y sin necesidad de leer.

**4.1 Boletín de radio «GAIA Voz»** (para la demo hace falta solo esto de la Fase 4)
- Plantilla que convierte el JSON de la Fase 1 en un guion de 30–60 s en español, más frases en quechua **revisadas** (regla 6).
- Audio: TTS en español sin clave (voz de Windows por `pyttsx3`, generado en el servidor) + audios quechua grabados por un hablante en `apps/web/public/audio/qu/`. Se descarga como MP3 desde la ficha.
- Ejemplo de guion: «Atención, comunidades de Huanta y La Mar. El radar detectó cambios en tres zonas; la más cercana está a 1,2 km. Hay cultivos cerca. Autoridades: verificar en campo. Este es un aviso de monitoreo, no una alerta oficial».

**4.2 SMS y llamada (IVR)** · requiere Twilio (ver sección 3)
- Envío de SMS de verificación a líderes registrados («Responde 1 si viste fuego, 2 si no»), con las respuestas guardadas como reportes ciudadanos.
- Llamada automática que reproduce el audio quechua grabado.
- Lista de contactos solo en el servidor, con consentimiento explícito. Sin clave: modo «vista previa» que muestra el mensaje y **no** dice que se envió.

**4.3 Minka digital**
- Cuando una zona pasa a riesgo alto, se arma una solicitud de ayuda («se necesitan 30 comuneros con picos y palas en el sector X» o «500 plantones de ichu») para las 3 comunidades más cercanas y el municipio, compartible por WhatsApp (enlace `wa.me`, sin clave), SMS o la ficha impresa.
- Las respuestas quedan como compromisos visibles en la ficha de la zona.

**4.4 Yachaq digital (voz en quechua)** · hoja de ruta, no para la demo
- Línea donde el comunero llama y deja su reporte de voz; el audio se guarda y se ubica en el mapa para revisión humana.
- El reconocimiento automático de voz en quechua todavía no es confiable: primero grabación + revisión por un promotor bilingüe.

**4.5 Uso sin conexión**
- PWA instalable para técnicos de Tambos PAIS y promotores: guarda en caché la última ficha y el boletín de su zona.

**4.6 Aliados (trabajo del equipo, no del código):** Tambos del Programa PAIS, municipios distritales, agencias agrarias, presidentes de comunidades y radios locales. El impacto se mide en comunidades alcanzadas, boletines emitidos, respuestas de verificación e idiomas o canales cubiertos.

**Criterios de aceptación de la Fase 4:** ningún envío real sin clave y sin consentimiento; el MP3 se genera sin internet; todos los mensajes llevan el aviso de la regla 2.

## 3. Credenciales y APIs

| Servicio | ¿Hace falta clave? | Fase | Qué conseguir | Variable en `.env` (servidor) |
|---|---|---|---|---|
| NASA Earthdata (NISAR SME2, HLS) | **Ya la tienes** | 1, 3 | — | `EARTHDATA_TOKEN` |
| NASA FIRMS | **Ya la tienes** | 1 | — | `FIRMS_MAP_KEY` |
| Cesium ion | **Ya la tienes** | todas | — | `VITE_CESIUM_ION_TOKEN` (`apps/web/.env`) |
| SoilGrids (ISRIC) | No | 1 | — | — |
| Copernicus DEM GLO-30 (AWS) | No | 1 | — | — |
| NASA POWER | No | 2 | — | — |
| Open-Meteo | No (uso no comercial) | 2 | — | — |
| USGS sismos | No | 1 | — | — |
| TTS español (`pyttsx3` + voz de Windows) | No | 4 | — | — |
| WhatsApp por enlace `wa.me` | No | 4 | — | — |
| **Twilio** (SMS y llamadas) | **Sí** | 4 | Cuenta en twilio.com → Account SID, Auth Token y un número. La cuenta de prueba solo envía a números verificados; para Perú en producción se requiere registro regulatorio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` |
| Copernicus Data Space (Sentinel-2) | Opcional | 3 | Cuenta gratuita en dataspace.copernicus.eu, solo si HLS tiene nubes | `CDSE_USER`, `CDSE_PASSWORD` |
| Google Earth Engine | Opcional, **no recomendado ahora** | 3 | Proyecto de Google Cloud registrado para uso no comercial + cuenta de servicio. HLS y Earthdata ya cubren lo necesario | `GEE_SERVICE_ACCOUNT`, archivo JSON fuera del repositorio |
| WhatsApp Business Cloud API (Meta) | Opcional | 4 | Solo si se quiere enviar automáticamente; la verificación de negocio tarda días | `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` |

**Conclusión:** las fases 1 a 3 se hacen con las claves que ya tienes. La única clave nueva necesaria es **Twilio** (Fase 4.2), y la demo puede usar el modo de vista previa sin ella. Las claves van solo en `.env` del servidor y se cargan con `tools/configurar-credenciales.ps1`, nunca en el código, el navegador ni el chat. Añade las variables nuevas, sin valores, a `.env.example`.

## 4. Cómo trabajan Antigravity y Claude Code

1. Antigravity trabaja en la rama `feat/gaia-alerta`, una fase (o subfase) por commit, con una línea en `CHANGELOG.md` en cada uno.
2. Al terminar cada subfase, Antigravity ejecuta y pega la salida de `uv run pytest -q`, `npm --prefix apps/web run typecheck`, `npm --prefix apps/web test` y una captura en `localhost:5173`.
3. Claude Code revisa con `/code-review` y el subagente `security-reviewer`, y comprueba las reglas de la sección 0: fuentes de costos, etiquetas de escenario, quechua revisado y NISAR separado.
4. Para no pisarse: mientras Antigravity edita, Claude Code solo lee. Antes de empezar, `git status` debe estar limpio.

## 5. Prompt para Antigravity (pégalo tal cual)

```text
Eres el ingeniero de GAIA Alerta (NASA Space Apps 2026, reto Dancing with the SARs). Trabajas en
D:\GAIA, rama feat/gaia-alerta. Todo se usa en http://localhost:5173 (npm --prefix apps/web run dev
arranca también la API interna).

Lee antes de tocar nada, en este orden:
1. CLAUDE.md y AGENTS.md (reglas de oro; no leas .env).
2. docs/23_Plan_Maestro_Accion_Natural.md (este plan, sobre todo la sección 0).
3. docs/22_Arranque_en_otra_PC.md, docs/21_Datos_Extra_Verificados.md y docs/data-notes.md.

Construye SOLO la FASE <N> del doc 23, subfase por subfase, en el orden indicado.
- Configuración en config/nbs/*.yaml; nada de pesos, costos ni textos en el código.
- Cada costo con fuente y fecha; sin fuente, la interfaz dice «costo por confirmar».
- Rutas HDF5 solo después de `uv run sarlab inspect`, anotadas en docs/data-notes.md.
- Lo proyectado lleva la etiqueta «escenario, no observación». Nada de imágenes generadas por IA.
- Frases en quechua como borrador hasta que las revise un hablante.
- Sin claves en el código ni en el navegador.
Al terminar cada subfase: ejecuta uv run pytest -q, npm --prefix apps/web run typecheck y
npm --prefix apps/web test; pega la salida; agrega una línea a CHANGELOG.md; haz commit; y detente
para que Claude Code revise. No empieces la siguiente fase sin confirmación.
```

## 6. Guion de la demo (añadir 40 s al de 2:50 del doc 17)

1. «El radar no solo ve cambios: GAIA dice qué hacer». Tocar una mancha de Huanta con riesgo alto.
2. Ficha: por qué (pendiente, caída HV, focos), receta (ichu y zanjas de infiltración), presupuesto con su fuente.
3. Botón «Boletín de radio»: se escucha el audio en español y la frase en quechua grabada.
4. Cierre: «Del satélite a la radio comunitaria, con soluciones que los Andes conocen hace siglos».
