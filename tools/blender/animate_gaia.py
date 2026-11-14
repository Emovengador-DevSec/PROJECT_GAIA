"""PROJECT GAIA · animación de la portada (intro de 6 s + bucle de 10 s sin corte).

Uso dentro de Blender:
    exec(open(r"<repo>/tools/blender/build_gaia_scene.py", encoding="utf-8").read())
    exec(open(r"<repo>/tools/blender/animate_gaia.py", encoding="utf-8").read())
    build(); animate()

Línea de tiempo a 30 fps:
    cuadros   1-180  intro: estrellas -> la Tierra entra en cuadro -> el sol asoma por el
                     limbo -> baja NISAR y su haz toca la costa del Perú
    cuadros 181-480  bucle: deriva de cámara, el haz recorre la costa,
                     las rocas giran y cruzan tres meteoros
El cuadro 481 sería idéntico al 181, así que el bucle no tiene corte: todo movimiento del
bucle es periódico (vueltas enteras o curvas 1-cos que empiezan y acaban en reposo).

Cámaras horneadas: Cam_Cine (16:9) y Cam_Cine_V (9:16).
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 30
INTRO = 180
LOOP = 300
TOTAL = INTRO + LOOP
PULSES_PER_LOOP = 9          # frentes de onda del haz que salen en cada bucle

# requiere los símbolos de build_gaia_scene.py en el mismo espacio de nombres


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def _ramp(t, a, b):
    return _ease((t - a) / (b - a))


def _breath(phase, cycles=1):
    """0 -> 1 -> 0 con velocidad cero al inicio y al final del bucle."""
    return (1 - math.cos(2 * math.pi * cycles * phase)) / 2


_prev = {}


def _key(ob, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert("location", frame=frame)
    if rot is not None:
        ob.rotation_mode = "QUATERNION"
        prev = _prev.get(ob.name)            # evita saltos de signo entre cuadros
        if prev is not None and prev.dot(rot) < 0:
            rot = -rot
        _prev[ob.name] = rot.copy()
        ob.rotation_quaternion = rot
        ob.keyframe_insert("rotation_quaternion", frame=frame)
    if scale is not None:
        ob.scale = scale
        ob.keyframe_insert("scale", frame=frame)


def _key_value(node, frame, value):
    sock = node.outputs[0]
    sock.default_value = value
    sock.keyframe_insert("default_value", frame=frame)


def animate():
    scene = bpy.context.scene
    pose_final()
    bpy.context.view_layer.update()
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, TOTAL
    _prev.clear()

    objs = bpy.data.objects
    earth, sat = objs["Tierra"], objs["NISAR"]
    beam, foot, cam_a = objs["Haz"], objs["Huella"], objs["Cam_A"]
    rocks = [o for o in objs if o.name.startswith("Roca_")]
    meteors = [objs[f"Meteoro_{i}"] for i in range(len(METEORS))]
    beam_nt = bpy.data.materials["M_Haz"].node_tree
    beam_nt.animation_data_clear()

    cams = {}
    for name, lens, yaw_off, pitch_off in (("Cam_Cine", 35, 0.0, 0.0),
                                           ("Cam_Cine_V", 21, -3.0, -4.0)):
        old = objs.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        cam = _camera(name, lens)
        cam.data.dof.use_dof = False
        cams[name] = (cam, math.radians(yaw_off), math.radians(pitch_off))

    # estado final (= composición de portada), en coordenadas de mundo
    m = cam_a.matrix_world.to_3x3()
    right, up = m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0))
    f_final = (CAM_A_TARGET - CAM_A_POS).normalized()
    sat_loc, sat_rot, sat_scale = sat.location.copy(), sat.rotation_quaternion.copy(), sat.scale.copy()
    earth_q, az0 = earth.rotation_quaternion.copy(), earth["az0"]
    rock_base = {r.name: r.location.copy() for r in rocks}
    for ob in (sat, beam, foot, *rocks, *meteors):
        ob.animation_data_clear()

    def ground(u):
        return (earth_q @ latlon_local(*swath_latlon(u), az0)).normalized()

    def surface(lat, lon):
        return (earth_q @ latlon_local(lat, lon, az0)).normalized()

    for frame in range(1, TOTAL + 1):
        t = (frame - 1) / FPS                     # segundos desde el inicio
        in_loop = frame > INTRO
        ph = (frame - 1 - INTRO) / LOOP           # fase del bucle (negativa en la intro)

        # --- cámara: paneo desde las estrellas + desplazamiento que destapa el sol ---
        pan = 1.0 - _ramp(t, 0.3, 3.6)            # 1 = mirando a las estrellas
        hide = 1.0 - _ramp(t, 1.8, 4.6)           # 1 = sol oculto tras el limbo
        pos = CAM_A_POS - _LIMB * 0.95 * hide
        yaw, pitch = math.radians(38) * pan, math.radians(5) * pan
        if in_loop:
            pos = (CAM_A_POS - _LIMB * 0.2 * _breath(ph)
                   + right * 0.07 * _breath(ph, 2) * math.cos(2 * math.pi * ph)
                   + up * 0.08 * _breath(ph, 2))
            yaw = math.radians(0.5) * _breath(ph, 2) * math.cos(2 * math.pi * ph)
        for cam, yaw_off, pitch_off in cams.values():
            d = Quaternion((0, 0, 1), yaw + yaw_off) @ f_final
            d = (d + Vector((0, 0, 1)) * math.tan(pitch + pitch_off)).normalized()
            _key(cam, frame, loc=pos, rot=d.to_track_quat("-Z", "Y"))

        # --- NISAR: baja desde arriba y queda flotando ---
        arrive = _ramp(t, 2.2, 5.0)
        s_loc = sat_loc + (right * -1.0 + up * 7.5) * (1.0 - arrive)
        s_rot = sat_rot @ Quaternion((0, 0, 1), math.radians(-55) * (1.0 - arrive))
        if in_loop:
            s_loc = sat_loc + up * 0.06 * _breath(ph) + right * 0.05 * _breath(ph, 2)
            s_rot = sat_rot @ Quaternion((0, 0, 1), math.radians(5) * _breath(ph))
        _key(sat, frame, loc=s_loc, rot=s_rot)


        # --- rocas: fijas en el espacio (el paralaje las mueve) y girando vueltas enteras ---
        for r in rocks:
            ang = r["phase0"] + 2 * math.pi * r["turns"] * ph
            _key(r, frame, loc=rock_base[r.name], rot=Quaternion(Vector(r["axis"]), ang))

        # --- haz ilustrativo: se despliega al final de la intro y recorre la costa ---
        grow, land = _ramp(t, 4.4, 5.5), _ramp(t, 5.2, 5.9)
        u = 0.1 + 0.8 * (_breath(ph) if in_loop else 0.0)
        src = s_loc + s_rot @ (FEED_LOCAL * sat_scale.x)
        cone, fp = aim_beam(src, ground(u), grow=grow, land=land)
        _key(beam, frame, *cone)
        _key(foot, frame, *fp)
        _key_value(beam_nt.nodes["FASE"], frame, ph * PULSES_PER_LOOP)

        # --- meteoros sobre el lado nocturno ---
        for mob, (start, end, a, b) in zip(meteors, METEORS):
            if not (in_loop and a <= ph <= b):
                _key(mob, frame, scale=(0, 0, 0))
                continue
            k = (ph - a) / (b - a)
            n0, n1 = surface(*start), surface(*end)
            n = n0.slerp(n1, k).normalized()
            d = (n1 - n0)
            d = (d - d.dot(n) * n).normalized()
            rot = Matrix((d, n.cross(d), n)).transposed().to_quaternion()
            length = 1.5 * math.sin(math.pi * k) ** 0.7
            _key(mob, frame, loc=n * (R * 1.02), rot=rot, scale=(length, 0.045, 1))

    scene.camera = cams["Cam_Cine"][0]
    scene.frame_set(INTRO)
    return "ok"
