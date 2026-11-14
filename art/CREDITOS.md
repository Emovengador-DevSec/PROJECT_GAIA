# Créditos de recursos · portada PROJECT GAIA

Las texturas viven en `art/textures/` (fuera de Git; se vuelven a descargar de la fuente).
Todo es de dominio público de la NASA. No se usa el logotipo ni la insignia de la NASA.

| Recurso | Archivo local | Fuente | Licencia | Tamaño |
|---|---|---|---|---|
| Tierra de día (Blue Marble Next Generation con relieve, dic. 2004, 21600×10800) | `earth_day_topo_21600.jpg` (original) → `earth_day_16k.jpg` (16384×8192, derivado para la portada) | NASA Visible Earth — `assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-topography/december/world.topo.200412.3x21600x10800.jpg` | Dominio público (NASA) | 24,5 MB → 16,0 MB |
| Tierra de noche (Black Marble 2016, 3 km, 13500×6750) | `earth_night_3km.jpg` | NASA Earth Observatory, imagen 144898 — `.../imagerecords/144000/144898/BlackMarble_2016_3km.jpg` | Dominio público (NASA) | 8,1 MB |
| Mapa estelar (Deep Star Maps 2020, 4K EXR) | `starmap_2020_4k.exr` | NASA SVS 4851 — `svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/starmap_2020_4k.exr` | Dominio público (NASA/GSFC SVS) | 36 MB |
| Astronauta anterior (ya no se usa en la escena) | `art/models/nasa_astronaut/Astronaut.glb` | NASA 3D Resources · `3D Models/Astronaut/` | Dominio público (NASA) | 0,76 MB |

## Hecho en el proyecto (sin recursos externos)

Los dos modelos EMU de la antigua portada v3 se retiraron de la carpeta porque la escena vigente no los utiliza (5,99 MB liberados). Su fuente original es NASA 3D Resources, `3D Models/Extravehicular Mobility Unit/`.
- **NISAR**: modelado a mano en `tools/blender/build_gaia_scene.py` con proporciones reales (reflector de 12 m, brazo de 9 m). NASA 3D Resources no tiene modelo de NISAR.
- **Nubes**: procedurales (ruido). El mapa de nubes de Blue Marble 2002 solo está en `eoimages.gsfc.nasa.gov`, que no responde desde esta red.
- **Máscara de océano y brillo del sol en el mar**: derivados del color de la textura de día en el material.
- La atmósfera, los pulsos del haz ilustrativo y el destello solar usan materiales y composición propios.
- **Rocas y meteoros**: modelados y animados en `tools/blender/build_gaia_scene.py` y `animate_gaia.py`.
- **Estrellas puntuales**: capa procedural sobre el mapa estelar de la NASA, para que se vean nítidas a 1440p.
- **Sonido ambiente** (`apps/web/public/media/gaia-ambient.ogg` y `.m4a`): sintetizado con ffmpeg en `tools/audio/make_gaia_ambient.sh`. Original, sin muestras de terceros.

El control «Créditos de la escena» de la portada identifica la escena ilustrativa, las imágenes de NASA Blue Marble y Black Marble y los datos de NISAR (NASA–ISRO).

En el globo de GAIA Alerta, `apps/web/public/globe/` contiene derivados de Blue Marble y Black Marble de NASA, el mosaico óptico histórico de Ayacucho [Landsat WELD de NASA GIBS](https://gibs.earthdata.nasa.gov/), y los límites y localidades con sus licencias en `geography-sources.json`.

El relieve local de Ayacucho proviene de Terrain Tiles de Mapzen. El recorte conserva alturas en metros y sus metadatos están en `ayacucho-terrain.json`. [Registro del conjunto de elevación](https://registry.opendata.aws/terrain-tiles/) · [Atribuciones de sus fuentes](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)
