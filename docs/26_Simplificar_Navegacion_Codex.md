# 26 · De 10 pestañas a 4 (plan para Codex)

Escrito el 15 de noviembre de 2026. La barra inferior tiene **10 pestañas**: Historia, Lugares, Cambios, Tiempo, Calidad, Relieve 3D, Alertas, Acción, Fuentes y Mi comunidad. Varias muestran lo mismo:

- «Alertas» y «Acción» son dos listas de las mismas zonas.
- «Lugares» y «Mi comunidad» sirven para elegir un sitio.
- «Cambios», «Tiempo», «Calidad» y «Relieve 3D» son vistas del mismo dato NISAR.

Además, cada panel repite procedencia, avisos y fuentes. El jurado no sabe por dónde empezar.

**Orden de trabajo:** primero el doc 25 (ficha precisa), luego este y al final el doc 24 (impacto al entrar). Este plan **no borra ninguna función que pida el reto**: la reubica.

## 0. Antes de empezar (estado al 15-nov, tras F1–F7 del doc 25 y P1 del doc 24)

- La ficha de zona **ya tiene** sus 4 pestañas internas (F7). No se tocan; solo cambia desde dónde se abre.
- La tarjeta «Del radar a la acción» (P1) ya está en el panel izquierdo. Ahí va el botón «Ver recorrido» del paso N4.
- En el árbol hay cambios visuales sin confirmar: la marca GAIA RIKCHAY, los botones azules, la intro y las acciones de órbita. **No los mezcles:** pide al equipo que los confirme o los guarde antes de empezar (`git status` limpio).
- Un intento anterior de este plan se revirtió. Empieza de cero desde el paso N1, en commits pequeños, y detente después de cada uno.

## 1. Qué hace hoy cada pestaña y a dónde va

| Hoy | Contenido (`Inspector.tsx`) | Va a | Cómo |
|---|---|---|---|
| Historia | relato por pasos e hipótesis (`config/stories`) | **Botón «Ver recorrido»** en Inicio | El reto pide «contar historias» e «hipótesis»: se conservan como recorrido guiado y dentro de Cambios («Hipótesis») |
| Lugares | elegir territorio (4 casos) | **Selector de zona** en la barra superior | Ya existe el buscador; se suman los 4 casos como sugerencias |
| Mi comunidad | resumen por pueblo, semáforo, clima, reportes | **Mi zona** (pestaña 1) | Es la vista para la población |
| Cambios | cortina antes/después, polarización HH/HV | **Radar** (pestaña 2), modo «Cambio» | |
| Tiempo | serie de tiempo y clima | **Radar**, modo «Serie» | |
| Relieve 3D | terreno exagerado | **Interruptor «Relieve 3D»** en el mapa | No necesita panel |
| Calidad | gránulos, % válido, OPERA | **Radar**, sección plegable «Calidad del dato» | Procedencia visible: requisito del proyecto |
| Alertas | feed USGS, FIRMS, NISAR | **Alertas y acción** (pestaña 3) | Se fusiona con Acción |
| Acción | riesgo y recetas SbN por zona | **Alertas y acción** | Cada alerta NISAR abre su ficha con receta (doc 25) |
| Fuentes | recursos del reto y estado de fuentes | **Fuentes** (pestaña 4) | Única sección con licencias, créditos y estado |

## 2. Navegación nueva

```
[ Mi zona ]  [ Radar ]  [ Alertas y acción ]  [ Fuentes ]        + botón «Ver recorrido» en el panel izquierdo
```

- **Mi zona:** el lugar elegido con su semáforo, clima de la estación, «qué hacer» (receta resumida) y reportes. Abre por defecto con Ayacucho.
- **Radar:** un selector de tres modos (Cambio · Serie · Calidad), HH/HV y las hipótesis del relato.
- **Alertas y acción:** una sola lista agrupada por fuente. Las zonas NISAR muestran nivel de riesgo y causa; al tocar una se abre la ficha del doc 25.
- **Fuentes:** recursos del reto, licencias, estado de las conexiones y la hoja de ruta (Yachaq, SMS real).

## 3. Quitar repeticiones de información

| Se repite hoy | Queda en un solo lugar |
|---|---|
| Aviso «No reemplaza a INDECI…» en cada panel y en cada ficha | Una línea fija y pequeña al pie del panel derecho |
| Listas de procedencia con licencias en cada ficha | En la ficha, una línea («NISAR GCOV 24-jun → 10-oct · WorldCover · SoilGrids») con enlace a **Fuentes** |
| «Producto provisional», «calibración sujeta a revisión» | Una etiqueta «Provisional» junto a la fecha |
| «¿Para qué sirve esto?», «Aprende más», documento de NASA en cada alerta | En **Fuentes** |
| Contadores 104 / 763 / 498 en el panel izquierdo y otra vez en Alertas | Solo en el panel izquierdo; Alertas filtra |
| Leyenda del mapa y textos de color repetidos en paneles | Solo en la tarjeta de leyenda |

## 4. Funciones que no suman: fuera de la vista principal

Estas funciones no se borran del código; quedan ocultas tras `config/features.yaml` o pasan a Fuentes, como hoja de ruta:

- Yachaq digital: solo es hoja de ruta.
- Vista previa de SMS sin envío real: se muestra solo si hay credencial de Twilio.
- «Radios aliadas»: mientras la lista esté vacía.
- Código QR, «Guardar ficha sin conexión» e «Imprimir ficha»: se agrupan en un único botón «Compartir» con menú.
- Audio quechua: hasta que haya grabación de una persona hablante.
- Costo-beneficio y escenario NDVI: hasta tener fuentes verificadas (doc 25, F4 y F5).

## 5. Pasos para Codex

### N1 · Nueva barra de 4 pestañas
- `config/tabs.ts`: `zone | radar | alerts | sources`. Mantener redirecciones: los enlaces viejos `?tab=` o `?lugar=` abren la pestaña nueva equivalente.
- `Inspector.tsx`: un componente por pestaña (`ZonePanel`, `RadarPanel`, `AlertsActionPanel`, `SourcesPanel`); mover el código existente, sin reescribirlo.
- Iconos y etiquetas de 1 o 2 palabras. La barra cabe sin desplazarse en 375 px.

### N2 · Radar con modos
- Selector segmentado Cambio · Serie · Calidad dentro del panel, más HH/HV.
- Relieve 3D pasa a ser un interruptor en el mapa, junto a la leyenda.
- Las hipótesis del relato quedan en un plegable «Hipótesis» dentro de Radar.

### N3 · Alertas y acción fusionadas
- Una lista con grupos por fuente (NISAR · USGS · FIRMS · Clima). En NISAR, cada fila muestra causa, nivel, área y factor principal (doc 25, F2).
- Se elimina la pestaña Acción; su resumen de niveles va arriba del grupo NISAR.

### N4 · Historia como recorrido
- El botón «Ver recorrido» en el panel izquierdo reproduce los pasos de `config/stories/<zona>.yaml` con vuelos de cámara.
- Sin vuelos si está activado `prefers-reduced-motion`.

### N5 · Limpieza de repeticiones
- Aplicar la tabla de la sección 3 y ocultar lo de la sección 4 con interruptores en `config/features.yaml`.
- Medir antes y después la altura de la ficha de una zona en 1366×768 (en píxeles) y el número de palabras visibles al abrir cada pestaña. Objetivo: al menos un 50 % menos.

## 6. Verificación (Codex pega la salida)

1. `uv run pytest -q`, `uv run ruff check services`, `npm --prefix apps/web run typecheck`, `npm --prefix apps/web test`. Agregar una prueba de que las 4 pestañas existen y de que los enlaces viejos redirigen.
2. Revisar `docs/06_Requisitos_del_Reto.md` punto por punto y actualizar la columna «Dónde» con la ubicación nueva: relato, hipótesis, polarizaciones, serie de tiempo, calidad, contexto y factores humanos. **Ninguno puede quedar sin lugar.**
3. Capturas en `localhost:5173` a 1366×768 y 375×812 de las 4 pestañas y del recorrido.
4. Tabla de antes y después: palabras visibles al abrir cada pestaña y altura de la ficha.

## 7. Prompt para Codex

```text
Eres el ingeniero de GAIA Alerta (NASA Space Apps 2026). Trabajas en D:\GAIA, rama feat/gaia-alerta,
todo en http://localhost:5173.

Lee primero: CLAUDE.md, AGENTS.md (no leas .env), docs/06_Requisitos_del_Reto.md, docs/25 y
docs/26_Simplificar_Navegacion_Codex.md.

Construye SOLO el paso N<N> del doc 26. Mueve código existente; no lo reescribas ni borres funciones
que pide el reto. Lo que se oculta va detrás de config/features.yaml. Mantén los enlaces viejos con
redirección.
Al terminar: ejecuta la sección 6 del doc 26, pega la salida y las capturas, actualiza docs/06 si
cambió una ubicación, agrega una línea a CHANGELOG.md, haz commit y detente para que Claude Code revise.
```
