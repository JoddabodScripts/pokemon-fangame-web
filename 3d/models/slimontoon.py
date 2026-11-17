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
