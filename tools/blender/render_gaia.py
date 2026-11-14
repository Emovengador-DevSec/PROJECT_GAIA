"""PROJECT GAIA · render por lotes de la portada (sin interfaz).

    blender -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- h [inicio fin]
    blender -b art/blender/gaia.blend -P tools/blender/render_gaia.py -- v [inicio fin]

h = 2560x1440 con Cam_Cine; v = 1080x1920 con Cam_Cine_V.
Escribe PNG sin pérdidas en art/render/v4/<formato>/.
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
if fmt not in ("h", "v"):
    raise ValueError("El formato debe ser h o v")
out = os.path.join(repo, "art", "render", "v4", fmt)
os.makedirs(out, exist_ok=True)

r = scene.render
if fmt == "v":
    r.resolution_x, r.resolution_y = 1080, 1920
    scene.camera = bpy.data.objects["Cam_Cine_V"]
else:
    r.resolution_x, r.resolution_y = 2560, 1440
    scene.camera = bpy.data.objects["Cam_Cine"]
r.resolution_percentage = 100
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.image_settings.compression = 15
scene.eevee.taa_render_samples = 64
scene.frame_start, scene.frame_end = start, end
r.filepath = os.path.join(out, "gaia_")
bpy.ops.render.render(animation=True)
print(f"GAIA_RENDER_DONE {fmt} {start}-{end}")
