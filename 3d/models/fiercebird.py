"""Fiercebird: huge snowy eagle with spiky ice-blue wings, red scarf and a snowflake eye."""
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


def crystal(lib, name, loc, r, h, m, parent, rot=(0, 0, 0)):
    """Faceted ice diamond (flat shaded)."""
    vs = [(0, 0, h), (r, 0, 0), (0, r * .7, 0), (-r, 0, 0), (0, -r * .7, 0), (0, 0, -h)]
    fs = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    o = lib.from_verts(name, vs, fs, m, parent, loc=loc, subsurf=0)
    o.rotation_euler = rot
    for p in o.data.polygons:
        p.use_smooth = False
    return o


def flake_eye(lib, name, loc, r, look, parent):
    """Pale eye with a six-armed snowflake for an iris."""
    look = Vector(look).normalized()
    p = lib.pivot(name, loc, parent)
    p.rotation_euler = Vector((0, -1, 0)).rotation_difference(look).to_euler()
    pale = lib.mat('fie_eyepale', '#cfeeff', 0.15, coat=1.0, emit=0.25)
    blue = lib.mat('fie_eyeblue', '#1e5ab8', 0.2, coat=1.0)
    lib.sphere(name + '_w', (0, 0, 0), (r, r * 0.5, r), pale, p)
    for k in range(3):
        lib.box(name + f'_arm{k}', (0, -r * 0.43, 0), (r * 1.45, r * 0.16, r * 0.15), blue, p, rot=(0, k * math.pi / 3, 0), bevel=r * 0.03)
    lib.sphere(name + '_c', (0, -r * 0.5, 0), (r * 0.24, r * 0.1, r * 0.24), lib.mat('fie_eyedark', '#0c1c40', 0.1, coat=1), p, seg=12)
    lib.sphere(name + '_s', (-r * 0.3, -r * 0.56, r * 0.32), (r * 0.13, r * 0.06, r * 0.13), lib.mat('fie_shine', '#ffffff', 0.1, emit=2), p, seg=8)
    return p


def build(lib):
    rig = lib.Rig('Fiercebird', 'fiercebird', 'Ice', height_cm=550, gait='fly', attack='cast')
    w3 = lib.mat('fie_w3', '#4f8fc0', 0.35, coat=0.6, sss=0.08)
    w2 = lib.mat('fie_w2', '#86c0e8', 0.35, coat=0.6, sss=0.08)
    w1 = lib.mat('fie_w1', '#c4e8f8', 0.35, coat=0.6, sss=0.1)
    tipm = lib.mat('fie_tip', '#ffffff', 0.3, coat=0.8, emit=0.35, emit_color='#dff6ff')
    body = lib.mat('fie_body', '#f6fbff', 0.45, sss=0.25, coat=0.25)
    shade = lib.mat('fie_shade', '#d0e6f4', 0.45, sss=0.25, coat=0.25)
    scal = lib.mat('fie_scal', '#e2f0fa', 0.45, sss=0.2, coat=0.3)
    ye = lib.mat('fie_ye', '#f0b828', 0.3, coat=0.5)
    yeD = lib.mat('fie_yeD', '#c08810', 0.3, coat=0.5)
    claw = lib.mat('fie_claw', '#333338', 0.3, coat=0.5)
    ice = lib.mat('fie_ice', '#7fd8ff', 0.08, coat=1.0, emit=0.9, emit_color='#7fd8ff')
    red = lib.mat('fie_red', '#e0303a', 0.7)
    redD = lib.mat('fie_redD', '#b81c26', 0.7)
    browm = lib.mat('fie_brow', '#1c2a4a', 0.5)
    H = math.pi / 2

    rig.body = lib.pivot('fie_bodyp', (0, 0, 1.02), rig.root)
    bt = lib.pivot('fie_bodyt', (0, 0, 0), rig.body, rot=(0.1, 0, 0))
    C, R = (0, 0, 0), (0.38, 0.35, 0.52)
    lib.sphere('fie_body', C, R, body, bt, seg=40)
    patch(lib, 'fie_belly', C, R, (0.25, -0.8, -1), 0.6, 0.75, shade, bt, k=1.008)
    # scalloped chest feathers
    for row, (z, n) in enumerate([(0.0, 4), (-0.22, 5), (-0.44, 4), (-0.64, 3)]):
        for q in range(n):
            x = (q - (n - 1) / 2) * 0.17
            lib.sphere(f'fie_sc{row}{q}', on(C, R, (x, -1, z), 0.97), (0.085, 0.04, 0.06), scal, bt, seg=12)
    # chest fluff under the scarf
    for i, (x, z, s) in enumerate([(-0.2, 0.3, 0.14), (0.2, 0.3, 0.14), (0, 0.26, 0.15)]):
        lib.sphere(f'fie_fluff{i}', on(C, R, (x, -0.8, z), 0.9), (s, s * 0.8, s * 1.2), body, bt, seg=16)
    # column of ice beads down the chest
    for i, z in enumerate([-0.02, -0.24, -0.46, -0.68]):
        lib.sphere(f'fie_bead{i}', on(C, R, (0, -1, z), 1.05), 0.072 - i * 0.005, ice, bt, seg=20)

    # ---- red scarf, one end hanging down the chest
    sc = lib.torus('fie_scarf', (0, -0.04, 0.42), 0.25, 0.1, red, bt, rot=(0.12, 0, 0))
    sc.scale = (1, 1, 1.15)
    lib.sphere('fie_knot', (0.2, -0.26, 0.4), (0.1, 0.08, 0.1), redD, bt, seg=16)
    sp = lib.pivot('fie_scarfp', (0.2, -0.3, 0.38), bt, rot=(-0.17, 0, -0.08))
    ribbon = [(-0.085, 0), (0.085, 0), (0.12, -0.56), (0.08, -0.5), (0.04, -0.6), (0, -0.5), (-0.04, -0.6), (-0.08, -0.5), (-0.12, -0.56)]
    lib.extrude_shape('fie_scarfend', ribbon, 0.035, redD, sp, bevel=0.008)
    rig.extras.append((sp, 'sway'))

    # ---- head
    rig.head = lib.pivot('fie_headp', (0, -0.08, 0.44), rig.body)
    HC, HR = (0, -0.04, 0.27), (0.3, 0.3, 0.29)
    lib.sphere('fie_head', HC, HR, body, rig.head, seg=40)
    patch(lib, 'fie_nape', HC, HR, (0, 1, 0.1), 0.9, 0.8, shade, rig.head, k=1.006)
    # frosty crest sweeping back
    for i, (y, L, a, wd) in enumerate([(-0.1, 0.5, -0.25, 0.2), (0.05, 0.42, -0.75, 0.19), (0.17, 0.3, -1.2, 0.17)]):
        f = lib.extrude_shape(f'fie_crest{i}', blade(L, wd), 0.07, w1, rig.head, loc=(0, HC[1] + y, HC[2] + HR[2] - 0.07), bevel=0.012)
        f.rotation_mode = 'ZYX'
        f.rotation_euler = (a, 0, H)
    # hooked beak (upper) and lower jaw
    z0 = HC[2] - 0.03
    ub = lib.tube('fie_beakU', [(0, -0.24, z0), (0, -0.44, z0 + 0.01), (0, -0.58, z0 - 0.05), (0, -0.6, z0 - 0.2)],
                  [0.13, 0.115, 0.085, 0.01], ye, rig.head)
    ub.scale = (0.85, 1, 1)
    rig.jaw = lib.pivot('fie_jaw', (0, -0.28, z0 - 0.09), rig.head)
    lb = lib.cone('fie_beakL', (0, -0.1, -0.012), 0.09, 0.01, 0.22, yeD, rig.jaw, rot=(H - 0.05, 0, 0), seg=20)
    lb.scale = (1, 0.45, 1)
    # snowflake eyes under angry brows
    for sx, nm in ((-1, 'L'), (1, 'R')):
        look = (sx * 0.6, -0.8, 0.08)
        flake_eye(lib, 'fie_eye' + nm, on(HC, HR, look, 0.96), 0.118, look, rig.head)
        b0, b1 = Vector(on(HC, HR, (sx * 0.95, -0.5, 0.52), 1.03)), Vector(on(HC, HR, (sx * 0.2, -1, 0.2), 1.06))
        lib.tube('fie_brow' + nm, [b0, (b0 + b1) / 2 + Vector((sx * 0.02, -0.03, 0.0)), b1], [0.02, 0.042, 0.034], browm, rig.head, seg=8)

    # ---- big spiky wings, spread in the XZ plane; hinge at the shoulder
    spikes = [(58, 1.5), (42, 1.75), (24, 1.6), (6, 1.42), (-12, 1.25), (-30, 1.1), (-48, 0.95)]
    for sx, nm in ((-1, 'L'), (1, 'R')):
        w = lib.pivot('fie_wing' + nm, (sx * 0.3, 0.12, 0.2), rig.body, rot=(0, 0, sx * 0.22))
        for li, (m, k, yoff, wd) in enumerate([(w3, 1.0, 0.03, 0.52), (w2, 0.72, -0.01, 0.48), (w1, 0.47, -0.05, 0.42)]):
            for fi, (a, L) in enumerate(spikes):
                ang = sx * (H - math.radians(a + li * 3))
                lib.extrude_shape(f'fie_wf{nm}{li}{fi}', blade(L * k, wd * 0.82), 0.035, m, w, loc=(sx * 0.02, yoff, 0),
                                  rot=(0, ang, 0), bevel=0.01)
                if li == 0:   # frosty white tip on each primary feather
                    tl = L * k
                    tip = lib.extrude_shape(f'fie_wt{nm}{fi}', blade(0.22 * tl, wd * 0.5), 0.04, tipm, w,
                                            loc=(sx * 0.02 + math.sin(ang) * tl * 0.78, yoff - 0.005, math.cos(ang) * tl * 0.78),
                                            rot=(0, ang, 0), bevel=0.008)
        for ci in range(6):   # covert feathers near the shoulder
            a = math.radians(70 - ci * 26)
            ang = sx * (H - a)
            lib.extrude_shape(f'fie_cv{nm}{ci}', blade(0.42, 0.24), 0.05, w1 if ci % 2 else body, w,
                              loc=(sx * 0.05, -0.08, 0.02), rot=(0, ang, 0), bevel=0.015)
        lib.sphere('fie_shoulder' + nm, (sx * 0.1, -0.1, 0.0), (0.2, 0.1, 0.17), body, w, seg=20)
        for ci, (cx, cz, r) in enumerate([(0.62, 0.02, 0.11), (0.8, -0.3, 0.095), (1.02, 0.2, 0.08), (0.48, -0.42, 0.075)]):
            crystal(lib, f'fie_cry{nm}{ci}', (sx * cx, -0.11, cz), r, r * 1.6, ice, w, rot=(0, 0, sx * 0.3))
        rig.wings.append((w, sx))

    # ---- tail fan
    t0 = lib.pivot('fie_tail0', (0, 0.16, -0.38), rig.body)
    for i, (fan, L, m, y) in enumerate([(-0.45, 0.66, w3, 0), (0.45, 0.66, w3, 0), (0, 0.56, w2, -0.03)]):
        f = lib.extrude_shape(f'fie_tailf{i}', blade(L, 0.3), 0.035, m, t0, loc=(0, y, 0.05), bevel=0.01)
        f.rotation_mode = 'YXZ'
        f.rotation_euler = (0.35, math.pi + fan, 0)
    rig.tail = [t0]

    # ---- legs with yellow talons
    for i, sx in enumerate((-1, 1)):
        leg = lib.pivot(f'fie_leg{i}', (sx * 0.18, -0.02, -0.36), rig.body)
        lib.sphere(f'fie_thigh{i}', (0, 0, -0.06), (0.14, 0.15, 0.2), body, leg, seg=20)
        for q in range(5):
            a = q * 2 * math.pi / 5
            lib.sphere(f'fie_fluffL{i}{q}', (0.12 * math.cos(a), 0.12 * math.sin(a), -0.2), (0.07, 0.07, 0.09), scal, leg, seg=10)
        g = -0.66 + 0.04
        lib.tube(f'fie_legm{i}', [(0, 0, -0.15), (0, 0.02, -0.4), (0, 0, g)], [0.06, 0.045, 0.045], ye, leg, seg=8)
        for j, (tx, ty) in enumerate([(0, -0.24), (-0.13, -0.19), (0.13, -0.19), (0, 0.13)]):
            lib.tube(f'fie_toe{i}{j}', [(0, 0, g), (tx * 0.5, ty * 0.5, g + 0.03), (tx, ty, g)], [0.045, 0.042, 0.03], ye, leg, seg=8)
            lib.tube(f'fie_claw{i}{j}', [(tx, ty, g), (tx * 1.2, ty * 1.2, g + 0.015), (tx * 1.38, ty * 1.38, g - 0.035)], [0.03, 0.022, 0.003], claw, leg, seg=8)
        rig.legs.append((leg, i * 0.5))

    rig.attack_origin = (0, -0.75, 1.7)
    rig.t_pose = {'fie_wingL': (0, 0, 0), 'fie_wingR': (0, 0, 0)}   # flat in the XZ plane, back-sweep removed
    return rig
