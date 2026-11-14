"""PROJECT GAIA · construye la escena de portada en Blender (dirección "Amanecer orbital").

Uso dentro de Blender (o vía MCP):
    exec(open(r"<repo>/tools/blender/build_gaia_scene.py", encoding="utf-8").read())
    build()            # reconstruye toda la escena y la deja en la composición de portada
    render_still(r"<ruta>.png")

Unidades: radio terrestre = 10. El satélite, situado cerca de la cámara, usa una escala cinematográfica.
"""
import math
import os
import subprocess

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

REPO = r"C:\Users\USUARIO\Desktop\GAIA"
TEX = os.path.join(REPO, "art", "textures")
R = 10.0  # radio de la Tierra en unidades de escena

# --- Geometría del plano A: el sol asoma por el limbo superior izquierdo ---------------
CAM_A_POS = Vector((0.0, -24.0, 0.0))
CAM_A_TARGET = Vector((-8.5, 0.0, 3.0))
_AXIS = Vector((0, 1, 0))                       # cámara A -> centro de la Tierra
_LIMB = Vector((-0.8, 0.0, 0.6)).normalized()   # hacia el limbo superior izquierdo
_SUN_ANGLE = math.radians(25.1)                # limbo geométrico: 24.6°
SUN_DIR = (math.cos(_SUN_ANGLE) * _AXIS + math.sin(_SUN_ANGLE) * _LIMB).normalized()
# Truco de cine: el disco del sol se ve en el limbo (SUN_DIR), pero la Tierra se ilumina
# desde un ángulo más abierto para que se vea una media luna ancha con color de día.
EARTH_SUN_DIR = Vector((-0.72, -0.38, 0.45)).normalized()

PERU = (-9.2, -75.0)  # lat, lon


# ---------------------------------------------------------------- utilidades de nodos
def _sock(sockets, ident):
    for s in sockets:
        if s.identifier == ident or s.name == ident:
            return s
    raise KeyError(f"{ident} not in {[s.identifier for s in sockets]}")


def _node(nt, kind, loc=(0, 0), **props):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def _link(nt, a, b):
    nt.links.new(a, b)


def _new_material(name, blended=False):
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputMaterial", (900, 0))
    if blended:
        try:
            mat.surface_render_method = "BLENDED"
        except (AttributeError, TypeError):
            mat.blend_method = "BLEND"
    return mat, nt, out


def _image(name):
    path = os.path.join(TEX, name)
    return bpy.data.images.load(path, check_existing=True)


def _sun_facing(nt, lo, hi, loc=(-600, -400)):
    """0..1 según el coseno entre la normal y la dirección al sol, remapeado [lo, hi]."""
    geo = _node(nt, "ShaderNodeNewGeometry", loc)
    dot = _node(nt, "ShaderNodeVectorMath", (loc[0] + 180, loc[1]), operation="DOT_PRODUCT")
    dot.inputs[1].default_value = EARTH_SUN_DIR
    _link(nt, geo.outputs["Normal"], dot.inputs[0])
    mr = _node(nt, "ShaderNodeMapRange", (loc[0] + 360, loc[1]))
    mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = lo
    mr.inputs["From Max"].default_value = hi
    _link(nt, dot.outputs["Value"], mr.inputs["Value"])
    return mr.outputs["Result"]


def _principled(nt, loc=(500, 0), **vals):
    p = _node(nt, "ShaderNodeBsdfPrincipled", loc)
    for k, v in vals.items():
        _sock(p.inputs, k).default_value = v
    return p


def _simple_mat(name, color, metallic=0.0, rough=0.5, emission=None, strength=0.0):
    mat, nt, out = _new_material(name)
    vals = {"Base Color": (*color, 1), "Metallic": metallic, "Roughness": rough}
    if emission:
        vals["Emission Color"] = (*emission, 1)
        vals["Emission Strength"] = strength
    p = _principled(nt, **vals)
    _link(nt, p.outputs[0], out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------- mallas
def _add(obj_name, mesh_fn, coll, **kw):
    mesh_fn(**kw)
    ob = bpy.context.active_object
    ob.name = obj_name
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    return ob


def _smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True


def _collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def _sphere(name, radius, coll, seg=192, rings=96):
    ob = _add(name, bpy.ops.mesh.primitive_uv_sphere_add, coll,
              segments=seg, ring_count=rings, radius=radius, location=(0, 0, 0))
    _smooth(ob)
    return ob


def _uv_lon_offset(ob):
    """Devuelve el ángulo local (rad) al que cae u=0.5 (lon 0°) en la esfera UV."""
    me = ob.data
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if abs(co.z) < 0.3 * R and 0.3 < uv[li].uv.x < 0.7:
                az = math.atan2(co.y, co.x)
                return az - (uv[li].uv.x - 0.5) * 2 * math.pi
    return 0.0


def latlon_local(lat, lon, az0):
    la, lo = math.radians(lat), math.radians(lon) + az0
    return Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))


def orient_earth(lat, lon, toward, north_hint, tilt_deg=0.0):
    """Gira la Tierra para que (lat, lon) apunte a `toward` con el norte hacia `north_hint`."""
    earth = bpy.data.objects["Tierra"]
    az0 = earth["az0"]
    p = latlon_local(lat, lon, az0)
    w = toward.normalized()
    q1 = p.rotation_difference(w)
    north = q1 @ Vector((0, 0, 1))
    n_proj = (north - north.dot(w) * w).normalized()
    h_proj = (north_hint - north_hint.dot(w) * w).normalized()
    ang = math.atan2(w.dot(n_proj.cross(h_proj)), n_proj.dot(h_proj))
    q = Quaternion(w, ang + math.radians(tilt_deg)) @ q1
    earth.rotation_mode = "QUATERNION"
    earth.rotation_quaternion = q
    return q


# ---------------------------------------------------------------------------- Tierra
def _add_const(nt, sock, value, loc=(0, 0)):
    n = _node(nt, "ShaderNodeMath", loc, operation="ADD")
    n.inputs[1].default_value = value
    _link(nt, sock, n.inputs[0])
    return n.outputs[0]


def _mul(nt, a, b, loc=(0, 0)):
    n = _node(nt, "ShaderNodeMath", loc, operation="MULTIPLY")
    for i, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            _link(nt, v, n.inputs[i])
    return n.outputs[0]


def _additive(nt, out, color_sock, strength_sock, loc=(300, 0)):
    """Emisión sumada sobre lo que hay detrás (no depende del orden de dibujo)."""
    em = _node(nt, "ShaderNodeEmission", loc)
    if isinstance(color_sock, tuple):
        em.inputs["Color"].default_value = color_sock
    else:
        _link(nt, color_sock, em.inputs["Color"])
    _link(nt, strength_sock, em.inputs["Strength"])
    tr = _node(nt, "ShaderNodeBsdfTransparent", (loc[0], loc[1] - 180))
    add = _node(nt, "ShaderNodeAddShader", (loc[0] + 260, loc[1] - 80))
    _link(nt, em.outputs[0], add.inputs[0])
    _link(nt, tr.outputs[0], add.inputs[1])
    _link(nt, add.outputs[0], out.inputs["Surface"])


def build_earth():
    coll = _collection("Tierra")
    earth = _sphere("Tierra", R, coll)
    earth["az0"] = _uv_lon_offset(earth)
    earth.visible_shadow = False   # las sombras de esferas tan grandes multiplican x70 el render

    mat, nt, out = _new_material("M_Tierra")
    # Un solo derivado del Blue Marble original mantiene el detalle costero en 1440p.
    day_file = "earth_day_16k.jpg"
    if not os.path.isfile(os.path.join(TEX, day_file)):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i",
                        os.path.join(TEX, "earth_day_topo_21600.jpg"), "-vf",
                        "scale=16384:8192:flags=lanczos", "-frames:v", "1", "-q:v", "2",
                        "-pix_fmt", "yuvj444p", os.path.join(TEX, day_file)], check=True)
    day = _node(nt, "ShaderNodeTexImage", (-900, 300), image=_image(day_file))
    night = _node(nt, "ShaderNodeTexImage", (-900, -200), image=_image("earth_night_3km.jpg"))
    # máscara de océano: el azul domina sobre rojo y verde (razón, no diferencia)
    sep = _node(nt, "ShaderNodeSeparateColor", (-600, 600))
    _link(nt, day.outputs["Color"], sep.inputs[0])
    mx = _node(nt, "ShaderNodeMath", (-420, 700), operation="MAXIMUM")
    _link(nt, sep.outputs[0], mx.inputs[0])
    _link(nt, sep.outputs[1], mx.inputs[1])
    sub = _node(nt, "ShaderNodeMath", (-420, 550), operation="SUBTRACT")
    _link(nt, sep.outputs[2], sub.inputs[0])
    _link(nt, mx.outputs[0], sub.inputs[1])
    den = _add_const(nt, sep.outputs[2], 0.004, (-420, 400))
    ratio = _node(nt, "ShaderNodeMath", (-250, 550), operation="DIVIDE")
    _link(nt, sub.outputs[0], ratio.inputs[0])
    _link(nt, den, ratio.inputs[1])
    ocean = _node(nt, "ShaderNodeMapRange", (-80, 550))
    ocean.inputs["From Min"].default_value = 0.08
    ocean.inputs["From Max"].default_value = 0.3
    _link(nt, ratio.outputs[0], ocean.inputs["Value"])
    rough = _node(nt, "ShaderNodeMapRange", (100, 550))
    rough.inputs["To Min"].default_value = 0.85
    rough.inputs["To Max"].default_value = 0.52
    _link(nt, ocean.outputs["Result"], rough.inputs["Value"])
    # día: tierra más viva y mar azul profundo
    hsv = _node(nt, "ShaderNodeHueSaturation", (-600, 300))
    hsv.inputs["Saturation"].default_value = 1.12
    hsv.inputs["Value"].default_value = 1.40
    _link(nt, day.outputs["Color"], hsv.inputs["Color"])
    sea = _node(nt, "ShaderNodeMix", (100, 300), data_type="RGBA")
    _sock(sea.inputs, "B_Color").default_value = (0.008, 0.09, 0.31, 1)
    _link(nt, _mul(nt, ocean.outputs["Result"], 0.8, (-80, 250)), _sock(sea.inputs, "Factor_Float"))
    _link(nt, hsv.outputs["Color"], _sock(sea.inputs, "A_Color"))
    # noche: solo las luces (umbral), no el gris del terreno de Black Marble
    bw = _node(nt, "ShaderNodeRGBToBW", (-600, -200))
    _link(nt, night.outputs["Color"], bw.inputs[0])
    lights = _node(nt, "ShaderNodeMapRange", (-420, -200))
    lights.inputs["From Min"].default_value = 0.14
    lights.inputs["From Max"].default_value = 0.75
    _link(nt, bw.outputs[0], lights.inputs["Value"])
    night_f = _sun_facing(nt, 0.1, -0.14, (-900, -550))
    estr = _mul(nt, _mul(nt, lights.outputs["Result"], night_f, (-200, -300)), 26.0, (-20, -300))
    tint = _node(nt, "ShaderNodeMix", (-420, -420), data_type="RGBA", blend_type="MULTIPLY")
    _sock(tint.inputs, "Factor_Float").default_value = 1.0
    _sock(tint.inputs, "B_Color").default_value = (1.0, 0.62, 0.3, 1)
    _link(nt, night.outputs["Color"], _sock(tint.inputs, "A_Color"))
    p = _principled(nt, (500, 100))
    _sock(p.inputs, "Specular IOR Level").default_value = 0.11
    _link(nt, _sock(sea.outputs, "Result_Color"), _sock(p.inputs, "Base Color"))
    _link(nt, rough.outputs["Result"], _sock(p.inputs, "Roughness"))
    # emisión = luces de ciudades + un resplandor lunar muy tenue para que se lea el relieve
    city = _node(nt, "ShaderNodeVectorMath", (150, -350), operation="SCALE")
    _link(nt, _sock(tint.outputs, "Result_Color"), city.inputs[0])
    _link(nt, estr, city.inputs["Scale"])
    moon = _node(nt, "ShaderNodeVectorMath", (150, -550), operation="SCALE")
    _link(nt, _sock(sea.outputs, "Result_Color"), moon.inputs[0])
    _link(nt, _mul(nt, night_f, 0.05, (-20, -550)), moon.inputs["Scale"])
    emis = _node(nt, "ShaderNodeVectorMath", (320, -450), operation="ADD")
    _link(nt, city.outputs["Vector"], emis.inputs[0])
    _link(nt, moon.outputs["Vector"], emis.inputs[1])
    _link(nt, emis.outputs["Vector"], _sock(p.inputs, "Emission Color"))
    _sock(p.inputs, "Emission Strength").default_value = 1.0
    _link(nt, p.outputs[0], out.inputs["Surface"])
    earth.data.materials.append(mat)

    # --- nubes procedurales (dos escalas de ruido deformadas) ---
    clouds = _sphere("Nubes", R * 1.005, coll)
    clouds.parent = earth
    clouds.visible_shadow = False
    mat, nt, out = _new_material("M_Nubes", blended=True)
    mat.use_backface_culling = True
    tc = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    warp = _node(nt, "ShaderNodeTexNoise", (-700, -200))
    warp.inputs["Scale"].default_value = 0.22
    warp.inputs["Detail"].default_value = 4
    _link(nt, tc.outputs["Object"], warp.inputs["Vector"])
    mixv = _node(nt, "ShaderNodeMix", (-500, 0), data_type="VECTOR")
    _sock(mixv.inputs, "Factor_Float").default_value = 0.22
    _link(nt, tc.outputs["Object"], _sock(mixv.inputs, "A_Vector"))
    _link(nt, warp.outputs["Color"], _sock(mixv.inputs, "B_Vector"))
    big = _node(nt, "ShaderNodeTexNoise", (-300, 150))
    big.inputs["Scale"].default_value = 0.33
    big.inputs["Detail"].default_value = 15
    big.inputs["Roughness"].default_value = 0.64
    _link(nt, _sock(mixv.outputs, "Result_Vector"), big.inputs["Vector"])
    small = _node(nt, "ShaderNodeTexNoise", (-300, -150))
    small.inputs["Scale"].default_value = 1.7
    small.inputs["Detail"].default_value = 12
    _link(nt, _sock(mixv.outputs, "Result_Vector"), small.inputs["Vector"])
    alpha = _node(nt, "ShaderNodeMapRange", (100, 0))
    alpha.interpolation_type = "SMOOTHSTEP"
    alpha.inputs["From Min"].default_value = 0.27
    alpha.inputs["From Max"].default_value = 0.44
    alpha.inputs["To Max"].default_value = 0.96
    _link(nt, _mul(nt, big.outputs["Fac"], small.outputs["Fac"], (-100, 0)), alpha.inputs["Value"])
    p = _principled(nt, (500, 0), **{"Base Color": (1, 1, 1, 1), "Roughness": 0.9})
    _sock(p.inputs, "Specular IOR Level").default_value = 0.1
    _link(nt, alpha.outputs["Result"], _sock(p.inputs, "Alpha"))
    _link(nt, p.outputs[0], out.inputs["Surface"])
    clouds.data.materials.append(mat)

    # --- atmósfera: velo azul sobre el disco + halo exterior con caída suave ---
    def atmo(name, radius, inner, strength, glow_night):
        ob = _sphere(name, radius, coll, 128, 64)
        mat, nt, out = _new_material("M_" + name, blended=True)
        mat.use_backface_culling = True
        g = _node(nt, "ShaderNodeNewGeometry", (-1100, 400))
        dt = _node(nt, "ShaderNodeVectorMath", (-950, 400), operation="DOT_PRODUCT")
        _link(nt, g.outputs["Incoming"], dt.inputs[0])
        _link(nt, g.outputs["Normal"], dt.inputs[1])
        ab = _node(nt, "ShaderNodeMath", (-800, 400), operation="ABSOLUTE")
        _link(nt, dt.outputs["Value"], ab.inputs[0])      # 1 = de frente, 0 = borde de la esfera
        shape = _node(nt, "ShaderNodeMapRange", (-600, 400))
        shape.interpolation_type = "SMOOTHERSTEP"
        if inner:   # bruma que crece hacia el limbo, sin línea dura en el borde
            shape.inputs["From Min"].default_value = 0.74
            shape.inputs["From Max"].default_value = 1.0
            power = 1.7
        else:       # halo: máximo en el limbo del planeta y cero en el borde del halo
            limb = math.sqrt(1.0 - (R / radius) ** 2)
            shape.inputs["From Min"].default_value = 0.0
            shape.inputs["From Max"].default_value = limb
            power = 2.6
            inside = _node(nt, "ShaderNodeMapRange", (-600, 620))
            inside.interpolation_type = "SMOOTHSTEP"
            inside.inputs["From Min"].default_value = limb
            inside.inputs["From Max"].default_value = limb + 0.055
            inside.inputs["To Min"].default_value = 1.0
            inside.inputs["To Max"].default_value = 0.0
            _link(nt, ab.outputs[0], inside.inputs["Value"])
        if inner:
            inv = _node(nt, "ShaderNodeMath", (-700, 250), operation="SUBTRACT")
            inv.inputs[0].default_value = 1.0
            _link(nt, ab.outputs[0], inv.inputs[1])
            _link(nt, inv.outputs[0], shape.inputs["Value"])
        else:
            _link(nt, ab.outputs[0], shape.inputs["Value"])
        pw = _node(nt, "ShaderNodeMath", (-420, 400), operation="POWER")
        pw.inputs[1].default_value = power if inner else 3.0
        _link(nt, shape.outputs["Result"], pw.inputs[0])
        f = pw.outputs[0] if inner else _mul(nt, pw.outputs[0], inside.outputs["Result"], (-250, 480))
        lit = _sun_facing(nt, -0.24, 0.32, (-1100, -100))
        twilight = _sun_facing(nt, 0.12, -0.1, (-1100, -380))
        col = _node(nt, "ShaderNodeMix", (-200, -250), data_type="RGBA")
        _sock(col.inputs, "A_Color").default_value = (0.07, 0.3, 1.0, 1)
        _sock(col.inputs, "B_Color").default_value = (0.48, 0.70, 0.95, 1)
        _link(nt, _mul(nt, twilight, 0.52, (-420, -380)), _sock(col.inputs, "Factor_Float"))
        s = _mul(nt, _mul(nt, f, _add_const(nt, lit, glow_night, (-420, -100)), (-60, 200)),
                 strength, (120, 200))
        _additive(nt, out, _sock(col.outputs, "Result_Color"), s, (320, 100))
        ob.data.materials.append(mat)
        ob.visible_shadow = False
        return ob

    atmo("Atmosfera", R * 1.004, True, 0.22, 0.015)
    atmo("Halo", R * 1.018, False, 0.7, 0.01)
    return earth


# ------------------------------------------------------------------- cielo y sol
def build_sky():
    scene = bpy.context.scene
    world = bpy.data.worlds.get("Espacio") or bpy.data.worlds.new("Espacio")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputWorld", (900, 0))
    tc = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    # 1) mapa estelar real (NASA Deep Star Maps): Vía Láctea y color
    mp = _node(nt, "ShaderNodeMapping", (-700, 0))
    mp.inputs["Rotation"].default_value = (math.radians(62), 0, math.radians(200))
    env = _node(nt, "ShaderNodeTexEnvironment", (-480, 0), image=_image("starmap_2020_4k.exr"))
    _link(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    _link(nt, mp.outputs["Vector"], env.inputs["Vector"])
    gm = _node(nt, "ShaderNodeGamma", (-250, 0))
    gm.inputs["Gamma"].default_value = 1.7
    _link(nt, env.outputs["Color"], gm.inputs["Color"])
    bg = _node(nt, "ShaderNodeBackground", (0, 0))
    bg.inputs["Strength"].default_value = 1.3
    _link(nt, gm.outputs["Color"], bg.inputs["Color"])
    # 2) estrellas puntuales nítidas (el mapa 4K se ve blando a 1440p)
    vor = _node(nt, "ShaderNodeTexVoronoi", (-480, -350))
    vor.inputs["Scale"].default_value = 210.0
    _link(nt, tc.outputs["Generated"], vor.inputs["Vector"])
    dot = _node(nt, "ShaderNodeMapRange", (-250, -350))
    dot.inputs["From Min"].default_value = 0.0
    dot.inputs["From Max"].default_value = 0.045
    dot.inputs["To Min"].default_value = 1.0
    dot.inputs["To Max"].default_value = 0.0
    _link(nt, vor.outputs["Distance"], dot.inputs["Value"])
    sepc = _node(nt, "ShaderNodeSeparateColor", (-250, -600))
    _link(nt, vor.outputs["Color"], sepc.inputs[0])
    rare = _node(nt, "ShaderNodeMath", (-60, -600), operation="POWER")   # pocas brillantes
    rare.inputs[1].default_value = 7.0
    _link(nt, sepc.outputs[0], rare.inputs[0])
    sq = _node(nt, "ShaderNodeMath", (-60, -350), operation="POWER")
    sq.inputs[1].default_value = 2.0
    _link(nt, dot.outputs["Result"], sq.inputs[0])
    pts = _node(nt, "ShaderNodeBackground", (300, -350))
    tintc = _node(nt, "ShaderNodeMix", (100, -700), data_type="RGBA")
    _sock(tintc.inputs, "A_Color").default_value = (0.75, 0.85, 1.0, 1)
    _sock(tintc.inputs, "B_Color").default_value = (1.0, 0.86, 0.7, 1)
    _link(nt, sepc.outputs[1], _sock(tintc.inputs, "Factor_Float"))
    _link(nt, _sock(tintc.outputs, "Result_Color"), pts.inputs["Color"])
    _link(nt, _mul(nt, _mul(nt, sq.outputs[0], rare.outputs[0], (100, -450)), 9.0, (200, -500)),
          pts.inputs["Strength"])
    both = _node(nt, "ShaderNodeAddShader", (500, -100))
    _link(nt, bg.outputs[0], both.inputs[0])
    _link(nt, pts.outputs[0], both.inputs[1])
    # las estrellas solo se ven desde la cámara; no iluminan la escena
    lp = _node(nt, "ShaderNodeLightPath", (500, 250))
    black = _node(nt, "ShaderNodeBackground", (500, -300))
    black.inputs["Color"].default_value = (0, 0, 0, 1)
    mix = _node(nt, "ShaderNodeMixShader", (700, 0))
    _link(nt, lp.outputs["Is Camera Ray"], mix.inputs[0])
    _link(nt, black.outputs[0], mix.inputs[1])
    _link(nt, both.outputs[0], mix.inputs[2])
    _link(nt, mix.outputs[0], out.inputs["Surface"])

    coll = _collection("Luz")
    light = bpy.data.lights.new("Sol", "SUN")
    light.energy = 7.5
    light.angle = math.radians(0.6)
    light.color = (0.98, 0.99, 1.0)
    light.use_shadow = False
    sun = bpy.data.objects.new("Sol", light)
    coll.objects.link(sun)
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = EARTH_SUN_DIR.to_track_quat("Z", "Y")

    # disco solar visible en el limbo (el destello lo añade el compositor)
    dist = 900.0
    disc = _add("SolDisco", bpy.ops.mesh.primitive_uv_sphere_add, coll,
                segments=48, ring_count=24, radius=dist * math.tan(math.radians(0.15)),
                location=CAM_A_POS + SUN_DIR * dist)
    mat, nt, out = _new_material("M_Sol")
    em = _node(nt, "ShaderNodeEmission", (300, 0))
    em.inputs["Color"].default_value = (0.98, 0.99, 1.0, 1)
    em.inputs["Strength"].default_value = 1800.0
    _link(nt, em.outputs[0], out.inputs["Surface"])
    disc.data.materials.append(mat)
    disc.visible_shadow = False
    # El pase solar limita la difracción al Sol y conserva la nitidez del planeta.
    aovs = bpy.context.view_layer.aovs
    sun_pass = aovs.get("GAIA_Sun") or aovs.add()
    sun_pass.name, sun_pass.type = "GAIA_Sun", "COLOR"
    aov = _node(nt, "ShaderNodeOutputAOV", (300, -220))
    aov.aov_name = sun_pass.name
    aov.inputs["Color"].default_value = (1800.0, 1780.0, 1740.0, 1.0)


def _foil_mat():
    """Manta térmica dorada (MLI) con arrugas."""
    mat, nt, out = _new_material("M_MLI_Oro")
    tc = _node(nt, "ShaderNodeTexCoord", (-700, 0))
    n1 = _node(nt, "ShaderNodeTexVoronoi", (-450, 0))
    n1.inputs["Scale"].default_value = 9.0
    _link(nt, tc.outputs["Object"], n1.inputs["Vector"])
    n2 = _node(nt, "ShaderNodeTexNoise", (-450, -300))
    n2.inputs["Scale"].default_value = 26.0
    n2.inputs["Detail"].default_value = 6
    _link(nt, tc.outputs["Object"], n2.inputs["Vector"])
    hsum = _node(nt, "ShaderNodeMath", (-200, -100), operation="ADD")
    _link(nt, n1.outputs["Distance"], hsum.inputs[0])
    _link(nt, _mul(nt, n2.outputs["Fac"], 0.5, (-300, -300)), hsum.inputs[1])
    bump = _node(nt, "ShaderNodeBump", (50, -150))
    bump.inputs["Strength"].default_value = 0.55
    bump.inputs["Distance"].default_value = 0.12
    _link(nt, hsum.outputs[0], bump.inputs["Height"])
    rg = _node(nt, "ShaderNodeMapRange", (50, 150))
    rg.inputs["To Min"].default_value = 0.16
    rg.inputs["To Max"].default_value = 0.42
    _link(nt, n2.outputs["Fac"], rg.inputs["Value"])
    p = _principled(nt, (350, 0), **{"Base Color": (1.0, 0.62, 0.16, 1), "Metallic": 1.0})
    _link(nt, rg.outputs["Result"], _sock(p.inputs, "Roughness"))
    _link(nt, bump.outputs["Normal"], _sock(p.inputs, "Normal"))
    _link(nt, p.outputs[0], out.inputs["Surface"])
    return mat


# -------------------------------------------------------------------------- NISAR
def build_nisar():
    """NISAR con proporciones reales en metros: bus, instrumento, brazo de 9 m,
    reflector de malla de 12 m y paneles solares. Padre: 'NISAR' (vacío)."""
    coll = _collection("NISAR")
    root = bpy.data.objects.new("NISAR", None)
    root.empty_display_size = 2
    coll.objects.link(root)

    gold = _foil_mat()
    dark = _simple_mat("M_Estructura", (0.04, 0.04, 0.045), metallic=0.6, rough=0.45)
    white = _simple_mat("M_Radiador", (0.86, 0.86, 0.84), rough=0.5)
    boom_m = _simple_mat("M_Brazo", (0.55, 0.56, 0.58), metallic=0.9, rough=0.3)

    # panel solar con retícula de celdas
    solar, nt, out = _new_material("M_PanelSolar")
    tc = _node(nt, "ShaderNodeTexCoord", (-700, 0))
    br = _node(nt, "ShaderNodeTexBrick", (-450, 0))
    br.offset = 0.0
    br.inputs["Color1"].default_value = (0.008, 0.03, 0.2, 1)
    br.inputs["Color2"].default_value = (0.012, 0.05, 0.3, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.36, 0.4, 1)
    br.inputs["Scale"].default_value = 9.0
    br.inputs["Mortar Size"].default_value = 0.012
    _link(nt, tc.outputs["UV"], br.inputs["Vector"])
    p = _principled(nt, (300, 0), **{"Metallic": 0.85, "Roughness": 0.22})
    _link(nt, br.outputs["Color"], _sock(p.inputs, "Base Color"))
    _link(nt, p.outputs[0], out.inputs["Surface"])

    # malla dorada del reflector: retícula fina semitransparente
    mesh_m, nt, out = _new_material("M_MallaReflector")
    tc = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    alphas = []
    for i, axis in enumerate(("X", "Y")):
        wv = _node(nt, "ShaderNodeTexWave", (-600, 200 - 300 * i), bands_direction=axis)
        wv.inputs["Scale"].default_value = 34.0
        _link(nt, tc.outputs["Object"], wv.inputs["Vector"])
        mr = _node(nt, "ShaderNodeMapRange", (-380, 200 - 300 * i))
        mr.inputs["From Min"].default_value = 0.72
        mr.inputs["From Max"].default_value = 0.9
        _link(nt, wv.outputs["Fac"], mr.inputs["Value"])
        alphas.append(mr.outputs["Result"])
    mx = _node(nt, "ShaderNodeMath", (-150, 50), operation="MAXIMUM")
    _link(nt, alphas[0], mx.inputs[0])
    _link(nt, alphas[1], mx.inputs[1])
    base = _node(nt, "ShaderNodeMath", (40, 50), operation="MAXIMUM")
    base.inputs[1].default_value = 0.2
    _link(nt, mx.outputs[0], base.inputs[0])
    p = _principled(nt, (300, 0), **{"Base Color": (0.95, 0.68, 0.22, 1),
                                     "Metallic": 1.0, "Roughness": 0.3})
    _link(nt, base.outputs[0], _sock(p.inputs, "Alpha"))
    _link(nt, p.outputs[0], out.inputs["Surface"])
    mesh_m.use_backface_culling = False

    def part(name, fn, mat, **kw):
        ob = _add(name, fn, coll, **kw)
        ob.data.materials.append(mat)
        ob.parent = root
        ob.visible_shadow = False   # a escala cinematográfica su sombra taparía continentes
        return ob

    def box(name, size, loc, mat, bevel=0.04):
        ob = part(name, bpy.ops.mesh.primitive_cube_add, mat, size=1, location=loc)
        ob.scale = size
        if bevel:
            m = ob.modifiers.new("Bevel", "BEVEL")
            m.width = bevel
            m.segments = 2
        return ob

    def tube(name, a, b, radius, mat, verts=16):
        a, b = Vector(a), Vector(b)
        ob = part(name, bpy.ops.mesh.primitive_cylinder_add, mat, vertices=verts,
                  radius=radius, depth=(b - a).length, location=(a + b) / 2)
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = (b - a).to_track_quat("Z", "Y")
        _smooth(ob)
        return ob

    # bus (cuerpo principal) y estructura del instrumento radar encima
    box("Bus", (1.9, 1.9, 2.3), (0, 0, 0), gold, 0.06)
    box("Bus_Radiador", (1.5, 0.05, 1.7), (0, -0.98, 0.0), white, 0.0)
    oct_ = part("Instrumento", bpy.ops.mesh.primitive_cylinder_add, gold, vertices=8,
                radius=1.35, depth=1.6, location=(0, 0, 1.95))
    oct_.rotation_euler = (0, 0, math.radians(22.5))
    m = oct_.modifiers.new("Bevel", "BEVEL")
    m.width = 0.05
    box("Electronica_L", (2.0, 1.0, 0.5), (0, 0.2, 2.95), dark, 0.03)
    # alimentadores (banda L y banda S) que iluminan el reflector
    feed = box("Alimentador_L", (2.1, 0.12, 1.5), (0, -1.45, 2.2), white, 0.02)
    feed.rotation_euler = (math.radians(-20), 0, 0)
    feed2 = box("Alimentador_S", (0.9, 0.1, 1.0), (1.3, -1.3, 2.9), white, 0.02)
    feed2.rotation_euler = (math.radians(-20), 0, math.radians(12))
    # antena de alta ganancia y sensores
    dish = part("AntenaHG", bpy.ops.mesh.primitive_cone_add, white, vertices=32,
                radius1=0.0, radius2=0.45, depth=0.22, location=(0.6, 0.6, -1.45))
    dish.rotation_euler = (math.radians(180), 0, 0)
    tube("AntenaHG_Mastil", (0.6, 0.6, -1.15), (0.6, 0.6, -1.4), 0.04, dark)

    # paneles solares: dos alas a cada lado del bus
    for side in (-1, 1):
        tube(f"Yugo_{side}", (side * 0.95, 0, -0.2), (side * 1.7, 0, -0.2), 0.05, dark)
        for k in range(3):
            pan = box(f"Panel_{side}_{k}", (1.75, 0.04, 2.6),
                      (side * (2.62 + 1.8 * k), 0, -0.2), solar, 0.0)
            pan.rotation_euler = (math.radians(18), 0, 0)

    # brazo desplegable de 9 m en dos tramos con codo
    j0 = Vector((0, 0.9, 2.9))
    j1 = Vector((0, 2.2, 7.2))
    j2 = Vector((0, -1.4, 10.6))
    tube("Brazo_1", j0, j1, 0.09, boom_m)
    tube("Brazo_2", j1, j2, 0.09, boom_m)
    for i, j in enumerate((j0, j1, j2)):
        k = part(f"Codo_{i}", bpy.ops.mesh.primitive_uv_sphere_add, dark,
                 segments=16, ring_count=8, radius=0.17, location=j)
        _smooth(k)

    # reflector de malla de 12 m: paraboloide poco profundo + anillo perimetral
    rr, depth = 6.0, 1.15
    me = bpy.data.meshes.new("Reflector")
    bm = bmesh.new()
    rings, segs = 14, 72
    grid = [[bm.verts.new((0, 0, 0))]]
    for i in range(1, rings + 1):
        r = rr * i / rings
        grid.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs),
                                   r * math.sin(2 * math.pi * s / segs),
                                   depth * (r / rr) ** 2)) for s in range(segs)])
    for s in range(segs):
        bm.faces.new((grid[0][0], grid[1][s], grid[1][(s + 1) % segs]))
    for i in range(1, rings):
        for s in range(segs):
            bm.faces.new((grid[i][s], grid[i + 1][s], grid[i + 1][(s + 1) % segs],
                          grid[i][(s + 1) % segs]))
    bm.to_mesh(me)
    bm.free()
    refl = bpy.data.objects.new("Reflector", me)
    coll.objects.link(refl)
    refl.data.materials.append(mesh_m)
    refl.visible_shadow = False
    _smooth(refl)
    refl_root = bpy.data.objects.new("Reflector_Raiz", None)
    coll.objects.link(refl_root)
    refl_root.parent = root
    refl.parent = refl_root
    for kk in range(24):                    # costillas radiales bajo la malla
        ang = 2 * math.pi * kk / 24
        cx, sy = math.cos(ang), math.sin(ang)
        pts = [(rr * q * cx, rr * q * sy, depth * q * q) for q in (0.02, 0.5, 1.0)]
        for seg in range(2):
            rib = tube(f"Costilla_{kk}_{seg}", pts[seg], pts[seg + 1], 0.02, boom_m, verts=6)
            rib.parent = refl_root
    # anillo de celosía (dos aros + montantes)
    for name, z in (("Aro_frontal", depth), ("Aro_trasero", depth + 0.9)):
        t = part(name, bpy.ops.mesh.primitive_torus_add, boom_m, major_radius=rr,
                 minor_radius=0.045, major_segments=96, minor_segments=8, location=(0, 0, z))
        _smooth(t)
        t.parent = refl_root
    for s in range(30):
        a0 = 2 * math.pi * s / 30
        a1 = 2 * math.pi * (s + 0.5) / 30
        a2 = 2 * math.pi * (s + 1) / 30
        pa = (rr * math.cos(a0), rr * math.sin(a0), depth)
        pb = (rr * math.cos(a1), rr * math.sin(a1), depth + 0.9)
        pc = (rr * math.cos(a2), rr * math.sin(a2), depth)
        for nm, (u, v) in (("a", (pa, pb)), ("b", (pb, pc))):
            st = tube(f"Montante_{s}{nm}", u, v, 0.022, boom_m, verts=6)
            st.parent = refl_root
    # el reflector cuelga del extremo del brazo, mirando hacia los alimentadores
    refl_root.location = j2 + Vector((0, -5.6, 1.6))
    refl_root.rotation_euler = (math.radians(150), 0, 0)
    return root




# --------------------------------------------------------------------- haz de radar
SWATH_PATH = [(-4.6, -80.9), (-12.0, -76.7), (-18.1, -70.7)]   # costa del Perú (lat, lon)
SWATH_WIDTH_DEG = 2.3                                            # ≈ 240 km, la franja de NISAR


def swath_latlon(u, across=0.5):
    """Punto de la franja: u de 0 (norte) a 1 (sur); across de 0 (costa) a 1 (interior)."""
    u = max(0.0, min(1.0, u)) * (len(SWATH_PATH) - 1)
    i = min(int(u), len(SWATH_PATH) - 2)
    f = u - i
    (la0, lo0), (la1, lo1) = SWATH_PATH[i], SWATH_PATH[i + 1]
    return la0 + (la1 - la0) * f, lo0 + (lo1 - lo0) * f - 0.25 + SWATH_WIDTH_DEG * across


def _value(nt, label, value, loc):
    n = _node(nt, "ShaderNodeValue", loc)
    n.name = n.label = label
    n.outputs[0].default_value = value
    return n


def build_beam():
    coll = _collection("Haz")
    # --- cono del haz: núcleo suave + frentes de onda que viajan hacia el suelo ---
    mat, nt, out = _new_material("M_Haz", blended=True)
    mat.use_backface_culling = True      # solo la cara frontal: los frentes se ven como arcos
    tc = _node(nt, "ShaderNodeTexCoord", (-1100, 0))
    sep = _node(nt, "ShaderNodeSeparateXYZ", (-900, 0))      # Z: 0 en el suelo, 1 en el satélite
    _link(nt, tc.outputs["Generated"], sep.inputs[0])
    phase = _value(nt, "FASE", 0.0, (-900, -200))
    k = _node(nt, "ShaderNodeMath", (-700, -100), operation="MULTIPLY_ADD")
    k.inputs[1].default_value = 7.0
    _link(nt, sep.outputs["Z"], k.inputs[0])
    _link(nt, phase.outputs[0], k.inputs[2])
    wave = _node(nt, "ShaderNodeMath", (-520, -100), operation="COSINE")
    _link(nt, _mul(nt, k.outputs[0], math.tau, (-620, -220)), wave.inputs[0])
    ring = _node(nt, "ShaderNodeMapRange", (-340, -100))
    ring.interpolation_type = "SMOOTHSTEP"
    ring.inputs["From Min"].default_value = -0.2
    ring.inputs["From Max"].default_value = 1.0
    _link(nt, wave.outputs[0], ring.inputs["Value"])
    ring2 = _node(nt, "ShaderNodeMath", (-160, -100), operation="POWER")
    ring2.inputs[1].default_value = 2.4
    _link(nt, ring.outputs["Result"], ring2.inputs[0])
    lw = _node(nt, "ShaderNodeLayerWeight", (-900, 300))
    lw.inputs["Blend"].default_value = 0.5
    core = _node(nt, "ShaderNodeMath", (-700, 300), operation="SUBTRACT")
    core.inputs[0].default_value = 1.0
    _link(nt, lw.outputs["Facing"], core.inputs[1])
    core2 = _node(nt, "ShaderNodeMath", (-520, 300), operation="POWER")
    core2.inputs[1].default_value = 1.6
    _link(nt, core.outputs[0], core2.inputs[0])
    near = _node(nt, "ShaderNodeMapRange", (-520, 100))       # más denso cerca del suelo
    near.inputs["From Min"].default_value = 1.0
    near.inputs["From Max"].default_value = 0.0
    near.inputs["To Min"].default_value = 0.3
    near.inputs["To Max"].default_value = 1.0
    _link(nt, sep.outputs["Z"], near.inputs["Value"])
    glow = _add_const(nt, _mul(nt, ring2.outputs[0], 0.72, (0, -100)), 0.09, (160, -100))
    s = _mul(nt, _mul(nt, _mul(nt, core2.outputs[0], near.outputs["Result"], (-300, 250)), glow, (0, 200)),
             1.25, (160, 200))
    col = _node(nt, "ShaderNodeMix", (160, -300), data_type="RGBA")
    _sock(col.inputs, "A_Color").default_value = (0.05, 0.62, 1.0, 1)
    _sock(col.inputs, "B_Color").default_value = (0.65, 1.0, 0.95, 1)
    _link(nt, ring2.outputs[0], _sock(col.inputs, "Factor_Float"))
    _additive(nt, out, _sock(col.outputs, "Result_Color"), s, (380, 100))
    beam = _add("Haz", bpy.ops.mesh.primitive_cone_add, coll, vertices=96,
                radius1=1.0, radius2=0.015, depth=1.0, end_fill_type="NOTHING")
    beam.data.materials.append(mat)
    beam.visible_shadow = False
    _smooth(beam)

    # --- huella: elipse que late donde el haz toca el suelo ---
    fmat, nt, out = _new_material("M_Huella", blended=True)
    tc = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    mp = _node(nt, "ShaderNodeMapping", (-700, 0))
    mp.inputs["Location"].default_value = (-1, -1, 0)
    mp.inputs["Scale"].default_value = (2, 2, 2)
    _link(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    ln = _node(nt, "ShaderNodeVectorMath", (-500, 0), operation="LENGTH")
    _link(nt, mp.outputs["Vector"], ln.inputs[0])
    edge = _node(nt, "ShaderNodeMapRange", (-300, 100))       # aro fino en el borde
    edge.inputs["From Min"].default_value = 0.8
    edge.inputs["From Max"].default_value = 0.96
    _link(nt, ln.outputs["Value"], edge.inputs["Value"])
    cut = _node(nt, "ShaderNodeMapRange", (-300, -150))
    cut.inputs["From Min"].default_value = 0.97
    cut.inputs["From Max"].default_value = 1.0
    cut.inputs["To Min"].default_value = 1.0
    cut.inputs["To Max"].default_value = 0.0
    _link(nt, ln.outputs["Value"], cut.inputs["Value"])
    s = _mul(nt, _mul(nt, _add_const(nt, _mul(nt, edge.outputs["Result"], 0.9, (-100, 100)), 0.06, (60, 100)),
                      cut.outputs["Result"], (220, 0)), 0.85, (380, 0))
    _additive(nt, out, (0.35, 0.95, 1.0, 1), s, (560, 100))
    foot = _add("Huella", bpy.ops.mesh.primitive_circle_add, coll, vertices=64,
                radius=1.0, fill_type="NGON")
    foot.data.materials.append(fmat)
    foot.visible_shadow = False



def aim_beam(source, ground_dir, radius=0.42, grow=1.0, land=1.0):
    """Tiende el haz desde `source` (mundo) hasta el punto de superficie en `ground_dir`.
    Devuelve (loc, rot, scale) del cono y de la huella para poder hornearlos."""
    n = ground_dir.normalized()
    tip = source + (n * (R * 1.012) - source) * max(grow, 1e-3)
    axis = tip - source
    east = Vector((0, 0, 1)).cross(n)
    east = east.normalized() if east.length > 1e-6 else Vector((1, 0, 0))
    cone = ((source + tip) / 2, axis.to_track_quat("-Z", "Y"),
            Vector((radius * grow, radius * 0.5 * grow, axis.length)))
    foot = (n * (R * 1.013), n.to_track_quat("Z", "Y"),
            Vector((radius * land + 1e-4, radius * 0.5 * land + 1e-4, 1)))
    return cone, foot


# ------------------------------------------------------------------ rocas y meteoros
# (derecha, arriba, adelante) respecto a la cámara final, tamaño, vueltas por bucle
ROCKS = [(-0.9, 0.62, 2.6, 0.05, 1), (0.42, 0.78, 3.8, 0.085, 1), (2.1, 1.35, 7.0, 0.2, 1),
         (2.9, 0.4, 9.0, 0.12, 1), (-0.2, 0.34, 5.2, 0.04, 2), (1.45, -0.1, 3.4, 0.035, 2),
         (0.25, -0.2, 1.3, 0.02, 2)]
# (lat, lon) inicial y final sobre el lado nocturno; ventana dentro del bucle (fase 0..1)
METEORS = [((1.0, -52.0), (-4.0, -45.0), 0.10, 0.17), ((-21.0, -54.0), (-25.5, -47.0), 0.46, 0.52),
           ((-9.0, -41.0), (-13.5, -36.5), 0.76, 0.83)]


def build_debris():
    import random
    rnd = random.Random(7)
    coll = _collection("Rocas")
    mat, nt, out = _new_material("M_Roca")
    tc = _node(nt, "ShaderNodeTexCoord", (-700, 0))
    n1 = _node(nt, "ShaderNodeTexNoise", (-450, 100))
    n1.inputs["Scale"].default_value = 3.0
    n1.inputs["Detail"].default_value = 12
    _link(nt, tc.outputs["Object"], n1.inputs["Vector"])
    n2 = _node(nt, "ShaderNodeTexVoronoi", (-450, -200))
    n2.inputs["Scale"].default_value = 7.0
    _link(nt, tc.outputs["Object"], n2.inputs["Vector"])
    cr = _node(nt, "ShaderNodeMix", (-150, 150), data_type="RGBA")
    _sock(cr.inputs, "A_Color").default_value = (0.05, 0.045, 0.04, 1)
    _sock(cr.inputs, "B_Color").default_value = (0.3, 0.25, 0.2, 1)
    _link(nt, n1.outputs["Fac"], _sock(cr.inputs, "Factor_Float"))
    h = _node(nt, "ShaderNodeMath", (-200, -150), operation="ADD")
    h.inputs[1].default_value = 0.0
    _link(nt, n1.outputs["Fac"], h.inputs[0])
    bump = _node(nt, "ShaderNodeBump", (50, -150))
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.15
    _link(nt, h.outputs[0], bump.inputs["Height"])
    p = _principled(nt, (300, 0), **{"Roughness": 0.92})
    _link(nt, _sock(cr.outputs, "Result_Color"), _sock(p.inputs, "Base Color"))
    _link(nt, bump.outputs["Normal"], _sock(p.inputs, "Normal"))
    _link(nt, p.outputs[0], out.inputs["Surface"])
    textures = []
    for name, kind, size in (("Roca_T1", "CLOUDS", 1.9), ("Roca_T2", "CLOUDS", 0.7)):
        t = bpy.data.textures.get(name) or bpy.data.textures.new(name, kind)
        t.noise_scale = size
        textures.append(t)
    for i, (rx, ry, rz, size, turns) in enumerate(ROCKS):
        ob = _add(f"Roca_{i}", bpy.ops.mesh.primitive_ico_sphere_add, coll, subdivisions=4, radius=1.0)
        ob.scale = (size * rnd.uniform(0.8, 1.35), size * rnd.uniform(0.6, 1.0), size * rnd.uniform(0.55, 0.95))
        for t, strength in zip(textures, (0.7, 0.2)):
            mod = ob.modifiers.new(t.name, "DISPLACE")
            mod.texture = t
            mod.texture_coords = "OBJECT"
            mod.strength = strength
        _smooth(ob)
        ob.data.materials.append(mat)
        ob.visible_shadow = False
        ob["cam_rel"] = (rx, ry, rz)
        ob["turns"] = turns
        ob["axis"] = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()[:]
        ob["phase0"] = rnd.uniform(0, 6.28)


def build_meteors():
    coll = _collection("Meteoros")
    mat, nt, out = _new_material("M_Meteoro", blended=True)
    mat.use_backface_culling = False
    tc = _node(nt, "ShaderNodeTexCoord", (-700, 0))
    sep = _node(nt, "ShaderNodeSeparateXYZ", (-500, 0))       # UV.x: 0 cola, 1 cabeza
    _link(nt, tc.outputs["UV"], sep.inputs[0])
    tail = _node(nt, "ShaderNodeMath", (-300, 100), operation="POWER")
    tail.inputs[1].default_value = 3.0
    _link(nt, sep.outputs["X"], tail.inputs[0])
    vc = _node(nt, "ShaderNodeMath", (-300, -100), operation="MULTIPLY_ADD")
    vc.inputs[1].default_value = 2.0
    vc.inputs[2].default_value = -1.0
    _link(nt, sep.outputs["Y"], vc.inputs[0])
    va = _node(nt, "ShaderNodeMath", (-140, -100), operation="ABSOLUTE")
    _link(nt, vc.outputs[0], va.inputs[0])
    soft = _node(nt, "ShaderNodeMapRange", (20, -100))
    soft.inputs["To Min"].default_value = 1.0
    soft.inputs["To Max"].default_value = 0.0
    _link(nt, va.outputs[0], soft.inputs["Value"])
    col = _node(nt, "ShaderNodeMix", (20, -350), data_type="RGBA")
    _sock(col.inputs, "A_Color").default_value = (0.2, 1.0, 0.65, 1)
    _sock(col.inputs, "B_Color").default_value = (1.0, 0.95, 0.85, 1)
    _link(nt, tail.outputs[0], _sock(col.inputs, "Factor_Float"))
    s = _mul(nt, _mul(nt, tail.outputs[0], soft.outputs["Result"], (200, 0)), 22.0, (360, 0))
    _additive(nt, out, _sock(col.outputs, "Result_Color"), s, (540, 100))
    for i in range(len(METEORS)):
        me = bpy.data.meshes.new(f"Meteoro_{i}")
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        vs = [bm.verts.new(c) for c in ((-1, -0.5, 0), (0, -0.5, 0), (0, 0.5, 0), (-1, 0.5, 0))]
        face = bm.faces.new(vs)
        for loop, uv in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uvl].uv = uv
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"Meteoro_{i}", me)
        coll.objects.link(ob)
        ob.data.materials.append(mat)
        ob.visible_shadow = False
        ob.scale = (0, 0, 0)


# --------------------------------------------------------------------------- cámaras
def _camera(name, lens):
    coll = _collection("Camaras")
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.02
    cam.clip_end = 3000
    ob = bpy.data.objects.new(name, cam)
    coll.objects.link(ob)
    return ob


def _look_at(ob, target, roll_deg=0.0):
    d = (Vector(target) - ob.location).normalized()
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), math.radians(roll_deg))


def _look_dir(ob, forward, up):
    f = forward.normalized()
    r = f.cross(up).normalized()
    u = r.cross(f)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Matrix((r, u, -f)).transposed().to_quaternion()


def _place(ob, cam, right, up, fwd, scale, quat=None):
    """Coloca `ob` en coordenadas de cámara (derecha, arriba, adelante)."""
    m = cam.matrix_world.to_3x3()
    ob.location = cam.location + m @ Vector((right, up, -fwd))
    ob.scale = (scale,) * 3
    if quat is not None:
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = cam.rotation_quaternion @ quat


SAT_CAM_REL = (-2.0, 1.72, 8.4, 0.105)       # derecha, arriba, adelante, escala
FEED_LOCAL = Vector((0, -1.45, 2.2))          # alimentador de banda L, origen del haz


def pose_final():
    """Deja la escena en la composición de portada (último cuadro de la intro)."""
    scene = bpy.context.scene
    objs = bpy.data.objects
    sat, cam = objs["NISAR"], objs["Cam_A"]
    cam.location = CAM_A_POS
    _look_at(cam, CAM_A_TARGET)
    cam.data.dof.use_dof = False
    scene.camera = cam
    bpy.context.view_layer.update()
    orient_earth(-12.0, -66.0, CAM_A_POS + Vector((-6.5, 0, 3.4)), Vector((0.22, 0, 1)))
    r, u, f, s = SAT_CAM_REL
    _place(sat, cam, r, u, f, s,
           Quaternion((1, 0, 0), math.radians(62)) @ Quaternion((0, 0, 1), math.radians(-38)))
    for ob in objs:
        if ob.name.startswith("Roca_"):
            rx, ry, rz = ob["cam_rel"]
            m = cam.matrix_world.to_3x3()
            ob.location = cam.location + m @ Vector((rx, ry, -rz))
            ob.rotation_mode = "QUATERNION"
            ob.rotation_quaternion = Quaternion(Vector(ob["axis"]), ob["phase0"])
    bpy.context.view_layer.update()
    earth = objs["Tierra"]
    n = earth.rotation_quaternion @ latlon_local(*swath_latlon(0.35), earth["az0"])
    src = sat.matrix_world @ FEED_LOCAL
    cone, foot = aim_beam(src, n)
    for ob, (loc, rot, scale) in ((objs["Haz"], cone), (objs["Huella"], foot)):
        ob.location, ob.scale = loc, scale
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = rot
    # luces locales: siguen a la cámara y no llegan a la Tierra
    m = cam.matrix_world.to_3x3()
    for name, target, off in (("Relleno_Sat", sat, (0.6, -1.2, 2.2)),
                              ("Contra_Sat", sat, (-2.5, 1.5, -1.0))):
        lamp = objs[name]
        lamp.location = target.location + m @ Vector(off)
        _look_at(lamp, target.location + m @ Vector((0, 0.5, 0)))
    bpy.context.view_layer.update()


# ----------------------------------------------------------------------------- render
def setup_render(width=2560, height=1440):
    scene = bpy.context.scene
    r = scene.render
    try:
        r.engine = "BLENDER_EEVEE"
    except TypeError:
        r.engine = "BLENDER_EEVEE_NEXT"
    r.resolution_x, r.resolution_y, r.resolution_percentage = width, height, 100
    r.film_transparent = False
    r.filter_size = 0.78
    r.dither_intensity = 1.5                 # evita bandas en los degradados de la atmósfera
    r.image_settings.file_format = "PNG"
    ee = scene.eevee
    for attr, val in (("taa_render_samples", 64), ("use_raytracing", False), ("use_shadows", True)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    vs = scene.view_settings
    try:
        vs.view_transform = "AgX"
    except TypeError:
        pass
    for cand in ("AgX - Punchy", "Punchy", "AgX - High Contrast", "High Contrast"):
        try:
            vs.look = cand
            break
        except TypeError:
            continue
    vs.exposure = 0.0
    vs.gamma = 1.0


def build_compositor():
    """Difracción y corona local del pase solar, compuestas sobre la imagen nítida."""
    scene = bpy.context.scene
    old = bpy.data.node_groups.get("GAIA_Comp")
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new("GAIA_Comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = _node(ng, "CompositorNodeRLayers", (-700, 0))
    bloom = _node(ng, "CompositorNodeGlare", (-450, 0))
    bloom.inputs["Type"].default_value = "Bloom"
    bloom.inputs["Highlights Threshold"].default_value = 2.0
    bloom.inputs["Strength"].default_value = 0.16
    bloom.inputs["Size"].default_value = 0.38
    bloom.inputs["Saturation"].default_value = 1.0
    streak = _node(ng, "CompositorNodeGlare", (-200, 0))
    streak.inputs["Type"].default_value = "Streaks"
    streak.inputs["Highlights Threshold"].default_value = 2.0
    streak.inputs["Strength"].default_value = 0.06
    streak.inputs["Streaks"].default_value = 6
    streak.inputs["Streaks Angle"].default_value = math.radians(18)
    streak.inputs["Iterations"].default_value = 4
    streak.inputs["Fade"].default_value = 0.86
    streak.inputs["Color Modulation"].default_value = 0.0
    streak.inputs["Tint"].default_value = (0.75, 0.88, 1.0, 1.0)
    ng.links.new(rl.outputs["GAIA_Sun"], bloom.inputs["Image"])
    ng.links.new(rl.outputs["GAIA_Sun"], streak.inputs["Image"])
    result = rl.outputs["Image"]
    for i, effect in enumerate((bloom, streak)):
        add = _node(ng, "ShaderNodeMix", (100 + i * 220, 0), data_type="RGBA", blend_type="ADD")
        _sock(add.inputs, "Factor_Float").default_value = 1.0
        ng.links.new(result, _sock(add.inputs, "A_Color"))
        ng.links.new(effect.outputs["Glare"], _sock(add.inputs, "B_Color"))
        result = _sock(add.outputs, "Result_Color")
    out = _node(ng, "NodeGroupOutput", (580, 0))
    ng.links.new(result, out.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True


def render_still(path, percent=100, samples=64):
    scene = bpy.context.scene
    scene.render.resolution_percentage = percent
    scene.eevee.taa_render_samples = samples
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 64
    return path


def _area(name, energy, size, color):
    light = bpy.data.lights.new(name, "AREA")
    light.energy, light.size, light.color = energy, size, color
    light.use_custom_distance = True      # luz local: no debe alcanzar la Tierra
    light.cutoff_distance = 7.0
    ob = bpy.data.objects.new(name, light)
    _collection("Luz").objects.link(ob)
    return ob


def build():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for block in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras):
        for d in list(block):
            if d.users == 0:
                block.remove(d)
    setup_render()
    build_earth()
    build_sky()
    build_nisar()
    build_beam()
    build_debris()
    build_meteors()
    _camera("Cam_A", 35)
    _area("Relleno_Sat", 260, 3.0, (0.45, 0.62, 1.0))  # reflejo de la Tierra en el satélite
    _area("Contra_Sat", 900, 2.0, (0.97, 0.99, 1.0))   # contraluz solar
    build_compositor()
    pose_final()
    return "ok"
