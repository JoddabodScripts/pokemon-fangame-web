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
import quad
import sv
from sv import El, ell, frame

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
TAIL = [(0, 0.4, 0.6, 0.07), (0, 0.6, 0.64, 0.13), (0, 0.78, 0.82, 0.2), (0, 0.86, 1.06, 0.215), (0, 0.84, 1.28, 0.16),
        (0, 0.8, 1.4, 0.08)]

# chibi proportions: a short round body, a big head, short legs that still bend at the joints
SPEC = dict(
    spine=[(-0.24, 0.62, 0.2, 0.22), (-0.06, 0.6, 0.23, 0.24), (0.14, 0.57, 0.2, 0.21), (0.32, 0.58, 0.21, 0.22)],
    neck=[(-0.2, 0.72, 0.18), (-0.27, 0.84, 0.17), (-0.3, 0.92, 0.17)],
    head=(tuple(HEAD), (0.47, 0.41, 0.41)),
    front=[(0.14, -0.18, 0.56, 0.095), (0.15, -0.13, 0.35, 0.072), (0.15, -0.2, 0.13, 0.062), (0.15, -0.21, 0.065, 0.06)],
    back=[(0.15, 0.3, 0.56, 0.115), (0.16, 0.2, 0.36, 0.082), (0.16, 0.36, 0.17, 0.064), (0.16, 0.32, 0.065, 0.06)],
    paw=(0.088, 0.115, 0.062),
    tails=[TAIL],
)


def extra_bones():
    return [('ear.' + s, (sx * 0.2, -0.28, 1.34), (sx * 0.42, -0.26, 1.78), 'head', True) for s, sx in SIDE.items()]


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
    top = sv.smoothstep(0.42, 0.56, P[:, 2])[:, None]
    col = np.array(GOLD) + (bc - np.array(GOLD)) * top
    sock = sv.smoothstep(0.21, 0.16, P[:, 2])
    col += (np.array(NAVY) - col) * sock[:, None]
    return col, np.zeros(len(q))


def tail_paint(q, P, bc, bg):
    """Gold tail that fades to a cream puff at the end, just under the star."""
    t = sv.smoothstep(0.34, 0.2, np.linalg.norm(P - np.array(TAIL[-1][:3]), axis=1))
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
    bib = ss(-0.2, -0.32, P[:, 1]) * ss(0.92, 0.82, P[:, 2]) * ss(0.24, 0.14, np.abs(P[:, 0]))
    belly = quad.underside(P, SPEC, frac=0.4)
    m = np.clip(face + side + bib + belly, 0, 1)
    col += (np.array(CREAM) - col) * m[:, None]
    # a slightly deeper gold stripe down the back
    return col, np.zeros(n)


# ------------------------------------------------------------------ shapes
def elements():
    E = quad.elements(SPEC, leg_paint, tail_paint=tail_paint)
    # skull top, short muzzle and a button nose on the big round head
    E.append(ell((0, -0.3, 1.3), (0.3, 0.26, 0.17)))
    E.append(ell((0, -0.66, 0.96), (0.18, 0.17, 0.13), (-0.15, 0, 0), paint=muzzle_paint))
    E.append(ell((0, -0.825, 1.0), (0.055, 0.04, 0.04), paint='solid', color=NAVY, probe=False))
    side = []
    root = V((0.2, -0.28, 1.34))
    d = V((0.5, 0.06, 1)).normalized()
    side.append(El(root + d * 0.26, (0.18, 0.28, 0.065), frame(d, (0.1, -1, 0.15)), paint=ear_paint, weights={'ear.R': 1.0}))
    side.append(El(root + d * 0.5, (0.08, 0.12, 0.045), frame(d, (0.1, -1, 0.15)), paint=ear_tip_paint, weights={'ear.R': 1.0}))
    # cheek fluff lying back along the jaw
    for rt, dd, L in (((0.38, -0.36, 0.98), (0.6, 0.5, -0.55), 0.13), ((0.34, -0.3, 0.88), (0.45, 0.5, -0.75), 0.1)):
        dv = V(dd).normalized()
        side.append(El(V(rt) + dv * L * 0.45, (0.075, L, 0.05), frame(dv, (0.5, -0.8, 0.2)), paint='solid', color=CREAM))
    return E + sv.mirror(side)


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
    """Curious head tilt, tail swishing to one side."""
    pb['head'].rotation_euler = (0.05, 0.2, -0.16)
    pb['tail1'].rotation_euler = (0, 0, 0.15)
    pb['tail2'].rotation_euler = (-0.1, 0, 0.22)


def build():
    root = kit.empty('Twinkit')
    B = quad.bones(SPEC, extra_bones())
    arm = kit.make_armature(P_ + 'rig', B, parent=root)
    E = elements()
    body = sv.build_body(P_ + 'body', E, arm, body_paint, quad.seg(B), quad.radii(SPEC), sv.body_material(P_ + 'fur'))
    eyes(arm, E)
    tip = V(TAIL[-1][:3]) + V((0, -0.02, 0.12))
    sv.star(arm, P_, tip, 0.25, 'star', 'tail2', face=(0, -1, 0.1), depth=0.09)
    sv.star_light(P_, tip + V((0, -0.25, 0)), 6.0, arm)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.parent is None:
            o.parent = arm
    arm.scale = (SIZE, SIZE, SIZE)
    return dict(root=root, arm=arm, body=body)
