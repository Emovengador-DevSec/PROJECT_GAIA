# Registro de cambios

Una línea por cambio relevante: qué cambió y por qué importa.

## Sin publicar

- Esqueleto inicial del repositorio, configuración y documentación.
- v0.3.0: pipeline NISAR GCOV probado (ventana, dB, umbral robusto, COG, alertas, ingesta), API FastAPI, globo 3D Cesium con shader de franjas, configuración de Claude Code y documentación v3.
- v0.3.1: cumplimiento del enunciado oficial: comparación HH/HV, series de tiempo, relatos con hipótesis físicas, pestaña Historia, modo público/técnico, licencia MIT y plan para los recursos del sábado.
- Portada PROJECT GAIA, fase 1: escena Blender reproducible (`tools/blender/build_gaia_scene.py`, `art/blender/gaia.blend`), 2 cuadros clave en `art/frames/` y créditos en `art/CREDITOS.md`.
- Portada PROJECT GAIA, fase 2: Tierra de día en 8K, máscara de océano con brillo solar, astronauta de NASA 3D Resources; créditos actualizados.
- Portada PROJECT GAIA, fase 3: animación (intro 6 s + bucle 10 s) renderizada en EEVEE; videos MP4/WebM horizontales y verticales y pósteres en `apps/web/public/media/`; NISAR y astronauta en `.glb` con Draco en `apps/web/public/models/`.
- Portada PROJECT GAIA, fase 4: portada web en `apps/web/src/features/gaia/` (video de Blender + interfaz coreografiada con el amanecer, versión vertical, póster con movimiento reducido); el globo Cesium carga en un trozo aparte y se abre con «Entrar a la Tierra».
- Portada PROJECT GAIA, fase 5: verificación visual en 1440×900 y 390×844 (capturas e informe en `art/verificacion/`), contraste del texto corregido, `docs/08_Portada_Project_Gaia.md` y script `tools/verify/verificar_portada.mjs`.
