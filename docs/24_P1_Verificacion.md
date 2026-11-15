# P1 · Del radar a la acción

Implementado y verificado el 14 de noviembre de 2026 (hora de Lima), siguiendo el primer paso del plan 24.

## Resultado

La tarjeta del panel izquierdo muestra cuatro accesos: Riesgo, Clima, Acción y Voz. Usa el territorio elegido o el caso principal configurado cuando el globo muestra Sudamérica.

- Riesgo lee `summary` de `/api/remediation/{aoi}` y cuenta las manchas por `risk_id`; abre Acción.
- Clima muestra el aviso vigente de mayor prioridad con su fecha. Un pronóstico ausente o vencido tiene un estado explícito. Abre Tiempo con el clima del territorio correspondiente.
- Acción abre las recetas existentes, sin presentar precios no verificados.
- Voz consulta el guion español de la zona con mayor índice que tenga receta y no sea «causa por verificar». Abre su ficha y enfoca GAIA Voz; no reproduce ni envía mensajes automáticamente.
- El resumen identifica NISAR provisional y fuentes complementarias. Su desplegable conserva fechas, procedencia, aviso de monitoreo y comandos de publicación cuando faltan datos.

En celular, la tarjeta utiliza cifras compactas. Al abrir un panel se ocultan temporalmente el contexto y la línea de tiempo para dejar libre la ficha. Al cerrarlo, vuelven a mostrarse.

## Datos contrastados con la API local

```text
GET localhost:5173/api/remediation/ayacucho-huanta → 200
summary: total_alerts=498, high=0, medium=61, low=437
Conteo risk_id=erosion_huaico: 138
Zona prioritaria: alr_ayacucho-huanta_2026-06-24__2026-10-10_hvhv_413
GET localhost:5173/api/climate/ayacucho-huanta → 200
```

Estas cifras son evidencia de esta verificación; no están escritas a mano en la interfaz. Los contadores de USGS y FIRMS pueden variar al actualizarse.

## Comprobaciones ejecutadas

```text
uv run pytest -q
122 passed, 5 warnings in 15.59s

uv run ruff check services
All checks passed!

npm --prefix apps/web test
Test Files 2 passed (2)
Tests 10 passed (10)

npm --prefix apps/web run typecheck
Código de salida 0; sin errores.

npm --prefix apps/web run build
✓ built in 31.11s

Impeccable detect: []

node tools/verify/action-summary.mjs
1366×768: rowsVisible=true, overflow=false, errors=[]
375×812: rowsVisible=true, overflow=false, errors=[]
Los cuatro destinos abren; Voz enfoca el boletín de la zona prioritaria.
```

Las pruebas nuevas usan los JSON reales publicados y comprueban el resumen, la selección prioritaria, los estados ausentes y un pronóstico vencido. Se omiten las pruebas dependientes de archivos reales si estos no están disponibles; en esta ejecución pasaron las diez, sin omisiones. Las cinco advertencias Python son las conocidas de Rasterio en pruebas. La compilación conserva el aviso de tamaño del módulo Cesium.

## Capturas revisadas

- `deploy/verificacion-p1/entrada-1366.png`
- `deploy/verificacion-p1/entrada-375.png`
- `deploy/verificacion-p1/voz-1366.png`
- `deploy/verificacion-p1/voz-375.png`

P1 no añade costos, escenarios ni grabaciones en quechua. El acceso de Voz afirma que el **guion** está disponible, sin afirmar que el audio esté generado. Los pasos P2–P6 del plan 24 quedan pendientes de su turno y revisión. Los cambios visuales anteriores del árbol de trabajo se mantienen separados del commit de P1.
