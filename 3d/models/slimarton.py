"""Slimarton: slime core with a face and five beaded starfish arms."""
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
    rig = lib.Rig('Slimarton', 'slimarton', 'Water', height_cm=130, gait='hop', attack='slam')
    slime = lib.mat('sla_slime', '#2a6cd0', 0.12, sss=0.2, coat=0.8)
    beadA = lib.mat('sla_beadA', '#6aa8f0', 0.12, sss=0.2, coat=0.8)
    beadB = lib.mat('sla_beadB', '#2c6cc4', 0.12, sss=0.2, coat=0.8)
    ring1 = lib.mat('sla_ring1', '#1e52a6', 0.2, sss=0.1, coat=0.8)
    ring2 = lib.mat('sla_ring2', '#6aa8f0', 0.15, sss=0.15, coat=0.8)
    gloss = lib.mat('sla_gloss', '#e8f4ff', 0.1, emit=0.6, coat=1.0)
    dark = lib.mat('sla_dark', '#0e1a3a', 0.3)
    pink = lib.mat('sla_cheek', '#ff9ac0', 0.5, sss=0.3)

    CZ, CR = 0.90, 0.38
    rig.body = lib.pivot('sla_bodyp', (0, 0, 0), rig.root)
    C, R = (0, 0, CZ), (CR, CR * 0.9, CR)
    lib.sphere('sla_core', C, R, slime, rig.body, seg=40)

    # five beaded arms: up, upper pair, lower pair (it stands on the lower pair)
    radii = [0.15, 0.128, 0.11, 0.092]
    for k, a in enumerate([90, 18, -54, -126, 162]):
        ar = math.radians(a)
        d0 = CR - 0.06
        arm = lib.pivot(f'sla_arm{k}', (math.cos(ar) * d0, 0, CZ + math.sin(ar) * d0), rig.body,
                        rot=(0, math.pi / 2 - ar, 0))
        z = 0.11
        for j, r in enumerate(radii):
            lib.sphere(f'sla_arm{k}_b{j}', (0, 0, z), (r, r * 0.92, r), beadA if j % 2 == 0 else beadB, arm, seg=20)
            lib.sphere(f'sla_arm{k}_g{j}', (-r * 0.45, -r * 0.72, z + r * 0.4), r * 0.16, gloss, arm, seg=8)
            if j + 1 < len(radii):
                z += (r + radii[j + 1]) * 0.78
        rig.arms.append((arm, (k * 0.4) % 1.0))

    # ring inside the core
    fd = (0, -1, -0.1)
    patch(lib, 'sla_ringA', C, R, fd, 0.80, 0.80, ring1, rig.body, k=1.006)
    patch(lib, 'sla_ringB', C, R, fd, 0.62, 0.62, ring2, rig.body, k=1.012)
    patch(lib, 'sla_gloss', C, R, (-0.66, -0.6, 0.5), 0.07, 0.2, gloss, rig.body, k=1.016, rings=3, seg=16)

    # face
    for sx, nm in ((-1, 'L'), (1, 'R')):
        e = lib.eye('sla_eye' + nm, on(C, R, (sx * 0.3, -1, 0.1), 0.99), 0.062, rig.body,
                    iris='#1c3470', pupil='#0e1a3a', sclera='#0e1a3a', look=(sx * 0.22, -1, 0.08), iris_frac=0.7)
        e.scale = (0.85, 1, 1.35)
        patch(lib, 'sla_cheek' + nm, C, R, (sx * 0.62, -1, -0.2), 0.12, 0.075, pink, rig.body, k=1.018, rings=3, seg=16)
    pts = [on(C, R, (x, -1, z), 1.016) for x, z in [(-0.19, -0.26), (-0.1, -0.33), (0, -0.35), (0.1, -0.33), (0.19, -0.26)]]
    lib.tube('sla_mouth', pts, [0.008, 0.012, 0.012, 0.012, 0.008], dark, rig.body, seg=8)

    rig.attack_origin = (0, -0.5, CZ)
    return rig
