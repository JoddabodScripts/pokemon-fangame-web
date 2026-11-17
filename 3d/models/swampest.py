import math
from mathutils import Vector, Matrix


# ---------------------------------------------------------------- local helpers
def _aim(d):
    """Euler that turns local +Z onto direction d."""
    return Vector((0, 0, 1)).rotation_difference(Vector(d).normalized()).to_euler()


def drop(lib, name, r, h, m, parent, loc=(0, 0, 0), d=(0, 0, 1), bend=(0, 0), flat=1.0,
         seg=10, rings=8, base=0.55, subsurf=1):
    """Flame / teardrop growing from `loc` along direction d: widest near the base, thin curved tip."""
    verts = [(0, 0, -r * 0.3)]
    t0 = 0.25
    for i in range(rings):
        t = i / rings
        if t < t0:
            f = base + (1 - base) * math.sin(math.pi / 2 * t / t0)
        else:
            u = (t - t0) / (1 - t0)
            f = (0.5 + 0.5 * math.cos(math.pi * u)) ** 0.8
        ox, oy = bend[0] * t * t, bend[1] * t * t
        for k in range(seg):
            a = 2 * math.pi * k / seg
            verts.append((ox + math.cos(a) * r * f, oy + math.sin(a) * r * f * flat, h * t))
    verts.append((bend[0], bend[1], h))
    tip = len(verts) - 1
    faces = []
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((0, 1 + k2, 1 + k))
        for i in range(rings - 1):
            a, b = 1 + i * seg, 1 + (i + 1) * seg
            faces.append((a + k, a + k2, b + k2, b + k))
        a = 1 + (rings - 1) * seg
        faces.append((a + k, a + k2, tip))
    o = lib.from_verts(name, verts, faces, m, parent, loc, subsurf=subsurf)
    o.rotation_euler = _aim(d)
    return o


def on_ell(c, radii, x, z, lift=1.0):
    """Point on the front (-Y) face of an ellipsoid (center c, radii) at local x, z."""
    q = 1 - (x / radii[0]) ** 2 - (z / radii[2]) ** 2
    y = -radii[1] * math.sqrt(max(q, 0.0))
    return (c[0] + x * lift, c[1] + y * lift, c[2] + z * lift)


def decal(lib, name, outline, c, radii, m, parent, lift=1.012, thick=0.008, n=6, rings=4):
    """A flat marking wrapped onto the front of an ellipsoid. outline = [(x, z)] around the ellipsoid center."""
    pts = []
    for i, (x0, z0) in enumerate(outline):
        x1, z1 = outline[(i + 1) % len(outline)]
        for k in range(n):
            pts.append((x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n))
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    verts = [on_ell(c, radii, cx, cz, lift)]
    N = len(pts)
    for r in range(1, rings + 1):
        s = r / rings
        for x, z in pts:
            verts.append(on_ell(c, radii, cx + (x - cx) * s, cz + (z - cz) * s, lift))
    faces = []
    for k in range(N):
        k2 = (k + 1) % N
        faces.append((0, 1 + k, 1 + k2))
        for r in range(rings - 1):
            a, b = 1 + r * N, 1 + (r + 1) * N
            faces.append((a + k, b + k, b + k2, a + k2))
    return lib.from_verts(name, verts, faces, m, parent, subsurf=0, solidify=thick)


def leaf(lib, name, origin, axis, side, length, width, m, parent, arch=0.0, fold=0.2, n=8, thick=0.012):
    """A leaf from `origin` along `axis`, widening along `side`, with a folded midrib."""
    o, ax, sd = Vector(origin), Vector(axis).normalized(), Vector(side).normalized()
    up = sd.cross(ax).normalized()
    verts, faces = [], []
    for i in range(n + 1):
        t = i / n
        w = width * math.sin(math.pi * (0.04 + 0.93 * t ** 0.75))
        cpt = o + ax * length * t + up * arch * math.sin(math.pi * t * 0.9)
        verts += [tuple(cpt - sd * w + up * w * fold), tuple(cpt), tuple(cpt + sd * w + up * w * fold)]
    for i in range(n):
        a, b = i * 3, (i + 1) * 3
        faces += [(a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1)]
    return lib.from_verts(name, verts, faces, m, parent, subsurf=1, solidify=thick)


def jaw_loft(lib, name, secs, z0, m, parent, K=8, subsurf=2):
    """Half-pipe jaw: sections (y, half_width, z_peak) with a flat face at z0 (the bite plane)."""
    import bmesh
    verts, faces = [], []
    for y, w, zt in secs:
        for k in range(K + 1):
            a = math.pi * k / K
            verts.append((w * math.cos(a), y, z0 + (zt - z0) * math.sin(a) ** 0.7))
    n = K + 1
    for i in range(len(secs) - 1):
        a, b = i * n, (i + 1) * n
        for k in range(K):
            faces.append((a + k, a + k + 1, b + k + 1, b + k))
        faces.append((a + K, a, b, b + K))
    faces.append(tuple(range(n)))
    faces.append(tuple(range((len(secs) - 1) * n, len(secs) * n)))
    o = lib.from_verts(name, verts, faces, m, parent, subsurf=subsurf)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(o.data)
    bm.free()
    return o


def _interp(secs, y):
    """Half width of a jaw at y (linear between sections)."""
    for (y0, w0, _), (y1, w1, _) in zip(secs, secs[1:]):
        if min(y0, y1) <= y <= max(y0, y1):
            t = (y - y0) / (y1 - y0)
            return w0 + (w1 - w0) * t
    return secs[-1][1]


def slit_eye(lib, name, loc, r, parent, look, s, P, iris='#f8e870', brow=None, anger=0.25):
    """Yellow reptile eye with a vertical slit pupil and a brow line. s = side (-1 left, +1 right)."""
    p = lib.pivot(name, loc, parent)
    p.rotation_euler = Vector((0, -1, 0)).rotation_difference(Vector(look).normalized()).to_euler()
    lib.sphere(name + '_ball', (0, 0, 0), (r, r * 0.55, r), lib.mat(P + 'iris', iris, 0.15, coat=1, emit=0.25), p)
    lib.sphere(name + '_slit', (0, -r * 0.47, 0), (r * 0.17, r * 0.14, r * 0.74), lib.mat(P + 'pupil', '#0c0c0c', 0.1, coat=1), p)
    lib.sphere(name + '_shine', (s * r * 0.34, -r * 0.56, r * 0.38), (r * 0.16, r * 0.07, r * 0.16), lib.mat('shine', '#ffffff', 0.1, emit=2), p)
    if brow is not None:
        # local +x points forward on the left eye and backward on the right eye
        f = -s
        lib.tube(name + '_brow', [(f * r * 1.15, -r * 0.5, r * (0.72 - anger)), (0, -r * 0.72, r * 0.98), (-f * r * 1.15, -r * 0.4, r * (0.95 + anger))],
                 [r * 0.16, r * 0.2, r * 0.14], brow, p)
    return p


def scaly(lib, name, groove, c1, c2, scale=17.0, rough=0.3, coat=0.7, sss=0.05, bump=0.35):
    """Wet reptile skin: scale cells with darker grooves, lighter centers and a little relief."""
    m = lib.mat(name, c1, rough, sss=sss, coat=coat)
    nt = m.node_tree
    if 'scales' in nt.nodes:
        return m
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    tex = nt.nodes.new('ShaderNodeTexVoronoi')
    tex.name = 'scales'
    tex.feature = 'DISTANCE_TO_EDGE'
    tex.inputs['Scale'].default_value = scale
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[1].position = 0.0, 0.09
    cr.elements[0].color = (*lib._rgb(groove), 1)
    cr.elements[1].color = (*lib._rgb(c1), 1)
    e = cr.elements.new(0.5)
    e.color = (*lib._rgb(c2), 1)
    nt.links.new(tc.outputs['Object'], tex.inputs['Vector'])
    nt.links.new(tex.outputs['Distance'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    if bump:
        bp = nt.nodes.new('ShaderNodeBump')
        bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = 0.02
        cl = nt.nodes.new('ShaderNodeMath')
        cl.operation = 'MINIMUM'
        cl.inputs[1].default_value = 0.14
        nt.links.new(tex.outputs['Distance'], cl.inputs[0])
        nt.links.new(cl.outputs[0], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def baked_sphere(lib):
    """lib.sphere, but with the radii baked into the mesh so textures keep one scale everywhere."""
    def sph(name, loc, scale=(1, 1, 1), m=None, parent=None, rot=(0, 0, 0), seg=32, subsurf=0):
        o = lib.sphere(name, loc, scale, m, parent, rot, seg, subsurf)
        sc = o.scale.copy()
        o.data.transform(Matrix.Diagonal((sc.x, sc.y, sc.z, 1)))
        o.scale = (1, 1, 1)
        return o
    return sph


def build(lib):
    P = 'swe_'
    rig = lib.Rig('Swampest', 'swampest', 'Grass', height_cm=220, gait='walk', attack='bite')
    R = math.radians
    k = 0.88
    sph = baked_sphere(lib)
    dk = lib.mat(P + 'dk', '#164a2a', 0.4, coat=0.5)
    md = scaly(lib, P + 'md', '#1c6032', '#267a40', '#2e8848', 12, 0.3, 0.8, bump=0.25)
    bs = scaly(lib, P + 'bs', '#2c8040', '#3a9a50', '#46a85a', 9.5, 0.26, 0.9, 0.08, bump=0.25)
    lt = lib.mat(P + 'lt', '#7ccc70', 0.3, coat=0.8, sss=0.1)
    hl = lib.mat(P + 'hl', '#b4ea96', 0.25, coat=0.9, emit=0.2)
    belly = lib.mat(P + 'belly', '#dce4a0', 0.32, sss=0.15, coat=0.7)
    bellydk = lib.mat(P + 'bellydk', '#a8b270', 0.45, coat=0.4)
    mud = lib.mat(P + 'mud', '#5a3d22', 0.22, coat=0.9)
    mossm = lib.mat(P + 'moss', '#4f8a2c', 0.7, sss=0.2)
    mosslt = lib.mat(P + 'mosslt', '#8ab848', 0.7, sss=0.2)
    X = rig.x = dict(tail=[], eyes=[], legs=[], petals=[])
    tooth = lib.mat(P + 'tooth', '#fbfbf0', 0.25, coat=0.6)
    claw = lib.mat(P + 'claw', '#f4f4e8', 0.3, coat=0.5)
    mouth = lib.mat(P + 'mouth', '#6a1424', 0.5)
    tongue = lib.mat(P + 'tongue', '#e06080', 0.4, sss=0.2, coat=0.3)
    petal = lib.mat(P + 'petal', '#f48cc4', 0.3, sss=0.3, coat=0.6)
    petaldk = lib.mat(P + 'petaldk', '#c8508a', 0.5)
    pollen = lib.mat(P + 'pollen', '#ffd84a', 0.4, emit=1.0)
    dark = lib.mat(P + 'dark', '#0e2a18', 0.5)

    rig.body = lib.pivot(P + 'body', (0, 0.12 * k, 0.5 * k), rig.root)
    B = rig.body
    B.scale = (k, k, k)

    # torso
    tc, tr = (0, 0.08, 0.0), (0.35, 0.54, 0.3)
    sph(P + 'torso', tc, tr, bs, B)
    sph(P + 'chest', (0, -0.3, 0.0), (0.32, 0.33, 0.275), bs, B)
    bc, br = (0, 0.03, -0.1), (0.32, 0.55, 0.23)
    sph(P + 'belly', bc, br, belly, B)
    for i in range(7):
        y = -0.42 + i * 0.14
        f = math.sqrt(max(0.05, 1 - ((y - bc[1]) / br[1]) ** 2)) * 1.004
        t = lib.torus(f'{P}bstripe{i}', (0, y, bc[2]), 1.0, 0.012, bellydk, B, rot=(math.pi / 2, 0, 0))
        t.scale = (br[0] * f, br[2] * f, 1.0)
    # back spikes
    for i in range(5):
        y = -0.36 + i * 0.17
        z = tr[2] * math.sqrt(max(0.0, 1 - ((y - tc[1]) / tr[1]) ** 2)) - 0.035
        if y < -0.2:
            z = max(z, 0.215)
        sp = drop(lib, f'{P}ridge{i}', 0.1, 0.25 - 0.02 * abs(i - 1), md, B, (0, y, z), d=(0, 0.25, 1), base=0.9, seg=8, rings=5)
        sp.scale = (0.5, 1, 1)
        sph(f'{P}ridgehl{i}', (0, y + 0.045, z + 0.2 - 0.02 * abs(i - 1)), 0.014, hl, B)
    for j, (y, z) in enumerate([(-0.3, 0.1), (0.05, 0.15), (0.3, 0.06), (-0.12, -0.02)]):
        for s in (-1, 1):
            x = tr[0] * math.sqrt(max(0, 1 - ((y - tc[1]) / tr[1]) ** 2 - (z / tr[2]) ** 2))
            if y < -0.2:
                x = max(x, 0.32 * math.sqrt(max(0, 1 - ((y + 0.3) / 0.33) ** 2 - (z / 0.275) ** 2)))
            sph(f'{P}fleck{j}{s}', (s * x, y, z), (0.013, 0.04, 0.03), hl, B)
    # moss hanging from the belly
    for j, (x, y, L) in enumerate([(-0.27, -0.22, 0.16), (0.28, -0.05, 0.19), (-0.29, 0.12, 0.2), (0.27, 0.3, 0.16),
                                   (-0.24, 0.36, 0.14), (0.25, -0.3, 0.14), (-0.28, -0.05, 0.13), (0.28, 0.14, 0.13)]):
        q = 1 - (x / br[0]) ** 2 - ((y - bc[1]) / br[1]) ** 2
        z = bc[2] - br[2] * math.sqrt(max(q, 0)) + 0.03
        L = min(L, (0.5 + z) - 0.02)
        drop(lib, f'{P}moss{j}', 0.05, L, mossm if j % 2 else mosslt, B, (x, y, z), d=(0, 0, -1), bend=(0.03, 0.02), base=0.9, seg=6, rings=5)
        drop(lib, f'{P}mossb{j}', 0.035, L * 0.6, mosslt if j % 2 else mossm, B, (x * 0.93, y + 0.06, z), d=(0, 0, -1), bend=(-0.02, 0.02), base=0.9, seg=6, rings=5)

    # thick clawed legs
    for (nm, s, y, ph) in (('FL', -1, -0.33, 0.0), ('FR', 1, -0.33, 0.5), ('BL', -1, 0.4, 0.5), ('BR', 1, 0.4, 0.0)):
        lp = lib.pivot(P + 'leg' + nm, (s * 0.26, y, -0.1), B)
        sph(P + 'hip' + nm, (0, 0, 0.01), (0.175, 0.215, 0.2), bs, lp)
        lib.tube(P + 'legm' + nm, [(0, 0, 0), (s * 0.07, 0, -0.12), (s * 0.1, -0.01, -0.25), (s * 0.1, -0.02, -0.35)],
                 [0.15, 0.14, 0.12, 0.115], bs, lp)
        sph(P + 'foot' + nm, (s * 0.1, -0.08, -0.345), (0.13, 0.18, 0.055), md, lp)
        sph(P + 'fmud' + nm, (s * 0.1, -0.05, -0.345), (0.15, 0.17, 0.045), mud, lp)
        sph(P + 'fmud2' + nm, (s * 0.2, 0.0, -0.3), (0.045, 0.06, 0.05), mud, lp)
        for c in (-1.5, -0.5, 0.5, 1.5):
            lib.cone(f'{P}claw{nm}{c}', (s * 0.1 + c * 0.055, -0.255, -0.365), 0.027, 0.0, 0.09, claw, lp,
                     rot=_aim((c * 0.18, -1, -0.12)), seg=10)
        X['legs'].append((lp, s, ph, y < 0))
        rig.legs.append((lp, ph))

    # head: jaws wide open at rest
    rig.head = lib.pivot(P + 'head', (0, -0.56, 0.08), B)
    H = rig.head
    H.scale = (1.3, 1.3, 1.3)
    sph(P + 'neck', (0, 0.04, -0.04), (0.25, 0.2, 0.22), bs, H)
    sph(P + 'skull', (0, -0.1, 0.03), (0.235, 0.22, 0.19), bs, H)
    sph(P + 'throat', (0, -0.2, -0.045), (0.165, 0.2, 0.1), mouth, H)
    z0 = 0.0
    U = X['upper'] = lib.pivot(P + 'upper', (0, -0.08, -0.03), H, rot=(R(-16), 0, 0))
    up = [(0.0, 0.21, 0.16), (-0.2, 0.2, 0.135), (-0.42, 0.165, 0.095), (-0.62, 0.15, 0.08), (-0.76, 0.15, 0.095), (-0.84, 0.1, 0.05)]
    jaw_loft(lib, P + 'snout', up, z0, bs, U)
    jaw_loft(lib, P + 'palate', [(y, w - 0.03, -0.014) for y, w, _ in up[1:]], 0.01, mouth, U)
    lib.tube(P + 'snoutline', [(0, -0.25, 0.135), (0, -0.45, 0.103), (0, -0.62, 0.089)], [0.02, 0.016, 0.012], lt, U)
    for s in (-1, 1):
        sph(f'{P}nosb{s}', (s * 0.06, -0.75, 0.078), (0.045, 0.05, 0.03), bs, U)
        sph(f'{P}nos{s}', (s * 0.066, -0.775, 0.098), (0.017, 0.02, 0.012), dark, U)
        sph(f'{P}browb{s}', (s * 0.13, -0.13, 0.175), (0.115, 0.135, 0.105), bs, H)
        X['eyes'].append(slit_eye(lib, f'{P}eye{s}', (s * 0.205, -0.185, 0.195), 0.09, H, (s * 0.8, -0.65, 0.12), s, P, iris='#f8d040', brow=dk, anger=0.45))

    rig.jaw = lib.pivot(P + 'jaw', (0, -0.08, -0.03), H, rot=(R(24), 0, 0))
    J = rig.jaw
    lo = [(0.05, 0.2, -0.13), (-0.14, 0.195, -0.12), (-0.36, 0.16, -0.1), (-0.56, 0.145, -0.085), (-0.69, 0.14, -0.08), (-0.75, 0.09, -0.05)]
    jaw_loft(lib, P + 'jawm', lo, 0.0, md, J)
    jaw_loft(lib, P + 'bed', [(y, w - 0.03, 0.014) for y, w, _ in lo[1:]], -0.01, mouth, J)
    tg = lib.tube(P + 'tongue', [(0, -0.12, 0), (0, -0.3, 0.02), (0, -0.48, 0.01), (0, -0.58, 0)], [0.085, 0.09, 0.075, 0.05], tongue, J)
    tg.scale = (1, 1, 0.4)
    tg.location = (0, 0, 0.022)
    lib.tube(P + 'tongueline', [(0, -0.2, 0.062), (0, -0.4, 0.058), (0, -0.54, 0.04)], [0.006, 0.007, 0.004], lib.mat(P + 'tgdk', '#b8406a', 0.5), J)

    # mud-soaked jaws: a smear under the chin and drips hanging off it
    sph(P + 'jmud', (0, -0.5, -0.07), (0.125, 0.24, 0.035), mud, J)
    for q, (x, y, L) in enumerate([(-0.09, -0.62, 0.11), (0.07, -0.5, 0.15), (-0.04, -0.38, 0.09), (0.1, -0.68, 0.08)]):
        drop(lib, f'{P}jdrip{q}', 0.03, L, mud, J, (x, y, -0.075), d=(0, 0.35, -1), base=0.9, seg=6, rings=5)
    sph(P + 'smud', (0.07, -0.66, 0.085), (0.06, 0.08, 0.02), mud, U, rot=(0, R(25), 0))

    # rows of teeth
    n = 8
    for i in range(n):
        yu = -0.15 - i * 0.084
        for s in (-1, 1):
            w = _interp(up, yu) - 0.018
            big = 1.25 if i in (2, 6) else 1.0
            lib.cone(f'{P}tu{i}{s}', (s * w, yu, -0.03 * big), 0.026 * big, 0.0, 0.09 * big, tooth, U, rot=(math.pi, 0, 0), seg=10)
            yl = yu + 0.04
            w2 = _interp(lo, yl) - 0.018
            if i < n - 1:
                lib.cone(f'{P}tl{i}{s}', (s * w2, yl, 0.03), 0.025, 0.0, 0.085, tooth, J, seg=10)
    for s in (-1, 1):
        lib.cone(f'{P}tuf{s}', (s * 0.05, -0.82, -0.028), 0.024, 0.0, 0.08, tooth, U, rot=(math.pi, 0, 0), seg=10)
        lib.cone(f'{P}tlf{s}', (s * 0.045, -0.725, 0.026), 0.022, 0.0, 0.075, tooth, J, seg=10)

    # tail rising like a tall neck, flower on top
    prev, ploc = B, (0, 0.5, 0.02)
    lens = [0.2, 0.19, 0.19, 0.18, 0.17, 0.16]
    rads = [0.24, 0.215, 0.19, 0.17, 0.15, 0.135, 0.115]
    curl = [38, 24, 18, 10, 6, 6]
    for i in range(6):
        tp = lib.pivot(f'{P}tail{i}', ploc, prev, rot=(R(curl[i]), 0, 0))
        sph(f'{P}tailj{i}', (0, 0, 0), rads[i], bs, tp)
        lib.tube(f'{P}tailm{i}', [(0, 0, 0), (0, lens[i] / 2, 0), (0, lens[i], 0)],
                 [rads[i], (rads[i] + rads[i + 1]) / 2, rads[i + 1]], bs, tp)
        sph(f'{P}tailhl{i}', (0, lens[i] * 0.5, rads[i] * 0.93), (0.03, 0.05, 0.012), lt, tp)
        X['tail'].append(tp)
        if i % 2 == 0:
            rig.tail.append(tp)
        rig.t_pose[tp.name] = (R(50) if i == 0 else R(4), 0, 0)
        prev, ploc = tp, (0, lens[i], 0)
    sph(P + 'tailtop', (0, lens[-1], 0), rads[-1], bs, prev)
    # in the last link's frame: +Y is up, +Z is forward
    top = (0, lens[-1] + 0.06, 0.02)
    for s, m_ in ((-1, lt), (1, md)):
        leaf(lib, f'{P}leaf{s}', (0, lens[-1] + 0.03, 0), (s * 1, 0.25, 0.15), (0, 0.2, s * 1), 0.4, 0.12, m_, prev, arch=-0.05 * s)
    F = X['flower'] = lib.pivot(P + 'flower', top, prev, rot=(R(-125), 0, 0))
    F.scale = (1.3, 1.3, 1.3)
    lib.tube(P + 'fstem', [(0, 0.1, 0), (0, 0.04, 0), (0, 0.0, 0)], [0.05, 0.045, 0.04], md, F)
    for q in range(5):
        a = q * 2 * math.pi / 5
        # each petal hinges at the flower's center: rotating its pivot +X folds it shut
        pp = lib.pivot(f'{P}petalp{q}', (0, -0.01, 0), F, rot=(0, a, 0))
        X['petals'].append(pp)
        pt = [(0, 0, 0.02), (0.085, -0.012, 0.1), (0.11, -0.03, 0.2), (0.06, -0.05, 0.28), (0, -0.06, 0.305), (-0.06, -0.05, 0.28),
              (-0.11, -0.03, 0.2), (-0.085, -0.012, 0.1), (0, 0.012, 0.16)]
        lib.from_verts(f'{P}petal{q}', pt, [(0, 1, 8, 7), (1, 2, 8), (2, 3, 4, 8), (8, 4, 5, 6), (8, 6, 7)], petal, pp, subsurf=2, solidify=0.022)
        sph(f'{P}petalt{q}', (0, -0.05, 0.262), (0.04, 0.014, 0.03), petaldk, pp, rot=(R(12), 0, 0))
        lib.tube(f'{P}petalv{q}', [(0, -0.012, 0.06), (0, -0.005, 0.15), (0, -0.04, 0.24)], [0.007, 0.006, 0.003], petaldk, pp, seg=8)
    sph(P + 'pollen', (0, -0.035, 0), (0.07, 0.045, 0.07), pollen, F)
    for q in range(6):
        a = q * math.pi / 3
        sph(f'{P}stamen{q}', (0.045 * math.sin(a), -0.075, 0.045 * math.cos(a)), 0.014, lib.mat(P + 'pol2', '#f08a20', 0.4, emit=0.4), F, seg=10)
    rig.extras.append((F, 'sway'))

    rig.attack_origin = (0, -1.2, 0.55)
    return rig


def animate(A):
    """Swampest: bursts out of a mud mound with its flower shut, blooms and roars, lumbers across with
    heavy dusty footfalls, then Bog Chomp: jaws wide, a lunge, a crushing snap that explodes mud and
    leaves on the opponent, and a head-thrash before letting go."""
    import anim_kit as K
    from anim_kit import E, spring, decay
    from mathutils import Vector
    r, T, s, lib = A.rig, A.T, A.size, A.lib
    X = r.x
    root, B, H, J = r.root, r.body, r.head, r.jaw
    tail, petals, F = X['tail'], X['petals'], X['flower']
    pi = math.pi
    win = K.win
    D = 1.2 * s
    aim = 0.8
    stride = D / 3.2
    dirv = Vector((math.sin(aim), -math.cos(aim), 0))

    def walk_x(f):
        return D * E(f, 80, 130)

    A.key(root, 0, scale=0.001)
    A.key(root, T['OUT'] - 1, scale=0.001)
    for f in range(T['OUT'], T['END'] + 1):
        # ------------------------------------------------ root
        rise = -1.1 * s * (1 - spring((f - 21) / 10, 4, 7)) if f < 40 else 0
        x = walk_x(f)
        yaw = (pi / 2) * win(f, 72, 80, 130, 138) + aim * win(f, 141, 149, 176, 184)
        crouch = win(f, 141, 150, 151, 153)
        lunge = win(f, 152, 156, 172, 180)
        kb = win(f, 186, 190, 202, 214)
        off = dirv * (0.55 * s * lunge - 0.08 * s * crouch - 0.3 * s * kb)
        A.key(root, f, loc=(x + off.x, off.y, rise), rot=(0, 0, yaw - 0.2 * kb), scale=1.0)

        # ------------------------------------------------ weights
        W = win(f, 78, 84, 126, 132)
        th = 2 * pi * walk_x(f) / stride
        cry = win(f, 39, 42, 46, 48)
        breathe = math.sin(2 * pi * f / 30)
        thrash = win(f, 159, 162, 170, 174)
        hitw = decay(f, 186, 6, 1.0)
        roar = win(f, 214, 218, 224, 228)

        # ------------------------------------------------ body: heavy sway, crouch, lunge
        A.key(B, f, loc=(0.03 * s * math.sin(th) * W, 0, -0.06 * s * crouch - 0.03 * s * abs(math.sin(th)) * W + 0.008 * s * breathe),
              rot=(-0.12 * cry + 0.14 * crouch - 0.1 * lunge + 0.08 * kb, 0.08 * math.sin(th) * W + 0.12 * hitw, 0.06 * math.sin(th) * W),
              scale=(1 + 0.02 * breathe, 1, 1 + 0.025 * breathe))
        for lp, sd, ph, front in X['legs']:
            p_ = th + 2 * pi * ph
            sw = 0.5 * math.sin(p_) * W
            lift = max(0, -math.cos(p_)) * 0.25 * W
            brace = (0.35 if front else -0.2) * crouch + (-0.3 if front else 0.25) * lunge
            A.key(lp, f, rot=(sw + brace + (0.3 if front else -0.2) * kb, -sd * (0.25 * W * lift + 0.2 * crouch), 0))

        # ------------------------------------------------ tail: drags while walking, whips on the chomp
        for i, tp in enumerate(tail):
            sway = 0.12 * math.sin(2 * pi * f / 36 - i * 0.5) * (1 - W) + 0.18 * math.sin(th - 0.7 - i * 0.5) * W
            whip = 0.35 * math.sin((f - 160) * 0.9 - i * 0.6) * thrash
            droop = -0.25 * win(f, 186, 190, 204, 214) + 0.1 * roar - 0.15 * (1 - E(f, 30, 40))
            A.key(tp, f, rot=(droop + 0.06 * cry, 0, sway + whip))

        # ------------------------------------------------ head and jaw (jaw rests 24 deg open)
        look = win(f, 52, 56, 66, 70) * math.sin(2 * pi * (f - 52) / 18)
        A.key(H, f, rot=(-0.4 * cry - 0.3 * crouch + 0.15 * lunge - 0.3 * roar + 0.2 * hitw + 0.02 * breathe,
                         0.25 * math.sin((f - 160) * 1.4) * thrash, 0.3 * look - 0.08 * math.sin(th) * W + 0.25 * kb))
        gape = 0.75 * cry + 0.8 * crouch + 0.8 * win(f, 152, 154, 157, 158) + 0.7 * roar + 0.3 * win(f, 186, 188, 194, 200)
        snap = -0.42 * win(f, 158, 159, 172, 176)            # fully shut around the opponent
        chew = 0.05 * max(0, breathe) * (1 - W)
        A.key(J, f, rot=(gape + snap + chew, 0, 0))
        blink = max(win(f, x0, x0 + 1, x0 + 2, x0 + 4) for x0 in (55, 67, 110, 188))
        for e in X['eyes']:
            A.key(e, f, scale=(1, 1, 1 - max(0.9 * blink, 0.35 * crouch, 0.3 * W)))

        # ------------------------------------------------ flower: shut, blooms, shuts when hurt, re-blooms
        shut = (1 - spring((f - 37) / 8, 4, 9)) if f < 60 else 0
        hurt = win(f, 187, 190, 206, 214)
        bloom2 = spring((f - 212) / 8, 4, 9) if f >= 212 else 0
        for q, pp in enumerate(petals):
            fold = 1.4 * max(shut, 0) + 1.1 * hurt * (1 - bloom2) - 0.15 * thrash - 0.1 * win(f, 141, 146, 156, 160)
            A.key(pp, f, rot=(fold + 0.05 * math.sin(f * 0.2 + q), 0, 0))
        A.key(F, f, rot=(0.15 * math.sin(2 * pi * f / 40) + 0.3 * thrash * math.sin(f * 0.8), 0, 0.1 * math.sin(2 * pi * f / 52)))

    # ---------------------------------------------------- send-out: mud mound and clods
    mud = lib.mat('swe_fx_mud', '#5a3a1e', 0.75)
    mudw = lib.mat('swe_fx_mudw', '#4a3018', 0.25, coat=0.6)
    mound = lib.pivot('swe_fx_mound')
    lib.sphere('swe_fx_moundm', (0, 0, 0), (1.0, 1.2, 0.35), mud, mound, seg=24)
    for f, sc in [(0, 0.001), (15, 0.001), (18, 0.7), (22, 1.0), (30, 0.9), (40, 0.4), (46, 0.001)]:
        A.key(mound, f, loc=(0, -0.1 * s, 0), scale=sc * s * 0.45 if sc > 0.001 else 0.001, absolute=True)
    K.burst(A, 'swe_fx_clod', (0, -0.1 * s, 0.3 * s), 24, n=16, dur=16, speed=1.2, up=0.9, size=0.05, mat=mud, seed=2)
    pollen = lib.mat('swe_fx_pollen', '#ffd84a', 0.3, emit=3.0)
    fl = A.world(F, 40)
    K.burst(A, 'swe_fx_pollen', fl, 40, n=14, dur=18, speed=0.5, up=0.4, gravity=0.3, size=0.02, mat=pollen, seed=1)
    A.light('swe_fx_bloomlight', '#ffd84a', fl, [(0, 0), (38, 0), (42, 250 * s * s), (52, 0)])

    # ---------------------------------------------------- walk: dust puffs on footfalls
    dust = lib.mat('swe_fx_dust', '#c9b98d', 0.9, alpha=0.7)
    for i, f0 in enumerate(range(86, 128, 10)):
        p = A.world(root, f0)
        K.ring(A, f'swe_fx_dust{i}', (p.x + 0.2 * s * (1 if i % 2 else -1), p.y + 0.25 * s, 0.03), f0, dur=10, r0=0.05, r1=0.35, thick=0.07, mat=dust)

    # ---------------------------------------------------- Bog Chomp
    here = A.world(root, 140)
    tgt = A.world(root, 159) + dirv * 0.8 * s      # right at the snapping jaws
    tgt.z = 0.25 * s
    for i in range(6):   # bog bubbles at its feet while it winds up
        a = i * 1.05
        c = here + Vector((math.cos(a) * 0.55 * s, math.sin(a) * 0.45 * s, 0.03))
        K.flash_sphere(A, f'swe_fx_bub{i}', c, 142 + i * 2, dur=7, r1=0.07, mat=mudw)
    K.burst(A, 'swe_fx_bogA', tgt, 159, n=20, dur=18, speed=1.3, up=1.0, size=0.06, mat=mud, seed=4)
    K.burst(A, 'swe_fx_bogB', tgt, 160, n=12, dur=20, speed=1.0, up=1.2, gravity=0.8, size=0.05,
            mat=lib.mat('swe_fx_leaf', '#5fbf4a', 0.4, coat=0.4), shape='leaf', seed=7)
    K.ring(A, 'swe_fx_bogring', (tgt.x, tgt.y, 0.03), 159, dur=14, r0=0.2, r1=1.4, thick=0.08, mat=mudw)
    K.spikes(A, 'swe_fx_bogspike', tgt, 160, n=6, dur=16, height=0.5, mat=mudw, radius=0.4, seed=3)
    K.flash_sphere(A, 'swe_fx_bite', tgt + Vector((0, 0, 0.3 * s)), 158, dur=6, r1=0.16, mat=lib.mat("swe_fx_flash", '#f0ffc0', 0.3, emit=5))
    A.light('swe_fx_chomplight', '#c8ff7a', tgt + Vector((0, 0, 0.6 * s)), [(0, 0), (157, 0), (159, 800 * s * s), (170, 0)])
    # roar at the end shakes pollen loose
    fl2 = A.world(F, 216)
    K.burst(A, 'swe_fx_pollen2', fl2, 216, n=10, dur=16, speed=0.5, up=0.5, gravity=0.3, size=0.02, mat=pollen, seed=5)


# Phase speeds for render.retime: above 1 is slower and longer, below 1 is quicker.
TIMING = {'send': 1.5, 'idle': 1.6, 'walk': 1.5, 'attack': 1.5, 'hit': 1.3, 'recover': 1.4}
