# 18 · Datos extra para el domingo y entrega

Escrito el 14 de noviembre de 2026 (sábado). La entrega cierra el **domingo 15 a las 11:59 p. m.** El pitch oficial es un **video de 30 segundos en inglés**; el recorrido de 2 min 38 s queda como demo de respaldo.

Las reglas de `CLAUDE.md` siguen: datos reales con fuente y fecha, NISAR separado de lo complementario, pedir permiso para descargas de más de 5 GB y para dependencias nuevas.

## Qué resolvemos (una frase para todo el equipo)
> Las nubes y el humo ocultan los Andes a los satélites ópticos. Por eso las comunidades de Ayacucho se enteran tarde de los cambios en sus chacras, pastos y bosques. **GAIA Alerta convierte el radar NISAR (NASA–ISRO), que ve a través de las nubes, en un semáforo por comunidad.** Dice qué cambió, a quién afecta y qué hacer, junto con el fuego y los sismos en vivo y 45 años de clima de la NASA.

## Datos extra, ordenados por impacto y esfuerzo

| # | Dato | Fuente | Criterio que sube | Esfuerzo | Por qué |
|---|---|---|---|---|---|
| D1 | **Pendiente del terreno → riesgo de erosión** | Relieve de Ayacucho que ya está en `apps/web/public/globe/ayacucho-terrain.*`; si no basta, NASADEM (NASA, LP DAAC) | Impacto, Creatividad | Bajo, sin descarga | «X ha de chacras con suelo desnudo en pendientes de más de 15° antes de las lluvias»: convierte el hallazgo agrícola en riesgo concreto de erosión |
| D2 | **Imagen óptica antes/después (HLS)** | NASA Harmonized Landsat Sentinel-2 vía GIBS (visual, sin descarga) | Validez, Presentación | Bajo | Permite ver con los ojos las chacras de junio y de octubre en las manchas NISAR; apoya o refuta la hipótesis de la cosecha |
| D3 | **Calendario agrícola oficial de Ayacucho** | MIDAGRI o SENAMHI (documento oficial citado) | Validez, Relevancia | Bajo | Respalda con una fuente peruana que de junio a octubre es cosecha y preparación de la tierra |
| D4 | **Historial de incendios 2001–2025** | NASA MODIS Burned Area (MCD64A1) o el archivo de FIRMS | Impacto (arco térmico, pasado) | Medio | Muestra en qué meses se quema más cada año y justifica el semáforo de temporada |
| D5 | **Humedad del suelo NISAR (SME2)** | ASF, el propio NISAR (27 observaciones) | Relevancia | Medio; **ver el tamaño antes** | Es el dato de agua del propio NISAR y sostiene la sequía con radar, no solo con reanálisis |
| D6 | Radar banda C (Sentinel-1 RTC) | Microsoft Planetary Computer | Creatividad | Alto | Compara la banda L con la C en Ayacucho. Solo si sobra tiempo |
| D7 | Pronóstico de 7 días | Meteomatics (cuenta de socio del reto) | Impacto (futuro cercano) | Medio; requiere cuenta | Futuro real a corto plazo. Opcional: NASA POWER ya cubre el pasado y la tendencia |

**No ahora:** SAOCOM y RADARSAT (el registro tarda). Se mencionan como «siguiente paso» en el texto del proyecto.

## Fases para Codex (domingo)
1. **D1 + D2 + D3**, a terminar a las 13:00:
   - Calcular la pendiente con el relieve existente y cruzarla con las manchas HV en cultivo; añadir el resultado a «Mi comunidad» y a la historia de Ayacucho.
   - Añadir la capa HLS de GIBS antes/después, confirmando el nombre de la capa en GIBS.
   - Citar el calendario agrícola oficial.
   - **Aceptación:** una cifra «ha de chacras desnudas en pendiente fuerte», con fuente y método; una prueba suma por pendiente y comprueba que da el total de cultivo.
2. **D4**, a terminar a las 15:00: serie anual de área quemada o focos en Ayacucho en el arco térmico, tramo «Pasado».
3. **Congelar funciones a las 15:00.** Desde ahí solo se corrigen errores.
4. **Entrega**:
   - Desplegar G10 con los secretos.
   - Verificar el enlace público en PC y teléfono.
   - Pasar el `security-reviewer`.
   - README final con capturas.

## Prompt para Codex

```text
Lee CLAUDE.md, AGENTS.md y docs/18_Datos_Extra_y_Entrega.md. Primero confirma el commit limpio de
C1–C4 (doc 17) mostrando pytest, typecheck y build. Después implementa D1, D2 y D3 (pendiente y
erosión con el relieve existente, imagen HLS de GIBS antes/después, calendario agrícola oficial
citado) y luego D4. Confirma cada capa y cada URL en la documentación oficial. Datos reales con
fuente y fecha; la erosión y la cosecha son hipótesis con su evidencia. Pide permiso antes de
descargar más de 5 GB o añadir dependencias. A las 15:00 congela funciones y prepara el despliegue
G10 y el README.
```
