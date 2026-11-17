"""Slimarton: slime core with a big face and five beaded starfish arms that curl, grip and flick."""
import bpy
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


ARM_ANGLES = [90, 18, -54, -126, 162]          # top, right, right leg, left leg, left
BEADS = [0.165, 0.142, 0.12, 0.1]


def build(lib):
    rig = lib.Rig('Slimarton', 'slimarton', 'Water', height_cm=130, gait='hop', attack='slam')
    slime = lib.mat('sla_slime', '#2a6cd0', 0.12, sss=0.2, coat=1.0)
    beadA = lib.mat('sla_beadA', '#5c9cec', 0.12, sss=0.25, coat=1.0)
    beadB = lib.mat('sla_beadB', '#2458b4', 0.12, sss=0.2, coat=1.0)
    coreA = lib.mat('sla_coreA', '#a8d2ff', 0.15, sss=0.2, coat=1.0)
    coreB = lib.mat('sla_coreB', '#5c9cec', 0.15, sss=0.2, coat=1.0)
    ring1 = lib.mat('sla_ring1', '#1a4aa0', 0.2, sss=0.1, coat=1.0)
    ring2 = lib.mat('sla_ring2', '#62a4f0', 0.15, sss=0.15, coat=1.0)
    ring3 = lib.mat('sla_ring3', '#a4d0ff', 0.15, sss=0.15, coat=1.0)
    gloss = lib.mat('sla_gloss', '#e8f4ff', 0.1, emit=0.6, coat=1.0)
    bub = lib.mat('sla_bubble', '#b8d8ff', 0.1, emit=0.25, coat=1.0)
    dark = lib.mat('sla_dark', '#0e1a3a', 0.3)
    pink = lib.mat('sla_cheek', '#ff9ac0', 0.5, sss=0.3)
    puddle = lib.mat('sla_puddle', '#2f6fc4', 0.05, sss=0.15, coat=1.0)

    # body pivot on the ground; hub at the core's center; the core (face) and the wheel of arms
    # hang off the hub separately, so the arms can cartwheel around a face that stays upright
    rig.body = lib.pivot('sla_bodyp', (0, 0, 0), rig.root)
    hub = lib.pivot('sla_hub', (0, 0, 1.0), rig.body)
    corep = lib.pivot('sla_corep', (0, 0, 0), hub)
    wheel = lib.pivot('sla_wheel', (0, 0, 0), hub)
    rig.head = corep

    CR = 0.5
    C, R = (0, 0, 0), (CR, CR * 0.92, CR * 0.96)
    lib.sphere('sla_core', C, R, slime, corep, seg=48)

    # ---- five beaded arms, each a chain of pivots (one per bead) so it can curl like a tentacle
    curls = [(0.10, 0.20), (0.14, -0.16), (-0.03, -0.12), (-0.03, 0.12), (0.14, 0.16)]   # rest curl per joint (rx, ry)
    arms = []
    for k, a in enumerate(ARM_ANGLES):
        ar = math.radians(a)
        d0 = CR * 0.84
        base = lib.pivot(f'sla_arm{k}', (math.cos(ar) * d0, 0, math.sin(ar) * d0), wheel, rot=(0, math.pi / 2 - ar, 0))
        # shoulder: the arm grows out of the core
        lib.tube(f'sla_arm{k}_sh', [(0, 0, -0.16), (0, 0, -0.04), (0, 0, 0.1), (0, 0, 0.2)], [0.25, 0.22, 0.17, 0.12], slime, base)
        chain, beads, par, z = [base], [], base, 0.15
        for j, r in enumerate(BEADS):
            bp = lib.pivot(f'sla_arm{k}_bp{j}', (0, 0, z), par)       # bead holder (scaled when a bead is flicked off)
            rr = (r, r * 0.94, r * 0.96)
            lib.sphere(f'sla_arm{k}_b{j}', (0, 0, 0), rr, beadA if j % 2 == 0 else beadB, bp, seg=24)
            # the ball of sticky slime inside each bead, and a small highlight
            patch(lib, f'sla_arm{k}_n{j}', (0, 0, 0), rr, (0, -1, 0.05), 0.62, 0.62, coreA if j % 2 == 0 else coreB, bp,
                  k=1.012, rings=3, seg=16)
            lib.sphere(f'sla_arm{k}_g{j}', on((0, 0, 0), rr, (-0.25, -0.9, 0.3), 1.0), (r * 0.16, r * 0.05, r * 0.16), gloss, bp, seg=8)
            beads.append(bp)
            if j + 1 < len(BEADS):
                seg = lib.pivot(f'sla_arm{k}_j{j + 1}', (0, 0, z), par, rot=(curls[k][0], curls[k][1], 0))
                chain.append(seg)
                par, z = seg, (r + BEADS[j + 1]) * 0.74
        arms.append(dict(chain=chain, beads=beads, tip=beads[-1], tip_z=z))
        rig.arms.append((base, (k * 0.4) % 1.0))

    # ---- inside the core: concentric ring, gloss, bubbles
    fd = (0, -1, -0.1)
    patch(lib, 'sla_ringA', C, R, fd, 0.84, 0.80, ring1, corep, k=1.004)
    patch(lib, 'sla_ringB', C, R, fd, 0.68, 0.64, ring2, corep, k=1.008)
    patch(lib, 'sla_ringC', C, R, (-0.05, -1, -0.04), 0.46, 0.42, ring3, corep, k=1.012)
    patch(lib, 'sla_gloss', C, R, (-0.6, -0.62, 0.56), 0.08, 0.22, gloss, corep, k=1.016, rings=3, seg=16)
    patch(lib, 'sla_gloss2', C, R, (-0.44, -0.6, 0.78), 0.065, 0.065, gloss, corep, k=1.016, rings=3, seg=16)
    for i, (d, sz) in enumerate([((-0.4, -0.78, -0.62), 0.032), ((0.52, -0.75, -0.5), 0.022), ((0.36, -0.7, -0.72), 0.018),
                                 ((0.6, 0.4, 0.6), 0.03), ((-0.5, 0.7, 0.3), 0.024)]):
        lib.sphere(f'sla_bub{i}', on(C, R, d, 0.99), sz, bub, corep, seg=12)

    # ---- face: big shiny eyes, cheeks, a cheeky grin, and brows that only show when it is angry
    eyes, brows = [], []
    for sx, nm in ((-1, 'L'), (1, 'R')):
        e = lib.eye('sla_eye' + nm, on(C, R, (sx * 0.3, -1, 0.14), 0.99), 0.105, corep,
                    iris='#1c3470', pupil='#0e1a3a', sclera='#0e1a3a', look=(sx * 0.22, -1, 0.1), iris_frac=0.7)
        e.scale = (0.85, 1, 1.3)
        eyes.append(e)
        patch(lib, 'sla_cheek' + nm, C, R, (sx * 0.64, -1, -0.16), 0.12, 0.075, pink, corep, k=1.016, rings=3, seg=16)
        bp = lib.pivot('sla_browp' + nm, on(C, R, (sx * 0.3, -1, 0.5), 1.03), corep)
        o = Vector(bp.location)
        b0, b1 = Vector(on(C, R, (sx * 0.52, -1, 0.56), 1.04)) - o, Vector(on(C, R, (sx * 0.1, -1, 0.4), 1.05)) - o
        lib.tube('sla_brow' + nm, [b0, (b0 + b1) / 2 + Vector((0, -0.012, 0.006)), b1], [0.016, 0.03, 0.024], dark, bp, seg=8)
        bp.scale = (0.001, 0.001, 0.001)
        brows.append(bp)
    pts = [on(C, R, (x, -1, z), 1.014) for x, z in [(-0.2, -0.2), (-0.11, -0.29), (0.01, -0.32), (0.12, -0.28), (0.21, -0.17)]]
    lib.tube('sla_mouth', pts, [0.01, 0.016, 0.018, 0.016, 0.01], dark, corep, seg=8)

    # ---- stand it on its two lower arms: measure the lowest bead and drop the hub onto the ground
    bpy.context.view_layer.update()
    low = min((arms[k]['beads'][j].matrix_world.translation.z - BEADS[j] * 0.96) for k in (2, 3) for j in range(len(BEADS)))
    hub.location.z -= low
    bpy.context.view_layer.update()

    # wet footprints under its feet and a drip off each side arm (the story: it has just come off a rock)
    puddles = []
    for k in (2, 3):
        t = arms[k]['tip'].matrix_world.translation
        puddles.append(lib.sphere(f'sla_puddle{k}', (t.x * 1.02, t.y, 0.01), (0.2, 0.17, 0.02), puddle, rig.root))
        puddles.append(lib.sphere(f'sla_puddle{k}b', (t.x * 1.3, t.y - 0.14, 0.008), (0.07, 0.06, 0.015), puddle, rig.root))
    puddles.append(lib.sphere('sla_puddleC', (0.05, 0.05, 0.008), (0.12, 0.1, 0.015), puddle, rig.root))
    for k in (1, 4):
        tip, r = arms[k]['tip'], BEADS[-1]
        down = tip.matrix_world.to_3x3().inverted() @ Vector((0, 0, -1))
        a, b = down * r * 0.75, down * r * 1.55
        lib.tube(f'sla_drip{k}', [a, (a + b) / 2, b], [r * 0.34, r * 0.2, r * 0.3], beadB, tip)
        lib.sphere(f'sla_dripb{k}', b + down * r * 0.2, r * 0.36, beadB, tip, seg=12)

    hz = hub.location.z
    rig.sla = dict(hub=hub, core=corep, wheel=wheel, arms=arms, eyes=eyes, brows=brows, puddles=puddles,
                   hz=hz, rt=hz / math.cos(math.radians(36)))
    rig.attack_origin = (0, -0.5, hz)
    return rig


# ---------------------------------------------------------------- animation
def animate(A):
    """Slimarton: drops in as a spinning ball of wrapped arms and unfurls, cartwheels on its arm tips
    around a face that stays upright, then Slime Shot: it gets angry and flicks beads off its arms."""
    r, T, s, lib = A.rig, A.T, A.size, A.lib
    P = r.sla
    root, body, hub, core, wheel, arms = r.root, r.body, P['hub'], P['core'], P['wheel'], P['arms']
    hz, Rt = P['hz'], P['rt']
    E = 2 * Rt * math.sin(math.radians(36))            # distance between two arm tips = one cartwheel step
    TOP, RA, RL, LL, LA = 0, 1, 2, 3, 4

    def curve(pts, t):
        """Smooth piecewise curve through (t, value) points."""
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t <= t1:
                return v0 + (v1 - v0) * A.ease((t - t0) / (t1 - t0))
        return pts[-1][1]

    def pose(k, f, b=(0, 0), c=(0, 0)):
        """Key arm k: b = (rx, ry) at the shoulder, c = (rx, ry) per joint, or a function of the joint index."""
        ch = arms[k]['chain']
        A.key(ch[0], f, rot=(b[0], b[1], 0))
        for j in range(1, len(ch)):
            cj = c(j) if callable(c) else c
            A.key(ch[j], f, rot=(cj[0], cj[1], 0))

    def wrap(k, f, u):                                 # u = 1: arm wrapped around the core, 0: rest
        pose(k, f, (0, 1.3 * u), lambda j: (-0.1 * u if k in (TOP, RA, LA) else 0, 0.5 * u + (0.16 * u if k in (RA, RL) else 0)))

    def B(f, z=1.0, loc=(0, 0, 0), rot=(0, 0, 0)):
        w = 1 / math.sqrt(z)
        A.key(body, f, loc=loc, rot=rot, scale=(w, w, z))

    def eyes(f, v, which=(0, 1)):
        for i in which:
            A.key(P['eyes'][i], f, scale=(1, 1, v))

    def brows(f, v):
        for b in P['brows']:
            A.key(b, f, scale=(v, v, v), absolute=True)

    def pud(f, v):
        for q in P['puddles']:
            A.key(q, f, scale=(v, v, 1))

    def roll(deg):
        """Center offset (x, z) of the five-pointed wheel after rolling `deg` on its arm tips."""
        n = math.floor(deg / 72)
        m = math.radians(deg - 72 * n - 36)
        return n * E + E / 2 + Rt * math.sin(m), Rt * math.cos(m) - hz

    # ---- send-out: a tight spinning ball of wrapped arms; it bounces, then the arms unfurl one by one
    A.key(root, 0, scale=0.001); A.key(root, 15, scale=0.001); A.key(root, 16, scale=1)
    A.key(root, 0, loc=(0, 0, 0), rot=(0, 0, 0))
    ball = -(hz - 0.74)
    pud(0, 0.001); pud(33, 0.001); pud(36, 1.25); pud(40, 1.0)
    A.key(body, 16, loc=(0, -0.25 * s, 0.5 * s - 0.3 * hz), scale=0.3, rot=(0, 0, 0))
    A.key(body, 19, loc=(0, -0.1 * s, ball + 0.5), scale=1.0)
    A.key(body, 22, loc=(0, 0, ball), scale=(1.1, 1.1, 0.92))
    A.key(body, 26, loc=(0, 0, ball + 0.5), scale=1.0)
    A.key(body, 30, loc=(0, 0, 0.42))
    A.key(body, 34, loc=(0, 0, 0), scale=(1.12, 1.12, 0.8))
    A.key(body, 37, loc=(0, 0, 0), scale=(0.96, 0.96, 1.08))
    A.key(body, 40, scale=(1.07, 1.07, 0.88))                              # anticipation of the cry
    A.key(body, 43, loc=(0, 0, 0.3), scale=(0.94, 0.94, 1.14))             # cry: star jump
    A.key(body, 46, loc=(0, 0, 0), scale=(1.06, 1.06, 0.9))
    B(48)
    for f in A.frames(16, 34):
        A.key(wheel, f, rot=(0, -2 * math.pi * (1 - A.ease((f - 16) / 18.0)) ** 1.5, 0))
    for k, a0 in ((RL, 23), (LL, 24), (RA, 26), (LA, 28), (TOP, 30)):
        wrap(k, 16, 1.0); wrap(k, a0, 1.0); wrap(k, a0 + 5, -0.22); wrap(k, a0 + 8, 0.1); wrap(k, a0 + 10, 0.0)
    for k in range(5):
        wrap(k, 40, 0.22); wrap(k, 43, -0.2); wrap(k, 46, 0.06); wrap(k, 48, 0.0)
    A.key(core, 16, scale=1.0, rot=(0, 0, 0)); A.key(core, 40, scale=0.94); A.key(core, 43, scale=1.14, rot=(-0.15, 0, 0))
    A.key(core, 47, scale=1.0, rot=(0, 0, 0))
    eyes(16, 0.2); eyes(30, 0.2); eyes(33, 1.0); eyes(40, 1.0); eyes(42, 0.15); eyes(46, 0.15); eyes(48, 1.0)

    # ---- idle: bounces on its feet, the top arm sways like a feeler, a glance to the side
    for f in A.frames(50, 70, 2):
        t = f - 48
        B(f, 1 + 0.035 * math.sin(t * 0.52))
        pose(TOP, f, (0.05 * math.sin(t * 0.26), 0.2 * math.sin(t * 0.26)), lambda j: (0, 0.14 * math.sin(t * 0.26 - 0.7 * j)))
        pose(RA, f, (0.12 * math.sin(t * 0.52 + 1), -0.1 * math.sin(t * 0.52)), lambda j: (0.06 * math.sin(t * 0.52 - 0.6 * j), 0))
        pose(LA, f, (0.12 * math.sin(t * 0.52 + 2.5), 0.1 * math.sin(t * 0.52 + 1.5)), lambda j: (0.06 * math.sin(t * 0.52 + 1.5 - 0.6 * j), 0))
        A.key(core, f, rot=(0, 0.06 * math.sin(t * 0.26), 0.28 * math.sin(t * 0.26) * math.sin(t * 0.13)))
    eyes(59, 1.0); eyes(60, 0.1); eyes(62, 1.0)
    for k in (TOP, RA, LA):
        pose(k, 72)
    A.key(core, 72, rot=(0, 0, 0)); B(72)

    # ---- walk: a cartwheel on its arm tips, three tips over, the face riding upright in the middle
    th = [(72, 0), (77, -13), (126, 223), (131, 213), (136, 216)]
    theta = lambda f: curve(th[:2], f) if f <= 77 else (-13 + 236 * (0.55 * (f - 77) / 49 + 0.45 * A.ease((f - 77) / 49)) if f <= 126 else curve(th[2:], f))  # noqa: E731
    A.key(wheel, 72, rot=(0, 0, 0), absolute=True)
    for f in A.frames(72, 137):
        d = theta(f)
        w = (theta(f + 1) - theta(f - 1)) / 2          # degrees per frame
        x, z = roll(d)
        A.key(root, f, loc=(x, 0, 0))
        tip_down = abs(((d + 36) % 72) - 36) / 36       # 0 standing on two tips, 1 balanced on one
        B(f, 1 - 0.05 * (1 - tip_down) * min(1, abs(w) / 3), (0, 0, z))
        A.key(wheel, f, rot=(0, math.radians(d), 0), absolute=True)
        for k in range(5):                              # the arms trail behind the spin and whip at each step
            snap = 0.1 * math.sin(math.radians(d) * 5 + k) * min(1, abs(w) / 4)
            pose(k, f, (0, -0.02 * w), lambda j: (0, -0.035 * w * (0.6 + 0.25 * j) + snap))
        A.key(core, f, rot=(0, 0.02 * w, curve([(72, 0), (78, 0.55), (124, 0.5), (134, 0)], f)))
    eyes(96, 1.0); eyes(98, 0.2); eyes(110, 0.2); eyes(113, 1.0)          # happy squint mid-roll
    pud(72, 1.0); pud(79, 0.001); pud(129, 0.001); pud(133, 1.2); pud(137, 1.0)
    D = roll(216)[0]
    A.key(root, 138, loc=(D, 0, 0)); B(138)
    for k in range(5):
        pose(k, 139)
    A.key(core, 139, rot=(0, 0, 0))
    W0 = math.radians(216)                              # the wheel now rests three tips round; it looks the same

    # ---- attack: Slime Shot. It gets angry and flicks the end beads off three arms, one after another
    t0 = T['ATTACK']
    here = A.world(root, t0)
    tgt = A.opponent(here)
    off = Vector((tgt.x - here.x, tgt.y - here.y, 0.0))
    aim = off.normalized()
    yaw = math.atan2(off.x, -off.y) * 0.85
    shots = [(RA, t0 + 12), (TOP, t0 + 18), (LA, t0 + 24)]
    brows(0, 0.001); brows(t0 + 1, 0.001); brows(t0 + 4, 1.2); brows(t0 + 6, 1.0); brows(t0 + 41, 1.0); brows(t0 + 44, 0.001)
    eyes(t0 + 1, 1.0); eyes(t0 + 4, 0.62); eyes(t0 + 40, 0.62); eyes(t0 + 44, 1.0)
    # stomps round to face the target
    B(t0); B(t0 + 3, 0.86, rot=(0, 0, yaw * 0.3)); B(t0 + 5, 1.1, (0, 0, 0.12), (0, 0, yaw * 0.8)); B(t0 + 7, 0.9, rot=(0, 0, yaw)); B(t0 + 9, 1.0, rot=(0, 0, yaw))
    bead_m = [lib.mat('sla_beadB', '#2458b4'), lib.mat('sla_beadA', '#5c9cec')]
    splat_m = lib.mat('sla_fx_splat', '#7fb8ff', 0.1, emit=0.8, coat=1.0)
    for i, (k, fr) in enumerate(shots):
        ch, tip = arms[k]['chain'], arms[k]['tip']
        big = 1.0 + 0.2 * i                              # each flick is angrier than the last
        base = [(-9, 0), (-3, -1.0 * big), (0, 0.85), (2, 1.15), (6, -0.18), (10, 0)]
        whip = [(-9, 0), (-3, -0.5 * big), (0, 0.6), (3, 0.3), (7, -0.12), (11, 0)]
        for f in A.frames(fr - 9, fr + 13):
            t = f - fr
            pose(k, f, (curve(base, t), 0), lambda j: (curve(whip, t - 0.8 * j), 0))
        # body: rocks back with the wind-up, snaps forward on the release
        B(fr - 3, 0.92, tuple(-aim * 0.07 * s), (-0.1, 0, yaw)); B(fr, 1.06, tuple(aim * 0.1 * s), (0.14, 0, yaw)); B(fr + 4, 1.0, rot=(0, 0, yaw))
        A.key(core, fr - 3, rot=(-0.16, 0, 0)); A.key(core, fr, rot=(0.2, 0, 0)); A.key(core, fr + 4, rot=(0, 0, 0))
        # the bead leaves the arm, flies, and bursts on the target; then a new one swells back
        A.key(tip, fr - 1, scale=1.0); A.key(tip, fr, scale=0.001)
        g = t0 + 32 + 3 * i
        A.key(tip, g, scale=0.001); A.key(tip, g + 3, scale=1.4); A.key(tip, g + 5, scale=0.88); A.key(tip, g + 7, scale=1.0)
        a = A.world(tip, fr - 1)
        b = tgt + Vector((0.1 * s * (i - 1), 0, 0.08 * s * (i - 1)))
        shot = lib.pivot(f'sla_fx_shot{i}')
        lib.sphere(f'sla_fx_shotm{i}', (0, 0, 0), BEADS[-1] * 1.25, bead_m[0], shot, seg=16)
        lib.sphere(f'sla_fx_shotn{i}', (0, -BEADS[-1] * 0.5, 0), BEADS[-1] * 0.9, bead_m[1], shot, seg=12)
        A.key(shot, 0, loc=a, scale=0.001, absolute=True); A.key(shot, fr - 1, loc=a, scale=0.001, absolute=True)
        n = 8
        for f in A.frames(fr, fr + n):
            u = (f - fr) / n
            pos = a.lerp(b, u) + Vector((0, 0, 0.22 * s * 4 * u * (1 - u)))
            A.key(shot, f, loc=pos, rot=(u * 9, u * 5, 0), scale=(1 + 0.5 * math.sin(math.pi * u), 1 - 0.2 * math.sin(math.pi * u), 1), absolute=True)
        A.key(shot, fr + n + 1, loc=b, scale=0.001, absolute=True)
        for j in range(3):                              # a string of slime trailing the bead
            dr = lib.pivot(f'sla_fx_tr{i}_{j}')
            lib.sphere(f'sla_fx_trm{i}_{j}', (0, 0, 0), BEADS[-1] * (0.6 - 0.13 * j), bead_m[1], dr, seg=10)
            A.key(dr, 0, loc=a, scale=0.001, absolute=True); A.key(dr, fr + j, loc=a, scale=0.001, absolute=True)
            for f in A.frames(fr + j + 1, fr + n + j + 1):
                u = (f - fr - j - 1) / n
                A.key(dr, f, loc=a.lerp(b, u) + Vector((0, 0, 0.22 * s * 4 * u * (1 - u) - 0.03 * j)), scale=1.0, absolute=True)
            A.key(dr, fr + n + j + 2, loc=b, scale=0.001, absolute=True)
        fh = fr + n
        sp = lib.sphere(f'sla_fx_splat{i}', (0, 0, 0), 1.0, splat_m, seg=16)
        A.key(sp, 0, loc=b, scale=0.001, absolute=True); A.key(sp, fh - 1, loc=b, scale=0.001, absolute=True)
        A.key(sp, fh + 2, loc=b, scale=(0.4 * s, 0.4 * s, 0.28 * s), absolute=True); A.key(sp, fh + 7, loc=b + Vector((0, 0, -0.2 * s)), scale=0.001, absolute=True)
        for j in range(6):                              # sticky spray, half of it flung back toward Slimarton
            ang = j * 1.05 + i
            dr = lib.pivot(f'sla_fx_sp{i}_{j}')
            lib.sphere(f'sla_fx_spm{i}_{j}', (0, 0, 0), 0.05 * s, bead_m[j % 2], dr, seg=10)
            end = (here + Vector((math.cos(ang * 2) * 0.6 * s + 0.5 * s, math.sin(ang) * 0.5 * s - 0.3 * s, 0.03))) if j % 2 else \
                b + Vector((math.cos(ang) * 0.9 * s, math.sin(ang) * 0.9 * s, -b.z))
            A.key(dr, 0, loc=b, scale=0.001, absolute=True); A.key(dr, fh - 1, loc=b, scale=0.001, absolute=True)
            m = 9 + j
            for f in A.frames(fh, fh + m):
                u = (f - fh) / m
                A.key(dr, f, loc=b.lerp(end, u) + Vector((0, 0, 0.5 * s * 4 * u * (1 - u))), scale=1.4 - 0.7 * u, absolute=True)
            A.key(dr, fh + m + 1, loc=end, scale=0.001, absolute=True)
        A.light(f'sla_fx_light{i}', '#8fc8ff', tuple(here + off * 0.7 + Vector((0, 0, 0.7 * s))),
                [(0, 0), (fh - 1, 0), (fh + 1, 2500 * s * s * big), (fh + 7, 0)], radius=0.2 * s)
    B(t0 + 38, 1.0, rot=(0, 0, yaw)); B(t0 + 41, 0.88, rot=(0, 0, yaw * 0.5)); B(t0 + 43, 1.08, (0, 0, 0.1)); B(t0 + 45, 1.0)
    for k in range(5):
        pose(k, T['HIT'] - 1)

    # ---- hit: bowled back onto one foot, arms flung forward, teeters, almost goes over
    t0 = T['HIT']
    rock = [(0, 216), (5, 181), (12, 228), (16, 211), (20, 216)]
    slide = [(0, 0), (6, 1), (20, 1)]
    for f in A.frames(t0, T['RECOVER']):
        t = f - t0
        x, z = roll(curve(rock, t))
        q = curve(slide, t)
        A.key(root, f, loc=(x - 0.1 * s * q, 0.22 * s * q, 0))
        B(f, 1 - 0.1 * math.exp(-t / 4.0) * math.cos(t * 0.9), (0, 0, z))
        A.key(wheel, f, rot=(0, math.radians(curve(rock, t)), 0), absolute=True)
        A.key(core, f, rot=(-0.4 * math.exp(-t / 6.0) * math.cos(t * 0.5), 0.25 * math.exp(-t / 7.0) * math.sin(t * 0.7), 0),
              scale=(1 + 0.16 * math.exp(-t / 5.0) * math.cos(t * 1.1), 1 - 0.2 * math.exp(-t / 5.0) * math.cos(t * 1.1), 1 + 0.1 * math.exp(-t / 5.0) * math.cos(t * 1.1)))
        for k in range(5):
            fl = curve([(0, 0), (3, 0.75), (9, -0.35), (14, 0.15), (19, 0)], t - 0.4 * k)
            pose(k, f, (fl, 0), lambda j: (curve([(0, 0), (3, 0.4), (9, -0.3), (14, 0.12), (19, 0)], t - 0.4 * k - 0.9 * j), 0))
    eyes(t0 - 1, 1.0); eyes(t0 + 1, 0.1); eyes(t0 + 17, 0.1); eyes(t0 + 20, 1.0)
    pud(t0, 1.0); pud(t0 + 3, 0.001)
    hx, hy = D - 0.1 * s, 0.22 * s

    # ---- recover: shakes its arms out, then a twirling star jump back to its mark and a salute
    t0 = T['RECOVER']
    for f in A.frames(t0 + 1, t0 + 9):
        t = f - t0
        for k in range(5):
            pose(k, f, (0, 0.12 * math.sin(t * 2.2 + k * 1.3) * (1 - t / 10)), lambda j: (0, 0.3 * math.sin(t * 2.2 + k * 1.3 - 0.8 * j) * (1 - t / 10)))
        B(f, 1 + 0.03 * math.sin(t * 2.2))
    for k in range(5):
        wrap(k, t0 + 10, 0.0); wrap(k, t0 + 13, 0.3); wrap(k, t0 + 17, -0.22); wrap(k, t0 + 21, 0.1)
    A.key(core, t0 + 10, rot=(0, 0, 0), scale=1.0); A.key(core, t0 + 13, scale=0.94); A.key(core, t0 + 17, scale=1.12); A.key(core, t0 + 21, scale=1.0)
    B(t0 + 10); B(t0 + 13, 0.8)
    A.key(root, t0 + 13, loc=(hx, hy, 0)); A.key(wheel, t0 + 13, rot=(0, W0, 0), absolute=True)
    for f in A.frames(t0 + 14, t0 + 20):
        a = (f - t0 - 14) / 6
        B(f, 1.14 - 0.1 * math.sin(math.pi * a), (0, 0, 0.75 * 4 * a * (1 - a)))
        A.key(wheel, f, rot=(0, W0 + math.radians(144) * A.ease(a), 0), absolute=True)
        A.key(root, f, loc=(hx + (D - hx) * a, hy * (1 - a), 0))
    B(t0 + 21, 0.8); B(t0 + 23, 1.07); B(T['END'], 1.0)
    pud(t0 + 20, 0.001); pud(t0 + 22, 1.25); pud(T['END'], 1.0)
    # final pose: side arms thrown up, the top arm curls forward in a salute, and a wink
    pose(RA, T['END'], (0.1, -0.4), (0.05, -0.12)); pose(LA, T['END'], (0.1, 0.4), (0.05, 0.12))
    pose(TOP, t0 + 22, (0.5, 0), (0.45, 0)); pose(TOP, T['END'], (0.3, -0.15), (0.3, 0))
    pose(RL, T['END']); pose(LL, T['END'])
    A.key(core, T['END'], rot=(-0.08, 0, 0))
    eyes(t0 + 21, 1.0); eyes(t0 + 23, 0.12, which=(1,)); eyes(T['END'], 0.12, which=(1,))
