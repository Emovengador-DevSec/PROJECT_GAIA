"""PROJECT GAIA · construye la escena de portada en Blender (dirección "Amanecer orbital").

Uso dentro de Blender (o vía MCP):
    exec(open(r"<repo>/tools/blender/build_gaia_scene.py", encoding="utf-8").read())
    build()            # reconstruye toda la escena
    apply_shot("A")    # cuadro clave A: amanecer por el limbo (portada)
    apply_shot("B")    # cuadro clave B: NISAR barre Perú con su haz

Unidades: radio terrestre = 10. El satélite y el astronauta están a escala
"cinematográfica" (no real) y cerca de la cámara.
"""
import math
import os

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
    dot.inputs[1].default_value = SUN_DIR
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
def build_earth():
    coll = _collection("Tierra")
    earth = _sphere("Tierra", R, coll)
    earth["az0"] = _uv_lon_offset(earth)
    earth.visible_shadow = False   # las sombras de esferas tan grandes multiplican x70 el render

    mat, nt, out = _new_material("M_Tierra")
    day = _node(nt, "ShaderNodeTexImage", (-700, 300), image=_image("earth_day_8k.jpg"))
    night = _node(nt, "ShaderNodeTexImage", (-700, -100), image=_image("earth_night_3km.jpg"))
    # máscara de océano: el azul domina sobre rojo y verde (razón, no diferencia,
    # para que el mar profundo y oscuro también cuente como agua)
    sep = _node(nt, "ShaderNodeSeparateColor", (-400, 500))
    _link(nt, day.outputs["Color"], sep.inputs[0])
    mx = _node(nt, "ShaderNodeMath", (-220, 600), operation="MAXIMUM")
    _link(nt, sep.outputs[0], mx.inputs[0])
    _link(nt, sep.outputs[1], mx.inputs[1])
    sub = _node(nt, "ShaderNodeMath", (-220, 450), operation="SUBTRACT")
    _link(nt, sep.outputs[2], sub.inputs[0])
    _link(nt, mx.outputs[0], sub.inputs[1])
    den = _node(nt, "ShaderNodeMath", (-220, 300), operation="ADD")
    den.inputs[1].default_value = 0.004
    _link(nt, sep.outputs[2], den.inputs[0])
    ratio = _node(nt, "ShaderNodeMath", (-130, 500), operation="DIVIDE")
    _link(nt, sub.outputs[0], ratio.inputs[0])
    _link(nt, den.outputs[0], ratio.inputs[1])
    ocean = _node(nt, "ShaderNodeMapRange", (-40, 500))
    ocean.inputs["From Min"].default_value = 0.08
    ocean.inputs["From Max"].default_value = 0.3
    _link(nt, ratio.outputs[0], ocean.inputs["Value"])
    rough = _node(nt, "ShaderNodeMapRange", (140, 500))
    rough.inputs["To Min"].default_value = 0.85
    rough.inputs["To Max"].default_value = 0.4
    _link(nt, ocean.outputs["Result"], rough.inputs["Value"])
    # color de día algo más saturado
    hsv = _node(nt, "ShaderNodeHueSaturation", (-400, 300))
    hsv.inputs["Saturation"].default_value = 1.15
    hsv.inputs["Value"].default_value = 1.1
    _link(nt, day.outputs["Color"], hsv.inputs["Color"])
    # luces nocturnas solo en el lado oscuro
    night_f = _sun_facing(nt, 0.08, -0.18, (-700, -450))
    tint = _node(nt, "ShaderNodeMix", (-300, -150), data_type="RGBA", blend_type="MULTIPLY")
    _sock(tint.inputs, "Factor_Float").default_value = 1.0
    _sock(tint.inputs, "B_Color").default_value = (1.0, 0.72, 0.42, 1)
    _link(nt, night.outputs["Color"], _sock(tint.inputs, "A_Color"))
    estr = _node(nt, "ShaderNodeMath", (-100, -350), operation="MULTIPLY")
    estr.inputs[1].default_value = 6.0
    _link(nt, night_f, estr.inputs[0])
    p = _principled(nt, (500, 100))
    _sock(p.inputs, "Specular IOR Level").default_value = 0.6
    sea = _node(nt, "ShaderNodeMix", (200, 300), data_type="RGBA")
    _sock(sea.inputs, "B_Color").default_value = (0.012, 0.055, 0.16, 1)
    seaf = _node(nt, "ShaderNodeMath", (40, 250), operation="MULTIPLY")
    seaf.inputs[1].default_value = 0.75
    _link(nt, ocean.outputs["Result"], seaf.inputs[0])
    _link(nt, seaf.outputs[0], _sock(sea.inputs, "Factor_Float"))
    _link(nt, hsv.outputs["Color"], _sock(sea.inputs, "A_Color"))
    _link(nt, _sock(sea.outputs, "Result_Color"), _sock(p.inputs, "Base Color"))
    _link(nt, rough.outputs["Result"], _sock(p.inputs, "Roughness"))
    _link(nt, _sock(tint.outputs, "Result_Color"), _sock(p.inputs, "Emission Color"))
    _link(nt, estr.outputs[0], _sock(p.inputs, "Emission Strength"))
    _link(nt, p.outputs[0], out.inputs["Surface"])
    earth.data.materials.append(mat)

    # --- nubes (procedurales en fase 1; mapa NASA en fase 2) ---
    clouds = _sphere("Nubes", R * 1.006, coll)
    clouds.parent = earth
    clouds.visible_shadow = False
    mat, nt, out = _new_material("M_Nubes")
    tc = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    warp = _node(nt, "ShaderNodeTexNoise", (-700, -200))
    warp.inputs["Scale"].default_value = 0.22
    warp.inputs["Detail"].default_value = 4
    _link(nt, tc.outputs["Object"], warp.inputs["Vector"])
    mixv = _node(nt, "ShaderNodeMix", (-500, 0), data_type="VECTOR")
    _sock(mixv.inputs, "Factor_Float").default_value = 0.2
    _link(nt, tc.outputs["Object"], _sock(mixv.inputs, "A_Vector"))
    _link(nt, warp.outputs["Color"], _sock(mixv.inputs, "B_Vector"))
    big = _node(nt, "ShaderNodeTexNoise", (-300, 150))
    big.inputs["Scale"].default_value = 0.33
    big.inputs["Detail"].default_value = 14
    big.inputs["Roughness"].default_value = 0.62
    _link(nt, _sock(mixv.outputs, "Result_Vector"), big.inputs["Vector"])
    small = _node(nt, "ShaderNodeTexNoise", (-300, -150))
    small.inputs["Scale"].default_value = 1.6
    small.inputs["Detail"].default_value = 10
    _link(nt, _sock(mixv.outputs, "Result_Vector"), small.inputs["Vector"])
    mul = _node(nt, "ShaderNodeMath", (-100, 0), operation="MULTIPLY")
    _link(nt, big.outputs["Fac"], mul.inputs[0])
    _link(nt, small.outputs["Fac"], mul.inputs[1])
    alpha = _node(nt, "ShaderNodeMapRange", (100, 0))
    alpha.interpolation_type = "SMOOTHSTEP"
    alpha.inputs["From Min"].default_value = 0.25
    alpha.inputs["From Max"].default_value = 0.42
    alpha.inputs["To Max"].default_value = 0.95
    _link(nt, mul.outputs[0], alpha.inputs["Value"])
    p = _principled(nt, (500, 0), **{"Base Color": (1, 1, 1, 1), "Roughness": 0.9})
    _sock(p.inputs, "Specular IOR Level").default_value = 0.1
    _link(nt, alpha.outputs["Result"], _sock(p.inputs, "Alpha"))
    _link(nt, p.outputs[0], out.inputs["Surface"])
    clouds.data.materials.append(mat)

    # --- atmósfera: borde interior (sobre el disco) + halo exterior ---
    def atmo(name, radius, inner, strength):
        ob = _sphere(name, radius, coll, 128, 64)
        mat, nt, out = _new_material("M_" + name, blended=True)
        lw = _node(nt, "ShaderNodeLayerWeight", (-700, 200))
        lw.inputs["Blend"].default_value = 0.5
        shape = _node(nt, "ShaderNodeMapRange", (-500, 200))
        shape.interpolation_type = "SMOOTHERSTEP"
        if inner:   # brilla hacia el limbo del planeta
            shape.inputs["From Min"].default_value = 0.5
            shape.inputs["From Max"].default_value = 1.0
        else:       # halo: máximo en el limbo del planeta, cero en el borde del halo
            shape.inputs["From Min"].default_value = 0.0
            shape.inputs["From Max"].default_value = math.sqrt(1.0 - (R / radius) ** 2)
        if inner:
            _link(nt, lw.outputs["Facing"], shape.inputs["Value"])
        else:
            g = _node(nt, "ShaderNodeNewGeometry", (-900, 400))
            dt = _node(nt, "ShaderNodeVectorMath", (-750, 400), operation="DOT_PRODUCT")
            _link(nt, g.outputs["Incoming"], dt.inputs[0])
            _link(nt, g.outputs["Normal"], dt.inputs[1])
            ab = _node(nt, "ShaderNodeMath", (-600, 400), operation="ABSOLUTE")
            _link(nt, dt.outputs["Value"], ab.inputs[0])
            _link(nt, ab.outputs[0], shape.inputs["Value"])
            mat.use_backface_culling = True
        pw = _node(nt, "ShaderNodeMath", (-320, 200), operation="POWER")
        pw.inputs[1].default_value = 2.2 if inner else 3.2
        _link(nt, shape.outputs["Result"], pw.inputs[0])
        if not inner:   # sobre el disco el halo se apaga enseguida (solo bruma en el limbo)
            limb = math.sqrt(1.0 - (R / radius) ** 2)
            inside = _node(nt, "ShaderNodeMapRange", (-500, 420))
            inside.interpolation_type = "SMOOTHSTEP"
            inside.inputs["From Min"].default_value = limb
            inside.inputs["From Max"].default_value = limb + 0.22
            inside.inputs["To Min"].default_value = 1.0
            inside.inputs["To Max"].default_value = 0.0
            _link(nt, ab.outputs[0], inside.inputs["Value"])
            pw2 = _node(nt, "ShaderNodeMath", (-200, 320), operation="MULTIPLY")
            _link(nt, pw.outputs[0], pw2.inputs[0])
            _link(nt, inside.outputs["Result"], pw2.inputs[1])
            pw = pw2
        lit = _sun_facing(nt, -0.22, 0.35, (-900, -150))
        warm = _sun_facing(nt, 0.16, -0.1, (-900, -420))    # 1 cerca del terminador
        col = _node(nt, "ShaderNodeMix", (-200, -200), data_type="RGBA")
        _sock(col.inputs, "A_Color").default_value = (0.16, 0.42, 1.0, 1)
        _sock(col.inputs, "B_Color").default_value = (1.0, 0.42, 0.14, 1)
        wmul = _node(nt, "ShaderNodeMath", (-380, -350), operation="MULTIPLY")
        wmul.inputs[1].default_value = 0.6
        _link(nt, warm, wmul.inputs[0])
        _link(nt, wmul.outputs[0], _sock(col.inputs, "Factor_Float"))
        s = _node(nt, "ShaderNodeMath", (-100, 150), operation="MULTIPLY")
        _link(nt, pw.outputs[0], s.inputs[0])
        _link(nt, lit, s.inputs[1])
        s2 = _node(nt, "ShaderNodeMath", (80, 150), operation="MULTIPLY")
        s2.inputs[1].default_value = strength
        _link(nt, s.outputs[0], s2.inputs[0])
        em = _node(nt, "ShaderNodeEmission", (300, 100))
        _link(nt, _sock(col.outputs, "Result_Color"), em.inputs["Color"])
        _link(nt, s2.outputs[0], em.inputs["Strength"])
        tr = _node(nt, "ShaderNodeBsdfTransparent", (300, -80))
        add = _node(nt, "ShaderNodeAddShader", (560, 0))
        _link(nt, em.outputs[0], add.inputs[0])
        _link(nt, tr.outputs[0], add.inputs[1])
        _link(nt, add.outputs[0], out.inputs["Surface"])
        ob.data.materials.append(mat)
        ob.visible_shadow = False
        return ob

    atmo("Atmosfera", R * 1.012, True, 1.5)
    atmo("Halo", R * 1.09, False, 2.4)
    return earth


# ------------------------------------------------------------------- cielo y sol
def build_sky():
    scene = bpy.context.scene
    world = bpy.data.worlds.get("Espacio") or bpy.data.worlds.new("Espacio")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputWorld", (600, 0))
    env = _node(nt, "ShaderNodeTexEnvironment", (-300, 0), image=_image("starmap_2020_4k.exr"))
    mp = _node(nt, "ShaderNodeMapping", (-520, 0))
    mp.inputs["Rotation"].default_value = (math.radians(62), 0, math.radians(200))
    tc = _node(nt, "ShaderNodeTexCoord", (-720, 0))
    _link(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    _link(nt, mp.outputs["Vector"], env.inputs["Vector"])
    # las estrellas solo se ven desde la cámara; no iluminan la escena
    lp = _node(nt, "ShaderNodeLightPath", (-100, 250))
    bg = _node(nt, "ShaderNodeBackground", (100, 0))
    bg.inputs["Strength"].default_value = 0.9
    gm = _node(nt, "ShaderNodeGamma", (-100, 0))
    gm.inputs["Gamma"].default_value = 1.9
    _link(nt, env.outputs["Color"], gm.inputs["Color"])
    _link(nt, gm.outputs["Color"], bg.inputs["Color"])
    black = _node(nt, "ShaderNodeBackground", (100, -160))
    black.inputs["Color"].default_value = (0, 0, 0, 1)
    mix = _node(nt, "ShaderNodeMixShader", (350, 0))
    _link(nt, lp.outputs["Is Camera Ray"], mix.inputs[0])
    _link(nt, black.outputs[0], mix.inputs[1])
    _link(nt, bg.outputs[0], mix.inputs[2])
    _link(nt, mix.outputs[0], out.inputs["Surface"])

    coll = _collection("Luz")
    light = bpy.data.lights.new("Sol", "SUN")
    light.energy = 5.5
    light.angle = math.radians(0.6)
    light.color = (1.0, 0.96, 0.9)
    sun = bpy.data.objects.new("Sol", light)
    coll.objects.link(sun)
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = SUN_DIR.to_track_quat("Z", "Y")

    # disco solar visible (el destello lo añade el compositor)
    dist = 900.0
    disc = _add("SolDisco", bpy.ops.mesh.primitive_uv_sphere_add, coll,
                segments=48, ring_count=24, radius=dist * math.tan(math.radians(0.42)),
                location=CAM_A_POS + SUN_DIR * dist)
    mat, nt, out = _new_material("M_Sol")
    em = _node(nt, "ShaderNodeEmission", (300, 0))
    em.inputs["Color"].default_value = (1.0, 0.93, 0.82, 1)
    em.inputs["Strength"].default_value = 900.0
    _link(nt, em.outputs[0], out.inputs["Surface"])
    disc.data.materials.append(mat)
    disc.visible_shadow = False


# -------------------------------------------------------------------------- NISAR
def build_nisar():
    """NISAR con proporciones reales en metros: bus, instrumento, brazo de 9 m,
    reflector de malla de 12 m y paneles solares. Padre: 'NISAR' (vacío)."""
    coll = _collection("NISAR")
    root = bpy.data.objects.new("NISAR", None)
    root.empty_display_size = 2
    coll.objects.link(root)

    gold = _simple_mat("M_MLI_Oro", (0.83, 0.56, 0.16), metallic=1.0, rough=0.38)
    dark = _simple_mat("M_Estructura", (0.04, 0.04, 0.045), metallic=0.6, rough=0.45)
    white = _simple_mat("M_Radiador", (0.86, 0.86, 0.84), rough=0.5)
    boom_m = _simple_mat("M_Brazo", (0.55, 0.56, 0.58), metallic=0.9, rough=0.3)

    # panel solar con retícula de celdas
    solar, nt, out = _new_material("M_PanelSolar")
    tc = _node(nt, "ShaderNodeTexCoord", (-700, 0))
    br = _node(nt, "ShaderNodeTexBrick", (-450, 0))
    br.offset = 0.0
    br.inputs["Color1"].default_value = (0.012, 0.022, 0.09, 1)
    br.inputs["Color2"].default_value = (0.016, 0.03, 0.12, 1)
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
        wv.inputs["Scale"].default_value = 14.0
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
    base.inputs[1].default_value = 0.34
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


# ---------------------------------------------------------------------- astronauta
ASTRONAUT_GLB = os.path.join(REPO, "art", "models", "nasa_astronaut", "Astronaut.glb")


def build_astronaut():
    """Astronauta de NASA 3D Resources (dominio público), normalizado a 1.9 m de alto,
    pies en el origen, mirando a -Y. Padre: 'Astronauta'."""
    if not os.path.exists(ASTRONAUT_GLB):
        return _build_astronaut_placeholder()
    coll = _collection("Astronauta")
    root = bpy.data.objects.new("Astronauta", None)
    coll.objects.link(root)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ASTRONAUT_GLB)
    new = [o for o in bpy.data.objects if o not in before]
    suit = _simple_mat("M_Traje", (0.86, 0.86, 0.84), rough=0.82)
    for ob in new:
        if ob.type != "MESH":
            continue
        mw = ob.matrix_world.copy()
        ob.parent = None
        ob.matrix_world = mw
        zs = [(mw @ Vector(c)).z for c in ob.bound_box]
        k = 1.9 / (max(zs) - min(zs))
        ob.matrix_world = Matrix.Translation((0, 0, -min(zs) * k)) @ Matrix.Scale(k, 4) @ mw
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
        ob.parent = root
        ob.name = "Astronauta_Malla"
        _smooth(ob)
        for i, m in enumerate(ob.data.materials):
            if m and m.name.startswith("astnt1_2"):   # parche de 128 px mal mapeado
                ob.data.materials[i] = suit
            elif m:
                pr = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if pr:
                    _sock(pr.inputs, "Roughness").default_value = 0.7
                    _sock(pr.inputs, "Metallic").default_value = 0.0
    for ob in new:
        if ob.type != "MESH":
            bpy.data.objects.remove(ob, do_unlink=True)
    return root


def _build_astronaut_placeholder():
    """Respaldo de volúmenes simples si falta el modelo de NASA; alto ≈ 1.9 m."""
    coll = _collection("Astronauta")
    root = bpy.data.objects.new("Astronauta", None)
    coll.objects.link(root)
    suit = _simple_mat("M_Traje", (0.86, 0.86, 0.84), rough=0.82)
    grey = _simple_mat("M_TrajeGris", (0.32, 0.33, 0.35), rough=0.6)
    visor = _simple_mat("M_Visor", (0.9, 0.62, 0.18), metallic=1.0, rough=0.08)
    red = _simple_mat("M_Franja", (0.7, 0.05, 0.04), rough=0.6)

    def part(name, fn, mat, **kw):
        ob = _add(name, fn, coll, **kw)
        ob.data.materials.append(mat)
        ob.parent = root
        _smooth(ob)
        return ob

    def rbox(name, size, loc, mat, rot=(0, 0, 0)):
        ob = part(name, bpy.ops.mesh.primitive_cube_add, mat, size=1, location=loc)
        ob.scale = size
        ob.rotation_euler = rot
        m = ob.modifiers.new("Subsurf", "SUBSURF")
        m.levels = m.render_levels = 3
        return ob

    def limb(name, pts, radius, mat=suit):
        for i in range(len(pts) - 1):
            a, b = Vector(pts[i]), Vector(pts[i + 1])
            c = part(f"{name}_{i}", bpy.ops.mesh.primitive_cylinder_add, mat, vertices=20,
                     radius=radius, depth=(b - a).length, location=(a + b) / 2)
            c.rotation_mode = "QUATERNION"
            c.rotation_quaternion = (b - a).to_track_quat("Z", "Y")
        for i, pt in enumerate(pts):
            part(f"{name}_j{i}", bpy.ops.mesh.primitive_uv_sphere_add, mat, segments=20,
                 ring_count=10, radius=radius * 1.08, location=pt)

    rbox("Torso", (0.62, 0.46, 0.72), (0, 0, 1.25), suit)
    rbox("Mochila", (0.6, 0.3, 0.86), (0, 0.3, 1.32), suit)
    rbox("Pecho_Control", (0.3, 0.14, 0.24), (0, -0.25, 1.22), grey)
    rbox("Pelvis", (0.5, 0.4, 0.34), (0, 0, 0.84), suit)
    part("Casco", bpy.ops.mesh.primitive_uv_sphere_add, suit, segments=40, ring_count=20,
         radius=0.2, location=(0, -0.02, 1.76))
    v = part("Visor", bpy.ops.mesh.primitive_uv_sphere_add, visor, segments=40, ring_count=20,
             radius=0.172, location=(0, -0.075, 1.765))
    v.scale = (1.0, 0.92, 0.95)
    ring = part("Cuello", bpy.ops.mesh.primitive_torus_add, grey, major_radius=0.17,
                minor_radius=0.03, location=(0, 0, 1.6))
    for side in (-1, 1):
        limb(f"Brazo_{side}", [(side * 0.36, 0, 1.5), (side * 0.6, -0.12, 1.26),
                               (side * 0.66, -0.42, 1.2 + 0.1 * side)], 0.085)
        part(f"Guante_{side}", bpy.ops.mesh.primitive_uv_sphere_add, grey, segments=16,
             ring_count=8, radius=0.1, location=(side * 0.67, -0.5, 1.2 + 0.1 * side))
        limb(f"Pierna_{side}", [(side * 0.15, 0, 0.78), (side * 0.2, -0.1 - 0.06 * side, 0.4),
                                (side * 0.22, 0.12, 0.05)], 0.105)
        b = rbox(f"Bota_{side}", (0.17, 0.3, 0.14), (side * 0.22, 0.06, -0.02), grey)
        part(f"Franja_{side}", bpy.ops.mesh.primitive_torus_add, red, major_radius=0.108,
             minor_radius=0.012, location=(side * 0.175, -0.05, 0.6))
    return root


# --------------------------------------------------------------------- haz de radar
def build_beam():
    coll = _collection("Haz")
    mat, nt, out = _new_material("M_Haz", blended=True)
    tc = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    sep = _node(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    _link(nt, tc.outputs["Generated"], sep.inputs[0])
    fade = _node(nt, "ShaderNodeMapRange", (-500, 0))      # más intenso hacia el suelo
    fade.inputs["From Min"].default_value = 1.0
    fade.inputs["From Max"].default_value = 0.0
    fade.inputs["To Min"].default_value = 0.05
    fade.inputs["To Max"].default_value = 1.0
    _link(nt, sep.outputs["Z"], fade.inputs["Value"])
    wave = _node(nt, "ShaderNodeTexWave", (-700, -300), bands_direction="Z")
    wave.inputs["Scale"].default_value = 9.0
    _link(nt, tc.outputs["Generated"], wave.inputs["Vector"])
    wmr = _node(nt, "ShaderNodeMapRange", (-500, -300))
    wmr.inputs["To Min"].default_value = 0.55
    _link(nt, wave.outputs["Fac"], wmr.inputs["Value"])
    lw = _node(nt, "ShaderNodeLayerWeight", (-700, 300))
    lw.inputs["Blend"].default_value = 0.35
    m1 = _node(nt, "ShaderNodeMath", (-250, 0), operation="MULTIPLY")
    _link(nt, fade.outputs["Result"], m1.inputs[0])
    _link(nt, wmr.outputs["Result"], m1.inputs[1])
    edge = _node(nt, "ShaderNodeMath", (-250, 300), operation="ADD")
    edge.inputs[1].default_value = 0.25
    _link(nt, lw.outputs["Facing"], edge.inputs[0])
    m2 = _node(nt, "ShaderNodeMath", (-50, 100), operation="MULTIPLY")
    _link(nt, m1.outputs[0], m2.inputs[0])
    _link(nt, edge.outputs[0], m2.inputs[1])
    m3 = _node(nt, "ShaderNodeMath", (130, 100), operation="MULTIPLY")
    m3.inputs[1].default_value = 1.6
    _link(nt, m2.outputs[0], m3.inputs[0])
    em = _node(nt, "ShaderNodeEmission", (330, 100))
    em.inputs["Color"].default_value = (0.25, 0.85, 1.0, 1)
    _link(nt, m3.outputs[0], em.inputs["Strength"])
    tr = _node(nt, "ShaderNodeBsdfTransparent", (330, -80))
    add = _node(nt, "ShaderNodeAddShader", (560, 0))
    _link(nt, em.outputs[0], add.inputs[0])
    _link(nt, tr.outputs[0], add.inputs[1])
    _link(nt, add.outputs[0], out.inputs["Surface"])
    mat.use_backface_culling = False

    beam = _add("Haz", bpy.ops.mesh.primitive_cone_add, coll, vertices=64,
                radius1=1.0, radius2=0.02, depth=1.0, end_fill_type="NOTHING")
    beam.data.materials.append(mat)
    beam.visible_shadow = False
    _smooth(beam)

    # huella sobre la superficie
    fmat, nt, out = _new_material("M_Huella", blended=True)
    tc = _node(nt, "ShaderNodeTexCoord", (-700, 0))
    gr = _node(nt, "ShaderNodeTexGradient", (-300, 0), gradient_type="SPHERICAL")
    mp = _node(nt, "ShaderNodeMapping", (-500, 0))
    mp.inputs["Location"].default_value = (-1, -1, 0)
    mp.inputs["Scale"].default_value = (2, 2, 2)
    _link(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    _link(nt, mp.outputs["Vector"], gr.inputs["Vector"])
    ramp = _node(nt, "ShaderNodeValToRGB", (-100, 0))
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0, 0, 0, 1)
    els[1].position, els[1].color = 0.12, (1, 1, 1, 1)
    e = els.new(0.3)
    e.color = (0.25, 0.25, 0.25, 1)
    _link(nt, gr.outputs["Fac"], ramp.inputs["Fac"])
    st = _node(nt, "ShaderNodeMath", (180, 0), operation="MULTIPLY")
    st.inputs[1].default_value = 2.2
    _link(nt, ramp.outputs["Color"], st.inputs[0])
    em = _node(nt, "ShaderNodeEmission", (360, 100))
    em.inputs["Color"].default_value = (0.3, 0.9, 1.0, 1)
    _link(nt, st.outputs[0], em.inputs["Strength"])
    tr = _node(nt, "ShaderNodeBsdfTransparent", (360, -80))
    add = _node(nt, "ShaderNodeAddShader", (560, 0))
    _link(nt, em.outputs[0], add.inputs[0])
    _link(nt, tr.outputs[0], add.inputs[1])
    _link(nt, add.outputs[0], out.inputs["Surface"])
    foot = _add("Huella", bpy.ops.mesh.primitive_circle_add, coll, vertices=64,
                radius=1.0, fill_type="NGON")
    foot.data.materials.append(fmat)
    foot.visible_shadow = False


def aim_beam(source, ground_dir, radius=0.55, visible=True):
    """Tiende el haz desde `source` (mundo) hasta el punto de superficie en `ground_dir`."""
    beam, foot = bpy.data.objects["Haz"], bpy.data.objects["Huella"]
    for ob in (beam, foot):
        ob.hide_render = ob.hide_viewport = not visible
    if not visible:
        return
    n = ground_dir.normalized()
    g = n * (R * 1.012)
    axis = g - source
    beam.location = (source + g) / 2
    beam.rotation_mode = "QUATERNION"
    beam.rotation_quaternion = axis.to_track_quat("-Z", "Y")
    beam.scale = (radius, radius * 0.45, axis.length)
    foot.location = n * (R * 1.014)
    foot.rotation_mode = "QUATERNION"
    foot.rotation_quaternion = n.to_track_quat("Z", "Y") @ Quaternion((0, 0, 1), 0.0)
    foot.scale = (radius * 1.15, radius * 0.5, 1)


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


def _feed_world(sat):
    return sat.matrix_world @ Vector((0, -1.45, 2.2))


def apply_shot(shot):
    """Deja la escena lista para el cuadro clave A (portada) o B (haz sobre Perú)."""
    scene = bpy.context.scene
    sat, astro = bpy.data.objects["NISAR"], bpy.data.objects["Astronauta"]
    fill = bpy.data.objects["Relleno"]
    if shot == "A":
        cam = bpy.data.objects["Cam_A"]
        cam.location = CAM_A_POS
        _look_at(cam, CAM_A_TARGET)
        bpy.context.view_layer.update()
        orient_earth(-14.0, -62.0, CAM_A_POS + Vector((-6, 0, 3)), Vector((0.25, 0, 1)))
        _place(sat, cam, -2.0, 1.25, 8.4, 0.12,
               Quaternion((1, 0, 0), math.radians(62)) @ Quaternion((0, 0, 1), math.radians(-38)))
        _place(astro, cam, 0.52, -0.5, 1.3, 0.2,
               Quaternion((0, 0, 1), math.radians(-16)) @ Quaternion((0, 1, 0), math.radians(-28))
               @ Quaternion((1, 0, 0), math.radians(-90)) @ Quaternion((0, 0, 1), math.radians(180)))
        bpy.context.view_layer.update()
        aim_beam(_feed_world(sat), Vector((0, -1, 0)), visible=False)
        cam.data.dof.use_dof = True
        cam.data.dof.focus_object = None
        cam.data.dof.focus_distance = 22.0
        cam.data.dof.aperture_fstop = 2.0
        scene.frame_set(1)
    else:
        cam = bpy.data.objects["Cam_B"]
        up = (Vector((0, 0, 1)) - Vector((0, 0, 1)).dot(SUN_DIR) * SUN_DIR).normalized()
        c = Quaternion(up, math.radians(48)) @ SUN_DIR      # Tierra -> cámara, lado de día
        right = (-c).cross(up).normalized()
        if SUN_DIR.dot(right) > 0:                           # el sol debe entrar por la izquierda
            c = Quaternion(up, math.radians(-48)) @ SUN_DIR
            right = (-c).cross(up).normalized()
        cam.location = c * 26.0
        fwd = (-c + right * math.tan(math.radians(-11)) + up * math.tan(math.radians(9))).normalized()
        _look_dir(cam, fwd, up)
        bpy.context.view_layer.update()
        peru_dir = (c - right * 0.2 + up * 0.12).normalized()
        orient_earth(PERU[0], PERU[1], peru_dir, up)
        _place(sat, cam, -2.1, 1.2, 8.0, 0.13,
               Quaternion((1, 0, 0), math.radians(100)) @ Quaternion((0, 0, 1), math.radians(-140)))
        _place(astro, cam, -3.0, -2.0, 1.4, 0.2,   # fuera de cuadro en B
              
               Quaternion((0, 0, 1), math.radians(14)) @ Quaternion((0, 1, 0), math.radians(24))
               @ Quaternion((1, 0, 0), math.radians(-90)) @ Quaternion((0, 0, 1), math.radians(180)))
        bpy.context.view_layer.update()
        aim_beam(_feed_world(sat), peru_dir, radius=0.38, visible=True)
        cam.data.dof.use_dof = True
        cam.data.dof.focus_object = None
        cam.data.dof.focus_distance = 14.0
        cam.data.dof.aperture_fstop = 2.0
        scene.frame_set(2)
    scene.camera = cam
    # luz de relleno (reflejo de la Tierra) siguiendo a la cámara
    m = cam.matrix_world.to_3x3()
    fill.location = cam.location + m @ Vector((1.5, -1.2, -0.2))
    _look_at(fill, astro.location)
    key = bpy.data.objects["Relleno_Sat"]
    key.location = sat.location + m @ Vector((-1.2, -0.6, 1.6))
    _look_at(key, sat.location)
    bpy.context.view_layer.update()


# ----------------------------------------------------------------------------- render
def setup_render():
    scene = bpy.context.scene
    r = scene.render
    try:
        r.engine = "BLENDER_EEVEE"
    except TypeError:
        r.engine = "BLENDER_EEVEE_NEXT"
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    ee = scene.eevee
    for attr, val in (("taa_render_samples", 64), ("use_raytracing", False),
                      ("use_shadows", True)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    vs = scene.view_settings
    looks = [i.identifier for i in type(vs).bl_rna.properties["look"].enum_items]
    try:
        vs.view_transform = "AgX"
        for cand in ("AgX - Medium High Contrast", "Medium High Contrast"):
            if cand in looks:
                vs.look = cand
                break
    except TypeError:
        pass
    vs.exposure = 0.0


def build_compositor():
    """Destello del sol: resplandor + rayos anamórficos + leve aberración de lente."""
    scene = bpy.context.scene
    old = bpy.data.node_groups.get("GAIA_Comp")
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new("GAIA_Comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = _node(ng, "CompositorNodeRLayers", (-600, 0))
    bloom = _node(ng, "CompositorNodeGlare", (-350, 0))
    bloom.inputs["Type"].default_value = "Bloom"
    bloom.inputs["Highlights Threshold"].default_value = 1.2
    bloom.inputs["Strength"].default_value = 0.55
    bloom.inputs["Size"].default_value = 0.75
    streak = _node(ng, "CompositorNodeGlare", (-100, 0))
    streak.inputs["Type"].default_value = "Streaks"
    streak.inputs["Highlights Threshold"].default_value = 40.0
    streak.inputs["Strength"].default_value = 0.1
    streak.inputs["Streaks"].default_value = 2
    streak.inputs["Streaks Angle"].default_value = 0.0
    streak.inputs["Iterations"].default_value = 5
    streak.inputs["Fade"].default_value = 0.94
    lens = _node(ng, "CompositorNodeLensdist", (150, 0))
    lens.inputs["Dispersion"].default_value = 0.012
    out = _node(ng, "NodeGroupOutput", (400, 0))
    ng.links.new(rl.outputs["Image"], bloom.inputs["Image"])
    ng.links.new(bloom.outputs["Image"], streak.inputs["Image"])
    ng.links.new(streak.outputs["Image"], lens.inputs["Image"])
    ng.links.new(lens.outputs["Image"], out.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True


def render_shot(shot, path):
    apply_shot(shot)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def build():
    # escena limpia
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
    build_astronaut()
    build_beam()
    _camera("Cam_A", 35)
    _camera("Cam_B", 40)
    fl = bpy.data.lights.new("Relleno", "AREA")
    fl.energy = 90
    fl.size = 2.5
    fl.color = (0.45, 0.62, 1.0)
    fo = bpy.data.objects.new("Relleno", fl)
    _collection("Luz").objects.link(fo)
    kl = bpy.data.lights.new("Relleno_Sat", "AREA")
    kl.energy = 110
    kl.size = 2.0
    kl.color = (1.0, 0.86, 0.7)
    _collection("Luz").objects.link(bpy.data.objects.new("Relleno_Sat", kl))
    build_compositor()
    apply_shot("A")
    return "ok"
