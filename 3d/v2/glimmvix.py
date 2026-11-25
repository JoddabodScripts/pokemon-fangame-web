"""Glimmvix (014), Normal. Twinkit grown into a lean dusk fox: the coat turns night blue, the tail
splits in two, and both tips carry a glowing star. A small star shows on its forehead.

Same build as Twinkit. Faces -Y, stands on z = 0, about 2.2 tall to the ear tips at design scale.
"""
import math

import bpy
import numpy as np
from mathutils import Vector as V

import kit
from kit import srgb as C
import sv
from sv import El, ell, frame, tube

KEY = 'glimmvix'
P_ = 'glx_'
SIZE = 0.41          # 90 cm tall in the game
SIDE = {'L': -1, 'R': 1}

NIGHT = C('#2f3a86')
NIGHT_D = C('#1d2358')
CREAM = C('#fff1d6')
GOLD = C('#f2b24a')
LILAC = C('#b7a2ff')
INK = C('#141633')

HEAD = V((0, -0.64, 1.62))
LOOK = {s: V((sx * 0.62, -1, 0.04)).normalized() for s, sx in SIDE.items()}
TAIL = {s: [(0, 0.66, 1.0), (sx * 0.08, 0.92, 1.12), (sx * 0.26, 1.12, 1.36), (sx * 0.38, 1.2, 1.66), (sx * 0.4, 1.12, 1.9)]
        for s, sx in SIDE.items()}


def bones():
    B = [('root', (0, 0, 0), (0, 0, 0.3), None, False),
         ('hips', (0, 0.5, 0.95), (0, 0.0, 0.95), 'root', True),
         ('chest', (0, 0.0, 0.95), (0, -0.36, 1.05), 'hips', True),
         ('neck', (0, -0.36, 1.05), (0, -0.56, 1.42), 'chest', True),
         ('head', (0, -0.56, 1.42), (0, -0.64, 1.86), 'neck', True)]
    for s, sx in SIDE.items():
        t = TAIL[s]
        B += [('ear.' + s, (sx * 0.15, -0.6, 1.8), (sx * 0.33, -0.56, 2.22), 'head', True),
              ('arm.' + s, (sx * 0.16, -0.34, 0.88), (sx * 0.17, -0.37, 0.44), 'chest', True),
              ('hand.' + s, (sx * 0.17, -0.37, 0.44), (sx * 0.17, -0.47, 0.05), 'arm.' + s, True),
              ('thigh.' + s, (sx * 0.17, 0.46, 0.92), (sx * 0.18, 0.6, 0.55), 'hips', True),
              ('shin.' + s, (sx * 0.18, 0.6, 0.55), (sx * 0.18, 0.56, 0.12), 'thigh.' + s, True),
              ('foot.' + s, (sx * 0.18, 0.56, 0.12), (sx * 0.18, 0.44, 0.04), 'shin.' + s, True),
              ('tail0.' + s, t[0], t[1], 'hips', True),
              ('tail1.' + s, t[1], t[3], 'tail0.' + s, True),
              ('tail2.' + s, t[3], t[4], 'tail1.' + s, True)]
    return B


def seg(B):
    return {n: (V(h), V(t)) for n, h, t, p, d in B if d}


# ------------------------------------------------------------------ paint
def ear_paint(q, P, bc, bg):
    n = len(q)
    col = np.tile(np.array(NIGHT), (n, 1))
    tip = sv.smoothstep(0.42, 0.6, q[:, 1])
    col += (np.array(GOLD) - col) * tip[:, None]
    inner = (q[:, 2] > 0.25) & (np.abs(q[:, 0]) < 0.6 * (1 - np.clip(q[:, 1], -1, 1) * 0.55)) & (q[:, 1] < 0.45) & (q[:, 1] > -0.75)
    col[inner] = LILAC
    return col, np.zeros(n)


def solid(c):
    def f(q, P, bc, bg):
        return np.tile(np.array(c), (len(q), 1)), np.zeros(len(q))
    return f


def snout_paint(q, P, bc, bg):
    """Cream snout, navy on the bridge, a small closed smile."""
    n = len(q)
    col = np.tile(np.array(CREAM), (n, 1))
    bridge = sv.smoothstep(0.35, 0.65, q[:, 2]) * sv.smoothstep(0.55, 0.3, np.abs(q[:, 0]))
    col += (np.array(NIGHT) - col) * bridge[:, None]
    ax = np.abs(q[:, 0])
    under = (q[:, 2] < -0.05) & (q[:, 1] < -0.2)
    zc = -0.25 - 0.18 * np.clip(ax / 0.5, 0, 1) ** 2
    mouth = under & (ax < 0.62) & (np.abs(q[:, 2] - zc) < 0.06) & (q[:, 1] < 0.4)
    col[mouth] = INK
    return col, np.zeros(n)


def leg_paint(q, P, bc, bg):
    """Night-blue legs with gold socks."""
    sock = sv.smoothstep(0.3, 0.24, P[:, 2])
    col = np.tile(np.array(NIGHT), (len(q), 1))
    col += (np.array(GOLD) - col) * sock[:, None]
    return col, np.zeros(len(q))


def tail_paint(q, P, bc, bg):
    tips = np.array([TAIL[s][-1] for s in SIDE])
    d = np.min(np.linalg.norm(P[:, None, :] - tips[None], axis=2), axis=1)
    t = sv.smoothstep(0.42, 0.26, d)
    col = np.tile(np.array(NIGHT), (len(q), 1))
    col += (np.array(CREAM) - col) * t[:, None]
    return col, np.zeros(len(q))


def body_paint(P):
    n = len(P)
    ss = sv.smoothstep
    col = np.tile(np.array(NIGHT), (n, 1))
    # cream underside: belly, chest bib, throat and the lower face
    under = ss(0.8, 0.72, P[:, 2]) * ss(0.75, 0.6, P[:, 1])
    bib = ss(-0.48, -0.58, P[:, 1]) * ss(0.24, 0.14, np.abs(P[:, 0])) * ss(1.5, 1.38, P[:, 2])
    throat = ss(-0.5, -0.62, P[:, 1]) * ss(0.16, 0.08, np.abs(P[:, 0])) * ss(1.1, 1.2, P[:, 2]) * ss(1.55, 1.45, P[:, 2])
    face = ss(-0.66, -0.76, P[:, 1]) * ss(1.58, 1.5, P[:, 2])
    cheek = ss(0.18, 0.26, np.abs(P[:, 0])) * ss(-0.5, -0.62, P[:, 1]) * ss(1.6, 1.5, P[:, 2]) * ss(1.35, 1.42, P[:, 2])
    m = np.clip(under + bib + throat + face + cheek, 0, 1)
    col += (np.array(CREAM) - col) * m[:, None]
    # darker saddle along the spine
    back = ss(0.12, 0.02, np.abs(P[:, 0])) * ss(1.1, 1.2, P[:, 2]) * ss(-0.4, -0.2, P[:, 1]) * ss(0.7, 0.55, P[:, 1])
    col += (np.array(NIGHT_D) - col) * (back * 0.8)[:, None]
    return col, np.zeros(n)


# ------------------------------------------------------------------ shapes
def elements():
    E = []
    # lean torso: deep chest, tucked belly, rounded hips
    E.append(ell((0, -0.28, 0.98), (0.3, 0.32, 0.33), (0.15, 0, 0)))
    E.append(ell((0, 0.1, 0.95), (0.26, 0.42, 0.25)))
    E.append(ell((0, 0.46, 0.98), (0.28, 0.28, 0.28)))
    # neck and head with a fox snout
    E += tube([(0, -0.36, 1.1), (0, -0.52, 1.36), (0, -0.6, 1.5)], [0.18, 0.15, 0.15], normal=(0, -1, 0))
    E.append(ell(tuple(HEAD), (0.35, 0.32, 0.31)))
    E.append(ell((0, -0.6, 1.8), (0.25, 0.22, 0.14)))
    E.append(ell((0, -0.96, 1.5), (0.14, 0.21, 0.115), (0.25, 0, 0), paint=snout_paint))
    E.append(ell((0, -1.15, 1.53), (0.05, 0.04, 0.04), paint='solid', color=INK, probe=False))
    for s, sx in SIDE.items():
        if sx < 0:
            continue
        root = V((sx * 0.17, -0.6, 1.84))
        d = V((sx * 0.42, 0.08, 1)).normalized()
        E.append(El(root + d * 0.24, (0.16, 0.27, 0.058), frame(d, (sx * 0.1, -1, 0.15)), paint=ear_paint,
                    weights={'ear.' + s: 1.0}))
        E.append(El(root + d * 0.47, (0.065, 0.12, 0.04), frame(d, (sx * 0.1, -1, 0.15)), paint=solid(GOLD),
                    weights={'ear.' + s: 1.0}))
        # cheek fur sweeping back along the jaw
        for rt, dd, L in (((0.24, -0.66, 1.52), (0.55, 0.6, -0.35), 0.17), ((0.22, -0.6, 1.44), (0.45, 0.6, -0.65), 0.14)):
            dv = V((sx * dd[0], dd[1], dd[2])).normalized()
            E.append(El(V((sx * rt[0], rt[1], rt[2])) + dv * L * 0.45, (0.07, L, 0.045), frame(dv, (sx * 0.4, -0.6, 0.3)),
                        paint='solid', color=CREAM))
        # long front legs
        E += tube([(sx * 0.15, -0.32, 0.9), (sx * 0.17, -0.36, 0.55), (sx * 0.17, -0.38, 0.12)], [0.12, 0.082, 0.072],
                  paint=leg_paint)
        E.append(ell((sx * 0.17, -0.46, 0.055), (0.09, 0.13, 0.065), paint=leg_paint, weights={'hand.' + s: 1.0}))
        # back legs: thigh, hock bent back, paw
        E.append(ell((sx * 0.16, 0.48, 0.8), (0.17, 0.27, 0.28), (0.35, 0, 0)))
        E += tube([(sx * 0.18, 0.56, 0.62), (sx * 0.18, 0.62, 0.36), (sx * 0.18, 0.56, 0.11)], [0.1, 0.075, 0.07],
                  paint=leg_paint)
        E.append(ell((sx * 0.18, 0.48, 0.055), (0.09, 0.13, 0.065), paint=leg_paint, weights={'foot.' + s: 1.0}))
        # one of the two tails
        E += tube(TAIL[s], [0.08, 0.15, 0.18, 0.16, 0.1], flat=0.85, normal=(1, 0, 0), paint=tail_paint)
    return sv.mirror(E)


def radii():
    r = dict(hips=0.34, chest=0.36, neck=0.24, head=0.42)
    for s in 'LR':
        r.update({'arm.' + s: 0.12, 'hand.' + s: 0.1, 'thigh.' + s: 0.2, 'shin.' + s: 0.1, 'foot.' + s: 0.09,
                  'ear.' + s: 0.18, 'tail0.' + s: 0.14, 'tail1.' + s: 0.2, 'tail2.' + s: 0.16})
    return r


def eyes(arm, E):
    hits = sv.probe_hit(E, [HEAD + LOOK[s] * 1.4 + V((0, 0, 0.0)) for s in SIDE], [-LOOK[s] for s in SIDE])
    mb = kit.MeshBuilder()
    for (s, sx), hit in zip(SIDE.items(), hits):
        f = LOOK[s]
        sv.eye_mesh(mb, hit - f * 0.02, f, (0, 0, 1), 0.12, 0.115, 0.045,
                    iris=[C('#3a2a7a'), C('#6a4ad0'), C('#b48cff'), C('#ffd27a')], pupil=INK, rim=INK,
                    shine=[(-0.3, 0.35, 0.22), (0.3, -0.4, 0.1)], weights={'head': 1.0}, tilt=sx * 0.28)
    o = mb.build(P_ + 'eyes', sv.eye_material(P_ + 'eyem'))
    o.modifiers.new('arm', 'ARMATURE').object = arm
    return o


def display_pose(arm):
    pb = arm.pose.bones
    pb['head'].rotation_euler = (0.08, 0, -0.15)
    pb['neck'].rotation_euler = (-0.05, 0, 0)


def build():
    root = kit.empty('Glimmvix')
    B = bones()
    arm = kit.make_armature(P_ + 'rig', B, parent=root)
    E = elements()
    body = sv.build_body(P_ + 'body', E, arm, body_paint, seg(B), radii(), sv.body_material(P_ + 'fur', sheen=0.6))
    eyes(arm, E)
    for s, sx in SIDE.items():
        tip = V(TAIL[s][-1]) + V((sx * 0.02, -0.02, 0.14))
        sv.star(arm, P_, tip, 0.2, 'star.' + s, 'tail2.' + s, face=(sx * 0.3, -1, 0.1), depth=0.075, spin=-sx * 0.25)
        sv.star_light(P_, tip + V((0, -0.2, 0)), 4.0, arm, 'starlight.' + s)
    # small star on the forehead, laid onto the fur
    fh = sv.probe_hit(E, [HEAD + V((0, -1.2, 0.55))], [V((0, 1.0, -0.42))])[0]
    sv.star(arm, P_, fh + V((0, -0.005, 0)), 0.075, 'brow_star', 'head', face=(0, -1, 0.55), depth=0.02)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.parent is None:
            o.parent = arm
    arm.scale = (SIZE, SIZE, SIZE)
    return dict(root=root, arm=arm, body=body)
