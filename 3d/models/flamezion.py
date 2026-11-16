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
    P = 'flz_'
    rig = lib.Rig('Flamezion', 'flamezion', 'Fire', height_cm=90, gait='float', attack='cast')
    R = math.radians
    M = fire_mats(lib, P)
    body = lib.mat(P + 'body', '#c82c10', 0.4, emit=0.04, coat=0.35)
    bor = lib.mat(P + 'bor', '#f06812', 0.4, emit=0.12, coat=0.3)
    bye = lib.mat(P + 'bye', '#ffbe24', 0.4, emit=0.25, coat=0.3)
    bhl = lib.mat(P + 'bhl', '#ff9a50', 0.4, emit=0.2, coat=0.3)
    cheek = lib.mat(P + 'cheek', '#ff6a70', 0.5, emit=0.1)
    mouth = lib.mat(P + 'mouth', '#5a1010', 0.5)
    tongue = lib.mat(P + 'tongue', '#ff6a7a', 0.45)
    eyem = lib.mat(P + 'eye', '#1a1010', 0.08, coat=1)
    white = lib.mat(P + 'white', '#ffffff', 0.2, emit=1.5)
    fang = lib.mat(P + 'fang', '#ffffff', 0.25, coat=0.5, emit=0.2)

    rig.body = lib.pivot(P + 'body', (0, 0, 0.0), rig.root)
    B = rig.body
    c, rr = (0, 0, 0.58), (0.42, 0.4, 0.42)
    lib.sphere(P + 'ball', c, rr, body, B, seg=40)
    decal(lib, P + 'band1', oval(0.31, 0.31, 0, -0.02), c, rr, bor, B, lift=1.006, n=1, rings=6)
    decal(lib, P + 'band2', oval(0.235, 0.17, 0, -0.17), c, rr, bye, B, lift=1.012, n=1)
    decal(lib, P + 'hl', oval(0.085, 0.05, -0.15, 0.24), c, rr, bhl, B, lift=1.012, n=1)

    # face
    rig.head = lib.pivot(P + 'head', (0, 0, 0.3), B)
    H = rig.head
    hc = (0, 0, c[2] - 0.3)
    for s in (-1, 1):
        p = on_ell(hc, rr, s * 0.15, 0.1, 1.0)
        e = lib.pivot(f'{P}eye{s}', p, H)
        e.rotation_euler = Vector((0, -1, 0)).rotation_difference(ell_n(hc, rr, p)).to_euler()
        lib.sphere(f'{P}eyeb{s}', (0, 0, 0), (0.07, 0.035, 0.105), eyem, e)
        lib.sphere(f'{P}eyes{s}', (-0.022, -0.03, 0.045), (0.026, 0.012, 0.032), white, e)
        lib.sphere(f'{P}eyet{s}', (0.022, -0.031, -0.04), (0.012, 0.006, 0.014), white, e)
        lib.sphere(f'{P}cheek{s}', on_ell(hc, rr, s * 0.29, -0.06, 0.995), (0.07, 0.03, 0.04), cheek, H, rot=(0, 0, s * R(42)))
        fp = on_ell(hc, rr, s * 0.135, -0.075, 1.0)
        f = lib.cone(f'{P}fang{s}', (fp[0], fp[1] - 0.012, fp[2] - 0.035), 0.03, 0.0, 0.09, fang, H, rot=_aim((0, 0.3, -1)), seg=12)
    decal(lib, P + 'mouth', [(-0.2, -0.06), (0.2, -0.06), (0.12, -0.21), (-0.12, -0.21)], hc, rr, mouth, H, lift=1.02)
    decal(lib, P + 'tongue', oval(0.085, 0.04, 0, -0.185), hc, rr, tongue, H, lift=1.028, n=1)
    pts = []
    for k in range(11):
        x = -0.25 + 0.5 * k / 10
        pts.append(on_ell(hc, rr, x, -0.06 + 0.05 * max(0, (abs(x) - 0.17) / 0.08) ** 1.5, 1.025))
    lib.tube(P + 'grin', pts, [0.006] + [0.011] * 9 + [0.006], mouth, H)

    # crown of five layered flame spikes
    cr = lib.pivot(P + 'crown', (0, 0, 0.9), B)
    angs = [-64, -33, 0, 33, 64]
    hs = [0.36, 0.48, 0.56, 0.48, 0.36]
    for i, (a, h) in enumerate(zip(angs, hs)):
        a = R(a)
        o = (0.33 * math.sin(a), 0.03, 0.33 * math.cos(a) - 0.32)
        drop(lib, f'{P}cr_r{i}', 0.125, h, M['rd'], cr, o, d=(math.sin(a), 0, math.cos(a)), bend=(0.07 - 0.05 * math.sin(a), 0), flat=0.85)
        a2 = a * 0.88
        o = (0.31 * math.sin(a2), -0.09, 0.31 * math.cos(a2) - 0.32)
        drop(lib, f'{P}cr_o{i}', 0.09, h * 0.68, M['orr'], cr, o, d=(math.sin(a2), -0.08, math.cos(a2)), flat=0.75)
        # a second red row behind so the crown is not flat from the side
        a3 = a * 0.7
        o = (0.3 * math.sin(a3), 0.15, 0.3 * math.cos(a3) - 0.33)
        drop(lib, f'{P}cr_b{i}', 0.1, h * 0.6, M['rd'], cr, o, d=(math.sin(a3), 0.3, math.cos(a3)), flat=0.9)
    for i, a in enumerate([-30, 0, 30]):
        a = R(a)
        o = (0.29 * math.sin(a), -0.16, 0.29 * math.cos(a) - 0.33)
        drop(lib, f'{P}cr_y{i}', 0.062, 0.24 if i == 1 else 0.2, M['ye'], cr, o, d=(math.sin(a), -0.15, math.cos(a)), flat=0.7)
    rig.extras.append((cr, 'flicker'))

    # side wisps
    for s, nm in ((-1, 'L'), (1, 'R')):
        wp = lib.pivot(P + 'wisp' + nm, (s * 0.38, 0, 0.55), B)
        drop(lib, P + 'w_a' + nm, 0.11, 0.34, M['rd'], wp, (0, 0, 0.03), d=(s, 0, 0.6), bend=(0, 0), flat=0.85)
        drop(lib, P + 'w_b' + nm, 0.095, 0.26, M['rd'], wp, (0, 0, -0.04), d=(s, 0, -0.35), flat=0.85)
        drop(lib, P + 'w_c' + nm, 0.06, 0.2, M['orr'], wp, (s * 0.02, -0.07, 0.0), d=(s, -0.1, 0.2), flat=0.8)
        rig.extras.append((wp, 'flicker'))
        rig.t_pose[wp.name] = (0, 0, 0)

    # flickering base instead of feet
    bp = lib.pivot(P + 'base', (0, 0, 0.36), B)
    for i in range(8):
        a = 2 * math.pi * i / 8
        x, y = math.cos(a), math.sin(a)
        drop(lib, f'{P}b_r{i}', 0.1, 0.3 if i % 2 else 0.25, M['rd'], bp, (x * 0.2, y * 0.19, 0), d=(x * 0.28, y * 0.28, -1))
    for i in range(5):
        a = 2 * math.pi * (i + 0.5) / 5
        x, y = math.cos(a), math.sin(a)
        drop(lib, f'{P}b_o{i}', 0.075, 0.26, M['orr'], bp, (x * 0.08, y * 0.08 - 0.03, -0.05), d=(x * 0.1, y * 0.1, -1))
    rig.extras.append((bp, 'flicker'))

    rig.attack_origin = (0, -0.5, 0.6)
    return rig
