"""Flamezion: a round flame with a crown of fire and a huge grin. A show-off king; floats, pirouettes, Flame Wheel."""
import math
from mathutils import Vector

P = 'flz_'
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


def sticker(lib, name, p, n, scale, m, parent, roll=0.0):
    """A flattened blob lying on a surface at p with normal n (gloss streaks, cheeks)."""
    o = lib.sphere(name, p, scale, m, parent, seg=16)
    q = Vector((0, -1, 0)).rotation_difference(Vector(n).normalized())
    o.rotation_euler = (q @ Vector((0, 1, 0)).rotation_difference(Vector((0, 1, 0)))).to_euler()
    o.rotation_euler.rotate_axis('Y', roll)
    return o


def on_ell(c, radii, x, z, lift=1.0):
    """Point on the front (-Y) face of an ellipsoid (center c, radii) at local x, z."""
    q = 1 - (x / radii[0]) ** 2 - (z / radii[2]) ** 2
    y = -radii[1] * math.sqrt(max(q, 0.0))
    return (c[0] + x * lift, c[1] + y * lift, c[2] + z * lift)


def ell_n(c, radii, p):
    return Vector(((p[0] - c[0]) / radii[0] ** 2, (p[1] - c[1]) / radii[1] ** 2, (p[2] - c[2]) / radii[2] ** 2)).normalized()


def decal(lib, name, outline, c, radii, m, parent, lift=1.012, thick=0.008, n=6, rings=4, off=(0, 0, 0)):
    """A flat marking wrapped onto the front of an ellipsoid. outline = [(x, z)] around the ellipsoid center.
    `off` is subtracted from every vertex (for markings that live under their own pivot)."""
    pts = []
    for i, (x0, z0) in enumerate(outline):
        x1, z1 = outline[(i + 1) % len(outline)]
        for k in range(n):
            pts.append((x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n))
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    sub = lambda p: (p[0] - off[0], p[1] - off[1], p[2] - off[2])  # noqa: E731
    verts = [sub(on_ell(c, radii, cx, cz, lift))]
    N = len(pts)
    for r in range(1, rings + 1):
        s = r / rings
        for x, z in pts:
            verts.append(sub(on_ell(c, radii, cx + (x - cx) * s, cz + (z - cz) * s, lift)))
    faces = []
    for k in range(N):
        k2 = (k + 1) % N
        faces.append((0, 1 + k, 1 + k2))
        for r in range(rings - 1):
            a, b = 1 + r * N, 1 + (r + 1) * N
            faces.append((a + k, b + k, b + k2, a + k2))
    return lib.from_verts(name, verts, faces, m, parent, subsurf=0, solidify=thick)


def oval(rx, rz, cx=0.0, cz=0.0, n=24):
    return [(cx + rx * math.cos(TAU * i / n), cz + rz * math.sin(TAU * i / n)) for i in range(n)]


CZ = 0.66                       # height of the body's center when hovering
RR = (0.43, 0.41, 0.43)
C0 = (0, 0, 0)


# ---------------------------------------------------------------- model
def build(lib):
    rig = lib.Rig('Flamezion', 'flamezion', 'Fire', height_cm=90, gait='float', attack='cast')
    R = math.radians
    FR = gmat(lib, P + 'fr', [(0.0, '#9c160a'), (0.5, '#d22a12'), (1.0, '#ff661a')], emit=0.45, coat=0.5)
    FO = gmat(lib, P + 'fo', [(0.0, '#e24c0c'), (0.55, '#f8861a'), (1.0, '#ffc23c')], emit=0.9, coat=0.4)
    FY = gmat(lib, P + 'fy', [(0.0, '#ffa818'), (0.5, '#ffd040'), (1.0, '#fff4a8')], emit=1.5, coat=0.3)
    body = gmat(lib, P + 'body', [(0.0, '#fff0a0'), (0.16, '#ffd244'), (0.27, '#ffb024'), (0.36, '#f47616'),
                                   (0.52, '#de4216'), (0.72, '#c82a10'), (1.0, '#8e160c')],
                mode='radial', center=(0, -0.9, -0.42), span=1.85, rough=0.2, coat=0.85, emit=0.22, sss=0.15)
    gloss = lib.mat(P + 'gloss', '#ffe8d0', 0.1, emit=0.7, coat=1)
    cheek = lib.mat(P + 'cheek', '#ff5a6a', 0.45, emit=0.3, sss=0.3)
    mouth = lib.mat(P + 'mouth', '#4a0c0c', 0.5)
    tongue = lib.mat(P + 'tongue', '#ff6a7a', 0.35, coat=0.5, sss=0.2)
    eyem = lib.mat(P + 'eye', '#180c0c', 0.05, coat=1)
    eyeir = lib.mat(P + 'eyeir', '#a8480c', 0.1, coat=1, emit=0.25)
    white = lib.mat(P + 'white', '#ffffff', 0.2, emit=1.8)
    fang = lib.mat(P + 'fang', '#fffdf4', 0.2, coat=0.8, emit=0.25)
    glow = lib.mat(P + 'glow', '#ff8a28', 0.5, emit=1.8, alpha=0.4)
    coal = lib.mat(P + 'coal', '#7a5238', 0.9)
    em_y = lib.mat(P + 'emy', '#ffd850', 0.4, emit=3.0)
    em_o = lib.mat(P + 'emo', '#ff8a28', 0.4, emit=2.4)

    # heat shimmer on the ground under it
    lib.sphere(P + 'scorch', (0, 0, 0.004), (0.4, 0.37, 0.006), coal, rig.root, seg=24)
    lib.sphere(P + 'heat', (0, 0, 0.008), (0.3, 0.28, 0.006), glow, rig.root, seg=24)

    hov = lib.pivot(P + 'hover', (0, 0, CZ), rig.root)          # always-on bobbing
    spin = lib.pivot(P + 'spin', (0, 0, 0), hov)                # big moves: whirls, rolls, knock-backs
    rig.body = lib.pivot(P + 'body', (0, 0, 0), spin)           # squash and stretch about its middle
    B = rig.body
    lib.sphere(P + 'ball', C0, RR, body, B, seg=48)
    sticker(lib, P + 'gloss1', on_ell(C0, RR, -0.2, 0.26, 0.985), (-0.5, -0.7, 0.6), (0.085, 0.012, 0.045), gloss, B, roll=-0.5)
    sticker(lib, P + 'gloss2', on_ell(C0, RR, -0.29, 0.15, 0.985), (-0.7, -0.6, 0.3), (0.025, 0.01, 0.025), gloss, B)

    # face
    rig.head = lib.pivot(P + 'head', (0, 0, 0), B)
    H = rig.head
    eyes = []
    for s in (-1, 1):
        p = on_ell(C0, RR, s * 0.165, 0.095, 0.99)
        e = lib.pivot(f'{P}eye{s}', p, H)
        e.rotation_euler = Vector((0, -1, 0)).rotation_difference(ell_n(C0, RR, p)).to_euler()
        lib.sphere(f'{P}eyeb{s}', (0, 0, 0), (0.088, 0.04, 0.128), eyem, e, seg=32)
        lib.sphere(f'{P}eyei{s}', (0, -0.012, -0.04), (0.066, 0.031, 0.078), eyeir, e, seg=24)
        lib.sphere(f'{P}eyes{s}', (-0.026, -0.034, 0.056), (0.034, 0.012, 0.042), white, e, seg=16)
        lib.sphere(f'{P}eyet{s}', (0.03, -0.036, -0.05), (0.016, 0.007, 0.018), white, e, seg=12)
        eyes.append(e)
        sticker(lib, f'{P}cheek{s}', on_ell(C0, RR, s * 0.305, -0.075, 0.992), (s * 0.75, -0.6, -0.15), (0.068, 0.014, 0.04), cheek, H)
        lib.tube(f'{P}brow{s}', [on_ell(C0, RR, s * 0.09, 0.265, 1.012), on_ell(C0, RR, s * 0.17, 0.3, 1.02), on_ell(C0, RR, s * 0.25, 0.275, 1.012)],
                 [0.008, 0.014, 0.006], mouth, H)
        fp = on_ell(C0, RR, s * 0.14, -0.085, 1.0)
        lib.cone(f'{P}fang{s}', (fp[0], fp[1] - 0.014, fp[2] - 0.04), 0.034, 0.0, 0.1, fang, H, rot=_aim((0, 0.3, -1)), seg=12, subsurf=1)
    hinge = on_ell(C0, RR, 0, -0.07, 1.0)
    mouthp = lib.pivot(P + 'mouthp', hinge, H)
    decal(lib, P + 'mouth', [(-0.215, -0.07), (0.215, -0.07), (0.13, -0.225), (-0.13, -0.225)], C0, RR, mouth, mouthp, lift=1.02, off=hinge)
    decal(lib, P + 'tongue', oval(0.09, 0.042, 0, -0.195), C0, RR, tongue, mouthp, lift=1.03, n=1, off=hinge)
    pts = []
    for k in range(11):
        x = -0.265 + 0.53 * k / 10
        pts.append(on_ell(C0, RR, x, -0.07 + 0.055 * max(0, (abs(x) - 0.18) / 0.085) ** 1.5, 1.025))
    lib.tube(P + 'grin', pts, [0.006] + [0.012] * 9 + [0.006], mouth, H)

    # crown: five layered flame spikes, each on its own pivot so the crown can grow spike by spike
    cr = lib.pivot(P + 'crown', (0, 0, 0), B)
    spikes = []
    for i, (a, h) in enumerate(zip([-66, -34, 0, 34, 66], [0.44, 0.58, 0.7, 0.58, 0.44])):
        a = R(a)
        sp = lib.pivot(f'{P}spike{i}', (0.34 * math.sin(a), 0.02, 0.34 * math.cos(a)), cr, rot=(0, a, 0))
        c = 0.035 * (1 if i % 2 else -1)
        flame(lib, f'{P}cr_b{i}', 0.125, h * 0.72, FR, sp, (0, 0.14, -0.03), d=(0, 0.42, 1), curl=-c, flat=0.9)
        flame(lib, f'{P}cr_r{i}', 0.15, h, FR, sp, (0, 0, 0), bend=(0.05 - 0.07 * math.sin(a), 0), curl=c, flat=0.85)
        flame(lib, f'{P}cr_o{i}', 0.105, h * 0.68, FO, sp, (0, -0.085, 0.0), d=(0, -0.08, 1), curl=c * 0.7, flat=0.75)
        if 1 <= i <= 3:
            flame(lib, f'{P}cr_y{i}', 0.068, h * 0.42, FY, sp, (0, -0.15, -0.01), d=(0, -0.17, 1), flat=0.7)
        spikes.append(sp)
    for i, x in enumerate((-0.2, 0.0, 0.2)):          # swept-back flames so the back of its head is not bald
        flame(lib, f'{P}cr_s{i}', 0.13, 0.4 if i == 1 else 0.33, FR, cr, (x, 0.2, 0.24), d=(x * 1.5, 1, 0.55), bend=(0, 0.1), flat=0.9)
    rig.extras.append((cr, 'flicker'))

    # side wisps curling up
    wisps = []
    for s, nm in ((-1, 'L'), (1, 'R')):
        wp = lib.pivot(P + 'wisp' + nm, (s * 0.38, 0, -0.03), B)
        flame(lib, P + 'w_a' + nm, 0.12, 0.4, FR, wp, (0, 0, 0.03), d=(s, 0, 0.45), bend=(-s * 0.14, 0), flat=0.8, base=0.8)
        flame(lib, P + 'w_b' + nm, 0.095, 0.26, FR, wp, (0, 0.01, -0.05), d=(s, 0, -0.4), bend=(s * 0.05, 0), flat=0.8, base=0.8)
        flame(lib, P + 'w_c' + nm, 0.065, 0.24, FO, wp, (s * 0.03, -0.075, 0.02), d=(s, -0.1, 0.45), bend=(-s * 0.07, 0), flat=0.7, base=0.8)
        rig.extras.append((wp, 'flicker'))
        rig.t_pose[wp.name] = (0, 0, 0)
        wisps.append(wp)

    # flickering flame skirt instead of feet
    bp = lib.pivot(P + 'base', (0, 0, -0.24), B)
    for i in range(9):
        a = TAU * i / 9
        x, y = math.cos(a), math.sin(a)
        flame(lib, f'{P}b_r{i}', 0.115, 0.36 if i % 2 else 0.28, FR, bp, (x * 0.2, y * 0.19, 0.02), d=(x * 0.3, y * 0.3, -1),
              bend=(0.04 if i % 2 else -0.04, 0), seg=10, rings=8)
    for i in range(5):
        a = TAU * (i + 0.5) / 5
        x, y = math.cos(a), math.sin(a)
        flame(lib, f'{P}b_o{i}', 0.085, 0.33, FO, bp, (x * 0.08, y * 0.08 - 0.03, -0.04), d=(x * 0.1, y * 0.1, -1), seg=10, rings=8)
    flame(lib, P + 'b_y', 0.06, 0.3, FY, bp, (0, -0.02, -0.1), d=(0, 0, -1), seg=8, rings=6)
    rig.extras.append((bp, 'flicker'))

    em = lib.pivot(P + 'embers', (0, 0, 0), B)
    for i, (a, r, z, s) in enumerate([(0.4, 0.75, 0.5, 0.03), (2.3, 0.72, 0.2, 0.024), (3.7, 0.78, -0.3, 0.028),
                                      (5.1, 0.7, 0.62, 0.02), (1.4, 0.68, -0.45, 0.022)]):
        lib.sphere(f'{P}ember{i}', (math.cos(a) * r, math.sin(a) * r, z), s, em_o if i % 2 else em_y, em, seg=10)
    rig.extras.append((em, 'spin'))

    rig.attack_origin = (0, -0.5, CZ)
    rig._p = dict(hov=hov, spin=spin, eyes=eyes, mouth=mouthp, crown=cr, spikes=spikes, wisps=wisps, base=bp,
                  embers=em, mats=(FR, FO, FY))
    return rig


# ---------------------------------------------------------------- animation
def animate(A):
    """Spins up out of a fire whirl and grows its crown spike by spike; glides with a pirouette;
    Flame Wheel charge; gets its crown blown flat and regrows it with a wink."""
    lib, r, T, s = A.lib, A.rig, A.T, A.size
    root, B, H = r.root, r.body, r.head
    p = r._p
    hov, spin, mouth, cr, spikes, bp, embers = p['hov'], p['spin'], p['mouth'], p['crown'], p['spikes'], p['base'], p['embers']
    eyeL, eyeR = p['eyes']
    wL, wR = p['wisps']
    FR, FO, FY = p['mats']
    em_y = lib.mat(P + 'emy', '#ffd850', 0.4, emit=3.0)
    D = 1.45 * s

    def glow(f, k):
        k = 1 + (k - 1) * 0.8
        A.emission(FR, f, 0.45 * k); A.emission(FO, f, 0.9 * k); A.emission(FY, f, 1.5 * k)

    def eyes(f, z, zr=None):
        A.key(eyeL, f, scale=(1, 1, z)); A.key(eyeR, f, scale=(1, 1, z if zr is None else zr))

    def jaw(f, open_):                              # 0 = grin, 1 = wide open
        A.key(mouth, f, scale=(1 - 0.12 * open_, 1, 1 + 0.75 * open_), rot=(0.22 * open_, 0, 0))

    def wisps(f, spread, sc=1.0):                   # spread > 0 lifts both wisps
        A.key(wL, f, scale=sc); A.key(wR, f, scale=sc)
        wisp_pose[f] = spread

    wisp_pose = {}

    # ---- send-out: a whirl of fire spins up from the ground, the body winds out of it, the crown grows last
    whirl = lib.pivot(P + 'fx_whirl')
    for j in range(7):
        a = TAU * j / 7
        flame(lib, f'{P}fx_wh{j}', 0.1, 0.75 + 0.15 * (j % 2), FO if j % 2 else FR, whirl, (math.cos(a) * 0.33, math.sin(a) * 0.33, 0),
              d=(-math.sin(a) * 0.55 + math.cos(a) * 0.15, math.cos(a) * 0.55 + math.sin(a) * 0.15, 1), bend=(0.1, 0), seg=8, rings=7)
    A.key(whirl, 0, scale=0.001, rot=(0, 0, 0), absolute=True); A.key(whirl, 15, scale=0.001, absolute=True)
    A.key(whirl, 19, scale=(0.9, 0.9, 0.6), absolute=True); A.key(whirl, 24, scale=(1.15, 1.15, 1.5), absolute=True)
    A.key(whirl, 29, scale=(1.3, 1.3, 1.1), absolute=True); A.key(whirl, 34, scale=(1.6, 1.6, 0.001), absolute=True)
    for f in A.frames(15, 34, 1):
        A.key(whirl, f, rot=(0, 0, (f - 15) * 0.75), absolute=True)
    A.light(P + 'fx_whl', '#ff8a28', (0, -0.6, 0.5), [(15, 0), (20, 60 * s * s), (28, 90 * s * s), (36, 20 * s * s), (44, 70 * s * s), (50, 0)])

    A.key(root, 0, scale=0.001, loc=(0, 0, 0), rot=(0, 0, 0)); A.key(root, 18, scale=0.001)
    A.key(root, 24, scale=(0.7, 0.7, 0.8)); A.key(root, 29, scale=(1.08, 1.08, 1.12)); A.key(root, 33, scale=1)
    A.key(spin, 18, loc=(0, 0, -0.5), rot=(0, 0, -TAU * 2.5))
    A.key(spin, 24, loc=(0, 0, -0.1), rot=(0, 0, -TAU * 1.0))
    A.key(spin, 30, loc=(0, 0, 0.22), rot=(0, 0, -0.5))
    A.key(spin, 35, loc=(0, 0, 0), rot=(0, 0, 0.12)); A.key(spin, 39, rot=(0, 0, 0))
    eyes(18, 0.1); eyes(30, 0.1); eyes(33, 1.15); eyes(37, 1)
    jaw(18, 0); jaw(38, 0)
    order = (0, 4, 1, 3, 2)                          # outer spikes first, the tall middle one last
    for n, i in enumerate(order):
        f0 = 28 + n * 2
        A.key(spikes[i], 18, scale=0.001); A.key(spikes[i], f0, scale=0.001)
        A.key(spikes[i], f0 + 3, scale=(1.2, 1.2, 1.5)); A.key(spikes[i], f0 + 6, scale=0.92); A.key(spikes[i], f0 + 8, scale=1)
    glow(18, 1.8); glow(30, 1); glow(38, 1)
    wisps(18, -0.6, 0.3); wisps(30, 0.5, 1.2); wisps(36, 0)
    # cry: puffs itself up, crown flaring, mouth wide
    A.key(B, 38, scale=1); A.key(B, 41, scale=(0.94, 0.94, 0.92)); A.key(B, 44, scale=(1.16, 1.16, 1.14)); A.key(B, 50, scale=1)
    A.key(cr, 38, scale=1); A.key(cr, 41, scale=0.9); A.key(cr, 44, scale=(1.2, 1.2, 1.35)); A.key(cr, 51, scale=1)
    A.key(H, 38, rot=(0, 0, 0)); A.key(H, 44, rot=(-0.18, 0, 0)); A.key(H, 51, rot=(0, 0, 0))
    jaw(41, 0); jaw(44, 1); jaw(48, 1); jaw(52, 0)
    eyes(41, 1); eyes(44, 0.55); eyes(48, 0.55); eyes(51, 1)
    glow(41, 1); glow(44, 2.1); glow(52, 1)
    wisps(41, -0.2); wisps(44, 0.8, 1.25); wisps(52, 0, 1)

    # ---- idle: smug look to each side, a blink, then a wink at the camera
    A.key(H, 54, rot=(0, 0, 0)); A.key(H, 58, rot=(0.05, 0, 0.34)); A.key(H, 62, rot=(0.05, 0, 0.34))
    A.key(H, 66, rot=(0, 0, -0.3)); A.key(H, 69, rot=(0, 0, -0.3)); A.key(H, 73, rot=(0, 0, 0))
    eyes(58, 1); eyes(60, 0.1); eyes(62, 1); eyes(66, 1); eyes(68, 1, 0.1); eyes(71, 1, 0.1); eyes(73, 1)
    A.key(B, 54, scale=1); A.key(B, 62, scale=(1.03, 1.03, 0.98)); A.key(B, 70, scale=1)

    # ---- walk: a leaning glide along a lazy S, skirt streaming behind, with a rising pirouette in the middle
    A.key(root, 72, rot=(0, 0, 0), loc=(0, 0, 0)); A.key(root, 79, rot=(0, 0, math.pi / 2))
    for f in A.frames(79, 130, 3):
        t = A.ease((f - 79) / 51)
        A.key(root, f, loc=(D * t, math.sin(t * TAU) * 0.16 * s, 0))
    A.key(root, 130, loc=(D, 0, 0), rot=(0, 0, math.pi / 2)); A.key(root, 137, rot=(0, 0, 0))
    A.key(spin, 72, rot=(0, 0, 0), loc=(0, 0, 0))
    A.key(spin, 76, rot=(-0.2, 0, 0))                                    # rears back before setting off
    A.key(spin, 82, rot=(0.38, 0, 0)); A.key(spin, 96, rot=(0.3, 0.1, 0), loc=(0, 0, 0))
    A.key(spin, 100, rot=(0.0, 0, -0.5), loc=(0, 0, -0.06))              # wind-up for the pirouette
    A.key(spin, 106, rot=(0, 0, TAU * 0.6), loc=(0, 0, 0.3))
    A.key(spin, 111, rot=(0, 0, TAU + 0.35), loc=(0, 0, 0.36))
    A.key(spin, 115, rot=(0.1, 0, TAU - 0.08), loc=(0, 0, 0.05))
    A.key(spin, 119, rot=(0.34, -0.1, TAU), loc=(0, 0, 0)); A.key(spin, 128, rot=(0.3, 0, TAU))
    A.key(spin, 133, rot=(-0.12, 0, TAU)); A.key(spin, 138, rot=(0, 0, TAU))
    RZ = TAU
    A.key(B, 96, scale=1); A.key(B, 100, scale=(1.1, 1.1, 0.88)); A.key(B, 106, scale=(0.92, 0.92, 1.12)); A.key(B, 115, scale=(1.06, 1.06, 0.94)); A.key(B, 120, scale=1)
    A.key(cr, 100, scale=1); A.key(cr, 108, scale=(1.15, 1.15, 1.3)); A.key(cr, 118, scale=1)
    wisps(76, -0.3); wisps(84, -0.5); wisps(98, -0.5); wisps(106, 0.9, 1.35); wisps(112, 0.9, 1.35); wisps(119, -0.4, 1); wisps(130, -0.3); wisps(138, 0)
    jaw(100, 0); jaw(106, 0.8); jaw(113, 0.8); jaw(118, 0)
    eyes(104, 1); eyes(107, 0.3); eyes(113, 0.3); eyes(116, 1)
    glow(100, 1); glow(108, 1.8); glow(118, 1)
    for n in range(9):                                                    # embers shed along the way
        f0 = 82 + n * 5
        pos = A.world(bp, f0, (0, 0, -0.25))
        e = lib.sphere(f'{P}fx_trail{n}', pos, 0.035 + 0.01 * (n % 3), em_y, seg=8)
        A.key(e, 0, scale=0.001); A.key(e, f0, scale=0.001); A.key(e, f0 + 2, scale=1)
        A.key(e, f0 + 2, loc=(0, 0, 0)); A.key(e, f0 + 16, loc=(0.05 * (n % 2 * 2 - 1), 0, 0.3), scale=0.001)

    # ---- attack: Flame Wheel. Rears back, spins itself into a ring of fire and rolls into the foe, then bounces home
    aim = math.atan2(2.6, 1.8)
    dist = math.hypot(2.6, 1.8) * s - 0.5 * s
    ring = lib.pivot(P + 'fx_ring', (0, 0, 0), spin)
    for j in range(12):
        a = TAU * j / 12
        y, z = math.cos(a), math.sin(a)
        flame(lib, f'{P}fx_rg{j}', 0.13, 0.5, FO if j % 2 else FY, ring, (0, y * 0.72, z * 0.72), d=(0, z * 0.9 + y * 0.3, -y * 0.9 + z * 0.3),
              flat=0.7, seg=8, rings=7)
    lib.torus(P + 'fx_rgt', (0, 0, 0), 0.74, 0.07, lib.mat(P + 'ringm', '#ffb030', 0.4, emit=3.0, alpha=0.7), ring, rot=(0, math.pi / 2, 0))
    A.key(ring, 0, scale=0.001); A.key(ring, 145, scale=0.001); A.key(ring, 151, scale=(1, 1.1, 1.1)); A.key(ring, 172, scale=1); A.key(ring, 179, scale=0.001)
    A.key(root, 140, rot=(0, 0, 0)); A.key(root, 145, rot=(0, 0, aim)); A.key(root, 178, rot=(0, 0, aim)); A.key(root, 185, rot=(0, 0, 0))
    turns = 6
    roll = [(140, 0), (146, -0.5), (150, 0.4), (154, TAU * 1.2), (163, TAU * 3.6), (172, TAU * 5.3), (179, TAU * turns)]
    path = [(140, 0, 0), (147, 0.32, 0.22), (151, 0.36, 0.16), (155, -0.2 * dist, 0.0), (163, -dist, 0.0),
            (167, -0.75 * dist, 0.55 * s), (173, -0.25 * dist, 0.6 * s), (179, 0, 0.0), (182, 0, 0.1), (185, 0, 0)]
    for f, a in roll:
        A.key(spin, f, rot=(a, 0, RZ))
    for f, y, z in path:
        A.key(spin, f, loc=(0, y, z))
    A.key(spin, 185, rot=(TAU * turns, 0, RZ))
    RX = TAU * turns
    A.key(B, 140, scale=1); A.key(B, 147, scale=(1.12, 0.9, 1.1)); A.key(B, 152, scale=(0.85, 1.12, 1.12)); A.key(B, 163, scale=(0.85, 1.12, 1.12))
    A.key(B, 164, scale=(1.2, 0.75, 1.15)); A.key(B, 167, scale=1); A.key(B, 179, scale=(1.1, 1.1, 0.85)); A.key(B, 183, scale=1)
    A.key(cr, 140, scale=1, rot=(0, 0, 0)); A.key(cr, 147, rot=(-0.3, 0, 0), scale=0.9); A.key(cr, 152, rot=(0, 0, 0), scale=(1.1, 1.1, 1.25)); A.key(cr, 180, scale=1)
    jaw(140, 0); jaw(147, 0.9); jaw(176, 0.9); jaw(182, 0)
    eyes(140, 1); eyes(147, 0.6); eyes(176, 0.6); eyes(181, 1)
    glow(140, 1); glow(150, 2.2); glow(172, 2.0); glow(182, 1)
    wisps(140, 0); wisps(147, 0.7, 1.2); wisps(176, 0.5, 1.2); wisps(183, 0, 1)
    opp = A.world(root, 163) + Vector((math.sin(aim), -math.cos(aim), 0)) * (dist + 0.4 * s) + Vector((0, 0, CZ))
    boom = lib.sphere(P + 'fx_boom', opp, 1, lib.mat(P + 'boom', '#ff7a18', 0.5, emit=5.0, alpha=0.55), seg=16)
    A.key(boom, 0, scale=0.001); A.key(boom, 162, scale=0.001); A.key(boom, 164, scale=0.6 * s); A.key(boom, 168, scale=0.9 * s); A.key(boom, 171, scale=0.001)
    for j in range(8):
        a = TAU * j / 8
        sp = lib.sphere(f'{P}fx_spark{j}', opp, 0.04 * s, em_y, seg=8)
        A.key(sp, 0, scale=0.001); A.key(sp, 163, scale=0.001); A.key(sp, 164, scale=1, loc=(0, 0, 0))
        A.key(sp, 171, loc=(math.cos(a) * 0.9 * s, math.sin(a) * 0.6 * s, (0.2 + 0.3 * (j % 2)) * s), scale=0.9)
        A.key(sp, 176, loc=(math.cos(a) * 1.0 * s, math.sin(a) * 0.7 * s, 0), scale=0.001)
    A.light(P + 'fx_hitl', '#ff8a20', opp + Vector((-0.4 * s, 0.2 * s, 0.3 * s)), [(161, 0), (164, 400 * s * s), (169, 120 * s * s), (176, 0)])
    A.light(P + 'fx_ringl', '#ffa030', (0, -0.3, 0), [(144, 0), (151, 60 * s * s), (172, 50 * s * s), (180, 0)], parent=spin)

    # ---- hit: crown blown flat, tumbles back and sinks, wobbling like jelly
    def sp_rot(f, x=0, y=0, z=0):
        A.key(spin, f, rot=(RX + x, y, RZ + z))
    sp_rot(186); A.key(spin, 186, loc=(0, 0, 0))
    A.key(spin, 190, loc=(-0.12, 0.38, 0.12)); sp_rot(190, -0.75, 0.3, 0)
    A.key(spin, 196, loc=(-0.2, 0.6, -0.3)); sp_rot(196, -0.3, -0.35, 0.3)
    A.key(spin, 201, loc=(-0.22, 0.66, -0.22)); sp_rot(201, 0.12, 0.25, 0.3)
    A.key(spin, 206, loc=(-0.22, 0.68, -0.3)); sp_rot(206, 0, -0.12, 0.25)
    A.key(B, 185, scale=1); A.key(B, 187, scale=(1.25, 0.72, 1.2)); A.key(B, 191, scale=(0.9, 1.15, 0.92)); A.key(B, 196, scale=(1.18, 1.1, 0.78))
    A.key(B, 200, scale=(0.94, 0.96, 1.1)); A.key(B, 204, scale=(1.06, 1.04, 0.92)); A.key(B, 208, scale=1)
    for i, sp in enumerate(spikes):
        A.key(sp, 185, scale=1); A.key(sp, 188 + i % 2, scale=(0.7, 0.7, 0.3)); A.key(sp, 196, scale=(0.6, 0.6, 0.22 + 0.06 * (i % 3)))
        A.key(sp, 206 + i, scale=(0.6, 0.6, 0.25))
    A.key(cr, 185, scale=1); A.key(cr, 210, scale=1)
    A.key(bp, 185, scale=1); A.key(bp, 189, scale=(0.8, 0.8, 0.4)); A.key(bp, 208, scale=(0.8, 0.8, 0.45))
    eyes(185, 1); eyes(187, 0.1); eyes(208, 0.1)
    A.key(mouth, 185, scale=1, rot=(0, 0, 0)); A.key(mouth, 188, scale=(0.5, 1, 1.5), rot=(0.2, 0, 0)); A.key(mouth, 207, scale=(0.5, 1, 1.3), rot=(0.2, 0, 0))
    glow(185, 1); glow(188, 0.3); glow(197, 0.5); glow(200, 0.2); glow(208, 0.3)
    wisps(185, 0); wisps(189, 1.0, 0.7); wisps(197, -0.8, 0.5); wisps(206, -0.7, 0.5)

    # ---- recover: shakes its head, drifts back up, regrows the crown one spike at a time, and winks
    for k, f in enumerate(range(208, 217, 2)):
        sp_rot(f, 0, 0, (0.4 if k % 2 else -0.4) * (1 - k / 6))
    sp_rot(218); A.key(spin, 210, loc=(-0.22, 0.68, -0.3)); A.key(spin, 219, loc=(-0.05, 0.15, 0.12)); A.key(spin, 224, loc=(0, 0, 0))
    eyes(211, 1.15); eyes(214, 1)
    A.key(mouth, 212, scale=1, rot=(0, 0, 0))
    A.key(bp, 214, scale=(1.1, 1.1, 1.3)); A.key(bp, 219, scale=1)
    for n, i in enumerate(order):
        f0 = 211 + n * 2
        A.key(spikes[i], f0 + 3, scale=(1.2, 1.2, 1.55)); A.key(spikes[i], f0 + 6, scale=0.92); A.key(spikes[i], f0 + 8, scale=1)
    glow(211, 0.4); glow(222, 2.3); glow(230, 1.3)
    A.light(P + 'fx_crownl', '#ffb040', A.world(root, 206) + Vector((0, -0.4, 1.6)), [(212, 0), (222, 60 * s * s), (230, 15 * s * s)])
    wisps(212, -0.6, 0.6); wisps(220, 0.7, 1.25); wisps(226, 0.2, 1.1); wisps(230, 0.3, 1.1)
    A.key(B, 216, scale=1); A.key(B, 220, scale=(0.95, 0.95, 0.92)); A.key(B, 224, scale=(1.14, 1.14, 1.12)); A.key(B, 230, scale=(1.05, 1.05, 1.05))
    A.key(cr, 220, scale=1); A.key(cr, 224, scale=(1.15, 1.15, 1.3)); A.key(cr, 230, scale=(1.08, 1.08, 1.15))
    A.key(H, 218, rot=(0, 0, 0)); A.key(H, 224, rot=(-0.14, 0, 0.1)); A.key(H, 230, rot=(-0.1, 0, 0.1))
    jaw(219, 0); jaw(224, 0.8); jaw(230, 0.6)
    eyes(222, 1); eyes(225, 1, 0.1); eyes(230, 1, 0.1)

    # ---- always on: hover bob, crown ripple, wisp and skirt flicker, orbiting embers
    for f in A.frames(16, 230, 2):
        glide = 79 <= f <= 130
        A.key(hov, f, loc=(0, 0, A.wave(f, 26) * 0.045 + (A.wave(f, 13, 0.2) * 0.02 if glide else 0)))
        for i, sp in enumerate(spikes):
            A.key(sp, f, rot=(A.wave(f, 9, i * 0.17) * 0.07 + (-0.25 if glide else 0), A.wave(f, 14, i * 0.21) * 0.09, 0))
        keys = sorted(wisp_pose)
        lo = max([k for k in keys if k <= f], default=keys[0]); hi = min([k for k in keys if k >= f], default=keys[-1])
        t = 0 if hi == lo else A.ease((f - lo) / (hi - lo))
        sprd = wisp_pose[lo] + (wisp_pose[hi] - wisp_pose[lo]) * t
        A.key(wL, f, rot=(A.wave(f, 8) * 0.1, sprd + A.wave(f, 11, 0.3) * 0.12, 0))
        A.key(wR, f, rot=(A.wave(f, 8, 0.5) * 0.1, -sprd + A.wave(f, 11, 0.8) * 0.12, 0))
        A.key(bp, f, rot=(A.wave(f, 7) * 0.08 + (0.55 if glide else 0), A.wave(f, 10, 0.4) * 0.08, f * 0.05))
        A.key(embers, f, rot=(0, 0, -f * 0.07), loc=(0, 0, A.wave(f, 21) * 0.05))


# Phase speeds for render.retime: above 1 is slower and longer, below 1 is quicker.
TIMING = {'send': 1.3, 'idle': 1.2, 'walk': 1.1, 'attack': 1.3, 'hit': 1.1, 'recover': 1.3}
