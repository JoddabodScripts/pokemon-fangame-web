"""A four-legged body for the SV-style models: spine, neck, legs and tail from a short spec.

The spine runs through a deep chest, a narrower waist and rounded hips. Shoulders and thighs are big
masses that grow out of the body. Front legs bend at the elbow and wrist, back legs at the knee
(forward) and hock (backward). Everything is built from sv.chain, so each form tapers evenly and
melts into the next. Bones come from the same points, so the skin follows the anatomy.

Coordinates: faces -Y, z up, stands on z = 0. x values in the spec are for the right side (+x);
the left side is mirrored.
"""
import numpy as np
from mathutils import Vector as V

import sv
from sv import El, ell, frame


def _pt(p):
    return V(p[:3])


def elements(spec, leg_paint, body_paint='body', tail_paint='body'):
    """Spec keys: spine [(y, z, rx, rz)] front to back, neck [(y, z, r)] chest to head, head (center, size),
    front [(x, y, z, r)] shoulder, elbow, wrist, paw; back [(x, y, z, r)] hip, knee, hock, paw;
    paw (rx, ry, rz); tails: list of [(x, y, z, r)] each. Optional: shoulder (size), thigh (size)."""
    E = []
    E += sv.chain([(0, y, z, rx, rz) for y, z, rx, rz in spec['spine']], normal=(0, 0, 1), paint=body_paint)
    E += sv.chain([(0, y, z, r, r) for y, z, r in spec['neck']], normal=(0, -1, 0.3), paint=body_paint)
    c, sz = spec['head']
    E.append(El(V(c), sz, stiff=2.6, paint=body_paint))
    side = []
    f = spec['front']
    # shoulder blade mass: sits on the chest, long axis down the upper arm
    sh = spec.get('shoulder', (f[0][3] * 1.1, f[0][3] * 1.5, f[0][3] * 1.35))
    d = _pt(f[1]) - _pt(f[0])
    side.append(El(_pt(f[0]) + V((-0.15 * sh[0], 0, 0.05 * sh[2])), sh, frame(d, (1, 0, 0)), stiff=2.4, paint=body_paint))
    side += sv.chain([(x, y, z, r, r) for x, y, z, r in f], normal=(1, 0, 0), paint=leg_paint)
    pw = spec['paw']
    side.append(El(_pt(f[-1]) + V((0, -pw[1] * 0.35, pw[2] - f[-1][2])), pw, stiff=3.0, paint=leg_paint, weights={'hand.R': 1.0}))
    b = spec['back']
    th = spec.get('thigh', (b[0][3] * 0.95, b[0][3] * 1.45, b[0][3] * 1.6))
    k = _pt(b[1]) - _pt(b[0])
    side.append(El(_pt(b[0]) * 0.5 + _pt(b[1]) * 0.5 + V((0, 0.03, 0.04)), th, frame(k, (1, 0, 0)), stiff=2.4, paint=body_paint))
    side += sv.chain([(x, y, z, r, r) for x, y, z, r in b], normal=(1, 0, 0), paint=leg_paint)
    side.append(El(_pt(b[-1]) + V((0, -pw[1] * 0.35, pw[2] - b[-1][2])), pw, stiff=3.0, paint=leg_paint, weights={'foot.R': 1.0}))
    E += sv.mirror(side)
    for tl in spec['tails']:
        E += sv.chain([(x, y, z, r, r * 0.88) for x, y, z, r in tl], normal=(1, 0, 0), paint=tail_paint)
    return E


def bones(spec, extra=()):
    sp = spec['spine']
    chest = V((0, sp[0][0] * 0.6, sp[0][1]))
    mid = V((0, (sp[0][0] + sp[-1][0]) * 0.45, (sp[0][1] + sp[-1][1]) / 2))
    rear = V((0, sp[-1][0], sp[-1][1]))
    nk = spec['neck']
    n0, n1 = V((0, nk[0][0], nk[0][1])), V((0, nk[-1][0], nk[-1][1]))
    hc = V(spec['head'][0])
    B = [('root', (0, 0, 0), (0, 0, 0.3), None, False),
         ('hips', rear, mid, 'root', True),
         ('chest', mid, chest, 'hips', True),
         ('neck', n0, n1, 'chest', True),
         ('head', n1, hc + V((0, -0.05, spec['head'][1][2])), 'neck', True)]
    for s, sx in (('L', -1), ('R', 1)):
        f = [V((p[0] * sx, p[1], p[2])) for p in spec['front']]
        b = [V((p[0] * sx, p[1], p[2])) for p in spec['back']]
        pawf = f[3] + V((0, -spec['paw'][1], 0))
        pawb = b[3] + V((0, -spec['paw'][1], 0))
        B += [('arm.' + s, f[0], f[1], 'chest', True), ('fore.' + s, f[1], f[2], 'arm.' + s, True),
              ('hand.' + s, f[2], pawf, 'fore.' + s, True),
              ('thigh.' + s, b[0], b[1], 'hips', True), ('shin.' + s, b[1], b[2], 'thigh.' + s, True),
              ('foot.' + s, b[2], pawb, 'shin.' + s, True)]
    for ti, tl in enumerate(spec['tails']):
        sfx = '' if len(spec['tails']) == 1 else ('.L' if tl[-1][0] < 0 else '.R')
        P = [V(p[:3]) for p in tl]
        n = len(P)
        cuts = [0, n // 3, (2 * n) // 3, n - 1]
        par = 'hips'
        for j in range(3):
            nm = f'tail{j}{sfx}'
            B.append((nm, P[cuts[j]], P[cuts[j + 1]], par, True))
            par = nm
    B += list(extra)
    return B


def seg(B):
    return {n: (V(h), V(t)) for n, h, t, p, d in B if d}


def radii(spec, scale=1.0):
    sp = spec['spine']
    body = max(max(rx, rz) for _, _, rx, rz in sp)
    r = dict(hips=body * 1.25, chest=body * 1.25, neck=spec['neck'][0][2] * 1.3, head=max(spec['head'][1]) * 1.25)
    fr = spec['front'][0][3]
    br = spec['back'][0][3]
    for s in 'LR':
        r.update({'arm.' + s: fr * 1.3, 'fore.' + s: fr * 0.9, 'hand.' + s: fr * 0.9, 'thigh.' + s: br * 1.5,
                  'shin.' + s: br * 0.8, 'foot.' + s: br * 0.8, 'ear.' + s: 0.25})
    for tl in spec['tails']:
        sfx = '' if len(spec['tails']) == 1 else ('.L' if tl[-1][0] < 0 else '.R')
        rt = max(p[3] for p in tl)
        for j in range(3):
            r[f'tail{j}{sfx}'] = rt * 1.3
    return {k: v * scale for k, v in r.items()}


def underside(P, spec, frac=0.3, soft=0.18):
    """0..1 mask of the belly: below the spine's center line by more than frac of its height."""
    sp = spec['spine']
    ys = np.array([p[0] for p in sp])
    o = np.argsort(ys)
    zc = np.interp(P[:, 1], ys[o], np.array([p[1] for p in sp])[o])
    rz = np.interp(P[:, 1], ys[o], np.array([p[3] for p in sp])[o])
    rx = np.interp(P[:, 1], ys[o], np.array([p[2] for p in sp])[o])
    v = (P[:, 2] - zc) / rz
    inside = (P[:, 1] > ys.min() - 0.05) & (P[:, 1] < ys.max() + 0.1)
    # only the belly itself, not the outside of the shoulders and thighs that hang just as low
    mid = sv.smoothstep(0.85, 0.6, np.abs(P[:, 0]) / rx)
    return sv.smoothstep(-frac + soft, -frac - soft, v) * inside * mid
