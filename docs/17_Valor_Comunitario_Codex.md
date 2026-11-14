# 17 · Valor comunitario: de «qué cambió» a «qué hago yo»

Escrito el 14 de noviembre de 2026 tras el commit `fd0966e`. Manda sobre los planes anteriores en lo que toca a impacto social.
Las reglas de `CLAUDE.md` siguen vigentes: **todo dato real, con fuente y fecha; nada simulado en la interfaz**.

## Ejecución local

La pestaña **Mi comunidad** usa tres provincias, 39 distritos y 1148 centros poblados con nombre. Los límites distritales provienen de IGN/OCHA en [HDX COD-AB Perú](https://data.humdata.org/dataset/cod-ab-per), con licencia CC BY 3.0 IGO y referencia del 14 de julio de 2020. En provincias y distritos, las manchas HV se recortan al territorio observado. En centros poblados, se agregan las manchas identificadas a 2 km o menos. Las alertas recientes se miden desde el punto de referencia del lugar. La población estimada corresponde a los píxeles válidos dentro de las manchas.

- `uv run python scripts/publish_community.py --districts <per_admin_boundaries.geojson.zip>` regenera las fichas a partir del par activo y sus cruces de exposición.
- `uv run sarlab climate --aoi ayacucho-huanta` actualiza la serie de [NASA POWER](https://power.larc.nasa.gov/docs/referencing/). La pestaña **Tiempo** muestra una extrapolación estadística basada en 45 años completos de estimaciones diarias de reanálisis. El semáforo usa datos climáticos de hasta cinco días de antigüedad. La exposición de suelo antes de las lluvias sigue como hipótesis sin activar una regla.
- Para preparar otra imagen Docker, vuelve a ejecutar el exportador de datos con un destino nuevo e incorpora sus fichas y climatología a `deploy/data/`.

### Moderación

Configura `GAIA_REPORTS_ADMIN_TOKEN` como secreto del servidor. La nota libre se consulta solo en la cola autenticada y se borra al decidir. Las ubicaciones públicas se redondean a una cuadrícula de aproximadamente 500 m. Una coincidencia espacial con NISAR describe únicamente el par histórico.

Consulta `GET /api/reports/moderation` con autorización Bearer. Envía `PATCH /api/reports/moderation/<id>?action=visible` para aprobar o `?action=rejected` para descartar o retirar. El servidor desplegado utiliza un proceso. Si el alojamiento ofrece un volumen persistente, monta la carpeta `/srv/gaia/data/reports` con permisos de escritura para UID 1000.

### Comprobaciones de la implementación

Las pruebas Python terminaron con 51 aprobadas y Ruff pasó. TypeScript y la compilación web terminaron correctamente. `tools/verify/community.mjs` compara las áreas del resumen con la exposición HV, busca Pucajasa, abre el formulario y los arcos climáticos, y comprueba el enlace de WhatsApp y la ficha impresa de una página. Se ejecuta en 1440 × 900 y 390 × 844. Las capturas y los PDF de esta ejecución están en `deploy/verificacion-comunidad/`.

La revisión de seguridad comprobó el origen autorizado, la ubicación redondeada, el acceso a moderación, la nota privada, la caché y la retirada inmediata de un reporte. La regla amarilla por posible suelo desnudo continúa pendiente de contraste con datos de cobertura y calendario agrícola. El clima publicado corresponde a una celda regional, con último dato válido del 12 de noviembre de 2026.

## 1. Dónde está hoy el valor (y qué falta)

| Lo que pidió el equipo | Dónde se ve hoy | Qué falta |
|---|---|---|
| Cambios en la tierra (NISAR) | Cambios: cortina antes/después en Ayacucho | Explicar qué significa para la gente |
| ¿A quién afecta? | Alertas → una mancha → «¿A quién afecta?» | Hay que abrir una de 498 manchas para verlo; no hay un resumen por pueblo |
| Incendios en tiempo real | Globo y alertas (FIRMS, 7 días) | Que diga qué pueblos tienen fuego cerca hoy |
| Sismos | Globo y alertas (USGS, 30 días) | Enlace a la fuente oficial peruana (IGP) |
| Olas de calor y sequía | **No existe** | Datos de temperatura y lluvia (NASA POWER) |
| Pasado, presente y futuro | Solo «últimos 30 días» y 2 fechas NISAR | Línea de 40 años de clima y tendencia honesta |
| Agricultura | Hectáreas de cultivo por mancha, ocultas | Un mensaje claro para agricultores |
| Alerta a la comunidad | **No existe** (doc 10 lo pedía) | Semáforo por pueblo y botón para compartir |
| Volcanes | Zona Sabancaya sin deformación (G6 pendiente) | GUNW o, como mínimo, el nivel oficial del OVI con su fuente |
| Deforestación | Zona Madre de Dios con OPERA | Sin cambios ahora |

## 2. El hallazgo que más valor da

Las 498 zonas HV de Ayacucho (938 ha), sumadas desde `exposure/ayacucho-huanta.json`:

| Cobertura (ESA WorldCover) | Hectáreas |
|---|---|
| **Cultivo** | **518,4** |
| Pastizal | 384,1 |
| Bosque | 19,1 |
| Otro | 17,3 |

- **Comunidades con alguna zona a menos de 2 km:** 597 lugares de OpenStreetMap, por ejemplo Pucajasa, Macachacra, Ichupata, Acco y Ollucopampa.
- **Personas según WorldPop:** unas 435 viven dentro de las propias zonas.

**Más de la mitad del cambio está en chacras.** Del 24 de junio al 10 de octubre las chacras andinas pasan de la cosecha a la tierra preparada para la siembra. Por eso la caída de HV probablemente muestra **el calendario agrícola** y no un incendio: el contraste con OPERA (2,25 %) apoya esa lectura.

Este es el mensaje honesto y potente:
> «Desde el espacio, NISAR ve cuándo se cosecha y se prepara la tierra en 518 ha de chacras de Ayacucho, aunque haya nubes. Eso permite saber qué comunidades agrícolas tienen el suelo desnudo, y por tanto expuesto a la erosión, justo antes de las lluvias.»

Es una hipótesis: se muestra como tal, con su evidencia y lo que la contradeciría.

## 3. Revisión de las ideas del equipo

| Idea | Veredicto | Cómo hacerla sin inventar |
|---|---|---|
| **Dos arcos** (térmico-atmosférico y terrestre-hídrico) con pasado, presente y futuro | **Sí, es la columna visual** | Línea de tiempo con dos carriles (sección 4, C3) |
| **Alerta temprana comunitaria** | **Sí, el mayor impacto** | Un semáforo por pueblo con reglas escritas y datos observados. GAIA no da alertas oficiales: enlaza a SENAMHI, INDECI, IGP y el OVI |
| «En tiempo real» | Con matices | FIRMS: horas. USGS: minutos. NISAR: cada 12 días. Decir siempre la hora del último dato |
| **Ciencia ciudadana** | Sí, como prototipo seguro | Reportes sin datos personales, marcados «sin verificar», contrastados con FIRMS y NISAR. Sin reportes inventados: si no hay, el estado vacío lo dice |
| **Saberes ancestrales** | Solo con fuentes reales | **Codex no escribe saberes andinos de memoria.** Solo entra lo que el equipo reúna de personas o publicaciones citadas, con su autoría. Si no hay fuente, no se muestra |
| Quechua | Solo revisado | Frases cortas del semáforo, solo si alguien que habla quechua chanka las revisa. Si no, nada |
| Predicción del futuro | Como proyección, no predicción | Tendencia de 40 años de NASA POWER (Theil–Sen) con banda de incertidumbre y la etiqueta «si la tendencia sigue igual». Nunca se predicen sismos ni incendios |
| SMS o WhatsApp automáticos | **No ahora** | Piden cuentas, costos y verificación. Sí: botón «Compartir por WhatsApp» que abre el mensaje ya escrito (`wa.me/?text=`), que la persona envía |

## 4. Fases para Codex (orden por impacto)

Cada fase termina con pytest, typecheck, build, capturas a 1440×900 y 390×844, una línea en `CHANGELOG.md` y un commit propio.

### C1 · «Mi comunidad»: el resumen por pueblo (prioridad máxima)
Nueva pestaña o panel **«Mi comunidad»**.
- **Selector** de provincia y distrito: Huamanga, Huanta y La Mar, con los límites geoBoundaries ADM2 que ya existen; ADM3 si se descarga con su licencia. También se puede buscar un centro poblado (OSM).
- **Tarjeta del lugar elegido**, solo con datos que ya existen:
  - Cambio NISAR cerca, en ha por cobertura: cultivo, pastizal, bosque.
  - Focos FIRMS a menos de 5 km en 24 h y en 7 días, con hora.
  - Sismos USGS a menos de 100 km en 30 días, con magnitud y fecha.
  - Población (WorldPop) y fuentes.
- **Mensaje para agricultores** según la sección 2, marcado como hipótesis, con la evidencia y lo que la contradeciría.
- **Comprobar la zona:** la caja `[-74.4,-13.4,-73.9,-12.8]` incluye Huamanga (ciudad de Ayacucho, cerca de −74,22 y −13,16). Si es así, renombrar la zona a «Ayacucho · Huamanga, Huanta y La Mar» en `config/aois` sin cambiar su `id`.
- **Aceptación:** al elegir Huamanga se ve su tarjeta con al menos 3 fuentes con fecha. Una prueba comprueba que las ha por cobertura de la tarjeta coinciden con `exposure`.

### C2 · Semáforo comunitario y compartir
- **Reglas en `config/thresholds.yaml`**, visibles en la interfaz bajo «¿Por qué este color?»:
  - 🔴 Rojo: foco FIRMS a menos de 5 km en las últimas 24 h.
  - 🟠 Naranja:
    - foco a menos de 5 km en 7 días;
    - ola de calor según C3 (temperatura máxima sobre el percentil 90 de 1991–2020 durante 3 días o más);
    - sismo M ≥ 4,5 a menos de 100 km en 24 h.
  - 🟡 Amarillo:
    - lluvia de 30 días por debajo del 50 % de lo normal (sequía), o
    - suelo desnudo en chacras según NISAR antes de la temporada de lluvias (riesgo de erosión).
  - 🟢 Verde: nada de lo anterior.
- **Texto fijo:** «Indicador informativo de GAIA, no es una alerta oficial.» Debajo, enlaces a **SENAMHI** (avisos meteorológicos), **INDECI** (emergencias), **IGP** (sismos del Perú) y **OVI-INGEMMET** (volcanes). Codex debe **confirmar cada URL y número de emergencia en la web oficial**, no de memoria.
- **Qué hacer:** 2–3 acciones de prevención por color, tomadas de una fuente oficial citada (INDECI o SERFOR para quemas agrícolas), con su enlace.
- **Compartir:**
  - Botón «Compartir por WhatsApp» con texto corto y el enlace a la vista del pueblo (URL con `?lugar=`).
  - Botón «Imprimir ficha» de una página para el local comunal; `export_pdf` ya está activo en `features.yaml`.
- **Aceptación:**
  - Cada color se puede explicar con datos y hora.
  - Una prueba cubre cada regla con datos sintéticos, solo en `tests`.
  - El texto de WhatsApp no supera 500 caracteres e incluye la fuente y la hora.

### C3 · Los dos arcos: pasado, presente y futuro
- **Datos nuevos: NASA POWER**, sin clave. Usar el API diario por punto con la comunidad `AG` (agroclimatología) y las variables de temperatura máxima, mínima y precipitación, desde 1981 hasta hoy. Hay que **confirmar en power.larc.nasa.gov la URL, los parámetros y la licencia** antes de usarla.
- **Proceso:**
  - Caché en `data/04_published/climate/<zona>.json`.
  - Un comando `sarlab climate --aoi <zona>`.
  - Climatología 1991–2020, días de ola de calor por año, déficit de lluvia y tendencia Theil–Sen con su banda.
- **Visual:** la barra «Últimos 30 días» crece a una línea con dos carriles y tres tramos.
  - **Arco 1, térmico y atmosférico:** ola de calor (POWER), focos de incendio (FIRMS) y anomalía de temperatura.
  - **Arco 2, terrestre e hídrico:** sismos (USGS), cambio del suelo (NISAR), lluvia y sequía (POWER, GPM) y deformación (GUNW, cuando exista).
  - Tramos: **Pasado** (1981–2025), **Presente** (últimos 30 días, en vivo) y **Futuro** (proyección punteada hasta 2035, con su banda y la etiqueta «si la tendencia sigue igual · no es una predicción»).
- **Aceptación:**
  - En Ayacucho se ven 40+ años de temperatura con su tendencia en °C por década.
  - Se ven los días de ola de calor del último año.
  - Ningún sismo ni incendio se proyecta al futuro.

### C4 · Reportes ciudadanos (prototipo seguro)
- **Formulario corto** con tipo (humo/fuego, grieta o deslizamiento, fuente de agua seca, cosecha dañada), punto en el mapa, fecha y una nota de hasta 280 caracteres.
  - Sin nombre, teléfono ni fotos en esta versión.
  - La ubicación se redondea a unos 500 m.
- **API:** `POST /api/reports`.
  - Validación estricta, límite por IP y almacenamiento en SQLite fuera de Git.
  - Moderación: `pending` → `visible` con una clave de administración que solo existe en `.env` del servidor.
- **Capa propia** «Reportes ciudadanos · sin verificar», separada de NISAR y de las fuentes complementarias. Marca «coincide con FIRMS» si hay un foco a menos de 2 km en 24 h.
- **Sin datos inventados:** si no hay reportes, el estado vacío dice «Aún no hay reportes». En el alojamiento gratuito el disco puede borrarse al reiniciar: decirlo en la interfaz.
- **Seguridad:** el `security-reviewer` revisa este endpoint (inyección, abuso, privacidad) antes de publicarlo.

### C5 · Extras si sobra tiempo
- **Humedad del suelo NISAR (SME2)** para Ayacucho: 27 observaciones en el catálogo. **Ver el tamaño antes de descargar**; confirmar las rutas con `sarlab inspect`. Es el dato de agua del propio NISAR y apoya la sequía con radar.
- **Sabancaya:** G6 (GUNW), o mínimo el nivel de alerta del OVI citado con fecha.
- **Proyecciones climáticas oficiales** (NASA NEX-GDDP-CMIP6) para el futuro, solo si se puede extraer un punto sin descargas grandes.
- **Saberes andinos:** solo con contenido reunido por el equipo y citado (sección 3).

## 5. Lo que hace la persona del equipo (no Codex)
- Reunir 2–3 testimonios o fuentes publicadas sobre señales del clima y cuidado del agua en Ayacucho, con permiso y autoría, si se quiere la parte intercultural.
- Pedir a alguien que hable quechua chanka que revise las frases del semáforo, o dejarlas solo en español.
- En la demo, contar la historia de una comunidad concreta: elegirla en C1.

## 6. Guion actualizado (de 2:20 a 2:50)
1. **Portada:** «Un radar que ve a través de nubes y humo.»
2. **Globo vivo:** fuego, sismos y NISAR en órbita.
3. **Los dos arcos:** 40 años de calor y lluvia en Ayacucho, el presente en vivo y la tendencia punteada.
4. **Vuelo a Ayacucho** y cortina NISAR: 938 ha cambiaron, **518 en chacras**.
5. **«Mi comunidad»:** se elige un pueblo; aparece el semáforo y su porqué; se pulsa «Compartir por WhatsApp».
6. **Un reporte ciudadano** real, si el equipo lo envía en vivo, se cruza con FIRMS.
7. **Cierre:** lo que NISAR no puede hacer y a quién sirve (comunidades, agricultores, gobiernos locales).

## Prompt para Codex

```text
Lee CLAUDE.md, AGENTS.md y docs/17_Valor_Comunitario_Codex.md. Implementa C1, C2, C3 y C4 en ese
orden, un commit por fase, con pytest, typecheck, build y capturas a 1440x900 y 390x844.
Todo dato real con fuente y fecha; nada simulado en la interfaz. Confirma en la web oficial cada URL
de NASA POWER, SENAMHI, INDECI, IGP y OVI y cada número de emergencia antes de escribirlos. No
escribas saberes ancestrales ni quechua de memoria. El semáforo es informativo, no alerta oficial.
Para C4 pide al security-reviewer una revisión del endpoint antes del commit. Pide permiso antes de
descargas de más de 5 GB o de dependencias nuevas. Si se acaba el tiempo, entrega C1 y C2 completas
antes que C3 y C4 a medias.
```
