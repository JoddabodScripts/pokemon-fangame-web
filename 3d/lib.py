"""Modeling toolkit for the Star Region 3D prototypes.

Each Pokemon lives in models/<key>.py and defines build(lib) -> Rig.
Conventions:
  * Blender units are meters, Z is up.
  * The creature stands on z = 0, centered on the origin, FACING -Y (toward the camera).
  * Every moving part is a child of a pivot empty placed at its joint. The animation
    system only rotates/scales/moves pivots, so put each pivot where the joint is.
  * Build at "display size": about 1.0-2.0 m tall or long. The real height goes in
    Rig.height_cm and the game scales it later.
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

# ---------------------------------------------------------------- materials
_MATS = {}


def mat(name, color, rough=0.5, emit=0.0, emit_color=None, sss=0.0, metal=0.0,
        alpha=1.0, coat=0.0, transmission=0.0):
    """Principled material. color/emit_color are (r, g, b) in 0-1 or '#rrggbb'."""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    c = _rgb(color)
    b.inputs['Base Color'].default_value = (*c, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Transmission Weight'].default_value = transmission
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (c[0] + .2, c[1] + .1, c[2] + .1)
        b.inputs['Subsurface Scale'].default_value = 0.05
    if emit:
        b.inputs['Emission Color'].default_value = (*_rgb(emit_color or color), 1)
        b.inputs['Emission Strength'].default_value = emit
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'
    m.diffuse_color = (*c, 1)
    _MATS[name] = m
    return m


def _rgb(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        srgb = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        # hex colors are sRGB; Blender wants linear
        return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in srgb)
    return tuple(c)


# ---------------------------------------------------------------- objects
def _link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def pivot(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    """An empty used as a joint. loc is relative to the parent pivot."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.05
    e.location = loc
    e.rotation_euler = rot
    return _link(e, parent)


def _finish(obj, m, parent, smooth=True, subsurf=0):
    if m is not None:
        obj.data.materials.append(m)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    if subsurf:
        mod = obj.modifiers.new('sub', 'SUBSURF')
        mod.levels = subsurf
        mod.render_levels = subsurf
    return _link(obj, parent)


def _bm_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return bpy.data.objects.new(name, me)


def sphere(name, loc, scale=(1, 1, 1), m=None, parent=None, rot=(0, 0, 0), seg=32, subsurf=0):
    """UV sphere of radius 1 scaled by `scale` (so scale = radii)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1)
    o = _bm_obj(name, bm)
    o.location, o.scale, o.rotation_euler = loc, _v3(scale), rot
    return _finish(o, m, parent, subsurf=subsurf)


def box(name, loc, size=(1, 1, 1), m=None, parent=None, rot=(0, 0, 0), bevel=0.0, subsurf=0):
    """Box with full edge lengths `size`. bevel rounds the edges (meters)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=3, profile=0.5, affect='EDGES')
    o = _bm_obj(name, bm)
    o.location, o.rotation_euler = loc, rot
    return _finish(o, m, parent, smooth=bool(bevel or subsurf), subsurf=subsurf)


def cone(name, loc, r1, r2, depth, m=None, parent=None, rot=(0, 0, 0), seg=24, subsurf=0):
    """Cone/cylinder along local Z, base radius r1 at -depth/2, tip radius r2 at +depth/2."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=depth)
    o = _bm_obj(name, bm)
    o.location, o.rotation_euler = loc, rot
    return _finish(o, m, parent, smooth=True, subsurf=subsurf)


def cylinder(name, loc, r, depth, m=None, parent=None, rot=(0, 0, 0), seg=24):
    return cone(name, loc, r, r, depth, m, parent, rot, seg)


def torus(name, loc, major, minor, m=None, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=16)
    o = bpy.context.active_object
    bpy.context.scene.collection.objects.unlink(o)
    o.name = name
    o.location, o.rotation_euler = loc, rot
    return _finish(o, m, parent)


def tube(name, points, radii, m=None, parent=None, seg=16, cap=True):
    """A smooth tube through `points` (list of xyz, relative to parent) with a radius per point.
    Good for tails, necks, arms, legs, horns, tentacles."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = max(2, seg // 4)
    cu.use_fill_caps = cap
    sp = cu.splines.new('NURBS')
    sp.points.add(len(points) - 1)
    for p, co, r in zip(sp.points, points, radii):
        p.co = (*co, 1)
        p.radius = r
    sp.order_u = min(4, len(points))
    sp.use_endpoint_u = True
    sp.resolution_u = 12
    o = bpy.data.objects.new(name, cu)
    if m is not None:
        o.data.materials.append(m)
    return _link(o, parent)


def from_verts(name, verts, faces, m=None, parent=None, loc=(0, 0, 0), subsurf=2, solidify=0.0):
    """Custom mesh from vertex/face lists (relative to `loc`). Use for flames, leaves, petals, wings,
    jaws: anything primitives can't do. subsurf smooths it; solidify gives a flat shape thickness."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    o = bpy.data.objects.new(name, me)
    o.location = loc
    if solidify:
        mod = o.modifiers.new('thick', 'SOLIDIFY')
        mod.thickness = solidify
        mod.offset = 0
    return _finish(o, m, parent, subsurf=subsurf)


def extrude_shape(name, outline, depth, m=None, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.01, subsurf=1):
    """Flat 2D outline (list of (x, z) in the XZ plane) extruded `depth` along Y, edges rounded.
    Great for flames, leaves, feathers, crests, spikes, scarves."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in outline]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += depth
    for v in bm.verts:
        v.co.y -= depth / 2
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    o = _bm_obj(name, bm)
    o.location, o.rotation_euler = loc, rot
    return _finish(o, m, parent, subsurf=subsurf)


def mirror_x(obj):
    """Mirror an object across the creature's center plane (X = 0 of its parent)."""
    obj.modifiers.new('mirror', 'MIRROR')
    obj.modifiers.move(len(obj.modifiers) - 1, 0)
    return obj


def eye(name, loc, radius, parent, iris='#3a2a1a', pupil='#0a0a0a', sclera='#ffffff', look=(0, -1, 0), iris_frac=0.62, flat=0.55):
    """Cartoon eye: white sclera, colored iris, pupil and a catch-light, facing `look`."""
    look = Vector(look).normalized()
    p = pivot(name, loc, parent)
    p.rotation_euler = Vector((0, -1, 0)).rotation_difference(look).to_euler()
    sphere(name + '_white', (0, 0, 0), (radius, radius * flat, radius), mat('eye_white_' + sclera, sclera, 0.15, coat=1), p)
    ir = radius * iris_frac
    sphere(name + '_iris', (0, -radius * flat * 0.86, 0), (ir, ir * 0.35, ir), mat('iris_' + iris, iris, 0.2, coat=1), p)
    sphere(name + '_pupil', (0, -radius * flat * 0.98, 0), (ir * .5, ir * .2, ir * .5), mat('pupil_' + pupil, pupil, 0.1, coat=1), p)
    sphere(name + '_shine', (-ir * .35, -radius * flat * 1.08, ir * .35), (ir * .22, ir * .1, ir * .22), mat('shine', '#ffffff', 0.1, emit=2), p)
    return p


def _v3(s):
    return (s, s, s) if isinstance(s, (int, float)) else s


# ---------------------------------------------------------------- rig
class Rig:
    """What a model hands to the animation system.

    gait:   'walk'   legs swing (4+ legs or 2 legs), body bobs
            'hop'    no real legs; whole body squashes and hops (slimes, blobs)
            'float'  hovers and drifts, no ground contact (flame spirits)
            'fly'    wings flap, body hovers; legs tuck
    attack: 'bite' | 'slam' | 'peck' | 'cast' (projectile from attack_origin)
    type:   main type, picks the attack effect: Grass Fire Water Ice Flying Normal
    """

    def __init__(self, name, key, type_, height_cm=None, gait='walk', attack='cast'):
        self.name, self.key, self.type, self.height_cm = name, key, type_, height_cm
        self.gait, self.attack = gait, attack
        self.root = pivot(key + '_root')
        self.body = None           # main torso pivot (bob, squash, lean)
        self.head = None           # head pivot (look, cry, bite)
        self.jaw = None            # optional: lower jaw pivot, rotates +X to open
        self.legs = []             # [(pivot, phase 0..1)] swing around local X
        self.arms = []             # [(pivot, phase)] swing around local X
        self.wings = []            # [(pivot, side -1 left / +1 right)] flap around local Y
        self.tail = []             # chain of pivots, base first; sway around local Z
        self.extras = []           # [(pivot, 'flicker'|'spin'|'sway'|'pulse')] ambient motion
        self.attack_origin = (0, -0.5, 0.8)   # where projectiles start, in root space
        self.t_pose = {}           # optional {pivot_name: (rx, ry, rz) radians} to spread limbs for the T-pose shot
