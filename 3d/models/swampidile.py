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


def build(lib):
    P = 'swi_'
    rig = lib.Rig('Swampidile', 'swampidile', 'Grass', height_cm=40, gait='walk', attack='cast')
    R = math.radians
    dk = lib.mat(P + 'dk', '#1f5a2e', 0.5)
    md = lib.mat(P + 'md', '#3f9a4a', 0.45, coat=0.3, sss=0.1)
    bs = lib.mat(P + 'bs', '#5cbf5a', 0.4, coat=0.4, sss=0.15)
    lt = lib.mat(P + 'lt', '#9ee07a', 0.4, coat=0.3, sss=0.2)
    belly = lib.mat(P + 'belly', '#e6e8a8', 0.5, sss=0.1)
    blush = lib.mat(P + 'blush', '#f09ab0', 0.6)
    dark = lib.mat(P + 'dark', '#1a2a1a', 0.5)

    rig.body = lib.pivot(P + 'body', (0, 0, 0.2), rig.root)
    B = rig.body

    # segmented body
    seg_y = [-0.3 + i * 0.2 for i in range(6)]
    seg_r = [0.17, 0.18, 0.18, 0.175, 0.16, 0.14]
    for i, (y, r) in enumerate(zip(seg_y, seg_r)):
        lib.sphere(f'{P}seg{i}', (0, y, 0.0), (r, r * 0.8, r * 0.95), bs, B)
        # darker saddle on the back of each bump
        lib.sphere(f'{P}sad{i}', (0, y + 0.02, r * 0.42), (r * 0.62, r * 0.5, r * 0.58), md, B)
    # belly stripe
    by = [-0.42, -0.2, 0.1, 0.4, 0.62, 0.76]
    bt = lib.tube(P + 'belly', [(0, y, -0.105) for y in by], [0.12, 0.16, 0.165, 0.155, 0.13, 0.08], belly, B)
    bt.scale = (1, 1, 0.45)
    bt.location = (0, 0, -0.058)

    # six pairs of short legs
    for i, y in enumerate(seg_y):
        for s, nm in ((-1, 'L'), (1, 'R')):
            ph = (i * 0.17 + (0 if s < 0 else 0.5)) % 1.0
            lp = lib.pivot(f'{P}leg{nm}{i}', (s * 0.12, y, -0.06), B)
            lib.tube(f'{P}legm{nm}{i}', [(0, 0, 0), (s * 0.08, 0, -0.02), (s * 0.11, -0.01, -0.075), (s * 0.115, -0.015, -0.11)],
                     [0.05, 0.045, 0.036, 0.032], md, lp)
            lib.sphere(f'{P}foot{nm}{i}', (s * 0.12, -0.035, -0.113), (0.042, 0.06, 0.027), dk, lp)
            rig.legs.append((lp, ph))

    # head
    rig.head = lib.pivot(P + 'head', (0, -0.4, 0.03), B)
    H = rig.head
    hc, hr = (0, -0.16, 0.05), (0.215, 0.22, 0.195)
    sc, sr = (0, -0.34, -0.005), (0.15, 0.17, 0.12)
    lib.sphere(P + 'skull', hc, hr, bs, H)
    lib.sphere(P + 'snout', sc, sr, bs, H)
    lib.sphere(P + 'chin', (0, -0.22, -0.07), (0.16, 0.2, 0.09), belly, H)
    for s, nm in ((-1, 'L'), (1, 'R')):
        ex, ez = s * 0.125, 0.075
        p = on_ell(hc, hr, ex, ez, 0.97)
        lib.eye(f'{P}eye{nm}', p, 0.082, H, iris='#2a1a10', look=(s * 0.55, -1, 0.12), iris_frac=0.7)
        lib.sphere(f'{P}blush{nm}', on_ell(hc, hr, s * 0.165, -0.035, 1.0), (0.04, 0.02, 0.026), blush, H,
                   rot=(0, 0, s * R(50)))
        lib.sphere(f'{P}nos{nm}', on_ell(sc, sr, s * 0.04, 0.07, 1.0), 0.011, dark, H)
    # smile
    pts = []
    for k in range(9):
        x = -0.125 + 0.25 * k / 8
        z = -0.03 + 0.045 * (abs(x) / 0.125) ** 2.2
        pts.append(on_ell(sc, sr, x, z, 1.005))
    lib.tube(P + 'smile', pts, [0.008] * 9, dark, H)

    # sprout with two veined leaves
    sp = lib.pivot(P + 'sprout', (0, -0.14, 0.235), H)
    lib.tube(P + 'stem', [(0, 0, -0.03), (0, 0.01, 0.1), (0, -0.01, 0.22)], [0.022, 0.018, 0.015], dk, sp)
    top = (0, -0.01, 0.215)
    yaw = R(22)
    for s, nm, m_ in ((-1, 'L', bs), (1, 'R', lt)):
        ax = (s * math.cos(yaw) * 0.9, -s * math.sin(yaw) * 0.9, 0.34)
        side = (s * math.sin(yaw), math.cos(yaw), 0)
        leaf(lib, f'{P}leaf{nm}', top, ax, side, 0.38, 0.125, m_, sp, arch=0.05 * s)
        a = Vector(ax).normalized()
        upv = Vector(side).normalized().cross(a) * s
        vp = [tuple(Vector(top) + a * 0.38 * t + upv * (0.05 * math.sin(math.pi * t * 0.9) + 0.007)) for t in (0, 0.3, 0.6, 0.92)]
        lib.tube(f'{P}vein{nm}', vp, [0.009, 0.008, 0.006, 0.003], md, sp)
    lib.sphere(P + 'bud', top, 0.028, dk, sp)
    rig.extras.append((sp, 'sway'))

    # curled tail: 7 short links, every other one is an animated tail joint
    prev, ploc = B, (0, 0.72, 0.0)
    n = 7
    lens = [0.105, 0.1, 0.095, 0.09, 0.08, 0.07, 0.06]
    rads = [0.115, 0.1, 0.088, 0.076, 0.064, 0.052, 0.04, 0.028]
    curl = [38, 36, 36, 36, 36, 34, 30]
    for i in range(n):
        tp = lib.pivot(f'{P}tail{i}', ploc, prev, rot=(R(curl[i]), 0, 0))
        m_ = md if i < 3 else bs
        lib.sphere(f'{P}tailj{i}', (0, 0, 0), rads[i], m_, tp)
        lib.tube(f'{P}tailm{i}', [(0, 0, 0), (0, lens[i] / 2, 0), (0, lens[i], 0)],
                 [rads[i], (rads[i] + rads[i + 1]) / 2, rads[i + 1]], m_, tp)
        if i % 2 == 0 and i < 6:
            rig.tail.append(tp)
        rig.t_pose[tp.name] = (R(10) if i == 0 else R(3), 0, 0)
        prev, ploc = tp, (0, lens[i], 0)
    lib.sphere(P + 'tailtip', (0, lens[-1], 0), rads[-1], bs, prev)

    rig.attack_origin = (0, -0.75, 0.6)
    return rig
