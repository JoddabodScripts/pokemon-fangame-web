"""Shared building blocks for the Scarlet/Violet-style models.

A model is a list of El shapes (metaball ellipsoids). They melt into one smooth mesh, then every
vertex takes its color and its bone weights from the shape it sits inside. Small hard pieces
(eyes, glowing stars) are separate meshes set into the body.
"""
import math

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector as V

import kit
from kit import srgb as C

STIFF = 5.0
ISO = math.sqrt(1 - (0.6 / STIFF) ** (1 / 3))      # where a lone element's surface sits, as a fraction of its size


class El:
    """One metaball ellipsoid: center, semi-axes (x, y = long axis, z), orientation, paint, skin weights.

    paint: 'body' uses the model's body paint, 'solid' uses color, 'grad' runs stops along local Y,
    or a function (q) -> (rgb array, glow array) of the vertex's local coords, scaled so the surface is ~1.
    """

    def __init__(self, co, size, rot=None, paint='body', stops=None, color=None, glow=0.0, weights='skin', probe=True):
        self.co = V(co)
        self.size = V(size)
        self.R = rot if rot is not None else Matrix.Identity(3)
        self.paint, self.stops, self.color, self.glow = paint, stops, color, glow
        self.weights = weights
        self.probe = probe          # False: leave it out of the quick probe used to find where the eyes sit


def frame(long_dir, flat_normal):
    """Rotation whose local Y = long_dir and local Z = flat_normal (orthogonalized)."""
    y = V(long_dir).normalized()
    z = V(flat_normal)
    z = (z - y * z.dot(y)).normalized()
    x = y.cross(z).normalized()
    return Matrix((x, y, z)).transposed()


def ell(co, size, rot=(0, 0, 0), **kw):
    return El(co, size, Euler(rot).to_matrix(), **kw)


def mirror(E):
    """Copy every element with x > 0 to the other side."""
    out = list(E)
    F = Matrix.Diagonal((-1, 1, 1))
    for e in E:
        if e.co.x > 1e-4:
            m = El(V((-e.co.x, e.co.y, e.co.z)), e.size, F @ e.R @ F, e.paint, e.stops, e.color, e.glow,
                   _flip_w(e.weights), e.probe)
            out.append(m)
    return out


def _flip_w(w):
    if isinstance(w, dict):
        return {(k[:-1] + ('R' if k.endswith('L') else 'L')) if k[-2:] in ('.L', '.R') else k: v for k, v in w.items()}
    return w


def tube(points, radii, flat=1.0, normal=(0, 0, 1), **kw):
    """A chain of overlapping ellipsoids along a polyline: a smooth tapering limb, tail or ear."""
    out = []
    pts = [V(p) for p in points]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = b - a
        r = (radii[i] + radii[i + 1]) / 2
        out.append(El((a + b) / 2, (r, d.length / 2 + r * 0.55, r * flat), frame(d, normal), **kw))
    return out


# ------------------------------------------------------------------ sculpt
def metaballs(name, E, resolution=0.02):
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


def ramp_np(stops, t):
    xs = [s[0] for s in stops]
    return np.stack([np.interp(t, xs, [s[1][i] for s in stops]) for i in range(3)], axis=1)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def paint_and_skin(o, E, body_paint, bone_segs, radii, seam=0.06, wseam=0.35):
    """Vertex colors ('Col'), glow ('Glow') and bone weights from the shape each vertex sits in."""
    me = o.data
    P = np.array([v.co[:] for v in me.vertices])
    n = len(P)
    R = np.zeros((len(E), n))
    Q = []
    for i, e in enumerate(E):
        q = (P - np.array(e.co)) @ np.array(e.R) / np.array(e.size)
        R[i] = np.linalg.norm(q, axis=1)
        Q.append(q)
    order = np.argsort(R, axis=0)
    i1, i2 = order[0], order[1]
    r1 = R[i1, np.arange(n)]
    r2 = R[i2, np.arange(n)]
    body_c, body_g = body_paint(P)

    def color_of(idx):
        col = np.zeros((n, 3))
        glow = np.zeros(n)
        for i, e in enumerate(E):
            m = idx == i
            if not m.any():
                continue
            if e.paint == 'body':
                col[m], glow[m] = body_c[m], body_g[m]
            elif e.paint == 'solid':
                col[m], glow[m] = e.color, e.glow
            elif e.paint == 'grad':
                col[m] = ramp_np(e.stops, np.clip((Q[i][m, 1] + 1) / 2, 0, 1))
                glow[m] = e.glow
            else:
                c, g = e.paint(Q[i][m], P[m], body_c[m], body_g[m])
                col[m], glow[m] = c, g
        return col, glow
    (c1, g1), (c2, g2) = color_of(i1), color_of(i2)
    k = 0.5 * np.clip(1 - (r2 - r1) / seam, 0, 1)
    col = c1 + (c2 - c1) * k[:, None]
    glow = g1 + (g2 - g1) * k
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.hstack([col, np.ones((n, 1))]).astype(np.float32).ravel())
    ga = me.attributes.new('Glow', 'FLOAT', 'POINT')
    ga.data.foreach_set('value', glow.astype(np.float32))

    skin = kit.skin_weights([V(p) for p in P], bone_segs, radii, top=3, falloff=2.0)
    kb = 0.5 * np.clip(1 - (r2 - r1) / wseam, 0, 1)
    W = []
    for vi in range(n):
        a = E[i1[vi]].weights
        b = E[i2[vi]].weights
        a = skin[vi] if a == 'skin' else a
        b = skin[vi] if b == 'skin' else b
        t = kb[vi]
        w = {}
        for g, x in a.items():
            w[g] = w.get(g, 0) + x * (1 - t)
        for g, x in b.items():
            w[g] = w.get(g, 0) + x * t
        W.append(w)
    return W


def body_material(name, rough=0.6, sheen=0.5, sss=0.08, glow=6.0):
    """Vertex-colored fur: soft sheen, a touch of subsurface, and emission where 'Glow' is painted."""
    m, old = kit.new_mat(name)
    if old:
        return m
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'Col'
    nt.links.new(attr.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(attr.outputs['Color'], b.inputs['Emission Color'])
    ga = nt.nodes.new('ShaderNodeAttribute')
    ga.attribute_name = 'Glow'
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = glow
    nt.links.new(ga.outputs['Fac'], mul.inputs[0])
    nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Sheen Roughness'].default_value = 0.35
    b.inputs['Subsurface Weight'].default_value = sss
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.6, 0.4)
    b.inputs['Subsurface Scale'].default_value = 0.04
    b.inputs['Specular IOR Level'].default_value = 0.35
    return m


def build_body(name, E, arm, body_paint, bone_segs, radii, mat, resolution=0.03, voxel=0.02, smooth_iter=3):
    o = metaballs(name, E, resolution=resolution)
    remesh(o, voxel=voxel, smooth_iter=smooth_iter)
    W = paint_and_skin(o, E, body_paint, bone_segs, radii)
    o.data.materials.append(mat)
    kit.bind(o, arm, W)
    return o


def probe_hit(E, origin, direction, voxel=0.03):
    """Where a ray first hits the fused body (built quickly, without the shapes marked probe=False)."""
    B = [e for e in E if e.probe]
    o = metaballs('probe', B, resolution=voxel * 1.5)
    remesh(o, voxel=voxel, smooth_iter=3)
    bvh = kit.bvh_of(o)
    hits = []
    for org, d in zip(origin, direction):
        hits.append(bvh.ray_cast(V(org), V(d).normalized())[0])
    bpy.data.objects.remove(o)
    return hits


# ------------------------------------------------------------------ eyes
def eye_mesh(mb, center, look, up, rx, rz, depth, iris, pupil, rim, shine, weights, iris_r=0.78, pupil_r=0.42,
             tilt=0.0, rings=22, segs=36, slit=None):
    """A glossy cartoon eye: a shallow oval dome set into the face. The iris, pupil and two shine spots
    are painted into the vertex colors, so it stays one clean surface."""
    f = V(look).normalized()
    r = V(up).cross(f).normalized()            # sideways
    u = f.cross(r).normalized()                # up across the face
    ca, sa = math.cos(tilt), math.sin(tilt)
    r, u = r * ca + u * sa, u * ca - r * sa
    vs, fs, cs = [], [], []
    for i in range(rings + 1):
        th = (math.pi / 2) * i / rings          # 0 = front of the dome, pi/2 = rim
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            x, z = math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph)
            y = math.cos(th)
            p = V(center) + r * (x * rx) + u * (z * rz) + f * (y * depth)
            vs.append(tuple(p))
            # paint: iris centered a little low, pupil inside, rim dark at the edge
            ix, iz = x, z + 0.08
            d = math.sqrt(ix * ix + iz * iz)
            if slit:
                # cat eye: a vertical slit pupil inside a round iris
                c = kit.ramp3([(0, iris[0]), (iris_r * 0.45, iris[1]), (iris_r - 0.02, iris[2]), (iris_r + 0.03, rim), (1, rim)], d)
                if (ix / slit[0]) ** 2 + (iz / slit[1]) ** 2 < 1:
                    c = pupil
            else:
                c = kit.ramp3([(0, pupil), (pupil_r - 0.04, pupil), (pupil_r + 0.02, iris[0]), (iris_r * 0.75, iris[1]),
                               (iris_r - 0.02, iris[2]), (iris_r + 0.03, rim), (1, rim)], d)
            # lower iris glow
            if d < iris_r and iz < -0.1:
                c = kit.lerp3(c, iris[3], min(1, (-0.1 - iz) * 2.2) * 0.6)
            for (sx_, sz_, rr) in shine:
                if (x - sx_) ** 2 + (z - sz_) ** 2 < rr * rr:
                    c = (1.0, 1.0, 1.0)
            cs.append(c)
    for i in range(rings):
        for j in range(segs):
            a = i * segs + j
            b = i * segs + (j + 1) % segs
            fs.append((a, b, b + segs, a + segs))
    # front cap
    ctr = len(vs)
    vs.append(tuple(V(center) + f * depth * 1.0005))
    cs.append(cs[0])
    for j in range(segs):
        fs.append((ctr, (j + 1) % segs, j))
    mb.add(vs, fs, cs, None, weights)


def eye_material(name):
    return kit.mat_vcol(name, rough=0.08, coat=1.0, spec=0.6)


# ------------------------------------------------------------------ star
def star_geo(R, r_in, depth, pts=5, rings=6, rot=0.0):
    """A puffy five-pointed star in the local XZ plane, thickness along Y (a pillow, not a flat cutout)."""
    outline = []
    n_out = pts * 2
    sub = 6
    corners = []
    for k in range(n_out):
        a = rot + math.pi / 2 + 2 * math.pi * k / n_out
        rr = R if k % 2 == 0 else r_in
        corners.append((math.cos(a) * rr, math.sin(a) * rr))
    for k in range(n_out):
        x0, z0 = corners[k]
        x1, z1 = corners[(k + 1) % n_out]
        for s in range(sub):
            t = s / sub
            outline.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t))
    m = len(outline)
    vs, fs = [], []
    # front half and back half, each as rings shrinking toward the center
    for side in (-1, 1):
        base = len(vs)
        for i in range(rings + 1):
            s = 1 - i / rings                       # 1 at the outline, 0 at the center
            h = math.sqrt(max(0.0, 1 - s * s)) * 0.85 + 0.15 * (1 - s)
            for (x, z) in outline:
                vs.append((x * s, side * depth * h, z * s))
        for i in range(rings):
            for j in range(m):
                a = base + i * m + j
                b = base + i * m + (j + 1) % m
                f = (a, b, b + m, a + m)
                fs.append(f if side > 0 else f[::-1])
    return vs, fs


def star(arm, prefix, loc, R, name, bone, face=(0, -1, 0.15), depth=0.07, color='#ffa914', emit=0.6, spin=0.0):
    """A glowing puffy star set onto the body, rigidly weighted to one bone."""
    import bmesh
    vs, fs = star_geo(R, R * 0.47, depth, rot=spin)
    M = V((0, -1, 0)).rotation_difference(V(face).normalized()).to_matrix().to_4x4()
    M.translation = V(loc)
    mb = kit.MeshBuilder()
    mb.add(kit.transform(vs, M), fs, [C(color)] * len(vs), None, {bone: 1.0})
    o = mb.build(prefix + name, kit.mat_basic(prefix + 'starm', color, rough=0.3, emit=emit, emit_color=color, coat=0.5))
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(o.data)
    bm.free()
    o.modifiers.new('arm', 'ARMATURE').object = arm
    sub = o.modifiers.new('sub', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    return o


def star_light(prefix, loc, power, parent=None, name='starlight'):
    d = bpy.data.lights.new(prefix + name, 'POINT')
    d.energy = power
    d.color = (1.0, 0.8, 0.35)
    d.shadow_soft_size = 0.15
    o = bpy.data.objects.new(prefix + name, d)
    o.location = loc
    kit.link(o, parent)
    return o
