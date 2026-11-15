# 24 · Que las 4 fases se vean al entrar (plan para Codex)

Escrito el 15 de noviembre de 2026. Las fases 1–4 del doc 23 ya funcionan, pero están escondidas: hay que abrir la pestaña **Acción**, elegir una mancha y bajar mucho. El jurado ve primero el globo y «Alertas», y nunca llega a lo nuevo. Este plan lo hace visible en los primeros 10 segundos, **sin inventar nada**.

## 1. Dónde está hoy cada fase

| Fase | Qué es | Dónde está hoy | Problema |
|---|---|---|---|
| 1 · Riesgo y recetas SbN | índice por mancha, causa, receta, especies, presupuesto | pestaña **Acción** (8.ª de 10) → lista → ficha `AlertDetails.tsx` (secciones «Qué pasa», «Por qué», «Receta») | Sin entrada en la portada ni en Alertas; la lista son 498 filas iguales |
| 2 · Clima y calendario | normales por estación, anomalías Open-Meteo, ventanas de siembra, saber tradicional | **Mi comunidad** → un pueblo → `AgricultureEvidence.tsx` (al final) | Solo aparece si eliges un pueblo; las anomalías no llegan a Alertas |
| 3 · Presente vs. escenario, constancia PDF | foto HLS antes/después, escenario a 3 y 5 años, costo-beneficio, PDF | dentro de la ficha de una mancha, muy abajo | Hay que bajar 4 pantallas; el costo-beneficio está oculto hasta verificar costos |
| 4 · GAIA Voz y Minka | guion de radio, audio en español, WhatsApp, compromisos | dentro de la ficha, al final | Igual: escondido; el quechua sin grabar se ve como «pendiente» |

## 2. Reglas (no se negocian)

1. Mantener todo `CLAUDE.md` y la sección 0 del doc 23.
2. **Solo cifras que ya publica la API** (`/api/remediation`, `/api/alerts`, `/api/climate`, `/api/community`). Ningún número escrito a mano en la interfaz.
3. Lo que está «por verificar» sigue diciéndolo; hacerlo visible no lo convierte en dato.
4. Quechua: sin audio sintético; el texto sigue como borrador sin revisar.
5. Diseño: usar los tokens del panel (`--panel-w`, `--panel-bg`, `--panel-line`, `--panel-accent`) y los paneles simétricos de 340 px ya hechos. Respetar `prefers-reduced-motion`. Funcionar en 1366×768 y en celular.
6. Todo en `localhost:5173`. Un commit por paso, con línea en `CHANGELOG.md`.

## 3. Pasos para Codex (en este orden)

### P1 · Tarjeta «Del radar a la acción» en el panel izquierdo (máximo impacto)
- En el panel de Sudamérica/zona (`map-context`), debajo de las tres cifras, una tarjeta nueva de una línea por fase, cada una clicable:
  - **Riesgo:** «61 zonas en nivel medio · 138 con riesgo de erosión» (de `/api/remediation/{aoi}` → `summary` y conteo por `risk_id`).
  - **Clima:** la anomalía activa de la estación o «Sin anomalías esta semana» (de `/api/climate/{aoi}`).
  - **Acción:** «Receta natural y presupuesto por zona» → abre la pestaña Acción.
  - **Voz:** «Boletín de radio listo» → abre la ficha de la zona prioritaria en la sección GAIA Voz.
- Cada línea con icono, cifra en el color del panel y flecha. Si el dato falta, estado vacío que diga qué ejecutar.
- Archivo nuevo `features/workspace/ActionSummary.tsx`; se monta en `App.tsx` dentro de `map-context`.

### P2 · Abrir «Acción» con la zona prioritaria
- Al entrar a la app (tras la portada) la pestaña activa por defecto pasa de «Alertas» a **«Acción»**, salvo que la URL traiga `?alert=` o `?lugar=`.
- Mover «Acción» al 2.º lugar del riel (`config/tabs.ts`), justo después de «Historia».
- En el panel Acción, arriba de la lista: **«Prioridad ahora»** = la mancha con mayor índice que tenga receta (no «causa por verificar»), con su causa, factores con unidades, especies y botón «Ver plan».

### P3 · Ficha de mancha en 4 pestañas cortas, no una pantalla larga
- En `AlertDetails.tsx`, dividir la parte de remediación en pestañas internas: **Diagnóstico** (fase 1) · **Clima** (fase 2) · **Futuro y costos** (fase 3) · **Voz y Minka** (fase 4).
- Cada pestaña cabe en el panel de 340 px sin desplazarse en 1366×768.
- **Diagnóstico** abre por defecto y muestra arriba una franja de factores (caída HV dB, pendiente °, humedad m³/m³, focos, cultivo ha), con «fuera del índice» para los que faltan.
- **Clima:** mover a la ficha el resumen estacional y la anomalía de esa zona (hoy solo están en Mi comunidad).

### P4 · El mapa muestra el riesgo, no solo el cambio
- Nueva capa «Riesgo SbN» en `Globe.tsx`: polígonos de `/api/remediation` coloreados por `color_hex`; gris rayado para «causa por verificar».
- Leyenda: tres niveles + «causa por verificar», en la tarjeta de leyenda ya existente.
- Interruptor en la leyenda «Cambio radar / Riesgo SbN». En la pestaña Acción, «Riesgo SbN» es el modo por defecto.

### P5 · Las anomalías de clima entran en Alertas
- Las anomalías de Open-Meteo frente a P10/P90 aparecen en el feed de Alertas como fuente «Clima · Open-Meteo / NASA POWER», separadas de NISAR, con °C o mm y la fecha.
- Las heladas en puna llevan prioridad alta.

### P6 · Momento de demo de 20 segundos
- Botón «Ver recorrido» en la tarjeta del P1 que hace, con un vuelo de cámara: zona prioritaria → ficha Diagnóstico → Voz (reproduce el audio en español) → Minka (muestra el mensaje de WhatsApp).
- Con `prefers-reduced-motion`: sin vuelo, solo cambia de pestaña.
- Actualizar el guion de `docs/18` con este recorrido.

## 4. Verificación (Codex la ejecuta y pega la salida)

1. `uv run pytest -q` (más pruebas para el resumen de P1 y la prioridad de P2, con datos sintéticos solo en `services/pipeline/tests` o `services/api/tests`).
2. `npm --prefix apps/web run typecheck` y `npm --prefix apps/web test` (pruebas de `ActionSummary` y de la elección de la zona prioritaria).
3. `uv run ruff check services`.
4. En `localhost:5173`, con capturas en 1366×768 y 375×812:
   - al entrar se ve la tarjeta del P1 con cifras que coinciden con `curl localhost:5173/api/remediation/ayacucho-huanta` (`summary`);
   - la pestaña Acción abre con la zona prioritaria y sus 4 pestañas internas;
   - la capa Riesgo SbN colorea el mapa y la leyenda la explica;
   - una anomalía de clima aparece en Alertas (o el estado vacío, si no hay);
   - ningún panel se solapa con otro ni con la barra inferior.
5. Recorrer la sección 0 del doc 23: ningún costo sin fuente, escenario siempre rotulado, quechua sin voz sintética, NISAR separado de lo complementario.

Al terminar cada paso, Codex se detiene y Claude Code lo revisa antes del siguiente.

## 5. Prompt para Codex

```text
Eres el ingeniero de GAIA Alerta (NASA Space Apps 2026). Trabajas en D:\GAIA, rama feat/gaia-alerta.
Todo se usa en http://localhost:5173 (npm --prefix apps/web run dev arranca también la API).

Lee primero, en este orden: CLAUDE.md, AGENTS.md (no leas .env), docs/23_Plan_Maestro_Accion_Natural.md
(sección 0) y docs/24_Plan_Impacto_Accion_Codex.md.

Construye SOLO el paso P<N> del doc 24. Reglas: solo cifras que ya publica la API; lo «por verificar»
sigue diciéndolo; nada de audio quechua sintético; usa los tokens de panel y el ancho de 340 px;
respeta prefers-reduced-motion; prueba en 1366×768 y 375×812.
Al terminar: ejecuta las verificaciones de la sección 4 del doc 24, pega la salida y las capturas,
agrega una línea a CHANGELOG.md, haz commit y detente para que Claude Code revise.
```
