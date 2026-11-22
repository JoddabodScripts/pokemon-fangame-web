"""Build Freezer Flock step by step inside the Blender UI, so the build can be screen-recorded.

Run with a display (not -b):  blender --factory-startup -P gui_build.py
Each stage runs on a timer, so the viewport redraws in between: you see the skeleton appear,
the sculpted body, the eyes and beak, thousands of feathers, then materials and the final pose.
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


def s_body():
    ff.place_eyes()
    body, bb, radii = ff.build_body(state['arm'])
    state.update(body=body, bb=bb, radii=radii)


def s_eyes():
    for s in 'LR':
        ff.snowflake_eye(state['arm'], s)


def s_beak():
    ff.beak(state['arm'])


def s_feathers():
    ff.body_feathers(state['body'], state['arm'], state['bb'], state['radii'])


def s_wing_l():
    ff.wing(state['arm'], 'L')


def s_wing_r():
    ff.wing(state['arm'], 'R')


def s_tail():
    ff.tail(state['arm'])


def s_legs():
    ff.legs(state['arm'])


def s_ice():
    ff.ice(state['arm'])


def s_scarf():
    ff.scarf(state['arm'])
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers):
            o.parent = state['arm']


def s_pose():
    ff.pose_bones(state['arm'], ff.display_pose())
    select_only([state['arm'].name])


def s_material():
    look(-35, 10, 13, (0, 0, 3.2), 'MATERIAL')


def s_render_view():
    # light + world so the rendered viewport shows the real look
    import render2
    render2.sky()
    render2.sun()
    look(-30, 8, 12.5, (0, 0, 3.3), 'RENDERED')
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.preview_samples = 4
    sc.cycles.use_preview_denoising = True


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
    add(s_body, 2.5, (10, 10, 10, (0, 0, 2.8)))
    PLAN.extend(spin(10, -40, 8, 10, 9.5, (0, 0, 3.0)))
    add(s_eyes, 1.5, (-25, 8, 4.5, (0, -0.5, 3.95)))
    add(s_beak, 2.0, (-35, 8, 4.5, (0, -0.6, 3.9)))
    PLAN.extend(spin(-35, 20, 8, 8, 4.5, (0, -0.6, 3.9)))
    add(s_feathers, 2.5, (-30, 10, 9, (0, 0, 3.0)))
    PLAN.extend(spin(-30, 30, 10, 8, 8.5, (0, 0, 3.1)))
    add(s_wing_l, 1.5, (40, 35, 13, (1.6, 0, 3.0)))
    add(s_wing_r, 1.5, (-20, 35, 14, (0, 0, 3.0)))
    PLAN.extend(spin(-20, 20, 6, 35, 14, (0, 0, 3.0)))
    add(s_tail, 1.5, (150, 15, 10, (0, 0.6, 2.0)))
    add(s_legs, 1.5, (-40, 5, 6, (0, 0, 1.1)))
    add(s_ice, 1.5, (-25, 15, 12, (0, 0, 3.4)))
    add(s_scarf, 2.0, (-25, 8, 6, (0, -0.2, 3.3)))
    add(s_pose, 2.0, (-30, 8, 14, (0, 0, 3.4)))
    PLAN.append((s_material, 4.0))
    PLAN.extend(spin(-35, 25, 10, 8, 13, (0, 0, 3.3)))
    PLAN.append((s_render_view, 10.0))
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
