"""Quick look at one of the new SV-style models: a 4-view sheet (front 3/4, front, side, back).

  blender -b --factory-startup -P v2/preview_sv.py -- <module> [samples] [stage]

Writes renders/_sv_<module>.png. stage=meadow uses the Star Fields dusk set instead of the plain studio.
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import render2  # noqa: E402

OUT = os.path.join(HERE, '..', 'renders')


def bbox(objs):
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        pts += [o.matrix_world @ v.co for v in me.vertices]
        oe.to_mesh_clear()
    lo = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def studio():
    render2.sky()
    d = bpy.data.lights.new('key', 'SUN')
    d.energy = 4.0
    d.angle = math.radians(3)
    d.color = kit.srgb('#fff1dc')
    o = bpy.data.objects.new('key', d)
    o.rotation_euler = (math.radians(55), 0, math.radians(-35))
    kit.link(o)
    bpy.ops.mesh.primitive_plane_add(size=60)
    g = bpy.context.active_object
    g.data.materials.append(kit.mat_basic('ground', '#8fb37a', rough=0.9))


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    mod = args[0]
    samples = int(args[1]) if len(args) > 1 else 16
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kit._M.clear()
    m = importlib.import_module(mod)
    rig = m.build()
    if hasattr(m, 'display_pose'):
        m.display_pose(rig['arm'])
    bpy.context.view_layer.update()
    studio()
    render2.settings(samples, 640, 640)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(m.P_)]
    lo, hi = bbox(meshes)
    c = (lo + hi) / 2
    h = max(hi.z - lo.z, (hi.y - lo.y) * 0.8, hi.x - lo.x)
    dist = h * 2.6
    views = [(-35, 12), (0, 6), (-90, 6), (150, 15)]
    paths = []
    for i, (yaw, pitch) in enumerate(views):
        a, p = math.radians(yaw), math.radians(pitch)
        loc = c + V((math.sin(a) * math.cos(p), -math.cos(a) * math.cos(p), math.sin(p))) * dist
        for ob in [o for o in bpy.data.objects if o.type == 'CAMERA']:
            bpy.data.objects.remove(ob)
        render2.camera(loc, c + V((0, 0, -h * 0.02)), 50)
        path = os.path.join(OUT, f'_svv_{mod}_{i}.png')
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
    # 2x2 sheet
    imgs = [bpy.data.images.load(p) for p in paths]
    W, H = imgs[0].size
    sheet = bpy.data.images.new('sheet', W * 2, H * 2)
    import numpy as np
    buf = np.zeros((H * 2, W * 2, 4), dtype=np.float32)
    for k, im in enumerate(imgs):
        px = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)
        r, cc = 1 - k // 2, k % 2
        buf[r * H:(r + 1) * H, cc * W:(cc + 1) * W] = px
    sheet.pixels = buf.ravel()
    sheet.filepath_raw = os.path.join(OUT, f'_sv_{mod}.png')
    sheet.file_format = 'PNG'
    sheet.save()
    print('SHEET', sheet.filepath_raw)


main()
