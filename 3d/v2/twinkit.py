"""Twinkit (013), Normal. A fox kit with oversized ears and a glowing star on the tip of its tail.

Built the same way as Freezer Flock: metaball shapes fused into one painted body, with glossy eyes
and the star set in as separate pieces. Faces -Y, stands on z = 0. Design scale: about 1.7 tall to the
ear tips; SIZE turns that into its in-game height relative to the other models.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector as V

import kit
from kit import srgb as C
import sv
from sv import El, ell, frame, tube

KEY = 'twinkit'
P_ = 'twk_'
SIZE = 0.17          # 30 cm tall in the game; 1 unit = 1 m at SIZE 1
SIDE = {'L': -1, 'R': 1}

GOLD = C('#f0b14e')
GOLD_D = C('#d98a33')
CREAM = C('#fff3dc')
NAVY = C('#252b66')
LILAC = C('#b7a2ff')
STAR = C('#ffd447')

HEAD = V((0, -0.32, 1.08))
LOOK = {s: V((sx * 0.55, -1, 0.06)).normalized() for s, sx in SIDE.items()}


def bones():
    B = [('root', (0, 0, 0), (0, 0, 0.2), None, False),
         ('hips', (0, 0.34, 0.5), (0, 0.0, 0.55), 'root', True),
         ('chest', (0, 0.0, 0.55), (0, -0.22, 0.66), 'hips', True),
         ('neck', (0, -0.22, 0.66), (0, -0.3, 0.86), 'chest', True),
         ('head', (0, -0.3, 0.86), (0, -0.33, 1.36), 'neck', True),
         ('tail0', (0, 0.46, 0.56), (0, 0.72, 0.66), 'hips', True),
         ('tail1', (0, 0.72, 0.66), (0, 0.88, 0.95), 'tail0', True),
         ('tail2', (0, 0.88, 0.95), (0, 0.86, 1.36), 'tail1', True)]
    for s, sx in SIDE.items():
        B += [('ear.' + s, (sx * 0.2, -0.28, 1.34), (sx * 0.42, -0.26, 1.78), 'head', True),
              ('arm.' + s, (sx * 0.15, -0.18, 0.5), (sx * 0.16, -0.22, 0.12), 'chest', True),
              ('hand.' + s, (sx * 0.16, -0.22, 0.12), (sx * 0.16, -0.36, 0.05), 'arm.' + s, True),
              ('thigh.' + s, (sx * 0.17, 0.34, 0.45), (sx * 0.17, 0.4, 0.16), 'hips', True),
              ('foot.' + s, (sx * 0.17, 0.4, 0.16), (sx * 0.17, 0.26, 0.05), 'thigh.' + s, True)]
    return B


def seg(B):
    return {n: (V(h), V(t)) for n, h, t, p, d in B if d}


# ------------------------------------------------------------------ paint functions for special shapes
def ear_paint(q, P, bc, bg):
    """Gold ear, navy tip, lilac inside on the front face."""
    n = len(q)
    col = np.tile(np.array(GOLD), (n, 1))
    tip = sv.smoothstep(0.35, 0.55, q[:, 1])
    col += (np.array(NAVY) - col) * tip[:, None]
    inner = (q[:, 2] > 0.25) & (np.abs(q[:, 0]) < 0.62 * (1 - np.clip(q[:, 1], -1, 1) * 0.5)) & (q[:, 1] < 0.42) & (q[:, 1] > -0.75)
    col[inner] = LILAC
    return col, np.zeros(n)


def ear_tip_paint(q, P, bc, bg):
    n = len(q)
    return np.tile(np.array(NAVY), (n, 1)), np.zeros(n)


def muzzle_paint(q, P, bc, bg):
    """Cream muzzle with a little 'w' mouth under the nose."""
    n = len(q)
    col = np.tile(np.array(CREAM), (n, 1))
    ax = np.abs(q[:, 0])
    front = q[:, 1] < -0.45
    zc = -0.18 - 0.2 * np.sin(np.pi * np.clip(ax / 0.42, 0, 1))
    mouth = front & (ax < 0.42) & (np.abs(q[:, 2] - zc) < 0.07)
    philtrum = front & (ax < 0.05) & (q[:, 2] > -0.2) & (q[:, 2] < 0.3)
    col[mouth | philtrum] = NAVY
    return col, np.zeros(n)


def leg_paint(q, P, bc, bg):
    """Fur color above, navy socks below."""
    sock = sv.smoothstep(0.2, 0.16, P[:, 2])
    col = bc + (np.array(NAVY) - bc) * sock[:, None]
    return col, np.zeros(len(q))


def tail_paint(q, P, bc, bg):
    """Gold tail that fades to a cream puff at the end, just under the star."""
    t = sv.smoothstep(1.0, 1.22, P[:, 2])
    col = np.tile(np.array(GOLD), (len(q), 1))
    col += (np.array(CREAM) - col) * t[:, None]
    return col, np.zeros(len(q))


def body_paint(P):
    n = len(P)
    col = np.tile(np.array(GOLD), (n, 1))
    ss = sv.smoothstep
    # cream lower face and cheeks
    face = ss(-0.38, -0.5, P[:, 1]) * ss(1.06, 0.98, P[:, 2]) * ss(0.7, 0.6, P[:, 2] * 0 + 0.5)
    face = ss(-0.4, -0.52, P[:, 1]) * ss(1.07, 0.99, P[:, 2])
    side = ss(0.28, 0.36, np.abs(P[:, 0])) * ss(1.02, 0.92, P[:, 2]) * ss(0.85, 0.9, P[:, 2]) * ss(-0.1, -0.25, P[:, 1])
    # cream chest bib and belly
    bib = ss(-0.12, -0.24, P[:, 1]) * ss(0.88, 0.8, P[:, 2]) * ss(0.24, 0.16, np.abs(P[:, 0]))
    belly = ss(0.42, 0.34, P[:, 2]) * ss(0.2, 0.12, np.abs(P[:, 0])) * ss(0.55, 0.4, P[:, 1])
    m = np.clip(face + side + bib + belly, 0, 1)
    col += (np.array(CREAM) - col) * m[:, None]
    # a slightly deeper gold stripe down the back
    back = ss(0.08, 0.0, np.abs(P[:, 0])) * ss(0.6, 0.72, P[:, 2]) * ss(-0.1, 0.1, P[:, 1]) * ss(1.2, 1.0, P[:, 2])
    col += (np.array(GOLD_D) - col) * (back * 0.6)[:, None]
    return col, np.zeros(n)


# ------------------------------------------------------------------ shapes
def elements():
    E = []
    # torso: chest, belly and haunches
    E.append(ell((0, -0.12, 0.6), (0.26, 0.24, 0.26)))
    E.append(ell((0, 0.15, 0.55), (0.24, 0.34, 0.23), (0.1, 0, 0)))
    E.append(ell((0, -0.24, 0.8), (0.19, 0.17, 0.19)))
    # big round head with a short muzzle and a button nose
    E.append(ell(tuple(HEAD), (0.47, 0.41, 0.41)))
    E.append(ell((0, -0.3, 1.3), (0.3, 0.26, 0.17)))
    E.append(ell((0, -0.66, 0.96), (0.18, 0.17, 0.13), (-0.15, 0, 0), paint=muzzle_paint))
    E.append(ell((0, -0.825, 1.0), (0.055, 0.04, 0.04), paint='solid', color=NAVY, probe=False))
    for s, sx in SIDE.items():
        if sx < 0:
            continue
        # big ears
        root = V((sx * 0.2, -0.28, 1.34))
        d = V((sx * 0.5, 0.06, 1)).normalized()
        E.append(El(root + d * 0.26, (0.18, 0.28, 0.065), frame(d, (sx * 0.1, -1, 0.15)), paint=ear_paint,
                    weights={'ear.' + s: 1.0}))
        E.append(El(root + d * 0.5, (0.08, 0.12, 0.045), frame(d, (sx * 0.1, -1, 0.15)), paint=ear_tip_paint,
                    weights={'ear.' + s: 1.0}))
        # cheek fluff sweeping out and down
        for rt, dd, L in (((0.38, -0.36, 0.98), (0.75, 0.25, -0.55), 0.13), ((0.34, -0.3, 0.88), (0.5, 0.35, -0.8), 0.1)):
            dv = V((sx * dd[0], dd[1], dd[2])).normalized()
            E.append(El(V((sx * rt[0], rt[1], rt[2])) + dv * L * 0.45, (0.075, L, 0.05), frame(dv, (sx * 0.3, -1, 0.2)),
                        paint='solid', color=CREAM))
        # front legs with paws
        E += tube([(sx * 0.15, -0.16, 0.5), (sx * 0.16, -0.2, 0.3), (sx * 0.16, -0.23, 0.13)], [0.09, 0.075, 0.07],
                  paint=leg_paint)
        E.append(ell((sx * 0.16, -0.29, 0.06), (0.09, 0.12, 0.065), paint=leg_paint, weights={'hand.' + s: 1.0}))
        # haunch and back leg
        E.append(ell((sx * 0.15, 0.3, 0.42), (0.15, 0.2, 0.19)))
        E += tube([(sx * 0.17, 0.38, 0.34), (sx * 0.17, 0.41, 0.15)], [0.085, 0.07], paint=leg_paint)
        E.append(ell((sx * 0.17, 0.32, 0.06), (0.09, 0.12, 0.065), paint=leg_paint, weights={'foot.' + s: 1.0}))
    E = sv.mirror(E)
    # fluffy tail curling up behind
    E += tube([(0, 0.4, 0.55), (0, 0.66, 0.6), (0, 0.84, 0.82), (0, 0.9, 1.08), (0, 0.85, 1.3)],
              [0.08, 0.15, 0.22, 0.23, 0.15], flat=0.85, normal=(1, 0, 0), paint=tail_paint)
    return E


def radii():
    r = dict(hips=0.32, chest=0.32, neck=0.25, head=0.5, tail0=0.18, tail1=0.24, tail2=0.24)
    for s in 'LR':
        r.update({'arm.' + s: 0.12, 'hand.' + s: 0.1, 'thigh.' + s: 0.16, 'foot.' + s: 0.1, 'ear.' + s: 0.2})
    return r


# ------------------------------------------------------------------ set-in pieces
def eyes(arm, E):
    hits = sv.probe_hit(E, [HEAD + LOOK[s] * 1.5 + V((0, 0, -0.02)) for s in SIDE], [-LOOK[s] for s in SIDE])
    mb = kit.MeshBuilder()
    for (s, sx), hit in zip(SIDE.items(), hits):
        f = LOOK[s]
        sv.eye_mesh(mb, hit - f * 0.025, f, (0, 0, 1), 0.12, 0.155, 0.055,
                    iris=[C('#2a2470'), C('#4a40b4'), C('#8a78f0'), C('#d6c8ff')], pupil=C('#0f0f2a'), rim=C('#0f0f2a'),
                    shine=[(-0.3, 0.38, 0.24), (0.3, -0.42, 0.11)], weights={'head': 1.0}, tilt=sx * 0.12)
    o = mb.build(P_ + 'eyes', sv.eye_material(P_ + 'eyem'))
    o.modifiers.new('arm', 'ARMATURE').object = arm
    return o


def display_pose(arm):
    pb = arm.pose.bones
    pb['head'].rotation_euler = (0.05, 0, -0.12)
    pb['tail1'].rotation_euler = (0, 0, 0.12)
    pb['tail2'].rotation_euler = (-0.1, 0, 0.2)
    for s, sx in SIDE.items():
        pb['ear.' + s].rotation_euler = (0, 0, 0)


def build():
    root = kit.empty('Twinkit')
    B = bones()
    arm = kit.make_armature(P_ + 'rig', B, parent=root)
    E = elements()
    body = sv.build_body(P_ + 'body', E, arm, body_paint, seg(B), radii(), sv.body_material(P_ + 'fur'))
    eyes(arm, E)
    tip = V((0, 0.84, 1.52))
    sv.star(arm, P_, tip, 0.25, 'star', 'tail2', face=(0, -1, 0.1), depth=0.09)
    sv.star_light(P_, tip + V((0, -0.25, 0)), 6.0, arm)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.parent is None:
            o.parent = arm
    arm.scale = (SIZE, SIZE, SIZE)
    return dict(root=root, arm=arm, body=body)
