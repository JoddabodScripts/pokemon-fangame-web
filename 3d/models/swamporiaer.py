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


def lily_pad(lib, name, r, m, parent, loc, rot, notch=0.5, n=20):
    verts, faces = [(0, 0, 0)], []
    for k in range(n + 1):
        a = notch / 2 + (2 * math.pi - notch) * k / n
        w = 1 + 0.04 * math.sin(a * 5)
        verts.append((math.cos(a) * r * w, math.sin(a) * r * w, 0.012 * math.sin(a * 3)))
    for k in range(n):
        faces.append((0, 1 + k, 2 + k))
    o = lib.from_verts(name, verts, faces, m, parent, loc, subsurf=1, solidify=0.012)
    o.rotation_euler = rot
    return o


def build(lib):
    P = 'swo_'
    rig = lib.Rig('Swamporiaer', 'swamporiaer', 'Grass', height_cm=150, gait='walk', attack='bite')
    R = math.radians
    k = 0.85
    sph = baked_sphere(lib)
    dk = lib.mat(P + 'dk', '#1d5233', 0.4, coat=0.5)
    md = scaly(lib, P + 'md', '#247238', '#2f8a46', '#389650', 13, 0.3, 0.8, bump=0.2)
    bs = scaly(lib, P + 'bs', '#368f4a', '#45a856', '#52b560', 11, 0.26, 0.9, 0.08, bump=0.2)
    lt = lib.mat(P + 'lt', '#8fd67c', 0.3, coat=0.8, sss=0.1)
    hl = lib.mat(P + 'hl', '#c8f0a8', 0.25, coat=0.9, emit=0.2)
    belly = lib.mat(P + 'belly', '#e2e8a8', 0.32, sss=0.15, coat=0.7)
    bellydk = lib.mat(P + 'bellydk', '#b2bc78', 0.45, coat=0.4)
    padm = lib.mat(P + 'pad', '#58b04a', 0.3, coat=0.8, sss=0.2)
    padv = lib.mat(P + 'padv', '#3a8a3a', 0.4)
    budm = lib.mat(P + 'bud', '#f6a8cc', 0.4, sss=0.3, coat=0.4)
    dew = lib.mat(P + 'dew', '#d8f4ff', 0.03, coat=1.0, emit=0.3, transmission=0.6)
    X = rig.x = dict(tail=[], eyes=[], legs=[])
    tooth = lib.mat(P + 'tooth', '#fbfbf0', 0.25, coat=0.6)
    claw = lib.mat(P + 'claw', '#f4f4e8', 0.3, coat=0.5)
    mouth = lib.mat(P + 'mouth', '#6a1424', 0.5)
    tongue = lib.mat(P + 'tongue', '#e06080', 0.45, sss=0.2)
    sun = lib.mat(P + 'sun', '#e8c838', 0.3, emit=0.5, coat=0.6)
    sunlt = lib.mat(P + 'sunlt', '#f8e870', 0.3, emit=1.0, coat=0.6)
    X['sun'] = (sun, sunlt)
    dark = lib.mat(P + 'dark', '#12301e', 0.5)

    rig.body = lib.pivot(P + 'body', (0, 0.1 * k, 0.45 * k), rig.root)
    B = rig.body
    B.scale = (k, k, k)

    # torso
    tc, tr = (0, 0.1, 0.0), (0.3, 0.56, 0.26)
    sph(P + 'torso', tc, tr, bs, B)
    sph(P + 'chest', (0, -0.3, -0.005), (0.27, 0.32, 0.235), bs, B)
    bc, br = (0, 0.05, -0.085), (0.275, 0.56, 0.2)
    sph(P + 'belly', bc, br, belly, B)
    for i in range(7):
        y = -0.4 + i * 0.14
        f = math.sqrt(max(0.05, 1 - ((y - bc[1]) / br[1]) ** 2)) * 1.004
        t = lib.torus(f'{P}bstripe{i}', (0, y, bc[2]), 1.0, 0.012, bellydk, B, rot=(math.pi / 2, 0, 0))
        t.scale = (br[0] * f, br[2] * f, 1.0)
    # back ridges
    for i in range(7):
        y = -0.36 + i * 0.145
        z = tr[2] * math.sqrt(max(0.0, 1 - ((y - tc[1]) / tr[1]) ** 2)) - 0.03
        if y < -0.2:
            z = max(z, 0.19)
        h = 0.17 - 0.012 * abs(i - 2)
        h *= 1.15
        sp = drop(lib, f'{P}ridge{i}', 0.08, h, md, B, (0, y, z), d=(0, 0.25, 1), flat=1.0, base=0.9, seg=8, rings=5)
        sp.scale = (0.5, 1, 1)
        sph(f'{P}ridgehl{i}', (0, y + h * 0.2, z + h * 0.8), (0.011, 0.02, 0.03), hl, B, rot=(R(-14), 0, 0))
    # a lily pad with a bud stuck to its wet back, and a few water drops
    lily_pad(lib, P + 'lily', 0.15, padm, B, (-0.165, 0.33, 0.185), (R(8), R(-40), R(160)))
    lib.tube(P + 'lilyv', [(-0.165, 0.33, 0.2), (-0.24, 0.28, 0.14)], [0.006, 0.003], padv, B, seg=8)
    drop(lib, P + 'lilybud', 0.04, 0.1, budm, B, (-0.13, 0.37, 0.2), d=(-0.5, 0.2, 1), base=0.8, seg=8, rings=6)
    for j, (x, y, z, r_) in enumerate([(0.17, -0.2, 0.19, 0.022), (0.21, 0.3, 0.17, 0.018), (-0.2, -0.05, 0.19, 0.02), (0.1, 0.45, 0.2, 0.015)]):
        sph(f'{P}dew{j}', (x, y, z), (r_, r_, r_ * 0.7), dew, B, seg=12)
    # scale flecks
    for j, (y, z) in enumerate([(-0.3, 0.1), (-0.1, 0.15), (0.38, 0.1), (0.5, 0.02), (-0.2, -0.0)]):
        for s in (-1, 1):
            x = tr[0] * math.sqrt(max(0, 1 - ((y - tc[1]) / tr[1]) ** 2 - (z / tr[2]) ** 2))
            if y < -0.2:
                x = max(x, 0.27 * math.sqrt(max(0, 1 - ((y + 0.3) / 0.32) ** 2 - (z / 0.235) ** 2)))
            sph(f'{P}fleck{j}{s}', (s * x, y, z), (0.012, 0.035, 0.028), hl, B)
    # sun spot on each side
    for s in (-1, 1):
        def side(y, z, lift=0.0):
            x = tr[0] * math.sqrt(max(0, 1 - ((y - tc[1]) / tr[1]) ** 2 - (z / tr[2]) ** 2))
            return (s * (x + lift), y, z)
        cy, cz = 0.14, 0.035
        sph(f'{P}sun{s}', side(cy, cz, -0.004), (0.02, 0.085, 0.085), sun, B)
        sph(f'{P}sunin{s}', side(cy, cz, 0.004), (0.016, 0.055, 0.055), sunlt, B)
        for q in range(8):
            a = q * math.pi / 4
            y, z = cy + math.cos(a) * 0.125, cz + math.sin(a) * 0.125
            sph(f'{P}ray{s}{q}', side(y, z, -0.004), (0.012, 0.03, 0.014), sun, B, rot=(a, 0, 0))

    # legs
    for (nm, s, y, ph) in (('FL', -1, -0.32, 0.0), ('FR', 1, -0.32, 0.5), ('BL', -1, 0.42, 0.5), ('BR', 1, 0.42, 0.0)):
        lp = lib.pivot(P + 'leg' + nm, (s * 0.22, y, -0.1), B)
        sph(P + 'hip' + nm, (s * 0.0, 0, 0.01), (0.14, 0.17, 0.16), bs, lp)
        lib.tube(P + 'legm' + nm, [(0, 0, 0), (s * 0.07, 0, -0.1), (s * 0.1, -0.01, -0.22), (s * 0.1, -0.02, -0.31)],
                 [0.115, 0.105, 0.088, 0.085], bs, lp)
        sph(P + 'foot' + nm, (s * 0.1, -0.07, -0.305), (0.1, 0.15, 0.045), md, lp)
        for c in (-1, 0, 1):
            lib.cone(f'{P}claw{nm}{c}', (s * 0.1 + c * 0.055, -0.215, -0.322), 0.024, 0.0, 0.08, claw, lp,
                     rot=_aim((c * 0.25, -1, -0.12)), seg=10)
        X['legs'].append((lp, s, ph, y < 0))
        rig.legs.append((lp, ph))

    # head
    rig.head = lib.pivot(P + 'head', (0, -0.55, 0.04), B)
    H = rig.head
    H.scale = (1.18, 1.18, 1.18)
    sph(P + 'neck', (0, 0.02, -0.02), (0.24, 0.2, 0.21), bs, H)
    sph(P + 'skull', (0, -0.12, 0.03), (0.235, 0.22, 0.18), bs, H)
    z0 = -0.03
    up = [(0.0, 0.21, 0.15), (-0.2, 0.195, 0.125), (-0.42, 0.16, 0.085), (-0.62, 0.145, 0.07), (-0.76, 0.145, 0.085), (-0.84, 0.1, 0.045)]
    jaw_loft(lib, P + 'snout', up, z0, bs, H)
    sph(P + 'palate', (0, -0.42, z0 - 0.004), (0.1, 0.36, 0.012), mouth, H)
    for s in (-1, 1):
        sph(f'{P}nosb{s}', (s * 0.06, -0.75, 0.068), (0.045, 0.05, 0.03), bs, H)
        sph(f'{P}nos{s}', (s * 0.066, -0.775, 0.088), (0.017, 0.02, 0.012), dark, H)
        sph(f'{P}browb{s}', (s * 0.13, -0.15, 0.165), (0.11, 0.125, 0.1), bs, H)
        X['eyes'].append(slit_eye(lib, f'{P}eye{s}', (s * 0.2, -0.205, 0.185), 0.088, H, (s * 0.8, -0.65, 0.12), s, P, brow=dk))
    # light stripe along the top of the snout
    lib.tube(P + 'snoutline', [(0, -0.25, 0.122), (0, -0.45, 0.092), (0, -0.62, 0.078)], [0.02, 0.016, 0.012], lt, H)

    # lower jaw
    rig.jaw = lib.pivot(P + 'jaw', (0, -0.08, z0), H)
    J = rig.jaw
    lo = [(0.05, 0.2, -0.125), (-0.14, 0.19, -0.115), (-0.36, 0.155, -0.095), (-0.56, 0.14, -0.08), (-0.69, 0.135, -0.075), (-0.75, 0.09, -0.05)]
    jaw_loft(lib, P + 'jawm', lo, 0.0, md, J)
    sph(P + 'bed', (0, -0.36, 0.004), (0.095, 0.34, 0.012), mouth, J)
    sph(P + 'tongue', (0, -0.36, 0.01), (0.065, 0.24, 0.016), tongue, J)

    # interlocking teeth: upper ones point down, lower ones point up
    n = 8
    for i in range(n):
        yu = -0.16 - i * 0.082
        for s in (-1, 1):
            w = _interp(up, yu) - 0.014
            lib.cone(f'{P}tu{i}{s}', (s * w, yu, z0 - 0.025), 0.021, 0.0, 0.07, tooth, H, rot=(math.pi, 0, 0), seg=10)
            yl = yu - 0.041 + 0.08          # in jaw space
            w2 = _interp(lo, yl) - 0.014
            if i < n - 1:
                lib.cone(f'{P}tl{i}{s}', (s * w2, yl, 0.022), 0.02, 0.0, 0.064, tooth, J, seg=10)
    for s in (-1, 1):
        lib.cone(f'{P}tuf{s}', (s * 0.045, -0.825, z0 - 0.022), 0.02, 0.0, 0.06, tooth, H, rot=(math.pi, 0, 0), seg=10)

    # tail curling up and over
    prev, ploc = B, (0, 0.52, 0.0)
    lens = [0.2, 0.19, 0.18, 0.17, 0.15, 0.13, 0.11, 0.09]
    rads = [0.185, 0.17, 0.15, 0.13, 0.11, 0.09, 0.072, 0.055, 0.035]
    curl = [15, 20, 30, 38, 42, 45, 45, 40]
    for i in range(8):
        tp = lib.pivot(f'{P}tail{i}', ploc, prev, rot=(R(curl[i]), 0, 0))
        sph(f'{P}tailj{i}', (0, 0, 0), rads[i], bs, tp)
        lib.tube(f'{P}tailm{i}', [(0, 0, 0), (0, lens[i] / 2, 0), (0, lens[i], 0)],
                 [rads[i], (rads[i] + rads[i + 1]) / 2, rads[i + 1]], bs, tp)
        if i < 5:
            sp = drop(lib, f'{P}tridge{i}', 0.05 - i * 0.005, 0.11 - i * 0.012, md, tp, (0, lens[i] * 0.5, rads[i] * 0.8),
                      d=(0, 0.25, 1), base=0.9, seg=8, rings=5)
            sp.scale = (0.5, 1, 1)
        X['tail'].append(tp)
        if i % 2 == 0:
            rig.tail.append(tp)
        rig.t_pose[tp.name] = (R(8) if i == 0 else R(4), 0, 0)
        prev, ploc = tp, (0, lens[i], 0)
    sph(P + 'tailtip', (0, lens[-1], 0), rads[-1], lt, prev)

    rig.attack_origin = (0, -1.2, 0.4)
    return rig


# ---------------------------------------------------------------- animation
def animate(A):
    """Swamporiaer: surfaces from a swamp pool eyes first, stalks in two creeping bursts with a
    freeze in between, and lashes the opponent with two vines called up by its sun spot (Vine Whip)."""
    r, T, s, lib = A.rig, A.T, A.size, A.lib
    X = r.x
    root, B, H, J = r.root, r.body, r.head, r.jaw
    tail = X['tail']
    pi = math.pi
    E = lambda f, a, b: A.ease((f - a) / (b - a))                     # noqa: E731
    win = lambda f, a, b, c, d: E(f, a, b) * (1 - E(f, c, d))          # noqa: E731

    def spring(t, k=5.0, w=9.0):
        return 0.0 if t <= 0 else 1 - math.exp(-k * t) * math.cos(w * t)

    D = 1.15 * s
    aim = 0.8
    stride = D / 3.0
    dirv = Vector((2.6, -1.8, 0)).normalized()                          # toward the opponent
    A.key(root, 0, scale=0.001)
    A.key(root, T['OUT'] - 1, scale=0.001)

    def walk_x(f):
        return D * (0.5 * E(f, 80, 101) + 0.5 * E(f, 110, 131))

    for f in range(T['OUT'], T['END'] + 1):
        # ------------------------------------------------ root
        # send-out: hidden under the pool, rises to a lurk (eyes and ridges only), then surges out
        rise = -1.15 + 0.63 * E(f, 18, 27) + 0.52 * spring((f - 34) / 9, 5, 7)
        if f >= 47:
            rise = 0
        lurk_y = 0.25 - 0.25 * E(f, 20, 40)
        x = walk_x(f)
        yaw = (pi / 2) * win(f, 72, 82, 130, 138) + aim * win(f, 140, 147, 174, 184)
        wind = win(f, 142, 149, 150, 153)
        thrust = max(win(f, 158, 161, 163, 166), win(f, 165, 167, 169, 174))
        kb = win(f, 186, 191, 207, 217)
        off = dirv * (-0.1 * s * wind + 0.1 * s * thrust - 0.22 * s * kb)
        A.key(root, f, loc=(x + off.x, off.y + lurk_y, rise), rot=(0, 0, yaw - 0.2 * kb), scale=1.0)

        # ------------------------------------------------ weights
        W = max(win(f, 78, 83, 100, 103), win(f, 108, 111, 130, 134))   # creeping
        freeze = win(f, 101, 103, 107, 110)
        th = 2 * pi * x / stride
        surge = win(f, 34, 38, 44, 48)
        cry = win(f, 39, 42, 45, 47)
        hitc = math.exp(-(f - 186) / 6) * math.cos((f - 186) * 0.9) if f >= 186 else 0
        shake = win(f, 206, 208, 213, 217)
        growl = win(f, 219, 223, 232, 240)
        idle = math.sin(2 * pi * f / 34)

        # ------------------------------------------------ body: low, swinging side to side
        low = 0.05 * W + 0.03 * freeze + 0.05 * wind + 0.06 * kb + 0.04 * growl
        A.key(B, f, loc=(0.035 * math.sin(th) * W, 0, -low + 0.012 * idle * (1 - W) + 0.05 * abs(hitc)),
              rot=(-0.3 * surge + 0.1 * wind - 0.08 * thrust - 0.14 * kb + 0.05 * growl,
                   0.07 * math.sin(th + 0.6) * W + 0.2 * hitc,
                   0.11 * math.sin(th) * W),
              scale=(1 + 0.015 * idle, 1, 1 + 0.02 * idle))
        for lp, sd, ph, front in X['legs']:
            p_ = th + 2 * pi * ph
            sw = 0.55 * math.sin(p_) * W
            lift = max(0, -math.cos(p_)) * 0.3 * W
            splay = 0.3 * W + 0.3 * freeze + 0.35 * wind + 0.5 * kb + 0.3 * growl + 0.5 * surge
            paddle = 0.5 * math.sin(f * 0.7 + ph * 6) * win(f, 18, 22, 36, 40)       # treading water
            stomp = -0.5 * wind + 0.3 * thrust if front else 0.2 * wind - 0.25 * thrust
            A.key(lp, f, rot=(sw + paddle + stomp + (0.3 if front else -0.2) * kb, -sd * (splay * 0.6 + lift), 0))

        # ------------------------------------------------ tail: S-wave behind the walk, uncurls when hurt
        for i, tp in enumerate(tail):
            wave = 0.2 * math.sin(th - 0.8 - i * 0.6) * W * (0.5 + i * 0.12) + 0.05 * math.sin(2 * pi * f / 26 - i * 0.7) * (1 - W)
            flick = 0.3 * math.sin((f - 101) * 1.3) * freeze * (1 if i > 4 else 0)
            recurl = spring((f - (208 + i * 1.6)) / 9, 5, 8) if f >= 200 else 0
            straight = (E(f, 186, 190) - recurl) if f >= 186 else 0
            curl = -0.12 * W - 0.3 * straight + 0.1 * wind - 0.14 * thrust + 0.05 * math.sin(th * 2 - i) * W - 0.1 * surge
            A.key(tp, f, rot=(curl, 0, wave + flick + 0.25 * math.sin((f - 206) * 1.5 - i) * shake))

        # ------------------------------------------------ head and jaw
        look = win(f, 50, 55, 66, 71) * math.sin(2 * pi * (f - 50) / 22)
        peek = freeze                                                    # lifts its head and looks at the camera
        A.key(H, f, loc=(0, -0.05 * thrust * s * 0.3, 0),
              rot=(-0.45 * cry - 0.3 * wind + 0.1 * thrust - 0.12 * peek + 0.07 * W - 0.45 * kb * (0.5 + 0.5 * abs(hitc)) + 0.14 * growl
                   + 0.02 * idle,
                   0.3 * math.sin((f - 206) * 1.6) * shake + 0.15 * peek,
                   -0.11 * math.sin(th) * W + 0.3 * look - 0.75 * peek + 0.4 * kb))
        snap1 = win(f, 39, 42, 45, 46)                                   # the cry: jaws gape, then clap shut
        roar = win(f, 142, 146, 160, 162)
        snap2 = win(f, 163, 165, 167, 168)
        yelp = win(f, 186, 188, 196, 202)
        gr = win(f, 220, 224, 227, 228)
        A.key(J, f, rot=(0.75 * snap1 + 0.6 * roar + 0.5 * snap2 + 0.45 * yelp + 0.35 * gr + 0.03 * max(0, idle) * (1 - W), 0, 0))
        blink = max(win(f, 29, 30, 31, 33), win(f, 58, 60, 61, 63), win(f, 104, 105, 106, 107), win(f, 186, 188, 200, 205))
        narrow = 0.35 * max(W, growl, wind)
        for e in X['eyes']:
            A.key(e, f, scale=(1, 1, 1 - max(0.9 * blink, narrow)))

    # sun spot glows when it calls the vines (and flickers in the cry)
    for m_, base in zip(X['sun'], (0.5, 1.0)):
        for f, v in [(0, 1), (38, 1), (43, 5), (48, 1), (141, 1), (149, 9), (168, 9), (180, 1)]:
            A.emission(m_, f, base * v)

    # ---------------------------------------------------- the swamp pool it surfaces from
    wm = lib.mat('swo_fx_water', '#1f5a52', 0.04, coat=1.0, sss=0.1)
    pool = lib.sphere('swo_fx_pool', (0, -0.1, 0.005), (1.05, 1.75, 0.02), wm, seg=40)
    for f, sc in [(0, 0.001), (15, 0.001), (20, 1.08), (23, 1.0), (44, 1.0), (54, 0.001)]:
        A.key(pool, f, scale=(sc, sc, 1))
    pm = lib.mat('swo_fx_lily', '#58b04a', 0.3, coat=0.8)
    for j, (x_, y_) in enumerate([(0.7, -0.9), (-0.75, 0.3)]):
        pad = lily_pad(lib, f'swo_fx_pad{j}', 0.16, pm, None, (x_, y_, 0.03), (0, 0, j * 2.0))
        for f, sc in [(0, 0.001), (18, 0.001), (22, 1.0), (44, 1.0), (50, 0.001)]:
            A.key(pad, f, scale=sc)
        A.key(pad, 22, loc=(0, 0, 0)); A.key(pad, 36, loc=(0, 0, 0)); A.key(pad, 42, loc=(x_ * 0.25, y_ * 0.15, 0))
    for j, (f0, cx, cy) in enumerate([(19, 0, 0.0), (25, 0, -0.5), (35, 0, -0.5), (38, 0, 0.1)]):
        rm = lib.mat(f'swo_fx_rip{j}', '#b8f0e0', 0.2, emit=0.8)
        ring = lib.torus(f'swo_fx_ring{j}', (cx, cy, 0.03), 1.0, 0.03, rm)
        A.key(ring, 0, scale=0.001); A.key(ring, f0, scale=(0.15, 0.15, 0.3)); A.key(ring, f0 + 10, scale=(0.95, 1.3, 0.05))
        A.key(ring, f0 + 11, scale=0.001)
        A.alpha(rm, f0, 0.9); A.alpha(rm, f0 + 10, 0.0)
    dm = lib.mat('swo_fx_drop', '#c8f4ec', 0.05, coat=1, emit=0.5)
    for j in range(10):
        a = j * 0.63 + 0.3
        d = lib.pivot(f'swo_fx_dropp{j}')
        lib.sphere(f'swo_fx_drop{j}', (0, 0, 0), 0.045 + 0.02 * (j % 3), dm, d, seg=10)
        p0 = Vector((0.3 * math.cos(a), -0.6 + 0.6 * math.sin(a), 0.1))
        v = Vector((math.cos(a) * 0.9, math.sin(a) * 0.9 - 0.3, 1.2 + 0.4 * (j % 3)))
        f0 = 35 + j % 3
        A.key(d, 0, loc=p0, scale=0.001, absolute=True); A.key(d, f0 - 1, loc=p0, scale=0.001, absolute=True)
        for k in range(0, 13, 2):
            t = k / 12
            A.key(d, f0 + k, loc=p0 + v * t + Vector((0, 0, -1.5 * t * t * 1.1)), scale=1.0 if k < 12 else 0.001, absolute=True)

    # ---------------------------------------------------- Vine Whip: two vines burst from the ground and lash
    vm = lib.mat('swo_fx_vine', '#2f8a46', 0.35, coat=0.6)
    vl = lib.mat('swo_fx_vleaf', '#8fd67c', 0.35, coat=0.5, emit=0.3)
    vt = lib.mat('swo_fx_vtip', '#e8ff9a', 0.3, emit=2.5)
    dirt = lib.mat('swo_fx_dirt', '#6a4a2c', 0.8)
    base0 = A.world(root, 160)
    base0.z = 0
    tgt = A.opponent(base0)
    perp = Vector((-dirv.y, dirv.x, 0))
    n = 20
    for vi, (side, f_a, f_h) in enumerate([(1, 149, 162), (-1, 153, 168)]):
        p0 = base0 + dirv * 0.28 * s + perp * side * 0.42 * s
        d = tgt - p0
        hz = math.hypot(d.x, d.y)
        Lk = d.length * 1.03 / n
        tilt = -(pi / 2 - math.atan2(d.z, hz)) + 0.16                    # link 0: from straight up to aimed
        vb = lib.pivot(f'swo_fx_vb{vi}', p0, None, rot=(0, 0, math.atan2(-d.x, d.y)))
        lib.sphere(f'swo_fx_mound{vi}', (0, 0, 0), (0.22, 0.22, 0.09), dirt, vb, seg=12)
        for q in range(5):
            lib.sphere(f'swo_fx_clod{vi}{q}', (0.26 * math.cos(q * 1.3), 0.26 * math.sin(q * 1.3), 0.02), 0.05, dirt, vb, seg=8)
        for f, sc in [(0, 0.001), (f_a - 1, 0.001), (f_a + 4, 1.0), (f_h + 12, 1.0), (f_h + 17, 0.001)]:
            A.key(vb, f, scale=sc)
        links, prev = [], vb
        for i in range(n):
            lp = lib.pivot(f'swo_fx_v{vi}_{i}', (0, 0, 0 if i == 0 else Lk), prev)
            r0, r1 = 0.085 * (1 - i / n * 0.72), 0.085 * (1 - (i + 1) / n * 0.72)
            lib.tube(f'swo_fx_vm{vi}_{i}', [(0, 0, 0), (0, 0, Lk / 2), (0, 0, Lk)], [r0, (r0 + r1) / 2, r1], vm, lp)
            lib.sphere(f'swo_fx_vj{vi}_{i}', (0, 0, 0), r0, vm, lp, seg=12)
            if i % 3 == 1:
                sgn = 1 if i % 2 == 1 else -1
                leaf(lib, f'swo_fx_vlf{vi}_{i}', (sgn * r0 * 0.6, 0, Lk * 0.3), (sgn, 0, 0.7), (0, 1, 0), 0.26, 0.085, vl, lp)
            links.append(lp)
            prev = lp
        drop(lib, f'swo_fx_vtip{vi}', 0.07, 0.3, vt, prev, (0, 0, Lk), seg=8, rings=6)
        for f in range(f_a - 1, f_h + 18):
            ret = E(f, f_h + 7, f_h + 15)
            for i, lp in enumerate(links):
                grow = spring((f - (f_a + i * 0.25)) / 6, 5, 6)
                lw = E(f, f_h - 9 + 0.25 * i, f_h - 4.75 + 0.25 * i)       # the lash runs base to tip
                coil = (0.2 + 0.012 * i) * (1 + 0.5 * win(f, f_h - 12, f_h - 9, f_h - 8, f_h - 5)) if i else -0.25
                target = tilt if i == 0 else -0.015
                wob = 0.14 * 0.5 * math.sin((f - f_h) * 1.3 - i * 0.45) * math.exp(-(f - f_h) / 4) if f > f_h else 0
                ang = coil * (1 - lw) + target * lw + wob
                ang = ang * (1 - ret) + (0.3 if i else -0.1) * ret
                A.key(lp, f, rot=(ang, side * 0.05 * math.sin(i + f * 0.4) * (1 - lw), 0),
                      scale=(1, 1, max(0.05, grow * (1 - 0.6 * ret))) if i == 0 else None)
        A.light(f'swo_fx_l{vi}', '#b0ff60', tgt + Vector((0, -0.3 * s, 0.25 * s)), [(0, 0), (f_h - 1, 0), (f_h + 1, 700 * s * s), (f_h + 7, 0)])
        st = lib.sphere(f'swo_fx_hit{vi}', tgt, 1.0, lib.mat('swo_fx_hitm', '#e8ffb0', 0.4, emit=4, alpha=0.5), seg=16)
        for f, sc in [(0, 0.001), (f_h - 1, 0.001), (f_h + 1, 0.28 * s), (f_h + 5, 0.001)]:
            A.key(st, f, scale=(sc, sc * 0.5, sc) if not isinstance(sc, float) or sc > 0.01 else sc)
    A.light('swo_fx_sun', '#ffe060', (0, 0.1, 0.9), [(0, 0), (141, 0), (149, 120 * s * s), (168, 120 * s * s), (180, 0)], parent=root)
