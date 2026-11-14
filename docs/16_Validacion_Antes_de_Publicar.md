# 16 · Validación antes de publicar

Revisión del 14 de noviembre de 2026, 00:30 hora de Perú. Se revisó el commit `ec79661` (G9) más los cambios sin confirmar que Codex tenía en curso. Se comprobó contra los planes 11 y 13 ejecutando el software, no leyendo informes.

## Lo que se comprobó y funciona

| Prueba | Resultado |
|---|---|
| Pruebas Python (`pytest`) | **41 aprobadas**, 0 fallos |
| Tipos (`npm run typecheck`) | Sin errores |
| Compilación web (`vite build`) | Correcta en 8 s; el globo pesa 4,3 MB, 1,15 MB comprimido |
| `/api/health` | `earthdata: true`, `firms: true` |
| USGS en vivo | 106 sismos, respuesta en 1,3 s |
| FIRMS en vivo | 933 focos y 510 celdas; **7,3 s la primera vez**, 0,5 s con caché |
| NISAR G1 | Trayectoria 147 ascendente, cuadro 171. Gránulos del 24-jun-2026 y del 10-oct-2026, ambos a las 10:41 UTC, versión P05023. **Área válida del 99,91 %** (antes 1,7 %) |
| Cifras contra el manifiesto | Coinciden: HV 3607,0 ha (píxeles) y 938,28 ha en 498 zonas; HH 4240,44 ha. Umbral HV de 2,63 dB, método MAD |
| G2 exposición | 1114 entradas con población, cobertura y localidades |
| G3 OPERA | 21,08 ha en común; el 2,25 % de lo que marca NISAR también lo marca OPERA |
| Recorrido en Chrome (portada → globo → Lugares → Ayacucho → Historia, Cambios, Calidad, Tiempo) | **0 errores de JavaScript, 0 respuestas 4xx/5xx, 119 llamadas a la API**. Teselas NISAR reales hasta el zoom 11; la cortina antes/después funciona |
| Secretos | Ningún `.env` en Git. El historial no contiene claves. El bundle solo lleva el token de Cesium, por diseño, más el token público de la librería |

## Lo que hay que corregir antes de publicar

### Bloqueantes para subir a internet
1. **Token de Cesium.**
   - Va dentro del bundle; es normal en Cesium, pero quedará público.
   - Antes de publicar, en cesium.com → Access Tokens, **limitarlo al dominio final** (por ejemplo `*.hf.space`).
2. **Sin compresión.**
   - `/api/alerts?include_live=true` envía **6,2 MB por visita**, sin gzip.
   - Añadir `GZipMiddleware` en FastAPI y redondear las coordenadas de los polígonos a 5 decimales (~1 m).
   - Meta: menos de 1,5 MB.
3. **FIRMS lento la primera vez (7,3 s).** Caché del servidor de unos 10 min, y precarga al arrancar el contenedor (ya está previsto en G10).

### Cifras que el jurado puede cuestionar
4. **Hora falsa.**
   - La tarjeta NISAR dice «10 oct. 2026, 12:00 a. m. UTC», pero el gránulo se tomó a las **10:41 UTC**.
   - Mostrar la hora real del nombre del gránulo, o solo la fecha.
5. **Contador «1,106 Cambios NISAR».**
   - Suma las 498 zonas HV y las 608 HH, que son los mismos lugares contados dos veces.
   - Mostrar **498 zonas (HV)**, coherente con la tarjeta.
6. **3607 ha y 938,28 ha sin explicación.**
   - Las 3607 ha son todos los píxeles con caída de HV; las 938,28 ha son los que forman zonas delimitadas.
   - Rótulo propuesto: «3607 ha con caída de señal HV · 938 ha agrupadas en 498 zonas».
7. **Título de la historia: «Ayacucho, las huellas que deja el fuego».**
   - Afirma que fue fuego, pero OPERA solo coincide en un 2,25 % y la propia validación dice que la atribución a incendios requiere más evidencia.
   - Nuevo título: «Ayacucho: qué cambió entre junio y octubre».
   - El fuego pasa a ser una hipótesis que se contrasta con FIRMS.
8. **Datos viejos en la API.**
   - `/api/alerts` sin filtro, y la exposición, siguen incluyendo 8 polígonos del periodo antiguo de la trayectoria 75 (`2026-06-19__2026-10-05`).
   - La interfaz los oculta con `active_only`. En la versión pública, archivar ese periodo o filtrar por defecto.

### Presentación
9. **Formato de números en inglés** dentro de una interfaz en español: «3,607.00», «1,106», «a. m.». Usar `es-PE` sin decimales innecesarios («3607 ha») y hora de 24 h en UTC.
10. **Leyenda poco distinguible**: NISAR (naranja) y USGS (amarillo) se parecen. El plan 10 asigna violeta a NISAR, y además conviene una forma distinta por tipo.
11. **Título de zona sin fondo**: «Ayacucho · Huanta y La Mar», arriba a la izquierda, se mezcla con las etiquetas del mapa. Necesita fondo o sombra.
12. **Portada**: una roca tapa la «S» de «Sudamérica bajo observación» y el satélite queda cortado arriba.

## Estado del árbol de trabajo
- Codex está quitando la versión estática G9 sin confirmar: más de 2900 archivos borrados, entre ellos `tools/snapshot_static.py`, `docs/14_Publicacion.md` y su prueba. También borró capturas de verificación de G4 y G9.
- `astronauta.glb` sigue borrado sin confirmar.
- Antes de subir a GitHub, Codex debe terminar G10 y hacer **un commit limpio**.

## Prompt para Codex

```text
Lee docs/16_Validacion_Antes_de_Publicar.md. Antes de seguir con G10 corrige los puntos 2 a 11, en
este orden: 4, 5, 6, 7 (cifras y textos que el jurado puede cuestionar), luego 2 y 3 (gzip,
coordenadas a 5 decimales, caché y precarga de FIRMS), 8 (archivar el periodo de la trayectoria 75
sin borrar archivos de data/ sin mi permiso), 9, 10 y 11. Añade una prueba que compare el contador y la tarjeta
NISAR con manifest_hvhv.json. Muestra pytest, typecheck, build y capturas a 1440x900 y 390x844.
Termina G10 y haz un commit limpio; dime qué pasa con astronauta.glb y con la versión estática G9
antes de confirmarlo.
```
