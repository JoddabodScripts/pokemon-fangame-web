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
    P = 'blz_'
    rig = lib.Rig('Blazian', 'blazian', 'Fire', height_cm=200, gait='walk', attack='cast')
    R = math.radians
    k = 0.92
    M = fire_mats(lib, P)
    rd = lib.mat(P + 'brd', '#c62c0e', 0.45, emit=0.06, coat=0.2)
    orr = lib.mat(P + 'bor', '#ec6612', 0.42, emit=0.08, coat=0.3)
    orlt = lib.mat(P + 'borlt', '#ff9438', 0.42, emit=0.12, coat=0.3)
    ye = lib.mat(P + 'bye', '#ffc626', 0.4, emit=0.35, coat=0.2)
    face = lib.mat(P + 'face', '#ffdc8c', 0.4, emit=0.22)
    sun = lib.mat(P + 'sun', '#ffcc28', 0.35, emit=0.9)
    sunpl = lib.mat(P + 'sunpl', '#fff0a8', 0.35, emit=1.2)
    dark = lib.mat(P + 'dark', '#6a140a', 0.5)
    mouth = lib.mat(P + 'mouth', '#7a1a10', 0.5)
    fang = lib.mat(P + 'fang', '#ffffff', 0.25, emit=0.3)

    rig.body = lib.pivot(P + 'body', (0, 0, 0.95 * k), rig.root)
    B = rig.body
    B.scale = (k, k, k)

    # torso with the sun emblem
    tc, tr = (0, 0, 0.02), (0.26, 0.2, 0.31)
    lib.sphere(P + 'torso', tc, tr, orr, B)
    lib.sphere(P + 'pelvis', (0, 0, -0.235), (0.22, 0.18, 0.11), rd, B)
    decal(lib, P + 'chestlt', oval(0.16, 0.2, 0, 0.03), tc, tr, orlt, B, lift=1.008, n=1)
    decal(lib, P + 'sun', oval(0.085, 0.085, 0, 0.03), tc, tr, sun, B, lift=1.03, n=1)
    decal(lib, P + 'sunc', oval(0.04, 0.04, -0.012, 0.045), tc, tr, sunpl, B, lift=1.045, n=1)
    for q in range(8):
        a = q * math.pi / 4
        p = on_ell(tc, tr, math.cos(a) * 0.135, 0.03 + math.sin(a) * 0.135, 1.02)
        lib.sphere(f'{P}sunray{q}', p, (0.016, 0.012, 0.026), sun, B, rot=(0, -(a - math.pi / 2), 0))

    # legs with flame feet
    for s, nm, ph in ((-1, 'L', 0.0), (1, 'R', 0.5)):
        lp = lib.pivot(P + 'leg' + nm, (s * 0.11, 0, -0.26), B)
        lib.sphere(P + 'hip' + nm, (0, 0, 0), 0.115, orr, lp)
        lib.tube(P + 'legm' + nm, [(0, 0, 0), (s * 0.04, -0.01, -0.28), (s * 0.09, 0, -0.56)], [0.115, 0.1, 0.085], orr, lp)
        fx, fz = s * 0.09, -0.6
        lib.sphere(P + 'foot' + nm, (fx, -0.03, fz - 0.005), (0.11, 0.15, 0.08), M['rd'], lp)
        drop(lib, P + 'ff_a' + nm, 0.085, 0.26, M['rd'], lp, (fx + s * 0.04, 0.0, fz), d=(s * 0.9, 0, 0.8), flat=0.9)
        drop(lib, P + 'ff_b' + nm, 0.085, 0.26, M['rd'], lp, (fx, -0.08, fz), d=(0, -1, 0.45), flat=0.9)
        drop(lib, P + 'ff_c' + nm, 0.075, 0.22, M['rd'], lp, (fx, 0.05, fz), d=(-s * 0.2, 1, 0.7), flat=0.9)
        drop(lib, P + 'ff_d' + nm, 0.055, 0.18, M['ye'], lp, (fx, -0.12, fz + 0.02), d=(s * 0.2, -1, 0.9), flat=0.8)
        rig.legs.append((lp, ph))

    # head: glowing face in a ring of flame
    rig.head = lib.pivot(P + 'head', (0, 0, 0.3), B)
    H = rig.head
    hc, hr = (0, 0, 0.3), (0.27, 0.25, 0.27)
    lib.sphere(P + 'neck', (0, 0, 0.03), (0.1, 0.09, 0.1), orr, H)
    lib.sphere(P + 'headm', hc, hr, ye, H, seg=40)
    lib.sphere(P + 'disc', (0, 0.08, 0.3), (0.34, 0.215, 0.34), orr, H)
    decal(lib, P + 'facep', oval(0.18, 0.175, 0, -0.01), hc, hr, face, H, lift=1.01, n=1, rings=6)
    mn = lib.pivot(P + 'mane', (0, 0.05, 0.3), H)
    for q in range(12):
        a = q * math.pi / 6
        dx, dz = math.sin(a), math.cos(a)
        long_ = q % 2 == 0
        drop(lib, f'{P}mane{q}', 0.115 if long_ else 0.1, 0.42 if long_ else 0.3, M['rd'] if long_ else M['orr'], mn,
             (dx * 0.24, 0, dz * 0.24), d=(dx, 0, dz), bend=(0.03 * dz, 0) if long_ else (0, 0), flat=0.75, base=0.8)
        if long_:
            drop(lib, f'{P}manei{q}', 0.055, 0.22, M['orr'], mn, (dx * 0.27, -0.075, dz * 0.27), d=(dx, -0.05, dz), flat=0.6, base=0.8)
    rig.extras.append((mn, 'pulse'))
    for s in (-1, 1):
        p = on_ell(hc, hr, s * 0.098, 0.03, 0.99)
        lib.eye(f'{P}eye{s}', p, 0.062, H, iris='#ff8a2a', pupil='#2a0a06', sclera='#2a0a06', look=(s * 0.2, -1, 0.05), iris_frac=0.5, flat=0.7)
        lib.tube(f'{P}brow{s}', [on_ell(hc, hr, s * 0.035, 0.085, 1.03), on_ell(hc, hr, s * 0.1, 0.115, 1.04), on_ell(hc, hr, s * 0.165, 0.125, 1.03)],
                 [0.012, 0.016, 0.01], dark, H)
        decal(lib, f'{P}mark{s}', [(s * 0.215, -0.045), (s * 0.15, -0.015), (s * 0.15, -0.085)], hc, hr, M['rd'], H, lift=1.03, rings=3)
        fp = on_ell(hc, hr, s * 0.062, -0.1, 1.0)
        lib.cone(f'{P}fang{s}', (fp[0], fp[1] - 0.01, fp[2] - 0.022), 0.018, 0.0, 0.055, fang, H, rot=_aim((0, 0.35, -1)), seg=10)
    decal(lib, P + 'mouth', [(-0.095, -0.095), (0.095, -0.095), (0.045, -0.165), (-0.045, -0.165)], hc, hr, mouth, H, lift=1.03)
    pts = []
    for q in range(9):
        x = -0.125 + 0.25 * q / 8
        pts.append(on_ell(hc, hr, x, -0.095 + 0.035 * max(0, (abs(x) - 0.08) / 0.045) ** 1.5, 1.035))
    lib.tube(P + 'grin', pts, [0.005] + [0.008] * 7 + [0.005], mouth, H)

    # arms raised up and out, fireballs for hands. Mesh hangs straight down; the rest pose lifts it.
    for s, nm, ph in ((-1, 'L', 0.0), (1, 'R', 0.5)):
        ap = lib.pivot(P + 'arm' + nm, (s * 0.2, 0, 0.19), B, rot=(0, -s * R(118), 0))
        lib.sphere(P + 'sho' + nm, (0, 0, 0), 0.095, orr, ap)
        lib.tube(P + 'armm' + nm, [(0, 0, 0), (0, 0, -0.22), (0, 0, -0.44)], [0.095, 0.082, 0.075], orr, ap)
        lib.torus(P + 'band' + nm, (0, 0, -0.26), 0.078, 0.03, M['rd'], ap)
        up = (s * 0.88, 0, -0.47)        # world-up seen from the raised arm
        hz = -0.54
        lib.sphere(P + 'ball' + nm, (0, 0, hz), 0.15, M['rd'], ap)
        lib.sphere(P + 'ballo' + nm, (0, -0.035, hz), 0.128, M['orr'], ap)
        lib.sphere(P + 'bally' + nm, (0, -0.085, hz), 0.085, M['ye'], ap)
        lib.sphere(P + 'ballp' + nm, (0, -0.15, hz), (0.035, 0.03, 0.035), M['pl'], ap)
        drop(lib, P + 'bf_a' + nm, 0.12, 0.36, M['rd'], ap, (up[0] * 0.06, 0.02, hz + up[2] * 0.06), d=up, flat=0.9, base=0.85)
        drop(lib, P + 'bf_b' + nm, 0.075, 0.26, M['orr'], ap, (up[0] * 0.08, -0.07, hz + up[2] * 0.08), d=(up[0], -0.1, up[2]), flat=0.8, base=0.85)
        rig.arms.append((ap, ph))
        rig.t_pose[ap.name] = (0, -s * R(90), 0)

    # floating embers
    em = embers(lib, P, B, (0, 0, 0.0), [(0.4, 0.75, -0.2, 0.03), (2.2, 0.8, -0.35, 0.025), (3.5, 0.7, -0.6, 0.028),
                                          (5.0, 0.78, -0.65, 0.024), (1.2, 0.6, 0.85, 0.022), (4.2, 0.55, 0.2, 0.02)], [M['ye'], M['orr']])
    rig.extras.append((em, 'spin'))

    rig.attack_origin = (0, -0.5, 1.3)
    return rig
