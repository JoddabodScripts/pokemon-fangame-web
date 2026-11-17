"""Shared building blocks for per-Pokemon animate(A) functions.

Timing helpers (E, win, spring) shape motion; the fx helpers build keyed effect meshes.
All fx objects are hidden (scale 0.001) outside their own frames.
"""
import math
from mathutils import Vector


def E(f, a, b):
    """Eased 0 -> 1 between frames a and b."""
    t = max(0.0, min(1.0, (f - a) / float(b - a)))
    return t * t * (3 - 2 * t)


def win(f, a, b, c, d):
    """0 before a, eases up to 1 by b, holds, eases back to 0 between c and d."""
    return E(f, a, b) * (1 - E(f, c, d))


def spring(t, k=5.0, w=9.0):
    """Overshoot-and-settle curve from 0 to 1 (t in 'seconds-ish'; 0 before start)."""
    return 0.0 if t <= 0 else 1 - math.exp(-k * t) * math.cos(w * t)


def decay(f, f0, rate=6.0, freq=0.9):
    """A wobble that starts at f0 and dies away (for hits and landings)."""
    return math.exp(-(f - f0) / rate) * math.cos((f - f0) * freq) if f >= f0 else 0.0


def blink_scale(f, frames, closed=0.9):
    """Eye Z scale for blinks at the given frames (each blink lasts 4 frames)."""
    b = max([win(f, x, x + 1, x + 2, x + 4) for x in frames] + [0])
    return 1 - closed * b


def _hide(A, o, f0, f1):
    A.key(o, 0, scale=0.001, absolute=True)
    A.key(o, max(0, f0 - 1), scale=0.001, absolute=True)
    A.key(o, f1 + 1, scale=0.001, absolute=True)


def burst(A, name, center, f0, n=12, dur=14, speed=1.0, up=0.6, gravity=1.6, size=0.05,
          mat=None, shape='sphere', seed=0, spread=(1, 1, 1)):
    """Particles thrown out from `center` at f0, arcing under gravity and shrinking away."""
    lib, s = A.lib, A.size
    out = []
    for i in range(n):
        a = (i * 2.399 + seed) % (2 * math.pi)
        e = 0.3 + 0.7 * ((i * 0.618 + seed * 0.3) % 1.0)
        v = Vector((math.cos(a) * e * spread[0], math.sin(a) * e * spread[1], up * (0.6 + 0.8 * ((i * 0.37) % 1.0)) * spread[2])) * speed * s
        p = lib.pivot(f'{name}{i}')
        r = size * s * (0.7 + 0.6 * ((i * 0.43) % 1.0))
        if shape == 'shard':
            lib.cone(f'{name}m{i}', (0, 0, 0), r * 0.6, 0.0, r * 3.2, mat, p, rot=(0.4 * i, 0.7 * i, 0), seg=5)
        elif shape == 'leaf':
            lib.sphere(f'{name}m{i}', (0, 0, 0), (r * 1.6, r * 0.4, r * 0.8), mat, p, seg=10)
        elif shape == 'flake':
            for k in range(3):
                lib.box(f'{name}m{i}_{k}', (0, 0, 0), (r * 2.2, r * 0.3, r * 0.3), mat, p, rot=(0, k * math.pi / 3, 0))
        else:
            lib.sphere(f'{name}m{i}', (0, 0, 0), r, mat, p, seg=10)
        _hide(A, p, f0, f0 + dur)
        for k in range(0, dur + 1, 2):
            t = k / dur * (dur / 24.0)
            pos = Vector(center) + v * t + Vector((0, 0, -gravity * s * t * t))
            pos.z = max(pos.z, 0.01)
            sc = 1.0 if k < dur * 0.6 else max(0.001, 1 - (k - dur * 0.6) / (dur * 0.4))
            A.key(p, f0 + k, loc=pos, rot=(k * 0.3 + i, k * 0.2, k * 0.25), scale=sc, absolute=True)
        out.append(p)
    return out


def ring(A, name, center, f0, dur=10, r0=0.1, r1=1.2, thick=0.04, mat=None, tilt=(0, 0, 0)):
    """An expanding torus (shockwave / ripple) flat on the ground by default."""
    lib, s = A.lib, A.size
    p = lib.pivot(name)
    lib.torus(name + 'm', (0, 0, 0), 1.0, thick, mat, p)
    _hide(A, p, f0, f0 + dur)
    for k in range(0, dur + 1):
        r = (r0 + (r1 - r0) * A.ease(k / dur)) * s
        sc = r if k < dur else 0.001
        A.key(p, f0 + k, loc=Vector(center), rot=tilt, scale=(sc, sc, sc * (1 - 0.7 * k / dur) + 0.001), absolute=True)
    return p


def projectile(A, name, start, end, f0, flight=10, mat=None, radius=0.06, shape='sphere', arc=0.0, spin=0.0, trail=0):
    """One projectile from start to end over `flight` frames; optional arc height and fading trail copies."""
    lib, s = A.lib, A.size
    start, end = Vector(start), Vector(end)
    objs = []
    for t_i in range(trail + 1):
        p = lib.pivot(f'{name}t{t_i}')
        r = radius * s * (1 - 0.25 * t_i)
        if shape == 'shard':
            d = (end - start).normalized()
            q = Vector((0, 0, 1)).rotation_difference(d).to_euler()
            lib.cone(f'{name}m{t_i}', (0, 0, 0), r * 0.7, 0.0, r * 4, mat, p, rot=q, seg=6)
        elif shape == 'leaf':
            lib.sphere(f'{name}m{t_i}', (0, 0, 0), (r * 1.6, r * 0.4, r * 0.8), mat, p, seg=10)
        else:
            lib.sphere(f'{name}m{t_i}', (0, 0, 0), r, mat, p, seg=12)
        lag = t_i * 1
        _hide(A, p, f0 + lag, f0 + flight + lag)
        for k in range(0, flight + 1):
            t = k / flight
            pos = start.lerp(end, t) + Vector((0, 0, arc * s * 4 * t * (1 - t)))
            A.key(p, f0 + lag + k, loc=pos, rot=(0, 0, spin * k), scale=1.0 - 0.2 * t_i, absolute=True)
        objs.append(p)
    return objs


def swirl(A, name, center, f0, dur=24, n=16, radius=0.8, height=1.6, turns=1.5, mat=None, size=0.04,
          shape='sphere', inward=True, seed=0):
    """Particles spiralling around a vertical axis (snow flurry, ember tornado, leaf whirl)."""
    lib, s = A.lib, A.size
    out = []
    for i in range(n):
        p = lib.pivot(f'{name}{i}')
        r = size * s * (0.7 + 0.6 * ((i * 0.43 + seed) % 1.0))
        if shape == 'flake':
            for k in range(3):
                lib.box(f'{name}m{i}_{k}', (0, 0, 0), (r * 2.2, r * 0.3, r * 0.3), mat, p, rot=(0, k * math.pi / 3, 0))
        elif shape == 'leaf':
            lib.sphere(f'{name}m{i}', (0, 0, 0), (r * 1.6, r * 0.4, r * 0.8), mat, p, seg=10)
        else:
            lib.sphere(f'{name}m{i}', (0, 0, 0), r, mat, p, seg=10)
        a0 = i * 2 * math.pi / n + seed
        z0 = (i % 5) / 5.0 * height
        start = f0 + (i % 4)
        _hide(A, p, start, f0 + dur)
        for k in range(0, dur - (i % 4) + 1, 2):
            t = k / dur
            rr = radius * (1 - 0.7 * t if inward else 0.4 + 0.8 * t)
            a = a0 + turns * 2 * math.pi * t
            pos = Vector(center) + Vector((math.cos(a) * rr, math.sin(a) * rr, (z0 + height * 0.5 * t) % height)) * s
            sc = 1.0 if t < 0.8 else max(0.001, (1 - t) / 0.2)
            A.key(p, start + k, loc=pos, rot=(k * 0.4, k * 0.3, a), scale=sc, absolute=True)
        out.append(p)
    return out


def flash_sphere(A, name, center, f0, dur=8, r1=0.4, mat=None):
    """A glowing sphere that pops up and fades (impact flash, charge glow)."""
    lib, s = A.lib, A.size
    p = lib.pivot(name)
    lib.sphere(name + 'm', (0, 0, 0), 1.0, mat, p, seg=20)
    _hide(A, p, f0, f0 + dur)
    for k, sc in [(0, 0.1), (max(1, dur // 3), 1.0), (dur, 0.001)]:
        A.key(p, f0 + k, loc=Vector(center), scale=sc * r1 * s if sc > 0.001 else 0.001, absolute=True)
    return p


def spikes(A, name, center, f0, n=7, dur=18, height=0.6, mat=None, radius=0.35, seed=0):
    """Crystals or thorns that erupt from the ground in a cluster, then shatter away."""
    lib, s = A.lib, A.size
    out = []
    for i in range(n):
        a = i * 2.399 + seed
        rr = radius * s * (0.2 + 0.8 * ((i * 0.618) % 1.0))
        p = lib.pivot(f'{name}{i}')
        h = height * s * (0.6 + 0.6 * ((i * 0.37) % 1.0))
        tilt = (math.sin(a) * 0.4, math.cos(a) * 0.4, 0)
        lib.cone(f'{name}m{i}', (0, 0, h / 2), 0.09 * s * h / (height * s), 0.0, h, mat, p, seg=6)
        _hide(A, p, f0, f0 + dur)
        base = Vector(center) + Vector((math.cos(a) * rr, math.sin(a) * rr, 0))
        base.z = 0
        for k, sc in [(0, 0.05), (2 + i % 3, 1.15), (5 + i % 3, 1.0), (dur - 4, 1.0), (dur, 0.001)]:
            A.key(p, f0 + k, loc=base, rot=tilt, scale=sc, absolute=True)
        out.append(p)
    return out
