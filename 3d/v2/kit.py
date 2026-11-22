"""Toolkit v2: sculpted bodies, real feathers, skeletons, node materials.

Conventions: meters, Z up, creature faces -Y, stands on z = 0.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


# ------------------------------------------------------------------ colors
def srgb(c):
    """'#rrggbb' -> linear (r, g, b)."""
    if not isinstance(c, str):
        return tuple(c)
    c = c.lstrip('#')
    v = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in v)


def lerp3(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def ramp3(stops, t):
    """stops = [(t, rgb), ...] sorted; linear rgb interpolation."""
    t = max(stops[0][0], min(stops[-1][0], t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return lerp3(c0, c1, (t - t0) / max(1e-6, t1 - t0))
    return stops[-1][1]


# ------------------------------------------------------------------ scene helpers
def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.empty_display_size = 0.1
    return link(e, parent)


def smooth_obj(o, subsurf=0, auto=False):
    for p in o.data.polygons:
        p.use_smooth = True
    if subsurf:
        m = o.modifiers.new('sub', 'SUBSURF')
        m.levels = 1
        m.render_levels = subsurf
    return o


# ------------------------------------------------------------------ materials (node graphs)
_M = {}


def _bsdf(m):
    return m.node_tree.nodes['Principled BSDF']


def new_mat(name):
    if name in _M:
        return _M[name], True
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    _M[name] = m
    return m, False


def mat_basic(name, color, rough=0.5, metal=0.0, sss=0.0, sss_radius=(0.4, 0.2, 0.1), coat=0.0, sheen=0.0,
              emit=0.0, emit_color=None, transmission=0.0, ior=1.45, alpha=1.0, spec=0.5):
    m, old = new_mat(name)
    if old:
        return m
    b = _bsdf(m)
    b.inputs['Base Color'].default_value = (*srgb(color), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['IOR'].default_value = ior
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = sss_radius
        b.inputs['Subsurface Scale'].default_value = 0.08
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Transmission Weight'].default_value = transmission
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb(emit_color or color), 1)
        b.inputs['Emission Strength'].default_value = emit
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    m.diffuse_color = (*srgb(color), 1)
    return m


def mat_feather(name, rough=0.55, sheen=0.5, sparkle=0.0, sss=0.08):
    """Feathers: color comes from the mesh's 'Col' attribute (base -> tip gradient baked per vertex),
    with a fine barb stripe bump along the length and optional frost sparkle."""
    m, old = new_mat(name)
    if old:
        return m
    nt = m.node_tree
    b = _bsdf(m)
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'Col'
    nt.links.new(attr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Sheen Tint'].default_value = (1, 1, 1, 1)
    b.inputs['Subsurface Weight'].default_value = sss
    b.inputs['Subsurface Radius'].default_value = (0.6, 0.6, 0.8)
    b.inputs['Subsurface Scale'].default_value = 0.02
    # barbs: thin stripes across the vane using the 'barb' UV
    uv = nt.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'barb'
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Y'
    wave.inputs['Scale'].default_value = 60.0
    wave.inputs['Distortion'].default_value = 2.0
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.18
    nt.links.new(uv.outputs['UV'], wave.inputs['Vector'])
    nt.links.new(wave.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    if sparkle:
        vor = nt.nodes.new('ShaderNodeTexVoronoi')
        vor.inputs['Scale'].default_value = 220.0
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp.color_ramp.elements[1].position = 0.06
        ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
        nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac'])
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = sparkle
        nt.links.new(ramp.outputs['Color'], mul.inputs[0])
        b.inputs['Emission Color'].default_value = (0.85, 0.95, 1.0, 1)
        nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    return m


def mat_vcol(name, rough=0.4, coat=0.3, sss=0.0, sss_radius=(0.5, 0.3, 0.1), bump_scale=0.0, bump_strength=0.2, spec=0.5):
    """Generic material that takes its color from the 'Col' attribute (beaks, talons, scales)."""
    m, old = new_mat(name)
    if old:
        return m
    nt = m.node_tree
    b = _bsdf(m)
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'Col'
    nt.links.new(attr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Specular IOR Level'].default_value = spec
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = sss_radius
        b.inputs['Subsurface Scale'].default_value = 0.05
    if bump_scale:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        vor = nt.nodes.new('ShaderNodeTexVoronoi')
        vor.inputs['Scale'].default_value = bump_scale
        vor.feature = 'DISTANCE_TO_EDGE'
        bump = nt.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = bump_strength
        nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
        nt.links.new(vor.outputs['Distance'], bump.inputs['Height'])
        nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_ice(name, tint='#bfefff', emit=0.0):
    m, old = new_mat(name)
    if old:
        return m
    b = _bsdf(m)
    b.inputs['Base Color'].default_value = (*srgb(tint), 1)
    b.inputs['Roughness'].default_value = 0.04
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.31
    b.inputs['Coat Weight'].default_value = 0.5
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb(tint), 1)
        b.inputs['Emission Strength'].default_value = emit
    return m


def mat_knit(name, color):
    """Knitted wool: rib bands + fuzz."""
    m, old = new_mat(name)
    if old:
        return m
    nt = m.node_tree
    b = _bsdf(m)
    b.inputs['Base Color'].default_value = (*srgb(color), 1)
    b.inputs['Roughness'].default_value = 0.85
    b.inputs['Sheen Weight'].default_value = 0.8
    b.inputs['Sheen Roughness'].default_value = 0.6
    b.inputs['Subsurface Weight'].default_value = 0.1
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.2, 0.1)
    b.inputs['Subsurface Scale'].default_value = 0.01
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'RINGS'
    wave.rings_direction = 'X'
    wave.inputs['Scale'].default_value = 90.0
    wave.inputs['Distortion'].default_value = 1.5
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 400.0
    mix = nt.nodes.new('ShaderNodeMath')
    mix.operation = 'ADD'
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.5
    nt.links.new(tc.outputs['Object'], wave.inputs['Vector'])
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(wave.outputs['Fac'], mix.inputs[0])
    nt.links.new(noise.outputs['Fac'], mix.inputs[1])
    nt.links.new(mix.outputs[0], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


# ------------------------------------------------------------------ mesh builder
class MeshBuilder:
    """Accumulates many small parts into one mesh, with a per-vertex color ('Col'), an optional
    'barb' UV, and per-vertex bone weights (vertex groups)."""

    def __init__(self):
        self.v, self.f, self.col, self.uv, self.w = [], [], [], [], []

    def add(self, verts, faces, cols, uvs=None, weights=None, mat=None):
        base = len(self.v)
        self.v += [tuple(p) for p in verts]
        self.f += [tuple(i + base for i in fc) for fc in faces]
        self.col += [tuple(c) for c in cols]
        self.uv += [tuple(u) for u in (uvs or [(0, 0)] * len(verts))]
        if weights is None:
            weights = [{}] * len(verts)
        elif isinstance(weights, dict):
            weights = [weights] * len(verts)
        self.w += weights

    def build(self, name, material, parent=None, smooth=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        for i, c in enumerate(self.col):
            ca.data[i].color = (*c, 1)
        uvl = me.uv_layers.new(name='barb')
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = self.uv[me.loops[li].vertex_index]
        o = bpy.data.objects.new(name, me)
        o.data.materials.append(material)
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        groups = {}
        for i, wd in enumerate(self.w):
            for g, wt in wd.items():
                if g not in groups:
                    groups[g] = o.vertex_groups.new(name=g)
                groups[g].add([i], wt, 'REPLACE')
        return link(o, parent)


def feather_geo(L, W, bend=0.08, cup=0.12, twist=0.0, nl=9, nw=5, base_c=(1, 1, 1), tip_c=(1, 1, 1), mid=None, shaft=True,
                stops=None, edge_c=None, edge_amt=0.25, roundness=0.85, blunt=0.0):
    """One feather in local space: base at origin, length along +Z, width along X, top face +Y-ish.
    Returns verts, faces, colors, uvs. `bend` curls the tip toward -Y (backwards), `cup` curves across."""
    verts, cols, uvs, faces = [], [], [], []
    for i in range(nl + 1):
        t = i / nl
        # vane width profile: narrow base, widest ~55%, rounded tip
        if blunt:
            # flight-feather outline: narrow quill at the base, parallel vane, rounded elliptical tip
            prof = min(1.0, (t + 0.03) / 0.16) ** 0.6
            if t > 1 - blunt:
                u = (t - (1 - blunt)) / blunt
                prof *= math.sqrt(max(0.0, 1 - u * u))
            prof = max(prof, 0.04)
        else:
            prof = math.sin(math.pi * min(1.0, 0.08 + 0.95 * t) ** roundness) * (1 - 0.15 * t)
        z = L * t
        yb = -bend * L * t * t
        tw = twist * t
        for j in range(nw + 1):
            s = j / nw * 2 - 1          # -1..1 across
            x = s * W * 0.5 * prof
            y = yb - cup * W * (1 - s * s) * prof * 0.5
            cx, cy = x * math.cos(tw) - y * math.sin(tw) * 0, y
            verts.append((cx, cy, z))
            if stops:
                c = ramp3(stops, t)
            elif mid:
                c = ramp3([(0, base_c), (0.6, mid), (1.0, tip_c)], t)
            else:
                c = lerp3(base_c, tip_c, t ** 1.3)
            edge = abs(s) ** 3
            cols.append(lerp3(c, edge_c or tip_c, edge_amt * edge))
            uvs.append((s, t))
    for i in range(nl):
        for j in range(nw):
            a = i * (nw + 1) + j
            faces.append((a, a + 1, a + nw + 2, a + nw + 1))
    if shaft:
        # rachis: a thin ridge down the middle
        n0 = len(verts)
        for i in range(nl + 1):
            t = i / nl
            z = L * t
            yb = -bend * L * t * t - cup * W * 0.5 * math.sin(math.pi * min(1.0, 0.08 + 0.95 * t) ** 0.85)
            r = W * 0.045 * (1 - 0.8 * t) + 0.002
            for k in range(4):
                a = k * math.pi / 2
                verts.append((math.cos(a) * r, yb + math.sin(a) * r - r * 0.6, z))
                cols.append(lerp3(base_c, (1, 1, 1), 0.6))
                uvs.append((0, t))
        for i in range(nl):
            for k in range(4):
                a = n0 + i * 4 + k
                b2 = n0 + i * 4 + (k + 1) % 4
                faces.append((a, b2, b2 + 4, a + 4))
    return verts, faces, cols, uvs


def frame_matrix(origin, direction, up):
    """Matrix whose local +Z points along `direction`, local +Y roughly along -up (so the feather's
    top face, which is -Y, faces `up`)."""
    z = Vector(direction).normalized()
    upv = Vector(up).normalized()
    x = upv.cross(z)
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x).normalized()          # y points roughly along -up... flip so top faces up
    m = Matrix((-x, -y, z)).transposed()          # right-handed; local -Y faces `up`
    m = m.to_4x4()
    m.translation = Vector(origin)
    return m


def transform(verts, M):
    return [tuple(M @ Vector(v)) for v in verts]


def loft(sections, ring=16, cols=None, cap=True, shape=None):
    """Tube through sections [(center, rx, rz, forward_dir)] -> verts, faces. rx across X, rz across the
    section's up. cols: per-section rgb."""
    verts, faces, vc = [], [], []
    for si, (c, rx, rz, d) in enumerate(sections):
        d = Vector(d).normalized()
        upv = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
        x = upv.cross(d).normalized()
        y = d.cross(x).normalized()
        for k in range(ring):
            a = 2 * math.pi * k / ring
            mx, my = shape(a, si) if shape else (math.cos(a), math.sin(a))
            p = Vector(c) + x * mx * rx + y * my * rz
            verts.append(tuple(p))
            vc.append(cols[si] if cols else (1, 1, 1))
    n = len(sections)
    for i in range(n - 1):
        for k in range(ring):
            a = i * ring + k
            b = i * ring + (k + 1) % ring
            faces.append((a, b, b + ring, a + ring))
    if cap:
        for idx, ci in ((0, 0), (n - 1, n - 1)):
            ctr = len(verts)
            verts.append(tuple(sections[ci][0]))
            vc.append(cols[ci] if cols else (1, 1, 1))
            for k in range(ring):
                a = idx * ring + k
                b = idx * ring + (k + 1) % ring
                faces.append((a, b, ctr) if idx == n - 1 else (b, a, ctr))
    return verts, faces, vc


# ------------------------------------------------------------------ sculpted body from metaballs
def metaball_body(name, elements, resolution=0.035, smooth_iter=6, remesh=0.022):
    """elements: dicts {type: 'BALL'|'ELLIPSOID'|'CAPSULE', co, radius, size(x,y,z), rot(euler), negative}.
    Returns a smooth single mesh object (no modifiers left)."""
    mb = bpy.data.metaballs.new(name + '_mb')
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = 0.6
    for e in elements:
        el = mb.elements.new(type=e.get('type', 'BALL'))
        el.co = e['co']
        el.radius = e.get('radius', 0.3)
        el.stiffness = e.get('stiff', 2.0)
        if 'size' in e:
            el.size_x, el.size_y, el.size_z = e['size']
        if 'rot' in e:
            from mathutils import Euler
            el.rotation = Euler(e['rot']).to_quaternion()
        el.use_negative = e.get('negative', False)
    mo = bpy.data.objects.new(name + '_mbo', mb)
    link(mo)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(mo.evaluated_get(dg))
    bpy.data.objects.remove(mo)
    o = bpy.data.objects.new(name, me)
    link(o)
    r = o.modifiers.new('remesh', 'REMESH')
    r.mode = 'VOXEL'
    r.voxel_size = remesh
    sm = o.modifiers.new('smooth', 'CORRECTIVE_SMOOTH') if False else o.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.6
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


def surface_samples(obj, n, seed=1, accept=None):
    """Area-weighted random points on obj's surface (world space): [(point, normal), ...]."""
    rnd = random.Random(seed)
    me = obj.data
    mw = obj.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    polys = list(me.polygons)
    areas = [p.area for p in polys]
    total = sum(areas)
    cum = []
    acc = 0
    for a in areas:
        acc += a
        cum.append(acc)
    out = []
    tries = 0
    import bisect
    while len(out) < n and tries < n * 20:
        tries += 1
        r = rnd.random() * total
        pi_ = bisect.bisect_left(cum, r)
        p = polys[min(pi_, len(polys) - 1)]
        vs = [me.vertices[i].co for i in p.vertices]
        # random point in the polygon (fan of triangles from vs[0])
        k = rnd.randrange(1, len(vs) - 1)
        a, b, c = vs[0], vs[k], vs[k + 1]
        u, v = rnd.random(), rnd.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        pt = mw @ (a + (b - a) * u + (c - a) * v)
        nrm = (nm @ p.normal).normalized()
        if accept is None or accept(pt, nrm):
            out.append((pt, nrm))
    return out


def bvh_of(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(obj, dg)


# ------------------------------------------------------------------ skeleton + skinning
def make_armature(name, bones, parent=None):
    """bones: list of (name, head, tail, parent_name, deform). Builds in edit mode via bmesh-free API."""
    arm = bpy.data.armatures.new(name)
    ao = bpy.data.objects.new(name, arm)
    link(ao, parent)
    bpy.context.view_layer.objects.active = ao
    with bpy.context.temp_override(active_object=ao, object=ao, selected_objects=[ao]):
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm.edit_bones
        for bn, h, t, par, deform in bones:
            b = eb.new(bn)
            b.head, b.tail = h, t
            b.use_deform = deform
            if par:
                b.parent = eb[par]
        bpy.ops.object.mode_set(mode='OBJECT')
    ao.data.display_type = 'STICK'
    for pb in ao.pose.bones:
        pb.rotation_mode = 'XYZ'
    return ao


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.length_squared)))
    return (p - (a + ab * t)).length


def skin_weights(points, bone_segs, radii, top=3, falloff=2.0):
    """points: world Vectors. bone_segs: {name: (head, tail)}. radii: {name: influence radius}.
    Returns list of {bone: weight}."""
    out = []
    names = list(bone_segs)
    for p in points:
        ws = []
        for n in names:
            a, b = bone_segs[n]
            d = _seg_dist(p, a, b)
            r = radii.get(n, 0.3)
            w = max(0.0, 1 - d / r) ** falloff
            ws.append((w, n, d))
        ws.sort(reverse=True)
        if ws[0][0] <= 0:
            nearest = min(ws, key=lambda x: x[2])
            out.append({nearest[1]: 1.0})
            continue
        ws = [x for x in ws[:top] if x[0] > 0]
        s = sum(x[0] for x in ws)
        out.append({n: w / s for w, n, _ in ws})
    return out


def bind(obj, arm, weights_by_vertex):
    """Assign per-vertex weights and an Armature modifier."""
    groups = {}
    for i, wd in enumerate(weights_by_vertex):
        for g, w in wd.items():
            if g not in groups:
                groups[g] = obj.vertex_groups.get(g) or obj.vertex_groups.new(name=g)
            groups[g].add([i], w, 'REPLACE')
    m = obj.modifiers.new('arm', 'ARMATURE')
    m.object = arm
    m.use_deform_preserve_volume = True
    # keep the armature modifier first, before subsurf
    while obj.modifiers[0] != m:
        bpy.ops.object.modifier_move_up({'object': obj}, modifier=m.name) if False else None
        obj.modifiers.move(obj.modifiers.find(m.name), 0)
    return m


def bind_rigid(obj, arm, bone):
    """Parent a whole object rigidly to one bone (eyes, beads, crystals)."""
    mw = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = mw
