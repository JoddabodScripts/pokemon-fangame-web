"""Slimontoon: huge slime core with a glowing center, stern brows and eight beaded arms."""
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
    rig = lib.Rig('Slimontoon', 'slimontoon', 'Water', height_cm=600, gait='float', attack='slam')
    slime = lib.mat('slo_slime', '#2460c4', 0.12, sss=0.2, coat=0.8)
    beadA = lib.mat('slo_beadA', '#5a98e8', 0.12, sss=0.2, coat=0.8)
    beadB = lib.mat('slo_beadB', '#2458a8', 0.12, sss=0.2, coat=0.8)
    beadG = lib.mat('slo_beadG', '#7fb6ff', 0.12, coat=0.8, emit=0.35, emit_color='#bfe4ff')
    ring1 = lib.mat('slo_ring1', '#163f86', 0.2, sss=0.1, coat=0.8)
    ring2 = lib.mat('slo_ring2', '#5a98e8', 0.15, sss=0.15, coat=0.8)
    glow = lib.mat('slo_glow', '#bfe4ff', 0.2, emit=4.0, emit_color='#bfe4ff')
    gloss = lib.mat('slo_gloss', '#e8f4ff', 0.1, emit=0.6, coat=1.0)
    dark = lib.mat('slo_dark', '#0e1a3a', 0.3)
    ring3 = lib.mat('slo_ring3', '#9cc8ff', 0.15, sss=0.15, coat=1.0)
    bub = lib.mat('slo_bubble', '#b8d8ff', 0.1, emit=0.3, coat=1.0)
    puddle = lib.mat('slo_puddle', '#2458a8', 0.05, sss=0.15, coat=1.0, alpha=0.85)
    drip = lib.mat('slo_drip', '#3a7ad8', 0.1, sss=0.2, coat=1.0)

    CZ, CR = 1.16, 0.52
    rig.body = lib.pivot('slo_bodyp', (0, 0, 0), rig.root)
    C, R = (0, 0, CZ), (CR, CR * 0.9, CR)
    lib.sphere('slo_core', C, R, slime, rig.body, seg=48)

    # eight beaded arms, raked back a little so it reads in 3D
    radii = [0.13, 0.118, 0.106, 0.092, 0.064]
    for k in range(8):
        ar = math.radians(90 - k * 45)
        d0 = CR - 0.08
        arm = lib.pivot(f'slo_arm{k}', (math.cos(ar) * d0, 0.03, CZ + math.sin(ar) * d0), rig.body,
                        rot=(-0.22, math.pi / 2 - ar, 0))
        z, y = 0.12, 0.0
        for j, r in enumerate(radii):
            m = beadG if j == 2 else (beadA if j % 2 == 0 else beadB)
            lib.sphere(f'slo_arm{k}_b{j}', (0, y, z), (r, r * 0.92, r), m, arm, seg=20)
            lib.sphere(f'slo_arm{k}_g{j}', (-r * 0.45, y - r * 0.72, z + r * 0.4), r * 0.15, gloss, arm, seg=8)
            if j + 1 < len(radii):
                z += (r + radii[j + 1]) * 0.78
                y -= 0.012 * (j + 1)          # tips curl forward a touch
        rig.arms.append((arm, (k * 0.5) % 1.0))

    # ring and glowing center
    fd = (0, -1, -0.12)
    patch(lib, 'slo_ringA', C, R, fd, 0.72, 0.72, ring1, rig.body, k=1.006)
    patch(lib, 'slo_ringB', C, R, fd, 0.56, 0.56, ring2, rig.body, k=1.012)
    patch(lib, 'slo_ringC', C, R, fd, 0.4, 0.4, ring3, rig.body, k=1.016)
    # bubbles caught inside the slime
    for i, (dx, dz, br) in enumerate([(-0.55, -0.35, 0.05), (0.62, -0.22, 0.04), (0.45, 0.48, 0.035), (-0.38, 0.55, 0.03),
                                      (0.7, 0.1, 0.03), (-0.68, 0.12, 0.04), (0.2, -0.7, 0.03)]):
        lib.sphere(f'slo_bub{i}', on(C, R, (dx, -0.75, dz), 0.985), br, bub, rig.body, seg=12)
    # slime dripping from underneath
    for i, (dx, dy, ln) in enumerate([(-0.18, -0.1, 0.22), (0.12, 0.05, 0.3), (0.3, -0.18, 0.16), (-0.32, 0.12, 0.2)]):
        top = on(C, R, (dx, dy, -1), 0.9)
        lib.tube(f'slo_drip{i}', [top, (top[0], top[1], top[2] - ln * 0.6), (top[0], top[1], top[2] - ln)],
                 [0.06, 0.035, 0.012], drip, rig.body, seg=12)
        lib.sphere(f'slo_dripb{i}', (top[0], top[1], top[2] - ln - 0.02), 0.032, drip, rig.body, seg=12)
    # puddle on the ground under it (stays put while it floats)
    lib.sphere('slo_puddle', (0, 0.02, 0.006), (0.62, 0.55, 0.012), puddle, rig.root, seg=40)
    for i, (x, y, r) in enumerate([(0.68, -0.32, 0.09), (-0.7, 0.25, 0.07), (0.45, 0.5, 0.06)]):
        lib.sphere(f'slo_pud{i}', (x, y, 0.006), (r, r, 0.012), puddle, rig.root, seg=16)
    gp = lib.pivot('slo_glowp', C, rig.body)
    patch(lib, 'slo_glow', (0, 0, 0), R, (0, -1, -0.52), 0.2, 0.17, glow, gp, k=1.02, rings=4, seg=24)
    rig.extras.append((gp, 'pulse'))
    patch(lib, 'slo_gloss', C, R, (-0.66, -0.55, 0.56), 0.07, 0.24, gloss, rig.body, k=1.016, rings=3, seg=16)
    patch(lib, 'slo_gloss2', C, R, (-0.42, -0.62, 0.72), 0.05, 0.05, gloss, rig.body, k=1.018, rings=3, seg=16)
    patch(lib, 'slo_gloss3', C, R, (0.62, -0.5, -0.5), 0.04, 0.1, gloss, rig.body, k=1.016, rings=3, seg=16)

    # stern face
    for sx, nm in ((-1, 'L'), (1, 'R')):
        e = lib.eye('slo_eye' + nm, on(C, R, (sx * 0.3, -1, 0.2), 0.99), 0.092, rig.body,
                    iris='#1c3470', pupil='#0e1a3a', sclera='#0e1a3a', look=(sx * 0.22, -1, 0.14), iris_frac=0.7)
        e.scale = (1.0, 1, 1.0)
        b0, b1 = on(C, R, (sx * 0.55, -1, 0.5), 1.05), on(C, R, (sx * 0.1, -1, 0.26), 1.06)
        lib.tube('slo_brow' + nm, [b0, tuple((Vector(b0) + Vector(b1)) / 2), b1], [0.02, 0.03, 0.026], dark, rig.body, seg=8)
    pts = [on(C, R, (x, -1, -0.1), 1.016) for x in (-0.17, 0, 0.17)]
    lib.tube('slo_mouth', pts, [0.012, 0.015, 0.012], dark, rig.body, seg=8)

    rig.attack_origin = (0, -0.6, CZ)
    return rig


def animate(A):
    """Slimontoon: erupts from a geyser and unfurls its arms one by one, swims across in jellyfish
    pulses, and uses Slime Split: it pulls itself in two, both halves slam the opponent with water,
    then they flow back together."""
    import bpy
    import anim_kit as K
    from anim_kit import E, win, spring, decay
    r, T, s, lib = A.rig, A.T, A.size, A.lib
    root, B = r.root, r.body
    arms = [a for a, _ in r.arms]
    eyes = [bpy.data.objects['slo_eyeL'], bpy.data.objects['slo_eyeR']]
    glowp = bpy.data.objects['slo_glowp']
    glow = lib.mat('slo_glow', '#bfe4ff')
    pi = math.pi
    D = 1.5 * s
    aim = 0.7

    def walk_x(f):
        return D * (E(f, 84, 96) * 0.34 + E(f, 102, 114) * 0.33 + E(f, 120, 131) * 0.33)

    A.key(root, 0, scale=0.001)
    A.key(root, T['OUT'] + 1, scale=0.001)
    for f in range(T['OUT'] + 2, T['END'] + 1):
        # ---------------------------------------------------------------- root
        appear = spring((f - 20) / 10, 4.5, 8)
        x = walk_x(f)
        yaw = (pi / 2) * K.win(f, 74, 82, 130, 138) + aim * K.win(f, 146, 152, 176, 184)
        kb = K.win(f, 186, 190, 200, 212)
        A.key(root, f, loc=(x, 0.25 * s * kb, 0), rot=(0, 0, yaw - 0.15 * kb), scale=max(0.001, appear))

        # ---------------------------------------------------------------- weights
        cry = K.win(f, 38, 41, 45, 48)
        idle = math.sin(2 * pi * f / 40)
        pulse_ph = [(84, 96), (102, 114), (120, 131)]
        contract = max(K.win(f, a - 6, a - 1, a, a + 2) for a, b in pulse_ph)
        thrust = max(K.win(f, a, a + 2, a + 6, b) for a, b in pulse_ph)
        stretch = K.win(f, 140, 147, 148, 150)
        split = K.win(f, 148, 151, 176, 182)
        rear = K.win(f, 151, 156, 157, 159)
        slam = K.win(f, 158, 161, 164, 170)
        hit = decay(f, 186, 7, 1.1)
        flex = K.win(f, 212, 217, 226, 230)

        # ---------------------------------------------------------------- body: float, squash and stretch
        bob = 0.04 * s * idle * (1 - K.win(f, 80, 84, 128, 132)) + 0.05 * s * math.sin(2 * pi * f / 18) * K.win(f, 80, 84, 128, 132)
        sx = 1 + 0.08 * idle * 0.2 + 0.45 * stretch - 0.15 * contract + 0.12 * cry + 0.2 * hit + 0.1 * flex
        sz = 1 - 0.2 * stretch + 0.18 * contract - 0.12 * cry - 0.25 * hit + 0.06 * flex
        sy = 1 + 0.2 * thrust
        A.key(B, f, loc=(0, 0, bob + 0.1 * s * rear), rot=(-0.4 * rear + 0.35 * slam + 0.15 * thrust, 0.12 * hit, 0.0),
              scale=(sx, sy, sz))

        # ---------------------------------------------------------------- arms: unfurl, ripple, row, flail
        for k, a in enumerate(arms):
            unf = spring((f - (24 + k * 1.6)) / 8, 4, 9)
            ripple = 0.2 * math.sin(2 * pi * f / 40 - k * 0.8)
            row = 0.7 * contract - 0.55 * thrust
            flail = 0.5 * hit * math.sin(k * 1.7) + 0.35 * slam * math.cos(k * 1.3)
            A.key(a, f, rot=(ripple * (1 - K.win(f, 80, 84, 128, 132)) + row - 0.45 * cry + flail - 0.3 * rear - 0.4 * flex,
                             0.15 * math.sin(f * 0.3 + k) * K.win(f, 186, 188, 200, 206), 0),
                  scale=max(0.001, unf))

        # ---------------------------------------------------------------- face
        glare = max(0.35 * stretch, 0.3 * slam, 0.25 * flex)
        blink = max(K.win(f, x0, x0 + 1, x0 + 2, x0 + 4) for x0 in (56, 66, 100, 194, 198))
        for e in eyes:
            A.key(e, f, scale=(1, 1, 1 - max(0.9 * blink, glare)))
        A.key(glowp, f, scale=1 + 0.08 * idle + 0.35 * stretch + 0.25 * cry + 0.3 * flex)

    for f, v in [(0, 4), (36, 4), (42, 12), (48, 4), (140, 4), (148, 14), (166, 10), (184, 4), (187, 0.5), (190, 4), (192, 0.6), (196, 4), (215, 4), (220, 10), (230, 5)]:
        A.emission(glow, f, v)

    # ------------------------------------------------------------------ send-out geyser
    water = lib.mat('slo_fx_water', '#6fb2ff', 0.05, coat=1.0, sss=0.2, emit=0.3, alpha=0.85)
    foam = lib.mat('slo_fx_foam', '#e8f4ff', 0.2, emit=0.8)
    col = lib.pivot('slo_fx_geyser')
    for i in range(6):
        lib.sphere(f'slo_fx_gm{i}', (0, 0, 0.28 * i), (0.32 - 0.03 * i, 0.32 - 0.03 * i, 0.22), water, col, seg=20)
    for f, sz, sw in [(0, 0.001, 0.001), (15, 0.001, 0.001), (18, 0.6, 0.9), (22, 1.25, 1.0), (27, 1.1, 0.9), (32, 0.25, 0.6), (34, 0.001, 0.001)]:
        A.key(col, f, scale=(sw * s * 0.9, sw * s * 0.9, sz * s * 0.9), absolute=True)
    K.burst(A, 'slo_fx_gdrop', (0, 0, 1.2 * s), 30, n=16, dur=16, speed=1.1, up=0.8, size=0.035, mat=water, seed=1)
    K.ring(A, 'slo_fx_gring', (0, 0, 0.02), 18, dur=14, r0=0.2, r1=1.1, thick=0.05, mat=foam)
    K.ring(A, 'slo_fx_gring2', (0, 0, 0.02), 31, dur=12, r0=0.3, r1=0.9, thick=0.04, mat=foam)

    # ------------------------------------------------------------------ Slime Split
    import mathutils
    here = A.world(root, 150)
    here = mathutils.Vector((here.x, 0, 0))
    dirv = mathutils.Vector((math.sin(aim), -math.cos(aim), 0))
    side = mathutils.Vector((dirv.y * -1, dirv.x, 0)) * -1      # screen-ish sideways
    off = 0.62 * s

    def dup(obj, parent):
        c = obj.copy()
        bpy.context.scene.collection.objects.link(c)
        c.parent = parent
        for ch in obj.children:
            dup(ch, c)
        return c

    twin = dup(root, None)
    twin.animation_data_clear()
    for f in range(0, T['END'] + 1, 1):
        sp = K.win(f, 148, 151, 176, 182)
        rr = K.win(f, 151, 156, 157, 159)
        sl = K.win(f, 158, 161, 164, 170)
        pos_o = here - side * off * sp + dirv * (0.45 * s * sl - 0.12 * s * rr)
        pos_t = here + side * off * sp + dirv * (0.45 * s * sl - 0.12 * s * rr)
        sc_o = 1 - 0.3 * sp
        if 146 <= f <= 186:
            A.key(root, f, loc=(pos_o.x - here.x + walk_x(f), pos_o.y, 0.08 * s * rr), scale=sc_o)
        A.key(twin, f, loc=pos_t, rot=(0, 0, aim * K.win(f, 146, 152, 176, 184)),
              scale=max(0.001, 0.72 * spring((f - 148) / 6, 5, 9) * (1 - E(f, 176, 182))) if f >= 148 else 0.001, absolute=True)
    # water jets from both halves, then a splash on the opponent
    tgt = A.opponent(here)
    for h, sgn in enumerate((-1, 1)):
        st = here + side * off * sgn + dirv * 0.4 * s + mathutils.Vector((0, 0, 1.0 * s))
        for j in range(4):
            K.projectile(A, f'slo_fx_jet{h}{j}', st, tgt + mathutils.Vector((0, 0, 0.1 * j * s)), 157 + j * 2, flight=8,
                         mat=water, radius=0.07, trail=2)
    K.ring(A, 'slo_fx_hitring', (tgt.x, tgt.y, 0.03), 165, dur=12, r0=0.2, r1=1.3, thick=0.06, mat=foam)
    K.burst(A, 'slo_fx_hit', tgt, 165, n=18, dur=16, speed=1.3, up=0.9, size=0.04, mat=water, seed=3)
    K.flash_sphere(A, 'slo_fx_hitflash', tgt, 165, dur=8, r1=0.35, mat=foam)
    A.light('slo_fx_hitlight', '#7fc4ff', tgt + mathutils.Vector((0, 0, 0.5 * s)), [(0, 0), (164, 0), (166, 900 * s * s), (176, 0)])
    # splitting goo strand between the halves
    goo = lib.mat('slo_fx_goo', '#2f6fc4', 0.1, sss=0.2, coat=1.0)
    strand = lib.pivot('slo_fx_strand', (here.x, 0, 1.1 * s))
    lib.sphere('slo_fx_strandm', (0, 0, 0), (1.0, 0.25, 0.25), goo, strand, seg=20)
    for f, sc in [(0, 0.001), (146, 0.001), (148, 0.6), (151, 0.9), (153, 0.001), (175, 0.001), (178, 0.9), (182, 0.001)]:
        A.key(strand, f, scale=(sc * off, sc * off * 0.4, sc * off * 0.4) if sc > 0.001 else 0.001, absolute=True)
    # shaking off droplets at the end
    K.burst(A, 'slo_fx_shake', (here.x, 0, 1.2 * s), 210, n=12, dur=14, speed=0.9, up=0.5, size=0.03, mat=water, seed=5)


# Phase speeds for render.retime: above 1 is slower and longer, below 1 is quicker.
TIMING = {'send': 1.6, 'idle': 1.6, 'walk': 1.5, 'attack': 1.8, 'hit': 1.4, 'recover': 1.5}
