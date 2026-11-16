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
    lib.sphere('sli_puddle', (0, 0, 0.012), (0.78, 0.66, 0.03), puddle, rig.root)
    lib.sphere('sli_puddle2', (-0.52, -0.22, 0.01), (0.3, 0.24, 0.025), puddle, rig.root)
    lib.sphere('sli_puddle3', (0.5, 0.3, 0.01), (0.34, 0.26, 0.025), puddle, rig.root)
    lib.sphere('sli_puddle4', (0.62, -0.42, 0.008), (0.1, 0.09, 0.02), puddle, rig.root)

    rig.body = lib.pivot('sli_bodyp', (0, 0, 0), rig.root)
    C, R = (0, 0, 0.47), (0.64, 0.6, 0.5)
    lib.sphere('sli_body', C, R, slime, rig.body, seg=48)

    # concentric ring seen inside it
    fd = (0, -1, -0.08)
    patch(lib, 'sli_ringA', C, R, fd, 0.80, 0.76, ring1, rig.body, k=1.004)
    patch(lib, 'sli_ringB', C, R, fd, 0.64, 0.60, ring2, rig.body, k=1.008)
    patch(lib, 'sli_ringC', C, R, (-0.06, -1, -0.02), 0.42, 0.38, ring3, rig.body, k=1.012)

    # gloss streak and bubbles
    patch(lib, 'sli_gloss', C, R, (-0.62, -0.62, 0.52), 0.07, 0.2, gloss, rig.body, k=1.014, rings=3, seg=16)
    patch(lib, 'sli_gloss2', C, R, (-0.5, -0.6, 0.72), 0.06, 0.06, gloss, rig.body, k=1.014, rings=3, seg=16)
    for i, (d, s) in enumerate([((-0.42, -0.75, -0.62), 0.045), ((0.5, -0.75, -0.42), 0.03), ((0.38, -0.7, -0.68), 0.025),
                                ((0.7, 0.3, 0.5), 0.04), ((-0.5, 0.7, 0.3), 0.03)]):
        lib.sphere(f'sli_bub{i}', on(C, R, d, 0.99), s, bub, rig.body, seg=12)

    # face
    for sx, nm in ((-1, 'L'), (1, 'R')):
        e = lib.eye('sli_eye' + nm, on(C, R, (sx * 0.27, -1, 0.14), 0.99), 0.11, rig.body,
                    iris='#1c3470', pupil='#0e1a3a', sclera='#0e1a3a', look=(sx * 0.2, -1, 0.1), iris_frac=0.7)
        e.scale = (0.85, 1, 1.3)
        patch(lib, 'sli_cheek' + nm, C, R, (sx * 0.6, -1, -0.14), 0.12, 0.075, pink, rig.body, k=1.014, rings=3, seg=16)
    pts = [on(C, R, (x, -1, z), 1.012) for x, z in [(-0.17, -0.19), (-0.09, -0.25), (0, -0.27), (0.09, -0.25), (0.17, -0.19)]]
    lib.tube('sli_mouth', pts, [0.012, 0.018, 0.018, 0.018, 0.012], dark, rig.body, seg=8)

    # drips sliding down its sides: teardrops that hug the surface
    for i, (d, r) in enumerate([((-0.93, -0.36, -0.42), 0.085), ((0.86, -0.5, -0.52), 0.06), ((0.55, 0.83, -0.4), 0.07)]):
        base = Vector(on(C, R, d, 0.97))
        top = Vector(on(C, R, (d[0], d[1], d[2] + 0.55), 0.97))
        lib.sphere(f'sli_drip{i}', base, (r, r, r * 1.15), slime, rig.body, seg=16)
        lib.tube(f'sli_dript{i}', [base, base.lerp(top, 0.5), top], [r * 0.85, r * 0.5, r * 0.15], slime, rig.body)

    rig.attack_origin = (0, -0.65, 0.5)
    return rig
