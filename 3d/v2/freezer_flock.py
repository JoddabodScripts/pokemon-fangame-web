"""Freezer Flock, Scarlet/Violet style: one solid sculpted body.

Head, body, wings, tail, crest, tufts and legs are metaball shapes melted into a single mesh, so
nothing floats. Colors are painted per vertex from the shape each vertex belongs to (clean color
blocks, soft shading). Only the beak, eyes, talons and the knitted scarf are separate pieces, and
each is set into the body.
"""
import math

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector as V

import kit
from kit import srgb as C
import freezer_flock_detailed as D

# shared skeleton, palette and helpers
BONES, SEG, SIDE = D.BONES, D.SEG, D.SIDE
SNOW, SNOW2, FROST, ICE1, ICE2, ICE3, DEEP, NAVY, WHITE = D.SNOW, D.SNOW2, D.FROST, D.ICE1, D.ICE2, D.ICE3, D.DEEP, D.NAVY, D.WHITE
HEAD = D.HEAD
EYES, LOOK = D.EYES, D.LOOK
crystal_geo = D.crystal_geo
pose_bones, display_pose = D.pose_bones, D.display_pose
LEG_Y = C('#f5bd2c')
TALON = C('#22252e')


# ------------------------------------------------------------------ shape elements
class El:
    """One metaball ellipsoid: center, semi-axes (x, y = long axis, z), orientation, paint, skin weights."""

    def __init__(self, co, size, rot=None, paint='body', stops=None, color=None, weights='skin', stiff=2.0, brow=False, k=1.0):
        self.co = V(co)
        self.size = V(size)
        self.R = rot if rot is not None else Matrix.Identity(3)
        self.paint, self.stops, self.color, self.weights, self.stiff, self.brow = paint, stops, color, weights, stiff, brow
        self.k = k          # body shapes were tuned as metaball sizes; k shrinks them to exact ellipsoids


def frame(long_dir, flat_normal):
    """Rotation whose local Y = long_dir and local Z = flat_normal (orthogonalized)."""
    y = V(long_dir).normalized()
    z = V(flat_normal)
    z = (z - y * z.dot(y)).normalized()
    x = y.cross(z).normalized()
    return Matrix((x, y, z)).transposed()


def ell(co, size, rot=(0, 0, 0), **kw):
    return El(co, size, Euler(rot).to_matrix(), **kw)


def body_elements():
    E = []
    # torso
    E.append(ell((0, 0.0, 2.68), (0.82, 0.74, 0.86), (0.18, 0, 0), k=0.8))
    E.append(ell((0, -0.16, 2.92), (0.66, 0.6, 0.6), k=0.8))
    E.append(ell((0, 0.1, 2.15), (0.64, 0.62, 0.62), k=0.8))
    E.append(ell((0, 0.52, 1.84), (0.4, 0.52, 0.34), (-0.6, 0, 0), k=0.8))
    E.append(ell((0, -0.08, 3.45), (0.5, 0.5, 0.42)))
    # head: big and round
    E.append(ell(tuple(HEAD), (0.6, 0.58, 0.55)))
    E.append(ell((0, -0.5, 3.9), (0.32, 0.28, 0.28)))
    # chest ruff: three soft points along the bottom of the bib
    for x in (-0.3, 0.0, 0.3):
        E.append(El((x, -0.62, 2.28 - abs(x) * 0.25), (0.17, 0.3, 0.12), frame((0, -0.25, -1), (0, -1, 0.2)), stops=None))
    for s, sx in SIDE.items():
        e = EYES[s]
        # brow ridge over each eye, slanting down toward the beak
        E.append(El(e + V((0, -0.03, 0.13)), (0.21, 0.13, 0.075), Euler((0.3, sx * 0.4, sx * 0.25)).to_matrix(), brow=True))
        # upper lid: a navy shelf fused into the head that cuts across the top of the eye, low at the beak
        f = LOOK[s]
        r = V((0, 0, 1)).cross(f).normalized()
        u2 = f.cross(r).normalized()
        ang = math.radians(22)
        along = r * sx * math.cos(ang) + u2 * math.sin(ang)
        E.append(El(e + f * 0.1 + u2 * 0.16 + r * sx * 0.01, (0.085, 0.27, 0.06), frame(along, f), paint='solid',
                    color=NAVY, brow=True))
        # cheek tufts sweeping back
        for k, (dz, L) in enumerate(((0.0, 0.3), (-0.17, 0.24))):
            root = V((sx * 0.4, -0.3, 3.86 + dz))
            d = V((sx * 0.6, 1.0, -0.25 - 0.2 * k))
            E.append(El(root + d.normalized() * L * 0.55, (0.13, L, 0.1), frame(d, (sx * 1, 0, 0.4))))
        # shoulders
        E.append(ell((sx * 0.72, 0.12, 3.08), (0.32, 0.26, 0.22)))
        # feathered thigh tapering into a fringe of soft points around the ankle
        E.append(ell((sx * 0.44, 0.02, 1.68), (0.31, 0.34, 0.46), k=0.8))
        for k in range(6):
            a = 2 * math.pi * k / 6 + 0.3
            out = V((math.cos(a), math.sin(a), 0))
            d = out * 0.45 + V((0, 0, -1))
            c = V((sx * 0.46, -0.02, 1.3)) + out * 0.17 + d.normalized() * 0.08
            E.append(El(c, (0.09, 0.16, 0.06), frame(d, out)))
    return E


def crest_elements():
    E = []
    st = [(0, SNOW), (0.4, SNOW), (0.62, ICE1), (0.85, ICE2), (1, ICE3)]
    for x, L, up in ((0.0, 0.85, 0.75), (-0.2, 0.66, 0.5), (0.2, 0.66, 0.5), (-0.36, 0.44, 0.3), (0.36, 0.44, 0.3)):
        root = HEAD + V((x, 0.0, 0.42 - abs(x) * 0.35))
        d = V((x * 0.6, 1.0, up))
        E.append(El(root + d.normalized() * L * 0.75, (0.12, L, 0.09), frame(d, (x * 1.5, -0.3, 1)), paint='grad', stops=st,
                    weights={'head': 1.0}))
    return E


WING_ST = {
    'arm': [(0, SNOW), (1, SNOW)],
    'covert': [(0, SNOW), (0.6, SNOW), (1, FROST)],
    'secondary': [(0, SNOW2), (0.35, ICE1), (0.75, ICE2), (0.9, ICE3), (1, ICE3)],
    'primary': [(0, FROST), (0.3, ICE2), (0.7, ICE3), (0.86, DEEP), (1, DEEP)],
    'tertial': [(0, SNOW), (0.6, FROST), (1, ICE1)],
}


def wing_elements(s):
    sx = SIDE[s]
    S, E_, W_ = SEG['shoulder.' + s], SEG['forearm.' + s], SEG['hand.' + s]
    out = []
    up = V((0, 0, 1))
    bones = (('shoulder.' + s, S), ('forearm.' + s, E_), ('hand.' + s, W_))
    # bony leading edge and covert plates riding on each bone
    for bn, (h, t) in bones:
        d = t - h
        out.append(El((h + t) / 2 + V((0, -0.02, 0)), (0.17, d.length / 2 + 0.12, 0.11), frame(d, up), paint='grad',
                      stops=WING_ST['arm'], weights={bn: 1.0}))
        out.append(El((h + t) / 2 + V((0, 0.36, -0.01)), (0.4, d.length / 2 + 0.1, 0.08), frame(d, up), paint='grad',
                      stops=WING_ST['covert'], weights={bn: 1.0}))
    # tertials near the body
    for k in range(3):
        root = S[0].lerp(S[1], 0.15 + 0.3 * k)
        d = V((sx * -0.1, 1, -0.05))
        out.append(El(root + V((0, 0.3, 0)) + d.normalized() * 0.5, (0.22, 0.55, 0.06), frame(d, up), paint='grad',
                      stops=WING_ST['tertial'], weights={'shoulder.' + s: 1.0}))
    # secondaries: broad lobes along the arm, rounded ends make the scalloped trailing edge
    n = 8
    for k in range(n):
        f = k / (n - 1)
        if f < 0.25:
            root, bn = S[0].lerp(S[1], 0.7 + f * 1.2), 'shoulder.' + s
        else:
            root, bn = E_[0].lerp(E_[1], (f - 0.25) / 0.75), 'forearm.' + s
        d = V((sx * 0.08 * f, 1, -0.04))
        L = 0.72 - 0.06 * f
        out.append(El(root + V((0, 0.32, 0)) + d.normalized() * L * 0.85, (0.2, L, 0.06), frame(d, up), paint='grad',
                      stops=WING_ST['secondary'], weights={bn: 1.0}))
    # primaries: five long fingers fanning from the hand
    for k in range(5):
        f = k / 4
        root = W_[0].lerp(W_[1], 0.2 + 0.75 * f) + V((0, 0.1, 0))
        ang = math.radians(18 + 58 * f)
        d = V((sx * math.sin(ang), math.cos(ang), 0))
        L = 0.78 + 0.18 * math.sin(math.pi * (0.2 + 0.6 * f))
        out.append(El(root + d * L * 0.9, (0.17, L, 0.055), frame(d, up), paint='grad', stops=WING_ST['primary'],
                      weights={'hand.' + s: 1.0}))
    # primary coverts over the hand
    out.append(El(W_[0].lerp(W_[1], 0.5) + V((sx * 0.05, 0.3, 0.02)), (0.36, 0.6, 0.07), frame(W_[1] - W_[0], up),
                  paint='grad', stops=WING_ST['covert'], weights={'hand.' + s: 1.0}))
    return out


def tail_elements():
    out = []
    t0, t1 = SEG['tail']
    axis = V((0, 1, -0.75)).normalized()
    nrm = V((0, 0.6, 1.0))
    # thick wedge where the fan leaves the body, so it never reads as a needle from the side
    out.append(El(t0 + axis * 0.35 + V((0, 0, 0.02)), (0.3, 0.5, 0.14), frame(axis, nrm), paint='grad',
                  stops=[(0, SNOW), (1, SNOW2)], weights={'tail': 1.0}))
    st = [(0, SNOW), (0.4, SNOW2), (0.7, ICE1), (0.9, ICE2), (1, ICE3)]
    for k in range(5):
        a = (k / 4 * 2 - 1) * math.radians(34)
        d = Matrix.Rotation(a, 3, (nrm - axis * nrm.dot(axis)).normalized()) @ axis
        L = 0.95 - 0.1 * abs(k - 2)
        out.append(El(t0 + d * (L * 0.85 + 0.05), (0.3, L, 0.075), frame(d, nrm), paint='grad', stops=st, weights={'tail': 1.0}))
    return out


def leg_elements():
    out = []
    for s, sx in SIDE.items():
        k0, k1 = SEG['shin.' + s]
        out.append(El((k0 + k1) / 2 + V((0, 0, -0.04)), (0.12, (k1 - k0).length / 2 + 0.06, 0.12), frame(k1 - k0, (0, -1, 0)),
                      paint='solid', color=LEG_Y, weights={'shin.' + s: 1.0}))
        for yaw, L in ((-0.45, 0.26), (0.0, 0.3), (0.45, 0.26), (math.pi, 0.18)):
            d = V((math.sin(yaw) * sx if yaw != math.pi else 0, -math.cos(yaw), -0.25))
            out.append(El(k1 + V((0, 0, -0.06)) + d.normalized() * L * 0.85, (0.085, L, 0.075), frame(d, (0, 0, 1)),
                          paint='solid', color=LEG_Y, weights={'foot.' + s: 1.0}))
    return out


BODY_K = 0.8      # body shapes were tuned as metaball sizes; exact ellipsoids come out bigger


def all_elements():
    B = body_elements()
    for e in B:
        e.size = e.size * e.k
    E = B + crest_elements() + tail_elements() + leg_elements()
    for s in 'LR':
        E += wing_elements(s)
    return E


# ------------------------------------------------------------------ sculpt
STIFF = 5.0
ISO = math.sqrt(1 - (0.6 / STIFF) ** (1 / 3))      # where a lone element's surface sits, as a fraction of its size


def metaballs(name, E, resolution=0.02):
    """Smooth union of the shapes: metaball ellipsoids sized so each one alone matches its exact
    semi-axes; where shapes meet, their fields add up into soft fillets instead of hard creases."""
    mb = bpy.data.metaballs.new(name + '_mb')
    mb.resolution = mb.render_resolution = resolution
    mb.threshold = 0.6
    for e in E:
        el = mb.elements.new(type='ELLIPSOID')
        el.co = e.co
        el.radius = 1.0
        el.stiffness = STIFF
        sz = e.size / ISO
        el.size_x, el.size_y, el.size_z = sz
        el.rotation = e.R.to_quaternion()
    mo = bpy.data.objects.new(name + '_mbo', mb)
    kit.link(mo)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(mo.evaluated_get(dg))
    bpy.data.objects.remove(mo)
    o = bpy.data.objects.new(name, me)
    kit.link(o)
    return o


def remesh(o, voxel=0.02, smooth_iter=3):
    r = o.modifiers.new('remesh', 'REMESH')
    r.mode = 'VOXEL'
    r.voxel_size = voxel
    sm = o.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = smooth_iter
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear()
    old = o.data
    o.data = me2
    bpy.data.meshes.remove(old)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def place_eyes():
    """Raycast where each eye meets the head (on a quick probe without the brows), then sink it in."""
    B = [e for e in body_elements() if not e.brow]
    for e in B:
        e.size = e.size * e.k
    probe = metaballs('ffk_probe', B, resolution=0.04)
    remesh(probe, voxel=0.04, smooth_iter=4)
    bvh = kit.bvh_of(probe)
    for s in SIDE:
        look = LOOK[s]
        hit = bvh.ray_cast(HEAD + look * 1.5, -look)[0]
        EYES[s] = hit - look * 0.06
    bpy.data.objects.remove(probe)


# ------------------------------------------------------------------ paint + skin (vectorized)
def body_paint(P):
    """Snow white with a pale frost back and nape and the navy angry brow."""
    n = len(P)
    col = np.tile(np.array(SNOW), (n, 1))

    def sm(e0, e1, x):
        t = np.clip((x - e0) / (e1 - e0), 0, 1)
        return t * t * (3 - 2 * t)
    back = sm(0.15, 0.7, P[:, 1]) * sm(1.8, 2.6, P[:, 2]) * (1 - sm(3.3, 3.7, P[:, 2]))
    col = col + (np.array(FROST) - col) * (back * 0.8)[:, None]
    nape = sm(0.0, 0.5, P[:, 1]) * sm(3.6, 4.1, P[:, 2])
    col = col + (np.array(kit.lerp3(FROST, ICE1, 0.35)) - col) * (nape * 0.75)[:, None]
    # angry brows: crisp slanted wedges just above each eye, low at the beak and rising outward
    up = np.array((0.0, 0.0, 1.0))
    for s, sx in SIDE.items():
        e = np.array(EYES[s])
        f = np.array(LOOK[s])
        r = np.cross(up, f)
        r /= np.linalg.norm(r)
        u2 = np.cross(f, r)
        v = P - e
        u = (v @ r) * sx                     # + away from the beak
        w = v @ u2                           # up across the face
        fw = v @ f
        low = -0.035 + 0.3 * (u + 0.22)
        high = low + 0.2 - 0.09 * np.clip((u + 0.22) / 0.46, 0, 1)
        inside = (u > -0.22) & (u < 0.24) & (w > low) & (w < high) & (fw > -0.05)
        col[inside & False] = NAVY        # the brow is now a sculpted lid; keep the paint off
    # three ice "beads" down the chest: crisp diamonds with a darker rim
    front = (P[:, 1] < -0.2)
    for zc, sz in ((2.95, 1.0), (2.68, 0.9), (2.43, 0.78)):
        dd = np.abs(P[:, 0]) / (0.11 * sz) + np.abs(P[:, 2] - zc) / (0.13 * sz)
        col[front & (dd < 1.0)] = ICE2
        col[front & (dd < 0.72)] = ICE1
    return col


def ramp_np(stops, t):
    xs = [s[0] for s in stops]
    return np.stack([np.interp(t, xs, [s[1][i] for s in stops]) for i in range(3)], axis=1)


def paint_and_skin(o, E):
    me = o.data
    P = np.array([v.co[:] for v in me.vertices])
    n = len(P)
    # how deep each vertex sits inside each element (smaller = more inside)
    R = np.zeros((len(E), n))
    T = np.zeros((len(E), n))
    for i, e in enumerate(E):
        Rm = np.array(e.R)                     # columns = local axes
        q = (P - np.array(e.co)) @ Rm / np.array(e.size)
        R[i] = np.linalg.norm(q, axis=1)
        T[i] = np.clip((q[:, 1] + 1) / 2, 0, 1)
    order = np.argsort(R, axis=0)
    i1, i2 = order[0], order[1]
    r1 = R[i1, np.arange(n)]
    r2 = R[i2, np.arange(n)]
    # colors: each element's paint, softly blended with the runner-up only right at the seam
    body_c = body_paint(P)

    def color_of(idx):
        out = np.zeros((n, 3))
        for i, e in enumerate(E):
            m = idx == i
            if not m.any():
                continue
            if e.paint == 'body':
                out[m] = body_c[m]
            elif e.paint == 'solid':
                out[m] = e.color
            else:
                out[m] = ramp_np(e.stops, T[i, m])
        return out
    c1, c2 = color_of(i1), color_of(i2)
    k = 0.5 * np.clip(1 - (r2 - r1) / 0.06, 0, 1)
    col = c1 + (c2 - c1) * k[:, None]
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.hstack([col, np.ones((n, 1))]).astype(np.float32).ravel())

    # skin weights: element weights, or distance-to-bone skinning for the body shapes
    body_bones = {k_: SEG[k_] for k_ in ('hips', 'chest', 'neck', 'head', 'tail', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R',
                                         'shoulder.L', 'shoulder.R')}
    radii = dict(hips=0.7, chest=0.75, neck=0.45, head=0.7, tail=0.45)
    for s in 'LR':
        radii.update({'thigh.' + s: 0.4, 'shin.' + s: 0.25, 'shoulder.' + s: 0.3})
    skin = kit.skin_weights([V(p) for p in P], body_bones, radii, top=3, falloff=2.0)

    def weights_of(i, vi):
        e = E[i]
        return skin[vi] if e.weights == 'skin' else e.weights
    kb = 0.5 * np.clip(1 - (r2 - r1) / 0.35, 0, 1)
    W = []
    for vi in range(n):
        a = weights_of(i1[vi], vi)
        b = weights_of(i2[vi], vi)
        t = kb[vi]
        w = {}
        for g, x in a.items():
            w[g] = w.get(g, 0) + x * (1 - t)
        for g, x in b.items():
            w[g] = w.get(g, 0) + x * t
        W.append(w)
    return W


# ------------------------------------------------------------------ separate set-in pieces
def talons(arm):
    mb = kit.MeshBuilder()
    for s, sx in SIDE.items():
        k1 = SEG['shin.' + s][1]
        for yaw, L in ((-0.45, 0.26), (0.0, 0.3), (0.45, 0.26), (math.pi, 0.18)):
            d = V((math.sin(yaw) * sx if yaw != math.pi else 0, -math.cos(yaw), -0.25)).normalized()
            tip = k1 + V((0, 0, -0.06)) + d * L * 1.65
            dh = V((d.x, d.y, 0)).normalized()
            secs = []
            for i in range(8):
                t = i / 7
                p = tip - dh * 0.06 + dh * (0.15 * math.sin(t * 1.3)) + V((0, 0, -0.13 * (1 - math.cos(t * 1.3))))
                dd = (dh * math.cos(t * 1.3) + V((0, 0, -1)) * math.sin(t * 1.3)).normalized()
                r = 0.05 * (1 - t) ** 0.8 + 0.004
                secs.append((p, r, r * 1.25, dd))
            vs, fs, vc = kit.loft(secs, ring=12, cols=[TALON] * len(secs))
            mb.add(vs, fs, vc, None, {'foot.' + s: 1.0})
    o = mb.build('ffk_talons', kit.mat_vcol('ffk_talonm', rough=0.3, coat=0.4))
    o.modifiers.new('arm', 'ARMATURE').object = arm
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    return o


def eyes(arm):
    for s in 'LR':
        D.snowflake_eye(arm, s)
        lid = bpy.data.objects.get('ffk_lid.' + s)
        if lid:
            bpy.data.objects.remove(lid)


def body_material():
    m, old = kit.new_mat('ffk_sv')
    if old:
        return m
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'Col'
    nt.links.new(attr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55
    b.inputs['Sheen Weight'].default_value = 0.35
    b.inputs['Sheen Roughness'].default_value = 0.4
    b.inputs['Subsurface Weight'].default_value = 0.06
    b.inputs['Subsurface Radius'].default_value = (0.8, 0.85, 1.0)
    b.inputs['Subsurface Scale'].default_value = 0.05
    b.inputs['Specular IOR Level'].default_value = 0.35
    return m


# ------------------------------------------------------------------ assemble
def build_body(arm):
    E = all_elements()
    o = metaballs('ffk_body', E, resolution=0.03)
    remesh(o, voxel=0.02, smooth_iter=3)
    W = paint_and_skin(o, E)
    o.data.materials.append(body_material())
    kit.bind(o, arm, W)
    return o


def build(steps=None):
    tick = steps or (lambda label: None)
    root = kit.empty('Freezer Flock')
    arm = kit.make_armature('ffk_rig', BONES, parent=root)
    tick('skeleton')
    place_eyes()
    body = build_body(arm)
    tick('body')
    eyes(arm)
    tick('eyes')
    D.beak(arm)
    tick('beak')
    talons(arm)
    tick('talons')
    D.scarf(arm)
    tick('scarf')
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers):
            o.parent = arm
        elif o.type == 'MESH' and o.parent is None:
            o.parent = root
    return dict(root=root, arm=arm, body=body)
