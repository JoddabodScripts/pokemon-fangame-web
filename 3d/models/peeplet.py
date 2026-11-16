"""Peeplet: tiny brown songbird with a head tuft, cream belly and two-tone beak."""
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
    rig = lib.Rig('Peeplet', 'peeplet', 'Flying', height_cm=15, gait='walk', attack='peck')
    tan = lib.mat('pee_tan', '#d09a4e', 0.75)
    brown = lib.mat('pee_brown', '#a8743a', 0.75)
    dbrown = lib.mat('pee_dbrown', '#7a5228', 0.75)
    light = lib.mat('pee_light', '#f0c888', 0.75)
    cream = lib.mat('pee_cream', '#fff2d8', 0.8)
    beakU = lib.mat('pee_beakU', '#f0a020', 0.35, coat=0.4)
    beakL = lib.mat('pee_beakL', '#c87810', 0.35, coat=0.4)
    legm = lib.mat('pee_leg', '#d08a10', 0.45, coat=0.2)
    pink = lib.mat('pee_cheek', '#ff9a8a', 0.6)
    H = math.pi / 2

    rig.body = lib.pivot('pee_bodyp', (0, 0, 0.44), rig.root)
    bt = lib.pivot('pee_bodyt', (0, 0, 0), rig.body, rot=(-0.22, 0, 0))     # body tilted chest-up
    C, R = (0, 0.04, 0), (0.28, 0.36, 0.27)
    lib.sphere('pee_body', C, R, tan, bt, seg=40)
    patch(lib, 'pee_belly', C, R, (0, -0.55, -1), 0.95, 0.8, cream, bt, k=1.01)
    patch(lib, 'pee_back', C, R, (0, 0.5, 1), 0.75, 0.9, brown, bt, k=1.008)
    # rump blending into the tail
    lib.sphere('pee_rump', (0, 0.3, 0.07), (0.16, 0.2, 0.13), brown, rig.body, seg=24)

    # ---- head
    rig.head = lib.pivot('pee_headp', (0, -0.2, 0.2), rig.body)
    HC, HR = (0, -0.06, 0.17), (0.235, 0.235, 0.225)
    lib.sphere('pee_head', HC, HR, tan, rig.head, seg=40)
    patch(lib, 'pee_cap', HC, HR, (0, 0.35, 1), 0.8, 0.85, brown, rig.head, k=1.008)
    patch(lib, 'pee_face', HC, HR, (0, -1, -0.45), 0.6, 0.45, light, rig.head, k=1.008)
    for sx, nm in ((-1, 'L'), (1, 'R')):
        lib.eye('pee_eye' + nm, on(HC, HR, (sx * 0.72, -0.68, 0.16), 0.97), 0.072, rig.head,
                iris='#2a1a10', pupil='#0a0a0a', sclera='#111111', look=(sx * 0.72, -0.7, 0.1), iris_frac=0.7)
        patch(lib, 'pee_cheek' + nm, HC, HR, (sx * 0.8, -0.6, -0.42), 0.2, 0.14, pink, rig.head, k=1.014, rings=3, seg=16)
    # tuft
    for i, (dx, dy, L) in enumerate([(0, -0.03, 0.2), (-0.03, 0.03, 0.14), (0.035, 0.05, 0.16)]):
        b = (dx, HC[1] + dy, HC[2] + HR[2] - 0.03)
        lib.tube(f'pee_tuft{i}', [b, (b[0] + dx, b[1] + 0.02, b[2] + L * 0.55), (b[0] + dx * 2.5, b[1] + 0.1 + dy, b[2] + L)],
                 [0.04, 0.03, 0.006], brown, rig.head)
    # beak: upper half fixed, lower half on the jaw hinge
    by = HC[1] - HR[1] + 0.035
    ub = lib.cone('pee_beakU', (0, by - 0.1, HC[2] - 0.012), 0.085, 0.004, 0.24, beakU, rig.head, rot=(H + 0.1, 0, 0), seg=20)
    ub.scale = (1, 0.6, 1)
    rig.jaw = lib.pivot('pee_jaw', (0, by + 0.02, HC[2] - 0.05), rig.head)
    lb = lib.cone('pee_beakL', (0, -0.1, -0.008), 0.075, 0.004, 0.2, beakL, rig.jaw, rot=(H - 0.08, 0, 0), seg=20)
    lb.scale = (1, 0.42, 1)

    # ---- folded wings: hinge along the shoulder, they swing out sideways to flap
    for sx, nm in ((-1, 'L'), (1, 'R')):
        w = lib.pivot('pee_wing' + nm, (sx * 0.22, 0.0, 0.1), rig.body, rot=(0, -sx * 0.06, 0))
        lib.sphere('pee_wingm' + nm, (sx * 0.02, 0.14, -0.1), (0.05, 0.25, 0.155), brown, w, rot=(-0.3, 0, 0), seg=24)
        for i, (y, z, L, a) in enumerate([(0.2, -0.16, 0.24, -1.85), (0.24, -0.1, 0.25, -1.65), (0.24, -0.04, 0.2, -1.45)]):
            f = lib.extrude_shape(f'pee_wingf{nm}{i}', blade(L, 0.1), 0.02, dbrown, w, loc=(sx * 0.055, y, z), bevel=0.006)
            f.rotation_mode = 'ZYX'            # turn the blade flat against the side, then swing its tip back
            f.rotation_euler = (a, 0, H)
        rig.wings.append((w, sx))

    # ---- tail
    t0 = lib.pivot('pee_tail0', (0, 0.36, 0.1), rig.body)
    t1 = lib.pivot('pee_tail1', (0, 0.08, 0.03), t0)
    for i, (yaw, L, m) in enumerate([(0, 0.46, brown), (-0.4, 0.4, dbrown), (0.4, 0.4, dbrown)]):
        lib.extrude_shape(f'pee_tailf{i}', blade(L, 0.17), 0.025, m, t1,
                          loc=(0, -0.06, 0.004 * (1 if i == 0 else 0)), rot=(-H + 0.62, 0, yaw), bevel=0.008)
    rig.tail = [t0, t1]

    # ---- legs
    for i, sx in enumerate((-1, 1)):
        leg = lib.pivot(f'pee_leg{i}', (sx * 0.11, 0.06, -0.2), rig.body)
        g = -0.24 + 0.022
        lib.tube(f'pee_legm{i}', [(0, 0, 0.03), (0, 0.01, -0.1), (0, 0, g)], [0.03, 0.022, 0.022], legm, leg, seg=8)
        for j, (tx, ty) in enumerate([(0, -0.15), (-0.08, -0.12), (0.08, -0.12), (0, 0.08)]):
            lib.tube(f'pee_toe{i}{j}', [(0, 0, g), (tx * 0.5, ty * 0.5, g + 0.012), (tx, ty, g - 0.002)], [0.022, 0.02, 0.012], legm, leg, seg=8)
        rig.legs.append((leg, i * 0.5))

    rig.attack_origin = (0, -0.75, 0.8)
    rig.t_pose = {'pee_wingL': (0, 1.35, 0), 'pee_wingR': (0, -1.35, 0)}
    return rig
