# Créditos de recursos · portada PROJECT GAIA

Las texturas viven en `art/textures/` (fuera de Git; se vuelven a descargar de la fuente).
Todo es de dominio público de la NASA. No se usa el logotipo ni la insignia de la NASA.

| Recurso | Archivo local | Fuente | Licencia | Tamaño |
|---|---|---|---|---|
| Tierra de día (Blue Marble Next Generation con relieve, dic. 2004, 21600×10800) | `earth_day_topo_21600.jpg` (original) → `earth_day_8k.jpg` (8192×4096, la que usa la escena) | NASA Visible Earth — `assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-topography/december/world.topo.200412.3x21600x10800.jpg` | Dominio público (NASA) | 24,5 MB → 4,0 MB |
| Tierra de noche (Black Marble 2016, 3 km, 13500×6750) | `earth_night_3km.jpg` | NASA Earth Observatory, imagen 144898 — `.../imagerecords/144000/144898/BlackMarble_2016_3km.jpg` | Dominio público (NASA) | 8,1 MB |
| Mapa estelar (Deep Star Maps 2020, 4K EXR) | `starmap_2020_4k.exr` | NASA SVS 4851 — `svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/starmap_2020_4k.exr` | Dominio público (NASA/GSFC SVS) | 36 MB |
| Astronauta | `art/models/nasa_astronaut/Astronaut.glb` | NASA 3D Resources — `github.com/nasa/NASA-3D-Resources` · `3D Models/Astronaut/` | Dominio público (NASA) | 0,76 MB |

## Hecho en el proyecto (sin recursos externos)
- **NISAR**: modelado a mano en `tools/blender/build_gaia_scene.py` con proporciones reales (reflector de 12 m, brazo de 9 m). NASA 3D Resources no tiene modelo de NISAR.
- **Nubes**: procedurales (ruido). El mapa de nubes de Blue Marble 2002 solo está en `eoimages.gsfc.nasa.gov`, que no responde desde esta red.
- **Máscara de océano y brillo del sol en el mar**: derivados del color de la textura de día en el material.
- **Atmósfera, haz de radar y destello**: materiales y compositor propios.

Crédito en pantalla: «Datos: misión NISAR (NASA-ISRO)».
