import math
from mathutils import Vector


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


def build(lib):
    P = 'swo_'
    rig = lib.Rig('Swamporiaer', 'swamporiaer', 'Grass', height_cm=150, gait='walk', attack='bite')
    R = math.radians
    k = 0.85
    dk = lib.mat(P + 'dk', '#1d5233', 0.5, coat=0.2)
    md = lib.mat(P + 'md', '#2f8a46', 0.45, coat=0.3, sss=0.05)
    bs = lib.mat(P + 'bs', '#45a856', 0.42, coat=0.35, sss=0.08)
    lt = lib.mat(P + 'lt', '#7cc96e', 0.45, coat=0.3)
    belly = lib.mat(P + 'belly', '#dbe3a0', 0.5, sss=0.1)
    bellydk = lib.mat(P + 'bellydk', '#b2bc78', 0.6)
    tooth = lib.mat(P + 'tooth', '#fbfbf0', 0.25, coat=0.6)
    claw = lib.mat(P + 'claw', '#f4f4e8', 0.3, coat=0.5)
    mouth = lib.mat(P + 'mouth', '#6a1424', 0.5)
    tongue = lib.mat(P + 'tongue', '#e06080', 0.45, sss=0.2)
    sun = lib.mat(P + 'sun', '#e8c838', 0.4, emit=0.4)
    sunlt = lib.mat(P + 'sunlt', '#f8e870', 0.35, emit=0.7)
    dark = lib.mat(P + 'dark', '#12301e', 0.5)

    rig.body = lib.pivot(P + 'body', (0, 0.1 * k, 0.45 * k), rig.root)
    B = rig.body
    B.scale = (k, k, k)

    # torso
    tc, tr = (0, 0.1, 0.0), (0.3, 0.56, 0.26)
    lib.sphere(P + 'torso', tc, tr, bs, B)
    lib.sphere(P + 'chest', (0, -0.3, -0.005), (0.27, 0.32, 0.235), bs, B)
    bc, br = (0, 0.05, -0.085), (0.275, 0.56, 0.2)
    lib.sphere(P + 'belly', bc, br, belly, B)
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
        sp = drop(lib, f'{P}ridge{i}', 0.075, h, md, B, (0, y, z), d=(0, 0.25, 1), flat=1.0, base=0.9, seg=8, rings=5)
        sp.scale = (0.5, 1, 1)
    # scale flecks
    for j, (y, z) in enumerate([(-0.3, 0.1), (-0.1, 0.15), (0.38, 0.1), (0.5, 0.02), (-0.2, -0.0)]):
        for s in (-1, 1):
            x = tr[0] * math.sqrt(max(0, 1 - ((y - tc[1]) / tr[1]) ** 2 - (z / tr[2]) ** 2))
            if y < -0.2:
                x = max(x, 0.27 * math.sqrt(max(0, 1 - ((y + 0.3) / 0.32) ** 2 - (z / 0.235) ** 2)))
            lib.sphere(f'{P}fleck{j}{s}', (s * x, y, z), (0.012, 0.035, 0.028), lt, B)
    # sun spot on each side
    for s in (-1, 1):
        def side(y, z, lift=0.0):
            x = tr[0] * math.sqrt(max(0, 1 - ((y - tc[1]) / tr[1]) ** 2 - (z / tr[2]) ** 2))
            return (s * (x + lift), y, z)
        cy, cz = 0.14, 0.035
        lib.sphere(f'{P}sun{s}', side(cy, cz, -0.004), (0.02, 0.085, 0.085), sun, B)
        lib.sphere(f'{P}sunin{s}', side(cy, cz, 0.004), (0.016, 0.055, 0.055), sunlt, B)
        for q in range(8):
            a = q * math.pi / 4
            y, z = cy + math.cos(a) * 0.125, cz + math.sin(a) * 0.125
            lib.sphere(f'{P}ray{s}{q}', side(y, z, -0.004), (0.012, 0.03, 0.014), sun, B, rot=(a, 0, 0))

    # legs
    for (nm, s, y, ph) in (('FL', -1, -0.32, 0.0), ('FR', 1, -0.32, 0.5), ('BL', -1, 0.42, 0.5), ('BR', 1, 0.42, 0.0)):
        lp = lib.pivot(P + 'leg' + nm, (s * 0.22, y, -0.1), B)
        lib.sphere(P + 'hip' + nm, (s * 0.02, 0, 0.0), (0.13, 0.15, 0.14), md, lp)
        lib.tube(P + 'legm' + nm, [(0, 0, 0), (s * 0.07, 0, -0.1), (s * 0.1, -0.01, -0.22), (s * 0.1, -0.02, -0.31)],
                 [0.11, 0.105, 0.09, 0.085], md, lp)
        lib.sphere(P + 'foot' + nm, (s * 0.1, -0.07, -0.305), (0.1, 0.15, 0.045), md, lp)
        for c in (-1, 0, 1):
            lib.cone(f'{P}claw{nm}{c}', (s * 0.1 + c * 0.055, -0.215, -0.322), 0.024, 0.0, 0.08, claw, lp,
                     rot=_aim((c * 0.25, -1, -0.12)), seg=10)
        rig.legs.append((lp, ph))

    # head
    rig.head = lib.pivot(P + 'head', (0, -0.55, 0.04), B)
    H = rig.head
    H.scale = (1.18, 1.18, 1.18)
    lib.sphere(P + 'neck', (0, 0.02, -0.02), (0.24, 0.2, 0.21), bs, H)
    lib.sphere(P + 'skull', (0, -0.12, 0.03), (0.235, 0.22, 0.18), bs, H)
    z0 = -0.03
    up = [(0.0, 0.21, 0.15), (-0.2, 0.195, 0.125), (-0.42, 0.16, 0.085), (-0.62, 0.145, 0.07), (-0.76, 0.145, 0.085), (-0.84, 0.1, 0.045)]
    jaw_loft(lib, P + 'snout', up, z0, bs, H)
    lib.sphere(P + 'palate', (0, -0.42, z0 - 0.004), (0.1, 0.36, 0.012), mouth, H)
    for s in (-1, 1):
        lib.sphere(f'{P}nosb{s}', (s * 0.06, -0.75, 0.068), (0.045, 0.05, 0.03), bs, H)
        lib.sphere(f'{P}nos{s}', (s * 0.066, -0.775, 0.088), (0.017, 0.02, 0.012), dark, H)
        lib.sphere(f'{P}browb{s}', (s * 0.13, -0.16, 0.16), (0.095, 0.11, 0.09), bs, H)
        slit_eye(lib, f'{P}eye{s}', (s * 0.185, -0.2, 0.175), 0.07, H, (s * 0.85, -0.6, 0.12), s, P, brow=dk)
    # light stripe along the top of the snout
    lib.tube(P + 'snoutline', [(0, -0.25, 0.122), (0, -0.45, 0.092), (0, -0.62, 0.078)], [0.02, 0.016, 0.012], lt, H)

    # lower jaw
    rig.jaw = lib.pivot(P + 'jaw', (0, -0.08, z0), H)
    J = rig.jaw
    lo = [(0.05, 0.2, -0.125), (-0.14, 0.19, -0.115), (-0.36, 0.155, -0.095), (-0.56, 0.14, -0.08), (-0.69, 0.135, -0.075), (-0.75, 0.09, -0.05)]
    jaw_loft(lib, P + 'jawm', lo, 0.0, md, J)
    lib.sphere(P + 'bed', (0, -0.36, 0.004), (0.095, 0.34, 0.012), mouth, J)
    lib.sphere(P + 'tongue', (0, -0.36, 0.01), (0.065, 0.24, 0.016), tongue, J)

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
        lib.sphere(f'{P}tailj{i}', (0, 0, 0), rads[i], bs, tp)
        lib.tube(f'{P}tailm{i}', [(0, 0, 0), (0, lens[i] / 2, 0), (0, lens[i], 0)],
                 [rads[i], (rads[i] + rads[i + 1]) / 2, rads[i + 1]], bs, tp)
        if i < 5:
            sp = drop(lib, f'{P}tridge{i}', 0.05 - i * 0.005, 0.11 - i * 0.012, md, tp, (0, lens[i] * 0.5, rads[i] * 0.8),
                      d=(0, 0.25, 1), base=0.9, seg=8, rings=5)
            sp.scale = (0.5, 1, 1)
        if i % 2 == 0:
            rig.tail.append(tp)
        rig.t_pose[tp.name] = (R(8) if i == 0 else R(4), 0, 0)
        prev, ploc = tp, (0, lens[i], 0)
    lib.sphere(P + 'tailtip', (0, lens[-1], 0), rads[-1], bs, prev)

    rig.attack_origin = (0, -1.2, 0.4)
    return rig
