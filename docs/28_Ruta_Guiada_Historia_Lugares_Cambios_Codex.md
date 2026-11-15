# 28 · Ruta guiada y arreglo de Historia, Lugares y Cambios (plan para Codex)

Escrito el 15 de noviembre de 2026 tras revisar la app en `localhost:5173`. El usuario reporta que **la comparación de radar antes/después no funciona**, que **no sabe por dónde empezar** y que Historia, Lugares y Cambios no siguen una ruta clara. «Sanar la tierra» sí la tiene (diagnóstico → ruta para sanar → aviso por radio) y es el modelo a seguir.

## 0. Diagnóstico (comprobado)

| # | Problema | Causa | Estado |
|---|---|---|---|
| 1 | **No aparece el radar antes/después ni el falso color** | Los manifiestos de `data/03_processed/.../manifest_*.json` guardan rutas absolutas de la PC original (`C:\Users\USUARIO\Desktop\GAIA\data\03_processed\...`). La API (`_local_cog`) no las encuentra y todas las teselas devuelven 404 «El archivo procesado no está disponible localmente». | **Arreglado por Claude Code** en `services/api/app/main.py`: la ruta se reubica bajo la carpeta `03_processed` de esta PC, con la misma comprobación de seguridad. Probado con la función directamente. **Falta reiniciar el servidor de la API**, porque su recarga automática dejó de funcionar y sigue sirviendo el código viejo. |
| 2 | Los manifiestos se vuelven a romper al mover la carpeta | El pipeline escribe rutas absolutas | Pendiente: R1 |
| 3 | En **Lugares**, 3 de 4 lugares (Chosica, Madre de Dios, Sabancaya) **no tienen capas radar ni remediación**, pero se ofrecen igual que Ayacucho | Solo Ayacucho fue procesado | Pendiente: R3 |
| 4 | **Historia** tiene 8 pasos de texto, pero no muestran nada en el mapa ni llevan a la acción | Los pasos no están conectados a capas ni a pestañas | Pendiente: R4 |
| 5 | **Cambios** usa jerga (HH, HV, retrodispersión, falso color, polarización) y no dice qué mirar | Panel técnico sin guía | Pendiente: R5 |
| 6 | No hay una **ruta** entre los módulos: el usuario no sabe qué va primero | Diez pestañas sueltas (ver doc 26) | Pendiente: R2 |

## Estado de ejecución · 15 de noviembre de 2026

El diagnóstico anterior conserva el estado previo. R1–R5 están implementados:

- R1: manifiestos nuevos con rutas relativas; `sarlab fix-manifests` migró los cuatro existentes. La API también resuelve rutas antiguas de otra PC dentro de `03_processed`. Se reiniciaron las API locales.
- R2: guía fija de cinco pasos, con diagnóstico, acciones y aviso de una misma zona real. La primera entrada indica por dónde empezar.
- R3: disponibilidad calculada desde los archivos publicados; Ayacucho tiene comparación y 498 zonas. Chosica, Madre de Dios y Sabancaya conservan sus historias y muestran que no tienen radar procesado.
- R4: pasos de Historia conectados a cámara, capas y accesos a comparación, diagnóstico, calidad, serie y calendario. El paso elegido queda a la vista.
- R5: cortina automática al 50 %, selector HH/HV en lenguaje simple, cifras medidas, falso color con leyenda y error visible con reintento.

Verificación: 170 pruebas Python/API y 17 web aprobadas; Ruff, tipos y compilación correctos. Las cinco consultas directas (antes, después, cambio y ambas fechas RGB) devuelven PNG 200 con píxeles visibles. El navegador recorrió la guía y los cuatro lugares: sin errores de JavaScript y con 330 respuestas de teselas correctas. Capturas a 1366×768 y 375×812, sin desborde horizontal móvil, y resultados locales: `deploy/r28/`.

Revisión del doc 06: se conservan relatos, hipótesis por verificar, HH/HV, comparación temporal, calidad, fuentes, series y contexto complementario separado de NISAR. Los tres lugares sin procesamiento no se presentan como casos cuantitativos.

## 1. Reglas

1. Mantener `CLAUDE.md` y la sección 0 del doc 23: datos reales, procedencia visible y NISAR separado de lo complementario.
2. Mismo estilo que «Sanar la tierra»: títulos de color, viñetas cortas con unidades, sin párrafos largos.
3. Cada paso cabe en el panel sin desplazarse en 1366×768.
4. Un lugar sin datos procesados no se presenta como si los tuviera.

## 2. Pasos para Codex

### R1 · Rutas relativas en los manifiestos (pipeline)
- `publish/manifest.py` y `workflows.py`: guardar `cog_path`, `before_cog_path` y `after_cog_path` **relativos a `data/03_processed`**.
- Script `uv run sarlab fix-manifests`: reescribe los manifiestos existentes con rutas relativas.
- Prueba: un manifiesto con ruta absoluta de otra PC sirve teselas (200); una ruta fuera de `03_processed` sigue dando 404.

### R2 · La ruta guiada «Explorar el terreno» (5 pasos)
Una barra de pasos fija arriba del panel derecho, en todos los módulos:

```
① Lugar  →  ② Qué cambió  →  ③ Por qué  →  ④ Qué hacer  →  ⑤ Avisar
```

| Paso | Abre | Qué muestra | Botón «Siguiente» |
|---|---|---|---|
| ① Lugar | Lugares | Elegir territorio; solo los que tienen datos están activos | «Ver qué cambió» |
| ② Qué cambió | Cambios | Cortina antes/después del radar con explicación simple | «Ver por qué» |
| ③ Por qué | Sanar la tierra → zona prioritaria → Diagnóstico | Factores medidos y causa | «Ver qué hacer» |
| ④ Qué hacer | Ruta para sanar la zona | Técnica, plantas, temporada y quién | «Avisar a la comunidad» |
| ⑤ Avisar | Voz y Minka | Boletín de radio y convocatoria minka | «Volver a empezar» |

- El paso activo se resalta en color. Se puede saltar a cualquier paso.
- Al entrar a la app por primera vez, se muestra una vez «Empieza aquí: ① elige un lugar» (se recuerda en `localStorage` con try/catch).

### R3 · Lugares honesto
- Cada lugar muestra su estado: **«Radar procesado · 498 zonas»** (verde) o **«Solo historia y contexto · sin radar procesado»** (gris), según `/api/layers` y `/api/remediation`.
- Al elegir un lugar sin radar: la cámara vuela, se abre su Historia y Cambios dice «Este lugar aún no tiene comparación radar procesada», sin capas vacías.
- Arriba, una línea: «Ayacucho es el caso completo; los otros tres son relatos con datos históricos y de contexto».

### R4 · Historia conectada al mapa
- Cada uno de los 8 pasos de `config/stories/<zona>.yaml` tiene una **acción en el mapa**: vuelo de cámara y capa a mostrar (radar, fuego, sismos, verdor) y, si corresponde, un botón al módulo (por ejemplo, «La comparación radar» → abre Cambios con la cortina).
- Controles «‹ Anterior · 3 de 8 · Siguiente ›» y barra de progreso.
- Texto de cada paso en viñetas: qué se ve, qué significa y qué dato lo respalda.
- Con `prefers-reduced-motion`: sin vuelo, solo cambia la vista.

### R5 · Cambios claro
- Cabecera en lenguaje simple:
  - «Qué compara: dos pasadas del radar NISAR · 24 jun → 10 oct 2026».
  - «Qué mirar: las zonas oscuras perdieron señal (menos vegetación o suelo removido)».
- La cortina antes/después **se activa sola** al entrar, con el divisor al 50 % y una indicación «⇆ arrastra».
- Selector simple: «Vegetación (HV)» y «Superficie (HH)»; los términos técnicos van en «Ver detalle».
- Falso color: explicado con una leyenda de 3 colores y qué significa cada uno.
- Cifras clave en tarjetas: área con pérdida (ha), cobertura válida (%), umbral (dB).
- Si las teselas fallan, un estado vacío visible con el motivo, no un mapa sin cambios.

### R6 · Verificación (Codex pega la salida)
1. `uv run pytest -q`, `uv run ruff check services`, `npm --prefix apps/web run typecheck` y `npm --prefix apps/web test`.
2. `curl` a `/api/tiles/<capa HV del 24 jun–10 oct>/before/…`, `/after/…` y `?palette=rgb`: deben responder **200** con PNG.
3. Capturas a 1366×768:
   - el paso ② con la cortina activa y la imagen radar visible a ambos lados;
   - Lugares con los estados de los 4 lugares;
   - Historia en el paso 4 con el mapa mostrando la comparación;
   - la barra de 5 pasos recorrida de ① a ⑤.
4. Revisar `docs/06_Requisitos_del_Reto.md`: historia, hipótesis, polarizaciones y comparación siguen cumplidos.

## 3. Prompt para Codex

```text
Eres el ingeniero de GAIA Alerta (NASA Space Apps 2026). Trabajas en D:\GAIA, rama feat/gaia-alerta,
todo en http://localhost:5173. Antes de empezar, reinicia npm --prefix apps/web run dev para que la
API tome el arreglo de rutas del doc 28.

Lee primero: CLAUDE.md, AGENTS.md (no leas .env), la sección 0 del doc 23 y
docs/28_Ruta_Guiada_Historia_Lugares_Cambios_Codex.md.

Construye SOLO el paso R<N> del doc 28. Usa el estilo de «Sanar la tierra»: títulos de color, viñetas
cortas con unidades y nada de párrafos largos. Un lugar sin datos no se presenta como si los tuviera.
Al terminar: ejecuta la sección R6, pega la salida y las capturas, agrega una línea a CHANGELOG.md,
haz commit y detente para que Claude Code revise.
```
