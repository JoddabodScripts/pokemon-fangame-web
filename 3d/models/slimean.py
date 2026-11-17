"""Slimean: round glossy water slime with a ring inside, puddle and drips."""
import math
from mathutils import Vector


def _basis(d):
    d = Vector(d).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((0, 1, 0))
    u = up.cross(d).normalized()
    v = d.cross(u).normalized()
    return d, u, v


def on(c, r, d, k=1.0):
    """Point on the ellipsoid (center c, radii r) in unit direction d, pushed out by factor k."""
    d = Vector(d).normalized()
    return (c[0] + r[0] * d.x * k, c[1] + r[1] * d.y * k, c[2] + r[2] * d.z * k)


def patch(lib, name, c, r, d, au, av, m, parent, k=1.008, rings=6, seg=32):
    """A marking that hugs an ellipsoid: disc around direction d, angular radii au (sideways), av (up)."""
    d, u, v = _basis(d)
    verts, faces = [on(c, r, d, k)], []
    for i in range(1, rings + 1):
        rho = i / rings
        kk = k if i < rings else 0.985
        for j in range(seg):
            phi = 2 * math.pi * j / seg
            ang = rho * au * av / math.hypot(av * math.cos(phi), au * math.sin(phi))
            s = d * math.cos(ang) + (u * math.cos(phi) + v * math.sin(phi)) * math.sin(ang)
            verts.append(on(c, r, s, kk))
    for j in range(seg):
        faces.append((0, 1 + j, 1 + (j + 1) % seg))
    for i in range(1, rings):
        a, b = 1 + (i - 1) * seg, 1 + i * seg
        for j in range(seg):
            faces.append((a + j, b + j, b + (j + 1) % seg, a + (j + 1) % seg))
    return lib.from_verts(name, verts, faces, m, parent, subsurf=0)


def build(lib):
    rig = lib.Rig('Slimean', 'slimean', 'Water', height_cm=40, gait='hop', attack='slam')
    slime = lib.mat('sli_slime', '#2f74d8', 0.12, sss=0.2, coat=1.0)
    ring1 = lib.mat('sli_ring1', '#1a4aa0', 0.2, sss=0.1, coat=1.0)
    ring2 = lib.mat('sli_ring2', '#62a4f0', 0.15, sss=0.15, coat=1.0)
    ring3 = lib.mat('sli_ring3', '#a4d0ff', 0.15, sss=0.15, coat=1.0)
    gloss = lib.mat('sli_gloss', '#e8f4ff', 0.1, emit=0.6, coat=1.0)
    bub = lib.mat('sli_bubble', '#b8d8ff', 0.1, emit=0.25, coat=1.0)
    dark = lib.mat('sli_dark', '#0e1a3a', 0.3)
    pink = lib.mat('sli_cheek', '#ff9ac0', 0.5, sss=0.3)
    puddle = lib.mat('sli_puddle', '#2f6fc4', 0.05, sss=0.15, coat=1.0)

    # puddle stays on the ground (on the root) while the body hops
    puddles = [
        lib.sphere('sli_puddle', (0, 0, 0.012), (0.78, 0.66, 0.03), puddle, rig.root),
        lib.sphere('sli_puddle2', (-0.52, -0.22, 0.01), (0.3, 0.24, 0.025), puddle, rig.root),
        lib.sphere('sli_puddle3', (0.5, 0.3, 0.01), (0.34, 0.26, 0.025), puddle, rig.root),
        lib.sphere('sli_puddle4', (0.62, -0.42, 0.008), (0.1, 0.09, 0.02), puddle, rig.root)]

    # body pivot sits on the ground (squash and stretch against the floor); the spin pivot is at
    # the center of the ball so it can roll and flip
    rig.body = lib.pivot('sli_bodyp', (0, 0, 0), rig.root)
    spin = lib.pivot('sli_spin', (0, 0, 0.47), rig.body)
    C, R = (0, 0, 0), (0.64, 0.6, 0.5)
    lib.sphere('sli_body', C, R, slime, spin, seg=48)

    # concentric ring seen inside it
    fd = (0, -1, -0.08)
    patch(lib, 'sli_ringA', C, R, fd, 0.80, 0.76, ring1, spin, k=1.004)
    patch(lib, 'sli_ringB', C, R, fd, 0.64, 0.60, ring2, spin, k=1.008)
    patch(lib, 'sli_ringC', C, R, (-0.06, -1, -0.02), 0.42, 0.38, ring3, spin, k=1.012)

    # gloss streak and bubbles
    patch(lib, 'sli_gloss', C, R, (-0.62, -0.62, 0.52), 0.07, 0.2, gloss, spin, k=1.014, rings=3, seg=16)
    patch(lib, 'sli_gloss2', C, R, (-0.5, -0.6, 0.72), 0.06, 0.06, gloss, spin, k=1.014, rings=3, seg=16)
    for i, (d, s) in enumerate([((-0.42, -0.75, -0.62), 0.045), ((0.5, -0.75, -0.42), 0.03), ((0.38, -0.7, -0.68), 0.025),
                                ((0.7, 0.3, 0.5), 0.04), ((-0.5, 0.7, 0.3), 0.03)]):
        lib.sphere(f'sli_bub{i}', on(C, R, d, 0.99), s, bub, spin, seg=12)

    # face
    eyes = []
    for sx, nm in ((-1, 'L'), (1, 'R')):
        e = lib.eye('sli_eye' + nm, on(C, R, (sx * 0.27, -1, 0.14), 0.99), 0.11, spin,
                    iris='#1c3470', pupil='#0e1a3a', sclera='#0e1a3a', look=(sx * 0.2, -1, 0.1), iris_frac=0.7)
        e.scale = (0.85, 1, 1.3)
        eyes.append(e)
        patch(lib, 'sli_cheek' + nm, C, R, (sx * 0.6, -1, -0.14), 0.12, 0.075, pink, spin, k=1.014, rings=3, seg=16)
    pts = [on(C, R, (x, -1, z), 1.012) for x, z in [(-0.17, -0.19), (-0.09, -0.25), (0, -0.27), (0.09, -0.25), (0.17, -0.19)]]
    lib.tube('sli_mouth', pts, [0.012, 0.018, 0.018, 0.018, 0.012], dark, spin, seg=8)

    # drips sliding down its sides: teardrops that hug the surface
    for i, (d, r) in enumerate([((-0.93, -0.36, -0.42), 0.085), ((0.86, -0.5, -0.52), 0.06), ((0.55, 0.83, -0.4), 0.07)]):
        base = Vector(on(C, R, d, 0.97))
        top = Vector(on(C, R, (d[0], d[1], d[2] + 0.55), 0.97))
        lib.sphere(f'sli_drip{i}', base, (r, r, r * 1.15), slime, spin, seg=16)
        lib.tube(f'sli_dript{i}', [base, base.lerp(top, 0.5), top], [r * 0.85, r * 0.5, r * 0.15], slime, spin)

    rig.sli = dict(spin=spin, eyes=eyes, puddles=puddles)
    rig.attack_origin = (0, -0.65, 0.5)
    return rig


# ---------------------------------------------------------------- animation
def animate(A):
    """Slimean: splats out as a puddle and pulls itself into a ball, bounces along with big squash
    and stretch, then Slime Slam: a tumbling leap that pancakes onto the opponent."""
    r, T, s, lib = A.rig, A.T, A.size, A.lib
    root, body, spin = r.root, r.body, r.sli['spin']
    eyes, puddles = r.sli['eyes'], r.sli['puddles']
    slime = lib.mat('sli_slime', '#2f74d8')
    TAU = 2 * math.pi

    def vol(z):                      # volume-preserving squash
        w = 1 / math.sqrt(z)
        return (w, w, z)

    def B(f, scale, loc=(0, 0, 0), rot=(0, 0, 0)):
        A.key(body, f, loc=loc, rot=rot, scale=scale)

    def blink(f, v):
        for e in eyes:
            A.key(e, f, scale=(1, 1, v))

    def pud(f, v):
        for p in puddles:
            A.key(p, f, scale=(v, v, 1))

    def blob(name, rad, m=slime):
        p = lib.pivot(name)
        lib.sphere(name + '_m', (0, 0, 0), rad, m, p, seg=12)
        A.key(p, 0, loc=(0, 0, -5), scale=0.001, absolute=True)
        return p

    def fling(p, f0, f1, a, b, up, size=1.0):
        """Ballistic droplet from a to b between f0 and f1, arcing `up`."""
        a, b = Vector(a), Vector(b)
        A.key(p, f0 - 1, loc=a, scale=0.001, absolute=True)
        for f in A.frames(f0, f1):
            t = (f - f0) / (f1 - f0)
            pos = a.lerp(b, t) + Vector((0, 0, up * 4 * t * (1 - t)))
            A.key(p, f, loc=pos, scale=size * (1 - 0.5 * t), absolute=True)
        A.key(p, f1 + 1, loc=b, scale=0.001, absolute=True)

    # ---- send-out: a glob drops out of the ball, splats flat, then pulls itself up
    A.key(root, 0, scale=0.001); A.key(root, 15, scale=0.001); A.key(root, 16, scale=1)
    A.key(root, 0, loc=(0, 0, 0), rot=(0, 0, 0)); A.key(root, T['WALK'], loc=(0, 0, 0), rot=(0, 0, 0))
    A.key(spin, 0, rot=(0, 0, 0))
    pud(0, 0.001); pud(21, 0.001); pud(24, 1.35); pud(29, 0.92); pud(35, 1.0)
    B(16, (0.14, 0.14, 0.14), (0, -0.25 * s, 0.5 * s))
    B(19, (0.2, 0.2, 0.42), (0, -0.1 * s, 0.22 * s))
    B(21, (0.34, 0.34, 0.5))
    B(22, (1.25, 1.25, 0.14))
    B(24, (1.8, 1.8, 0.09))
    B(27, (1.6, 1.6, 0.15))
    B(30, (1.15, 1.15, 0.55))
    B(33, (0.78, 0.78, 1.42))                 # overshoots tall
    B(36, (1.16, 1.16, 0.78))
    B(38, (0.95, 0.95, 1.1))
    B(41, (1.12, 1.12, 0.82))                 # anticipation of the cry
    B(44, (0.85, 0.85, 1.3), (0, 0, 0.16), (-0.18, 0, 0))   # cry: stretches up, chin raised
    B(46, (1.1, 1.1, 0.86))
    B(48, vol(1.0))
    blink(16, 0.15); blink(31, 0.15); blink(34, 1.0); blink(41, 1.0); blink(43, 0.2); blink(46, 0.2); blink(48, 1.0)
    for i, (dx, dy) in enumerate([(-0.25, -0.5), (0.3, -0.45), (0.05, -0.62)]):       # cry bubbles
        b = blob(f'sli_fx_cry{i}', 0.05 + 0.02 * i, lib.mat('sli_bubble', '#b8d8ff'))
        f0 = 43 + i
        A.key(b, f0 - 1, loc=(dx * 0.3, dy, 0.75), scale=0.001, absolute=True)
        A.key(b, f0, loc=(dx * 0.4, dy, 0.8), scale=0.5, absolute=True)
        A.key(b, f0 + 7, loc=(dx * 1.6, dy - 0.1, 1.5 + 0.12 * i), scale=1.5, absolute=True)
        A.key(b, f0 + 8, loc=(dx * 1.6, dy - 0.1, 1.55 + 0.12 * i), scale=0.001, absolute=True)

    # ---- idle: breathing, a curious look left and right, blinks
    for f in A.frames(50, 70, 2):
        look = 0.3 * math.sin((f - 50) / 20 * TAU) * math.sin((f - 50) / 20 * math.pi)
        B(f, vol(1 + 0.045 * A.wave(f, 16)), rot=(0.05 * A.wave(f, 16, 0.25), 0, look))
    blink(57, 1.0); blink(58, 0.1); blink(60, 1.0); blink(66, 1.0); blink(67, 0.1); blink(69, 1.0)

    # ---- walk: four bouncing hops, each a little different, the last one a forward roll
    D = 1.5 * s
    t0 = T['WALK']
    B(t0, vol(1.0)); B(t0 + 3, vol(0.8)); B(t0 + 6, vol(1.05))
    A.key(root, t0 + 1, rot=(0, 0, 0)); A.key(root, t0 + 6, rot=(0, 0, math.pi / 2))
    hops = [(78, 12, 0.3, 0.2), (90, 12, 0.44, 0.24), (102, 11, 0.34, 0.2), (113, 15, 0.62, 0.36)]   # start, length, height, share
    x = 0.0
    pud(t0 + 4, 1.0)
    for hi, (h0, n, hgt, share) in enumerate(hops):
        dx = D * share
        for f in A.frames(h0, h0 + n):
            p = (f - h0) / n
            if p < 0.2:                              # crouch, then spring
                k = p / 0.2
                z, sqz, lean, xx = 0.0, 0.7 - 0.12 * math.sin(math.pi * k) + 0.55 * k * k * k, 0.12 * k, 0.0
            elif p <= 0.88:
                a = (p - 0.2) / 0.68
                z = hgt * 4 * a * (1 - a)
                sqz = 1.25 - 0.22 * math.sin(math.pi * a)
                lean, xx = 0.22 * math.cos(math.pi * a), A.ease(a)
            else:                                    # land and spread
                k = (p - 0.88) / 0.12
                z, sqz, lean, xx = 0.0, 1.25 - 0.62 * math.sin(math.pi * 0.5 * min(1, k * 1.6)) + 0.07 * k, -0.1 * (1 - k), 1.0
            B(f, vol(sqz), (0, 0, z), (lean, 0, 0))
            A.key(root, f, loc=(x + dx * xx, 0, 0))
            air = 0.2 < p < 0.88
            pud(f, 0.5 if air else (1.2 if p >= 0.88 else 0.9))
            if hi == 3:                              # forward roll on the big last hop
                a = min(1, max(0, (p - 0.2) / 0.68))
                A.key(spin, f, rot=(TAU * A.ease(a), 0, 0))
        x += dx
    A.key(spin, 112, rot=(0, 0, 0)); A.key(spin, 129, rot=(0, 0, 0), absolute=True)
    B(131, vol(1.1)); B(133, vol(0.82), (0, 0, 0)); B(135, vol(1.12), (0, 0, 0.12)); B(137, vol(0.9)); B(139, vol(1.0))
    A.key(root, 132, loc=(D, 0, 0), rot=(0, 0, math.pi / 2)); A.key(root, 137, loc=(D, 0, 0), rot=(0, 0, 0))
    pud(132, 1.0); pud(139, 1.0)
    blink(100, 1.0); blink(101, 0.1); blink(103, 1.0)
    blink(116, 1.0); blink(118, 0.25); blink(126, 0.25); blink(129, 1.0)       # eyes scrunched in the roll

    # ---- attack: Slime Slam
    t0 = T['ATTACK']
    here = A.world(root, t0)
    tgt = A.opponent(here)
    off = Vector((tgt.x - here.x, tgt.y - here.y, 0.0))
    yaw = math.atan2(off.x, -off.y)
    top = 0.34 * s                                    # lands on top of the opponent
    blink(t0, 1.0); blink(t0 + 3, 0.55)                # determined squint
    for f in A.frames(t0, t0 + 10):                   # wind-up: sinks low, trembles, backs off
        k = (f - t0) / 10
        B(f, vol(1 - 0.48 * A.ease(k)), tuple(-off.normalized() * 0.12 * s * A.ease(k)),
          (-0.15 * k, 0, yaw * A.ease(min(1, k * 2)) + 0.06 * math.sin(f * 2.4) * k))
    f_up, f_hit = t0 + 11, t0 + 21
    for f in A.frames(f_up, f_hit - 1):               # tumbling arc
        a = (f - f_up) / (f_hit - f_up)
        pos = off * A.ease(a) * 0.3 + off * a * 0.7 + Vector((0, 0, 0.42 * s * 4 * a * (1 - a) * (1 - a * 0.25) + top * a))
        st = 1.38 - 0.3 * math.sin(math.pi * a)
        B(f, vol(st), tuple(pos), (0, 0, yaw))
        A.key(spin, f, rot=(TAU * A.ease(a), 0, 0))
    A.key(spin, f_hit, rot=(0, 0, 0), absolute=True)
    land = off + Vector((0, 0, top))
    B(f_hit, (1.7, 1.7, 0.3), tuple(land), (0, 0, yaw))             # pancake
    B(f_hit + 2, (1.95, 1.95, 0.2), tuple(land - Vector((0, 0, 0.05 * s))), (0, 0, yaw))
    B(f_hit + 4, (1.3, 1.3, 0.6), tuple(land), (0, 0, yaw))
    f_back, f_home = f_hit + 5, t0 + 36
    for f in A.frames(f_back, f_home - 1):             # springs off with a backflip, back onto its puddle
        a = (f - f_back) / (f_home - f_back)
        pos = off * (1 - a) + Vector((0, 0, 0.4 * s * 4 * a * (1 - a) + top * (1 - a)))
        B(f, vol(1.3 - 0.25 * math.sin(math.pi * a)), tuple(pos), (0, 0, yaw * (1 - A.ease(a))))
        A.key(spin, f, rot=(-TAU * A.ease(a), 0, 0))
    A.key(spin, f_home, rot=(0, 0, 0), absolute=True)
    B(f_home, vol(0.6)); B(f_home + 2, vol(1.16)); B(f_home + 4, vol(0.92), (0, 0, 0)); B(f_home + 6, vol(1.1), (0, 0, 0.1)); B(f_home + 8, vol(0.94)); B(T['HIT'] - 1, vol(1.0))
    blink(f_up, 0.55); blink(f_up + 2, 1.0); blink(f_hit - 1, 1.0); blink(f_hit, 0.15); blink(f_hit + 4, 0.15); blink(f_back + 2, 1.0)
    pud(t0 + 9, 1.1); pud(f_up + 1, 0.6); pud(f_home - 1, 0.6); pud(f_home, 1.3); pud(f_home + 4, 1.0)
    # impact: shockwave ring, splash droplets, flash
    wave_m = lib.mat('sli_fx_wave', '#bfe2ff', 0.2, emit=2.5, alpha=0.8)
    hitp = here + land
    for i, (lag, grow) in enumerate([(0, 3.2), (3, 2.3)]):
        ring = lib.pivot(f'sli_fx_ringp{i}')
        lib.torus(f'sli_fx_ring{i}', (0, 0, 0), 0.5, 0.06, wave_m, ring)
        A.key(ring, 0, loc=hitp, scale=0.001, absolute=True)
        A.key(ring, f_hit + lag - 1, loc=hitp, scale=0.001, absolute=True)
        A.key(ring, f_hit + lag, loc=hitp, scale=(0.4 * s, 0.4 * s, 1.5), absolute=True)
        A.key(ring, f_hit + lag + 9, loc=hitp, scale=(grow * s, grow * s, 0.15), absolute=True)
        A.key(ring, f_hit + lag + 10, loc=hitp, scale=0.001, absolute=True)
    for f, v in [(0, 0.8), (f_hit, 0.8), (f_hit + 12, 0.0)]:
        A.alpha(wave_m, f, v)
    for i in range(12):
        ang = TAU * i / 12 + 0.3
        reach = (0.7 + 0.35 * ((i * 5) % 3)) * s
        d = blob(f'sli_fx_spl{i}', (0.05 + 0.02 * (i % 3)) * s)
        if i % 2:      # half of the spray is thrown all the way back around its puddle
            end = here + Vector((math.cos(ang * 2.3) * (0.5 + 0.1 * i) * s, math.sin(ang * 1.7) * 0.6 * s, 0.03))
            fling(d, f_hit, f_hit + 10 + i % 5, hitp, end, 0.7 * s, size=1.6)
        else:
            fling(d, f_hit, f_hit + 9 + i % 4, hitp, hitp + Vector((math.cos(ang) * reach, math.sin(ang) * reach, -top)),
                  (0.35 + 0.2 * (i % 2)) * s)
    A.light('sli_fx_flash', '#9fd4ff', tuple(here + off * 0.7 + Vector((0, 0, 0.8 * s))),
            [(0, 0), (f_hit - 1, 0), (f_hit + 1, 5000 * s * s), (f_hit + 9, 0)], radius=0.3 * s)

    # ---- hit: knocked back flat, wobbles like jelly
    t0 = T['HIT']
    away = -off.normalized()
    A.key(root, t0 - 1, loc=(D, 0, 0))
    A.key(root, t0 + 4, loc=(D + away.x * 0.3 * s, away.y * 0.3 * s, 0))
    A.key(root, t0 + 12, loc=(D + away.x * 0.38 * s, away.y * 0.38 * s, 0))
    blink(t0 - 1, 1.0); blink(t0 + 1, 0.1)
    for f in A.frames(t0, T['RECOVER']):
        t = f - t0
        if t < 3:
            B(f, (1.0 + 0.2 * t, 1.0 + 0.2 * t, 1.0 - 0.17 * t), rot=(-0.14 * t, 0, 0.12 * t))
        else:
            w = 0.5 * math.exp(-(t - 3) / 6.0) * math.cos((t - 3) * 1.15)
            B(f, vol(1 - w), rot=(-0.42 * math.exp(-(t - 3) / 5.0), 0, 0.36 * math.exp(-(t - 3) / 7.0) * math.cos((t - 3) * 0.6)))
    pud(t0, 1.0); pud(t0 + 3, 1.35); pud(t0 + 12, 1.0)

    # ---- recover: shakes itself dry, then a happy spinning hop back onto its spot
    t0 = T['RECOVER']
    blink(t0 + 1, 0.1); blink(t0 + 9, 0.1); blink(t0 + 11, 1.0)
    for f in A.frames(t0 + 1, t0 + 10):
        t = f - t0
        B(f, vol(1 + 0.05 * math.sin(t * 2.0)), rot=(0, 0, 0.5 * math.sin(t * 2.1) * (1 - t / 11)))
    for i in range(6):                                  # droplets shaken off
        ang = TAU * i / 6
        d = blob(f'sli_fx_shk{i}', 0.045)
        a = A.world(root, t0 + 2 + i) + Vector((math.cos(ang) * 0.55, math.sin(ang) * 0.5, 0.55))
        fling(d, t0 + 2 + i, t0 + 9 + i, a, a + Vector((math.cos(ang) * 0.7, math.sin(ang) * 0.7, -0.5)), 0.25)
    B(t0 + 12, vol(0.7))
    for f in A.frames(t0 + 13, t0 + 20):
        a = (f - t0 - 13) / 7
        B(f, vol(1.22 - 0.2 * math.sin(math.pi * a)), (0, 0, 0.7 * 4 * a * (1 - a)), (0, 0, TAU * A.ease(a)))
    A.key(root, t0 + 12, loc=(D + away.x * 0.38 * s, away.y * 0.38 * s, 0)); A.key(root, t0 + 20, loc=(D, 0, 0))
    B(t0 + 21, vol(0.66), rot=(0, 0, 0), ); B(t0 + 23, vol(1.12)); B(T['END'], vol(1.0))
    A.key(body, t0 + 21, rot=(0, 0, 0), absolute=True)
    pud(t0 + 12, 1.05); pud(t0 + 14, 0.55); pud(t0 + 20, 0.55); pud(t0 + 21, 1.3); pud(T['END'], 1.0)
    blink(t0 + 21, 1.0); blink(t0 + 22, 0.2); blink(T['END'] - 1, 0.2)          # ends with a happy squint
