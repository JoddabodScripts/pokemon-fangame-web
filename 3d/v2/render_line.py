"""Stills of the star fox line (Twinkit, Glimmvix, Novalynx) in the Star Fields at dusk.

  blender -b --factory-startup -P v2/render_line.py -- lineup|hero [samples] [w] [h]

lineup: all three side by side at their real heights (30, 90 and 160 cm).
hero:   one close three-quarter shot of each.
"""
import importlib
import math
import os
import sys
import time

import bpy
from mathutils import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import render2  # noqa: E402

OUT = os.path.join(HERE, '..', 'renders')
LINE = ['twinkit', 'glimmvix', 'novalynx']


def dusk_sky():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('dusk')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    s = nt.nodes.new('ShaderNodeTexSky')
    s.sky_type = 'NISHITA'
    s.sun_elevation = math.radians(6)
    s.sun_rotation = math.radians(-140)
    s.altitude = 300
    s.air_density = 1.4
    s.dust_density = 2.2
    s.ozone_density = 2.0
    s.sun_intensity = 0.25
    s.sun_disc = False
    nt.links.new(s.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.3
    sun = bpy.data.lights.new('sun', 'SUN')
    sun.energy = 3.6
    sun.angle = math.radians(2)
    sun.color = kit.srgb('#ffc68a')
    o = bpy.data.objects.new('sun', sun)
    o.rotation_euler = (math.radians(66), 0, math.radians(-38))
    kit.link(o)
    for name, loc, e, col, size in (('fill', (-6, -8, 4), 420, '#a9b8ff', 8), ('rim', (4, 7, 4), 900, '#ffd9b0', 5)):
        d = bpy.data.lights.new(name, 'AREA')
        d.energy = e
        d.size = size
        d.color = kit.srgb(col)
        ob = bpy.data.objects.new(name, d)
        ob.location = loc
        ob.rotation_euler = (V((0, 0, 0.8)) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
        kit.link(ob)


def meadow():
    """Rolling grass with soft color patches, a few flower specks and low hills behind."""
    bpy.ops.mesh.primitive_plane_add(size=80)
    g = bpy.context.active_object
    g.name = 'meadow'
    m, _ = kit.new_mat('grass')
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.35
    nz.inputs['Detail'].default_value = 4
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*kit.srgb('#4f7f3a'), 1)
    ramp.color_ramp.elements[1].color = (*kit.srgb('#8fb554'), 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    # tiny flower specks
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 7.0
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    lt = nt.nodes.new('ShaderNodeMath')
    lt.operation = 'LESS_THAN'
    lt.inputs[1].default_value = 0.06
    nt.links.new(vor.outputs['Distance'], lt.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['B'].default_value = (*kit.srgb('#fff2c4'), 1)
    nt.links.new(lt.outputs[0], mix.inputs['Factor'])
    nt.links.new(ramp.outputs['Color'], mix.inputs['A'])
    nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.95
    bump = nt.nodes.new('ShaderNodeBump')
    nz2 = nt.nodes.new('ShaderNodeTexNoise')
    nz2.inputs['Scale'].default_value = 40
    nt.links.new(nz2.outputs['Fac'], bump.inputs['Height'])
    bump.inputs['Strength'].default_value = 0.25
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    g.data.materials.append(m)
    # low hills
    for i, (x, y, sx_, sz) in enumerate(((-14, 30, 18, 3.5), (10, 34, 22, 4.5), (30, 26, 14, 3.0), (-34, 24, 16, 2.6))):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=(x, y, 0))
        h = bpy.context.active_object
        h.scale = (sx_, 6, sz)
        for p in h.data.polygons:
            p.use_smooth = True
        h.data.materials.append(kit.mat_basic(f'hill{i}', '#5f7f52' if i % 2 else '#6b8a58', rough=1.0))


def place(mod, x, yaw=0.0):
    m = importlib.import_module(mod)
    rig = m.build()
    if hasattr(m, 'display_pose'):
        m.display_pose(rig['arm'])
    rig['root'].location = (x, 0, 0)
    rig['root'].rotation_euler = (0, 0, yaw)
    return m, rig


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    mode = args[0]
    samples = int(args[1]) if len(args) > 1 else 32
    w = int(args[2]) if len(args) > 2 else 1280
    h = int(args[3]) if len(args) > 3 else 720
    t0 = time.time()
    if mode == 'lineup':
        bpy.ops.wm.read_factory_settings(use_empty=True)
        kit._M.clear()
        for mod, x, yaw in (('twinkit', -1.3, 0.45), ('glimmvix', -0.45, 0.35), ('novalynx', 0.85, 0.2)):
            place(mod, x, yaw)
        dusk_sky()
        meadow()
        render2.settings(samples, w, h)
        render2.camera((-1.5, -6.6, 1.0), (-0.1, 0, 0.78), 40, dof=5.6)
        bpy.context.scene.render.filepath = os.path.join(OUT, 'starfox_lineup.png')
        bpy.ops.render.render(write_still=True)
        print('WROTE', bpy.context.scene.render.filepath, round(time.time() - t0))
    else:
        for mod in LINE:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            kit._M.clear()
            m, rig = place(mod, 0, 0.0)
            dusk_sky()
            meadow()
            render2.settings(samples, w, h)
            hgt = {'twinkit': 0.3, 'glimmvix': 0.9, 'novalynx': 1.6}[mod]
            c = V((0, -0.1 * hgt, hgt * 0.55))
            a = math.radians(-32)
            loc = c + V((math.sin(a), -math.cos(a), 0.12)) * hgt * 3.1
            render2.camera(loc, c, 50, dof=4.0)
            bpy.context.scene.render.filepath = os.path.join(OUT, f'{mod}_hero.png')
            bpy.ops.render.render(write_still=True)
            print('WROTE', bpy.context.scene.render.filepath, round(time.time() - t0))


if __name__ == '__main__':
    main()
