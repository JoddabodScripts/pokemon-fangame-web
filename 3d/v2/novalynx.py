"""Novalynx (015), Normal. Glimmvix grown into a big night lynx. Its two tails have grown back into
one long tail with a large star at the end. Glowing spots dot its back like stars, its ear tufts
glow gold, and a bigger star sits on its forehead.

Same build as Twinkit and Glimmvix. Faces -Y, stands on z = 0, about 2.7 tall to the ear tufts.
"""
import math

import bpy
import numpy as np
from mathutils import Vector as V

import kit
from kit import srgb as C
import sv
from sv import El, ell, frame, tube

KEY = 'novalynx'
P_ = 'nvx_'
SIZE = 0.6           # 160 cm tall in the game
SIDE = {'L': -1, 'R': 1}

NIGHT = C('#252c6e')
NIGHT_D = C('#161a46')
INDIGO = C('#3c3f96')
CREAM = C('#fff0d4')
GOLD = C('#f2ad42')
GLOW = C('#ffd36a')
LILAC = C('#a995ff')
INK = C('#11122b')

HEAD = V((0, -0.88, 2.06))
LOOK = {s: V((sx * 0.6, -1, 0.02)).normalized() for s, sx in SIDE.items()}
TAIL = [(0, 0.9, 1.4), (0, 1.22, 1.52), (0, 1.48, 1.76), (0, 1.6, 2.08), (0, 1.54, 2.36)]


def bones():
    B = [('root', (0, 0, 0), (0, 0, 0.3), None, False),
         ('hips', (0, 0.7, 1.28), (0, 0.0, 1.28), 'root', True),
         ('chest', (0, 0.0, 1.28), (0, -0.46, 1.4), 'hips', True),
         ('neck', (0, -0.46, 1.4), (0, -0.78, 1.86), 'chest', True),
         ('head', (0, -0.78, 1.86), (0, -0.88, 2.36), 'neck', True),
         ('tail0', TAIL[0], TAIL[1], 'hips', True),
         ('tail1', TAIL[1], TAIL[3], 'tail0', True),
         ('tail2', TAIL[3], TAIL[4], 'tail1', True)]
    for s, sx in SIDE.items():
        B += [('ear.' + s, (sx * 0.22, -0.84, 2.3), (sx * 0.4, -0.8, 2.75), 'head', True),
              ('arm.' + s, (sx * 0.24, -0.42, 1.2), (sx * 0.25, -0.46, 0.62), 'chest', True),
              ('hand.' + s, (sx * 0.25, -0.46, 0.62), (sx * 0.25, -0.6, 0.07), 'arm.' + s, True),
              ('thigh.' + s, (sx * 0.24, 0.66, 1.24), (sx * 0.26, 0.84, 0.8), 'hips', True),
              ('shin.' + s, (sx * 0.26, 0.84, 0.8), (sx * 0.26, 0.78, 0.16), 'thigh.' + s, True),
              ('foot.' + s, (sx * 0.26, 0.78, 0.16), (sx * 0.26, 0.62, 0.06), 'shin.' + s, True)]
    return B


def seg(B):
    return {n: (V(h), V(t)) for n, h, t, p, d in B if d}


# ------------------------------------------------------------------ paint
def solid(c, g=0.0):
    def f(q, P, bc, bg):
        return np.tile(np.array(c), (len(q), 1)), np.full(len(q), g)
    return f


def ear_paint(q, P, bc, bg):
    n = len(q)
    col = np.tile(np.array(NIGHT), (n, 1))
    inner = (q[:, 2] > 0.25) & (np.abs(q[:, 0]) < 0.58 * (1 - np.clip(q[:, 1], -1, 1) * 0.55)) & (q[:, 1] < 0.5) & (q[:, 1] > -0.75)
    col[inner] = LILAC
    edge = (q[:, 2] > 0.25) & ~inner & (q[:, 1] > -0.6)
    col[edge] = INDIGO
    return col, np.zeros(n)


def snout_paint(q, P, bc, bg):
    n = len(q)
    col = np.tile(np.array(CREAM), (n, 1))
    bridge = sv.smoothstep(0.4, 0.7, q[:, 2]) * sv.smoothstep(0.5, 0.28, np.abs(q[:, 0]))
    col += (np.array(NIGHT) - col) * bridge[:, None]
    ax = np.abs(q[:, 0])
    front = q[:, 1] < -0.4
    zc = -0.22 - 0.2 * np.sin(np.pi * np.clip(ax / 0.5, 0, 1))
    mouth = front & (ax < 0.5) & (np.abs(q[:, 2] - zc) < 0.06)
    philtrum = front & (ax < 0.045) & (q[:, 2] > -0.24) & (q[:, 2] < 0.3)
    col[mouth | philtrum] = INK
    return col, np.zeros(n)


def leg_paint(q, P, bc, bg):
    sock = sv.smoothstep(0.34, 0.26, P[:, 2])
    col = np.tile(np.array(NIGHT), (len(q), 1))
    col += (np.array(GOLD) - col) * sock[:, None]
    return col, np.zeros(len(q))


def tail_paint(q, P, bc, bg):
    d = np.linalg.norm(P - np.array(TAIL[-1]), axis=1)
    t = sv.smoothstep(0.5, 0.3, d)
    col = np.tile(np.array(NIGHT), (len(q), 1))
    col += (np.array(CREAM) - col) * t[:, None]
    # a faint glowing streak up the top of the tail, like a comet trail
    top = sv.smoothstep(0.09, 0.03, np.abs(P[:, 0])) * sv.smoothstep(0.42, 0.62, d) * (P[:, 2] > 1.45)
    col += (np.array(GLOW) - col) * (top * 0.85)[:, None]
    return col, top * 0.8


def body_paint(P):
    n = len(P)
    ss = sv.smoothstep
    col = np.tile(np.array(NIGHT), (n, 1))
    under = ss(1.06, 0.96, P[:, 2]) * ss(0.7, 0.5, P[:, 1])
    bib = ss(-0.62, -0.74, P[:, 1]) * ss(0.3, 0.18, np.abs(P[:, 0])) * ss(1.95, 1.8, P[:, 2])
    throat = ss(-0.66, -0.8, P[:, 1]) * ss(0.2, 0.1, np.abs(P[:, 0])) * ss(1.4, 1.55, P[:, 2]) * ss(2.0, 1.9, P[:, 2])
    face = ss(-0.92, -1.04, P[:, 1]) * ss(2.06, 1.96, P[:, 2])
    m = np.clip(under + bib + throat + face, 0, 1)
    col += (np.array(CREAM) - col) * m[:, None]
    # lighter indigo on the flanks, dark saddle along the spine
    flank = ss(0.18, 0.32, np.abs(P[:, 0])) * ss(1.0, 1.15, P[:, 2]) * ss(1.5, 1.35, P[:, 2]) * (1 - m)
    col += (np.array(INDIGO) - col) * (flank * 0.6)[:, None]
    back = ss(0.16, 0.03, np.abs(P[:, 0])) * ss(1.5, 1.62, P[:, 2]) * ss(-0.6, -0.4, P[:, 1]) * ss(1.0, 0.85, P[:, 1])
    col += (np.array(NIGHT_D) - col) * (back * 0.85)[:, None]
    # glowing star spots scattered over the back, shoulders and haunches
    glow = np.zeros(n)
    rng = np.random.default_rng(7)
    cand = np.where((P[:, 2] > 1.42) & (P[:, 1] > -0.62) & (P[:, 1] < 1.0) & (P[:, 2] < 1.9))[0]
    rng.shuffle(cand)
    spots = []
    for i in cand:
        p = P[i]
        if all(np.linalg.norm(p - s_) > 0.3 for s_, _ in spots):
            spots.append((p, rng.uniform(0.016, 0.034) * (1.6 if len(spots) % 5 == 0 else 1.0)))
        if len(spots) >= 14:
            break
    for p, r in spots:
        d = np.linalg.norm(P - p, axis=1)
        core = ss(r, r * 0.6, d)
        halo = ss(r * 2.6, r, d) * 0.25
        k = np.maximum(core, halo)
        col += (np.array(GLOW) - col) * k[:, None]
        glow = np.maximum(glow, core * 1.0 + halo * 0.4)
    return col, glow


# ------------------------------------------------------------------ shapes
def elements():
    E = []
    E.append(ell((0, -0.36, 1.32), (0.4, 0.42, 0.43), (0.15, 0, 0)))
    E.append(ell((0, 0.15, 1.27), (0.34, 0.56, 0.33)))
    E.append(ell((0, 0.66, 1.3), (0.37, 0.36, 0.37)))
    E += tube([(0, -0.5, 1.5), (0, -0.72, 1.8), (0, -0.82, 1.96)], [0.26, 0.22, 0.21], normal=(0, -1, 0))
    E.append(ell(tuple(HEAD), (0.43, 0.39, 0.37)))
    E.append(ell((0, -0.84, 2.28), (0.31, 0.27, 0.17)))
    E.append(ell((0, -1.2, 1.95), (0.21, 0.18, 0.15), (0.12, 0, 0), paint=snout_paint))
    E.append(ell((0, -1.37, 1.99), (0.065, 0.048, 0.048), paint='solid', color=INK, probe=False))
    for s, sx in SIDE.items():
        if sx < 0:
            continue
        f = LOOK[s]
        r = V((0, 0, 1)).cross(f).normalized()
        u = f.cross(r).normalized()
        e = HEAD + f * 0.38
        # heavy brow: a dark shelf over each eye, lower toward the nose
        along = r * sx * math.cos(math.radians(16)) + u * math.sin(math.radians(16))
        E.append(El(e + u * 0.135 + f * 0.04, (0.06, 0.17, 0.045), frame(along, f), paint='solid', color=NIGHT_D,
                    probe=False))
        # tall ears with glowing gold tufts
        root = V((sx * 0.22, -0.84, 2.3))
        d = V((sx * 0.35, 0.1, 1)).normalized()
        E.append(El(root + d * 0.27, (0.18, 0.3, 0.065), frame(d, (sx * 0.1, -1, 0.15)), paint=ear_paint,
                    weights={'ear.' + s: 1.0}))
        E.append(El(root + d * 0.52, (0.08, 0.14, 0.045), frame(d, (sx * 0.1, -1, 0.15)), paint=solid(NIGHT),
                    weights={'ear.' + s: 1.0}))
        E.append(El(root + d * 0.78, (0.035, 0.17, 0.03), frame(d + V((sx * 0.15, 0, 0)), (0, -1, 0)), paint=solid(GOLD, 0.35),
                    weights={'ear.' + s: 1.0}))
        # lynx cheek ruff: cream tufts sweeping back and down from the jaw
        for rt, dd, L in (((0.37, -0.9, 1.98), (0.4, 0.85, -0.5), 0.22), ((0.33, -0.84, 1.86), (0.3, 0.85, -0.65), 0.2)):
            dv = V((sx * dd[0], dd[1], dd[2])).normalized()
            E.append(El(V((sx * rt[0], rt[1], rt[2])) + dv * L * 0.4, (0.085, L, 0.05), frame(dv, (sx * 0.85, -0.4, 0.2)),
                        paint='solid', color=CREAM))
        # shoulders
        E.append(ell((sx * 0.25, -0.32, 1.48), (0.2, 0.28, 0.22)))
        # strong front legs, big paws
        E += tube([(sx * 0.24, -0.4, 1.22), (sx * 0.25, -0.45, 0.72), (sx * 0.25, -0.47, 0.16)], [0.17, 0.11, 0.1],
                  paint=leg_paint)
        E.append(ell((sx * 0.25, -0.57, 0.08), (0.13, 0.17, 0.085), paint=leg_paint, weights={'hand.' + s: 1.0}))
        # haunch, hock and paw
        E.append(ell((sx * 0.24, 0.68, 1.1), (0.22, 0.36, 0.36), (0.35, 0, 0)))
        E += tube([(sx * 0.26, 0.78, 0.84), (sx * 0.26, 0.86, 0.48), (sx * 0.26, 0.78, 0.15)], [0.13, 0.1, 0.095],
                  paint=leg_paint)
        E.append(ell((sx * 0.26, 0.68, 0.08), (0.13, 0.17, 0.085), paint=leg_paint, weights={'foot.' + s: 1.0}))
    E = sv.mirror(E)
    E += tube(TAIL, [0.11, 0.18, 0.21, 0.19, 0.13], flat=0.85, normal=(1, 0, 0), paint=tail_paint)
    return E


def radii():
    r = dict(hips=0.48, chest=0.5, neck=0.32, head=0.55, tail0=0.2, tail1=0.26, tail2=0.22)
    for s in 'LR':
        r.update({'arm.' + s: 0.2, 'hand.' + s: 0.15, 'thigh.' + s: 0.28, 'shin.' + s: 0.15, 'foot.' + s: 0.13,
                  'ear.' + s: 0.22})
    return r


def eyes(arm, E):
    hits = sv.probe_hit(E, [HEAD + LOOK[s] * 1.4 for s in SIDE], [-LOOK[s] for s in SIDE])
    mb = kit.MeshBuilder()
    for (s, sx), hit in zip(SIDE.items(), hits):
        f = LOOK[s]
        sv.eye_mesh(mb, hit - f * 0.025, f, (0, 0, 1), 0.13, 0.11, 0.045,
                    iris=[C('#7a4a06'), C('#d89418'), C('#ffd24a'), C('#fff2b0')], pupil=INK, rim=INK,
                    shine=[(-0.3, 0.32, 0.2), (0.32, -0.38, 0.09)], weights={'head': 1.0}, tilt=sx * 0.2,
                    slit=(0.16, 0.62))
    o = mb.build(P_ + 'eyes', sv.eye_material(P_ + 'eyem'))
    o.modifiers.new('arm', 'ARMATURE').object = arm
    return o


def display_pose(arm):
    pb = arm.pose.bones
    pb['head'].rotation_euler = (0.06, 0, -0.14)
    pb['tail1'].rotation_euler = (0, 0, 0.1)
    pb['tail2'].rotation_euler = (-0.05, 0, 0.15)


def build():
    root = kit.empty('Novalynx')
    B = bones()
    arm = kit.make_armature(P_ + 'rig', B, parent=root)
    E = elements()
    body = sv.build_body(P_ + 'body', E, arm, body_paint, seg(B), radii(), sv.body_material(P_ + 'fur', sheen=0.6, glow=4.0),
                         resolution=0.035, voxel=0.022)
    eyes(arm, E)
    tip = V(TAIL[-1]) + V((0, -0.02, 0.2))
    sv.star(arm, P_, tip, 0.3, 'star', 'tail2', face=(0, -1, 0.1), depth=0.1)
    sv.star_light(P_, tip + V((0, -0.3, 0)), 10.0, arm)
    fh = sv.probe_hit(E, [HEAD + V((0, -1.4, 0.75))], [V((0, 1.0, -0.5))])[0]
    sv.star(arm, P_, fh, 0.12, 'brow_star', 'head', face=(0, -1, 0.5), depth=0.025)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.parent is None:
            o.parent = arm
    arm.scale = (SIZE, SIZE, SIZE)
    return dict(root=root, arm=arm, body=body)
