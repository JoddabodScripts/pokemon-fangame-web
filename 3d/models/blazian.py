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
    """Blazian as a floating sun spirit: a glowing sun body with the face on it, a corona of flames,
    two fireball hands floating at its sides and a flame wisp instead of legs."""
    P = 'blz_'
    rig = lib.Rig('Blazian', 'blazian', 'Fire', height_cm=200, gait='float', attack='cast')
    R = math.radians
    M = fire_mats(lib, P)
    sunb = lib.mat(P + 'sunbody', '#ffae1a', 0.35, emit=0.55, emit_color='#ffb030', sss=0.3, coat=0.35)
    rim = lib.mat(P + 'rim', '#f06412', 0.4, emit=0.4, coat=0.2)
    face = lib.mat(P + 'face', '#ffe49a', 0.35, emit=0.35, sss=0.2, coat=0.3)
    glow = lib.mat(P + 'glow', '#ffd84a', 0.3, emit=3.0)
    dark = lib.mat(P + 'dark', '#6a140a', 0.5)
    mouth = lib.mat(P + 'mouth', '#7a1a10', 0.5)
    tongue = lib.mat(P + 'tongue', '#ff6a5a', 0.4, sss=0.2)
    fang = lib.mat(P + 'fang', '#ffffff', 0.25, emit=0.3)
    blush = lib.mat(P + 'blush', '#ff5a3a', 0.4, emit=0.3)

    rig.body = lib.pivot(P + 'body', (0, 0, 1.0), rig.root)
    B = rig.body
    hc, hr = (0, 0, 0), (0.42, 0.37, 0.42)

    # ---- the sun: core, darker rim behind, glow ring
    lib.sphere(P + 'core', hc, hr, sunb, B, seg=48)
    lib.sphere(P + 'rimback', (0, 0.07, 0), (0.44, 0.3, 0.44), rim, B, seg=40)
    lib.torus(P + 'halo', (0, 0.06, 0), 0.47, 0.035, glow, B, rot=(math.pi / 2, 0, 0))

    # ---- corona: long and short flames all the way round, plus a yellow inner ring
    C = lib.pivot(P + 'corona', (0, 0.05, 0), B)
    for q in range(16):
        a = q * math.pi / 8 + 0.1
        dx, dz = math.sin(a), math.cos(a)
        long_ = q % 2 == 0
        drop(lib, f'{P}cor{q}', 0.12 if long_ else 0.09, 0.42 if long_ else 0.28, M['rd'] if long_ else M['orr'], C,
             (dx * 0.36, 0.02, dz * 0.36), d=(dx, 0.08, dz), bend=(0.05 * dz, 0) if long_ else (0, 0), flat=0.7, base=0.8)
        if long_:
            drop(lib, f'{P}cori{q}', 0.06, 0.24, M['ye'], C, (dx * 0.4, -0.04, dz * 0.4), d=(dx, -0.02, dz), flat=0.6, base=0.8)
    rig.extras.append((C, 'pulse'))

    # ---- face (its own pivot so it can nod across the sun)
    rig.head = lib.pivot(P + 'head', (0, 0, 0), B)
    H = rig.head
    decal(lib, P + 'facep', oval(0.27, 0.24, 0, -0.02), hc, hr, face, H, lift=1.006, n=1, rings=6)
    for sd in (-1, 1):
        p = on_ell(hc, hr, sd * 0.125, 0.05, 0.99)
        big_eye(lib, f'{P}eye{sd}', p, 0.085, H, (sd * 0.25, -1, 0.06), P, iris='#ff9a1a', ring='#8a2a08', pupil='#2a0a06')
        lib.tube(f'{P}brow{sd}', [on_ell(hc, hr, sd * 0.05, 0.16, 1.035), on_ell(hc, hr, sd * 0.13, 0.19, 1.04),
                                  on_ell(hc, hr, sd * 0.21, 0.175, 1.03)], [0.014, 0.02, 0.012], dark, H)
        decal(lib, f'{P}mark{sd}', [(sd * 0.27, -0.06), (sd * 0.2, -0.03), (sd * 0.2, -0.1)], hc, hr, M['rd'], H, lift=1.025, rings=3)
        lib.sphere(f'{P}blush{sd}', on_ell(hc, hr, sd * 0.22, -0.1, 1.0), (0.045, 0.012, 0.03), blush, H, seg=12)
    decal(lib, P + 'mouth', [(-0.11, -0.12), (0.11, -0.12), (0.06, -0.2), (-0.06, -0.2)], hc, hr, mouth, H, lift=1.02)
    decal(lib, P + 'tongue', oval(0.04, 0.025, 0, -0.18), hc, hr, tongue, H, lift=1.03, n=1, rings=3)
    for sd in (-1, 1):
        fp = on_ell(hc, hr, sd * 0.07, -0.125, 1.0)
        lib.cone(f'{P}fang{sd}', (fp[0], fp[1] - 0.012, fp[2] - 0.02), 0.02, 0.0, 0.055, fang, H, rot=_aim((0, 0.35, -1)), seg=10)

    # ---- two fireball hands, floating at the sides (pivot at the body centre, so they can orbit)
    rig.hands = []
    for sd, nm, ph in ((-1, 'L', 0.0), (1, 'R', 0.5)):
        hp = lib.pivot(P + 'hand' + nm, (0, 0, 0), B)
        x, z = sd * 0.74, -0.08
        lib.sphere(P + 'ball' + nm, (x, 0, z), 0.16, M['rd'], hp)
        lib.sphere(P + 'ballo' + nm, (x, -0.035, z), 0.135, M['orr'], hp)
        lib.sphere(P + 'bally' + nm, (x, -0.085, z), 0.09, M['ye'], hp)
        lib.sphere(P + 'ballp' + nm, (x, -0.15, z), (0.04, 0.03, 0.04), M['pl'], hp)
        drop(lib, P + 'bf_a' + nm, 0.12, 0.34, M['rd'], hp, (x + sd * 0.03, 0.02, z + 0.05), d=(sd * 0.35, 0, 1), flat=0.9, base=0.85)
        drop(lib, P + 'bf_b' + nm, 0.075, 0.24, M['orr'], hp, (x - sd * 0.04, -0.06, z + 0.06), d=(-sd * 0.2, -0.1, 1), flat=0.8, base=0.85)
        drop(lib, P + 'bf_c' + nm, 0.06, 0.18, M['ye'], hp, (x + sd * 0.07, -0.05, z + 0.03), d=(sd * 0.8, -0.1, 0.6), flat=0.8, base=0.85)
        rig.arms.append((hp, ph))
        rig.hands.append((hp, sd))

    # ---- flame wisp underneath instead of legs
    F = lib.pivot(P + 'wisp', (0, 0.02, -0.34), B)
    drop(lib, P + 'wisp_r', 0.22, 0.62, M['rd'], F, (0, 0, 0.05), d=(0, 0.1, -1), bend=(0.06, 0), flat=0.85, base=0.9)
    drop(lib, P + 'wisp_o', 0.15, 0.44, M['orr'], F, (0, -0.04, 0.04), d=(0, 0.05, -1), bend=(-0.04, 0), flat=0.8, base=0.9)
    drop(lib, P + 'wisp_y', 0.09, 0.26, M['ye'], F, (0, -0.07, 0.03), d=(0, 0, -1), flat=0.8, base=0.9)
    rig.extras.append((F, 'flicker'))
    rig.wisp = F

    em = embers(lib, P, B, (0, 0, 0.0), [(0.4, 0.95, -0.3, 0.03), (2.2, 0.9, -0.45, 0.025), (3.5, 0.85, -0.7, 0.028),
                                          (5.0, 0.9, -0.75, 0.024), (1.2, 0.75, 0.75, 0.022), (4.2, 0.7, 0.4, 0.02)], [M['ye'], M['orr']])
    rig.extras.append((em, 'spin'))
    rig.embers = em
    rig.attack_origin = (0, -0.6, 1.0)
    rig.t_pose = {}
    return rig


def animate(A):
    """Blazian, sun spirit: ignites inside a pillar of flame as its corona bursts open and its hands fly
    in, floats across trailing embers with the wisp streaming behind, then Flames of Health: the hands
    meet in front, charge a sun orb, blast a stream of fire, and golden sparks spiral in as it heals."""
    import bpy
    import anim_kit as K
    from anim_kit import E, spring, decay
    from mathutils import Vector
    r, T, s, lib = A.rig, A.T, A.size, A.lib
    root, B, H, C, F, em = r.root, r.body, r.head, bpy.data.objects['blz_corona'], r.wisp, r.embers
    eyes = [bpy.data.objects['blz_eye-1'], bpy.data.objects['blz_eye1']]
    sunb = lib.mat('blz_sunbody', '#ffae1a')
    face = lib.mat('blz_face', '#ffe49a')
    halo = lib.mat('blz_glow', '#ffd84a')
    pi = math.pi
    win = K.win
    D = 1.5 * s
    aim = 0.6

    def walk_x(f):
        return D * E(f, 80, 128)

    A.key(root, 0, scale=0.001)
    A.key(root, T['OUT'] - 1, scale=0.001)
    for f in range(T['OUT'], T['END'] + 1):
        app = spring((f - 20) / 9, 4, 8)
        x = walk_x(f)
        yaw = (pi / 2) * win(f, 72, 79, 129, 137) + aim * win(f, 141, 147, 178, 185)
        kb = win(f, 186, 190, 200, 212)
        hover = 0.06 * s + 0.035 * s * math.sin(2 * pi * f / 36)
        A.key(root, f, loc=(x - 0.15 * s * kb * math.sin(aim), 0.3 * s * kb, hover), rot=(0, 0, yaw), scale=max(0.001, app))

        W = win(f, 78, 84, 124, 130)
        cry = win(f, 37, 40, 45, 48)
        idle = math.sin(2 * pi * f / 36)
        charge = win(f, 141, 147, 152, 154)
        thrust = win(f, 153, 156, 164, 170)
        heal = win(f, 166, 170, 180, 185)
        hitw = decay(f, 186, 6, 1.0)
        stag = win(f, 186, 189, 198, 206)
        victory = win(f, 211, 216, 230, 240)

        # sun body: lean into travel, swell when charging, squash when hit
        sq = 1 + 0.08 * charge + 0.05 * cry - 0.12 * max(0, hitw) + 0.04 * heal
        A.key(B, f, rot=(0.18 * W + 0.12 * thrust - 0.1 * cry + 0.2 * stag - 0.08 * victory, 0.1 * hitw, 0.05 * idle * (1 - W)),
              scale=(sq * (1 + 0.06 * max(0, hitw)), sq, sq * (1 - 0.06 * max(0, hitw))))
        # face: nods, looks around, scrunches when hit
        look = win(f, 52, 56, 66, 70) * math.sin(2 * pi * (f - 52) / 22)
        A.key(H, f, rot=(-0.12 * cry + 0.08 * charge + 0.15 * stag - 0.1 * victory, 0, 0.18 * look))
        blink = max(win(f, x0, x0 + 1, x0 + 2, x0 + 4) for x0 in (55, 66, 100, 194))
        for e in eyes:
            A.key(e, f, scale=(1, 1, 1 - max(0.9 * blink, 0.45 * charge, 0.5 * stag)))
        # corona: bursts open, spins, flares, sputters, re-ignites
        burst = spring((f - 26) / 7, 4, 9)
        sput = 1 - 0.4 * win(f, 186, 188, 200, 210) + 0.08 * math.sin(f * 1.9) * win(f, 186, 190, 204, 210)
        flare = 0.25 * cry + 0.3 * charge + 0.15 * thrust + 0.35 * win(f, 210, 214, 216, 222) + 0.12 * heal + 0.05 * idle
        A.key(C, f, rot=(0, 0.015 * f + 0.6 * E(f, 141, 154), 0), scale=max(0.001, burst * sput * (1 + flare)))
        # hands: fly in, bob, raise for the cry, come together in front to charge, thrust, scatter, cheer
        for hp, sd in r.hands:
            fly_in = 1 - spring((f - 24) / 8, 4, 8)
            bob = 0.12 * math.sin(2 * pi * f / 28 + (0 if sd < 0 else pi))
            raise_ = -sd * (0.6 * cry + 0.75 * victory)
            front = -sd * (1.25 * charge + 1.35 * thrust)
            scatter = 0.6 * max(0, hitw) * sd
            swing = 0.35 * math.sin(2 * pi * f / 16 + (0 if sd < 0 else pi)) * W
            A.key(hp, f, rot=(swing, raise_ + bob * (1 - charge) + scatter - sd * 0.5 * fly_in, front),
                  scale=max(0.001, 1 - 0.9 * fly_in + 0.12 * charge))
        # wisp streams back when moving, gutters when hit
        A.key(F, f, rot=(-0.55 * W - 0.3 * kb + 0.15 * math.sin(f * 0.5), 0, 0.12 * math.sin(f * 0.37)),
              scale=(1, 1, 1 + 0.35 * W + 0.15 * math.sin(f * 0.8) - 0.3 * win(f, 186, 188, 200, 206)))
        A.key(em, f, rot=(0, 0, f * (0.06 + 0.15 * heal)))

    for f, v in [(0, 0.55), (140, 0.55), (150, 2.5), (156, 1.5), (166, 1.5), (172, 3.0), (184, 0.55), (187, 0.15), (200, 0.35), (214, 1.6), (224, 0.55)]:
        A.emission(sunb, f, v)
    for f, v in [(0, 0.35), (166, 0.35), (172, 1.4), (184, 0.35)]:
        A.emission(face, f, v)
    for f, v in [(0, 3.0), (186, 0.5), (205, 0.8), (214, 5.0), (224, 3.0)]:
        A.emission(halo, f, v)

    fire_r = lib.mat('blz_fx_red', '#ff3c00', 0.3, emit=3.0)
    fire_y = lib.mat('blz_fx_ye', '#ffb020', 0.3, emit=4.0)
    core = lib.mat('blz_fx_core', '#fff0a0', 0.2, emit=6.0)
    # ---------------------------------------------------- send-out: fire ring and flame pillar
    K.ring(A, 'blz_fx_ring', (0, 0, 0.03), 16, dur=12, r0=0.1, r1=0.9, thick=0.06, mat=fire_r)
    pil = lib.pivot('blz_fx_pillar')
    for i in range(5):
        lib.cone(f'blz_fx_pil{i}', (0.08 * math.sin(i * 2.1), 0.08 * math.cos(i * 2.1), 0.5), 0.26 - 0.03 * i, 0.0, 1.0 + 0.15 * i,
                 fire_r if i % 2 else fire_y, pil, seg=12)
    for f, sz, w in [(0, 0.001, 0.001), (16, 0.001, 0.001), (19, 1.2, 0.9), (24, 1.5, 0.8), (29, 0.8, 0.5), (33, 0.001, 0.001)]:
        A.key(pil, f, scale=(w * s * 0.8, w * s * 0.8, sz * s * 0.9) if sz > 0.001 else 0.001, absolute=True)
    A.light('blz_fx_pillight', '#ff8030', (0, -0.5 * s, 0.9 * s), [(0, 0), (16, 0), (20, 900 * s * s), (34, 0)])
    K.burst(A, 'blz_fx_cryembers', (0, 0, 0.7 * s), 38, n=18, dur=16, speed=0.9, up=0.9, gravity=0.6, size=0.025, mat=fire_y, seed=1)
    # ---------------------------------------------------- ember trail while floating across
    for n, f0 in enumerate(range(84, 128, 4)):
        p = A.world(F, f0, (0, 0.1, -0.4))
        K.burst(A, f'blz_fx_trail{n}', p, f0, n=3, dur=10, speed=0.2, up=0.3, gravity=0.3, size=0.02,
                mat=fire_y if n % 2 else fire_r, seed=n)
    # ---------------------------------------------------- Flames of Health
    front = A.world(B, 152, (0, -0.75, -0.05))
    orb = lib.pivot('blz_fx_orb')
    lib.sphere('blz_fx_orbc', (0, 0, 0), 0.6, core, orb, seg=20)
    lib.sphere('blz_fx_orbs', (0, 0, 0), 1.0, lib.mat('blz_fx_orbshell', '#ff7a1a', 0.3, emit=2.5, alpha=0.6), orb, seg=20)
    for f, sc in [(0, 0.001), (143, 0.001), (146, 0.05), (152, 0.15), (154, 0.19), (156, 0.001)]:
        A.key(orb, f, loc=front, scale=sc * s if sc > 0.001 else 0.001, absolute=True)
    A.light('blz_fx_orblight', '#ffa040', front, [(0, 0), (143, 0), (153, 700 * s * s), (157, 0)])
    tgt = A.opponent(front)
    for j in range(7):
        K.projectile(A, f'blz_fx_blast{j}', front + Vector((0, 0, 0.03 * s * (j % 3 - 1))), tgt, 155 + j, flight=8,
                     mat=fire_y if j % 2 else fire_r, radius=0.07 + 0.01 * (j % 3), trail=2)
    K.flash_sphere(A, 'blz_fx_muzzle', front, 155, dur=6, r1=0.22, mat=core)
    heal_m = lib.mat('blz_fx_heal', '#ffe66a', 0.3, emit=5.0)
    here = A.world(root, 168)
    K.swirl(A, 'blz_fx_heal', (here.x, here.y, 0.05), 166, dur=22, n=18, radius=0.6, height=1.9, turns=1.3, mat=heal_m, size=0.022, inward=True)
    K.ring(A, 'blz_fx_healring', (here.x, here.y, 0.04), 168, dur=14, r0=0.9, r1=0.2, thick=0.03, mat=heal_m)
    A.light('blz_fx_heallight', '#ffe080', here + Vector((0, -0.4 * s, 1.0 * s)), [(0, 0), (166, 0), (172, 500 * s * s), (184, 0)])
    vic = A.world(B, 214)
    K.burst(A, 'blz_fx_reflare', vic, 213, n=18, dur=16, speed=1.0, up=0.9, gravity=0.5, size=0.025, mat=fire_y, seed=4)


# Phase speeds for render.retime: above 1 is slower and longer, below 1 is quicker.
TIMING = {'send': 1.5, 'idle': 1.3, 'walk': 1.2, 'attack': 1.6, 'hit': 1.2, 'recover': 1.4}
