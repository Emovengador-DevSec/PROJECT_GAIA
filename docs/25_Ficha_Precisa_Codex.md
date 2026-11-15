# 25 · Ficha de zona precisa y concisa (plan para Codex)

Escrito el 15 de noviembre de 2026 tras revisar la ficha de la zona `…_hvhv_014` y la pestaña **Acción**. Va **antes** del doc 24: primero se corrige lo que parece falso o repetido; después se le da protagonismo.

## 1. Lo que encontramos (revisado con los datos publicados)

| # | Qué ve el usuario | Por qué pasa | Gravedad |
|---|---|---|---|
| 1 | **Las mismas fotos HLS en las 498 zonas** | `_build_optical_context` devuelve las imágenes de toda la caja (1 versión para las 498) | Parece simulado |
| 2 | **El mismo escenario NDVI** en todas las zonas con la misma causa (3 versiones para 498) y «Año 0 (actual) 0,18» | El NDVI de partida sale de `recovery_scenarios.yaml`; es un supuesto mostrado como «actual» | **Dato falso** |
| 3 | El diagnóstico dice «focos de calor recientes… la humedad baja **confirma**» en una zona **sin focos** | `risk_description` es un texto fijo por receta, no se arma con los factores de la zona | **Dato falso** |
| 4 | «Condición física: `caida_hv > 0 AND (heat_score…`» | Se muestra la regla interna | Ruido |
| 5 | Presupuesto con «Fuente: por_verificar», «Fuente: Sierra Azul… (2022)» junto a «costo por confirmar» y «Minka: hasta 40 % menos» | Muestra campos crudos y fuentes/descuentos sin verificar | Contradictorio |
| 6 | Minka: «34 comuneros · 3 días», «Ahorro S/ Sin dato», «Comunidades convocadas:» vacío; SMS «Cambio radar en .» | Cuadrillas y días salen de valores por defecto de `minka.yaml`; los centros poblados no llegan al registro de remediación (`exposure` va vacío) | Inventado / roto |
| 7 | «Descargar constancia **oficial** (PDF)» | Texto del botón | Contradice «no es un certificado oficial» |
| 8 | «Radios locales aliadas (0)», bloque Yachaq «Hoja de ruta», «Quechua Chanka (25 s)» de un borrador sin grabar | Secciones vacías o de futuro dentro de la ficha | Ruido |
| 9 | En la lista de Acción, las tarjetas repiten «Incendio o sequía · Receta: Molle, Tara… · costo por confirmar» | Cada tarjeta muestra la receta genérica en vez de lo que distingue a la zona | Parece repetido |
| 10 | Ficha de ~12 pantallas | Todo apilado en `AlertDetails.tsx` | Cansa leer |

Verificado como **real**: caída HV por zona (3,4–5,4 dB, p10–p90), pendiente, humedad SME2 (0,100 m³/m³ en la zona 014 es un valor medido; solo 1 de 337 zonas lo tiene), suelo SoilGrids, área y exposición WorldCover.

## 2. Regla de oro de la ficha

> **Cada frase debe estar sostenida por un dato de esa zona. Si no, no se muestra.**
> Una ficha cabe en **una pantalla de 1366×768** antes de «Ver más».

## 3. Pasos para Codex

### F1 · Diagnóstico armado con los factores de la zona (corrige #3 y #4)
- En `remediation/risk.py`, generar `summary` con frases solo de los factores presentes:
  «Caída de señal HV de 3,2 dB · ladera de 19° · suelo seco (0,10 m³/m³, 16-sep) · sin focos de calor a < 2 km · sin sismos a < 50 km».
- La explicación de la causa nombra **solo** las evidencias que la activaron (`erosion` → pendiente; `incendio` → focos o suelo seco; etc.).
- Quitar `risk_description` fijo de la ficha y no mostrar nunca `recipe.condition`.
- Prueba: zona sin focos → el texto no contiene «focos».

### F2 · Lo que distingue a cada zona, arriba (corrige #9 y #10)
- Cabecera de la ficha en 4 líneas: causa + nivel · área ha · los 3 factores más altos con unidades · centro poblado más cercano con distancia.
- Tarjetas de la lista Acción: causa · nivel · área · factor principal («19° · 3,2 dB») · centro poblado más cercano. Sin especies ni presupuesto en la tarjeta.
- Agrupar la lista por causa, con el número de zonas por grupo y ordenada por índice.

### F3 · Foto real de **esa** zona o nada (corrige #1)
- Recortar las imágenes HLS ya publicadas (`data/04_published/context/ayacucho-huanta/hls-optical-*.png`, con su georreferencia de GIBS) al rectángulo de la mancha + 300 m, en el servidor, y servirlas por `/api/remediation/{aoi}/{zone}/hls/{before|after}.png`.
- Dibujar el contorno de la mancha sobre el recorte.
- Si no hay georreferencia confiable, **quitar las fotos de la ficha** y dejar el enlace «Ver imagen de toda la zona» en la pestaña Cambios.
- Prueba: dos zonas distintas devuelven recortes distintos.

### F4 · Escenario honesto o fuera (corrige #2)
- Quitar «Año 0 (actual)». No hay NDVI medido por zona: o se calcula el NDVI real de la mancha con HLS (bandas B8A y B04 vía Earthdata, ya configurado) o el escenario se muestra solo como **ganancia relativa** («+0,24 de NDVI a 3 años, según [cita]»), sin valor absoluto.
- Mientras la cita esté «Por verificar», el escenario se oculta detrás de «Ver supuestos».

### F5 · Presupuesto y Minka sin inventos (corrige #5 y #6)
- Presupuesto: una línea por técnica, «costo por confirmar» y nada más. No mostrar fuente ni % de Minka hasta que el costo esté `verificado`. Nunca mostrar el texto `por_verificar`.
- Minka: quitar «34 comuneros», «3 días» y «Ahorro». Mostrar solo lo que se sabe: técnica, temporada, herramientas y las comunidades cercanas.
- Arreglo de datos: incluir en cada registro de remediación los 3 centros poblados más cercanos con distancia (de `/api/community` o del JSON de exposición). Con eso se llenan «Comunidades convocadas», el boletín y el SMS. Si no hay ninguno, el SMS no se genera.
- Prueba: ningún texto termina en «en .» ni muestra «Sin dato» en un campo de dinero.

### F6 · Quitar ruido (corrige #7 y #8)
- Botón: «Descargar constancia (PDF)».
- Ocultar «Radios aliadas» mientras la lista esté vacía.
- Sacar Yachaq de la ficha (va en Fuentes o en el doc de hoja de ruta).
- Quechua: botón «Quechua · borrador sin grabar», sin duración.

### F7 · Ficha en pestañas cortas
- Igual que el P3 del doc 24: **Diagnóstico · Clima · Futuro y costos · Voz y Minka**. Diagnóstico abre por defecto y cabe sin desplazarse en 1366×768.
- «¿A quién afecta?» se resume en una línea en Diagnóstico («Pastizal 1,36 ha · 0 personas estimadas · 4 centros poblados a < 2 km»); el detalle va en «Ver más».

## 4. Verificación (Codex pega la salida)

1. `uv run pytest -q`, `uv run ruff check services`, `npm --prefix apps/web run typecheck`, `npm --prefix apps/web test`.
2. Script de control en `services/pipeline/tests`: con el JSON publicado, comprobar que
   - ninguna `summary` menciona un factor ausente,
   - los recortes HLS de dos zonas distintas no son idénticos (hash),
   - ningún campo visible contiene `por_verificar`, `Sin dato` en dinero ni «en .».
3. Capturas en `localhost:5173` a 1366×768 de **tres zonas de causas distintas**: las fichas deben verse diferentes y la pestaña Diagnóstico entrar sin desplazarse.
4. Revisar de nuevo la sección 0 del doc 23.

## 5. Prompt para Codex

```text
Eres el ingeniero de GAIA Alerta (NASA Space Apps 2026). Trabajas en D:\GAIA, rama feat/gaia-alerta,
todo en http://localhost:5173 (npm --prefix apps/web run dev arranca también la API).

Lee primero: CLAUDE.md, AGENTS.md (no leas .env), la sección 0 de docs/23 y docs/25_Ficha_Precisa_Codex.md.

Construye SOLO el paso F<N> del doc 25. Regla: cada frase de la ficha debe estar sostenida por un dato
de esa zona; si no, no se muestra. No escribas cifras a mano en la interfaz. No uses datos sintéticos
fuera de las pruebas. Después de cambiar el pipeline, regenera con
`uv run sarlab remediation --aoi ayacucho-huanta`.
Al terminar: ejecuta la sección 4 del doc 25, pega la salida y las capturas, agrega una línea a
CHANGELOG.md, haz commit y detente para que Claude Code revise.
```
