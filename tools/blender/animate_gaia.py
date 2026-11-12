"""PROJECT GAIA · animación de la portada (intro de 6 s + bucle de 10 s sin corte).

Uso dentro de Blender, después de build_gaia_scene.build():
    exec(open(r"<repo>/tools/blender/build_gaia_scene.py", encoding="utf-8").read())
    exec(open(r"<repo>/tools/blender/animate_gaia.py", encoding="utf-8").read())
    animate()

Línea de tiempo a 30 fps:
    cuadros   1-180  intro: estrellas -> amanecer por el limbo -> entra NISAR y su haz toca Perú
    cuadros 181-480  bucle: deriva de cámara, el sol "respira" en el limbo, el haz barre Perú
El cuadro 481 sería idéntico al 181, así que el bucle no tiene corte.

Cámaras horneadas: Cam_Cine (16:9) y Cam_Cine_V (9:16).
"""
import math

import bpy
from mathutils import Quaternion, Vector

FPS = 30
INTRO = 180
LOOP = 300
TOTAL = INTRO + LOOP

# requiere los símbolos de build_gaia_scene.py en el mismo espacio de nombres


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def _ramp(t, a, b):
    return _ease((t - a) / (b - a))


def _breath(phase, cycles=1):
    """0 -> 1 -> 0 con velocidad cero al inicio y al final del bucle."""
    return (1 - math.cos(2 * math.pi * cycles * phase)) / 2


def _key(ob, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert("location", frame=frame)
    if rot is not None:
        ob.rotation_mode = "QUATERNION"
        if ob.get("_prev_q") is not None:      # evita saltos de signo entre cuadros
            prev = Quaternion(ob["_prev_q"])
            if prev.dot(rot) < 0:
                rot = -rot
        ob["_prev_q"] = list(rot)
        ob.rotation_quaternion = rot
        ob.keyframe_insert("rotation_quaternion", frame=frame)
    if scale is not None:
        ob.scale = scale
        ob.keyframe_insert("scale", frame=frame)


def animate():
    scene = bpy.context.scene
    apply_shot("A")
    bpy.context.view_layer.update()
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, TOTAL

    objs = bpy.data.objects
    earth, sat, astro = objs["Tierra"], objs["NISAR"], objs["Astronauta"]
    beam, foot, cam_a = objs["Haz"], objs["Huella"], objs["Cam_A"]
    for ob in (beam, foot):
        ob.hide_render = ob.hide_viewport = False

    cams = {}
    for name, lens, yaw_off, pitch_off in (("Cam_Cine", 35, 0.0, 0.0),
                                           ("Cam_Cine_V", 21, -3.0, -4.0)):
        old = objs.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        cam = _camera(name, lens)
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = 22.0
        cam.data.dof.aperture_fstop = 2.0
        cams[name] = (cam, math.radians(yaw_off), math.radians(pitch_off))

    # estado final (= cuadro clave A aprobado), en coordenadas de mundo
    m = cam_a.matrix_world.to_3x3()
    right, up = m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0))
    f_final = (CAM_A_TARGET - CAM_A_POS).normalized()
    sat_loc, sat_rot, sat_scale = sat.location.copy(), sat.rotation_quaternion.copy(), sat.scale.copy()
    as_loc, as_rot = astro.location.copy(), astro.rotation_quaternion.copy()
    earth_q, az0 = earth.rotation_quaternion.copy(), earth["az0"]
    for ob in (sat, astro, beam, foot, *[c[0] for c in cams.values()]):
        ob.animation_data_clear()
        if "_prev_q" in ob:
            del ob["_prev_q"]

    def peru(lat, lon):
        return earth_q @ latlon_local(lat, lon, az0)

    for frame in range(1, TOTAL + 1):
        t = (frame - 1) / FPS                     # segundos desde el inicio
        in_loop = frame > INTRO
        ph = (frame - 1 - INTRO) / LOOP if in_loop else 0.0   # fase del bucle 0..1

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

        # --- NISAR: entra desde arriba a la izquierda y queda flotando ---
        arrive = _ramp(t, 2.2, 5.0)
        s_loc = sat_loc + (right * -1.0 + up * 7.5) * (1.0 - arrive)
        s_rot = sat_rot @ Quaternion((0, 0, 1), math.radians(-55) * (1.0 - arrive))
        if in_loop:
            s_loc = sat_loc + up * 0.06 * _breath(ph) + right * 0.05 * _breath(ph, 2)
            s_rot = sat_rot @ Quaternion((0, 0, 1), math.radians(5) * _breath(ph))
        _key(sat, frame, loc=s_loc, rot=s_rot)

        # --- astronauta: deriva lenta ---
        a_loc = as_loc + (up * -0.1 + right * 0.06) * (1.0 - _ramp(t, 0.0, 6.0))
        a_rot = as_rot @ Quaternion((0, 0, 1), math.radians(-10) * (1.0 - _ramp(t, 0.0, 6.0)))
        if in_loop:
            a_loc = as_loc + up * 0.035 * _breath(ph) + right * -0.02 * _breath(ph, 2)
            a_rot = as_rot @ Quaternion((0, 0, 1), math.radians(7) * _breath(ph)) \
                @ Quaternion((1, 0, 0), math.radians(3) * _breath(ph, 2))
        # acompaña a la cámara (85 %) para que el paralaje sea sutil y no cruce el cuadro
        a_loc = a_loc + (pos - CAM_A_POS) * 0.85
        _key(astro, frame, loc=a_loc, rot=a_rot)

        # --- haz de radar: se despliega al final de la intro y barre la costa de Perú ---
        grow = _ramp(t, 4.5, 5.6)
        sweep = _breath(ph) if in_loop else 0.0
        lat, lon = -4.0 - 13.0 * sweep, -79.5 + 8.5 * sweep
        n = peru(lat, lon).normalized()
        src = s_loc + s_rot @ (Vector((0, -1.45, 2.2)) * sat_scale.x)
        ground = n * (R * 1.012)
        tip = src + (ground - src) * max(grow, 1e-3)
        axis = tip - src
        radius = 0.34
        _key(beam, frame, loc=(src + tip) / 2, rot=axis.to_track_quat("-Z", "Y"),
             scale=(radius * grow, radius * 0.45 * grow, axis.length))
        land = _ramp(t, 5.3, 5.9)
        _key(foot, frame, loc=n * (R * 1.014), rot=n.to_track_quat("Z", "Y"),
             scale=(radius * 1.15 * land + 1e-4, radius * 0.5 * land + 1e-4, 1))

    for ob in (sat, astro, beam, foot, *[c[0] for c in cams.values()]):
        if "_prev_q" in ob:
            del ob["_prev_q"]
    scene.camera = cams["Cam_Cine"][0]
    scene.frame_set(INTRO)
    return "ok"
