"""Render a Star Region Pokemon prototype.

  blender -b --factory-startup -P render.py -- <key> preview   # quick 3-view check sheet (for modeling)
  blender -b --factory-startup -P render.py -- <key> tpose     # T-pose reference shot
  blender -b --factory-startup -P render.py -- <key> video     # battle animation (mp4)

Output goes to 3d/renders/.
"""
import importlib.util
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402

OUT = os.path.join(HERE, 'renders')
FPS = 24


# ---------------------------------------------------------------- setup
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lib._MATS.clear()


def load_model(key):
    spec = importlib.util.spec_from_file_location(key, os.path.join(HERE, 'models', key + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rig = mod.build(lib)
    rig._module = mod
    return rig


def descendants(obj):
    out = []
    for c in obj.children:
        out.append(c)
        out += descendants(c)
    return out


def bounds(rig):
    bpy.context.view_layer.update()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    deps = bpy.context.evaluated_depsgraph_get()
    for o in descendants(rig.root):
        if o.type not in ('MESH', 'CURVE'):
            continue
        ev = o.evaluated_get(deps)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def stage(rig, quality):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = {'preview': 10, 'video': 8, 'tpose': 64}[quality]
    sc.cycles.adaptive_threshold = 0.05 if quality != 'tpose' else 0.01
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4 if quality == 'tpose' else 2
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    if quality == 'video':
        sc.render.use_simplify = True
        sc.render.simplify_subdivision_render = 1
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Punchy'
    sc.render.film_transparent = False

    # sky
    w = bpy.data.worlds.new('sky')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    grad = nt.nodes.new('ShaderNodeTexGradient')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    mapn = nt.nodes.new('ShaderNodeMapping')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    mapn.inputs['Rotation'].default_value = (0, math.pi / 2, 0)
    ramp.color_ramp.elements[0].color = (*lib._rgb('#cfe6f7'), 1)
    ramp.color_ramp.elements[1].color = (*lib._rgb('#5b9fd6'), 1)
    nt.links.new(coord.outputs['Generated'], mapn.inputs['Vector'])
    nt.links.new(mapn.outputs['Vector'], grad.inputs['Vector'])
    nt.links.new(grad.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.9

    lo, hi = bounds(rig)
    size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
    r = max(hi.x - lo.x, hi.y - lo.y) * 0.75 + 0.3

    # ground + battle platform
    ground = lib.cylinder('ground', (0, 0, -0.06), 60, 0.1, lib.mat('ground', '#7fbf63', 0.9), seg=64)
    lib.cylinder('platform', (0, 0, -0.012), r, 0.03, lib.mat('platform', '#c9b98d', 0.85), seg=64)
    lib.torus('platform_rim', (0, 0, 0.0), r, 0.025, lib.mat('platform_rim', '#a8966a', 0.8))

    # lights
    def light(name, kind, loc, energy, color='#ffffff', size_=1.0, rot=None):
        d = bpy.data.lights.new(name, kind)
        d.energy = energy
        d.color = lib._rgb(color)
        if kind == 'AREA':
            d.size = size_
        if kind == 'SUN':
            d.angle = math.radians(4)
        o = bpy.data.objects.new(name, d)
        o.location = loc
        if rot:
            o.rotation_euler = rot
        sc.collection.objects.link(o)
        return o

    light('key', 'SUN', (0, 0, 10), 3.2, '#fff4e0', rot=(math.radians(50), 0, math.radians(-35)))
    k = light('fill', 'AREA', (-4 * size, -4 * size, 2.5 * size), 220 * size * size, '#dce8ff', 3 * size)
    k.rotation_euler = (Vector((0, 0, 0.5 * size)) - k.location).to_track_quat('-Z', 'Y').to_euler()
    rim = light('rim', 'AREA', (2 * size, 3.5 * size, 3 * size), 300 * size * size, '#ffffff', 2 * size)
    rim.rotation_euler = (Vector((0, 0, 0.6 * size)) - rim.location).to_track_quat('-Z', 'Y').to_euler()
    return lo, hi, size


def camera(lo, hi, yaw_deg, pitch_deg=12, lens=50, pad=1.35, target=None, parent=None):
    center = (lo + hi) / 2 if target is None else target
    size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
    r = bpy.context.scene.render
    half_h = 18 * min(1.0, r.resolution_y / r.resolution_x)   # fit the shorter side of the frame
    fov = 2 * math.atan(half_h / lens)
    dist = size * pad / (2 * math.tan(fov / 2)) + max(hi.y - lo.y, hi.x - lo.x) / 2
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    off = Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch))) * dist
    cd = bpy.data.cameras.new('cam')
    cd.lens = lens
    cam = bpy.data.objects.new('cam', cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = center + off
    cam.rotation_euler = (-off).to_track_quat('-Z', 'Y').to_euler()
    if parent is not None:
        cam.parent = parent
    bpy.context.scene.camera = cam
    return cam


# ---------------------------------------------------------------- quick check sheet
def render_preview(key):
    rig = load_model(key)
    lo, hi, size = stage(rig, 'preview')
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 480, 400
    paths = []
    for i, (yaw, pitch) in enumerate([(-30, 12), (90, 5), (160, 15), (0, 60)]):
        cam = camera(lo, hi, yaw, pitch)
        sc.render.filepath = os.path.join(OUT, f'_preview_{key}_{i}.png')
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
        bpy.data.objects.remove(cam)
    os.system('ffmpeg -loglevel error -y ' + ' '.join(f'-i {p}' for p in paths) +
              f' -filter_complex "[0][1][2][3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0" {OUT}/preview_{key}.png')
    for p in paths:
        os.remove(p)
    print('PREVIEW', f'{OUT}/preview_{key}.png')


# ---------------------------------------------------------------- T-pose
def render_tpose(key):
    rig = load_model(key)
    for name, rot in rig.t_pose.items():
        bpy.data.objects[name].rotation_euler = rot
    lo, hi, size = stage(rig, 'tpose')
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1000
    paths = []
    for i, (yaw, pitch) in enumerate([(0, 8), (-40, 14)]):
        cam = camera(lo, hi, yaw, pitch, pad=1.25)
        sc.render.filepath = os.path.join(OUT, f'_tpose_{key}_{i}.png')
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
        bpy.data.objects.remove(cam)
    os.system(f'ffmpeg -loglevel error -y -i {paths[0]} -i {paths[1]} -filter_complex hstack {OUT}/_tpose_{key}.png')
    for p in paths:
        os.remove(p)
    print('TPOSE', f'{OUT}/_tpose_{key}.png')


# ---------------------------------------------------------------- animation
class Keys:
    """Keyframe helper that works in offsets from each pivot's rest pose."""

    def __init__(self):
        self.rest = {}

    def _rest(self, o):
        if o.name not in self.rest:
            self.rest[o.name] = (o.location.copy(), o.rotation_euler.copy(), o.scale.copy())
        return self.rest[o.name]

    def key(self, o, f, loc=None, rot=None, scale=None, absolute=False):
        rl, rr, rs = self._rest(o)
        if loc is not None:
            o.location = Vector(loc) if absolute else rl + Vector(loc)
            o.keyframe_insert('location', frame=f)
        if rot is not None:
            o.rotation_euler = Vector(rot) if absolute else Vector(rr) + Vector(rot)
            o.keyframe_insert('rotation_euler', frame=f)
        if scale is not None:
            s = Vector(scale) if not isinstance(scale, (int, float)) else Vector((scale,) * 3)
            o.scale = s if absolute else Vector((rs.x * s.x, rs.y * s.y, rs.z * s.z))
            o.keyframe_insert('scale', frame=f)


# timeline (frames at 24 fps)
T_BALL, T_OPEN, T_OUT, T_CRY, T_IDLE, T_TURN, T_WALK_END, T_BACK, T_ATK, T_STRIKE, T_HIT, T_WIN, T_END = \
    0, 14, 16, 30, 50, 74, 128, 138, 146, 158, 182, 202, 222


def _cols(n):
    return 4 if n % 4 == 0 else 3 if n % 3 == 0 else n


def wave(f, period, phase=0.0):
    return math.sin(2 * math.pi * (f / period + phase))


class Anim:
    """Handed to a model's animate(A). See MODELING_BRIEF.md, section "Animation".

    Fixed phases (frames at 24 fps). The framework throws the Star Ball and pops it open with a
    flash by frame 16; everything after that belongs to the model.
        OUT 16       the Pokemon starts to appear (it must be invisible before this, e.g. root scale 0)
        IDLE 48      settled, breathing / idling
        WALK 72      turn and move across (walk, hop, slither, glide, float...). The camera follows the root.
        WALK_END 138 must be facing the camera (-Y) again by ATTACK
        ATTACK 140   wind-up, strike, effect hits the opponent (A.opponent) by about 165
        HIT 186      gets hit (the framework adds a red flash at the Pokemon); react
        RECOVER 206  recover and finish with an in-character idle or victory pose
        END 230
    """
    T = dict(OPEN=14, OUT=16, IDLE=48, WALK=72, WALK_END=138, ATTACK=140, HIT=186, RECOVER=206, END=230)

    def __init__(self, rig, size):
        self.rig, self.size, self.lib = rig, size, lib
        self._k = Keys()

    # keyframes (offsets from each object's rest pose unless absolute=True)
    def key(self, obj, f, loc=None, rot=None, scale=None, absolute=False):
        self._k.key(obj, f, loc, rot, scale, absolute)

    @staticmethod
    def wave(f, period, phase=0.0):
        return wave(f, period, phase)

    @staticmethod
    def ease(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    @staticmethod
    def frames(f0, f1, step=1):
        return range(int(f0), int(f1) + 1, step)

    def opponent(self, from_xyz):
        """Where the opposing Pokemon would stand, seen from a Pokemon at from_xyz (world)."""
        x, y, _ = from_xyz
        return Vector((x + 2.6 * self.size, y - 1.8 * self.size, 0.45 * self.size))

    def world(self, obj, f, local=(0, 0, 0)):
        """World position of a point on obj at frame f (after the keys set so far)."""
        sc = bpy.context.scene
        sc.frame_set(int(f))
        return obj.matrix_world @ Vector(local)

    def emission(self, material, f, strength):
        b = material.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
        b.default_value = strength
        b.keyframe_insert('default_value', frame=f)

    def alpha(self, material, f, value):
        material.blend_method = 'BLEND'
        b = material.node_tree.nodes['Principled BSDF'].inputs['Alpha']
        b.default_value = value
        b.keyframe_insert('default_value', frame=f)

    def light(self, name, color, loc, keys, kind='POINT', radius=0.1, parent=None):
        """A light whose energy follows keys = [(frame, watts), ...]."""
        d = bpy.data.lights.new(name, kind)
        d.color = lib._rgb(color)
        d.shadow_soft_size = radius
        o = bpy.data.objects.new(name, d)
        bpy.context.scene.collection.objects.link(o)
        o.location = loc
        if parent is not None:
            o.parent = parent
        for f, e in keys:
            d.energy = e
            d.keyframe_insert('energy', frame=f)
        return o

    @staticmethod
    def interp(obj, kind='LINEAR'):
        """Set the interpolation of every key on obj (LINEAR, BEZIER, CONSTANT)."""
        if obj.animation_data and obj.animation_data.action:
            for fc in obj.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = kind


def animate_custom(rig, size):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, Anim.T['END']
    sc.render.fps = FPS
    sendout_ball(size)
    A = Anim(rig, size)
    rig._module.animate(A)
    # the camera follows the root's x
    track = lib.pivot('cam_track')
    K = Keys()
    for f in range(0, Anim.T['END'] + 1, 3):
        sc.frame_set(f)
        K.key(track, f, loc=(rig.root.matrix_world.translation.x, 0, 0), absolute=True)
    sc.frame_set(Anim.T['HIT'])
    hit_flash(size, rig.root.matrix_world.translation.x, Anim.T['HIT'])
    sc.frame_set(0)
    return track


def animate(rig, size):
    if hasattr(rig._module, 'animate'):
        return animate_custom(rig, size)
    K = Keys()
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, T_END
    sc.render.fps = FPS
    root, body, head = rig.root, rig.body or rig.root, rig.head
    walk_dist = 1.6 * size

    # ---- send-out: root scale pops from 0
    K.key(root, 0, scale=0.001); K.key(root, T_OUT, scale=0.001)
    K.key(root, T_OUT + 6, scale=1.15); K.key(root, T_OUT + 10, scale=0.94); K.key(root, T_OUT + 14, scale=1.0)

    # ---- root path: idle at origin, turn right, walk +X, turn back, attack lunge, knockback
    K.key(root, 0, loc=(0, 0, 0), rot=(0, 0, 0))
    K.key(root, T_TURN, rot=(0, 0, 0)); K.key(root, T_TURN + 6, rot=(0, 0, math.pi / 2))
    K.key(root, T_TURN + 6, loc=(0, 0, 0))
    K.key(root, T_WALK_END, loc=(walk_dist, 0, 0)); K.key(root, T_WALK_END, rot=(0, 0, math.pi / 2))
    K.key(root, T_BACK, rot=(0, 0, 0)); K.key(root, T_BACK, loc=(walk_dist, 0, 0))
    K.key(root, T_ATK + 6, loc=(walk_dist, 0.12 * size, 0))                       # wind-up, lean back
    K.key(root, T_STRIKE, loc=(walk_dist, -0.45 * size, 0))                       # lunge
    K.key(root, T_STRIKE + 12, loc=(walk_dist, 0, 0))
    K.key(root, T_HIT, loc=(walk_dist, 0, 0)); K.key(root, T_HIT, rot=(0, 0, 0))
    K.key(root, T_HIT + 3, loc=(walk_dist, 0.3 * size, 0)); K.key(root, T_HIT + 3, rot=(0, 0, math.radians(-12)))
    K.key(root, T_HIT + 14, loc=(walk_dist, 0, 0)); K.key(root, T_HIT + 14, rot=(0, 0, 0))
    K.key(root, T_END, loc=(walk_dist, 0, 0))

    walking = lambda f: T_TURN + 6 <= f <= T_WALK_END  # noqa: E731
    gait = rig.gait
    hover = 0.18 * size if gait in ('float', 'fly') else 0.0

    for f in range(0, T_END + 1, 2):
        mv = walking(f)
        energy = 1.0 if mv else 0.35
        # body motion per gait
        if gait == 'walk':
            bob = abs(wave(f, 8)) * 0.04 * size if mv else (wave(f, 36) * 0.012 * size)
            K.key(body, f, loc=(0, 0, bob), rot=(0, wave(f, 16) * (0.06 if mv else 0.015), 0))
        elif gait == 'hop':
            ph = (f % 16) / 16 if mv else (f % 30) / 30
            height = (0.3 if mv else 0.06) * size
            up = math.sin(math.pi * ph) * height
            sq = 1 + (0.18 if mv else 0.05) * math.cos(2 * math.pi * ph)
            K.key(body, f, loc=(0, 0, up), scale=(1 / math.sqrt(sq), 1 / math.sqrt(sq), sq))
        else:  # float / fly
            K.key(body, f, loc=(0, 0, hover + wave(f, 30) * 0.05 * size), rot=(wave(f, 40) * 0.05, wave(f, 24) * (0.08 if mv else 0.04), 0))
        for leg, ph in rig.legs:
            if gait == 'fly':
                K.key(leg, f, rot=(math.radians(35), 0, 0))
            else:
                K.key(leg, f, rot=(wave(f, 16, ph) * math.radians(30) * energy if mv else wave(f, 36, ph) * 0.03, 0, 0))
        for arm, ph in rig.arms:
            K.key(arm, f, rot=(wave(f, 16, ph) * math.radians(28 if mv else 6), 0, 0))
        for wing, side in rig.wings:
            amp = math.radians(50 if (gait == 'fly' or mv) else 12)
            K.key(wing, f, rot=(0, side * wave(f, 10 if gait == 'fly' else 14) * amp, 0))
        for i, t in enumerate(rig.tail):
            K.key(t, f, rot=(0, 0, wave(f, 28, -0.12 * i) * math.radians(10 + 6 * energy)))
        for o, kind in rig.extras:
            if kind == 'flicker':
                K.key(o, f, scale=(1 + 0.08 * wave(f, 6), 1 + 0.08 * wave(f, 7), 1 + 0.15 * wave(f, 5)))
            elif kind == 'spin':
                K.key(o, f, rot=(0, 0, f * 0.08))
            elif kind == 'sway':
                K.key(o, f, rot=(wave(f, 30) * 0.12, 0, wave(f, 40) * 0.1))
            elif kind == 'pulse':
                K.key(o, f, scale=1 + 0.06 * wave(f, 20))
        if head is not None and not (T_CRY - 4 <= f <= T_IDLE + 2) and not (T_ATK <= f <= T_STRIKE + 10) and not (T_HIT <= f <= T_HIT + 14):
            K.key(head, f, rot=(wave(f, 48) * 0.04, 0, wave(f, 70) * 0.08))

    # ---- cry after send-out: head up, jaw open, body stretch
    if head is not None:
        K.key(head, T_CRY - 4, rot=(0, 0, 0)); K.key(head, T_CRY + 4, rot=(math.radians(-25), 0, 0))
        K.key(head, T_IDLE - 6, rot=(math.radians(-22), 0, 0)); K.key(head, T_IDLE + 2, rot=(0, 0, 0))
    if rig.jaw is not None:
        for f, a in [(0, 0), (T_CRY - 2, 0), (T_CRY + 4, 35), (T_IDLE - 6, 30), (T_IDLE, 0),
                     (T_ATK + 4, 0), (T_STRIKE - 2, 45), (T_STRIKE + 2, 0), (T_STRIKE + 6, 0), (T_HIT, 0), (T_HIT + 2, 20), (T_HIT + 8, 0)]:
            K.key(rig.jaw, f, rot=(math.radians(a), 0, 0))

    # ---- attack: wind-up and strike on head/body
    if head is not None:
        K.key(head, T_ATK, rot=(0, 0, 0)); K.key(head, T_ATK + 8, rot=(math.radians(-20), 0, 0))
        K.key(head, T_STRIKE, rot=(math.radians(18), 0, 0)); K.key(head, T_STRIKE + 10, rot=(0, 0, 0))
        K.key(head, T_HIT, rot=(0, 0, 0)); K.key(head, T_HIT + 3, rot=(math.radians(-18), 0, math.radians(10)))
        K.key(head, T_HIT + 14, rot=(0, 0, 0))
    for arm, ph in rig.arms:
        K.key(arm, T_ATK, rot=(0, 0, 0)); K.key(arm, T_ATK + 8, rot=(math.radians(-70), 0, 0))
        K.key(arm, T_STRIKE, rot=(math.radians(60), 0, 0)); K.key(arm, T_STRIKE + 10, rot=(0, 0, 0))
    for wing, side in rig.wings:
        K.key(wing, T_ATK + 4, rot=(0, side * math.radians(-60), 0)); K.key(wing, T_STRIKE, rot=(0, side * math.radians(70), 0))

    effects(rig, size, walk_dist)
    sendout_ball(size)
    hit_flash(size, walk_dist)

    # camera follows the walk
    track = lib.pivot('cam_track')
    K.key(track, 0, loc=(0, 0, 0)); K.key(track, T_TURN + 6, loc=(0, 0, 0)); K.key(track, T_WALK_END, loc=(walk_dist, 0, 0))
    for fc in track.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
    return track


TYPE_FX = {
    'Grass': ('#5fcf4a', 'leaf'), 'Fire': ('#ff5a00', 'orb'), 'Water': ('#4aa8ff', 'bubble'),
    'Ice': ('#9ff0ff', 'shard'), 'Flying': ('#ffffff', 'ring'), 'Normal': ('#ffffff', 'ring'),
}


def effects(rig, size, walk_dist):
    """Projectiles (cast) or an impact burst (bite/slam/peck) at the strike."""
    K = Keys()
    color, kind = TYPE_FX.get(rig.type, TYPE_FX['Normal'])
    glow = lib.mat('fx_' + kind, color, 0.2, emit=2.5 if kind in ('orb', 'shard') else 1.2,
                   alpha=0.85 if kind == 'bubble' else 1.0, transmission=0.6 if kind == 'bubble' else 0)
    ox, oy, oz = rig.attack_origin
    start = Vector((walk_dist + ox, oy - 0.45 * size, oz))
    end = Vector((walk_dist + 2.6 * size, -1.8 * size, 0.45 * size))
    n = 6 if rig.attack == 'cast' else 1
    for i in range(n):
        f0 = T_STRIKE - 1 + i * 2
        o = lib.pivot(f'fxp{i}')
        if kind == 'leaf':
            lib.sphere(f'fx{i}', (0, 0, 0), (0.09 * size, 0.03 * size, 0.05 * size), glow, o)
        elif kind == 'shard':
            lib.cone(f'fx{i}', (0, 0, 0), 0.05 * size, 0.0, 0.25 * size, glow, o, rot=(math.pi / 2, 0, 0), seg=6)
        elif kind == 'ring':
            lib.torus(f'fx{i}', (0, 0, 0), 0.12 * size, 0.02 * size, glow, o, rot=(math.pi / 2, 0, 0))
        elif kind == 'orb':
            lib.sphere(f'fx{i}c', (0, 0, 0), 0.04 * size, lib.mat('fx_core', '#fff0a0', 0.2, emit=5), o)
            lib.sphere(f'fx{i}', (0, 0, 0), 0.07 * size, lib.mat('fx_shell', '#ff3c00', 0.3, emit=2.0, alpha=0.7), o)
        else:
            lib.sphere(f'fx{i}', (0, 0, 0), 0.08 * size, glow, o)
        if rig.attack == 'cast':
            jitter = Vector(((i % 3 - 1) * 0.12 * size, 0, ((i * 7) % 3 - 1) * 0.1 * size))
            K.key(o, 0, loc=start, scale=0.001, absolute=True)
            K.key(o, f0, loc=start, scale=0.001, absolute=True)
            K.key(o, f0 + 1, loc=start, scale=1.0, rot=(0, 0, 0), absolute=True)
            K.key(o, f0 + 12, loc=end + jitter, scale=1.3 if kind in ('orb', 'ring') else 1.0, rot=(0, i * 2.0, 6.0), absolute=True)
            K.key(o, f0 + 14, loc=end + jitter, scale=0.001, absolute=True)
        else:
            hit = Vector((walk_dist + ox, oy - 0.9 * size, oz))
            K.key(o, 0, loc=hit, scale=0.001, absolute=True)
            K.key(o, T_STRIKE - 1, loc=hit, scale=0.001, absolute=True)
            K.key(o, T_STRIKE + 3, loc=hit, scale=2.2, absolute=True)
            K.key(o, T_STRIKE + 9, loc=hit, scale=0.001, absolute=True)
    # flash of light at the strike
    d = bpy.data.lights.new('fx_light', 'POINT')
    d.color = lib._rgb(color)
    lo = bpy.data.objects.new('fx_light', d)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = start
    for f, e in [(0, 0), (T_STRIKE - 2, 0), (T_STRIKE + 2, 400 * size * size), (T_STRIKE + 14, 0)]:
        d.energy = e
        d.keyframe_insert('energy', frame=f)


def sendout_ball(size):
    """Star Ball arcs in, pops open with a white flash."""
    K = Keys()
    ball = lib.pivot('ball')
    r = 0.12 * size
    top = lib.pivot('ball_top_p', (0, r * 0.9, 0), ball)          # hinge at the back of the ball
    bot = lib.pivot('ball_bot_p', (0, 0, 0), ball)
    for piv, up, col, nm in ((top, True, '#f0c020', 'ball_top'), (bot, False, '#f4f4f4', 'ball_bot')):
        h = lib.sphere(nm, (0, -r * 0.9 if up else 0, 0), r, lib.mat(nm, col, 0.3, coat=1), piv)
        import bmesh as _bm
        bm = _bm.new(); bm.from_mesh(h.data)
        _bm.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0),
                             plane_no=(0, 0, 1), clear_inner=up, clear_outer=not up)
        bm.to_mesh(h.data); bm.free()
        h.modifiers.new('solid', 'SOLIDIFY').thickness = 0.06
    lib.torus('ball_band', (0, 0, 0), r, 0.1 * r, lib.mat('ball_band', '#202028', 0.4), bot)
    lib.cylinder('ball_button', (0, -r, 0), 0.28 * r, 0.12 * r, lib.mat('ball_button', '#ffffff', 0.2), bot, rot=(math.pi / 2, 0, 0))
    p0 = Vector((-2.2 * size, -1.6 * size, 0.3 * size))
    p1 = Vector((0, -0.25 * size, 0.55 * size))
    for f in range(0, T_OPEN + 1, 2):
        t = f / T_OPEN
        pos = p0.lerp(p1, t) + Vector((0, 0, math.sin(math.pi * t) * 1.0 * size))
        K.key(ball, f, loc=pos, rot=(f * 0.6, 0, f * 0.3), scale=1.0, absolute=True)
    K.key(top, T_OPEN, rot=(0, 0, 0)); K.key(top, T_OPEN + 4, rot=(math.radians(-100), 0, 0))
    K.key(ball, T_OPEN + 2, scale=1.0, absolute=True); K.key(ball, T_OPEN + 5, scale=0.001, absolute=True)
    flash = lib.sphere('flash', (0, -0.1 * size, 0.5 * size), 1.0, lib.mat('flash', '#ffffff', 0.5, emit=4, alpha=0.5))
    K.key(flash, 0, scale=0.001); K.key(flash, T_OPEN, scale=0.001)
    K.key(flash, T_OPEN + 3, scale=0.3 * size); K.key(flash, T_OPEN + 8, scale=0.001)
    d = bpy.data.lights.new('flash_light', 'POINT')
    lo = bpy.data.objects.new('flash_light', d)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (0, -0.8 * size, 0.6 * size)
    for f, e in [(0, 0), (T_OPEN, 0), (T_OPEN + 3, 1500 * size * size), (T_OPEN + 12, 0)]:
        d.energy = e
        d.keyframe_insert('energy', frame=f)


def hit_flash(size, walk_dist, t_hit=None):
    t_hit = T_HIT if t_hit is None else t_hit
    d = bpy.data.lights.new('hit_light', 'POINT')
    d.color = lib._rgb('#ff4040')
    lo = bpy.data.objects.new('hit_light', d)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (walk_dist, -1.2 * size, 0.8 * size)
    for f, e in [(0, 0), (t_hit, 0), (t_hit + 1, 900 * size * size), (t_hit + 4, 0), (t_hit + 6, 600 * size * size), (t_hit + 9, 0)]:
        d.energy = e
        d.keyframe_insert('energy', frame=f)


def render_video(key, start=None, end=None):
    rig = load_model(key)
    lo, hi, size = stage(rig, 'video')
    track = animate(rig, size)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    sc.frame_set(0)
    # frame for the whole move: creature plus walk distance
    wide_hi = hi.copy()
    camera(lo, wide_hi, -28, 12, lens=40, pad=1.4, target=(lo + hi) / 2, parent=track)
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    if start is not None:
        sc.frame_start, sc.frame_end = start, end
    sc.render.filepath = os.path.join(OUT, f'_video_{key}.mp4')
    t = time.time()
    bpy.ops.render.render(animation=True)
    print('VIDEO', sc.render.filepath, 'seconds', round(time.time() - t))


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    key, mode = args[0], args[1]
    os.makedirs(OUT, exist_ok=True)
    reset()
    if mode == 'preview':
        render_preview(key)
    elif mode == 'tpose':
        render_tpose(key)
    elif mode == 'frames':
        # spot-check the animation: render chosen frames as a contact sheet
        rig = load_model(key)
        lo, hi, size = stage(rig, 'preview')
        track = animate(rig, size)
        sc = bpy.context.scene
        sc.render.resolution_x, sc.render.resolution_y = 427, 240
        sc.frame_set(0)
        camera(lo, hi, -28, 12, lens=40, pad=1.4, target=(lo + hi) / 2, parent=track)
        paths = []
        for f in [int(a) for a in args[2:]]:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(OUT, f'_frame_{key}_{f:03d}.png')
            bpy.ops.render.render(write_still=True)
            paths.append(sc.render.filepath)
        os.system('ffmpeg -loglevel error -y ' + ' '.join(f'-i {p}' for p in paths) +
                  f' -filter_complex "xstack=inputs={len(paths)}:grid={_cols(len(paths))}x{len(paths) // _cols(len(paths))}" {OUT}/_frames_{key}.png')
        for p in paths:
            os.remove(p)
    elif mode == 'video':
        rng = (int(args[2]), int(args[3])) if len(args) > 3 else (None, None)
        render_video(key, *rng)
