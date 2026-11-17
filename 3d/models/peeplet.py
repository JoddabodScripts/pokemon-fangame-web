"""Peeplet: tiny brown songbird with a head tuft, cream belly and two-tone beak."""
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


def blade(L, W):
    """Feather/leaf outline in XZ: base at the origin, tip at (0, L)."""
    return [(-W * .3, 0), (W * .3, 0), (W * .5, L * .35), (W * .42, L * .7), (0, L), (-W * .42, L * .7), (-W * .5, L * .35)]


def fuzz(m, sheen=0.6, tint=None):
    """Soft feathery look: a sheen layer on top of the base colour."""
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Sheen Roughness'].default_value = 0.45
    if tint is not None:
        b.inputs['Sheen Tint'].default_value = (*tint, 1)
    return m


def build(lib):
    rig = lib.Rig('Peeplet', 'peeplet', 'Flying', height_cm=15, gait='walk', attack='peck')
    warm = (1.0, 0.86, 0.6)
    tan = fuzz(lib.mat('pee_tan', '#d9a35b', 0.7, sss=0.12), 0.7, warm)
    brown = fuzz(lib.mat('pee_brown', '#a8743a', 0.7, sss=0.08), 0.7, warm)
    dbrown = fuzz(lib.mat('pee_dbrown', '#7a5228', 0.65, coat=0.15), 0.5, warm)
    light = fuzz(lib.mat('pee_light', '#f0c888', 0.7, sss=0.15), 0.7, warm)
    cream = fuzz(lib.mat('pee_cream', '#fff2d8', 0.75, sss=0.25), 0.8, (1, 0.95, 0.85))
    beakU = lib.mat('pee_beakU', '#f6a820', 0.22, coat=1.0, sss=0.1)
    beakL = lib.mat('pee_beakL', '#c87810', 0.25, coat=1.0)
    legm = lib.mat('pee_leg', '#e09418', 0.35, coat=0.6, sss=0.1)
    pink = lib.mat('pee_cheek', '#ff8f84', 0.6, sss=0.3, emit=0.15)
    shine = lib.mat('pee_shine', '#ffffff', 0.1, emit=2.5)
    H = math.pi / 2

    # a couple of shed downy feathers on the ground (stay put while it hops about)
    for i, (x, y, a) in enumerate([(-0.42, -0.2, 0.6), (0.36, 0.3, -1.1)]):
        lib.extrude_shape(f'pee_down{i}', blade(0.17, 0.08), 0.012, cream if i else light, rig.root, loc=(x, y, 0.012),
                          rot=(H - 0.08, 0, a), bevel=0.004)

    rig.body = lib.pivot('pee_bodyp', (0, 0, 0.44), rig.root)
    bt = lib.pivot('pee_bodyt', (0, 0, 0), rig.body, rot=(-0.22, 0, 0))     # body tilted chest-up
    C, R = (0, 0.04, 0), (0.3, 0.37, 0.285)
    lib.sphere('pee_body', C, R, tan, bt, seg=40)
    patch(lib, 'pee_belly', C, R, (0, -0.55, -1), 0.95, 0.8, cream, bt, k=1.01)
    patch(lib, 'pee_back', C, R, (0, 0.5, 1), 0.75, 0.9, brown, bt, k=1.008)
    # fluffy bib: soft scallops where the cream belly meets the chest
    for i, (x, z, r) in enumerate([(-0.5, -0.5, 0.055), (-0.25, -0.4, 0.062), (0, -0.36, 0.066), (0.25, -0.4, 0.062), (0.5, -0.5, 0.055)]):
        lib.sphere(f'pee_bib{i}', on(C, R, (x, -1, z), 0.97), (r, r * 0.7, r * 1.1), cream, bt, seg=14)
    # rump blending into the tail
    lib.sphere('pee_rump', (0, 0.3, 0.07), (0.17, 0.2, 0.14), brown, rig.body, seg=24)

    # ---- head (big, for charm)
    rig.head = lib.pivot('pee_headp', (0, -0.2, 0.2), rig.body)
    HC, HR = (0, -0.06, 0.19), (0.265, 0.26, 0.25)
    lib.sphere('pee_head', HC, HR, tan, rig.head, seg=40)
    patch(lib, 'pee_cap', HC, HR, (0, 0.35, 1), 0.8, 0.85, brown, rig.head, k=1.008)
    patch(lib, 'pee_face', HC, HR, (0, -1, -0.5), 0.72, 0.5, light, rig.head, k=1.008)
    rig.eyes = []
    for sx, nm in ((-1, 'L'), (1, 'R')):
        look = (sx * 0.6, -0.8, 0.1)
        e = lib.eye('pee_eye' + nm, on(HC, HR, (sx * 0.56, -0.83, 0.12), 0.93), 0.092, rig.head,
                    iris='#6a3814', pupil='#0a0604', sclera='#1a0f08', look=look, iris_frac=0.8, flat=0.42)
        e.scale = (0.92, 1, 1.12)
        lib.sphere('pee_shine2' + nm, (0.032, -0.04, -0.03), (0.011, 0.006, 0.011), shine, e, seg=8)
        rig.eyes.append(e)
        patch(lib, 'pee_cheek' + nm, HC, HR, (sx * 0.62, -0.78, -0.42), 0.19, 0.13, pink, rig.head, k=1.014, rings=3, seg=16)
        # cheek fluff
        for j, (dz, L) in enumerate([(-0.3, 0.1), (-0.5, 0.08)]):
            b0 = Vector(on(HC, HR, (sx * 1, -0.25, dz), 0.9))
            lib.tube(f'pee_fluff{nm}{j}', [b0, b0 + Vector((sx * L * 0.6, 0.01, -0.01)), b0 + Vector((sx * L, 0.03, -0.04 - j * 0.02))],
                     [0.05, 0.035, 0.004], tan, rig.head, seg=8)
    # tuft
    rig.tuft = lib.pivot('pee_tuftp', (0, HC[1], HC[2] + HR[2] - 0.04), rig.head)
    for i, (dx, dy, L) in enumerate([(0, -0.03, 0.24), (-0.035, 0.03, 0.16), (0.04, 0.05, 0.19)]):
        lib.tube(f'pee_tuft{i}', [(dx, dy, 0), (dx * 2, dy + 0.0, L * 0.55), (dx * 3.2, dy + 0.11, L)],
                 [0.045, 0.034, 0.005], brown, rig.tuft)
    # beak: upper half fixed, lower half on the jaw hinge
    by = HC[1] - HR[1] + 0.04
    ub = lib.cone('pee_beakU', (0, by - 0.11, HC[2] - 0.035), 0.09, 0.004, 0.27, beakU, rig.head, rot=(H + 0.1, 0, 0), seg=20, subsurf=1)
    ub.scale = (1, 0.62, 1)
    rig.jaw = lib.pivot('pee_jaw', (0, by + 0.02, HC[2] - 0.072), rig.head)
    lb = lib.cone('pee_beakL', (0, -0.11, -0.008), 0.08, 0.004, 0.23, beakL, rig.jaw, rot=(H - 0.08, 0, 0), seg=20, subsurf=1)
    lb.scale = (1, 0.42, 1)

    # ---- folded wings: hinge along the shoulder, they swing out sideways to flap
    for sx, nm in ((-1, 'L'), (1, 'R')):
        w = lib.pivot('pee_wing' + nm, (sx * 0.235, 0.0, 0.1), rig.body, rot=(0, -sx * 0.06, 0))
        lib.sphere('pee_wingm' + nm, (sx * 0.02, 0.14, -0.1), (0.055, 0.26, 0.165), brown, w, rot=(-0.3, 0, 0), seg=24)
        lib.sphere('pee_wingbar' + nm, (sx * 0.05, 0.1, -0.075), (0.03, 0.15, 0.05), light, w, rot=(-0.3, 0, 0), seg=16)
        for i, (y, z, L, a) in enumerate([(0.18, -0.19, 0.24, -1.95), (0.22, -0.14, 0.27, -1.75), (0.24, -0.08, 0.26, -1.58), (0.24, -0.03, 0.2, -1.42)]):
            f = lib.extrude_shape(f'pee_wingf{nm}{i}', blade(L, 0.1), 0.02, dbrown, w, loc=(sx * 0.058, y, z), bevel=0.006)
            f.rotation_mode = 'ZYX'            # turn the blade flat against the side, then swing its tip back
            f.rotation_euler = (a, 0, H)
        rig.wings.append((w, sx))

    # ---- tail
    t0 = lib.pivot('pee_tail0', (0, 0.36, 0.1), rig.body)
    t1 = lib.pivot('pee_tail1', (0, 0.08, 0.03), t0)
    for i, (yaw, L, m) in enumerate([(0, 0.46, brown), (-0.4, 0.4, dbrown), (0.4, 0.4, dbrown)]):
        lib.extrude_shape(f'pee_tailf{i}', blade(L, 0.17), 0.025, m, t1,
                          loc=(0, -0.06, 0.004 * (1 if i == 0 else 0)), rot=(-H + 0.62, 0, yaw), bevel=0.008)
    rig.tail = [t0, t1]

    # ---- legs
    for i, sx in enumerate((-1, 1)):
        leg = lib.pivot(f'pee_leg{i}', (sx * 0.11, 0.06, -0.2), rig.body)
        g = -0.24 + 0.022
        lib.tube(f'pee_legm{i}', [(0, 0, 0.03), (0, 0.01, -0.1), (0, 0, g)], [0.03, 0.022, 0.022], legm, leg, seg=8)
        for j, (tx, ty) in enumerate([(0, -0.15), (-0.08, -0.12), (0.08, -0.12), (0, 0.08)]):
            lib.tube(f'pee_toe{i}{j}', [(0, 0, g), (tx * 0.5, ty * 0.5, g + 0.012), (tx, ty, g - 0.002)], [0.024, 0.021, 0.012], legm, leg, seg=8)
        rig.legs.append((leg, i * 0.5))

    rig.attack_origin = (0, -0.75, 0.8)
    rig.t_pose = {'pee_wingL': (0, 1.35, 0), 'pee_wingR': (0, -1.35, 0)}
    return rig


# ------------------------------------------------------------------ animation
def animate(A):
    """Peeplet: a fluttery, bouncy, slightly over-confident little songbird."""
    lib, r, T, s = A.lib, A.rig, A.T, A.size
    root, body, head, jaw = r.root, r.body, r.head, r.jaw
    t0, t1 = r.tail
    wave, ease = A.wave, A.ease
    TAU = 2 * math.pi

    def wings(f, a, flap=0.0):
        """a = how far open (0 folded, 1.3 spread); flap adds per-wing variation."""
        for w, side in r.wings:
            A.key(w, f, rot=(0, -side * max(0.0, a + flap), 0))

    def eyes(f, z):
        for e in r.eyes:
            A.key(e, f, scale=(1, 1, z))

    def blink(f):
        eyes(f - 1, 1); eyes(f + 1, 0.1); eyes(f + 3, 1)

    def hide(o, f0, f1, loc):
        A.key(o, 0, loc=loc, scale=0.001, absolute=True)
        A.key(o, f0 - 1, loc=loc, scale=0.001, absolute=True)
        return o

    # ---------- effect props
    note_m = lib.mat('pee_note', '#fff3b0', 0.3, emit=3.0, emit_color='#ffe060')
    spark_m = lib.mat('pee_spark', '#ffffff', 0.3, emit=5.0, emit_color='#fff6c0')
    fth_m = lib.mat('pee_loose', '#c98d48', 0.7)

    def note(i, f0, origin, drift, life=16, big=1.0):
        p = lib.pivot(f'pee_note{i}')
        k = 0.075 * s * big
        lib.sphere(f'pee_noteh{i}', (0, 0, 0), (k, k * 0.6, k * 0.75), note_m, p, rot=(0, 0.4, 0), seg=12)
        lib.cylinder(f'pee_notes{i}', (k * 0.85, 0, k * 1.5), k * 0.14, k * 3, note_m, p, seg=8)
        lib.box(f'pee_notef{i}', (k * 1.35, 0, k * 2.6), (k * 1.1, k * 0.25, k * 0.55), note_m, p, rot=(0, 0.5, 0), bevel=k * 0.08)
        o = Vector(origin)
        hide(p, f0, f0 + life, o)
        for j in range(life + 1):
            u = j / life
            pos = o + Vector(drift) * u + Vector((math.sin(u * 7 + i) * 0.07 * s, 0, 0))
            sc = min(1.0, j / 3) * (1.0 if u < 0.7 else max(0.001, (1 - u) / 0.3))
            A.key(p, f0 + j, loc=pos, rot=(0, math.sin(u * 9 + i) * 0.35, -0.5), scale=max(sc, 0.001), absolute=True)
        return p

    def star(i, f0, pos, size=1.0):
        p = lib.pivot(f'pee_star{i}')
        pts = []
        for j in range(8):
            a = j * TAU / 8
            rr = (0.16 if j % 2 == 0 else 0.055) * s * size
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
        lib.extrude_shape(f'pee_starm{i}', pts, 0.02 * s, spark_m, p, bevel=0.004, subsurf=0)
        hide(p, f0, f0 + 5, pos)
        A.key(p, f0, loc=pos, scale=0.4, rot=(0, 0, -0.49), absolute=True)          # yawed to face the camera
        A.key(p, f0 + 2, loc=pos, scale=1.7, rot=(0, 0.9, -0.49), absolute=True)
        A.key(p, f0 + 5, loc=pos, scale=0.001, rot=(0, 1.6, -0.49), absolute=True)

    # ================= send-out (16-48): tumbles out as a fluff ball, flutters down, lands with a bounce, sings
    A.key(root, 0, scale=0.001, loc=(0, 0, 0), rot=(0, 0, 0)); A.key(root, 16, scale=0.001)
    A.key(root, 18, scale=0.7); A.key(root, 21, scale=1.08); A.key(root, 24, scale=1.0)
    for f in A.frames(16, 40):
        if f <= 32:
            u = (f - 16) / 16
            z = (0.12 + 2.3 * u * (1 - u) + (0.0 if u < 0.5 else -0.12 * (u - 0.5) * 2)) * s * 0.5
            z = max(z, 0) if f < 32 else 0
            y = -0.22 * s * (1 - ease(u))
            spin = -TAU * (1 - ease(min(1, u / 0.7)))                 # one somersault, done by the time it flutters
            A.key(body, f, loc=(0, y, z), rot=(spin, 0, math.sin(u * 9) * 0.15), scale=(1, 1, 1))
            wings(f, 0.75, 0.55 * wave(f, 3))
        elif f <= 34:
            A.key(body, f, loc=(0, 0, -0.07 * s), rot=(0.12, 0, 0), scale=(1.2, 1.2, 0.72))   # splat-squash
            wings(f, 0.9)
        elif f <= 37:
            A.key(body, f, loc=(0, 0, 0.07 * s), rot=(-0.05, 0, 0), scale=(0.92, 0.92, 1.14))
            wings(f, 0.3)
        else:
            A.key(body, f, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1))
            wings(f, 0.0)
    for leg, ph in r.legs:
        A.key(leg, 16, rot=(0.9, 0, 0)); A.key(leg, 28, rot=(0.9, 0, 0)); A.key(leg, 32, rot=(-0.35, 0, 0)); A.key(leg, 36, rot=(0, 0, 0))
    eyes(16, 0.12); eyes(31, 0.12); eyes(35, 1.15); eyes(38, 1)         # eyes scrunched shut in the tumble
    A.key(t0, 32, rot=(0, 0, 0)); A.key(t0, 34, rot=(0.7, 0, 0)); A.key(t0, 39, rot=(-0.15, 0, 0)); A.key(t0, 42, rot=(0, 0, 0))
    A.key(r.tuft, 30, rot=(0, 0, 0)); A.key(r.tuft, 34, rot=(-0.6, 0, 0)); A.key(r.tuft, 38, rot=(0.3, 0, 0)); A.key(r.tuft, 42, rot=(0, 0, 0))
    # the cry: chest out, head thrown back, two chirps with notes floating up
    A.key(head, 16, rot=(0, 0, 0)); A.key(head, 38, rot=(0.15, 0, 0)); A.key(head, 41, rot=(-0.55, 0.12, 0))
    A.key(head, 43, rot=(-0.4, 0.1, 0)); A.key(head, 45, rot=(-0.62, -0.12, 0)); A.key(head, 48, rot=(-0.5, -0.1, 0)); A.key(head, 51, rot=(0, 0, 0))
    for f, a in [(16, 0), (39, 0), (41, 0.75), (43, 0.1), (45, 0.8), (48, 0.6), (50, 0)]:
        A.key(jaw, f, rot=(a, 0, 0))
    A.key(body, 41, scale=(1.06, 1.06, 1.1), rot=(-0.14, 0, 0), loc=(0, 0, 0.02 * s))
    A.key(body, 43, scale=(1, 1, 1.02), rot=(-0.1, 0, 0), loc=(0, 0, 0))
    A.key(body, 45, scale=(1.07, 1.07, 1.12), rot=(-0.16, 0, 0), loc=(0, 0, 0.025 * s))
    A.key(body, 50, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0))
    wings(40, 0); wings(41, 0.35); wings(43, 0.1); wings(45, 0.45); wings(49, 0)
    beak = A.world(head, 41, (0, -0.5, 0.2))
    note(0, 41, beak, (-0.25 * s, -0.1 * s, 0.55 * s), 18)
    beak = A.world(head, 45, (0, -0.5, 0.2))
    note(1, 45, beak, (0.3 * s, -0.15 * s, 0.6 * s), 18, 1.2)

    # ================= idle (48-72): bird-quick head snaps, blink, tail flick, a little feather ruffle
    for f, rot in [(53, (0, 0, 0)), (55, (0.05, 0.38, 0.25)), (60, (0.05, 0.38, 0.25)), (62, (-0.08, -0.34, -0.3)),
                   (67, (-0.08, -0.34, -0.3)), (69, (0, 0, 0)), (72, (0, 0, 0))]:
        A.key(head, f, rot=rot)
    blink(57); blink(65)
    for f, a in [(58, 0), (60, 0.5), (62, -0.1), (64, 0.4), (66, 0)]:
        A.key(t0, f, rot=(a, 0, 0)); A.key(t1, f + 1, rot=(a * 0.6, 0, 0))
    for f in A.frames(50, 72, 2):
        br = 1 + 0.025 * wave(f, 14)
        A.key(body, f, scale=(br, br, 2 - br), loc=(0, 0, 0), rot=(0, 0, 0))
    A.key(r.tuft, 55, rot=(0, 0.25, 0)); A.key(r.tuft, 58, rot=(0, -0.08, 0)); A.key(r.tuft, 62, rot=(0, -0.25, 0)); A.key(r.tuft, 66, rot=(0, 0.05, 0)); A.key(r.tuft, 70, rot=(0, 0, 0))

    # ================= walk (72-138): two-footed songbird hops with squash and stretch
    dist = 1.5 * s
    nh, hop_len, f_start = 5, 10, 78
    for f in A.frames(72, 78):                                       # hop-turn to the right
        u = ease((f - 72) / 6)
        A.key(root, f, loc=(0, 0, 0), rot=(0, 0, u * math.pi / 2))
        hz = math.sin(math.pi * (f - 72) / 6) * 0.1 * s
        A.key(body, f, loc=(0, 0, hz), rot=(0, 0, 0), scale=(1, 1, 1))
        wings(f, 0.35 * math.sin(math.pi * (f - 72) / 6))
    for f in A.frames(f_start, f_start + nh * hop_len):
        i = min(nh - 1, (f - f_start) // hop_len)
        t = (f - f_start - i * hop_len) / hop_len
        if f == f_start + nh * hop_len:
            i, t = nh - 1, 1.0
        big = 1.35 if i == nh - 1 else 1.0                             # last hop is a showy fluttering one
        if t < 0.3:
            q = math.sin(math.pi * t / 0.3)
            x = i * dist / nh
            A.key(root, f, loc=(x, 0, 0), rot=(0, 0, math.pi / 2))
            A.key(body, f, loc=(0, 0, -0.07 * s * q), rot=(0.16 * q, 0, 0), scale=(1 + 0.16 * q, 1 + 0.16 * q, 1 - 0.24 * q))
            A.key(head, f, rot=(-0.1 * q, (0.3 if i % 2 else -0.3) * (1 - q), 0))
            wings(f, 0.0)
            for leg, ph in r.legs:
                A.key(leg, f, rot=(-0.25 * (1 - q), 0, 0))
            A.key(t0, f, rot=(0.45 * q, 0, 0)); A.key(t1, f, rot=(0.3 * q, 0, 0))
            A.key(r.tuft, f, rot=(0.35 * q, 0, 0))
        else:
            u = (t - 0.3) / 0.7
            x = (i + ease(u) * 0.3 + u * 0.7) * dist / nh
            h = 4 * u * (1 - u) * 0.3 * s * big
            st = math.sin(math.pi * u)
            A.key(root, f, loc=(x, 0, 0), rot=(0, 0, math.pi / 2))
            A.key(body, f, loc=(0, 0, h), rot=(-0.24 * math.cos(math.pi * u), 0, 0), scale=(1 - 0.07 * st, 1 - 0.07 * st, 1 + 0.14 * st))
            A.key(head, f, rot=(0.2 * math.cos(math.pi * u), (0.3 if i % 2 else -0.3) * u, 0))
            wings(f, 0.55 * st * big, (0.3 * wave(f, 3)) if big > 1 else 0)
            for leg, ph in r.legs:
                A.key(leg, f, rot=(0.75 * math.cos(math.pi * u) - 0.1, 0, 0))
            A.key(t0, f, rot=(-0.3 * st, 0, 0)); A.key(t1, f, rot=(-0.2 * st, 0, 0))
            A.key(r.tuft, f, rot=(-0.4 * math.cos(math.pi * u), 0, 0))
    fe = f_start + nh * hop_len                                       # 128
    for f in A.frames(fe, 138):                                       # skip-turn back to the camera
        u = ease((f - fe) / 9)
        A.key(root, f, loc=(dist, 0, 0), rot=(0, 0, (1 - u) * math.pi / 2))
        hz = math.sin(math.pi * min(1, (f - fe) / 9)) * 0.12 * s
        A.key(body, f, loc=(0, 0, hz), rot=(0, 0, 0), scale=(1, 1, 1))
        A.key(head, f, rot=(0, 0, 0))
        wings(f, 0.4 * math.sin(math.pi * min(1, (f - fe) / 9)))
        for leg, ph in r.legs:
            A.key(leg, f, rot=(0.4 * math.sin(math.pi * min(1, (f - fe) / 9)), 0, 0))
        A.key(t0, f, rot=(0, 0, 0)); A.key(t1, f, rot=(0, 0, 0)); A.key(r.tuft, f, rot=(0, 0, 0))
    blink(96); blink(118)

    # ================= attack (140-186): Quick Attack dash into a triple Peck, then a backwards flutter home
    here = Vector((dist, 0, 0))
    opp = A.opponent(here) - here
    phi = math.atan2(opp.x, -opp.y)                                    # yaw that faces the opponent
    dirv = Vector((opp.x, opp.y, 0)).normalized()
    D = math.hypot(opp.x, opp.y) - 1.5 * s                             # as far as it can go and stay on camera
    zt = 0.22 * s

    def place(f, along, z, pitch=0.0, roll=0.0, scale=(1, 1, 1), yaw=1.0):
        """Fly the bird `along` meters toward the opponent; the root (and so the camera) leads in x."""
        P = dirv * along
        cx = P.x + 0.5 * s * max(0.0, min(1.0, along / max(D, 1e-6)))
        A.key(root, f, loc=(here.x + cx, 0, 0), rot=(0, 0, 0))
        A.key(body, f, loc=(P.x - cx, P.y, z), rot=(pitch, roll, phi * yaw), scale=scale)

    # anticipation: crouch, wiggle the tail, narrow the eyes
    for f in A.frames(140, 150):
        u = ease((f - 140) / 6)
        place(f, -0.1 * s * u, -0.08 * s * u, 0.3 * u, 0, (1 + 0.1 * u, 1 + 0.1 * u, 1 - 0.18 * u), yaw=ease((f - 140) / 5))
        A.key(head, f, rot=(-0.3 * u, 0, 0))
        A.key(t0, f, rot=(0.5 * u, 0, 0.45 * wave(f, 4) * u)); A.key(t1, f, rot=(0.2 * u, 0, 0.3 * wave(f, 4, -0.2) * u))
        wings(f, 0.25 * u)
        for leg, ph in r.legs:
            A.key(leg, f, rot=(-0.3 * u, 0, 0))
    eyes(140, 1); eyes(143, 0.55); eyes(156, 0.55); eyes(158, 1.1)
    # dash
    for f in A.frames(151, 157):
        u = (f - 150) / 7
        e = u * u * (3 - 2 * u)
        place(f, D * e, zt * e + 0.1 * s * math.sin(math.pi * u), 0.35 * (1 - u), 0,
              (0.84, 1.32, 0.84) if f < 157 else (1.1, 0.85, 1.1))
        A.key(head, f, rot=(-0.2, 0, 0))
        wings(f, 1.05)
        for leg, ph in r.legs:
            A.key(leg, f, rot=(1.0, 0, 0))
        A.key(t0, f, rot=(-0.15, 0, 0)); A.key(t1, f, rot=(0, 0, 0))
    # speed lines trailing behind it
    for i, (x, z, L) in enumerate([(-0.2, 0.12, 1.1), (0.22, 0.05, 0.9), (0.0, 0.3, 1.3), (-0.1, -0.12, 0.8), (0.14, -0.08, 1.0)]):
        ln = lib.tube(f'pee_speed{i}', [(x, 0.35, z), (x, 0.35 + L * 0.5, z), (x, 0.35 + L, z)], [0.022, 0.016, 0.002], spark_m, body, seg=8)
        for f, sc in [(0, 0.001), (150, 0.001), (152, 1.0), (155, 1.1), (157, 0.3), (158, 0.001)]:
            A.key(ln, f, scale=(1, sc, 1) if sc > 0.01 else 0.001)
    # three pecks
    pecks = [159, 163, 167]
    for f in A.frames(158, 170):
        hov = 0.03 * s * wave(f, 4)
        jab = max([1 - abs(f - p) / 2 for p in pecks] + [0])
        place(f, D + 0.12 * s * jab - 0.05 * s, zt + hov, 0.25 * jab - 0.1, 0.12 * wave(f, 8))
        A.key(head, f, rot=(0.75 * jab - 0.35, 0, 0))
        A.key(jaw, f, rot=(0.25 * (1 - jab), 0, 0))
        wings(f, 1.0, 0.6 * wave(f, 3))
        for leg, ph in r.legs:
            A.key(leg, f, rot=(0.5 + 0.2 * wave(f, 4, ph), 0, 0))
        A.key(t0, f, rot=(0.3 * jab, 0, 0))
    hitp = here + dirv * (D + 0.72 * s) + Vector((0, 0, 0.44 + zt + 0.12 * s))
    for i, p in enumerate(pecks):
        off = Vector(((i - 1) * 0.08 * s, 0, (0.08 if i != 1 else -0.06) * s))
        star(i, p, hitp + off, 0.8 + 0.25 * i)
    A.light('pee_peckl', '#fff0b0', hitp + Vector((-0.2 * s, -0.2 * s, 0.1 * s)),
            [(0, 0), (158, 0), (159, 300 * s * s), (161, 0), (163, 350 * s * s), (165, 0), (167, 450 * s * s), (171, 0)])
    # flutter home backwards, pleased with itself
    for f in A.frames(171, 184):
        u = (f - 170) / 13
        e = ease(u)
        land = f >= 183
        place(f, D * (1 - e), zt * (1 - e) + 0.3 * s * math.sin(math.pi * u), -0.3 * math.sin(math.pi * u), 0,
              (1.12, 1.12, 0.82) if land else (1, 1, 1), yaw=1 - ease((f - 174) / 9))
        A.key(head, f, rot=(-0.1 * math.sin(math.pi * u), 0, 0))
        A.key(jaw, f, rot=(0, 0, 0))
        wings(f, 0.0 if land else 0.8, 0 if land else 0.5 * wave(f, 3))
        for leg, ph in r.legs:
            A.key(leg, f, rot=(-0.5 * u if not land else 0, 0, 0))
        A.key(t0, f, rot=(0.4 * math.sin(math.pi * u), 0, 0))
    A.key(body, 186, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)); wings(186, 0)
    A.key(root, 186, rot=(0, 0, 0), loc=here)
    A.key(jaw, 186, rot=(0, 0, 0)); A.key(head, 186, rot=(0, 0, 0)); A.key(t0, 186, rot=(0, 0, 0)); A.key(t1, 186, rot=(0, 0, 0))
    for leg, ph in r.legs:
        A.key(leg, 186, rot=(0, 0, 0))

    # ================= hit (186-206): bowled over backwards in a puff of feathers, ends up sat on its tail
    back = 0.55 * s
    for f in A.frames(187, 199):
        u = (f - 186) / 13
        A.key(body, f, loc=(0, back * (1 - (1 - u) ** 2), 0.3 * s * math.sin(math.pi * u) - 0.1 * s * u),
              rot=(-TAU * ease(u) - 0.45 * u, 0, 0.2 * math.sin(u * 6)),
              scale=1.18 if f < 190 else 1.0)
        wings(f, 0.9, 0.4 * wave(f, 4))
        for leg, ph in r.legs:
            A.key(leg, f, rot=(-1.1 * u, 0, 0))
        A.key(head, f, rot=(0.3 * u, 0, 0))
    eyes(186, 1); eyes(187, 0.12); eyes(200, 0.12)
    A.key(jaw, 187, rot=(0.6, 0, 0)); A.key(jaw, 198, rot=(0.3, 0, 0)); A.key(jaw, 204, rot=(0, 0, 0))
    for f in A.frames(200, 206):                                       # sat dazed, head rolling
        q = (f - 200) / 6
        A.key(body, f, loc=(0, back, -0.1 * s), rot=(-TAU - 0.45, 0, 0), scale=(1 + 0.05 * (1 - q), 1 + 0.05 * (1 - q), 1 - 0.08 * (1 - q)))
        A.key(head, f, rot=(0.3 + 0.12 * math.cos(q * TAU), 0.25 * math.sin(q * TAU), 0))
        wings(f, 0.5 * (1 - q) + 0.15)
    eyes(203, 0.7); eyes(205, 0.2); eyes(207, 1)
    A.key(r.tuft, 187, rot=(0.6, 0, 0)); A.key(r.tuft, 199, rot=(-0.5, 0, 0)); A.key(r.tuft, 203, rot=(0.3, 0, 0)); A.key(r.tuft, 207, rot=(0, 0.3, 0))
    # loose feathers knocked out of it
    src = here + Vector((0, 0.1 * s, 0.5 * s))
    for i in range(6):
        p = lib.pivot(f'pee_loose{i}')
        lib.extrude_shape(f'pee_loosem{i}', blade(0.16 * s, 0.07 * s), 0.01, fth_m, p, bevel=0.003)
        a = i * TAU / 6 + 0.4
        out = Vector((math.cos(a) * 0.55 * s, -0.15 * s + math.sin(a) * 0.3 * s, (0.35 + 0.2 * (i % 3)) * s))
        hide(p, 187, 220, src)
        A.key(p, 187, loc=src, rot=(0, 0, a), scale=1, absolute=True)
        A.key(p, 192, loc=src + out, rot=(1.5 + i, 0.7 * i, a + 1), scale=1, absolute=True)
        for j in range(1, 6):
            ff = 192 + j * 4
            dn = src + out + Vector((math.sin(j * 1.7 + i) * 0.12 * s, 0, 0))
            dn.z = max(0.02, (src + out).z * (1 - j / 5))
            A.key(p, ff, loc=dn, rot=(1.5 + i + 0.6 * math.sin(j * 2 + i), 0.7 * i + j * 0.5, a + 1 + j * 0.4), scale=1, absolute=True)
        A.key(p, 220, scale=1); A.key(p, 226, scale=0.001)

    # ================= recover (206-230): ruffle-shake, spring back up, puff the chest and chirp defiantly
    for f in A.frames(207, 213):
        sh = wave(f, 3) * (1 - (f - 207) / 8)
        A.key(body, f, loc=(0, back, -0.1 * s + 0.02 * s), rot=(-TAU - 0.45 + 0.1, 0, 0.3 * sh), scale=1.1)
        A.key(head, f, rot=(0.1, -0.4 * sh, 0))
        wings(f, 0.45 + 0.2 * sh)
        A.key(t0, f, rot=(0, 0, 0.4 * sh))
    for f in A.frames(214, 220):                                       # spring up and hop back to its mark
        u = (f - 213) / 7
        A.key(body, f, loc=(0, back * (1 - ease(u)), -0.1 * s * (1 - u) + 0.3 * s * math.sin(math.pi * u)),
              rot=(-TAU - 0.45 * (1 - ease(u)), 0, 0), scale=(1 - 0.06 * math.sin(math.pi * u), 1 - 0.06 * math.sin(math.pi * u), 1 + 0.12 * math.sin(math.pi * u)))
        A.key(head, f, rot=(0, 0, 0))
        wings(f, 0.7 * math.sin(math.pi * u), 0.3 * wave(f, 3))
        for leg, ph in r.legs:
            A.key(leg, f, rot=(-1.1 * (1 - ease(u)), 0, 0))
        A.key(t0, f, rot=(0, 0, 0))
    A.key(body, 221, loc=(0, 0, -0.05 * s), rot=(-TAU + 0.08, 0, 0), scale=(1.14, 1.14, 0.8)); wings(221, 0.1)
    A.key(body, 224, loc=(0, 0, 0.03 * s), rot=(-TAU - 0.2, 0, 0), scale=(1.08, 1.08, 1.12))
    A.key(body, 230, loc=(0, 0, 0.02 * s), rot=(-TAU - 0.16, 0, 0), scale=(1.06, 1.06, 1.08))
    A.key(head, 221, rot=(0.15, 0, 0)); A.key(head, 224, rot=(-0.55, 0.1, 0)); A.key(head, 230, rot=(-0.48, 0.08, 0))
    A.key(jaw, 221, rot=(0, 0, 0)); A.key(jaw, 224, rot=(0.8, 0, 0)); A.key(jaw, 230, rot=(0.65, 0, 0))
    wings(224, 0.95); wings(227, 0.75); wings(230, 0.85)
    A.key(t0, 221, rot=(0, 0, 0)); A.key(t0, 224, rot=(0.6, 0, 0)); A.key(t0, 230, rot=(0.5, 0, 0))
    A.key(r.tuft, 221, rot=(0.4, 0, 0)); A.key(r.tuft, 225, rot=(-0.3, 0, 0)); A.key(r.tuft, 230, rot=(-0.1, 0, 0))
    eyes(222, 1); eyes(224, 0.45); eyes(230, 0.45)                     # happy squint
    beak = A.world(head, 224, (0, -0.5, 0.2))
    note(2, 224, beak, (-0.2 * s, -0.1 * s, 0.45 * s), 12, 1.3)


# Phase speeds for render.retime: above 1 is slower and longer, below 1 is quicker.
TIMING = {'send': 1.0, 'idle': 1.0, 'walk': 0.85, 'attack': 1.1, 'hit': 1.0, 'recover': 1.0}
