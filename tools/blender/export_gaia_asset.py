"""PROJECT GAIA · exporta un recurso de la escena a .glb con compresión Draco.

Uso dentro de Blender (con art/blender/gaia.blend abierto):
    exec(open(r"<repo>/tools/blender/export_gaia_asset.py", encoding="utf-8").read())
    export_asset("NISAR", "nisar.glb")

Exporta la jerarquía bajo el vacío raíz, centrada en el origen y sin animación,
a apps/web/public/models/. Los materiales procedurales (celdas del panel solar,
malla del reflector) se exportan solo con su color base: glTF no admite nodos.
"""
import os

import bpy
from mathutils import Matrix

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(
    bpy.data.filepath)))) if bpy.data.filepath else r"C:\Users\USUARIO\Desktop\GAIA"
OUT_DIR = os.path.join(REPO, "apps", "web", "public", "models")

# color base de respaldo para materiales con nodos procedurales
FALLBACK = {
    "M_PanelSolar": (0.014, 0.026, 0.105, 1.0),
    "M_MallaReflector": (0.95, 0.68, 0.22, 1.0),
}


def _descendants(ob):
    out = [ob]
    for ch in ob.children:
        out.extend(_descendants(ch))
    return out


def export_asset(root_name, filename):
    root = bpy.data.objects[root_name]
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    saved = root.matrix_world.copy()
    relinked = []
    for name, color in FALLBACK.items():
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        pr = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        sock = pr.inputs["Base Color"]
        for link in list(sock.links):
            relinked.append((mat, link.from_socket, sock))
            mat.node_tree.links.remove(link)
        sock.default_value = color
    try:
        root.matrix_world = Matrix.Identity(4)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action="DESELECT")
        for ob in _descendants(root):
            ob.hide_viewport = False
            ob.select_set(True)
        bpy.context.view_layer.objects.active = root
        bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB", use_selection=True, export_apply=True,
            export_animations=False, export_yup=True,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6,
        )
    finally:
        for mat, src, dst in relinked:
            mat.node_tree.links.new(src, dst)
        root.matrix_world = saved
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    size = os.path.getsize(path)
    print(f"{filename}: {size / 1e6:.2f} MB")
    return path
