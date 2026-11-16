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
    P = 'swe_'
    rig = lib.Rig('Swampest', 'swampest', 'Grass', height_cm=220, gait='walk', attack='bite')
    R = math.radians
    k = 0.88
    dk = lib.mat(P + 'dk', '#164a2a', 0.5, coat=0.2)
    md = lib.mat(P + 'md', '#267a40', 0.45, coat=0.3, sss=0.05)
    bs = lib.mat(P + 'bs', '#3a9a50', 0.42, coat=0.35, sss=0.08)
    lt = lib.mat(P + 'lt', '#6cbf66', 0.45, coat=0.3)
    hl = lib.mat(P + 'hl', '#a8e08a', 0.45, coat=0.3)
    belly = lib.mat(P + 'belly', '#d4dc98', 0.5, sss=0.1)
    bellydk = lib.mat(P + 'bellydk', '#a8b270', 0.6)
    tooth = lib.mat(P + 'tooth', '#fbfbf0', 0.25, coat=0.6)
    claw = lib.mat(P + 'claw', '#f4f4e8', 0.3, coat=0.5)
    mouth = lib.mat(P + 'mouth', '#6a1424', 0.5)
    tongue = lib.mat(P + 'tongue', '#e06080', 0.4, sss=0.2, coat=0.3)
    petal = lib.mat(P + 'petal', '#f08ac0', 0.45, sss=0.2)
    petaldk = lib.mat(P + 'petaldk', '#c8508a', 0.5)
    pollen = lib.mat(P + 'pollen', '#ffd84a', 0.4, emit=0.6)
    dark = lib.mat(P + 'dark', '#0e2a18', 0.5)

    rig.body = lib.pivot(P + 'body', (0, 0.12 * k, 0.5 * k), rig.root)
    B = rig.body
    B.scale = (k, k, k)

    # torso
    tc, tr = (0, 0.08, 0.0), (0.35, 0.54, 0.3)
    lib.sphere(P + 'torso', tc, tr, bs, B)
    lib.sphere(P + 'chest', (0, -0.3, 0.0), (0.32, 0.33, 0.275), bs, B)
    bc, br = (0, 0.03, -0.1), (0.32, 0.55, 0.23)
    lib.sphere(P + 'belly', bc, br, belly, B)
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
        lib.sphere(f'{P}ridgehl{i}', (0, y + 0.045, z + 0.2 - 0.02 * abs(i - 1)), 0.014, hl, B)
    for j, (y, z) in enumerate([(-0.3, 0.1), (0.05, 0.15), (0.3, 0.06), (-0.12, -0.02)]):
        for s in (-1, 1):
            x = tr[0] * math.sqrt(max(0, 1 - ((y - tc[1]) / tr[1]) ** 2 - (z / tr[2]) ** 2))
            if y < -0.2:
                x = max(x, 0.32 * math.sqrt(max(0, 1 - ((y + 0.3) / 0.33) ** 2 - (z / 0.275) ** 2)))
            lib.sphere(f'{P}fleck{j}{s}', (s * x, y, z), (0.013, 0.04, 0.03), hl, B)
    # moss hanging from the belly
    for j, (x, y, L) in enumerate([(-0.27, -0.22, 0.16), (0.28, -0.05, 0.19), (-0.29, 0.12, 0.2), (0.27, 0.3, 0.16),
                                   (-0.24, 0.36, 0.14), (0.25, -0.3, 0.14), (-0.28, -0.05, 0.13), (0.28, 0.14, 0.13)]):
        q = 1 - (x / br[0]) ** 2 - ((y - bc[1]) / br[1]) ** 2
        z = bc[2] - br[2] * math.sqrt(max(q, 0)) + 0.03
        L = min(L, (0.5 + z) - 0.02)
        drop(lib, f'{P}moss{j}', 0.045, L, md if j % 2 else dk, B, (x, y, z), d=(0, 0, -1), bend=(0.02, 0.02), base=0.9, seg=6, rings=5)

    # thick clawed legs
    for (nm, s, y, ph) in (('FL', -1, -0.33, 0.0), ('FR', 1, -0.33, 0.5), ('BL', -1, 0.4, 0.5), ('BR', 1, 0.4, 0.0)):
        lp = lib.pivot(P + 'leg' + nm, (s * 0.26, y, -0.1), B)
        lib.sphere(P + 'hip' + nm, (s * 0.02, 0, 0.0), (0.16, 0.19, 0.18), md, lp)
        lib.tube(P + 'legm' + nm, [(0, 0, 0), (s * 0.07, 0, -0.12), (s * 0.1, -0.01, -0.25), (s * 0.1, -0.02, -0.35)],
                 [0.14, 0.135, 0.12, 0.115], md, lp)
        lib.sphere(P + 'foot' + nm, (s * 0.1, -0.08, -0.345), (0.13, 0.18, 0.055), md, lp)
        for c in (-1.5, -0.5, 0.5, 1.5):
            lib.cone(f'{P}claw{nm}{c}', (s * 0.1 + c * 0.055, -0.255, -0.365), 0.027, 0.0, 0.09, claw, lp,
                     rot=_aim((c * 0.18, -1, -0.12)), seg=10)
        rig.legs.append((lp, ph))

    # head: jaws wide open at rest
    rig.head = lib.pivot(P + 'head', (0, -0.56, 0.08), B)
    H = rig.head
    H.scale = (1.3, 1.3, 1.3)
    lib.sphere(P + 'neck', (0, 0.04, -0.04), (0.25, 0.2, 0.22), bs, H)
    lib.sphere(P + 'skull', (0, -0.1, 0.03), (0.235, 0.22, 0.19), bs, H)
    lib.sphere(P + 'throat', (0, -0.2, -0.045), (0.165, 0.2, 0.1), mouth, H)
    z0 = 0.0
    U = lib.pivot(P + 'upper', (0, -0.08, -0.03), H, rot=(R(-16), 0, 0))
    up = [(0.0, 0.21, 0.16), (-0.2, 0.2, 0.135), (-0.42, 0.165, 0.095), (-0.62, 0.15, 0.08), (-0.76, 0.15, 0.095), (-0.84, 0.1, 0.05)]
    jaw_loft(lib, P + 'snout', up, z0, bs, U)
    jaw_loft(lib, P + 'palate', [(y, w - 0.03, -0.014) for y, w, _ in up[1:]], 0.01, mouth, U)
    lib.tube(P + 'snoutline', [(0, -0.25, 0.135), (0, -0.45, 0.103), (0, -0.62, 0.089)], [0.02, 0.016, 0.012], lt, U)
    for s in (-1, 1):
        lib.sphere(f'{P}nosb{s}', (s * 0.06, -0.75, 0.078), (0.045, 0.05, 0.03), bs, U)
        lib.sphere(f'{P}nos{s}', (s * 0.066, -0.775, 0.098), (0.017, 0.02, 0.012), dark, U)
        lib.sphere(f'{P}browb{s}', (s * 0.13, -0.14, 0.17), (0.1, 0.12, 0.095), bs, H)
        slit_eye(lib, f'{P}eye{s}', (s * 0.19, -0.18, 0.185), 0.072, H, (s * 0.85, -0.6, 0.12), s, P, iris='#f8d040', brow=dk, anger=0.45)

    rig.jaw = lib.pivot(P + 'jaw', (0, -0.08, -0.03), H, rot=(R(24), 0, 0))
    J = rig.jaw
    lo = [(0.05, 0.2, -0.13), (-0.14, 0.195, -0.12), (-0.36, 0.16, -0.1), (-0.56, 0.145, -0.085), (-0.69, 0.14, -0.08), (-0.75, 0.09, -0.05)]
    jaw_loft(lib, P + 'jawm', lo, 0.0, md, J)
    jaw_loft(lib, P + 'bed', [(y, w - 0.03, 0.014) for y, w, _ in lo[1:]], -0.01, mouth, J)
    tg = lib.tube(P + 'tongue', [(0, -0.12, 0), (0, -0.3, 0.02), (0, -0.48, 0.01), (0, -0.58, 0)], [0.085, 0.09, 0.075, 0.05], tongue, J)
    tg.scale = (1, 1, 0.4)
    tg.location = (0, 0, 0.022)
    lib.tube(P + 'tongueline', [(0, -0.2, 0.062), (0, -0.4, 0.058), (0, -0.54, 0.04)], [0.006, 0.007, 0.004], lib.mat(P + 'tgdk', '#b8406a', 0.5), J)

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
        lib.sphere(f'{P}tailj{i}', (0, 0, 0), rads[i], bs, tp)
        lib.tube(f'{P}tailm{i}', [(0, 0, 0), (0, lens[i] / 2, 0), (0, lens[i], 0)],
                 [rads[i], (rads[i] + rads[i + 1]) / 2, rads[i + 1]], bs, tp)
        lib.sphere(f'{P}tailhl{i}', (0, lens[i] * 0.5, rads[i] * 0.93), (0.03, 0.05, 0.012), lt, tp)
        if i % 2 == 0:
            rig.tail.append(tp)
        rig.t_pose[tp.name] = (R(50) if i == 0 else R(4), 0, 0)
        prev, ploc = tp, (0, lens[i], 0)
    lib.sphere(P + 'tailtop', (0, lens[-1], 0), rads[-1], bs, prev)
    # in the last link's frame: +Y is up, +Z is forward
    top = (0, lens[-1] + 0.06, 0.02)
    for s, m_ in ((-1, lt), (1, md)):
        leaf(lib, f'{P}leaf{s}', (0, lens[-1] + 0.03, 0), (s * 1, 0.25, 0.15), (0, 0.2, s * 1), 0.4, 0.12, m_, prev, arch=-0.05 * s)
    F = lib.pivot(P + 'flower', top, prev, rot=(R(-125), 0, 0))
    lib.tube(P + 'fstem', [(0, 0.1, 0), (0, 0.04, 0), (0, 0.0, 0)], [0.05, 0.045, 0.04], md, F)
    for q in range(5):
        a = q * 2 * math.pi / 5
        px, pz = math.sin(a) * 0.15, math.cos(a) * 0.15
        lib.sphere(f'{P}petal{q}', (px, -0.015, pz), (0.105, 0.035, 0.135), petal, F, rot=(R(-14) * math.cos(a), -a, 0) if False else (0, a, 0))
        lib.sphere(f'{P}petalt{q}', (px * 1.72, -0.012, pz * 1.72), (0.035, 0.02, 0.03), petaldk, F, rot=(0, a, 0))
    lib.sphere(P + 'pollen', (0, -0.045, 0), (0.07, 0.045, 0.07), pollen, F)
    lib.sphere(P + 'pollen2', (0, -0.08, 0), (0.03, 0.02, 0.03), lib.mat(P + 'pol2', '#f08a20', 0.4), F)
    rig.extras.append((F, 'sway'))

    rig.attack_origin = (0, -1.2, 0.55)
    return rig
