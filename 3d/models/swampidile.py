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


def skin(lib, name, c1, c2, scale=5.0, rough=0.3, coat=0.7, sss=0.1, lo=0.42, hi=0.62):
    """Glossy skin with a soft two-tone mottle, so it never reads as flat plastic."""
    m = lib.mat(name, c1, rough, sss=sss, coat=coat)
    nt = m.node_tree
    if 'mottle' in nt.nodes:
        return m
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    tex = nt.nodes.new('ShaderNodeTexNoise')
    tex.name = 'mottle'
    tex.inputs['Scale'].default_value = scale
    tex.inputs['Detail'].default_value = 1.5
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = lo, hi
    ramp.color_ramp.elements[0].color = (*lib._rgb(c1), 1)
    ramp.color_ramp.elements[1].color = (*lib._rgb(c2), 1)
    nt.links.new(tc.outputs['Object'], tex.inputs['Vector'])
    nt.links.new(tex.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    return m


def build(lib):
    P = 'swi_'
    rig = lib.Rig('Swampidile', 'swampidile', 'Grass', height_cm=40, gait='walk', attack='cast')
    R = math.radians
    dk = skin(lib, P + 'dk', '#1f5a2e', '#2c7038', 9, 0.35, 0.6, 0.05)
    md = skin(lib, P + 'md', '#2f8a40', '#47a650', 7, 0.28, 0.8, 0.1)
    bs = skin(lib, P + 'bs', '#58bd58', '#7ad268', 4, 0.22, 1.0, 0.15)
    lt = skin(lib, P + 'lt', '#9ee07a', '#c4f094', 6, 0.3, 0.7, 0.2)
    lf = skin(lib, P + 'lf', '#5cbf5a', '#86d870', 6, 0.3, 0.7, 0.2)
    hl = lib.mat(P + 'hl', '#d4f7a8', 0.25, coat=0.8, emit=0.15)
    belly = skin(lib, P + 'belly', '#e6e8a8', '#cfd088', 10, 0.35, 0.6, 0.15)
    blush = lib.mat(P + 'blush', '#f58aa8', 0.5, sss=0.2)
    dark = lib.mat(P + 'dark', '#16301c', 0.4, coat=0.5)
    mud = lib.mat(P + 'mud', '#6a4a2c', 0.25, coat=0.9)
    dew = lib.mat(P + 'dew', '#d8f4ff', 0.03, coat=1.0, emit=0.35, transmission=0.6)
    X = rig.x = dict(segs=[], legs=[], eyes=[], leaves=[], tail=[])

    rig.body = lib.pivot(P + 'body', (0, 0, 0.215), rig.root)
    B = rig.body

    # segmented body: every bump is its own joint so a wave can run down it
    seg_y = [-0.3 + i * 0.2 for i in range(6)]
    seg_r = [0.185, 0.195, 0.195, 0.185, 0.17, 0.15]
    X['seg_y'] = seg_y
    for i, (y, r) in enumerate(zip(seg_y, seg_r)):
        S = lib.pivot(f'{P}segp{i}', (0, y, 0), B)
        X['segs'].append(S)
        lib.sphere(f'{P}seg{i}', (0, 0, 0.0), (r, r * 0.78, r * 0.95), bs, S)
        lib.sphere(f'{P}bel{i}', (0, 0, -r * 0.33), (r * 0.8, r * 0.76, r * 0.66), belly, S)
        # darker saddle hugging the back of the bump, a pale spot each side, a shine
        lib.sphere(f'{P}sad{i}', (0, 0.012, r * 0.2), (r * 0.74, r * 0.62, r * 0.79), md, S)
        for s in (-1, 1):
            lib.sphere(f'{P}spot{i}{s}', (s * r * 0.84, 0, r * 0.18), (r * 0.2, r * 0.22, r * 0.2), lt, S)
        lib.sphere(f'{P}shine{i}', (-r * 0.3, -r * 0.3, r * 0.86), (r * 0.16, r * 0.1, r * 0.07), hl, S, rot=(R(-25), R(-20), 0))
        # a pair of short legs with muddy little feet
        for s, nm in ((-1, 'L'), (1, 'R')):
            ph = (i * 0.17 + (0 if s < 0 else 0.5)) % 1.0
            lp = lib.pivot(f'{P}leg{nm}{i}', (s * r * 0.62, 0, -0.065), S)
            lib.tube(f'{P}legm{nm}{i}', [(0, 0, 0), (s * 0.085, 0, -0.01), (s * 0.125, -0.012, -0.075), (s * 0.128, -0.02, -0.122)],
                     [0.055, 0.05, 0.04, 0.036], md, lp)
            lib.sphere(f'{P}foot{nm}{i}', (s * 0.132, -0.045, -0.124), (0.048, 0.068, 0.028), dk, lp)
            for c in (-1, 1):
                lib.sphere(f'{P}toe{nm}{i}{c}', (s * 0.132 + c * 0.024, -0.1, -0.132), (0.017, 0.024, 0.014), dk, lp)
            if (i + (s > 0)) % 2 == 0:
                lib.sphere(f'{P}mud{nm}{i}', (s * 0.14, -0.03, -0.108), (0.04, 0.05, 0.022), mud, lp)
            rig.legs.append((lp, ph))
            X['legs'].append((lp, i, s))

    # head: one big round shape with a short soft snout
    rig.head = lib.pivot(P + 'head', (0, -0.4, 0.04), B)
    H = rig.head
    hc, hr = (0, -0.17, 0.06), (0.25, 0.24, 0.225)
    sc, sr = (0, -0.36, -0.01), (0.165, 0.17, 0.125)
    lib.sphere(P + 'skull', hc, hr, bs, H, seg=40)
    lib.sphere(P + 'snout', sc, sr, bs, H)
    lib.sphere(P + 'chin', (0, -0.24, -0.085), (0.18, 0.21, 0.1), belly, H)
    lib.sphere(P + 'cap', (0, -0.1, 0.13), (0.19, 0.19, 0.165), md, H)
    lib.sphere(P + 'hshine', (-0.07, -0.3, 0.2), (0.04, 0.025, 0.02), hl, H, rot=(R(-40), R(-20), 0))
    for s, nm in ((-1, 'L'), (1, 'R')):
        p = on_ell(hc, hr, s * 0.128, 0.07, 0.96)
        lib.sphere(f'{P}lid{nm}', (p[0], p[1] + 0.03, p[2] + 0.012), (0.116, 0.09, 0.118), bs, H)
        e = lib.eye(f'{P}eye{nm}', p, 0.104, H, iris='#3c2a12', pupil='#0c0c0c', look=(s * 0.42, -1, 0.1), iris_frac=0.78)
        lib.sphere(f'{P}eyeshine2{nm}', (0.03, -0.062, -0.03), (0.012, 0.006, 0.012), lib.mat('shine', '#ffffff', 0.1, emit=2), e)
        X['eyes'].append(e)
        lib.sphere(f'{P}blush{nm}', on_ell(hc, hr, s * 0.2, -0.06, 1.0), (0.046, 0.02, 0.03), blush, H, rot=(0, 0, s * R(52)))
        lib.sphere(f'{P}nos{nm}', on_ell(sc, sr, s * 0.042, 0.075, 1.0), (0.012, 0.01, 0.014), dark, H)
    pts = []
    for k in range(9):
        x = -0.135 + 0.27 * k / 8
        z = -0.035 + 0.05 * (abs(x) / 0.135) ** 2.2
        pts.append(on_ell(sc, sr, x, z, 1.005))
    lib.tube(P + 'smile', pts, [0.006] + [0.009] * 7 + [0.006], dark, H)

    # sprout with two veined leaves, each on its own joint, and a dewdrop
    sp = lib.pivot(P + 'sprout', (0, -0.14, 0.265), H)
    X['sprout'] = sp
    lib.tube(P + 'stem', [(0, 0, -0.04), (0, 0.012, 0.1), (0, -0.01, 0.22)], [0.026, 0.02, 0.016], dk, sp)
    top = (0, -0.01, 0.215)
    yaw = R(22)
    for s, nm, m_ in ((-1, 'L', lf), (1, 'R', lt)):
        lp = lib.pivot(f'{P}leafp{nm}', top, sp)
        X['leaves'].append((lp, s))
        ax = (s * math.cos(yaw) * 0.9, -s * math.sin(yaw) * 0.9, 0.34)
        side = (s * math.sin(yaw), math.cos(yaw), 0)
        leaf(lib, f'{P}leaf{nm}', (0, 0, 0), ax, side, 0.44, 0.15, m_, lp, arch=0.06 * s, n=10)
        a = Vector(ax).normalized()
        sd = Vector(side).normalized()
        upv = sd.cross(a) * s
        mid = lambda t, o=0.0: a * 0.44 * t + upv * (0.06 * math.sin(math.pi * t * 0.9) + 0.009 + o)  # noqa: E731
        lib.tube(f'{P}vein{nm}', [tuple(mid(t)) for t in (0, 0.3, 0.6, 0.93)], [0.01, 0.009, 0.006, 0.003], md, lp)
        for j, t in enumerate((0.3, 0.48, 0.66)):
            for q in (-1, 1):
                w = 0.15 * math.sin(math.pi * (0.04 + 0.93 * t ** 0.75)) * 0.7
                lib.tube(f'{P}rib{nm}{j}{q}', [tuple(mid(t)), tuple(mid(t + 0.1, w * 0.2 * 0.6) + sd * q * w)], [0.005, 0.002], md, lp, seg=8)
        if s > 0:
            lib.sphere(P + 'dew', tuple(mid(0.55, 0.022) + sd * 0.04), (0.03, 0.03, 0.024), dew, lp, seg=16)
    lib.sphere(P + 'bud', top, 0.034, md, sp)
    rig.extras.append((sp, 'sway'))

    # curled tail: 7 links hanging off the last body segment
    prev, ploc = X['segs'][-1], (0, 0.03, 0.0)
    n = 7
    lens = [0.105, 0.1, 0.095, 0.09, 0.08, 0.07, 0.06]
    rads = [0.122, 0.106, 0.092, 0.079, 0.066, 0.054, 0.042, 0.03]
    curl = [38, 36, 36, 36, 36, 34, 30]
    for i in range(n):
        tp = lib.pivot(f'{P}tail{i}', ploc, prev, rot=(R(curl[i]), 0, 0))
        m_ = md if i < 3 else bs
        lib.sphere(f'{P}tailj{i}', (0, 0, 0), rads[i], m_, tp)
        lib.tube(f'{P}tailm{i}', [(0, 0, 0), (0, lens[i] / 2, 0), (0, lens[i], 0)],
                 [rads[i], (rads[i] + rads[i + 1]) / 2, rads[i + 1]], m_, tp)
        X['tail'].append(tp)
        if i % 2 == 0 and i < 6:
            rig.tail.append(tp)
        rig.t_pose[tp.name] = (R(10) if i == 0 else R(3), 0, 0)
        prev, ploc = tp, (0, lens[i], 0)
    lib.sphere(P + 'tailtip', (0, lens[-1], 0), rads[-1], lt, prev)

    rig.attack_origin = (0, -0.75, 0.6)
    return rig


# ---------------------------------------------------------------- animation
def animate(A):
    """Swampidile: springs out like an accordion, ripples along on twelve feet, and spins its
    sprout like a rotor to fling Razor Leaf."""
    r, T, s, lib = A.rig, A.T, A.size, A.lib
    X = r.x
    root, B, H, sp = r.root, r.body, r.head, X['sprout']
    segs, tail = X['segs'], X['tail']
    pi = math.pi
    E = lambda f, a, b: A.ease((f - a) / (b - a))                     # noqa: E731
    win = lambda f, a, b, c, d: E(f, a, b) * (1 - E(f, c, d))          # noqa: E731

    def spring(t, k=5.0, w=9.0):
        return 0.0 if t <= 0 else 1 - math.exp(-k * t) * math.cos(w * t)

    D = 1.25 * s                       # walk distance
    aim = 0.62                         # yaw toward the opponent while attacking
    A.key(root, 0, scale=0.001)
    A.key(root, T['OUT'] - 1, scale=0.001)

    for f in range(T['OUT'], T['END'] + 1):
        # ------------------------------------------------ root
        pop = spring((f - 16) / 9, 6, 8)
        hop_in = math.sin(pi * min(1, (f - 16) / 9)) * 0.22 * s if f < 25 else 0
        yaw = (pi / 2) * win(f, 72, 82, 128, 138) + aim * win(f, 141, 148, 176, 184)
        x = D * E(f, 79, 131)
        kb = win(f, 186, 190, 208, 218)                                  # knock-back
        end_hop = math.sin(pi * (f - 218) / 8) * 0.13 * s if 218 <= f <= 226 else 0
        lunge = win(f, 152, 156, 162, 172)
        A.key(root, f, loc=(x - 0.1 * s * kb + 0.07 * s * lunge, 0.17 * s * kb - 0.09 * s * lunge, hop_in + end_hop),
              rot=(0, 0, yaw - 0.25 * kb), scale=max(0.001, pop))

        # ------------------------------------------------ phase weights
        W = win(f, 76, 84, 127, 135)                                     # walking
        th = 2 * pi * (f - 72) / 16                                      # crawl cycle
        hitc = math.exp(-(f - 186) / 7) * math.cos((f - 186) * 0.85) if f >= 186 else 0
        shake = win(f, 206, 209, 215, 219)
        wind = win(f, 140, 150, 152, 156)                                # attack wind-up
        idle = math.sin(2 * pi * f / 30)

        # ------------------------------------------------ body segments
        B_z = -0.03 * wind + 0.02 * idle * (1 - W)
        A.key(B, f, loc=(0, 0, B_z), rot=(-0.1 * wind + 0.12 * lunge, 0, 0))
        for i, S in enumerate(segs):
            g = 1 - spring((f - (22 + 2.2 * i)) / 10)                    # bunched up behind the head
            y0 = X['seg_y'][i]
            gy = -(y0 + 0.36) * 0.86 * g
            ph = th - i * 0.95
            sx = 0.05 * math.sin(ph) * W + 0.045 * math.sin((f - 206) * 1.7 - i * 0.9) * shake
            sz = 0.045 * max(0, math.sin(ph + 1.2)) * W + 0.04 * max(0, math.sin((f - 28 - 2.2 * i) * 0.5)) * win(f, 26, 30, 40, 46)
            sy = -(y0 - 0.2) * 0.3 * hitc + 0.05 * (i + 1) / 6 * wind - 0.05 * (i + 1) / 6 * lunge
            br = 1 + 0.035 * math.sin(2 * pi * f / 30 - i * 0.7) * (1 - W)
            A.key(S, f, loc=(sx, gy + sy, sz + 0.05 * abs(hitc)),
                  rot=(0, 0.25 * math.sin((f - 206) * 1.7 - i * 0.9) * shake, -0.16 * math.cos(ph) * W),
                  scale=((1 - 0.45 * g) * (1 + 0.1 * hitc), 1 - 0.45 * g, (1 - 0.45 * g) * br * (1 + 0.16 * hitc)))
        # legs: a ripple that runs from the head to the tail
        for lp, i, sd in X['legs']:
            ph = 2 * th - i * 0.95 * 2 + (0 if sd < 0 else pi)
            sw = 0.6 * math.sin(ph) * W + 0.25 * math.sin((f - 206) * 1.7 - i) * shake
            lift = max(0, math.cos(ph)) * 0.35 * W + 0.5 * abs(hitc) + 0.25 * wind
            A.key(lp, f, rot=(sw, -sd * lift, 0))

        # ------------------------------------------------ tail: follows late, curls tight when scared
        unc = 1 - spring((f - 34) / 10)
        for i, tp in enumerate(tail):
            wag = 0.22 * math.sin(th - 6 * 0.95 - i * 0.5) * W + 0.1 * math.sin(2 * pi * f / 22 - i * 0.6) * (1 - W) \
                + 0.3 * math.sin((f - 218) * 1.4 - i * 0.5) * win(f, 216, 219, 226, 230)
            curl = 0.3 * unc + 0.22 * kb - 0.2 * lunge + 0.1 * wind + 0.06 * math.sin(th * 2 - i * 0.7) * W
            A.key(tp, f, rot=(curl, 0, wag * (0.4 + i * 0.15)))

        # ------------------------------------------------ head
        cry = win(f, 38, 41, 45, 48)
        look = math.sin(2 * pi * (f - 48) / 24) * win(f, 50, 54, 68, 72)
        hx = 0.05 * math.sin(th + 0.95) * W
        A.key(H, f, loc=(hx, 0.03 * wind - 0.06 * lunge, 0.03 * max(0, math.sin(th + 2.1)) * W + 0.03 * cry),
              rot=(-0.45 * cry + 0.3 * wind - 0.4 * lunge + 0.35 * kb - 0.2 * win(f, 218, 222, 230, 240) + 0.04 * idle * (1 - W),
                   0.12 * math.sin(th) * W + 0.3 * math.sin((f - 206) * 1.7) * shake,
                   0.35 * look + 0.14 * math.cos(th + 0.95) * W),
              scale=1 + 0.08 * cry)
        blink = max(win(f, 56, 58, 59, 61), win(f, 100, 102, 103, 105), win(f, 186, 188, 202, 206), win(f, 142, 145, 150, 153) * 0.5)
        for e in X['eyes']:
            A.key(e, f, scale=(1, 1, 1 - 0.88 * blink))

        # ------------------------------------------------ sprout and leaves
        spin_t = max(0.0, min(1.0, (f - 142) / 34))
        spin = 2 * pi * 7 * (3 * spin_t ** 2 - 2 * spin_t ** 3)       # ease in, ease out: 7 turns
        open_ = spring((f - 36) / 9, 5, 10)                              # leaves unfurl last
        A.key(sp, f, rot=(0.12 * math.sin(th * 2 - 1.2) * W + 0.25 * kb + 0.05 * idle, 0.2 * math.sin((f - 206) * 1.7 - 1) * shake, spin),
              scale=(1, 1, 0.3 + 0.7 * spring((f - 30) / 8, 5, 9)))
        for lp, sd in X['leaves']:
            flap = 0.5 * math.sin((f - 38) * 1.5) * cry + 0.22 * math.sin(th * 2 - 2.0 - (0.5 if sd > 0 else 0)) * W \
                + 0.07 * math.sin(2 * pi * f / 26 + sd) * (1 - W)
            up = 0.55 * win(f, 141, 150, 176, 184) + 0.4 * win(f, 218, 222, 226, 230) - 0.95 * kb - 1.3 * (1 - open_)
            A.key(lp, f, rot=(0, -sd * (up + flap), 0), scale=0.25 + 0.75 * min(1.0, open_ + 0.0))

    # ---------------------------------------------------- Razor Leaf
    gm = lib.mat('swi_fx_leaf', '#b8f070', 0.3, emit=2.2, emit_color='#8cff50')
    gm2 = lib.mat('swi_fx_leaf2', '#e8ffb0', 0.3, emit=3.0, emit_color='#d0ff80')
    A.emission(gm, 0, 2.2)
    tgt0 = None
    N = 12
    for i in range(N):
        f0 = 152 + i * 1.3
        f0i = int(round(f0))
        src = A.world(sp, f0i, (0, 0, 0.24))
        if tgt0 is None:
            tgt0 = A.opponent(A.world(root, 160))
        a = i * 2.4
        tgt = tgt0 + Vector((math.cos(a), 0.5 * math.sin(a * 1.7), math.sin(a))) * 0.1 * s
        d = (tgt - src)
        side = Vector((-d.y, d.x, 0)).normalized()
        p = lib.pivot(f'swi_fx{i}')
        L = 0.24 * s
        leaf(lib, f'swi_fxm{i}', (0, -L / 2, 0), (0, 1, 0), (1, 0, 0), L, L * 0.3, gm if i % 3 else gm2, p, fold=0.25, n=6, thick=0.008)
        A.key(p, 0, loc=src, scale=0.001, absolute=True)
        A.key(p, f0i - 1, loc=src, scale=0.001, absolute=True)
        dur = 11
        bow = (0.5 if i % 2 else -0.5) * s * (0.5 + 0.5 * math.sin(i * 1.3))
        heading = math.atan2(d.y, d.x) - pi / 2
        for k in range(dur + 1):
            t = k / dur
            pos = src.lerp(tgt, t ** 1.3) + side * bow * math.sin(pi * t) + Vector((0, 0, 0.35 * s * math.sin(pi * t) * (0.4 + 0.6 * ((i * 7) % 5) / 4)))
            A.key(p, f0i + k, loc=pos, rot=(t * 9 + i, 0.6 * math.sin(i), heading + 0.6 * math.cos(pi * t) * (1 if bow > 0 else -1)),
                  scale=min(1.0, 0.3 + t * 3), absolute=True)
        # shards scatter off the opponent
        out = tgt + Vector((math.cos(a * 1.3), -0.4, abs(math.sin(a * 1.3)) + 0.3)) * 0.45 * s
        A.key(p, f0i + dur + 5, loc=out, rot=(t * 9 + i + 4, 2, heading + 3), scale=0.5, absolute=True)
        A.key(p, f0i + dur + 9, loc=out + Vector((0, 0, -0.1 * s)), scale=0.001, absolute=True)
    # a ring of wind under the spinning sprout, and the impact flash
    ringm = lib.mat('swi_fx_ring', '#d8ffb0', 0.3, emit=2.5, alpha=0.5)
    ring = lib.torus('swi_fx_ring', (0, 0, 0.3), 0.36, 0.012, ringm, sp)
    for f, sc in [(0, 0.001), (143, 0.001), (150, 0.8), (158, 1.25), (170, 1.0), (178, 0.001)]:
        A.key(ring, f, scale=sc)
    hit = lib.sphere('swi_fx_hit', tgt0, 1.0, lib.mat('swi_fx_hitm', '#e0ffb0', 0.4, emit=4, alpha=0.45))
    for f, sc in [(0, 0.001), (162, 0.001), (166, 0.3 * s), (170, 0.22 * s), (174, 0.3 * s), (180, 0.001)]:
        A.key(hit, f, scale=sc)
    A.light('swi_fx_l', '#a0ff60', tgt0 + Vector((0, -0.3 * s, 0.2 * s)),
            [(0, 0), (161, 0), (165, 500 * s * s), (169, 250 * s * s), (173, 450 * s * s), (181, 0)])
    A.light('swi_fx_l2', '#c8ff80', (0, 0, 0.5), [(0, 0), (144, 0), (154, 60 * s * s), (174, 40 * s * s), (180, 0)], parent=sp)


# Phase speeds for render.retime: above 1 is slower and longer, below 1 is quicker.
TIMING = {'send': 1.2, 'idle': 1.3, 'walk': 1.1, 'attack': 1.3, 'hit': 1.1, 'recover': 1.2}
