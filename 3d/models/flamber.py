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


def ell_n(c, radii, p):
    """Outward normal of an ellipsoid at surface point p."""
    return Vector(((p[0] - c[0]) / radii[0] ** 2, (p[1] - c[1]) / radii[1] ** 2, (p[2] - c[2]) / radii[2] ** 2)).normalized()


def oval(rx, rz, cx=0.0, cz=0.0, n=24):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cz + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]


def fire_mats(lib, P):
    return dict(
        dk=lib.mat(P + 'dk', '#8e1a10', 0.5, emit=0.03),
        rd=lib.mat(P + 'rd', '#c62c0e', 0.45, emit=0.12),
        orr=lib.mat(P + 'or', '#f06a10', 0.45, emit=0.35),
        ye=lib.mat(P + 'ye', '#ffbc1e', 0.4, emit=0.7),
        pl=lib.mat(P + 'pl', '#ffe888', 0.4, emit=1.0),
    )


def embers(lib, P, parent, loc, spots, mats):
    sp = lib.pivot(P + 'embers', loc, parent)
    for i, (a, r, z, s) in enumerate(spots):
        lib.sphere(f'{P}ember{i}', (math.cos(a) * r, math.sin(a) * r, z), s, mats[i % len(mats)], sp, seg=12)
    return sp


def big_eye(lib, name, loc, r, parent, look, P, iris='#e8a020', ring='#7a3a10', pupil='#1a1010'):
    """Large cartoon eye with a layered iris, built flat enough to sit in the face."""
    p = lib.pivot(name, loc, parent)
    p.rotation_euler = Vector((0, -1, 0)).rotation_difference(Vector(look).normalized()).to_euler()
    lib.sphere(name + '_white', (0, 0, 0), (r, r * 0.4, r), lib.mat(P + 'ewhite', '#ffffff', 0.15, coat=1), p)
    lib.sphere(name + '_iris', (0, -r * 0.3, -r * 0.06), (r * 0.64, r * 0.12, r * 0.64), lib.mat(P + 'eiris', iris, 0.2, coat=1, emit=0.15), p)
    lib.sphere(name + '_ring', (0, -r * 0.33, -r * 0.06), (r * 0.44, r * 0.11, r * 0.44), lib.mat(P + 'ering', ring, 0.2, coat=1), p)
    lib.sphere(name + '_pupil', (0, -r * 0.36, -r * 0.06), (r * 0.25, r * 0.1, r * 0.25), lib.mat(P + 'epupil', pupil, 0.1, coat=1), p)
    sh = lib.mat('shine', '#ffffff', 0.1, emit=2)
    lib.sphere(name + '_shine', (-r * 0.3, -r * 0.42, r * 0.3), (r * 0.17, r * 0.06, r * 0.17), sh, p)
    lib.sphere(name + '_shine2', (r * 0.3, -r * 0.42, -r * 0.34), (r * 0.08, r * 0.04, r * 0.08), sh, p)
    return p


def build(lib):
    P = 'flb_'
    rig = lib.Rig('Flamber', 'flamber', 'Fire', height_cm=40, gait='hop', attack='cast')
    R = math.radians
    M = fire_mats(lib, P)
    body = lib.mat(P + 'body', '#cc3214', 0.4, emit=0.04, coat=0.35)
    bor = lib.mat(P + 'bor', '#f06c14', 0.4, emit=0.12, coat=0.3)
    bye = lib.mat(P + 'bye', '#ffbe24', 0.4, emit=0.25, coat=0.3)
    bpl = lib.mat(P + 'bpl', '#ffec90', 0.4, emit=0.35, coat=0.3)
    dark = lib.mat(P + 'dark', '#5a1410', 0.5)

    rig.body = lib.pivot(P + 'body', (0, 0, 0.02), rig.root)
    B = rig.body
    c, rr = (0, 0, 0.45), (0.31, 0.29, 0.36)
    lib.sphere(P + 'egg', c, rr, body, B, seg=40)
    lib.sphere(P + 'eggtop', (0, 0, 0.62), (0.235, 0.225, 0.25), body, B)
    decal(lib, P + 'band1', oval(0.235, 0.275, 0, -0.04), c, rr, bor, B, lift=1.008, n=1)
    decal(lib, P + 'band2', oval(0.16, 0.16, 0, -0.15), c, rr, bye, B, lift=1.016, n=1)
    decal(lib, P + 'band3', oval(0.09, 0.075, 0, -0.21), c, rr, bpl, B, lift=1.024, n=1)

    # head == body: one big eye
    rig.head = lib.pivot(P + 'head', (0, 0, 0.3), B)
    H = rig.head
    ep = on_ell((0, 0, 0.15), rr, 0, 0.1, 0.97)
    big_eye(lib, P + 'eye', ep, 0.145, H, (0, -1, 0.2), P)
    for s in (-1, 1):
        lib.tube(f'{P}lash{s}', [on_ell((0, 0, 0.15), rr, s * 0.1, 0.235, 1.01), on_ell((0, 0, 0.15), rr, s * 0.15, 0.25, 1.03),
                                 on_ell((0, 0, 0.15), rr, s * 0.19, 0.24, 1.02)], [0.014, 0.012, 0.006], dark, H)
    pts = []
    for k in range(7):
        x = -0.065 + 0.13 * k / 6
        pts.append(on_ell((0, 0, 0.15), rr, x, -0.105 + 0.03 * (abs(x) / 0.065) ** 2, 1.03))
    lib.tube(P + 'smile', pts, [0.006, 0.009, 0.01, 0.01, 0.01, 0.009, 0.006], dark, H)

    # layered flame on top
    fl = lib.pivot(P + 'flame', (0, 0, 0.74), B)
    drop(lib, P + 'f_r0', 0.15, 0.5, M['rd'], fl, (0, 0.02, -0.04), d=(0.03, 0, 1), bend=(0.1, 0), flat=0.8)
    drop(lib, P + 'f_r1', 0.11, 0.3, M['rd'], fl, (-0.11, 0.02, -0.07), d=(-0.42, 0, 1), bend=(0.07, 0), flat=0.8)
    drop(lib, P + 'f_r2', 0.11, 0.34, M['rd'], fl, (0.12, 0.02, -0.07), d=(0.4, 0, 1), bend=(-0.06, 0), flat=0.8)
    drop(lib, P + 'f_r3', 0.1, 0.28, M['rd'], fl, (0, 0.1, -0.08), d=(0, 0.4, 1), flat=1.0)
    drop(lib, P + 'f_o0', 0.105, 0.34, M['orr'], fl, (0.0, -0.07, -0.05), d=(0.02, -0.05, 1), bend=(0.07, 0), flat=0.75)
    drop(lib, P + 'f_o1', 0.075, 0.22, M['orr'], fl, (-0.08, -0.07, -0.07), d=(-0.4, -0.05, 1), flat=0.75)
    drop(lib, P + 'f_o2', 0.075, 0.24, M['orr'], fl, (0.09, -0.07, -0.07), d=(0.38, -0.05, 1), flat=0.75)
    drop(lib, P + 'f_y0', 0.065, 0.2, M['ye'], fl, (0.0, -0.135, -0.07), d=(0.03, -0.12, 1), flat=0.7)
    drop(lib, P + 'f_y1', 0.045, 0.13, M['ye'], fl, (0.055, -0.13, -0.08), d=(0.4, -0.12, 1), flat=0.7)
    rig.extras.append((fl, 'flicker'))

    # stubby flame arms
    for s, nm, ph in ((-1, 'L', 0.0), (1, 'R', 0.5)):
        ap = lib.pivot(P + 'arm' + nm, (s * 0.27, 0, 0.42), B)
        drop(lib, P + 'arm_a' + nm, 0.085, 0.24, M['rd'], ap, (0, 0, 0), d=(s, 0, 0.5), flat=0.85)
        drop(lib, P + 'arm_b' + nm, 0.07, 0.2, M['rd'], ap, (0, 0, -0.03), d=(s, 0, -0.4), flat=0.85)
        drop(lib, P + 'arm_c' + nm, 0.045, 0.13, M['orr'], ap, (s * 0.03, -0.055, 0.0), d=(s, -0.1, 0.25), flat=0.8)
        rig.arms.append((ap, ph))
        rig.t_pose[ap.name] = (0, 0, 0)

    # tiny feet
    for s, nm, ph in ((-1, 'L', 0.0), (1, 'R', 0.5)):
        lp = lib.pivot(P + 'leg' + nm, (s * 0.14, -0.02, 0.12), B)
        lib.sphere(P + 'foot' + nm, (0, -0.045, -0.07), (0.1, 0.14, 0.07), M['dk'], lp)
        lib.sphere(P + 'toe' + nm, (0, -0.1, -0.06), (0.07, 0.07, 0.045), body, lp)
        rig.legs.append((lp, ph))

    # floating embers
    em = embers(lib, P, B, (0, 0, 0.6), [(0.5, 0.52, 0.42, 0.028), (2.4, 0.5, 0.55, 0.022), (3.6, 0.55, 0.15, 0.025),
                                          (5.2, 0.5, 0.3, 0.02), (1.5, 0.45, 0.05, 0.018)], [M['ye'], M['orr']])
    rig.extras.append((em, 'spin'))

    rig.attack_origin = (0, -0.4, 0.55)
    return rig
