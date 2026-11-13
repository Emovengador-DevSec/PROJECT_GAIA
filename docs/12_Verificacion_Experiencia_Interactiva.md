# Verificación de la experiencia interactiva

13 de noviembre de 2026. Implementación de `11_Experiencia_Interactiva_Codex.md`.

## Estado por momento

| Momento | Resultado | Evidencia |
|---|---|---|
| W8 · Paneles | Implementado. Prioridad, grupos por tipo y lugar, texto adaptable y cifras con unidad. | Commit `68e4245`, tres capturas en `art/verificacion/interactiva/W8/`. |
| W2 · Marcadores | Implementado para observaciones disponibles. Ondas USGS, celdas hexagonales FIRMS de unos 10 km, columnas y puntos al acercarse. Los polígonos NISAR requieren datos publicados. | Commit `d8833a1`, pruebas de agregación espacial y tres capturas en `W2/`. |
| W1 · Llegada | Implementado. Vuelo de 3,6 s, giro suave, aparición escalonada y contadores calculados con los datos recibidos. Un gesto detiene el giro; vuelve tras 20 s sin uso. | Commit `e3b8909` y cierre de verificación. Capturas en `W1/`. |
| W3 · Cursor | Implementado. Resaltado y ficha con fecha, cifra, lugar y fuente. Consultas separadas por al menos 50 ms. | Commit `58134b9`. Cinco identificadores USGS respondieron en la comprobación del navegador. Capturas en `W3/`. |
| W5 · Secuencia | Implementado. Histograma, selector por minuto, reproducción de un día por segundo y recuentos filtrados por la hora real. | Commit `dd998d7`. El navegador compara los recuentos con la respuesta real de la API. Capturas en `W5/`. |
| W4 · Inmersión | Implementado. Vuelo oblicuo, giro alrededor del lugar y cancelación con Esc, arrastre o zoom. El móvil abre con el panel cerrado. | Commit `994be8d`. Sismo y foco térmico probados en las tres resoluciones. Capturas en `W4/`. |
| W6 · Órbita | Implementado con la dependencia autorizada. Modelo existente, elementos públicos fechados, traza y franja lateral aproximada. | Commit `66d46c8`. `node tools/verify/orbit.mjs`, validaciones de época y capturas en `W6/`. |
| W7 · Revelado | Pendiente. Hay cero capas NISAR procesadas y no está configurado Earthdata. La app indica el requisito en Cambios. | `/api/health` devuelve `layers: 0` y `earthdata: false`. Capturas del estado pendiente en `W7/`. |

Las capturas de cada momento registran su versión durante la implementación. Las de cierre
incluyen también las funciones que se añadieron después. Resoluciones de comprobación
1440 × 900, 2560 × 1440 y 390 × 844.

## Datos y límites comprobados

- USGS proporciona sismos de magnitud 4 o superior en Sudamérica durante los últimos
  30 días. La escala de magnitud se conserva cuando la fuente la incluye. Si una copia
  anterior no la conserva, se muestra `M`, sin atribuirle una escala específica.
- FIRMS público aporta siete días de VIIRS NOAA-20 de Perú. Se verificaron 1 143
  detecciones en la consulta. Los recuentos pueden cambiar al actualizar la fuente.
  El periodo anterior sin archivo FIRMS no demuestra ausencia de incendios.
- La línea de tiempo cubre el periodo actual de 30 días. No se pudo reproducir septiembre
  de 2026 porque ese archivo histórico no está descargado. No se sustituyó por detecciones
  de otras fechas.
- Los mosaicos oficiales NISAR de GIBS siguen siendo vistas visuales con procedencia.
  No se presentan como cambios cuantificados ni se usan para fingir el revelado W7.
- Continúa el límite autorizado de dos archivos NISAR, unos 3,9 GB. No se descargaron
  los cuatro archivos inicialmente propuestos.
- La órbita utiliza elementos públicos con una edad máxima de siete días y caché de
  seis horas. La visualización se refresca cada hora y se oculta durante la secuencia histórica.
  El acceso geométrico no confirma que NISAR vaya a adquirir una imagen.
- El ensayo orbital usa el ciclo nominal de 12 días para contrastar geometría con las
  trayectorias 54, 75 y 147 del catálogo. No asigna números de trayectoria al TLE/OMM.
  El modelo se centra durante su carga y mantiene la altura calculada sin exageración vertical.
- Falta Cesium ion. Continúan el respaldo NASA GIBS y el relieve regional de Ayacucho.
  La nitidez global al acercarse y el relieve mundial siguen limitados por esa configuración.
- El entorno de captura usa Chrome con renderizado por software. No se acredita una
  tasa de 60 fps en la máquina física a partir de estas capturas.

## Ejecución de comprobaciones

```powershell
npm --prefix apps/web run build
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check services
node tools/verify/interactive.mjs W1
node tools/verify/interactive.mjs W3
node tools/verify/interactive.mjs W5
node tools/verify/interactive.mjs W4
node tools/verify/interactive.mjs W6
node tools/verify/orbit.mjs
```

Resultado de las pruebas Python, 35 aprobadas. Compilación de producción correcta.
Persisten avisos de tamaño de los paquetes de Cesium y advertencias de georreferenciación
de los archivos sintéticos usados exclusivamente en pruebas. Se corrigió un fallo de las ondas
al usar tiempos distintos para los dos radios de una elipse. La prueba ahora detecta también
el panel interno de errores de Cesium, además de las excepciones JavaScript.

`satellite.js` quedó en la rama 6.0.2 compatible con Vite. La versión 7.2 incorporaba módulos
WASM que impedían compilar con la configuración actual. La auditoría npm también señaló
tres avisos preexistentes en Vitest y sus dependencias de desarrollo. La corrección propuesta
requiere un cambio mayor a Vitest 5.1.0 y queda fuera de esta fase de experiencia.

## Revisión de diseño

Se conservaron las excepciones específicas ya registradas en `.impeccable/config.json`
para Instrument Serif en la variante editorial de portada y el aviso de dato provisional
en `tokens.css`. No se añadieron excepciones de archivo completo ni de regla global.
