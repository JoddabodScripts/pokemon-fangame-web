"""Build Freezer Flock step by step inside the Blender UI, so the build can be screen-recorded.

Run with a display (not -b):  blender --factory-startup -P gui_build.py
Each stage runs on a timer, so the viewport redraws in between: you see the skeleton appear,
the sculpt shapes added group by group, the fused and painted body, the eyes, beak, talons and scarf,
then the pose, materials and a rendered viewport.
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import freezer_flock as ff  # noqa: E402

state = {}


def view3d():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                return win, area, area.spaces.active, [r for r in area.regions if r.type == 'WINDOW'][0]
    return None


def look(yaw_deg, pitch_deg, dist, center=(0, 0, 2.8), shading=None):
    win, area, space, region = view3d()
    r3 = space.region_3d
    r3.view_location = center
    r3.view_distance = dist
    r3.view_rotation = (Euler((math.radians(90 - pitch_deg), 0, math.radians(yaw_deg)))).to_quaternion()
    r3.view_perspective = 'PERSP'
    if shading:
        space.shading.type = shading
    space.overlay.show_floor = True
    area.tag_redraw()


def select_only(names):
    for o in bpy.context.scene.objects:
        o.select_set(o.name in names)
    if names and names[0] in bpy.context.scene.objects:
        bpy.context.view_layer.objects.active = bpy.context.scene.objects[names[0]]


def new_objects(before):
    return [o.name for o in bpy.context.scene.objects if o.name not in before]


def stage(fn, cam=None):
    def run():
        before = {o.name for o in bpy.context.scene.objects}
        fn()
        select_only(new_objects(before))
        if cam:
            look(*cam)
        return None
    return run


# ---- the build, one stage per step
def s_skeleton():
    state['root'] = kit.empty('Freezer Flock')
    state['arm'] = kit.make_armature('ffk_rig', ff.BONES, parent=state['root'])
    state['arm'].show_in_front = True


def preview_group(label, make):
    """Add one group of sculpt shapes to a live metaball preview, so the body grows part by part.
    These are the same shapes build_body() fuses; the preview only uses a coarser resolution."""
    def run():
        if 'mb' not in state:
            ff.place_eyes()
            mb = bpy.data.metaballs.new('ffk_sculpt_mb')
            mb.resolution = 0.07
            mb.threshold = 0.6
            o = bpy.data.objects.new('ffk_sculpt', mb)
            kit.link(o)
            state['mb'] = mb
            state['mbo'] = o
        for e in make():
            el = state['mb'].elements.new(type='ELLIPSOID')
            el.co = e.co
            el.radius = 1.0
            el.stiffness = ff.STIFF
            el.size_x, el.size_y, el.size_z = e.size / ff.ISO
            el.rotation = e.R.to_quaternion()
    run.__name__ = 's_' + label
    return run


def torso():
    B = ff.body_elements()
    for e in B:
        e.size = e.size * e.k
    return B


def s_body():
    bpy.data.objects.remove(state.pop('mbo'))
    state['body'] = ff.build_body(state['arm'])


def s_eyes():
    ff.eyes(state['arm'])


def s_beak():
    ff.D.beak(state['arm'])


def s_talons():
    ff.talons(state['arm'])


def s_scarf():
    ff.D.scarf(state['arm'])
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers):
            o.parent = state['arm']
        elif o.type == 'MESH' and o.parent is None:
            o.parent = state['root']


def s_pose():
    ff.pose_bones(state['arm'], ff.display_pose())
    select_only([state['arm'].name])


def s_colors():
    win, area, space, region = view3d()
    space.shading.color_type = 'VERTEX'
    space.shading.light = 'STUDIO'


def s_material():
    look(-35, 10, 13, (0, 0, 3.2), 'MATERIAL')


def s_render_view():
    # light + world so the rendered viewport shows the real look
    import render2
    render2.sky()
    render2.sun()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.preview_samples = 6
    sc.cycles.use_preview_denoising = True
    look(-30, 8, 12.5, (0, 0, 3.3), 'RENDERED')


def spin(start, end, steps, pitch, dist, center=(0, 0, 3.0)):
    """Orbit the viewport a little between stages."""
    out = []
    for i in range(steps):
        t = i / max(1, steps - 1)
        out.append((lambda y=start + (end - start) * t: look(y, pitch, dist, center), 0.25))
    return out


PLAN = []


def add(fn, wait, cam=None):
    PLAN.append((stage(fn, cam), wait))


def build_plan():
    PLAN.append((lambda: look(-30, 12, 14, (0, 0, 2.6), 'SOLID'), 1.5))
    add(s_skeleton, 2.0, (-30, 12, 12, (0, 0, 2.6)))
    PLAN.extend(spin(-30, 10, 6, 12, 12, (0, 0, 2.6)))
    add(preview_group('torso', torso), 2.0, (-25, 10, 10, (0, 0, 2.8)))
    add(preview_group('crest', ff.crest_elements), 1.5, (-40, 10, 7, (0, 0, 3.8)))
    add(preview_group('tail', ff.tail_elements), 1.5, (140, 15, 10, (0, 0.6, 2.2)))
    add(preview_group('legs', ff.leg_elements), 1.5, (-40, 5, 7, (0, 0, 1.2)))
    add(preview_group('wing_L', lambda: ff.wing_elements('L')), 1.5, (20, 30, 13, (1.2, 0, 3.0)))
    add(preview_group('wing_R', lambda: ff.wing_elements('R')), 1.5, (-20, 30, 14, (0, 0, 3.0)))
    PLAN.extend(spin(-20, 20, 6, 20, 14, (0, 0, 3.0)))
    add(s_body, 2.5, (-25, 10, 13, (0, 0, 3.0)))
    PLAN.append((s_colors, 2.0))
    PLAN.extend(spin(-25, 25, 8, 10, 13, (0, 0, 3.0)))
    add(s_eyes, 1.5, (-25, 8, 4.5, (0, -0.5, 3.95)))
    add(s_beak, 1.5, (-35, 8, 4.5, (0, -0.6, 3.9)))
    PLAN.extend(spin(-35, 20, 6, 8, 4.5, (0, -0.6, 3.9)))
    add(s_talons, 1.5, (-40, 5, 6, (0, 0, 1.1)))
    add(s_scarf, 2.0, (-25, 8, 6, (0, -0.2, 3.1)))
    add(s_pose, 2.0, (-30, 8, 14, (0, 0, 3.4)))
    PLAN.append((s_material, 4.0))
    PLAN.extend(spin(-35, 25, 10, 8, 13, (0, 0, 3.3)))
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
    # tidy the UI: hide the timeline header noise, keep the Layout workspace
    build_plan()
    bpy.app.timers.register(tick, first_interval=3.0)


bpy.app.timers.register(lambda: (start(), None)[1], first_interval=2.0)
