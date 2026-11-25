"""Novalynx (015), Normal. Glimmvix grown into a big night lynx. Its two tails have grown back into
one long tail with a large star at the end. Glowing spots dot its back like stars, its ear tufts
glow gold, and a bigger star sits on its forehead.

The body comes from quad.py: a heavy chest, big shoulders, thick jointed legs and wide paws.
Faces -Y, stands on z = 0, about 2.6 tall to the ear tufts at design scale.
"""
import math

import bpy
import numpy as np
from mathutils import Vector as V

import kit
from kit import srgb as C
import quad
import sv
from sv import El, ell, frame

KEY = 'novalynx'
P_ = 'nvx_'
SIZE = 0.62          # 160 cm tall in the game
SIDE = {'L': -1, 'R': 1}

NIGHT = C('#252c6e')
NIGHT_D = C('#161a46')
INDIGO = C('#3c3f96')
CREAM = C('#fff0d4')
GOLD = C('#f2ad42')
GLOW = C('#ffd36a')
LILAC = C('#a995ff')
INK = C('#11122b')

HEAD = V((0, -0.98, 1.74))
LOOK = {s: V((sx * 0.6, -1, 0.02)).normalized() for s, sx in SIDE.items()}
TAIL = [(0, 0.86, 1.36, 0.11), (0, 1.12, 1.42, 0.17), (0, 1.36, 1.58, 0.2), (0, 1.5, 1.86, 0.2), (0, 1.5, 2.12, 0.16),
        (0, 1.42, 2.3, 0.09)]

SPEC = dict(
    spine=[(-0.64, 1.36, 0.28, 0.33), (-0.38, 1.4, 0.4, 0.45), (-0.06, 1.33, 0.36, 0.38), (0.26, 1.27, 0.31, 0.32),
           (0.56, 1.32, 0.37, 0.37), (0.78, 1.34, 0.3, 0.3)],
    neck=[(-0.56, 1.46, 0.27), (-0.76, 1.6, 0.24), (-0.88, 1.68, 0.23)],
    head=(tuple(HEAD), (0.42, 0.38, 0.36)),
    front=[(0.25, -0.42, 1.3, 0.18), (0.27, -0.32, 0.8, 0.125), (0.27, -0.46, 0.26, 0.1), (0.27, -0.48, 0.1, 0.1)],
    back=[(0.25, 0.56, 1.3, 0.22), (0.28, 0.38, 0.8, 0.14), (0.28, 0.78, 0.4, 0.1), (0.28, 0.7, 0.1, 0.095)],
    paw=(0.135, 0.18, 0.09),
    shoulder=(0.21, 0.3, 0.3),
    tails=[TAIL],
)


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
    top = sv.smoothstep(0.85, 1.05, P[:, 2])[:, None]
    col = np.array(NIGHT) + (bc - np.array(NIGHT)) * top
    sock = sv.smoothstep(0.36, 0.27, P[:, 2])
    col += (np.array(GOLD) - col) * sock[:, None]
    return col, bg * top[:, 0]


def tail_paint(q, P, bc, bg):
    d = np.linalg.norm(P - np.array(TAIL[-1][:3]), axis=1)
    t = sv.smoothstep(0.42, 0.24, d)
    col = np.tile(np.array(NIGHT), (len(q), 1))
    col += (np.array(CREAM) - col) * t[:, None]
    return col, np.zeros(len(q))


def body_paint(P):
    n = len(P)
    ss = sv.smoothstep
    col = np.tile(np.array(NIGHT), (n, 1))
    belly = quad.underside(P, SPEC, frac=0.3, soft=0.14)
    bib = ss(-0.66, -0.86, P[:, 1]) * ss(0.34, 0.2, np.abs(P[:, 0])) * ss(1.7, 1.5, P[:, 2]) * ss(1.0, 1.15, P[:, 2])
    throat = ss(-0.7, -0.86, P[:, 1]) * ss(0.2, 0.1, np.abs(P[:, 0])) * ss(1.4, 1.5, P[:, 2]) * ss(1.7, 1.6, P[:, 2])
    face = ss(-1.04, -1.16, P[:, 1]) * ss(1.74, 1.64, P[:, 2])
    m = np.clip(belly + bib + throat + face, 0, 1)
    col += (np.array(CREAM) - col) * m[:, None]
    # glowing star spots over the back, shoulders and haunches
    glow = np.zeros(n)
    rng = np.random.default_rng(7)
    cand = np.where((P[:, 2] > 1.55) & (P[:, 1] > -0.6) & (P[:, 1] < 0.95))[0]
    rng.shuffle(cand)
    spots = []
    for i in cand:
        p = P[i]
        if all(np.linalg.norm(p - s_) > 0.3 for s_, _ in spots):
            spots.append((p, rng.uniform(0.02, 0.036) * (1.5 if len(spots) % 4 == 0 else 1.0)))
        if len(spots) >= 15:
            break
    for p, r in spots:
        d = np.linalg.norm(P - p, axis=1)
        core = ss(r, r * 0.6, d)
        halo = ss(r * 2.6, r, d) * 0.25
        k = np.maximum(core, halo)
        col += (np.array(GLOW) - col) * k[:, None]
        glow = np.maximum(glow, core + halo * 0.4)
    return col, glow


# ------------------------------------------------------------------ shapes
def elements():
    E = quad.elements(SPEC, leg_paint, tail_paint=tail_paint)
    side = []
    E.append(ell((0, -0.94, 1.96), (0.32, 0.27, 0.17)))
    E.append(El((0, -1.3, 1.64), (0.21, 0.19, 0.15), frame((0, -1, -0.15), (0, 0, 1)), paint=snout_paint, stiff=3.0))
    E.append(ell((0, -1.48, 1.68), (0.065, 0.048, 0.048), paint='solid', color=INK, probe=False))
    f = LOOK['R']
    r = V((0, 0, 1)).cross(f).normalized()
    u = f.cross(r).normalized()
    e = HEAD + f * 0.37
    along = r * math.cos(math.radians(16)) + u * math.sin(math.radians(16))
    side.append(El(e + u * 0.13 + f * 0.04, (0.06, 0.16, 0.045), frame(along, f), paint='solid', color=NIGHT_D, probe=False))
    # ears: shorter than Glimmvix's, with long glowing gold tufts
    root = V((0.22, -0.94, 1.98))
    d = V((0.4, 0.1, 1)).normalized()
    side.append(El(root + d * 0.24, (0.18, 0.26, 0.065), frame(d, (0.1, -1, 0.15)), paint=ear_paint, weights={'ear.R': 1.0}))
    side.append(El(root + d * 0.46, (0.075, 0.12, 0.045), frame(d, (0.1, -1, 0.15)), paint=solid(NIGHT), weights={'ear.R': 1.0}))
    side.append(El(root + d * 0.7, (0.035, 0.16, 0.03), frame(d + V((0.12, 0, 0)), (0, -1, 0)), paint=solid(GOLD, 0.35),
                   weights={'ear.R': 1.0}))
    # full cream cheeks, the lynx's ruff kept smooth
    side.append(El((0.26, -1.08, 1.6), (0.17, 0.15, 0.13), frame((0.5, -0.3, -0.5), (0, -1, 0)), paint='solid', color=CREAM,
                   stiff=2.6))
    return E + sv.mirror(side)


def extra_bones():
    return [('ear.' + s, (sx * 0.22, -0.94, 1.98), (sx * 0.4, -0.9, 2.42), 'head', True) for s, sx in SIDE.items()]


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
    """Confident stance: head low and turned toward the viewer, one front paw stepping forward."""
    pb = arm.pose.bones
    pb['head'].rotation_euler = (0.12, 0, -0.2)
    pb['neck'].rotation_euler = (0.05, 0, -0.08)
    pb['arm.L'].rotation_euler = (-0.25, 0, 0)
    pb['fore.L'].rotation_euler = (0.1, 0, 0)
    pb['hand.L'].rotation_euler = (0.15, 0, 0)
    pb['tail1'].rotation_euler = (0, 0, 0.12)
    pb['tail2'].rotation_euler = (-0.1, 0, 0.18)


def build():
    root = kit.empty('Novalynx')
    B = quad.bones(SPEC, extra_bones())
    arm = kit.make_armature(P_ + 'rig', B, parent=root)
    E = elements()
    body = sv.build_body(P_ + 'body', E, arm, body_paint, quad.seg(B), quad.radii(SPEC),
                         sv.body_material(P_ + 'fur', sheen=0.6, glow=4.0), resolution=0.035, voxel=0.022)
    eyes(arm, E)
    tip = V(TAIL[-1][:3]) + V((0, -0.02, 0.17))
    sv.star(arm, P_, tip, 0.3, 'star', 'tail2', face=(0, -1, 0.1), depth=0.1)
    sv.star_light(P_, tip + V((0, -0.3, 0)), 10.0, arm)
    fh = sv.probe_hit(E, [HEAD + V((0, -1.4, 0.75))], [V((0, 1.0, -0.5))])[0]
    sv.star(arm, P_, fh, 0.12, 'brow_star', 'head', face=(0, -1, 0.5), depth=0.025)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.parent is None:
            o.parent = arm
    arm.scale = (SIZE, SIZE, SIZE)
    return dict(root=root, arm=arm, body=body)
