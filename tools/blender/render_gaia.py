"""PROJECT GAIA · render por lotes de la portada (sin interfaz).

    blender -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- h [inicio fin]
    blender -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- v [inicio fin]

h = 1920x1080 con Cam_Cine; v = 1080x1920 con Cam_Cine_V (sin astronauta: en vertical
tapa Sudamérica). Escribe JPG numerados en art/render/<formato>/.
"""
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
fmt = args[0]
scene = bpy.context.scene
start = int(args[1]) if len(args) > 1 else scene.frame_start
end = int(args[2]) if len(args) > 2 else scene.frame_end

repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
out = os.path.join(repo, "art", "render", fmt)
os.makedirs(out, exist_ok=True)

r = scene.render
if fmt == "v":
    r.resolution_x, r.resolution_y = 1080, 1920
    scene.camera = bpy.data.objects["Cam_Cine_V"]
    bpy.data.collections["Astronauta"].hide_render = True
else:
    r.resolution_x, r.resolution_y = 1920, 1080
    scene.camera = bpy.data.objects["Cam_Cine"]
r.resolution_percentage = 100
r.image_settings.file_format = "JPEG"
r.image_settings.quality = 95
scene.eevee.taa_render_samples = 48
scene.frame_start, scene.frame_end = start, end
r.filepath = os.path.join(out, "gaia_")
bpy.ops.render.render(animation=True)
print(f"GAIA_RENDER_DONE {fmt} {start}-{end}")
