"""Build one of the star fox models step by step inside the Blender UI, so the build can be screen-recorded.

Run with a display (not -b):  blender --factory-startup -P gui_build_sv.py -- <module>
Each stage runs on a timer, so the viewport redraws in between: the skeleton appears, the sculpt
shapes go in group by group as a live metaball preview, then the real build runs (fused, painted and
skinned body, eyes, stars), then the pose, the materials and a rendered viewport.
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import quad  # noqa: E402
import sv  # noqa: E402

MOD = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'glimmvix'
m = importlib.import_module(MOD)
H = {'twinkit': 1.75, 'glimmvix': 2.2, 'novalynx': 2.6}[MOD]
state = {}


def view3d():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                return win, area, area.spaces.active
    return None


def look(yaw_deg, pitch_deg, dist, cz=None, shading=None):
    win, area, space = view3d()
    r3 = space.region_3d
    r3.view_location = (0, 0.1 * H, cz if cz is not None else 0.5 * H)
    r3.view_distance = dist * H
    r3.view_rotation = Euler((math.radians(90 - pitch_deg), 0, math.radians(yaw_deg))).to_quaternion()
    r3.view_perspective = 'PERSP'
    if shading:
        space.shading.type = shading
    area.tag_redraw()


def select_only(objs):
    for o in bpy.context.scene.objects:
        o.select_set(o in objs)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def s_skeleton():
    state['root0'] = kit.empty(MOD + ' (sketch)')
    state['arm0'] = kit.make_armature(m.P_ + 'sketch_rig', quad.bones(m.SPEC, m.extra_bones()), parent=state['root0'])
    state['arm0'].show_in_front = True
    select_only([state['arm0']])


def preview_group(chunk):
    """Add one group of the model's sculpt shapes to a live metaball preview (coarser resolution)."""
    def run():
        if 'mb' not in state:
            mb = bpy.data.metaballs.new(m.P_ + 'sculpt_mb')
            mb.resolution = 0.06 * H / 2
            mb.threshold = 0.6
            o = bpy.data.objects.new(m.P_ + 'sculpt', mb)
            kit.link(o)
            state['mb'], state['mbo'] = mb, o
        for e in chunk:
            el = state['mb'].elements.new(type='ELLIPSOID')
            el.co = e.co
            el.radius = 1.0
            el.stiffness = e.stiff
            el.size_x, el.size_y, el.size_z = e.size / sv.iso(e.stiff)
            el.rotation = e.R.to_quaternion()
        select_only([state['mbo']])
    return run


def s_build():
    """The real build: the same code the renders use."""
    for k in ('mbo', 'arm0', 'root0'):
        o = state.pop(k, None)
        if o:
            bpy.data.objects.remove(o)
    kit._M.clear()
    rig = m.build()
    rig['arm'].scale = (1, 1, 1)
    state['rig'] = rig
    select_only([rig['body']])


def s_colors():
    win, area, space = view3d()
    space.shading.type = 'SOLID'
    space.shading.color_type = 'VERTEX'
    space.shading.light = 'STUDIO'


def s_pose():
    m.display_pose(state['rig']['arm'])
    select_only([state['rig']['arm']])


def s_material():
    look(-35, 10, 3.2, None, 'MATERIAL')


def s_render_view():
    import render_line
    render_line.dusk_sky()
    render_line.meadow()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.preview_samples = 6
    sc.cycles.use_preview_denoising = True
    look(-30, 8, 3.0, None, 'RENDERED')


def spin(start, end, steps, pitch, dist):
    out = []
    for i in range(steps):
        t = i / max(1, steps - 1)
        out.append((lambda y=start + (end - start) * t: look(y, pitch, dist), 0.25))
    return out


PLAN = []


def add(fn, wait, cam=None):
    def run():
        fn()
        if cam:
            look(*cam)
        return None
    PLAN.append((run, wait))


def build_plan():
    PLAN.append((lambda: look(-30, 12, 3.4, None, 'SOLID'), 1.5))
    add(s_skeleton, 2.0, (-30, 12, 3.0))
    PLAN.extend(spin(-30, 15, 6, 12, 3.0))
    E = m.elements()
    n = len(E)
    groups = 7
    for g in range(groups):
        chunk = E[g * n // groups:(g + 1) * n // groups]
        add(preview_group(chunk), 1.2, (15 - g * 8, 10, 2.9))
    PLAN.extend(spin(-41, 20, 8, 10, 2.9))
    add(s_build, 2.5, (-25, 10, 2.9))
    PLAN.append((s_colors, 2.0))
    PLAN.extend(spin(-25, 30, 10, 10, 2.8))
    add(s_pose, 2.0, (-30, 8, 2.8))
    PLAN.append((s_material, 4.0))
    PLAN.extend(spin(-35, 25, 10, 8, 3.0))
    PLAN.append((s_render_view, 25.0))
    PLAN.append((lambda: bpy.ops.wm.quit_blender(), 1.0))


def tick():
    if not PLAN:
        return None
    fn, wait = PLAN.pop(0)
    fn()
    return wait


def start():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    kit._M.clear()
    build_plan()
    bpy.app.timers.register(tick, first_interval=3.0)


bpy.app.timers.register(lambda: (start(), None)[1], first_interval=2.0)
