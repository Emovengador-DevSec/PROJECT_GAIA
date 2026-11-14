# Registro de cambios

Una línea por cambio relevante: qué cambió y por qué importa.

## Sin publicar

- Datos extra D1–D4: cruce de cultivos y pendiente, cortina óptica HLS, contexto agrícola oficial de Ayacucho y archivo histórico MODIS con cobertura diaria verificada y cuota persistente.

- Revisión 19: lluvia excesiva en el semáforo, acumulado IMERG real de Chosica, vuelo y radar desde Mi comunidad, explicación del área fuera de las provincias y panel orbital legible.

- Añadido el plan de datos extra y entrega del domingo (docs/18): erosión por pendiente, óptico HLS, calendario agrícola, historial de incendios y pitch de 30 s en inglés.
- C4 añade reportes ciudadanos en el globo con ubicación aproximada, moderación y cruces informativos con FIRMS y NISAR.

- C3 agrega los arcos climáticos de Ayacucho con NASA POWER, observaciones recientes y una extrapolación térmica hasta 2035.

- C2 activa el semáforo informativo con umbrales publicados, fuentes oficiales peruanas y una ficha para imprimir o compartir por WhatsApp.

- C1 publica fichas de Mi comunidad con exposición HV por lugar, cultivos, población estimada y observaciones recientes de FIRMS y USGS.

- Añadido el plan de valor comunitario (docs/17): resumen por pueblo, semáforo informativo con fuentes oficiales, dos arcos de clima con NASA POWER y reportes ciudadanos seguros; destaca que 518 de las 938 ha de cambio HV están en chacras.
- Validación de publicación: fecha UTC del gránulo, recuento HV y superficies verificadas, relato corregido, compresión y precarga de fuentes, y contenedor con las teselas NISAR reales.

- Añadida la validación previa a publicar (docs/16): pruebas, compilación, recorrido real y secretos en orden; quedan 12 correcciones de cifras, rendimiento y presentación.
- Eliminadas grabaciones intermedias, capturas de prueba y una textura sin uso. Se conservaron los recursos de la app y la evidencia de entrega.

- Retirada la web estática de G9. La aplicación usa FastAPI para consultar los datos reales y generar las teselas NISAR.

- Añadida la fase G10 al plan 13: publicar la app completa y en vivo en un solo contenedor Docker (API, web y datos).

- G9 genera una foto estática fechada con JSON y teselas NISAR, agrega el modo static con mapas locales y prepara la publicación en Pages con verificación sin API y control de secretos.

- G8 prepara el texto y los pendientes de entrega, actualiza Vitest a 4.1.12 para resolver los avisos de seguridad y cierra doctor, pruebas y verificación de la demo con cero vulnerabilidades conocidas.

- G7 actualiza el relato de Ayacucho, verifica la demo con y sin conexión en PC y teléfono y graba un respaldo de 2 min 38 s con los datos nuevos.

- G3 muestra el total HV del manifiesto y las manchas delimitadas por separado, contrasta dos teselas OPERA originales y publica la coincidencia del 2,25 % con la interpretación pendiente de validación.

- G2 publica exposición real de las manchas NISAR con WorldPop, WorldCover y 1.192 localidades OSM, calcula distancias y conserva fecha, licencia y cobertura parcial.

- G4 añade Siempre de día y Hora real en el globo, conserva las luces nocturnas y ajusta el control a pantallas pequeñas.

- G1 activa el par GCOV de trayectoria 147 del 24 de junio y el 10 de octubre, con 99,91 % de cobertura válida, publicación completa por período y consulta de archivos históricos.

- Añadida la fase G9 al plan 13: publicar como sitio estático con foto fija de los datos (Cloudflare Pages o Vercel), sin servidor ni secretos, para que el jurado abra un enlace al instante.

- Procesados dos GCOV reales de Ayacucho con máscara de validez y cobertura común. Cambios abre el barrido en falso color sobre la franja observada y deja disponible la cortina manual.

- Añadido un asistente local en CMD para introducir las tres credenciales con entrada oculta y guardar los archivos de configuración conservando otros ajustes.

- Ajustado el vuelo para centrar las zonas al inclinar la cámara y respetar la oclusión de marcadores detrás del globo; las alturas de focos se actualizan al cargar el relieve.

- Verificación interactiva: aparición escalonada de marcadores al llegar, enlaces compartidos de celdas FIRMS y estado de W7 con el requisito real de Earthdata y procesamiento.

- W6: órbita NISAR propagada con satellite.js autorizado, elementos públicos de CelesTrak fechados, modelo 3D, traza y franja lateral aproximada; la pasada de Ayacucho indica acceso geométrico, sin prometer adquisición.

- W4: el clic vuela al lugar con vista oblicua y recorrido orbital interrumpible con Esc o arrastre; en teléfono el mapa abre con el panel cerrado para conservar espacio.

- W5: secuencia de 30 días con histograma y reproducción de un día por segundo; FIRMS público amplía su cobertura a siete días y los marcadores respetan cada hora observada sin reconstruir la escena.

- W3: el cursor resalta observaciones y muestra lugar, hora, cifra y fuente, con consultas al mapa limitadas a una cada 50 ms.

- W1: llegada a Sudamérica, giro orbital lento que se interrumpe con gestos y contadores calculados a partir de las fuentes disponibles.

- W2: ondas sísmicas, polígonos NISAR sobre el relieve y columnas FIRMS agregadas en hexágonos de unos 10 km, con focos individuales al acercarse.

- W8: paneles con texto legible adaptable, observaciones prioritarias por tipo, grupos por lugar y cifras animadas con movimiento reducido.

- Integradas vistas públicas NISAR de Ayacucho, perturbación OPERA, precipitación IMERG y escenas históricas RADARSAT-1 con fecha, fuente y controles sobre el globo.
- FIRMS admite el CSV público VIIRS NOAA-20 de las últimas 24 horas y conserva el acceso de siete días con clave.
- Ampliados los 14 recursos del reto con su función y uso en GAIA, glosario, explicación temática en fichas y catálogo de humedad SME2.
- Añadidos análisis cuantitativos de concordancia OPERA y acumulado IMERG de tres días para los archivos originales, con máscaras de datos, fechas y unidades verificadas en pruebas.
- Añadida la pestaña Fuentes con los 14 recursos oficiales de Dancing with the SARs, el estado de las fuentes complementarias y enlaces temáticos en las historias y fichas.
- La cortina NISAR admite un compuesto en falso color cuando ambas fechas tienen HH y HV de los mismos gránulos.

- GAIA Alerta F0: globo con imagen satelital y luces nocturnas de NASA, mosaico Landsat y relieve Mapzen de Ayacucho, límites geoBoundaries, localidades OSM, búsqueda y relieve global Cesium ion configurable.
- GAIA Alerta F1: caso Huanta y La Mar, catálogos ASF de Ayacucho y Sabancaya, selección por fechas, trayectoria y marco, ingesta con SHA-256 y publicación de las observaciones comparables.
- GAIA Alerta F2: sismos USGS y detecciones NASA FIRMS por separado, con caché fechada y estados de disponibilidad.
- GAIA Alerta F3: alertas con procedencia, filtros, fichas compartibles e imprimibles y cálculo de exposición con fuentes territoriales.
- GAIA Alerta F4: cortina de dos fechas con teselas de origen, series HH/HV y proyección Theil–Sen a partir de cuatro fechas.
- GAIA Alerta F5–F7: historia de Ayacucho, recursos del reto, navegación desde la portada y demo local con mapas y caché de sismos.

- Limpieza de 2.880 fotogramas intermedios de Blender y tres videos temporales de prueba, liberando 6,41 GB. Los recursos publicados se verificaron mediante SHA-256.

- Reorganizado el acceso en teléfonos verticales con botón a todo el ancho, tres esferas compactas centradas debajo y el control de información separado del grupo, respetando las áreas seguras.

- Retirado de la presentación el párrafo sobre Dancing with the SARs, radar NISAR y temperatura, a petición del usuario.

- Reorganizada la presentación con «Sudamérica bajo observación» en tipografía serif de mayor tamaño, una introducción destacada sobre Ayacucho y un párrafo separado para el reto y las preguntas ambientales.

- Ensanchada la presentación de Gaia en PC, con párrafos de hasta 70 caracteres por línea para reducir los saltos y dar más aire a la composición.

- La presentación de Gaia conecta Dancing with the SARs con Sudamérica y Ayacucho, los sismos, la erosión y los incendios forestales, e incorpora la temperatura como pregunta ambiental del proyecto.

- Rediseñada la presentación superior de Gaia con el título «La Tierra cambia. Comprende sus señales.» y una explicación de la comparación de observaciones NISAR, con jerarquía tipográfica y composición adaptable.

- La portada explica su propósito arriba a la izquierda con «Explora cómo cambia la Tierra con datos radar de NISAR», que aparece después del amanecer junto con el acceso.

- El fondo del botón PROJECT GAIA se llena de una nebulosa negra animada al pasar el cursor o enfocar con el teclado, con el texto blanco sobre las nubes y el recorrido luminoso del borde.

- El borde de PROJECT GAIA muestra un trazo blanco de carga al pasar el cursor o enfocar con el teclado; se detiene al salir y respeta movimiento reducido.

- La entrada PROJECT GAIA se sitúa a la derecha de las tres esferas y centrada con ellas. En pantallas estrechas pasa debajo de los indicadores.

- Ampliado el botón PROJECT GAIA y separados los tres indicadores de NISAR, con rótulos más precisos y aros blancos que giran alrededor del texto fijo. El movimiento reducido mantiene los aros estáticos.

- Esqueleto inicial del repositorio, configuración y documentación.
- v0.3.0: pipeline NISAR GCOV probado (ventana, dB, umbral robusto, COG, alertas, ingesta), API FastAPI, globo 3D Cesium con shader de franjas, configuración de Claude Code y documentación v3.
- v0.3.1: cumplimiento del enunciado oficial: comparación HH/HV, series de tiempo, relatos con hipótesis físicas, pestaña Historia, modo público/técnico, licencia MIT y plan para los recursos del sábado.
- Portada PROJECT GAIA, fase 1: escena Blender reproducible (`tools/blender/build_gaia_scene.py`, `art/blender/gaia.blend`), 2 cuadros clave en `art/frames/` y créditos en `art/CREDITOS.md`.
- Portada PROJECT GAIA, fase 2: Tierra de día en 8K, máscara de océano con brillo solar, astronauta de NASA 3D Resources; créditos actualizados.
- Portada PROJECT GAIA, fase 3: animación (intro 6 s + bucle 10 s) renderizada en EEVEE; videos MP4/WebM horizontales y verticales y pósteres en `apps/web/public/media/`; NISAR y astronauta en `.glb` con Draco en `apps/web/public/models/`.
- Portada PROJECT GAIA, fase 4: portada web en `apps/web/src/features/gaia/` (video de Blender + interfaz coreografiada con el amanecer, versión vertical, póster con movimiento reducido); el globo Cesium carga en un trozo aparte y se abre con «Entrar a la Tierra».
- Portada PROJECT GAIA, fase 5: verificación visual en 1440×900 y 390×844 (capturas e informe en `art/verificacion/`), contraste del texto corregido, `docs/08_Portada_Project_Gaia.md` y script `tools/verify/verificar_portada.mjs`.
- Portada PROJECT GAIA, versión 2: Tierra con media luna de día y luces nocturnas, atmósfera azul sin borde duro, haz con frentes de onda y franja de interferometría sobre el Perú, astronauta EMU de la NASA, rocas y meteoros; render a 2560×1440; sonido ambiente original con botón para silenciar; interfaz escalada para pantallas grandes.
- Relevo de la portada documentado en `docs/09_Relevo_Portada_Gaia.md` (pendientes tras la revisión de la versión 2).
- La portada de Gaia muestra el barrido cian sobre Perú, un amanecer neutro y un astronauta que se acerca la mano al visor. El render parte de Blue Marble en 16K y el título elegido usa Bricolage Grotesque.
- Retirado el astronauta de la portada. La Tierra tiene más luz y un borde atmosférico fino, el Sol produce un destello localizado y los datos del radar se leen en una franja clara.
- «PROJECT GAIA» abre el globo desde el primer fotograma. Se retiraron la presentación y la franja inferior, y las tres cifras del radar se agruparon en círculos sobre el cielo.
- La entrada «PROJECT GAIA» aparece a los 4,5 s de la introducción, con una línea de horizonte, una flecha circular y las tres cifras del radar en secuencia. Al saltar la intro o activar movimiento reducido, el acceso es inmediato.
- «PROJECT GAIA» adopta la forma de cápsula del botón original, con fondo transparente, borde blanco y una flecha dentro. El botón y su nombre aparecen animados tras el amanecer.
- Plan GAIA Alerta por fases para Codex en `docs/10_Plan_GAIA_Alerta_Codex.md`, con diagnóstico del globo y cobertura NISAR comprobada en Ayacucho y Sabancaya.
- Diagnóstico de interactividad y momentos W1–W8 para Codex en `docs/11_Experiencia_Interactiva_Codex.md`.
- Plan final G1–G8 en `docs/13_Plan_Final_Codex.md`: corrige la cobertura NISAR de Ayacucho (trayectoria 147, 100 %), exposición, luz de demo y entrega.
