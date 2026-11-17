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


def fuzz(m, sheen=0.6, tint=(1.0, 0.9, 0.75)):
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Sheen Roughness'].default_value = 0.45
    b.inputs['Sheen Tint'].default_value = (*tint, 1)
    return m


def crystal(lib, name, r, h, m, parent, loc=(0, 0, 0)):
    """Faceted ice shard along local Z (flat shaded), sharp at +Z."""
    vs = [(0, 0, h), (r, 0, 0), (0, r, 0), (-r, 0, 0), (0, -r, 0), (0, 0, -h * 0.45)]
    fs = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    o = lib.from_verts(name, vs, fs, m, parent, loc=loc, subsurf=0)
    for p in o.data.polygons:
        p.use_smooth = False
    return o


THIGH, SHANK = 0.27, 0.48
FOOT = [(-0.035, 0.07), (-0.11, -0.13), (-0.075, -0.17), (-0.02, -0.06), (-0.02, -0.21), (0.02, -0.21), (0.02, -0.06),
        (0.075, -0.17), (0.11, -0.13), (0.035, 0.07), (0.015, 0.12), (-0.015, 0.12)]


def build(lib):
    rig = lib.Rig('Featherdash', 'featherdash', 'Ice', height_cm=120, gait='walk', attack='peck')
    cold = (0.85, 0.95, 1.0)
    tan = fuzz(lib.mat('fea_tan', '#c98f4a', 0.7, sss=0.1))
    brown = fuzz(lib.mat('fea_brown', '#8c5a2a', 0.7, sss=0.06))
    dbrown = fuzz(lib.mat('fea_dbrown', '#653e1c', 0.65, coat=0.15), 0.4)
    light = fuzz(lib.mat('fea_light', '#e8b878', 0.7, sss=0.12))
    cream = fuzz(lib.mat('fea_cream', '#f6e6c8', 0.75, sss=0.2))
    snow = fuzz(lib.mat('fea_snow', '#f4fbff', 0.4, sss=0.35, emit=0.06, emit_color='#dff2ff'), 0.8, cold)
    snowsh = fuzz(lib.mat('fea_snowsh', '#c0e0f4', 0.45, sss=0.25), 0.6, cold)
    ice = lib.mat('fea_ice', '#9fdcf4', 0.08, coat=1.0, emit=0.35, emit_color='#9fdcf4', sss=0.2)
    spot = lib.mat('fea_spot', '#9fdcf4', 0.08, coat=1.0, emit=0.5, emit_color='#8fe0ff')
    iceD = lib.mat('fea_iceD', '#2a6ac0', 0.1, coat=1.0, emit=0.2, emit_color='#2a6ac0')
    print_m = lib.mat('fea_print', '#bfeaff', 0.05, coat=1.0, emit=0.5, emit_color='#9fdcf4')
    white = lib.mat('fea_white', '#ffffff', 0.2, emit=2.0)
    red = lib.mat('fea_red', '#e0303a', 0.75, sss=0.1)
    redD = lib.mat('fea_redD', '#b81c26', 0.75, sss=0.1)
    redL = lib.mat('fea_redL', '#ff6a6a', 0.75)
    for m in (red, redD, redL):
        fuzz(m, 0.5, (1, 0.7, 0.7))
    beakU = lib.mat('fea_beakU', '#f6a820', 0.22, coat=1.0, sss=0.1)
    beakL = lib.mat('fea_beakL', '#c87810', 0.25, coat=1.0)
    legm = lib.mat('fea_leg', '#e09418', 0.35, coat=0.6, sss=0.1)
    H = math.pi / 2

    # frozen footprints it has left behind (they stay on the ground)
    for i, (x, y, a) in enumerate([(-0.15, 0.55, 0.15), (0.17, 0.95, -0.1)]):
        lib.extrude_shape(f'fea_print{i}', FOOT, 0.012, print_m, rig.root, loc=(x, y, 0.008), rot=(H, 0, a), bevel=0.004)

    rig.body = lib.pivot('fea_bodyp', (0, 0, 0.9), rig.root)
    bt = lib.pivot('fea_bodyt', (0, 0, 0), rig.body, rot=(-0.16, 0, 0))
    C, R = (0, 0.06, 0), (0.3, 0.5, 0.29)
    lib.sphere('fea_body', C, R, tan, bt, seg=40)
    patch(lib, 'fea_belly', C, R, (0, -0.5, -1), 0.95, 0.75, cream, bt, k=1.01)
    patch(lib, 'fea_back', C, R, (0, 0.4, 1), 0.7, 1.0, brown, bt, k=1.008)
    # snow settling on the back, with a bluish edge
    patch(lib, 'fea_snow1', C, R, (0.05, 0.45, 1), 0.44, 0.58, snowsh, bt, k=1.016, rings=4, seg=24)
    patch(lib, 'fea_snow1b', C, R, (0.05, 0.42, 1), 0.35, 0.48, snow, bt, k=1.04, rings=4, seg=24)
    for i, (d, a) in enumerate([((-0.5, 1.2, 0.8), 0.2), ((0.5, -0.3, 1), 0.16), ((-0.45, 0.1, 1), 0.13), ((0.4, 1.4, 0.6), 0.12)]):
        patch(lib, f'fea_snowp{i}', C, R, d, a, a * 1.2, snow, bt, k=1.03, rings=3, seg=16)
    lib.sphere('fea_rump', (0, 0.44, 0.1), (0.18, 0.22, 0.15), brown, rig.body, seg=24)
    # chest feathers puffing out over the scarf line
    for i, (x, z, r) in enumerate([(-0.35, 0.25, 0.1), (0.35, 0.25, 0.1), (0, 0.12, 0.12)]):
        lib.sphere(f'fea_chest{i}', on(C, R, (x, -1, z), 0.86), (r, r * 0.8, r * 1.1), tan, bt, seg=14)

    # ---- neck (rig.head, pivot at the base so pecks swing the whole neck) and skull (nods)
    rig.head = lib.pivot('fea_headp', (0, -0.3, 0.12), rig.body)
    lib.tube('fea_neck', [(0, 0.12, -0.14), (0, 0.0, 0.08), (0, -0.09, 0.3), (0, -0.12, 0.52)], [0.25, 0.18, 0.125, 0.12], tan, rig.head)
    rig.skull = lib.pivot('fea_skull', (0, -0.12, 0.46), rig.head)
    HC, HR = (0, -0.04, 0.12), (0.215, 0.225, 0.21)
    sk = rig.skull
    lib.sphere('fea_head', HC, HR, tan, sk, seg=40)
    patch(lib, 'fea_face', HC, HR, (0, -1, -0.5), 0.65, 0.5, light, sk, k=1.008)
    patch(lib, 'fea_capsh', HC, HR, (0, 0.1, 1), 1.12, 1.12, snowsh, sk, k=1.012)
    patch(lib, 'fea_cap', HC, HR, (0, 0.1, 1), 1.0, 1.0, snow, sk, k=1.045)
    rig.tuft = lib.pivot('fea_tuftp', (0, HC[1] + 0.03, HC[2] + HR[2] - 0.03), sk)
    for i, (dx, L) in enumerate([(0, 0.2), (-0.055, 0.13), (0.055, 0.15)]):       # frosty swept-back crest
        lib.tube(f'fea_tuft{i}', [(dx, 0, 0), (dx * 1.5, 0.05, L * 0.6), (dx * 2.2, 0.2, L)], [0.05, 0.036, 0.004], snow, rig.tuft)
    rig.eyes = []
    for sx, nm in ((-1, 'L'), (1, 'R')):
        look = Vector((sx * 0.7, -0.7, 0.06)).normalized()
        ec = Vector(on(HC, HR, (sx * 0.66, -0.74, 0.1), 0.935))
        e = lib.eye('fea_eye' + nm, ec, 0.082, sk, iris='#3f78c8', pupil='#0a0a12', sclera='#10182c', look=look, iris_frac=0.78, flat=0.42)
        e.scale = (0.95, 1, 1.1)
        for j in range(4):                                             # faint snowflake hint: four ice flecks round the pupil
            a = j * H
            lib.sphere(f'fea_fleck{nm}{j}', (math.cos(a) * 0.04, -0.034, math.sin(a) * 0.04), (0.007, 0.004, 0.007), ice, e, seg=8)
        # a keen little brow ridge
        b0, b1 = Vector(on(HC, HR, (sx * 0.95, -0.4, 0.5), 1.0)), Vector(on(HC, HR, (sx * 0.4, -0.95, 0.42), 1.01))
        lib.tube('fea_brow' + nm, [b0, (b0 + b1) / 2 + Vector((sx * 0.012, -0.012, 0.008)), b1], [0.01, 0.022, 0.016], brown, sk, seg=8)
        rig.eyes.append(e)
    by = HC[1] - HR[1] + 0.035
    ub = lib.cone('fea_beakU', (0, by - 0.15, HC[2] - 0.025), 0.085, 0.003, 0.36, beakU, sk, rot=(H + 0.07, 0, 0), seg=20, subsurf=1)
    ub.scale = (1, 0.6, 1)
    rig.jaw = lib.pivot('fea_jaw', (0, by + 0.02, HC[2] - 0.062), sk)
    lb = lib.cone('fea_beakL', (0, -0.15, -0.008), 0.075, 0.003, 0.31, beakL, rig.jaw, rot=(H - 0.05, 0, 0), seg=20, subsurf=1)
    lb.scale = (1, 0.42, 1)

    # ---- red scarf wrapped round the base of the neck, one end streaming back on a 3-joint chain
    sc = lib.torus('fea_scarf', (0, 0.015, 0.11), 0.165, 0.062, red, rig.head, rot=(0.42, 0, 0))
    sc.scale = (1, 1, 1.5)
    sc2 = lib.torus('fea_scarfhi', (0, 0.012, 0.135), 0.172, 0.022, redL, rig.head, rot=(0.42, 0, 0))
    lib.sphere('fea_knot', (0.05, 0.19, 0.2), (0.075, 0.07, 0.07), redD, rig.head, seg=16)
    seg_len = 0.2
    rig.scarf = []
    par, at = rig.head, (0.05, 0.2, 0.2)
    for i in range(3):
        sp = lib.pivot(f'fea_scarf{i}', at, par, rot=(0.25, 0, 0) if i == 0 else (0, 0, 0))
        w0, w1 = 0.055 + i * 0.012, 0.067 + i * 0.012
        if i < 2:
            rib = [(-0.02, w0), (seg_len + 0.02, w1), (seg_len + 0.02, -w1), (-0.02, -w0)]
        else:
            rib = [(-0.02, w0), (seg_len + 0.06, w1 + 0.02), (seg_len - 0.02, 0), (seg_len + 0.06, -w1 - 0.02), (-0.02, -w0)]
        lib.extrude_shape(f'fea_scarfm{i}', rib, 0.028, redD if i % 2 == 0 else red, sp, rot=(0, 0, H), bevel=0.008)
        rig.scarf.append(sp)
        par, at = sp, (0, seg_len, 0)
    rig.extras.append((rig.scarf[0], 'sway'))

    # ---- folded wings
    for sx, nm in ((-1, 'L'), (1, 'R')):
        w = lib.pivot('fea_wing' + nm, (sx * 0.245, -0.05, 0.1), rig.body, rot=(0, -sx * 0.06, 0))
        lib.sphere('fea_wingm' + nm, (sx * 0.02, 0.22, -0.09), (0.058, 0.35, 0.17), brown, w, rot=(-0.2, 0, 0), seg=24)
        lib.sphere('fea_wingbar' + nm, (sx * 0.052, 0.17, -0.07), (0.03, 0.2, 0.05), light, w, rot=(-0.2, 0, 0), seg=16)
        for i, (y, z, L, a) in enumerate([(0.3, -0.21, 0.3, -1.95), (0.36, -0.16, 0.34, -1.78), (0.4, -0.1, 0.34, -1.62), (0.4, -0.04, 0.28, -1.45)]):
            f = lib.extrude_shape(f'fea_wingf{nm}{i}', blade(L, 0.11), 0.022, dbrown, w, loc=(sx * 0.062, y, z), bevel=0.006)
            f.rotation_mode = 'ZYX'
            f.rotation_euler = (a, 0, H)
        lib.sphere('fea_wingsnow' + nm, (sx * 0.04, 0.24, 0.04), (0.045, 0.22, 0.04), snow, w, rot=(-0.2, 0, 0), seg=16)
        rig.wings.append((w, sx))

    # ---- long tail: three paddle feathers, each with an ice-blue eye spot, each on its own pivot so they can fan
    t0 = lib.pivot('fea_tail0', (0, 0.5, 0.12), rig.body)
    lib.sphere('fea_tailroot', (0, 0.04, 0.01), (0.13, 0.17, 0.085), brown, t0, seg=20)
    t1 = lib.pivot('fea_tail1', (0, 0.1, 0.02), t0)
    rig.tfeathers = []
    rig.tf_rest = [(0.42, 0, 0), (0.12, -0.85, -0.42), (0.12, 0.85, 0.42)]
    for i, (L, m) in enumerate([(0.95, tan), (0.84, brown), (0.84, brown)]):
        fp = lib.pivot(f'fea_tf{i}', (0, -0.02, 0.006 * (i == 0)), t1, rot=rig.tf_rest[i])
        out = [(-0.03, 0), (0.03, 0), (0.045, L * .4), (0.12, L * .6), (0.155, L * .78), (0.1, L * .94), (0, L),
               (-0.1, L * .94), (-0.155, L * .78), (-0.12, L * .6), (-0.045, L * .4)]
        f = lib.extrude_shape(f'fea_tailf{i}', out, 0.03, m, fp, rot=(-H, 0, 0), bevel=0.01)
        z = L * 0.77
        lib.sphere(f'fea_spotr{i}', (0, 0, z), (0.125, 0.021, 0.125), snow, f, seg=20)
        lib.sphere(f'fea_spot{i}', (0, 0, z), (0.1, 0.027, 0.1), spot, f, seg=20)
        lib.sphere(f'fea_spotc{i}', (0, 0, z), (0.045, 0.034, 0.045), iceD, f, seg=16)
        for sd in (-1, 1):
            lib.sphere(f'fea_spoth{i}{sd}', (-0.035, sd * 0.03, z + 0.035), (0.017, 0.006, 0.017), white, f, seg=8)
        lib.tube(f'fea_quill{i}', [(0, 0, 0.02), (0, 0, z - 0.12)], [0.016, 0.008], dbrown, f, seg=8)
        rig.tfeathers.append(fp)
    rig.tail = [t0, t1]

    # ---- long running legs: hip (feathered drumstick) -> knee (shank) -> foot
    rig.knees, rig.feet = [], []
    for i, sx in enumerate((-1, 1)):
        leg = lib.pivot(f'fea_leg{i}', (sx * 0.14, 0.1, -0.12), rig.body)
        lib.tube(f'fea_thigh{i}', [(0, 0.02, 0.06), (0, 0.0, -0.1), (0, 0, -THIGH - 0.02)], [0.12, 0.115, 0.045], tan, leg, seg=12)
        lib.sphere(f'fea_frill{i}', (0, 0, -THIGH + 0.05), (0.07, 0.07, 0.035), snow, leg, seg=12)       # frosty cuff
        knee = lib.pivot(f'fea_knee{i}', (0, 0, -THIGH), leg)
        lib.sphere(f'fea_kneem{i}', (0, 0, 0), 0.042, legm, knee, seg=12)
        lib.tube(f'fea_shank{i}', [(0, 0, 0), (0, 0.012, -SHANK * 0.5), (0, 0, -SHANK)], [0.036, 0.027, 0.03], legm, knee, seg=8)
        foot = lib.pivot(f'fea_foot{i}', (0, 0, -SHANK), knee)
        for j, (tx, ty) in enumerate([(0, -0.22), (-0.11, -0.17), (0.11, -0.17), (0, 0.1)]):
            lib.tube(f'fea_toe{i}{j}', [(0, 0, 0), (tx * 0.5, ty * 0.5, 0.012), (tx, ty, -0.012)], [0.03, 0.026, 0.012], legm, foot, seg=8)
        rig.legs.append((leg, i * 0.5)); rig.knees.append(knee); rig.feet.append(foot)

    rig.attack_origin = (0, -0.95, 1.5)
    rig.t_pose = {'fea_wingL': (0, 1.35, 0), 'fea_wingR': (0, -1.35, 0),
                  'fea_tf0': (0.9, 0, 0), 'fea_tf1': (0.9, 0, -0.7), 'fea_tf2': (0.9, 0, 0.7)}
    return rig
