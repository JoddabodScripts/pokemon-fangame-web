"""Glimmvix (014), Normal. Twinkit grown into a lean dusk fox: the coat turns night blue, the tail
splits in two, and both tips carry a glowing star. A small star shows on its forehead.

The body comes from quad.py (spine, shoulders, thighs, jointed legs). Faces -Y, stands on z = 0,
about 2.2 tall to the ear tips at design scale.
"""
import bpy
import numpy as np
from mathutils import Vector as V

import kit
from kit import srgb as C
import quad
import sv
from sv import El, ell, frame

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

HEAD = V((0, -0.7, 1.58))
LOOK = {s: V((sx * 0.62, -1, 0.04)).normalized() for s, sx in SIDE.items()}
TAIL = {s: [(sx * 0.0, 0.66, 1.02, 0.075), (sx * 0.06, 0.86, 1.1, 0.12), (sx * 0.2, 1.06, 1.3, 0.16),
            (sx * 0.32, 1.16, 1.58, 0.16), (sx * 0.36, 1.12, 1.84, 0.12), (sx * 0.36, 1.06, 1.96, 0.07)]
        for s, sx in SIDE.items()}

SPEC = dict(
    spine=[(-0.52, 1.03, 0.2, 0.24), (-0.32, 1.04, 0.26, 0.31), (-0.08, 0.99, 0.23, 0.27), (0.18, 0.95, 0.19, 0.22),
           (0.42, 0.99, 0.24, 0.26), (0.62, 1.01, 0.2, 0.21)],
    neck=[(-0.44, 1.12, 0.17), (-0.56, 1.32, 0.15), (-0.64, 1.47, 0.15)],
    head=(tuple(HEAD), (0.33, 0.31, 0.29)),
    front=[(0.17, -0.34, 0.98, 0.12), (0.18, -0.26, 0.62, 0.08), (0.18, -0.36, 0.2, 0.062), (0.18, -0.38, 0.08, 0.06)],
    back=[(0.17, 0.44, 0.96, 0.15), (0.19, 0.3, 0.6, 0.095), (0.19, 0.62, 0.3, 0.065), (0.19, 0.56, 0.08, 0.06)],
    paw=(0.085, 0.12, 0.06),
    tails=[TAIL['L'], TAIL['R']],
)


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
    # continue the body paint at the top of the leg so the belly color doesn't break into patches
    top = sv.smoothstep(0.62, 0.8, P[:, 2])[:, None]
    col = np.array(NIGHT) + (bc - np.array(NIGHT)) * top
    sock = sv.smoothstep(0.3, 0.22, P[:, 2])
    col += (np.array(GOLD) - col) * sock[:, None]
    return col, np.zeros(len(q))


def tail_paint(q, P, bc, bg):
    tips = np.array([TAIL[s][-1][:3] for s in SIDE])
    d = np.min(np.linalg.norm(P[:, None, :] - tips[None], axis=2), axis=1)
    t = sv.smoothstep(0.36, 0.22, d)
    col = np.tile(np.array(NIGHT), (len(q), 1))
    col += (np.array(CREAM) - col) * t[:, None]
    return col, np.zeros(len(q))


def body_paint(P):
    n = len(P)
    ss = sv.smoothstep
    col = np.tile(np.array(NIGHT), (n, 1))
    belly = quad.underside(P, SPEC, frac=0.3, soft=0.14)
    bib = ss(-0.5, -0.66, P[:, 1]) * ss(0.26, 0.14, np.abs(P[:, 0])) * ss(1.45, 1.3, P[:, 2]) * ss(0.78, 0.9, P[:, 2])
    throat = ss(-0.58, -0.72, P[:, 1]) * ss(0.13, 0.05, np.abs(P[:, 0])) * ss(1.1, 1.25, P[:, 2]) * ss(1.55, 1.45, P[:, 2])
    face = ss(-0.74, -0.84, P[:, 1]) * ss(1.56, 1.48, P[:, 2])
    cheek = ss(0.16, 0.24, np.abs(P[:, 0])) * ss(-0.56, -0.68, P[:, 1]) * ss(1.58, 1.48, P[:, 2]) * ss(1.36, 1.42, P[:, 2])
    m = np.clip(belly + bib + throat + face + cheek, 0, 1)
    col += (np.array(CREAM) - col) * m[:, None]
    return col, np.zeros(n)


# ------------------------------------------------------------------ shapes
def elements():
    E = quad.elements(SPEC, leg_paint, tail_paint=tail_paint)
    side = []
    # skull top and fox snout
    E.append(ell((0, -0.66, 1.76), (0.24, 0.22, 0.14)))
    E.append(El((0, -0.98, 1.5), (0.135, 0.22, 0.11), frame((0, -1, -0.28), (0, 0, 1)), paint=snout_paint, stiff=3.0))
    E.append(ell((0, -1.17, 1.54), (0.05, 0.04, 0.04), paint='solid', color=INK, probe=False))
    root = V((0.17, -0.66, 1.8))
    d = V((0.42, 0.08, 1)).normalized()
    side.append(El(root + d * 0.24, (0.16, 0.27, 0.058), frame(d, (0.1, -1, 0.15)), paint=ear_paint, weights={'ear.R': 1.0}))
    side.append(El(root + d * 0.47, (0.065, 0.12, 0.04), frame(d, (0.1, -1, 0.15)), paint=solid(GOLD), weights={'ear.R': 1.0}))
    # cheek fur lying back along the jaw
    for rt, dd, L in (((0.24, -0.72, 1.5), (0.45, 0.75, -0.35), 0.17), ((0.21, -0.66, 1.42), (0.35, 0.75, -0.6), 0.14)):
        dv = V(dd).normalized()
        side.append(El(V(rt) + dv * L * 0.45, (0.07, L, 0.045), frame(dv, (0.6, -0.5, 0.3)), paint='solid', color=CREAM))
    return E + sv.mirror(side)


def extra_bones():
    return [('ear.' + s, (sx * 0.17, -0.66, 1.8), (sx * 0.35, -0.62, 2.22), 'head', True) for s, sx in SIDE.items()]


def eyes(arm, E):
    hits = sv.probe_hit(E, [HEAD + LOOK[s] * 1.4 for s in SIDE], [-LOOK[s] for s in SIDE])
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
    """Alert stance: head turned toward the viewer, right front paw lifted, tails swaying."""
    pb = arm.pose.bones
    pb['head'].rotation_euler = (0.1, 0, -0.22)
    pb['neck'].rotation_euler = (-0.08, 0, -0.06)
    pb['arm.R'].rotation_euler = (0.35, 0, 0)
    pb['fore.R'].rotation_euler = (-0.9, 0, 0)
    pb['hand.R'].rotation_euler = (0.5, 0, 0)
    for s, sx in SIDE.items():
        pb['tail1.' + s].rotation_euler = (0, 0, sx * 0.1)


def build():
    root = kit.empty('Glimmvix')
    B = quad.bones(SPEC, extra_bones())
    arm = kit.make_armature(P_ + 'rig', B, parent=root)
    E = elements()
    body = sv.build_body(P_ + 'body', E, arm, body_paint, quad.seg(B), quad.radii(SPEC), sv.body_material(P_ + 'fur', sheen=0.6))
    eyes(arm, E)
    for s, sx in SIDE.items():
        tip = V(TAIL[s][-1][:3]) + V((0, -0.02, 0.12))
        sv.star(arm, P_, tip, 0.2, 'star.' + s, 'tail2.' + s, face=(sx * 0.3, -1, 0.1), depth=0.075, spin=-sx * 0.25)
        sv.star_light(P_, tip + V((0, -0.2, 0)), 4.0, arm, 'starlight.' + s)
    fh = sv.probe_hit(E, [HEAD + V((0, -1.2, 0.6))], [V((0, 1.0, -0.45))])[0]
    sv.star(arm, P_, fh, 0.075, 'brow_star', 'head', face=(0, -1, 0.55), depth=0.02)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.parent is None:
            o.parent = arm
    arm.scale = (SIZE, SIZE, SIZE)
    return dict(root=root, arm=arm, body=body)
