"""v2 renderer: snowy mountain battle arena, physical sky, hero stills and the battle video.

  blender -b --factory-startup -P render2.py -- still [w h samples]
  blender -b --factory-startup -P render2.py -- tpose
  blender -b --factory-startup -P render2.py -- video [w h samples]
"""
import math
import os
import random
import sys
import time

import bpy
from mathutils import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import freezer_flock as ff  # noqa: E402

OUT = os.path.join(HERE, '..', 'renders')


def settings(samples, w, h):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 6
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = -0.35


def sky():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('sky')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    s = nt.nodes.new('ShaderNodeTexSky')
    s.sky_type = 'NISHITA'
    s.sun_elevation = math.radians(17)
    s.sun_rotation = math.radians(-125)
    s.altitude = 1500
    s.air_density = 1.2
    s.dust_density = 1.4
    s.ozone_density = 1.5
    s.sun_intensity = 0.3
    s.sun_disc = False
    nt.links.new(s.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.22


def sun():
    d = bpy.data.lights.new('sun', 'SUN')
    d.energy = 5.0
    d.angle = math.radians(1.5)
    d.color = kit.srgb('#ffd7a6')
    o = bpy.data.objects.new('sun', d)
    o.rotation_euler = (math.radians(68), 0, math.radians(-38))
    kit.link(o)
    # cool bounce from the camera side, warm-white rim from behind to split the white bird from the snow
    for name, loc, e, col, size in (('fill', (-10, -14, 5), 900, '#bcd6ff', 10), ('rim', (6, 10, 8), 6000, '#fff0dc', 5),
                                    ('rim2', (-7, 8, 6), 3000, '#d8e8ff', 5)):
        d = bpy.data.lights.new(name, 'AREA')
        d.energy = e
        d.size = size
        d.color = kit.srgb(col)
        o = bpy.data.objects.new(name, d)
        o.location = loc
        o.rotation_euler = (V((0, 0, 3)) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
        kit.link(o)


def mist():
    """Aerial perspective: blend distant things toward the horizon color with the mist pass."""
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    vl.use_pass_mist = True
    sc.world.mist_settings.start = 14
    sc.world.mist_settings.depth = 260
    sc.world.mist_settings.falloff = 'QUADRATIC'
    sc.use_nodes = True
    nt = sc.node_tree
    rl = nt.nodes['Render Layers']
    comp = nt.nodes['Composite']
    mix = nt.nodes.new('CompositorNodeMixRGB')
    mix.inputs[2].default_value = (*kit.srgb('#cbd9ea'), 1)
    mul = nt.nodes.new('CompositorNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 0.6
    nt.links.new(rl.outputs['Mist'], mul.inputs[0])
    vl.use_pass_z = True
    lt = nt.nodes.new('CompositorNodeMath')
    lt.operation = 'LESS_THAN'
    lt.inputs[1].default_value = 5000
    nt.links.new(rl.outputs['Depth'], lt.inputs[0])
    m2 = nt.nodes.new('CompositorNodeMath')
    m2.operation = 'MULTIPLY'
    nt.links.new(mul.outputs[0], m2.inputs[0])
    nt.links.new(lt.outputs[0], m2.inputs[1])
    nt.links.new(m2.outputs[0], mix.inputs[0])
    nt.links.new(rl.outputs['Image'], mix.inputs[1])
    glare = nt.nodes.new('CompositorNodeGlare')
    glare.glare_type = 'FOG_GLOW'
    glare.quality = 'MEDIUM'
    glare.threshold = 1.2
    glare.size = 7
    glare.mix = -0.8
    nt.links.new(mix.outputs[0], glare.inputs[0])
    nt.links.new(glare.outputs[0], comp.inputs[0])


def slope_mat(name, low, high, rock):
    """Snow on flat ground, rock on steep faces (by the surface normal)."""
    m = kit.mat_basic(name, low, rough=0.6, sss=0.3, sss_radius=(0.8, 0.9, 1.0))
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.08
    nz.inputs['Detail'].default_value = 10
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.95
    ramp.color_ramp.elements[0].color = (*kit.srgb(rock), 1)
    ramp.color_ramp.elements[1].position = 1.05
    ramp.color_ramp.elements[1].color = (*kit.srgb(high), 1)
    nt.links.new(geo.outputs['Normal'], sep.inputs[0])
    nt.links.new(sep.outputs['Z'], add.inputs[0])
    nt.links.new(nz.outputs['Fac'], add.inputs[1])
    nt.links.new(add.outputs[0], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    return m


def pine_variants():
    """Three reusable pine meshes: drooping tiers, snow loading the tops."""
    from mathutils import noise
    out = []
    pine = kit.mat_basic('pinem', '#1f3b33', rough=0.85, sheen=0.3)
    snowc = kit.mat_basic('pinesnow', '#f1f6fb', rough=0.6, sss=0.3)
    for vi in range(3):
        rnd = random.Random(vi)
        mb_v, mb_f, mats = [], [], []
        tiers = 9 + vi
        for t in range(tiers):
            f = t / tiers
            z0 = 0.6 + f * 5.2
            rad = 1.7 * (1 - f) ** 1.1 + 0.15
            seg = 14
            base = len(mb_v)
            tip = (0, 0, z0 + 0.9)
            mb_v.append(tip)
            for k in range(seg):
                a = 2 * math.pi * k / seg + rnd.uniform(-0.1, 0.1)
                rr = rad * rnd.uniform(0.8, 1.1)
                droop = -0.35 * rr
                mb_v.append((math.cos(a) * rr, math.sin(a) * rr, z0 + droop + rnd.uniform(-0.08, 0.08)))
            for k in range(seg):
                mb_f.append((base, base + 1 + k, base + 1 + (k + 1) % seg))
        me = bpy.data.meshes.new(f'pine{vi}')
        me.from_pydata(mb_v, [], mb_f)
        me.update()
        # trunk
        me.materials.append(pine)
        me.materials.append(snowc)
        for p in me.polygons:
            c = p.center
            p.material_index = 1 if (p.normal.z > 0.62 and noise.noise(c * 2.3) > -0.25) else 0
            p.use_smooth = False
        out.append(me)
    return out


def arena():
    """Snowfield with a stone battle ring dusted in snow, pines and mountains behind."""
    from mathutils import noise
    # snow ground with soft drifts
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=260, y_subdivisions=260, size=160, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = 'snow'
    for v in g.data.vertices:
        x, y = v.co.x, v.co.y
        r = math.hypot(x, y)
        k = min(1.0, max(0.0, (r - 9.5) / 12))
        h = noise.fractal(V((x * 0.05, y * 0.05, 0)), 0.6, 2.0, 4) * 1.2 * k
        h += max(0.0, y - 40) * 0.12 * k
        v.co.z = h - 0.01
    kit.smooth_obj(g)
    m = kit.mat_basic('snowm', '#eef4fa', rough=0.5, sss=0.6, sss_radius=(0.8, 0.9, 1.0), sheen=0.2)
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.8
    nz.inputs['Detail'].default_value = 10
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.3
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    nt.links.new(nz.outputs['Fac'], bump.inputs['Height'])
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 260
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (4, 4, 4.4, 1)
    ramp.color_ramp.elements[1].position = 0.03
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 0.12
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    g.data.materials.append(m)

    # battle ring: flagstones with a snow dusting and painted lines
    stone = kit.mat_basic('stonem', '#8a96a6', rough=0.75)
    nt = stone.node_tree
    b = nt.nodes['Principled BSDF']
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 0.9
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*kit.srgb('#3a4250'), 1)
    ramp.color_ramp.elements[1].position = 0.04
    ramp.color_ramp.elements[1].color = (*kit.srgb('#8f9bab'), 1)
    nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.6
    nz.inputs['Detail'].default_value = 8
    r2 = nt.nodes.new('ShaderNodeValToRGB')
    r2.color_ramp.elements[0].position = 0.5
    r2.color_ramp.elements[1].position = 0.62
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    nt.links.new(nz.outputs['Fac'], r2.inputs['Fac'])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    nt.links.new(r2.outputs['Color'], mix.inputs[0])
    nt.links.new(ramp.outputs['Color'], mix.inputs[6])
    mix.inputs[7].default_value = (*kit.srgb('#eef4fa'), 1)
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.6
    nt.links.new(vor.outputs['Distance'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])

    paint = kit.mat_basic('paintm', '#2b78c8', rough=0.6)
    bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=8.5, depth=0.12, location=(0, 0, 0.0))
    ring = bpy.context.active_object
    ring.name = 'ring'
    ring.data.materials.append(stone)
    bev = ring.modifiers.new('bev', 'BEVEL')
    bev.width = 0.04
    bev.segments = 3
    kit.smooth_obj(ring)
    for rad in (7.9, 1.8):
        bpy.ops.mesh.primitive_torus_add(major_radius=rad, minor_radius=0.07, major_segments=160, location=(0, 0, 0.065))
        t = bpy.context.active_object
        t.scale.z = 0.08
        t.data.materials.append(paint)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.065))
    t = bpy.context.active_object
    t.scale = (15.8, 0.14, 0.01)
    t.data.materials.append(paint)

    # pine forest behind the arena, kept clear of the camera's side
    rnd = random.Random(4)
    pines = pine_variants()
    for i in range(120):
        a = rnd.uniform(-0.35, math.pi + 0.35)
        rr = rnd.uniform(18, 60)
        x, y = math.cos(a) * rr * 1.25, math.sin(a) * rr + 4
        if y < 8:
            continue
        o = bpy.data.objects.new('pine', pines[i % 3])
        s = rnd.uniform(0.8, 1.5)
        o.scale = (s, s, s * rnd.uniform(0.9, 1.2))
        o.rotation_euler.z = rnd.uniform(0, 6.3)
        zz = 0.0
        o.location = (x, y, zz)
        kit.link(o)
        # sit on the snow
        d = math.hypot(x, y)
        k = min(1.0, max(0.0, (d - 9.5) / 12))
        o.location.z = noise.fractal(V((x * 0.05, y * 0.05, 0)), 0.6, 2.0, 4) * 1.2 * k + max(0.0, y - 40) * 0.12 * k - 0.2

    # mountain range: fractal terrain with snow on the flats and rock on cliffs
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=300, y_subdivisions=90, size=1, location=(0, 0, 0))
    mt = bpy.context.active_object
    mt.name = 'mountains'
    for v in mt.data.vertices:
        x = v.co.x * 900
        y = 190 + (v.co.y + 0.5) * 200
        ridge = math.exp(-((y - 280) / 55) ** 2)
        h = noise.ridged_multi_fractal(V((x * 0.012, y * 0.012, 3.1)), 1.0, 2.1, 6, 1.0, 2.0) * 34 * (0.3 + ridge)
        h += 40 * ridge + noise.fractal(V((x * 0.004, 7.0, 0)), 0.5, 2.0, 3) * 30 * ridge
        v.co = (x, y, h - 6)
    kit.smooth_obj(mt)
    mt.data.materials.append(slope_mat('mtnm', '#eef3f9', '#f4f8fc', '#5e6b7e'))


def snowfall(n=900, seed=5, frames=None):
    """Little drifting flakes in front of and around the arena."""
    rnd = random.Random(seed)
    mb = kit.MeshBuilder()
    for i in range(n):
        p = V((rnd.uniform(-16, 16), rnd.uniform(-14, 14), rnd.uniform(0, 12)))
        s = rnd.uniform(0.012, 0.03)
        vs = [(p.x - s, p.y, p.z), (p.x, p.y, p.z + s), (p.x + s, p.y, p.z), (p.x, p.y, p.z - s)]
        mb.add(vs, [(0, 1, 2, 3)], [(1, 1, 1)] * 4)
    o = mb.build('snowfall', kit.mat_basic('flakem', '#ffffff', rough=0.5, emit=0.6), smooth=False)
    return o


def camera(loc, target, lens=40, dof=None):
    cd = bpy.data.cameras.new('cam')
    cd.lens = lens
    cd.sensor_width = 36
    cam = bpy.data.objects.new('cam', cd)
    kit.link(cam)
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance = (V(target) - V(loc)).length
        cd.dof.aperture_fstop = dof
    bpy.context.scene.camera = cam
    return cam


def setup(pose=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kit._M.clear()
    rig = ff.build()
    if pose:
        ff.pose_bones(rig['arm'], ff.display_pose())
    rig['arm'].location = (0, 0, 0.7) if pose else (0, 0, 0)
    sky()
    sun()
    arena()
    mist()
    return rig


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    mode = args[0]
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    if mode in ('still', 'tpose', 'head'):
        w, h, s = (int(a) for a in (args[1:4] if len(args) >= 4 else (1280, 720, 48)))
        rig = setup(pose=(mode != 'tpose'))
        print('BUILD seconds', round(time.time() - t0))
        settings(s, w, h)
        shots = [((-3.9, -9.4, 1.4), (0, 0, 3.6), 30, 'a'), ((-1.5, -5.2, 3.7), (0, -0.7, 4.05), 60, 'b')]
        if mode == 'head':
            shots = [((0, -3.4, 4.0), (0, -0.6, 4.0), 50, 'h1'), ((-2.4, -2.6, 4.1), (0, -0.6, 4.0), 50, 'h2'),
                     ((-3.4, -0.6, 4.0), (0, -0.6, 4.0), 50, 'h3')]
        if mode == 'tpose':
            shots = [((0, -16, 3.0), (0, 0, 2.6), 32, 'a'), ((-9, -11, 4.5), (0, 0, 2.6), 32, 'b')]
        for loc, tgt, lens, tag in shots:
            camera(loc, tgt, lens, dof=4.0 if tag == 'b' else None)
            bpy.context.scene.render.filepath = os.path.join(OUT, f'_v2_{mode}_{tag}.png')
            bpy.ops.render.render(write_still=True)
            print('WROTE', bpy.context.scene.render.filepath, round(time.time() - t0))
    elif mode in ('frames', 'video'):
        import ffk_anim
        rig = setup(pose=False)
        ffk_anim.animate(rig)
        sc = bpy.context.scene
        print('BUILD seconds', round(time.time() - t0))
        if mode == 'frames':
            w, h, s = 480, 270, 10
            settings(s, w, h)
            fr = [int(a) for a in args[1:]]
            paths = []
            for f in fr:
                sc.frame_set(f)
                sc.render.filepath = os.path.join(OUT, f'_v2f_{f:03d}.png')
                bpy.ops.render.render(write_still=True)
                paths.append(sc.render.filepath)
            cols = 4
            rows = (len(paths) + cols - 1) // cols
            while len(paths) < rows * cols:
                paths.append(paths[-1])
            os.system('ffmpeg -loglevel error -y ' + ' '.join(f'-i {p}' for p in paths) +
                      f' -filter_complex "xstack=inputs={len(paths)}:grid={cols}x{rows}" {OUT}/_v2_frames.png')
        else:
            w, h, s = (int(a) for a in args[1:4]) if len(args) >= 4 else (1280, 720, 14)
            settings(s, w, h)
            sc.render.use_motion_blur = os.environ.get('MBLUR') == '1'
            sc.render.motion_blur_shutter = 0.4
            d = os.path.join(OUT, 'v2frames')
            os.makedirs(d, exist_ok=True)
            first = int(args[4]) if len(args) > 4 else 0
            sc.frame_start = first
            sc.render.filepath = os.path.join(d, 'f_')
            sc.render.image_settings.file_format = 'PNG'
            sc.render.use_overwrite = False
            bpy.ops.render.render(animation=True)
            print('VIDEO DONE', round(time.time() - t0))
