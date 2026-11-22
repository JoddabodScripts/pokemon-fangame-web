"""Freezer Flock v2: giant snowy eagle, Ice/Flying, 550 cm, red knitted scarf, snowflake eyes.

Built from a sculpted metaball body, a real skeleton and a few thousand individual feathers.
`build()` returns a dict with the armature and key objects; `pose_display()` sets the hero pose.
Rest pose is the T-pose: wings flat out to the sides, legs hanging, facing -Y.
"""
import math
import random

from mathutils import Euler, Matrix, Vector

import bpy

import kit
from kit import srgb as C

V = Vector
rnd = random.Random(7)

# ------------------------------------------------------------------ proportions (meters)
CHEST = V((0, 0.02, 2.62))
HEAD = V((0, -0.24, 4.05))
HEAD_R = 0.56
BEAK_TIP = V((0, -1.28, 3.66))
TAIL0 = V((0, 0.58, 1.78))

# bones: name, head, tail, parent, deform
SIDE = {'L': 1, 'R': -1}


def bone_list():
    b = [
        ('root', (0, 0, 0), (0, 0, 0.6), None, False),
        ('hips', (0, 0.12, 1.85), (0, 0.04, 2.45), 'root', True),
        ('chest', (0, 0.04, 2.45), (0, -0.04, 3.2), 'hips', True),
        ('neck', (0, -0.04, 3.2), (0, -0.16, 3.62), 'chest', True),
        ('head', (0, -0.16, 3.62), (0, -0.3, 4.4), 'neck', True),
        ('jaw', (0, -0.62, 3.78), (0, -0.9, 3.76), 'head', True),
        ('tail', (0, 0.5, 1.86), (0, 1.0, 1.42), 'hips', True),
        ('scarf0', (0.26, -0.62, 3.2), (0.34, -0.8, 2.85), 'chest', True),
        ('scarf1', (0.34, -0.8, 2.85), (0.42, -0.84, 2.45), 'scarf0', True),
        ('scarf2', (0.42, -0.84, 2.45), (0.52, -0.8, 2.05), 'scarf1', True),
    ]
    for s, sx in SIDE.items():
        b += [
            ('shoulder.' + s, (sx * 0.72, 0.1, 3.08), (sx * 1.65, 0.26, 3.12), 'chest', True),
            ('forearm.' + s, (sx * 1.65, 0.26, 3.12), (sx * 2.65, 0.06, 3.2), 'shoulder.' + s, True),
            ('hand.' + s, (sx * 2.65, 0.06, 3.2), (sx * 3.65, 0.16, 3.26), 'forearm.' + s, True),
            ('thigh.' + s, (sx * 0.42, 0.06, 1.92), (sx * 0.46, -0.04, 1.3), 'hips', True),
            ('shin.' + s, (sx * 0.46, -0.04, 1.3), (sx * 0.47, 0.0, 0.86), 'thigh.' + s, True),
            ('foot.' + s, (sx * 0.47, 0.0, 0.86), (sx * 0.47, -0.3, 0.78), 'shin.' + s, True),
        ]
    return b


BONES = bone_list()
SEG = {n: (V(h), V(t)) for n, h, t, p, d in BONES if d}

# ------------------------------------------------------------------ palette (sRGB hex -> linear)
SNOW = C('#f7fbff')
SNOW2 = C('#e6f0f8')
FROST = C('#cfe5f5')
ICE1 = C('#a6d6f4')
ICE2 = C('#5fa6de')
ICE3 = C('#2e6cba')
DEEP = C('#183e86')
NAVY = C('#1b2a52')
WHITE = C('#ffffff')


# ------------------------------------------------------------------ helpers
def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def tangent(n, d):
    """Project direction d onto the plane with normal n."""
    d = V(d)
    t = d - n * d.dot(n)
    if t.length < 1e-5:
        t = n.orthogonal()
    return t.normalized()


def add_feather(mb, root, direction, up, L, W, weights, stops, bend=0.05, cup=0.1, nl=6, nw=3, shaft=False,
                edge_c=None, edge_amt=0.25, roundness=0.85, lift=0.0, roll=0.0, blunt=0.0):
    d = V(direction).normalized()
    u = V(up).normalized()
    if lift:
        d = (d + u * math.tan(lift)).normalized()
    if roll:
        u = Matrix.Rotation(roll, 3, d) @ u
    vs, fs, cs, uvs = kit.feather_geo(L, W, bend=bend, cup=cup, nl=nl, nw=nw, shaft=shaft, stops=stops,
                                      edge_c=edge_c, edge_amt=edge_amt, roundness=roundness, blunt=blunt)
    M = kit.frame_matrix(root, d, u)
    mb.add(kit.transform(vs, M), fs, cs, uvs, weights)


# ------------------------------------------------------------------ the sculpted body
def body_elements():
    E = []

    def ell(co, size, rot=(0, 0, 0), neg=False, stiff=2.0):
        E.append(dict(type='ELLIPSOID', co=co, radius=1.0, size=size, rot=rot, negative=neg, stiff=stiff))

    def ball(co, r, neg=False, stiff=2.0):
        E.append(dict(type='BALL', co=co, radius=r, negative=neg, stiff=stiff))

    # torso: deep keel chest, rounder belly, tapering to the tail
    ell((0, 0.0, 2.68), (0.82, 0.74, 0.86), rot=(0.18, 0, 0))
    ell((0, -0.14, 2.9), (0.64, 0.6, 0.6))                      # chest puff
    ell((0, 0.08, 2.1), (0.74, 0.7, 0.66))                      # belly
    ell((0, 0.5, 1.85), (0.38, 0.5, 0.34), rot=(-0.6, 0, 0))    # rump to tail
    # neck and head
    ell((0, -0.08, 3.45), (0.5, 0.5, 0.42))
    ell(tuple(HEAD), (0.6, 0.6, 0.55))
    ell((0, -0.5, 3.9), (0.34, 0.3, 0.3))                       # face / muzzle
    for sx in (-1, 1):
        # cheek fluff
        ell((sx * 0.3, -0.42, 3.78), (0.2, 0.2, 0.2))
        # brow ridges, angled down toward the beak: the fierce look
        e = EYES['L' if sx > 0 else 'R']
        ell(tuple(e + V((sx * 0.0, -0.02, 0.135))), (0.2, 0.13, 0.075), rot=(0.3, sx * 0.4, sx * 0.25))
        E[-1]['brow'] = True
        # shoulders, joining the wings
        ell((sx * 0.75, 0.12, 3.08), (0.34, 0.28, 0.24))
        # feathered thighs ("trousers") with a shaggy ankle cuff
        ell((sx * 0.44, 0.0, 1.7), (0.36, 0.38, 0.44))
        ell((sx * 0.46, -0.03, 1.22), (0.27, 0.28, 0.3))
    return E


def body_color(p, n):
    """Feather color by position: snow-white with frosty blue on the back and a navy brow."""
    c = SNOW
    back = smooth(-0.1, 0.6, n.y) * smooth(1.6, 2.6, p.z) * (1 - smooth(3.3, 3.6, p.z))
    c = kit.lerp3(c, FROST, back * 0.85)
    nape = smooth(0.0, 0.7, n.y) * smooth(3.4, 3.8, p.z)
    c = kit.lerp3(c, kit.lerp3(FROST, ICE1, 0.4), nape * 0.8)
    # angry navy brow: a stripe over each eye, low at the beak, rising toward the back of the head
    for sx in (-1, 1):
        e = EYES['L' if sx > 0 else 'R']
        a, b = e + V((-sx * 0.13, -0.08, 0.1)), e + V((sx * 0.14, 0.2, 0.2))
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        q = p - (a + ab * t)
        d = math.hypot(q.z, 0.5 * (q.x * q.x + q.y * q.y) ** 0.5)
        w = 0.08 * (1 - 0.45 * t)
        c = kit.lerp3(c, NAVY, (1 - smooth(w * 0.6, w, d)) * 0.95)
    return c


def flow(p, n):
    """Direction feathers lie along: back from the beak on the head, down toward the tail on the body."""
    head_dir = (p - V((0, -1.1, 3.75)))
    body_dir = V((0, 0.45, -1))
    if p.y > 0.2 and p.z < 2.2:
        body_dir = V((0, 1, -0.6))
    k = smooth(3.25, 3.65, p.z)
    d = head_dir.normalized() * k + body_dir.normalized() * (1 - k)
    return tangent(n, d)


def build_body(arm):
    body = kit.metaball_body('ffk_body', body_elements(), resolution=0.04, remesh=0.025, smooth_iter=8)
    me = body.data
    # vertex colors + weights
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    for v in me.vertices:
        ca.data[v.index].color = (*kit.lerp3(body_color(v.co, v.normal), (0.8, 0.88, 0.95), 0.15), 1)
    body_bones = {k: SEG[k] for k in ('hips', 'chest', 'neck', 'head', 'tail', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R',
                                      'shoulder.L', 'shoulder.R')}
    radii = dict(hips=0.7, chest=0.7, neck=0.45, head=0.6, tail=0.45)
    for s in 'LR':
        radii.update({'thigh.' + s: 0.35, 'shin.' + s: 0.25, 'shoulder.' + s: 0.35})
    W = kit.skin_weights([v.co for v in me.vertices], body_bones, radii, top=3, falloff=2.0)
    body.data.materials.append(kit.mat_feather('ffk_down', rough=0.7, sheen=0.6, sparkle=0.0, sss=0.15))
    kit.bind(body, arm, W)
    return body, body_bones, radii


# ------------------------------------------------------------------ contour feathers over the body
def _eye(sx):
    look = V((sx * 0.42, -0.88, 0.1)).normalized()
    return HEAD + V((look.x * 0.54, look.y * 0.56, look.z * 0.5)) - look * 0.095, look


EYES = {s: _eye(sx)[0] for s, sx in (('L', 1), ('R', -1))}
LOOK = {s: _eye(sx)[1] for s, sx in (('L', 1), ('R', -1))}


def body_feathers(body, arm, body_bones, radii):
    mb = kit.MeshBuilder()
    big = kit.MeshBuilder()

    def ok(p, n):
        if p.z < 1.25 and abs(p.x) > 0.2:           # leave the yellow legs bare
            return False
        for e in EYES.values():
            if (p - e).length < 0.175:
                return False
        if p.y < -0.62 and abs(p.x) < 0.24 and 3.55 < p.z < 4.05:   # beak root
            return False
        return True

    samples = kit.surface_samples(body, 5200, seed=3, accept=ok)
    for p, n in samples:
        head = p.z > 3.45
        chest = p.y < -0.15 and 2.05 < p.z < 3.25
        c = body_color(p, n)
        tipc = kit.lerp3(c, WHITE, 0.6)
        if head:
            L = rnd.uniform(0.08, 0.12) * (1.0 if p.z < 4.3 else 1.25)
            Wd = L * 0.7
            lift = 0.05
        elif chest:
            L = rnd.uniform(0.16, 0.21)
            Wd = L * 0.9                     # broad, rounded chest scallops
            lift = 0.16
        else:
            L = rnd.uniform(0.14, 0.22)
            Wd = L * 0.6
            lift = 0.14
        d = flow(p, n)
        w = kit.skin_weights([p], body_bones, radii, top=2)[0]
        edge = kit.lerp3(FROST, ICE1, 0.3) if chest else None
        add_feather(mb if head else big, p - n * 0.012, d, n, L, Wd, w,
                    [(0, kit.lerp3(c, (0.75, 0.82, 0.9), 0.25)), (0.55, c), (1, tipc)],
                    bend=-0.05, cup=0.18, nl=5, nw=3, edge_c=edge, edge_amt=0.55 if chest else 0.2,
                    roundness=0.7 if chest else 0.85, lift=lift + rnd.uniform(-0.05, 0.05), roll=rnd.uniform(-0.15, 0.15))
    m = kit.mat_feather('ffk_contour', rough=0.6, sheen=0.7, sparkle=0.0, sss=0.12)
    o1 = mb.build('ffk_headfeathers', m)
    o2 = big.build('ffk_bodyfeathers', m)
    for o in (o1, o2):
        o.modifiers.new('arm', 'ARMATURE').object = arm
    return o1, o2


# ------------------------------------------------------------------ wings
WING_STOPS = {
    'primary': [(0, FROST), (0.35, ICE2), (0.78, DEEP), (0.86, ICE1), (0.93, WHITE), (1, WHITE)],
    'secondary': [(0, SNOW2), (0.4, ICE1), (0.8, ICE3), (0.88, ICE1), (0.95, WHITE), (1, WHITE)],
    'tertial': [(0, SNOW), (0.6, FROST), (0.9, ICE1), (1, WHITE)],
    'gcovert': [(0, SNOW), (0.7, FROST), (1, ICE1)],
    'mcovert': [(0, SNOW), (0.8, SNOW2), (1, FROST)],
    'under': [(0, SNOW), (0.8, SNOW), (1, SNOW2)],
}


def wing(arm, s):
    sx = SIDE[s]
    mb = kit.MeshBuilder()
    sh0, sh1 = SEG['shoulder.' + s]
    fa0, fa1 = SEG['forearm.' + s]
    hd0, hd1 = SEG['hand.' + s]
    back = V((0, 1, 0))
    up = V((0, 0, 1))
    down = V((0, 0, -1))
    out = V((sx, 0, 0))

    def chain(t):
        """t in 0..3 along shoulder, forearm, hand -> (point, bone name)."""
        if t < 1:
            return sh0.lerp(sh1, t), 'shoulder.' + s
        if t < 2:
            return fa0.lerp(fa1, t - 1), 'forearm.' + s
        return hd0.lerp(hd1, min(1.0, t - 2)), 'hand.' + s

    # arm flesh: a flattened tube along the bones, thick at the leading edge
    secs, cols, wts = [], [], []
    N = 16
    for i in range(N + 1):
        t = 3.0 * i / N
        p, bn = chain(t)
        d = (chain(min(3.0, t + 0.05))[0] - chain(max(0.0, t - 0.05))[0]).normalized()
        taper = 1 - 0.75 * (t / 3) ** 1.5
        secs.append((p + V((0, 0.06, 0)), 0.2 * taper + 0.04, 0.09 * taper + 0.03, d))
        cols.append(SNOW)
    vs, fs, vc = kit.loft(secs, ring=12, cols=cols)
    W = kit.skin_weights([V(v) for v in vs], {k: SEG[k] for k in ('shoulder.' + s, 'forearm.' + s, 'hand.' + s)},
                         {'shoulder.' + s: 0.4, 'forearm.' + s: 0.4, 'hand.' + s: 0.4}, top=2, falloff=1.5)
    mb.add(vs, fs, vc, None, W)

    # primaries: 10 fanning from the hand, longest near the tip
    n = 10
    for i in range(n):
        f = i / (n - 1)
        root = hd0.lerp(hd1, 0.12 + 0.86 * f) + V((0, 0.05, -0.01 * i))
        ang = math.radians(6 + 50 * f ** 1.2)           # 0 = straight back, 90 = straight out
        d = back * math.cos(ang) + out * math.sin(ang)
        L = 1.55 + 0.7 * math.sin(math.pi * (0.25 + 0.6 * f)) - 0.25 * f
        add_feather(mb, root, d, up, L, 0.38 - 0.05 * f, {'hand.' + s: 1.0},
                    WING_STOPS['primary'], bend=-0.04, cup=0.16, nl=12, nw=4, shaft=True, edge_c=ICE2, edge_amt=0.15,
                    blunt=0.45, lift=0.02 * i, roll=sx * -0.08)
    # secondaries along the forearm
    n = 13
    for i in range(n):
        f = i / (n - 1)
        root = fa1.lerp(fa0, f * 0.98) + V((0, 0.06, 0.005 * i))
        ang = math.radians(6 - 10 * f)
        d = (back * math.cos(ang) + out * math.sin(ang) + V((0, 0, -0.04))).normalized()
        L = 1.45 - 0.12 * f
        add_feather(mb, root, d, up, L, 0.34, {'forearm.' + s: 1.0}, WING_STOPS['secondary'],
                    bend=-0.03, cup=0.14, nl=10, nw=4, shaft=True, edge_c=ICE2, edge_amt=0.12, blunt=0.3, lift=0.01)
    # tertials along the humerus
    n = 6
    for i in range(n):
        f = i / (n - 1)
        root = sh1.lerp(sh0, 0.1 + 0.8 * f) + V((0, 0.08, 0.02))
        d = (back + out * (-0.15 * f) + V((0, 0, -0.08))).normalized()
        add_feather(mb, root, d, up, 1.15 - 0.3 * f, 0.34, {'shoulder.' + s: 1.0}, WING_STOPS['tertial'],
                    bend=-0.03, cup=0.14, nl=8, nw=4, shaft=True, blunt=0.35, lift=0.03)
    # covert rows on top (greater, median, lesser) and under the wing
    rows = [  # (offset back from bone, length, width, count, stops, lift)
        (0.04, 0.75, 0.26, 26, 'gcovert', 0.06),
        (-0.02, 0.45, 0.2, 32, 'mcovert', 0.09),
        (-0.08, 0.26, 0.14, 40, 'mcovert', 0.12),
    ]
    for ri, (off, L, Wd, cnt, st, lift) in enumerate(rows):
        for i in range(cnt):
            t = 2.92 * (i + 0.5) / cnt
            p, bn = chain(t)
            taper = 1 - 0.45 * (t / 3) ** 1.3
            ang = math.radians(10 + 35 * max(0.0, t - 2.0))
            d = back * math.cos(ang) + out * math.sin(ang)
            for side_up, zoff, stopkey in ((up, 0.08 + 0.02 * ri, st), (down, -0.07 - 0.015 * ri, 'under')):
                add_feather(mb, p + V((0, off, zoff * taper)), d, side_up, L * taper * rnd.uniform(0.93, 1.07),
                            Wd * taper, {bn: 1.0}, WING_STOPS[stopkey], bend=-0.05, cup=0.16, nl=5, nw=3,
                            blunt=0.45, lift=lift, roll=rnd.uniform(-0.08, 0.08))
    # leading-edge marginal coverts: tiny feathers wrapping the front of the arm
    for i in range(70):
        t = 2.9 * (i + 0.5) / 70
        p, bn = chain(t)
        taper = 1 - 0.6 * (t / 3) ** 1.5
        for side_up, z in ((up, 1), (down, -1)):
            add_feather(mb, p + V((0, -0.12 * taper, 0.05 * z * taper)), back, side_up, 0.2 * taper, 0.1 * taper,
                        {bn: 1.0}, WING_STOPS['mcovert'], bend=-0.08, cup=0.2, nl=3, nw=2, roundness=0.6, lift=0.2)
    m = kit.mat_feather('ffk_wing', rough=0.5, sheen=0.6, sparkle=0.0, sss=0.18)
    o = mb.build('ffk_wing.' + s, m)
    o.modifiers.new('arm', 'ARMATURE').object = arm
    return o


# ------------------------------------------------------------------ tail fan
def tail(arm):
    mb = kit.MeshBuilder()
    t0, t1 = SEG['tail']
    axis = (t1 - t0).normalized()
    up = V((0, 0.55, 0.85)).normalized()
    up = tangent(axis, up)
    n = 12
    for layer, (Lk, z) in enumerate(((1.0, 0.0), (0.62, 0.05))):
        for i in range(n if layer == 0 else 9):
            f = i / ((n if layer == 0 else 9) - 1) * 2 - 1
            ang = f * math.radians(42)
            d = Matrix.Rotation(ang, 3, up) @ axis
            L = (1.55 - 0.15 * abs(f)) * Lk
            stops = [(0, SNOW), (0.5, FROST), (0.78, ICE2), (0.88, ICE3), (0.94, WHITE), (1, WHITE)] if layer == 0 \
                else [(0, SNOW), (0.8, SNOW2), (1, FROST)]
            add_feather(mb, t0 + up * (0.04 + z) + d * 0.1, d, up, L, 0.3, {'tail': 1.0}, stops, bend=-0.03, cup=0.1,
                        nl=10, nw=4, shaft=layer == 0, blunt=0.35, lift=0.02 * layer, roll=f * 0.15)
    o = mb.build('ffk_tail', kit.mat_feather('ffk_tailm', rough=0.5, sheen=0.6, sss=0.18))
    o.modifiers.new('arm', 'ARMATURE').object = arm
    return o


# ------------------------------------------------------------------ legs and talons
LEG_Y = C('#f2b934')
LEG_Y2 = C('#d48f1a')
TALON = C('#1d1f26')


def legs(arm):
    mb = kit.MeshBuilder()
    claws = kit.MeshBuilder()
    for s, sx in SIDE.items():
        k0, k1 = SEG['shin.' + s]
        secs = []
        for i in range(8):
            t = i / 7
            p = k0.lerp(k1, t)
            r = 0.12 - 0.02 * t
            secs.append((p, r, r * 1.05, k1 - k0))
        vs, fs, vc = kit.loft(secs, ring=14, cols=[kit.lerp3(LEG_Y, LEG_Y2, 0.3) for _ in secs])
        mb.add(vs, fs, vc, None, {'shin.' + s: 1.0})
        # toes: three forward, one back
        ankle = k1
        for ti, (yaw, L) in enumerate(((-0.45, 0.48), (0.0, 0.56), (0.45, 0.48), (math.pi, 0.34))):
            dirv = V((math.sin(yaw) * sx * (1 if yaw != math.pi else 0), -math.cos(yaw), 0))
            pts = []
            for i in range(7):
                t = i / 6
                curl = 0.55 * t * t                    # toes curl down: a hovering grip
                p = ankle + dirv * (L * t * math.cos(curl)) + V((0, 0, -0.08 - L * 0.6 * math.sin(curl) * t))
                pts.append(p)
            secs = []
            for i, p in enumerate(pts):
                d = (pts[min(6, i + 1)] - pts[max(0, i - 1)]).normalized()
                r = 0.085 - 0.03 * i / 6
                # knuckle bulges
                r *= 1 + 0.12 * math.cos(i * math.pi)
                secs.append((p, r, r * 0.85, d))
            vs, fs, vc = kit.loft(secs, ring=10, cols=[LEG_Y for _ in secs])
            mb.add(vs, fs, vc, None, {'foot.' + s: 1.0})
            # talon: a hooked black claw
            tip0 = pts[-1]
            d0 = (pts[-1] - pts[-2]).normalized()
            down = V((0, 0, -1))
            csecs = []
            for i in range(8):
                t = i / 7
                d = (d0 * math.cos(t * 1.3) + down * math.sin(t * 1.3)).normalized()
                p = tip0 + d0 * (0.16 * math.sin(t * 1.3) / 1.3 * 1.3) + down * (0.12 * (1 - math.cos(t * 1.3)))
                r = 0.05 * (1 - t) ** 0.8 + 0.003
                csecs.append((p, r, r * 1.3, d))
            vs, fs, vc = kit.loft(csecs, ring=10, cols=[TALON for _ in csecs])
            claws.add(vs, fs, vc, None, {'foot.' + s: 1.0})
    o = mb.build('ffk_legs', kit.mat_vcol('ffk_scales', rough=0.45, coat=0.35, sss=0.2, bump_scale=90, bump_strength=0.35))
    c = claws.build('ffk_talons', kit.mat_vcol('ffk_talon', rough=0.15, coat=0.8))
    for x in (o, c):
        x.modifiers.new('arm', 'ARMATURE').object = arm
        x.modifiers.new('sub', 'SUBSURF').levels = 1
    return o, c


# ------------------------------------------------------------------ beak
BEAK_Y = C('#f7c62e')
BEAK_TIPC = C('#9a6a2a')
CERE = C('#ffd85a')


def beak(arm):
    mb = kit.MeshBuilder()
    # upper mandible: a deep, laterally narrow hook
    pts, secs, cols = [], [], []
    n = 14
    for i in range(n + 1):
        t = 0.9 * i / n                        # stop before the needle tip: a blunt, rounded hook
        y = -0.62 - 0.56 * t + 0.07 * t ** 4
        z = 3.93 + 0.05 * math.sin(t * math.pi * 0.7) - 0.32 * t ** 2.6
        pts.append(V((0, y, z)))
    for i, p in enumerate(pts):
        t = 0.9 * i / n
        d = (pts[min(n, i + 1)] - pts[max(0, i - 1)]).normalized()
        rx = 0.16 * (1 - t) ** 0.85 + 0.003
        rz = 0.16 * (1 - t) ** 0.55 + 0.004
        secs.append((p - V((0, 0, rz * 0.35)), rx, rz, d))
        cols.append(kit.ramp3([(0, CERE), (0.16, CERE), (0.22, BEAK_Y), (0.82, BEAK_Y), (1, kit.lerp3(BEAK_Y, BEAK_TIPC, 0.5))], t))
    def tear(a, si):
        # sharp ridge on top (culmen), flared cutting edges below
        x, y = math.cos(a), math.sin(a)
        return x * (1 - 0.55 * max(0.0, y) ** 1.5) * (1 + 0.15 * max(0.0, -y)), y
    vs, fs, vc = kit.loft(secs, ring=20, cols=cols, shape=tear)
    for si in range(len(secs)):
        for k in range(20):
            a = 2 * math.pi * k / 20
            if math.sin(a) < -0.55:
                vc[si * 20 + k] = kit.lerp3(vc[si * 20 + k], BEAK_TIPC, 0.55)
    mb.add(vs, fs, vc, None, {'head': 1.0})
    # lower mandible, hinged on the jaw bone
    pts, secs, cols = [], [], []
    for i in range(n + 1):
        t = i / n
        pts.append(V((0, -0.62 - 0.26 * t, 3.81 - 0.03 * t)))
    for i, p in enumerate(pts):
        t = i / n
        d = (pts[min(n, i + 1)] - pts[max(0, i - 1)]).normalized()
        secs.append((p, 0.11 * (1 - t) ** 0.8 + 0.01, 0.045 * (1 - t) + 0.01, d))
        cols.append(kit.ramp3([(0, BEAK_Y), (1, kit.lerp3(BEAK_Y, BEAK_TIPC, 0.6))], t))
    vs, fs, vc = kit.loft(secs, ring=14, cols=cols)
    mb.add(vs, fs, vc, None, {'jaw': 1.0})
    o = mb.build('ffk_beak', kit.mat_vcol('ffk_beakm', rough=0.38, coat=0.25, sss=0.2, sss_radius=(0.9, 0.5, 0.2), bump_scale=40, bump_strength=0.05))
    o.modifiers.new('arm', 'ARMATURE').object = arm
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    # nostril
    return o


# ------------------------------------------------------------------ snowflake eyes
def snowflake_eye(arm, s):
    sx = SIDE[s]
    c = EYES[s]
    look = LOOK[s]
    r = 0.165
    mb = kit.MeshBuilder()
    flake = kit.MeshBuilder()
    # eyeball: icy iris disc painted into the vertex colors
    rings, segs = 24, 32
    vs, fs, cs = [], [], []
    for i in range(rings + 1):
        th = math.pi * i / rings
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            vs.append((r * math.sin(th) * math.cos(ph), -r * math.cos(th), r * math.sin(th) * math.sin(ph)))
            a = th / math.pi
            col = kit.ramp3([(0, C('#eaf8ff')), (0.1, C('#bfe7ff')), (0.2, C('#7cc4f2')), (0.25, ICE2), (0.27, ICE3), (0.29, C('#f8fbfd')), (1, C('#e6eef5'))], a)
            cs.append(col)
    for i in range(rings):
        for j in range(segs):
            a = i * segs + j
            b = i * segs + (j + 1) % segs
            fs.append((a, b, b + segs, a + segs))
    rot = V((0, -1, 0)).rotation_difference(look).to_matrix().to_4x4()
    M = Matrix.Translation(c) @ rot
    mb.add(kit.transform(vs, M), fs, cs, None, {'head': 1.0})
    # six-armed snowflake iris, projected onto the eyeball just under the cornea
    def on_ball(x, z, k=1.006):
        rr = r * k
        y = -math.sqrt(max(1e-6, rr * rr - x * x - z * z))
        return M @ V((x, y, z))

    def strip(p0, p1, w, segs_=6):
        a = V(p0)
        b = V(p1)
        dv = (b - a)
        nrm = V((-dv.y, dv.x)).normalized() * w * 0.5
        base = len(flake.v)
        verts, faces = [], []
        for k in range(segs_ + 1):
            q = a + dv * (k / segs_)
            ww = 1 - 0.5 * (k / segs_)
            for sgn in (-1, 1):
                pp = q + nrm * sgn * ww
                verts.append(on_ball(pp.x, pp.y))
        for k in range(segs_):
            i0 = 2 * k
            faces.append((i0, i0 + 1, i0 + 3, i0 + 2))
        flake.add(verts, faces, [C('#1d55b8')] * len(verts), None, {'head': 1.0})

    from mathutils import Vector as V2
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        u = V2((math.cos(a), math.sin(a)))
        strip(u * r * 0.1, u * r * 0.66, r * 0.06)
        for t, bl in ((0.34, 0.17), (0.5, 0.11)):
            base = u * r * t
            for sgn in (-1, 1):
                b2 = V2((math.cos(a + sgn * math.pi / 3), math.sin(a + sgn * math.pi / 3)))
                strip(base, base + b2 * r * bl, r * 0.04, 3)
    # pupil: dark hexagon
    hexv = [on_ball(0, 0)] + [on_ball(math.cos(k * math.pi / 3) * r * 0.11, math.sin(k * math.pi / 3) * r * 0.11) for k in range(6)]
    flake.add(hexv, [(0, k + 1, (k + 1) % 6 + 1) for k in range(6)], [C('#08132e')] * 7, None, {'head': 1.0})
    # eyelids: an upper lid slanting down toward the beak (the fierce stare) and a thin lower lid
    lid = kit.MeshBuilder()
    rr = r * 1.07
    nr, ns = 18, 40
    lv, lf, lc = [], [], []
    keep = []
    for i in range(nr + 1):
        th = math.pi * i / nr
        for j in range(ns):
            ph = 2 * math.pi * j / ns
            x, y, z = rr * math.sin(th) * math.cos(ph), -rr * math.cos(th), rr * math.sin(th) * math.sin(ph)
            lv.append((x, y, z))
            # lateral axis in eye space points away from the beak for the +X eye; mirror for the other
            inner = -x * sx / r
            lc.append(NAVY)
            keep.append(z / r > 0.4 - 0.36 * inner)
    for i in range(nr):
        for j in range(ns):
            a0 = i * ns + j
            b0 = i * ns + (j + 1) % ns
            if keep[a0] and keep[b0] and keep[a0 + ns] and keep[b0 + ns]:
                lf.append((a0, b0, b0 + ns, a0 + ns))
    lid.add(kit.transform(lv, M), lf, lc, None, {'head': 1.0})
    lido = lid.build('ffk_lid.' + s, kit.mat_vcol('ffk_lidm', rough=0.55, coat=0.0))
    sol = lido.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.018
    lido.modifiers.new('arm', 'ARMATURE').object = arm
    eye = mb.build('ffk_eye.' + s, kit.mat_vcol('ffk_eyem', rough=0.12, coat=1.0, sss=0.0))
    em = eye.data.materials[0]
    if 'glow' not in em:
        em['glow'] = 1
        b_ = em.node_tree.nodes['Principled BSDF']
        em.node_tree.links.new(em.node_tree.nodes['Attribute'].outputs['Color'], b_.inputs['Emission Color'])
        b_.inputs['Emission Strength'].default_value = 0.35
    fl = flake.build('ffk_flake.' + s, kit.mat_basic('ffk_flakem', '#ffffff', rough=0.3, emit=0.0))
    # flake color via vertex attribute
    fl.data.materials[0] = kit.mat_vcol('ffk_flakem2', rough=0.15, coat=1.0)
    # cornea: a clear glassy dome for real reflections
    cmb = kit.MeshBuilder()
    vs2 = [tuple(V(v) * 1.045) for v in vs]
    cmb.add(kit.transform(vs2, M), fs, [WHITE] * len(vs2), None, {'head': 1.0})
    cor = cmb.build('ffk_cornea.' + s, kit.mat_basic('ffk_corneam', '#ffffff', rough=0.0, transmission=1.0, ior=1.38, coat=0.0))
    bpy.data.objects.remove(cor)
    for o in (eye, fl):
        o.modifiers.new('arm', 'ARMATURE').object = arm
    return eye, fl, cor


# ------------------------------------------------------------------ frost crest + ice crystals
def crystal_geo(L, r, sides=6):
    """A hexagonal ice crystal: prism with pointed ends, along +Z."""
    vs, fs = [(0, 0, 0)], []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        vs.append((math.cos(a) * r, math.sin(a) * r, L * 0.2))
    for k in range(sides):
        a = 2 * math.pi * k / sides
        vs.append((math.cos(a) * r * 0.9, math.sin(a) * r * 0.9, L * 0.75))
    vs.append((0, 0, L))
    top = len(vs) - 1
    for k in range(sides):
        a, b = 1 + k, 1 + (k + 1) % sides
        fs.append((0, b, a))
        fs.append((a, b, b + sides, a + sides))
        fs.append((a + sides, b + sides, top))
    return vs, fs


def ice(arm):
    mb = kit.MeshBuilder()

    def add(root, d, L, r, bone, up=V((0, 0, 1))):
        vs, fs = crystal_geo(L, r)
        M = kit.frame_matrix(root, d, up)
        mb.add(kit.transform(vs, M), fs, [WHITE] * len(vs), None, {bone: 1.0})

    # crest: five long frost plumes sweeping back off the crown, each ending in a crystal
    crest = kit.MeshBuilder()
    plumes = [(0, 1.05, 0.55, True), (-0.1, 0.85, 0.45, True), (0.1, 0.85, 0.45, True), (-0.19, 0.62, 0.3, False),
              (0.19, 0.62, 0.3, False), (-0.05, 0.7, 0.7, False), (0.05, 0.7, 0.7, False), (-0.26, 0.42, 0.15, False),
              (0.26, 0.42, 0.15, False)]
    for i, (x, L, pitch, tipped) in enumerate(plumes):
        root = HEAD + V((x, -0.12 + abs(x) * 0.5, 0.36 - abs(x) * 0.5))
        d = V((x * 0.9, 1, pitch + 0.2)).normalized()
        upv = V((0, -0.3, 1))
        add_feather(crest, root, d, upv, L, 0.13 + 0.03 * (L > 0.8), {'head': 1.0},
                    [(0, SNOW), (0.35, SNOW2), (0.7, ICE1), (0.92, ICE2), (1, ICE3)], bend=0.16, cup=0.3, nl=12, nw=4,
                    shaft=True, roundness=1.2, roll=x * 2.0)
        if tipped:
            tip = root + d * L * 0.97 + V((0, 0, L * 0.16))
            add(tip - d * 0.03, (d + V((0, 0, 0.5))).normalized(), 0.16, 0.026, 'head')
    co = crest.build('ffk_crest', kit.mat_feather('ffk_crestm', rough=0.45, sheen=0.5, sss=0.2))
    co.modifiers.new('arm', 'ARMATURE').object = arm
    # wrist spurs and shoulder shards: clusters along the leading edge of each wing
    for s, sx in SIDE.items():
        w0 = SEG['hand.' + s][0]
        for k, (L, yaw, pitch) in enumerate(((0.55, -0.5, 0.5), (0.36, -0.2, 0.9), (0.3, -0.85, 0.2))):
            d = V((sx * math.cos(yaw) * 0.6, -math.sin(-yaw) - 0.4, pitch)).normalized()
            add(w0 + V((0, -0.12, 0.06)), d, L, 0.06 - 0.008 * k, 'forearm.' + s)
        s0 = SEG['shoulder.' + s][0]
        for k, (L, ox) in enumerate(((0.32, 0.1), (0.22, 0.3))):
            add(s0 + V((sx * ox, 0.05, 0.12)), V((sx * 0.4, 0.3, 1)).normalized(), L, 0.045, 'shoulder.' + s)
    # chest: the old design's ice-bead column, now a short line of small crystals in the chest ruff
    o = mb.build('ffk_ice', kit.mat_ice('ffk_icem', '#b9ecff', emit=0.6))
    for p in o.data.polygons:
        p.use_smooth = False
    o.modifiers.new('arm', 'ARMATURE').object = arm
    return o, co


# ------------------------------------------------------------------ red knitted scarf
SCARF = '#c4122c'


def scarf(arm):
    mb = kit.MeshBuilder()
    red = C(SCARF)
    redD = C('#7c0a1e')
    # two loose wraps around the base of the neck, the lower one dipping at the front
    vs, fs, cs = [], [], []
    seg, rs = 72, 14
    for wrap, (zc, R, dip, tilt, ph0) in enumerate(((3.4, 0.5, -0.06, 0.03, 0.0), (3.24, 0.55, 0.14, -0.04, 1.3))):
        ring_c = V((0, -0.08, zc))
        base = len(vs)
        for i in range(seg):
            a = 2 * math.pi * i / seg
            cdir = V((math.sin(a), -math.cos(a), 0))
            front = max(0.0, -cdir.y) ** 2
            ctr = ring_c + V((cdir.x * R, cdir.y * R * 1.06, -dip * front + tilt * cdir.x))
            fold = 1 + 0.16 * math.sin(a * 4 + ph0) + 0.07 * math.sin(a * 11 + ph0 * 2)
            for j in range(rs):
                b = 2 * math.pi * j / rs
                p = ctr + cdir * (math.cos(b) * 0.04 * fold + 0.02 * math.sin(b) ** 2) + V((0, 0, math.sin(b) * 0.12 * (2 - fold)))
                vs.append(tuple(p))
                cs.append(kit.lerp3(red, redD, 0.25 + 0.35 * math.sin(a * 4 + ph0) * math.cos(b)))
        for i in range(seg):
            for j in range(rs):
                a0 = base + i * rs + j
                b0 = base + i * rs + (j + 1) % rs
                c2 = base + ((i + 1) % seg) * rs + j
                d2 = base + ((i + 1) % seg) * rs + (j + 1) % rs
                fs.append((a0, b0, d2, c2))
    W = kit.skin_weights([V(v) for v in vs], {'chest': SEG['chest'], 'neck': SEG['neck']}, {'chest': 0.6, 'neck': 0.6})
    mb.add(vs, fs, cs, None, W)
    # knot at the front-right
    kc = V((0.26, -0.64, 3.2))
    for k in range(2):
        secs = []
        for i in range(9):
            a = math.pi * i / 8
            p = kc + V((0.1 * math.cos(a) * (1 if k else -1), -0.04 * math.sin(a), 0.08 * math.sin(a) - 0.04))
            secs.append((p, 0.07, 0.06, V((math.sin(a), 0, math.cos(a)))))
        v2, f2, c2 = kit.loft(secs, ring=10, cols=[redD] * len(secs))
        mb.add(v2, f2, c2, None, {'chest': 1.0})
    # hanging tail: a flat ribbon down the chest, skinned to three bones so it can flutter
    s0, _ = SEG['scarf0']
    pts = [SEG['scarf0'][0], SEG['scarf0'][1], SEG['scarf1'][1], SEG['scarf2'][1] + V((0.04, 0.05, -0.12))]
    path = []
    for i in range(16):
        t = i / 15 * 3
        k = min(2, int(t))
        path.append(pts[k].lerp(pts[k + 1], t - k) + V((0, -0.06 * math.sin(t * 1.4), 0)))
    secs, cols = [], []
    for i, p in enumerate(path):
        d = (path[min(15, i + 1)] - path[max(0, i - 1)]).normalized()
        w = 0.15 + 0.04 * (i / 15)
        secs.append((p, w, 0.035, d))
        cols.append(kit.lerp3(red, redD, 0.3 + 0.3 * math.sin(i)))
    v2, f2, c2 = kit.loft(secs, ring=12, cols=cols)
    W = kit.skin_weights([V(v) for v in v2], {k: SEG[k] for k in ('scarf0', 'scarf1', 'scarf2')},
                         {'scarf0': 0.3, 'scarf1': 0.3, 'scarf2': 0.35})
    mb.add(v2, f2, c2, None, W)
    # fringe at the end
    end = path[-1]
    d = (path[-1] - path[-2]).normalized()
    xax = d.cross(V((0, 1, 0))).normalized()
    for k in range(9):
        o = (k / 8 * 2 - 1) * 0.16
        secs = []
        for i in range(4):
            t = i / 3
            secs.append((end + xax * o + d * (0.02 + 0.14 * t) + V((0, 0, 0)), 0.014, 0.014, d))
        v3, f3, c3 = kit.loft(secs, ring=6, cols=[redD] * 4)
        mb.add(v3, f3, c3, None, {'scarf2': 1.0})
    o = mb.build('ffk_scarf', kit.mat_vcol('ffk_knit', rough=0.9, coat=0.0, sss=0.1, bump_scale=0))
    # knit look on top of the vertex colors
    m = o.data.materials[0]
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Sheen Weight'].default_value = 0.35
    b.inputs['Sheen Tint'].default_value = (1.0, 0.35, 0.35, 1)
    b.inputs['Sheen Roughness'].default_value = 0.5
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = 22.0
    wave.inputs['Distortion'].default_value = 3.0
    wave.inputs['Detail'].default_value = 3.0
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 300.0
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.6
    nt.links.new(tc.outputs['Object'], wave.inputs['Vector'])
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(wave.outputs['Fac'], add.inputs[0])
    nt.links.new(noise.outputs['Fac'], add.inputs[1])
    nt.links.new(add.outputs[0], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    o.modifiers.new('arm', 'ARMATURE').object = arm
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    return o


# ------------------------------------------------------------------ assemble
def place_eyes():
    """Find where each eye meets the sculpted head (raycast on a quick body without brows), then sink it."""
    els = [e for e in body_elements() if not e.get('brow')]
    probe = kit.metaball_body('ffk_probe', els, resolution=0.05, remesh=0.04, smooth_iter=2)
    bvh = kit.bvh_of(probe)
    for s, sx in SIDE.items():
        look = LOOK[s]
        hit = bvh.ray_cast(HEAD + look * 1.5, -look)[0]
        EYES[s] = hit - look * 0.085
    bpy.data.objects.remove(probe)


def build(steps=None):
    """steps: optional callback(label) called after each stage (used by the timelapse recorder)."""
    tick = steps or (lambda label: None)
    root = kit.empty('Freezer Flock')
    arm = kit.make_armature('ffk_rig', BONES, parent=root)
    tick('skeleton')
    place_eyes()
    body, bb, radii = build_body(arm)
    body.parent = root
    tick('body')
    eyes = [snowflake_eye(arm, s) for s in 'LR']
    tick('eyes')
    bk = beak(arm)
    tick('beak')
    hf, bf = body_feathers(body, arm, bb, radii)
    tick('feathers')
    wings = [wing(arm, s) for s in 'LR']
    tick('wings')
    tl = tail(arm)
    tick('tail')
    lg = legs(arm)
    tick('legs')
    ic = ice(arm)
    tick('ice')
    sc = scarf(arm)
    tick('scarf')
    for o in list(root.children_recursive):
        pass
    import bpy
    # every deformed mesh rides on the armature object, so moving the rig moves the whole bird
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers):
            o.parent = arm
        elif o.type == 'MESH' and o.parent is None:
            o.parent = root
    return dict(root=root, arm=arm, body=body)


def pose_bones(arm, rots):
    for n, r in rots.items():
        arm.pose.bones[n].rotation_euler = r


def display_pose():
    """Heraldic hover: wings raised high and swept forward, head turned toward the camera."""
    P = {}
    for s, sx in SIDE.items():
        # local X raises the wing (same sign both sides); local Y rolls it and Z sweeps it (mirrored)
        P['shoulder.' + s] = (0.55, sx * -1.05, sx * -0.3)
        P['forearm.' + s] = (-0.1, sx * 0.1, sx * 0.3)
        P['hand.' + s] = (-0.15, sx * 0.05, sx * -0.12)
        P['thigh.' + s] = (0.25, 0, 0)
        P['shin.' + s] = (-0.2, 0, 0)
    P['chest'] = (0.08, 0, 0)
    P['neck'] = (-0.12, 0, 0)
    P['head'] = (0.08, 0, 0)
    P['tail'] = (-0.25, 0, 0)
    return P
