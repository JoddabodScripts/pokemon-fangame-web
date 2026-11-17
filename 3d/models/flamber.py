"""Flamber: a little flame egg with one big heat-seeing eye. Excitable; hops and somersaults."""
import math
from mathutils import Vector

P = 'flb_'
TAU = 2 * math.pi


# ---------------------------------------------------------------- local helpers
def _aim(d):
    """Euler that turns local +Z onto direction d."""
    return Vector((0, 0, 1)).rotation_difference(Vector(d).normalized()).to_euler()


def gmat(lib, name, stops, mode='z', center=(0, 0, 0), span=1.0, rough=0.35, coat=0.4, emit=0.3, sss=0.0, alpha=1.0):
    """Gradient material. stops = [(pos, '#hex')]. mode 'z': along the mesh's own height (bounding box);
    'radial': distance from `center` (object space) / span. The ramp drives base color and emission color."""
    m = lib.mat(name, stops[0][1], rough, emit=max(emit, 0.001), sss=sss, coat=coat, alpha=alpha)
    if m.get('grad'):
        return m
    m['grad'] = 1
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*lib._rgb(stops[0][1]), 1)
    els[1].position, els[1].color = stops[-1][0], (*lib._rgb(stops[-1][1]), 1)
    for pos, col in stops[1:-1]:
        e = els.new(pos)
        e.color = (*lib._rgb(col), 1)
    if mode == 'z':
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Generated'], sep.inputs[0])
        nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    else:
        dist = nt.nodes.new('ShaderNodeVectorMath')
        dist.operation = 'DISTANCE'
        dist.inputs[1].default_value = center
        div = nt.nodes.new('ShaderNodeMath')
        div.operation = 'DIVIDE'
        div.inputs[1].default_value = span
        nt.links.new(tc.outputs['Object'], dist.inputs[0])
        nt.links.new(dist.outputs['Value'], div.inputs[0])
        nt.links.new(div.outputs[0], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = emit
    return m


def flame(lib, name, r, h, m, parent, loc=(0, 0, 0), d=(0, 0, 1), bend=(0, 0), curl=0.0, flat=1.0,
          seg=12, rings=10, base=0.6, subsurf=1):
    """A flame tongue from `loc` along d: fat near the base, tapering to a curved tip. curl adds an S-wave."""
    verts = [(0, 0, -r * 0.35)]
    t0 = 0.24
    for i in range(rings):
        t = i / rings
        if t < t0:
            f = base + (1 - base) * math.sin(math.pi / 2 * t / t0)
        else:
            u = (t - t0) / (1 - t0)
            f = (0.5 + 0.5 * math.cos(math.pi * u)) ** 0.85
        ox = bend[0] * t * t + curl * math.sin(math.pi * 1.6 * t) * (1 - t * 0.3)
        oy = bend[1] * t * t
        for k in range(seg):
            a = TAU * k / seg
            verts.append((ox + math.cos(a) * r * f, oy + math.sin(a) * r * f * flat, h * t))
    verts.append((bend[0] + curl * math.sin(math.pi * 1.6) * 0.7, bend[1], h))
    tip = len(verts) - 1
    faces = []
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((0, 1 + k2, 1 + k))
        for i in range(rings - 1):
            a, b = 1 + i * seg, 1 + (i + 1) * seg
            faces.append((a + k, a + k2, b + k2, b + k))
        a = 1 + (rings - 1) * seg
        faces.append((a + k, a + k2, tip))
    o = lib.from_verts(name, verts, faces, m, parent, loc, subsurf=subsurf)
    o.rotation_euler = _aim(d)
    return o


# egg profile ------------------------------------------------------------------
EZ, EH, ER, EK, EFLAT = 0.46, 0.39, 0.33, 0.24, 0.95


def egg_r(z):
    c = max(-1.0, min(1.0, (EZ - z) / EH))        # +1 at the bottom
    return ER * math.sqrt(1 - c * c) * (1 + EK * c)


def egg_pt(x, z, lift=1.0):
    """Point on the front (-Y) of the egg at side offset x and height z."""
    r = egg_r(z)
    y = -EFLAT * math.sqrt(max(r * r - x * x, 0.0))
    return (x * lift, y * lift, EZ + (z - EZ) * lift)


def egg_dir(a, z, lift=1.0):
    """Point on the egg at angle a around Z (0 = front, + toward +X) and height z."""
    r = egg_r(z) * lift
    return (math.sin(a) * r, -math.cos(a) * r * EFLAT, z)


def egg_mesh(lib, name, m, parent, seg=32, rings=18):
    verts, faces = [(0, 0, EZ - EH)], []
    for i in range(1, rings):
        z = EZ - EH * math.cos(math.pi * i / rings)
        r = egg_r(z)
        for k in range(seg):
            a = TAU * k / seg
            verts.append((math.cos(a) * r, math.sin(a) * r * EFLAT, z))
    verts.append((0, 0, EZ + EH))
    top = len(verts) - 1
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((0, 1 + k2, 1 + k))
        for i in range(rings - 2):
            a, b = 1 + i * seg, 1 + (i + 1) * seg
            faces.append((a + k, a + k2, b + k2, b + k))
        a = 1 + (rings - 2) * seg
        faces.append((a + k, a + k2, top))
    return lib.from_verts(name, verts, faces, m, parent, subsurf=1)


def sticker(lib, name, p, n, scale, m, parent, roll=0.0):
    """A flattened blob lying on a surface at p with normal n (gloss streaks, cheeks)."""
    o = lib.sphere(name, p, scale, m, parent, seg=16)
    q = Vector((0, -1, 0)).rotation_difference(Vector(n).normalized())
    o.rotation_euler = (q @ Vector((0, 1, 0)).rotation_difference(Vector((0, 1, 0)))).to_euler()
    o.rotation_euler.rotate_axis('Y', roll)
    return o


def big_eye(lib, name, loc, r, parent, look):
    """The one huge amber eye: glossy white, layered glowing iris, two catch-lights."""
    p = lib.pivot(name, loc, parent)
    p.rotation_euler = Vector((0, -1, 0)).rotation_difference(Vector(look).normalized()).to_euler()
    lib.sphere(name + '_rim', (0, r * 0.04, 0), (r * 1.045, r * 0.36, r * 1.045), lib.mat(P + 'erim', '#a8241a', 0.4, coat=0.5), p)
    lib.sphere(name + '_white', (0, 0, 0), (r, r * 0.42, r), lib.mat(P + 'ewhite', '#fffaf2', 0.08, coat=1, sss=0.1), p, seg=40)
    iris = gmat(lib, P + 'eiris', [(0.0, '#7a3208'), (0.45, '#e08a10'), (0.8, '#ffc428'), (1.0, '#ffe070')],
                mode='radial', center=(0, 0, -0.55), span=1.9, rough=0.12, coat=1, emit=0.35)
    lib.sphere(name + '_iris', (0, -r * 0.31, -r * 0.05), (r * 0.66, r * 0.13, r * 0.66), iris, p)
    lib.sphere(name + '_ring', (0, -r * 0.345, -r * 0.05), (r * 0.42, r * 0.11, r * 0.42), lib.mat(P + 'ering', '#6a2c0a', 0.15, coat=1), p)
    lib.sphere(name + '_pupil', (0, -r * 0.37, -r * 0.05), (r * 0.27, r * 0.1, r * 0.27), lib.mat(P + 'epupil', '#160a08', 0.08, coat=1), p)
    sh = lib.mat('shine', '#ffffff', 0.1, emit=2)
    lib.sphere(name + '_shine', (-r * 0.3, -r * 0.43, r * 0.3), (r * 0.2, r * 0.06, r * 0.2), sh, p)
    lib.sphere(name + '_shine2', (r * 0.3, -r * 0.43, -r * 0.36), (r * 0.09, r * 0.04, r * 0.09), sh, p)
    return p


# ---------------------------------------------------------------- model
def build(lib):
    rig = lib.Rig('Flamber', 'flamber', 'Fire', height_cm=40, gait='hop', attack='cast')
    FR = gmat(lib, P + 'fr', [(0.0, '#a0180c'), (0.5, '#d42e14'), (1.0, '#ff6a1c')], emit=0.45, coat=0.5)
    FO = gmat(lib, P + 'fo', [(0.0, '#e4500e'), (0.55, '#f8881c'), (1.0, '#ffc23c')], emit=0.9, coat=0.4)
    FY = gmat(lib, P + 'fy', [(0.0, '#ffa818'), (0.5, '#ffd040'), (1.0, '#fff4a8')], emit=1.5, coat=0.3)
    body = gmat(lib, P + 'body', [(0.0, '#fff2a8'), (0.12, '#ffd648'), (0.21, '#ffb428'), (0.3, '#f67c18'),
                                   (0.43, '#e04818'), (0.62, '#cc2e14'), (1.0, '#96180e')],
                mode='radial', center=(0, -0.31, 0.3), span=0.72, rough=0.22, coat=0.8, emit=0.22, sss=0.15)
    dark = lib.mat(P + 'dark', '#5a1410', 0.45, coat=0.4)
    foot = gmat(lib, P + 'foot', [(0.0, '#6a120c'), (0.6, '#a82014'), (1.0, '#d43c1c')], rough=0.3, coat=0.7, emit=0.05)
    gloss = lib.mat(P + 'gloss', '#fff0e0', 0.1, emit=0.7, coat=1)
    cheek = lib.mat(P + 'cheek', '#ff7a5a', 0.5, emit=0.25, sss=0.3)
    coal = lib.mat(P + 'coal', '#6e4a36', 0.9)
    glow = lib.mat(P + 'glow', '#ff9a30', 0.5, emit=1.6, alpha=0.4)
    em_y = lib.mat(P + 'emy', '#ffd850', 0.4, emit=3.0)
    em_o = lib.mat(P + 'emo', '#ff8a28', 0.4, emit=2.4)

    # scorched spot with glowing cinders stays on the ground while it hops
    lib.sphere(P + 'scorch', (0, 0, 0.004), (0.31, 0.28, 0.006), coal, rig.root, seg=24)
    lib.sphere(P + 'scorchglow', (0, -0.02, 0.008), (0.22, 0.2, 0.006), glow, rig.root, seg=24)
    for i, (a, r, s) in enumerate([(0.6, 0.3, 0.02), (2.5, 0.27, 0.016), (4.1, 0.31, 0.022), (5.3, 0.25, 0.014)]):
        lib.sphere(f'{P}cinder{i}', (math.cos(a) * r, math.sin(a) * r, 0.012), (s, s, s * 0.6), em_o if i % 2 else em_y, rig.root, seg=8)

    # spin = whole-creature pivot at its middle (hops, flips); body = squash pivot on the ground
    spin = lib.pivot(P + 'spin', (0, 0, EZ), rig.root)
    rig.body = lib.pivot(P + 'body', (0, 0, -EZ), spin)
    B = rig.body
    egg_mesh(lib, P + 'egg', body, B)
    # gloss and rim light
    sticker(lib, P + 'gloss1', egg_dir(-0.85, 0.62, 0.985), (-0.7, -0.6, 0.4), (0.026, 0.01, 0.07), gloss, B, roll=0.3)
    sticker(lib, P + 'gloss2', egg_dir(-0.72, 0.74, 0.985), (-0.6, -0.6, 0.6), (0.026, 0.01, 0.03), gloss, B)

    # face (head pivot on the egg's axis, so turning it slides the eye around: a look to the side)
    rig.head = lib.pivot(P + 'head', (0, 0, 0.5), B)
    H = rig.head
    hp = lambda p: (p[0], p[1], p[2] - 0.5)  # noqa: E731
    eye = big_eye(lib, P + 'eye', hp(egg_pt(0, 0.53, 0.93)), 0.178, H, (0, -1, 0.14))
    for s in (-1, 1):
        lib.tube(f'{P}lash{s}', [hp(egg_pt(s * 0.12, 0.7, 1.015)), hp(egg_pt(s * 0.17, 0.735, 1.05)),
                                 hp(egg_pt(s * 0.215, 0.745, 1.06))], [0.017, 0.014, 0.005], dark, H)
        sticker(lib, f'{P}cheek{s}', hp(egg_pt(s * 0.215, 0.37, 0.99)), (s * 0.7, -1, -0.1), (0.045, 0.012, 0.03), cheek, H)
    pts = []
    for k in range(7):
        x = -0.075 + 0.15 * k / 6
        pts.append(hp(egg_pt(x, 0.285 + 0.035 * (abs(x) / 0.075) ** 2, 1.02)))
    lib.tube(P + 'smile', pts, [0.006, 0.011, 0.013, 0.013, 0.013, 0.011, 0.006], dark, H)

    # layered flame flowing out of the top of the egg
    fl = lib.pivot(P + 'flame', (0, 0, 0.76), B)
    for i, a in enumerate(range(0, 360, 45)):          # collar of small licks hides the seam
        a = math.radians(a + 20)
        x, y = math.sin(a), math.cos(a)
        flame(lib, f'{P}f_c{i}', 0.07, 0.17 + 0.04 * (i % 3), FR, fl, (x * 0.13, y * 0.12, -0.05), d=(x * 0.75, y * 0.75, 1),
              curl=0.012, flat=0.9, seg=8, rings=6)
    flame(lib, P + 'f_r0', 0.17, 0.62, FR, fl, (0, 0.02, -0.07), d=(0.02, 0, 1), bend=(0.08, 0), curl=0.045, flat=0.85)
    flame(lib, P + 'f_r1', 0.115, 0.36, FR, fl, (-0.11, 0.02, -0.08), d=(-0.45, 0, 1), bend=(0.08, 0), curl=-0.02, flat=0.85)
    flame(lib, P + 'f_r2', 0.12, 0.42, FR, fl, (0.12, 0.02, -0.08), d=(0.42, 0, 1), bend=(-0.07, 0), curl=0.02, flat=0.85)
    flame(lib, P + 'f_r3', 0.11, 0.34, FR, fl, (0, 0.1, -0.08), d=(0, 0.45, 1), bend=(0, -0.05))
    flame(lib, P + 'f_o0', 0.115, 0.42, FO, fl, (0.0, -0.065, -0.06), d=(0.02, -0.06, 1), bend=(0.06, 0), curl=0.035, flat=0.75)
    flame(lib, P + 'f_o1', 0.08, 0.25, FO, fl, (-0.085, -0.065, -0.07), d=(-0.42, -0.08, 1), flat=0.75)
    flame(lib, P + 'f_o2', 0.08, 0.29, FO, fl, (0.095, -0.065, -0.07), d=(0.4, -0.08, 1), flat=0.75)
    flame(lib, P + 'f_y0', 0.07, 0.25, FY, fl, (0.0, -0.125, -0.07), d=(0.03, -0.14, 1), curl=0.02, flat=0.7)
    flame(lib, P + 'f_y1', 0.048, 0.15, FY, fl, (0.058, -0.12, -0.075), d=(0.42, -0.14, 1), flat=0.7)
    rig.extras.append((fl, 'flicker'))

    # stubby flame arms: one chubby upturned flame each, with a hotter inner lick
    for s, nm, ph in ((-1, 'L', 0.0), (1, 'R', 0.5)):
        ap = lib.pivot(P + 'arm' + nm, (s * 0.27, -0.02, 0.43), B)
        flame(lib, P + 'arm_a' + nm, 0.1, 0.3, FR, ap, (0, 0, 0), d=(s, 0, 0.25), bend=(-s * 0.09, 0), flat=0.8, base=0.8)
        flame(lib, P + 'arm_b' + nm, 0.07, 0.17, FR, ap, (s * 0.02, 0.01, -0.04), d=(s, 0, -0.55), flat=0.8, base=0.8)
        flame(lib, P + 'arm_c' + nm, 0.055, 0.17, FO, ap, (s * 0.05, -0.062, 0.005), d=(s, -0.08, 0.3), bend=(-s * 0.04, 0), flat=0.7, base=0.8)
        rig.arms.append((ap, ph))
        rig.t_pose[ap.name] = (0, 0, 0)

    # tiny feet
    for s, nm, ph in ((-1, 'L', 0.0), (1, 'R', 0.5)):
        lp = lib.pivot(P + 'leg' + nm, (s * 0.14, -0.02, 0.13), B)
        lib.sphere(P + 'foot' + nm, (0, -0.05, -0.07), (0.1, 0.145, 0.065), foot, lp)
        rig.legs.append((lp, ph))

    # floating embers
    em = lib.pivot(P + 'embers', (0, 0, 0.6), B)
    for i, (a, r, z, s) in enumerate([(0.5, 0.52, 0.42, 0.03), (2.4, 0.5, 0.55, 0.022), (3.6, 0.55, 0.12, 0.026),
                                      (5.2, 0.5, 0.3, 0.02), (1.5, 0.47, 0.02, 0.018)]):
        lib.sphere(f'{P}ember{i}', (math.cos(a) * r, math.sin(a) * r, z), s, em_o if i % 2 else em_y, em, seg=10)
    rig.extras.append((em, 'spin'))

    rig.attack_origin = (0, -0.3, 1.1)
    rig._p = dict(spin=spin, flame=fl, eye=eye, embers=em, mats=(FR, FO, FY), body_mat=body)
    return rig


# ---------------------------------------------------------------- animation
def animate(A):
    """Ignites from a bouncing ember; bouncy hops with a somersault; Ember volley; gets bowled over and relights."""
    lib, r, T, s = A.lib, A.rig, A.T, A.size
    root, B, H = r.root, r.body, r.head
    spin, fl, eye, embers = r._p['spin'], r._p['flame'], r._p['eye'], r._p['embers']
    FR, FO, FY = r._p['mats']
    (armL, _), (armR, _) = r.arms
    (legL, _), (legR, _) = r.legs
    em_y = lib.mat(P + 'emy', '#ffd850', 0.4, emit=3.0)
    D = 1.5 * s

    def arms(f, up, fwd=0.0):                      # up > 0 raises both
        A.key(armL, f, rot=(fwd, up, 0))
        A.key(armR, f, rot=(fwd, -up, 0))

    def feet(f, a, b=None):
        A.key(legL, f, rot=(a, 0, 0))
        A.key(legR, f, rot=(a if b is None else b, 0, 0))

    def glow(f, k):                                 # flame brightness multiplier
        k = 1 + (k - 1) * 0.8
        A.emission(FR, f, 0.45 * k)
        A.emission(FO, f, 0.9 * k)
        A.emission(FY, f, 1.5 * k)

    def blink(f):
        A.key(eye, f - 2, scale=1)
        A.key(eye, f, scale=(1, 1, 0.08))
        A.key(eye, f + 2, scale=1)

    # ---- send-out: one ember drops out of the ball, bounces twice, and whooshes up into Flamber
    ember = lib.pivot(P + 'fx_ember')
    lib.sphere(P + 'fx_emberm', (0, 0, 0), 0.055, em_y, ember, seg=12)
    lib.sphere(P + 'fx_emberh', (0, 0, 0), 0.1, lib.mat(P + 'halo', '#ff8a20', 0.5, emit=2.0, alpha=0.35), ember, seg=12)
    p0 = Vector((0, -0.25 * s, 0.55 * s))
    A.key(ember, 0, loc=p0, scale=0.001, absolute=True)
    A.key(ember, 15, loc=p0, scale=0.001, absolute=True)
    A.key(ember, 16, loc=p0, scale=1, absolute=True)
    A.key(ember, 20, loc=(0, -0.08, 0.05), scale=(1.3, 1.3, 0.6), absolute=True)
    A.key(ember, 23, loc=(0, -0.03, 0.3), scale=1, absolute=True)
    A.key(ember, 26, loc=(0, 0, 0.05), scale=(1.5, 1.5, 0.5), absolute=True)
    A.key(ember, 28, loc=(0, 0, 0.25), scale=0.001, absolute=True)
    A.light(P + 'fx_ign', '#ff9a30', (0, -0.5, 0.6), [(15, 0), (20, 7 * s * s), (26, 15 * s * s), (30, 105 * s * s), (36, 20 * s * s), (44, 40 * s * s), (50, 0)])

    A.key(root, 0, scale=0.001, loc=(0, 0, 0), rot=(0, 0, 0))
    A.key(root, 26, scale=0.001)
    A.key(root, 28, scale=(0.45, 0.45, 0.8))
    A.key(root, 30, scale=(0.7, 0.7, 1.4))
    A.key(root, 34, scale=(1.22, 1.22, 0.74))
    A.key(root, 38, scale=(0.94, 0.94, 1.1))
    A.key(root, 41, scale=1)
    A.key(fl, 26, scale=0.15); A.key(fl, 31, scale=(1.3, 1.3, 2.1)); A.key(fl, 36, scale=0.85); A.key(fl, 40, scale=1)
    glow(16, 1); glow(30, 2.2); glow(38, 1)
    A.key(eye, 26, scale=(1, 1, 0.08)); A.key(eye, 36, scale=(1, 1, 0.08)); A.key(eye, 39, scale=1.12); A.key(eye, 42, scale=1)
    arms(26, -0.6); arms(34, -0.6); arms(40, 0)
    # cry: a bouncing squeak with its arms thrown up and the flame flaring
    A.key(spin, 41, loc=(0, 0, 0), rot=(0, 0, 0))
    A.key(B, 41, scale=1); A.key(B, 43, scale=(1.12, 1.12, 0.84)); A.key(B, 45, scale=(0.92, 0.92, 1.14)); A.key(B, 48, scale=1)
    A.key(spin, 43, loc=(0, 0, 0)); A.key(spin, 46, loc=(0, 0, 0.2), rot=(-0.18, 0, 0)); A.key(spin, 49, loc=(0, 0, 0), rot=(0, 0, 0))
    arms(43, -0.2); arms(46, 1.0); arms(51, 0)
    A.key(fl, 43, scale=1); A.key(fl, 46, scale=(1.25, 1.25, 1.6)); A.key(fl, 51, scale=1)
    glow(43, 1); glow(46, 1.9); glow(52, 1)
    feet(41, 0); feet(46, 0.5); feet(49, 0)

    # ---- idle: breathes, peers left and right (the eye slides round the egg), blinks
    for f, sc in ((52, 1), (58, (1.03, 1.03, 0.97)), (64, (0.98, 0.98, 1.03)), (70, 1)):
        A.key(B, f, scale=sc)
    A.key(H, 50, rot=(0, 0, 0)); A.key(H, 55, rot=(0, 0, 0.42)); A.key(H, 60, rot=(0, 0, 0.42))
    A.key(H, 65, rot=(0, 0, -0.38)); A.key(H, 69, rot=(0, 0, -0.38)); A.key(H, 73, rot=(0, 0, 0))
    blink(62)
    arms(56, 0.15); arms(64, -0.1); arms(71, 0)

    # ---- walk: turn with a skip, five springy hops (the third is a somersault), turn back
    A.key(root, 72, rot=(0, 0, 0), loc=(0, 0, 0))
    A.key(root, 78, rot=(0, 0, math.pi / 2))
    A.key(spin, 72, loc=(0, 0, 0)); A.key(spin, 75, loc=(0, 0, 0.12)); A.key(spin, 78, loc=(0, 0, 0))
    hops, rx0 = 5, 0.0
    for i in range(hops):
        f0 = 78 + i * 10
        flip = i == 2
        x0, x1 = D * i / hops, D * (i + 1) / hops
        apex = 0.62 if flip else (0.3 + 0.06 * (i % 2))
        A.key(root, f0 + 1, loc=(x0, 0, 0)); A.key(root, f0 + 8, loc=(x1, 0, 0))
        A.key(B, f0, scale=(1.18, 1.18, 0.76))                       # crouch
        A.key(B, f0 + 2, scale=(0.86, 0.86, 1.24))                   # launch stretch
        A.key(B, f0 + 5, scale=(1.04, 1.04, 0.96) if flip else 1)
        A.key(B, f0 + 8, scale=(0.9, 0.9, 1.16))                     # reach for the ground
        A.key(B, f0 + 9, scale=(1.24, 1.24, 0.7))                    # splat
        A.key(spin, f0 + 1, loc=(0, 0, 0)); A.key(spin, f0 + 5, loc=(0, 0, apex)); A.key(spin, f0 + 8, loc=(0, 0, 0))
        if flip:
            A.key(spin, f0 + 1, rot=(rx0, 0, 0))
            A.key(spin, f0 + 5, rot=(rx0 + math.pi * 1.1, 0, 0))
            A.key(spin, f0 + 8, rot=(rx0 + TAU, 0, 0))
            rx0 += TAU
            arms(f0, 0.2); arms(f0 + 3, -0.5); arms(f0 + 8, 0.9); arms(f0 + 10, 0.1)
            feet(f0, 0); feet(f0 + 4, 0.9); feet(f0 + 8, -0.3); feet(f0 + 10, 0)
        else:
            A.key(spin, f0 + 1, rot=(rx0 + 0.1, 0, 0)); A.key(spin, f0 + 4, rot=(rx0 + 0.2, 0, 0)); A.key(spin, f0 + 8, rot=(rx0 - 0.1, 0, 0))
            arms(f0, -0.35); arms(f0 + 4, 0.85); arms(f0 + 8, 0.25); arms(f0 + 10, -0.3)
            feet(f0, 0, 0); feet(f0 + 3, 0.7, 0.4); feet(f0 + 7, -0.45, -0.25); feet(f0 + 10, 0, 0)
        # flame follow-through: streams back in the air, whips forward on landing
        A.key(fl, f0, scale=(1.1, 1.1, 0.8)); A.key(fl, f0 + 4, scale=(0.9, 0.9, 1.35)); A.key(fl, f0 + 9, scale=(1.2, 1.2, 0.7))
        # embers kicked up where it lands
        puff = lib.pivot(f'{P}fx_puff{i}')
        for j in range(4):
            a = 0.8 + j * 1.6 + i
            lib.sphere(f'{P}fx_puff{i}_{j}', (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.06 + 0.05 * (j % 2)), 0.028, em_y, puff, seg=8)
        A.key(puff, 0, loc=(x1, 0, 0), scale=0.001, absolute=True); A.key(puff, f0 + 8, scale=0.001, absolute=True)
        A.key(puff, f0 + 9, loc=(x1, 0, 0), scale=(0.5, 0.5, 0.5), absolute=True)
        A.key(puff, f0 + 14, loc=(x1, 0, 0.22), scale=(1.7, 1.7, 1.3), absolute=True)
        A.key(puff, f0 + 17, loc=(x1, 0, 0.3), scale=0.001, absolute=True)
    A.key(B, 128, scale=(1.2, 1.2, 0.74)); A.key(B, 131, scale=(0.92, 0.92, 1.12)); A.key(B, 136, scale=(1.1, 1.1, 0.9)); A.key(B, 139, scale=1)
    A.key(spin, 128, loc=(0, 0, 0), rot=(rx0, 0, 0)); A.key(spin, 132, loc=(0, 0, 0.2)); A.key(spin, 136, loc=(0, 0, 0))
    A.key(root, 129, rot=(0, 0, math.pi / 2), loc=(D, 0, 0)); A.key(root, 136, rot=(0, 0, 0))
    A.key(fl, 128, scale=(1.2, 1.2, 0.7)); A.key(fl, 133, scale=(0.95, 0.95, 1.2)); A.key(fl, 138, scale=1)
    arms(128, -0.3); arms(132, 0.5); arms(138, 0)
    feet(128, 0); feet(132, 0.4); feet(136, 0)
    blink(137)

    # ---- attack: Ember. Sucks its flame in, swells, then flings three embers off its head, one hop each
    aim = 0.6
    A.key(root, 140, rot=(0, 0, 0)); A.key(root, 146, rot=(0, 0, aim)); A.key(root, 176, rot=(0, 0, aim)); A.key(root, 184, rot=(0, 0, 0))
    A.key(B, 140, scale=1); A.key(B, 147, scale=(1.22, 1.22, 0.7)); A.key(B, 151, scale=(1.26, 1.26, 0.68))
    A.key(spin, 140, rot=(rx0, 0, 0)); A.key(spin, 148, rot=(rx0 - 0.28, 0, 0)); A.key(spin, 151, rot=(rx0 - 0.32, 0, 0))
    A.key(fl, 140, scale=1); A.key(fl, 146, scale=0.45); A.key(fl, 151, scale=(1.5, 1.5, 1.9))
    glow(140, 1); glow(146, 0.5); glow(151, 2.2)
    A.key(eye, 140, scale=1); A.key(eye, 146, scale=(1, 1, 0.55)); A.key(eye, 151, scale=(1, 1, 0.5)); A.key(eye, 154, scale=1.1); A.key(eye, 174, scale=1)
    arms(140, 0); arms(147, -0.7, 0.3); arms(151, -0.8, 0.3)
    shots = (152, 157, 162)
    for n, f0 in enumerate(shots):
        A.key(B, f0, scale=(0.84, 0.84, 1.3)); A.key(B, f0 + 3, scale=(1.14, 1.14, 0.84))
        A.key(spin, f0, loc=(0, 0, 0), rot=(rx0 + 0.5, 0, 0)); A.key(spin, f0 + 1, loc=(0, -0.05, 0.2))
        A.key(spin, f0 + 4, loc=(0, 0, 0), rot=(rx0 - 0.15, 0, 0))
        A.key(fl, f0, scale=(0.9, 0.9, 1.8), rot=(0.7, 0, 0)); A.key(fl, f0 + 3, scale=(1.1, 1.1, 0.7), rot=(-0.2, 0, 0))
        arms(f0, 1.0, -0.6); arms(f0 + 3, -0.3, 0.3)
        glow(f0, 2.0); glow(f0 + 3, 1.4)
        # the ember itself
        src = A.world(fl, f0, (0, -0.25, 0.45))
        dst = A.opponent(A.world(root, f0)) + Vector((0.12 * (n - 1) * s, 0, 0.1 * n * s))
        shot = lib.pivot(f'{P}fx_shot{n}')
        lib.sphere(f'{P}fx_shotc{n}', (0, 0, 0), 0.07 * s, em_y, shot, seg=12)
        lib.sphere(f'{P}fx_shoth{n}', (0, 0, 0), 0.13 * s, lib.mat(P + 'halo', '#ff8a20', 0.5, emit=2.0, alpha=0.35), shot, seg=12)
        flame(lib, f'{P}fx_shott{n}', 0.07 * s, 0.3 * s, FO, shot, d=(-0.8, 0.55, 0.3), seg=8, rings=6)
        A.key(shot, 0, loc=src, scale=0.001, absolute=True); A.key(shot, f0 - 1, loc=src, scale=0.001, absolute=True)
        fly = 9
        for k in range(fly + 1):
            t = k / fly
            pos = src.lerp(dst, t) + Vector((0, 0, math.sin(math.pi * t) * (0.5 + 0.2 * n) * s))
            A.key(shot, f0 + k, loc=pos, scale=0.8 + 0.5 * t, absolute=True)
        A.key(shot, f0 + fly + 1, loc=dst, scale=0.001, absolute=True)
        A.interp(shot, 'LINEAR')
        boom = lib.sphere(f'{P}fx_boom{n}', dst, 1, lib.mat(P + 'boom', '#ff7a18', 0.5, emit=5.0, alpha=0.55), seg=16)
        hit = f0 + fly
        A.key(boom, 0, scale=0.001); A.key(boom, hit - 1, scale=0.001)
        A.key(boom, hit + 1, scale=0.3 * s); A.key(boom, hit + 4, scale=(0.5 * s, 0.5 * s, 0.38 * s)); A.key(boom, hit + 7, scale=0.001)
        for j in range(5):                                           # sparks thrown out of the burst
            a = TAU * j / 5 + n
            sp = lib.sphere(f'{P}fx_spark{n}_{j}', dst, 0.03 * s, em_y, seg=8)
            A.key(sp, 0, loc=dst, scale=0.001, absolute=True); A.key(sp, hit, loc=dst, scale=0.001, absolute=True)
            A.key(sp, hit + 1, loc=dst, scale=1, absolute=True)
            out = dst + Vector((math.cos(a) * 0.5 * s, math.sin(a) * 0.3 * s, (0.25 + 0.2 * (j % 2)) * s))
            A.key(sp, hit + 6, loc=out, scale=0.8, absolute=True)
            A.key(sp, hit + 10, loc=out + Vector((0, 0, -0.25 * s)), scale=0.001, absolute=True)
    opp = A.opponent(A.world(root, 160))
    A.light(P + 'fx_hitl', '#ff8a20', opp + Vector((0, 0, 0.3 * s)),
            [(160, 0), (162, 125 * s * s), (165, 30 * s * s), (167, 150 * s * s), (170, 37 * s * s), (172, 175 * s * s), (180, 0)])
    A.light(P + 'fx_selfl', '#ff9a30', A.world(root, 150) + Vector((0, -0.7, 0.9)),
            [(144, 0), (151, 65 * s * s), (156, 22 * s * s), (163, 50 * s * s), (172, 0)])
    # pleased with itself: little settle bounce
    A.key(B, 168, scale=1); A.key(B, 172, scale=(1.08, 1.08, 0.9)); A.key(B, 176, scale=(0.96, 0.96, 1.06)); A.key(B, 181, scale=1)
    A.key(spin, 168, loc=(0, 0, 0), rot=(rx0, 0, 0)); A.key(spin, 185, loc=(0, 0, 0), rot=(rx0, 0, 0))
    A.key(fl, 168, scale=1, rot=(0, 0, 0)); A.key(fl, 185, scale=1)
    arms(170, 0.2, 0); arms(176, 0.7); arms(183, 0)
    glow(170, 1); glow(185, 1)

    # ---- hit: bowled over backwards in a full tumble, flame nearly snuffed, eye screwed shut
    A.key(eye, 185, scale=1); A.key(eye, 187, scale=(1.05, 1, 0.1)); A.key(eye, 207, scale=(1.05, 1, 0.1))
    A.key(B, 186, scale=(0.8, 1.25, 1.05)); A.key(B, 189, scale=1); A.key(B, 198, scale=(0.92, 0.92, 1.1))
    A.key(B, 200, scale=(1.3, 1.3, 0.62)); A.key(B, 203, scale=(0.95, 0.95, 1.08)); A.key(B, 206, scale=(1.06, 1.06, 0.94))
    A.key(spin, 186, loc=(0, 0, 0), rot=(rx0, 0, 0))
    A.key(spin, 190, loc=(-0.08, 0.2, 0.42), rot=(rx0 - 2.2, 0, 0))
    A.key(spin, 194, loc=(-0.14, 0.4, 0.4), rot=(rx0 - 4.4, 0, 0))
    A.key(spin, 199, loc=(-0.18, 0.55, 0), rot=(rx0 - TAU, 0, 0))
    rx0 -= TAU
    A.key(spin, 202, loc=(-0.19, 0.6, 0.07), rot=(rx0 - 0.1, 0.12, 0))
    A.key(spin, 205, loc=(-0.2, 0.62, 0), rot=(rx0, -0.1, 0))
    A.key(fl, 187, scale=(0.6, 0.6, 0.4)); A.key(fl, 199, scale=0.22); A.key(fl, 202, scale=0.3); A.key(fl, 204, scale=0.18); A.key(fl, 208, scale=0.25)
    glow(187, 0.4); glow(200, 0.15); glow(203, 0.5); glow(205, 0.15)
    arms(187, 1.1, -0.5); arms(191, -0.6, 0.6); arms(195, 1.0, -0.4); arms(200, -0.5); arms(205, -0.4)
    feet(187, -0.8); feet(194, 0.8, -0.6); feet(200, 0)
    A.key(H, 186, rot=(0, 0, 0)); A.key(H, 200, rot=(0, 0, 0.2)); A.key(H, 203, rot=(0, 0, -0.2)); A.key(H, 206, rot=(0, 0, 0))

    # ---- recover: shakes the dizziness off, relights with a pop, hops back and cheers
    for k, f in enumerate(range(207, 216, 2)):
        A.key(H, f, rot=(0, 0, (0.35 if k % 2 else -0.35) * (1 - k / 6)))
        A.key(spin, f, rot=(rx0, 0.1 if k % 2 else -0.1, 0))
    A.key(H, 217, rot=(0, 0, 0)); A.key(spin, 217, rot=(rx0, 0, 0))
    A.key(eye, 210, scale=1.1); A.key(eye, 213, scale=1)
    A.key(fl, 212, scale=0.25); A.key(fl, 215, scale=(1.5, 1.5, 2.0)); A.key(fl, 218, scale=0.9); A.key(fl, 221, scale=1)
    glow(212, 0.2); glow(215, 2.3); glow(221, 1.2)
    A.light(P + 'fx_relight', '#ffb040', A.world(root, 206) + Vector((-0.2, 0.0, 1.0)), [(212, 0), (215, 87 * s * s), (222, 0)])
    A.key(B, 210, scale=1); A.key(B, 214, scale=(1.15, 1.15, 0.8)); A.key(B, 216, scale=(0.88, 0.88, 1.2))
    A.key(B, 221, scale=(1.2, 1.2, 0.75)); A.key(B, 223, scale=(0.9, 0.9, 1.18)); A.key(B, 227, scale=(1.12, 1.12, 0.86)); A.key(B, 230, scale=1)
    A.key(spin, 214, loc=(-0.2, 0.62, 0)); A.key(spin, 218, loc=(-0.1, 0.3, 0.3)); A.key(spin, 221, loc=(0, 0, 0))
    A.key(spin, 224, loc=(0, 0, 0.26), rot=(rx0 - 0.15, 0, 0)); A.key(spin, 227, loc=(0, 0, 0), rot=(rx0, 0, 0)); A.key(spin, 230, loc=(0, 0, 0))
    arms(214, -0.4); arms(218, 0.6); arms(221, -0.2); arms(224, 1.1); arms(230, 0.75)
    feet(214, 0); feet(218, 0.6); feet(221, 0); feet(224, 0.5); feet(227, 0)
    glow(224, 1.7); glow(230, 1.4)
    A.key(fl, 224, scale=(1.15, 1.15, 1.4)); A.key(fl, 230, scale=(1.05, 1.05, 1.15))

    # ---- always on: flame flicker and the embers orbiting (kept on their own channels)
    for f in A.frames(16, 230, 2):
        k = 1.8 if 78 <= f <= 128 else 1.0
        if not (152 <= f <= 167):
            A.key(fl, f, rot=(A.wave(f, 7) * 0.07 * k + (-0.35 if 78 <= f <= 128 and (f - 78) % 10 in (2, 4) else 0),
                              A.wave(f, 9, 0.3) * 0.1 * k, A.wave(f, 13, 0.6) * 0.15))
        A.key(embers, f, rot=(0, 0, f * 0.09), loc=(0, 0, A.wave(f, 23) * 0.05))
