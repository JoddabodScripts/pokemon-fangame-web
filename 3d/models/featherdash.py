"""Featherdash: long-legged running bird, half snowy, with a red scarf and an eye-spot tail."""
import math
from mathutils import Vector


def _basis(d):
    d = Vector(d).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((0, 1, 0))
    u = up.cross(d).normalized()
    v = d.cross(u).normalized()
    return d, u, v


def on(c, r, d, k=1.0):
    """Point on the ellipsoid (center c, radii r) in unit direction d, pushed out by factor k."""
    d = Vector(d).normalized()
    return (c[0] + r[0] * d.x * k, c[1] + r[1] * d.y * k, c[2] + r[2] * d.z * k)


def patch(lib, name, c, r, d, au, av, m, parent, k=1.008, rings=6, seg=32):
    """A marking that hugs an ellipsoid: disc around direction d, angular radii au (sideways), av (up)."""
    d, u, v = _basis(d)
    verts, faces = [on(c, r, d, k)], []
    for i in range(1, rings + 1):
        rho = i / rings
        kk = k if i < rings else 0.985
        for j in range(seg):
            phi = 2 * math.pi * j / seg
            ang = rho * au * av / math.hypot(av * math.cos(phi), au * math.sin(phi))
            s = d * math.cos(ang) + (u * math.cos(phi) + v * math.sin(phi)) * math.sin(ang)
            verts.append(on(c, r, s, kk))
    for j in range(seg):
        faces.append((0, 1 + j, 1 + (j + 1) % seg))
    for i in range(1, rings):
        a, b = 1 + (i - 1) * seg, 1 + i * seg
        for j in range(seg):
            faces.append((a + j, b + j, b + (j + 1) % seg, a + (j + 1) % seg))
    return lib.from_verts(name, verts, faces, m, parent, subsurf=0)


def blade(L, W):
    """Feather/leaf outline in XZ: base at the origin, tip at (0, L)."""
    return [(-W * .3, 0), (W * .3, 0), (W * .5, L * .35), (W * .42, L * .7), (0, L), (-W * .42, L * .7), (-W * .5, L * .35)]


def build(lib):
    rig = lib.Rig('Featherdash', 'featherdash', 'Ice', height_cm=120, gait='walk', attack='peck')
    tan = lib.mat('fea_tan', '#c98f4a', 0.75)
    brown = lib.mat('fea_brown', '#8c5a2a', 0.75)
    dbrown = lib.mat('fea_dbrown', '#653e1c', 0.75)
    light = lib.mat('fea_light', '#e8b878', 0.75)
    cream = lib.mat('fea_cream', '#f6e6c8', 0.8)
    snow = lib.mat('fea_snow', '#f4fbff', 0.45, sss=0.3)
    snowsh = lib.mat('fea_snowsh', '#c8e4f4', 0.5, sss=0.2)
    ice = lib.mat('fea_ice', '#9fdcf4', 0.15, coat=1.0, emit=0.15, emit_color='#9fdcf4')
    iceD = lib.mat('fea_iceD', '#2a6ac0', 0.15, coat=1.0)
    white = lib.mat('fea_white', '#ffffff', 0.2, emit=1.0)
    red = lib.mat('fea_red', '#e0303a', 0.7)
    redD = lib.mat('fea_redD', '#b81c26', 0.7)
    beakU = lib.mat('fea_beakU', '#f0a020', 0.35, coat=0.4)
    beakL = lib.mat('fea_beakL', '#c87810', 0.35, coat=0.4)
    legm = lib.mat('fea_leg', '#d08a10', 0.45, coat=0.2)
    H = math.pi / 2

    rig.body = lib.pivot('fea_bodyp', (0, 0, 0.8), rig.root)
    bt = lib.pivot('fea_bodyt', (0, 0, 0), rig.body, rot=(-0.14, 0, 0))
    C, R = (0, 0.05, 0), (0.28, 0.44, 0.27)
    lib.sphere('fea_body', C, R, tan, bt, seg=40)
    patch(lib, 'fea_belly', C, R, (0, -0.5, -1), 0.95, 0.75, cream, bt, k=1.01)
    patch(lib, 'fea_back', C, R, (0, 0.4, 1), 0.7, 1.0, brown, bt, k=1.008)
    # snow settling on the back
    patch(lib, 'fea_snow1', C, R, (0.05, 0.45, 1), 0.42, 0.55, snowsh, bt, k=1.016, rings=4, seg=24)
    patch(lib, 'fea_snow1b', C, R, (0.05, 0.42, 1), 0.34, 0.46, snow, bt, k=1.035, rings=4, seg=24)
    patch(lib, 'fea_snow2', C, R, (-0.5, 1.2, 0.8), 0.2, 0.2, snow, bt, k=1.03, rings=3, seg=16)
    patch(lib, 'fea_snow3', C, R, (0.5, -0.3, 1), 0.16, 0.2, snow, bt, k=1.03, rings=3, seg=16)
    lib.sphere('fea_rump', (0, 0.4, 0.08), (0.17, 0.2, 0.14), brown, rig.body, seg=24)

    # ---- neck + head (the pivot is at the base of the neck so pecks swing the whole neck)
    rig.head = lib.pivot('fea_headp', (0, -0.3, 0.12), rig.body)
    lib.tube('fea_neck', [(0, 0.04, -0.08), (0, -0.07, 0.2), (0, -0.12, 0.44)], [0.19, 0.12, 0.11], tan, rig.head)
    HC, HR = (0, -0.15, 0.52), (0.2, 0.21, 0.195)
    lib.sphere('fea_head', HC, HR, tan, rig.head, seg=40)
    patch(lib, 'fea_face', HC, HR, (0, -1, -0.5), 0.6, 0.45, light, rig.head, k=1.008)
    patch(lib, 'fea_capsh', HC, HR, (0, 0.1, 1), 1.12, 1.12, snowsh, rig.head, k=1.012)
    patch(lib, 'fea_cap', HC, HR, (0, 0.1, 1), 1.0, 1.0, snow, rig.head, k=1.04)
    for i, (dx, L) in enumerate([(0, 0.13), (-0.05, 0.09), (0.05, 0.1)]):
        b = (dx, HC[1] + 0.04, HC[2] + HR[2] - 0.02)
        lib.tube(f'fea_tuft{i}', [b, (dx * 1.5, b[1] + 0.03, b[2] + L * 0.6), (dx * 2.4, b[1] + 0.12, b[2] + L)],
                 [0.045, 0.032, 0.006], snow, rig.head)
    for sx, nm in ((-1, 'L'), (1, 'R')):
        look = Vector((sx * 0.78, -0.62, 0.08)).normalized()
        ec = Vector(on(HC, HR, look, 0.97))
        lib.eye('fea_eye' + nm, ec, 0.062, rig.head, iris='#22335a', pupil='#0a0a12', sclera='#141c30', look=look, iris_frac=0.7)
        # faint snowflake hint: four ice flecks around the pupil
        d, u, v = _basis(look)
        for j, (a, b) in enumerate([(1, 0), (-1, 0), (0, 1), (0, -1)]):
            lib.sphere(f'fea_fleck{nm}{j}', ec + d * 0.033 + (u * a + v * b) * 0.036, 0.0065, ice, rig.head, seg=8)
    by = HC[1] - HR[1] + 0.03
    ub = lib.cone('fea_beakU', (0, by - 0.12, HC[2] - 0.012), 0.08, 0.004, 0.28, beakU, rig.head, rot=(H + 0.08, 0, 0), seg=20)
    ub.scale = (1, 0.58, 1)
    rig.jaw = lib.pivot('fea_jaw', (0, by + 0.02, HC[2] - 0.048), rig.head)
    lb = lib.cone('fea_beakL', (0, -0.12, -0.008), 0.07, 0.004, 0.24, beakL, rig.jaw, rot=(H - 0.06, 0, 0), seg=20)
    lb.scale = (1, 0.42, 1)

    # ---- red scarf, one end blowing back
    sc = lib.torus('fea_scarf', (0, -0.07, 0.2), 0.115, 0.065, red, rig.head, rot=(0.38, 0, 0))
    sc.scale = (1, 1, 1.25)
    lib.sphere('fea_knot', (0.03, 0.07, 0.25), (0.07, 0.07, 0.065), redD, rig.head, seg=16)
    sp = lib.pivot('fea_scarfp', (0.03, 0.09, 0.25), rig.head)
    ribbon = [(0, 0.05), (0.18, 0.1), (0.38, 0.17), (0.6, 0.3), (0.52, 0.2), (0.62, 0.14), (0.38, 0.05), (0.18, -0.02), (0, -0.05)]
    lib.extrude_shape('fea_scarfend', ribbon, 0.03, redD, sp, rot=(0, 0, H), bevel=0.008)
    rig.extras.append((sp, 'sway'))

    # ---- folded wings
    for sx, nm in ((-1, 'L'), (1, 'R')):
        w = lib.pivot('fea_wing' + nm, (sx * 0.225, -0.05, 0.1), rig.body, rot=(0, -sx * 0.06, 0))
        lib.sphere('fea_wingm' + nm, (sx * 0.02, 0.2, -0.09), (0.055, 0.32, 0.16), brown, w, rot=(-0.2, 0, 0), seg=24)
        for i, (y, z, L, a) in enumerate([(0.32, -0.17, 0.3, -1.8), (0.37, -0.11, 0.32, -1.62), (0.37, -0.05, 0.26, -1.45)]):
            f = lib.extrude_shape(f'fea_wingf{nm}{i}', blade(L, 0.11), 0.022, dbrown, w, loc=(sx * 0.06, y, z), bevel=0.006)
            f.rotation_mode = 'ZYX'
            f.rotation_euler = (a, 0, H)
        lib.sphere('fea_wingsnow' + nm, (sx * 0.035, 0.24, 0.035), (0.045, 0.2, 0.04), snow, w, rot=(-0.2, 0, 0), seg=16)
        rig.wings.append((w, sx))

    # ---- long tail with three icy eye-spots
    t0 = lib.pivot('fea_tail0', (0, 0.44, 0.1), rig.body)
    lib.sphere('fea_tailroot', (0, 0.05, 0.02), (0.13, 0.16, 0.08), brown, t0, seg=20)
    t1 = lib.pivot('fea_tail1', (0, 0.1, 0.03), t0)
    for i, (yaw, pitch, roll, L, m) in enumerate([(0, 0.62, 0, 0.82, tan), (-0.5, 0.25, -0.75, 0.74, brown), (0.5, 0.25, 0.75, 0.74, brown)]):
        f = lib.extrude_shape(f'fea_tailf{i}', blade(L, 0.26), 0.03, m, t1, loc=(0, -0.05, 0), rot=(-H + pitch, roll, yaw), bevel=0.01)
        z = L * 0.68
        lib.sphere(f'fea_spot{i}', (0, 0, z), (0.085, 0.026, 0.085), ice, f, seg=20)
        lib.sphere(f'fea_spotc{i}', (0, 0, z), (0.036, 0.034, 0.036), iceD, f, seg=16)
        for s in (-1, 1):
            lib.sphere(f'fea_spoth{i}{s}', (-0.03, s * 0.027, z + 0.03), (0.014, 0.006, 0.014), white, f, seg=8)
        lib.tube(f'fea_quill{i}', [(0, 0, 0.02), (0, 0, z - 0.09)], [0.014, 0.008], dbrown, f, seg=8)
    rig.tail = [t0, t1]

    # ---- long running legs
    for i, sx in enumerate((-1, 1)):
        leg = lib.pivot(f'fea_leg{i}', (sx * 0.13, 0.08, -0.14), rig.body)
        lib.sphere(f'fea_thigh{i}', (0, 0, -0.04), (0.1, 0.12, 0.16), tan, leg, seg=20)
        g = -0.66 + 0.028
        lib.tube(f'fea_legm{i}', [(0, 0, -0.1), (0, 0.06, -0.36), (0, 0, g)], [0.04, 0.03, 0.028], legm, leg, seg=8)
        for j, (tx, ty) in enumerate([(0, -0.2), (-0.1, -0.16), (0.1, -0.16), (0, 0.1)]):
            lib.tube(f'fea_toe{i}{j}', [(0, 0, g), (tx * 0.5, ty * 0.5, g + 0.014), (tx, ty, g - 0.004)], [0.028, 0.025, 0.014], legm, leg, seg=8)
        rig.legs.append((leg, i * 0.5))

    rig.attack_origin = (0, -0.95, 1.42)
    rig.t_pose = {'fea_wingL': (0, 1.35, 0), 'fea_wingR': (0, -1.35, 0)}
    return rig
