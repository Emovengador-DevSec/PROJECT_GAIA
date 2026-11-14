# 19 · Verificación final tras C1–C4

Revisión del 14 de noviembre de 2026, 02:10 hora de Perú, sobre el commit `f217536`. Se probó la imagen Docker `gaia-alerta:community` (puerto 7860), que es la que se publicará.

## Resultado: funciona

| Prueba | Resultado |
|---|---|
| Pruebas Python | **51 aprobadas** |
| Tipos y compilación web | Sin errores; compilación en 8 s |
| Los 22 servicios de la API probados en el contenedor | Todos responden **200**; las teselas NISAR son PNG reales |
| Claves | `earthdata: true`, `firms: true`; USGS y FIRMS en vivo con hora |
| Compresión | Alertas: 381 kB |
| Recorrido en Chrome a 1600×900 y 390×844 | Portada → globo → Mi comunidad → reporte → Tiempo: **0 errores de JavaScript y 0 respuestas fallidas** |
| Mi comunidad | 3 provincias, 39 distritos y 1148 localidades. Huamanga: 270,9 ha de cultivo, 171,67 ha de pastizal y 8,03 ha de bosque en 261 zonas. Semáforo, «¿Por qué este color?», qué hacer, enlaces oficiales, WhatsApp e impresión |
| Clima (NASA POWER v2.10.3) | 45 años (1981–2025), tendencia Theil–Sen de 0,05 °C por década, proyección con banda, aviso de «celda regional» |
| Seguridad de reportes | La moderación sin clave o con clave falsa da 403. Un POST vacío, con tipo inválido o fuera de la zona da 422 |
| Entradas inválidas | Zoom inválido da 422; un intento de recorrer rutas da 404 |
| Secretos | Ningún `.env` en la imagen ni en su historial. El bundle lleva el token de Cesium, por diseño, más el token público de la librería |

## Lo que conviene corregir antes de entregar

### Alto (se nota en la demo)
1. **La API del puerto 8000 está desactualizada.**
   - En `localhost:5173`, «Mi comunidad», el clima y los reportes dan 404.
   - Hay que reiniciar `make dev-api`. El contenedor 7860 sí está al día.
2. **El semáforo ignora el exceso de lluvia.**
   - Ahora llueve **4 veces lo normal** (184 mm frente a 45,7 mm en 30 días, NASA POWER), y Ayacucho tiene huaicos entre sus fenómenos (`landslide`). Sin embargo, el semáforo marca verde.
   - Añadir una regla ámbar «lluvia muy por encima de lo normal → riesgo de huaicos y deslizamientos», con el umbral en `thresholds.yaml` y su porqué. La acción preventiva debe salir de una fuente oficial citada (INDECI).
3. **Chosica sin serie de lluvia.**
   - `/api/rainfall/chosica-rimac` devuelve `null`: no existe `data/04_published/rainfall/`.
   - Ejecutar `sarlab rainfall --aoi chosica-rimac` (GPM IMERG) para que la historia «Cuando la quebrada baja» tenga su gráfico.
4. **Tiempo muestra «Sin serie procesada» del radar** si la zona se eligió desde «Mi comunidad». Al elegir Huamanga, Huanta o La Mar, activar la zona `ayacucho-huanta`.
5. **«Mi comunidad» no mueve la cámara.** Al elegir un lugar, volar a él automáticamente, como hace «Ver en el mapa».

### Medio (validez)
6. **Totales que no cuadran sin explicación.**
   - Las tres provincias suman 488 zonas y 497,9 ha de cultivo; la región, 498 zonas y 518,36 ha.
   - Las ~10 zonas restantes caen fuera de Huamanga, Huanta y La Mar. Decirlo en la ficha: «20 ha fuera de las tres provincias».
7. **Enlace del OVI.** Apunta a un servicio ArcGIS REST, una página técnica. Cambiarlo por la página pública del Observatorio Vulcanológico de INGEMMET, confirmando la URL oficial.

### Bajo (presentación)
8. A 1600 px, el texto del panel izquierdo («NISAR en órbita») se superpone al borde del globo. Darle fondo o desplazar el globo.
9. **Archivos sin commit:**
   - **Para confirmar o descartar:** `CHANGELOG.md`, `tools/verify/verificar_portada.mjs`, las capturas de portada en `art/verificacion/` y `docs/18`–`docs/19`.
   - **A decidir:** `.impeccable/` y `art/models/nasa_emu/` siguen sin seguimiento.
   - **Ignorar:** `tsconfig.tsbuildinfo` se regenera solo; mejor añadirlo a `.gitignore`.

## Lo que hace la persona del equipo
- Reiniciar la API (punto 1) antes de enseñar la app en `5173`.
- Al publicar:
  - poner como secretos del servicio `EARTHDATA_TOKEN`, `FIRMS_MAP_KEY` y `GAIA_REPORTS_ADMIN_TOKEN`;
  - limitar el token de Cesium al dominio final.

## Prompt para Codex

```text
Lee docs/19_Verificacion_Final.md. Corrige en este orden: 2 (regla de lluvia excesiva con fuente
oficial), 3 (sarlab rainfall para Chosica), 4 y 5 (Mi comunidad activa la zona y vuela al lugar),
6 y 7, 8 y 9. Confirma cada URL oficial antes de escribirla. Muestra pytest, typecheck, build y
capturas a 1440x900 y 390x844. Reconstruye la imagen Docker, repite el recorrido sin errores y haz
un commit limpio. Después sigue con docs/18 (D1–D4) si hay tiempo antes de las 15:00 del domingo.
```
