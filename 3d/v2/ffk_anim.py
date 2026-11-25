"""Freezer Flock battle animation: send-out, hover, advance, Brittle Blast, hit, recover.

Everything is keyed on the skeleton's pose bones, the rig's root object and a few effect objects.
Frames are at 24 fps. The opponent stands off-screen at OPP.
"""
import math
import random

import bpy
from mathutils import Euler, Vector as V

import kit
import freezer_flock as ff

FPS = 24
T = dict(throw=0, open=26, appear=30, land=54, idle=84, advance=180, charge=236, dive=272, impact=284,
         back=300, hit=336, recover=364, end=420)
OPP = V((5.5, -13.0, 0.0))
HOVER = V((0, 0, 0.7))
S = ff.SIZE           # model scale: framing and effects that sit on the body grow with it
rnd = random.Random(11)


# ------------------------------------------------------------------ keying helpers
def kp(obj, path, f, value, index=-1):
    setattr(obj, path, value) if index < 0 else getattr(obj, path).__setitem__(index, value)
    obj.keyframe_insert(path, frame=f, index=index)


def kbone(arm, name, f, rot):
    pb = arm.pose.bones[name]
    pb.rotation_euler = rot
    pb.keyframe_insert('rotation_euler', frame=f)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def ease_out_back(t, s=1.7):
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


# ------------------------------------------------------------------ the flight cycle
def wing_pose(phi, power=1.0, raise_=0.0, fold=0.0, spread=0.0):
    """Pose of both wings at flap phase phi (0 = top of the stroke). power scales the stroke,
    raise_ lifts the whole stroke, fold tucks the wings (0..1), spread holds them wide (display)."""
    P = {}
    w = 2 * math.pi
    up = math.cos(w * phi)
    up_lag = math.cos(w * (phi - 0.07))
    up_lag2 = math.cos(w * (phi - 0.13))
    upstroke = max(0.0, -math.sin(w * phi))            # wings rising: fold a little to cut the air
    for s, sx in ff.SIDE.items():
        sh_x = 0.32 + raise_ + 0.62 * power * up
        sh_y = -(0.6 - 0.25 * math.sin(w * phi) * power)
        sh_z = -0.08 + 0.2 * upstroke
        fa_x = -0.22 * power * up_lag
        fa_z = 0.25 + 0.55 * upstroke * power
        hd_x = -0.25 * power * up_lag2
        hd_z = -0.1 + 0.6 * upstroke * power
        # fold: wings tucked against the body (dive)
        sh = mix((sh_x, sh_y, sh_z), (-0.15, -0.25, 1.25), fold)    # swept back like an arrowhead
        fa = mix((fa_x, 0.0, fa_z), (0.0, 0.0, 0.25), fold)
        hd = mix((hd_x, 0.0, hd_z), (0.0, 0.0, 0.15), fold)
        # display spread: the heraldic pose
        sh = mix(sh, (0.55, -1.05, -0.3), spread)
        fa = mix(fa, (-0.1, 0.1, 0.3), spread)
        hd = mix(hd, (-0.15, 0.05, -0.12), spread)
        P['shoulder.' + s] = (sh[0], sx * sh[1], sx * sh[2])
        P['forearm.' + s] = (fa[0], sx * fa[1], sx * fa[2])
        P['hand.' + s] = (hd[0], sx * hd[1], sx * hd[2])
    return P


def body_pose(phi, power=1.0, tuck=0.0):
    w = 2 * math.pi
    P = {}
    bob = math.sin(w * (phi - 0.12))
    P['chest'] = (0.06 + 0.04 * power * bob, 0, 0)
    P['neck'] = (-0.1 - 0.05 * power * bob, 0, 0)
    P['head'] = (0.06 + 0.04 * power * bob, 0, 0)
    P['tail'] = (0.3 + 0.12 * power * math.sin(w * (phi - 0.3)), 0, 0)
    for s in ('L', 'R'):
        P['thigh.' + s] = mix((0.25 + 0.05 * bob, 0, 0), (0.9, 0, 0), tuck)
        P['shin.' + s] = mix((-0.2 - 0.05 * bob, 0, 0), (-1.2, 0, 0), tuck)
        P['foot.' + s] = mix((0.0, 0, 0), (0.6, 0, 0), tuck)
    for i, n in enumerate(('scarf0', 'scarf1', 'scarf2')):
        P[n] = (0.15 * math.sin(w * (phi - 0.2 - 0.12 * i)) * power, 0, 0.18 * math.sin(w * (phi * 0.5 - 0.1 * i)))
    return P


def apply(arm, f, P, extra=None):
    if extra:
        for k, v in extra.items():
            base = P.get(k, (0, 0, 0))
            P[k] = tuple(a + b for a, b in zip(base, v))
    for n, r in P.items():
        kbone(arm, n, f, r)


# ------------------------------------------------------------------ effects
def mat_glow(name, color, strength, alpha=1.0):
    m = kit.mat_basic(name, color, rough=0.4, emit=strength, emit_color=color, alpha=alpha)
    if alpha < 1:
        m.blend_method = 'BLEND'
    return m


def star_ball():
    """Yellow-and-white Star Ball with a black band and a star on the button."""
    root = kit.empty('ball')
    top = kit.empty('ball_top', (0, 0.18, 0), root)
    r = 0.22
    for nm, up, col in (('ball_t', True, '#f5c21b'), ('ball_b', False, '#f4f4f4')):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r)
        h = bpy.context.active_object
        h.name = nm
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(h.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0),
                               plane_no=(0, 0, 1), clear_inner=up, clear_outer=not up)
        bm.to_mesh(h.data)
        bm.free()
        kit.smooth_obj(h)
        h.modifiers.new('sol', 'SOLIDIFY').thickness = 0.012
        h.data.materials.append(kit.mat_basic(nm + 'm', col, rough=0.25, coat=1.0))
        if up:
            h.parent = top
            h.location = (0, -0.18, 0)
        else:
            h.parent = root
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.018, major_segments=64)
    band = bpy.context.active_object
    band.parent = root
    band.data.materials.append(kit.mat_basic('ballband', '#202430', rough=0.4))
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.06, depth=0.04, location=(0, -r, 0), rotation=(math.pi / 2, 0, 0))
    btn = bpy.context.active_object
    btn.parent = root
    btn.data.materials.append(kit.mat_basic('ballbtn', '#ffffff', rough=0.2, coat=1.0))
    return root, top


def crystal_obj(name, L, r, mat, parent=None):
    vs, fs = ff.crystal_geo(L, r)
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, y, z - L * 0.4) for x, y, z in vs], [], fs)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    return kit.link(o, parent)


def sphere_obj(name, r, mat, loc=(0, 0, 0), parent=None, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    o = bpy.data.objects[bpy.context.active_object.name]
    o.name = name
    kit.smooth_obj(o)
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def point_light(name, loc, color, keys, radius=0.3):
    d = bpy.data.lights.new(name, 'POINT')
    d.color = kit.srgb(color)
    d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d)
    o.location = loc
    kit.link(o)
    for f, e in keys:
        d.energy = e
        d.keyframe_insert('energy', frame=f)
    return o


def scale_keys(o, keys):
    for f, s in keys:
        o.scale = (s, s, s) if isinstance(s, (int, float)) else s
        o.keyframe_insert('scale', frame=f)


def loc_keys(o, keys):
    for f, p in keys:
        o.location = p
        o.keyframe_insert('location', frame=f)


def snowfall():
    """Two drifting layers of snowflakes falling through the whole shot."""
    for layer in range(2):
        mb = kit.MeshBuilder()
        r2 = random.Random(20 + layer)
        for i in range(1400):
            p = V((r2.uniform(-22, 22), r2.uniform(-22, 18), r2.uniform(0, 30)))
            s = r2.uniform(0.015, 0.035)
            vs = [(p.x - s, p.y, p.z), (p.x, p.y, p.z + s), (p.x + s, p.y, p.z), (p.x, p.y, p.z - s)]
            mb.add(vs, [(0, 1, 2, 3)], [(1, 1, 1)] * 4)
        o = mb.build(f'snowfall{layer}', kit.mat_basic('flakem', '#ffffff', rough=0.5, emit=0.8), smooth=False)
        speed = 0.9 + 0.5 * layer
        loc_keys(o, [(0, (0, 0, 0)), (T['end'], (1.5 - 3 * layer, 0, -speed * T['end'] / FPS))])
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'


# ------------------------------------------------------------------ the performance
def animate(rig):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, T['end']
    sc.render.fps = FPS
    arm = rig['arm']
    root = rig['root']
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'

    # ---- 1. the Star Ball arcs in and pops open
    ball, top = star_ball()
    p0, p1 = V((-6.5, -9.0, 1.2)), V((0.0, -1.4, 1.6))
    for f in range(T['throw'], T['open'] + 1, 2):
        t = (f - T['throw']) / (T['open'] - T['throw'])
        pos = p0.lerp(p1, t) + V((0, 0, 3.2 * math.sin(math.pi * t)))
        loc_keys(ball, [(f, pos)])
        ball.rotation_euler = (f * 0.5, 0, f * 0.2)
        ball.keyframe_insert('rotation_euler', frame=f)
    kp(top, 'rotation_euler', T['open'], Euler((0, 0, 0)))
    kp(top, 'rotation_euler', T['open'] + 5, Euler((math.radians(-110), 0, 0)))
    scale_keys(ball, [(T['open'] + 4, 1.0), (T['open'] + 10, 0.0)])
    flash = sphere_obj('flash', 1.0, mat_glow('flashm', '#ffffff', 12, alpha=0.6), p1)
    scale_keys(flash, [(0, 0.0), (T['open'], 0.0), (T['open'] + 4, 1.6), (T['open'] + 12, 0.0)])
    point_light('flash_light', p1 + V((0, -0.5, 0.5)), '#fff6e0', [(0, 0), (T['open'], 0), (T['open'] + 3, 25000), (T['open'] + 14, 0)])
    # streaks of light that draw the silhouette
    for i in range(14):
        a = 2 * math.pi * i / 14
        o = sphere_obj(f'spark{i}', 0.06, mat_glow('sparkm', '#dff4ff', 20), p1, seg=8)
        end = V((math.cos(a) * 3.2, math.sin(a) * 1.2, 3.0 + math.sin(a) * 2.2))
        loc_keys(o, [(T['open'], p1), (T['open'] + 14, end)])
        scale_keys(o, [(0, 0.0), (T['open'], 0.0), (T['open'] + 2, 1.0), (T['open'] + 12, 0.8), (T['open'] + 16, 0.0)])

    # ---- 2. Freezer Flock appears: grows out of the light, then a huge entrance flap and a screech
    for f, s in [(0, 0.0), (T['appear'], 0.0), (T['appear'] + 8, 0.55), (T['appear'] + 15, 1.08), (T['appear'] + 20, 0.97), (T['land'], 1.0)]:
        root.scale = (s, s, s)
        root.keyframe_insert('scale', frame=f)
    glow = sphere_obj('appear_glow', 1.0, mat_glow('appearm', '#e8f8ff', 3, alpha=0.18), V((0, 0, 3.0 * S)))
    scale_keys(glow, [(0, 0.0), (T['appear'], 0.0), (T['appear'] + 6, (2.2 * S, 1.4 * S, 2.4 * S)), (T['appear'] + 14, 0.0)])

    def pos_at(f):
        """Root path: hover in place, advance, rise, dive, return, recoil."""
        if f < T['advance']:
            return HOVER.copy()
        if f < T['charge']:
            t = smooth((f - T['advance']) / (T['charge'] - T['advance']))
            return HOVER + V((0, -2.5 * t, 0.3 * t))
        base = HOVER + V((0, -2.5, 0.3))
        if f < T['dive']:
            t = smooth((f - T['charge']) / (T['dive'] - T['charge']))
            return base + V((0, 0.6 * t, 2.6 * t))
        top = base + V((0, 0.6, 2.6))
        tgt = OPP + V((-1.6, 4.6, 1.9)) * S  # rig origin is at the feet: the head lands ~4*S m ahead
        if f < T['impact']:
            t = ((f - T['dive']) / (T['impact'] - T['dive'])) ** 1.6
            return top.lerp(tgt, t)
        if f < T['back']:
            t = smooth((f - T['impact']) / (T['back'] - T['impact']))
            return tgt.lerp(tgt + V((-1.0, 1.5, 3.0)), t)
        if f < T['hit']:
            t = smooth((f - T['back']) / (T['hit'] - T['back']))
            return (tgt + V((-1.0, 1.5, 3.0))).lerp(HOVER, t)
        if f < T['recover']:
            t = (f - T['hit']) / (T['recover'] - T['hit'])
            return HOVER + V((0, 1.1 * math.sin(math.pi * min(1, t * 1.6)) * (1 - t * 0.4), -0.3 * math.sin(math.pi * t)))
        return HOVER.copy()

    # flap rate and strength over time
    def flap_params(f):
        if f < T['land']:
            return 0.9, 0.0, 0.0
        if f < T['idle']:
            return 1.3, 0.25, 0.0                       # the big entrance beat
        if f < T['advance']:
            return 0.85, 0.0, 0.0
        if f < T['charge']:
            return 1.1, 0.0, 0.0
        if f < T['dive']:
            return 1.25, 0.15, 0.0
        if f < T['impact'] + 4:
            return 0.0, 0.0, 1.0
        return 1.0, 0.0, 0.0

    period = 30.0           # frames per wingbeat
    phi = 0.0
    last = 0
    blast_spread = {}
    for f in range(0, T['end'] + 1, 2):
        power, raise_, fold = flap_params(f)
        # smooth transitions between flap settings
        p2, r2, f2 = flap_params(f - 6)
        power, raise_, fold = (power + p2) / 2, (raise_ + r2) / 2, (fold + f2) / 2
        rate = 1.0 if f < T['charge'] else 1.25
        phi += (f - last) / period * rate
        last = f
        spread = 0.0
        if T['land'] - 4 <= f < T['land'] + 10:
            spread = smooth((f - (T['land'] - 4)) / 8)                # wings flung open on arrival
        elif T['land'] + 10 <= f < T['land'] + 18:
            spread = 1 - smooth((f - T['land'] - 10) / 8)
        if T['charge'] + 10 <= f < T['dive']:
            spread = smooth((f - T['charge'] - 10) / 10)              # Brittle Blast wind-up: wings high
        if T['hit'] - 2 <= f < T['hit'] + 6:
            spread = 0.0
        if T['recover'] + 16 <= f:
            spread = smooth((f - T['recover'] - 16) / 12) * 0.85       # defiant finish
        P = wing_pose(phi, power * (1 - spread), raise_ + (0.35 if T['charge'] + 10 <= f < T['dive'] else 0), fold, spread)
        tuck = 1.0 if T['dive'] - 2 <= f < T['impact'] + 2 else 0.0
        B = body_pose(phi, max(0.4, power), tuck)
        extra = {}
        # head: looks around while idling, locks onto the opponent for the attack
        if T['idle'] <= f < T['advance']:
            t = (f - T['idle']) / (T['advance'] - T['idle'])
            extra['head'] = (0.05 * math.sin(t * 6.0), 0.35 * math.sin(t * 2 * math.pi), 0)
            extra['neck'] = (0, 0.12 * math.sin(t * 2 * math.pi - 0.4), 0)
        if T['charge'] <= f < T['impact']:
            extra['chest'] = (-0.25 * smooth((f - T['charge']) / 12), 0, 0)
            extra['head'] = (0.25 if f >= T['dive'] else -0.15, 0, 0)
        if T['dive'] - 2 <= f < T['impact'] + 2:
            extra['chest'] = (0.6, 0, 0)
            extra['neck'] = (0.3, 0, 0)
        if T['hit'] <= f < T['hit'] + 16:
            t = (f - T['hit']) / 16
            k = math.sin(math.pi * min(1, t * 2)) * (1 - t)
            extra['chest'] = (-0.45 * k, 0, 0.1 * k)
            extra['neck'] = (-0.3 * k, 0.2 * k, 0)
            extra['head'] = (-0.25 * k, -0.35 * k, 0.15 * k)
        if T['hit'] + 16 <= f < T['recover'] + 10:
            # shake it off: quick head and body shivers
            t = (f - T['hit'] - 16) / (T['recover'] + 10 - T['hit'] - 16)
            extra['head'] = (0, 0.35 * math.sin(t * 28) * (1 - t), 0)
            extra['chest'] = (0, 0.08 * math.sin(t * 28 + 1) * (1 - t), 0)
        # screeches: jaw open, head up
        jaw = 0.0
        for s0, s1 in ((T['land'] + 2, T['land'] + 22), (T['charge'] + 10, T['dive'] - 2), (T['recover'] + 20, T['end'] - 10)):
            if s0 <= f < s1:
                t = (f - s0) / (s1 - s0)
                k = smooth(t * 4) * (1 - smooth((t - 0.8) * 5))
                jaw = max(jaw, k)
                extra['head'] = tuple(a + b for a, b in zip(extra.get('head', (0, 0, 0)), (-0.3 * k, 0, 0)))
                extra['neck'] = tuple(a + b for a, b in zip(extra.get('neck', (0, 0, 0)), (-0.15 * k, 0, 0)))
        if T['hit'] <= f < T['hit'] + 10:
            jaw = max(jaw, 0.6)
        extra['jaw'] = (-0.45 * jaw, 0, 0)
        P.update(B)
        apply(arm, f, P, extra)
        # root: path + flap bob + facing
        pos = pos_at(f)
        bob = 0.16 * math.sin(2 * math.pi * (phi - 0.15)) * power * (1 - fold)
        arm.location = pos + V((0, 0, bob))
        arm.keyframe_insert('location', frame=f)
        yaw = 0.0
        pitch = 0.0
        if T['advance'] <= f < T['back']:
            d = (OPP - pos)
            yaw = math.atan2(d.x, -d.y) * smooth((f - T['advance']) / 20)
        if T['dive'] - 2 <= f < T['impact'] + 2:
            v = pos_at(f + 2) - pos_at(f - 2)
            elev = math.asin(max(-1.0, min(1.0, v.z / max(1e-4, v.length))))
            pitch = (math.pi / 2 - elev) * smooth((f - T['dive'] + 2) / 4)
            yaw = math.atan2(v.x, -v.y)
        elif T['impact'] + 2 <= f < T['impact'] + 12:
            pitch = 1.6 * (1 - smooth((f - T['impact'] - 2) / 10))
        elif T['charge'] <= f < T['dive']:
            pitch = -0.25 * smooth((f - T['charge']) / 14)
        if T['back'] <= f < T['hit']:
            yaw = math.atan2(OPP.x, -OPP.y) * (1 - smooth((f - T['back']) / 24))
        arm.rotation_euler = (pitch, 0, yaw)
        arm.keyframe_insert('rotation_euler', frame=f)

    # ---- 3. Brittle Blast effects
    icem = kit.mat_ice('blastice', '#bff0ff', emit=1.6)
    # crystals swirl around the bird while it charges, then rocket ahead of the dive
    shards = []
    for i in range(22):
        o = crystal_obj(f'shard{i}', rnd.uniform(0.35, 0.7), rnd.uniform(0.06, 0.11), icem)
        shards.append(o)
        a0 = 2 * math.pi * i / 22
        rr = rnd.uniform(2.6, 3.8)
        zz = rnd.uniform(-0.8, 1.6)
        for f in range(T['charge'], T['impact'] + 3, 2):
            c = pos_at(f) + V((0, 0, 3.2 * S))
            if f < T['dive']:
                t = (f - T['charge']) / (T['dive'] - T['charge'])
                a = a0 + t * 7.0
                r = rr * S * (1.3 - 0.5 * t)
                p = c + V((math.cos(a) * r, math.sin(a) * r, zz * (1 - 0.5 * t)))
            else:
                t = (f - T['dive']) / (T['impact'] - T['dive'])
                start = pos_at(T['dive']) + V((0, 0, 3.2 * S)) + V((math.cos(a0 + 7) * rr * 0.8, math.sin(a0 + 7) * rr * 0.8, zz * 0.5)) * S
                p = start.lerp(OPP + V((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), rnd.uniform(0.2, 1.5))), min(1.0, t * 1.15))
            loc_keys(o, [(f, p)])
            o.rotation_euler = (f * 0.2 + i, f * 0.13, a0)
            o.keyframe_insert('rotation_euler', frame=f)
        scale_keys(o, [(0, 0.0), (T['charge'] + i // 2, 0.0), (T['charge'] + 6 + i // 2, 1.0), (T['impact'], 1.0), (T['impact'] + 3, 0.0)])
    point_light('charge_light', V((0, -2.5, 4.5)), '#9fe0ff',
                [(0, 0), (T['charge'], 0), (T['dive'] - 2, 9000), (T['dive'] + 2, 4000), (T['impact'], 0)], radius=1.0)

    # impact: ice spikes burst out of the ground, a shockwave and a snow blast
    for i in range(40):
        a = 2 * math.pi * i / 40 + rnd.uniform(-0.1, 0.1)
        rr = rnd.uniform(0.3, 3.2)
        L = rnd.uniform(0.9, 2.4) * (1.25 - rr / 4)
        o = crystal_obj(f'spike{i}', L, L * 0.08, icem)
        o.location = OPP + V((math.cos(a) * rr, math.sin(a) * rr, -0.1))
        tilt = 0.12 + 0.2 * rr / 3
        o.rotation_euler = (-math.sin(a) * tilt, math.cos(a) * tilt, a)
        d = int(rr * 2)
        scale_keys(o, [(0, 0.0), (T['impact'] + d, 0.0), (T['impact'] + d + 4, 1.12), (T['impact'] + d + 7, 1.0),
                       (T['hit'] - 4, 1.0), (T['hit'] + 6, 0.0)])
    frost = kit.mat_basic('frostdisc', '#e4f6ff', rough=0.25, coat=0.6, sss=0.4, sss_radius=(0.6, 0.8, 1.0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=0.02, location=OPP + V((0, 0, 0.07)))
    disc = bpy.context.active_object
    disc.data.materials.append(frost)
    scale_keys(disc, [(0, (0, 0, 1)), (T['impact'], (0, 0, 1)), (T['impact'] + 8, (4.2, 4.2, 1)), (T['hit'], (4.4, 4.4, 1)),
                      (T['hit'] + 10, (0, 0, 1))])
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.06, major_segments=96, location=OPP + V((0, 0, 0.25)))
    wave = bpy.context.active_object
    wave.data.materials.append(mat_glow('wavem', '#d6f4ff', 5))
    scale_keys(wave, [(0, 0.0), (T['impact'], 0.1), (T['impact'] + 14, (9.0, 9.0, 3.0)), (T['impact'] + 15, 0.0)])
    puffm = bpy.data.materials.new('puffm')
    puffm.use_nodes = True
    nt = puffm.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (1, 1, 1, 1)
    vol.inputs['Density'].default_value = 2.0
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3.0
    rp = nt.nodes.new('ShaderNodeMath')
    rp.operation = 'MULTIPLY'
    rp.inputs[1].default_value = 3.0
    nt.links.new(nz.outputs['Fac'], rp.inputs[0])
    nt.links.new(rp.outputs[0], vol.inputs['Density'])
    nt.links.new(vol.outputs['Volume'], nt.nodes['Material Output'].inputs['Volume'])
    for i in range(16):
        a = 2 * math.pi * i / 16
        o = sphere_obj(f'puff{i}', rnd.uniform(0.5, 0.9), puffm, OPP, seg=16)
        out = OPP + V((math.cos(a) * rnd.uniform(2.5, 4.5), math.sin(a) * rnd.uniform(2.5, 4.5), rnd.uniform(0.3, 1.6)))
        loc_keys(o, [(T['impact'], OPP + V((0, 0, 0.4))), (T['impact'] + 18, out)])
        scale_keys(o, [(0, 0.0), (T['impact'], 0.0), (T['impact'] + 4, 1.0), (T['impact'] + 16, 1.4), (T['impact'] + 26, 0.0)])
    point_light('impact_light', OPP + V((0, 1.5, 1.5)), '#bfeeff', [(0, 0), (T['impact'] - 1, 0), (T['impact'] + 1, 40000), (T['impact'] + 12, 0)], 1.0)

    # ---- 4. hit: red flash, loose feathers
    point_light('hit_light', V((0.5, -3.5, 3.5)), '#ff5040',
                [(0, 0), (T['hit'] - 1, 0), (T['hit'], 3500), (T['hit'] + 3, 0), (T['hit'] + 5, 2000), (T['hit'] + 9, 0)], 1.0)
    fm = kit.mat_feather('ffk_loose', rough=0.6, sheen=0.6)
    for i in range(12):
        mb = kit.MeshBuilder()
        vs, fs, cs, uvs = kit.feather_geo(0.22, 0.1, stops=[(0, ff.SNOW), (1, ff.FROST)], nl=5, nw=3)
        mb.add(vs, fs, cs, uvs)
        o = mb.build(f'loose{i}', fm)
        c = HOVER + V((0, 0, 2.8 * S))
        out = c + V((rnd.uniform(-2.5, 2.5), rnd.uniform(-1.5, 2.5), rnd.uniform(0.5, 2.2)))
        loc_keys(o, [(T['hit'], c), (T['hit'] + 12, out), (T['hit'] + 50, out + V((rnd.uniform(-0.5, 0.5), 0, -3.2)))])
        o.rotation_euler = (0, 0, 0)
        o.keyframe_insert('rotation_euler', frame=T['hit'])
        o.rotation_euler = (rnd.uniform(-6, 6), rnd.uniform(-6, 6), rnd.uniform(-6, 6))
        o.keyframe_insert('rotation_euler', frame=T['hit'] + 50)
        scale_keys(o, [(0, 0.0), (T['hit'] - 1, 0.0), (T['hit'], 1.0), (T['hit'] + 44, 1.0), (T['hit'] + 50, 0.0)])

    snowfall()
    camera_moves(pos_at)


def camera_moves(pos_at):
    sc = bpy.context.scene
    tgt = kit.empty('cam_target')
    cd = bpy.data.cameras.new('cam')
    cd.sensor_width = 36
    cam = bpy.data.objects.new('cam', cd)
    kit.link(cam)
    sc.camera = cam
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    cd.dof.use_dof = True
    cd.dof.focus_object = tgt
    cd.dof.aperture_fstop = 5.6
    # (frame, camera location, target, lens, cut): a cut holds the previous framing until this frame
    shots = [
        (0, (-7.5, -13.5, 2.0), (-2.5, -5.0, 2.2), 30, False),
        (T['open'], (-6.0, -12.5, 1.7), (0, -1.0, 2.2), 30, False),
        (T['land'], (-4.0, -10.0, 1.3), (0, 0, 3.4), 28, False),
        (T['idle'] + 10, (-3.0, -8.6, 1.4), (0, 0, 3.6), 30, False),
        (T['advance'] - 4, (-0.8, -9.4, 1.8), (0, 0, 3.7), 32, False),
        (T['charge'] - 6, (-0.4, -11.0, 1.9), (0, -2.2, 3.8), 32, False),
        (T['charge'], (-3.6, -11.5, 1.1), (0, -2.0, 4.6), 26, True),          # low hero angle for the wind-up
        (T['dive'] - 2, (-3.0, -11.0, 1.0), (0, -1.9, 6.2), 26, False),
        (T['dive'], (-15.5, -8.0, 2.4), (1.6, -5.6, 2.8), 28, True),         # wide side view: the dive streaks across
        (T['back'] + 4, (-16.5, -9.5, 3.0), (2.0, -6.4, 4.6), 22, False),     # wider: the bigger bird pulls up high
        (T['back'] + 8, (-3.4, -10.6, 1.4), (1.0, -3.4, 5.2), 26, True),      # back home, braced for the hit
        (T['back'] + 24, (-3.0, -9.8, 1.6), (0.3, -1.0, 4.0), 28, False),
        (T['hit'], (-2.4, -9.2, 1.8), (0, -0.2, 3.5), 32, False),
        (T['recover'], (-2.6, -9.0, 1.7), (0, 0, 3.5), 32, False),
        (T['end'], (-3.6, -8.4, 1.0), (0, 0, 3.8), 28, False),
    ]
    # the bird is S times its original size: pull the home shots back by the same factor.
    # The dive shots frame the opponent's side and stay put.
    wide = {T['dive'], T['back'] + 4}
    shots = [(f, loc, t, lens, cut) if f in wide or f < T['land'] else
             (f, tuple(v * S for v in loc), tuple(v * S for v in t), lens, cut) for f, loc, t, lens, cut in shots]
    prev = None
    for f, loc, t, lens, cut in shots:
        if cut and prev:
            _, ploc, pt, plens, _ = prev
            # hold the old framing up to the frame before the cut
            for o, path, v in ((cam, 'location', ploc), (tgt, 'location', pt)):
                setattr(o, path, v)
                o.keyframe_insert(path, frame=f - 1)
            cd.lens = plens
            cd.keyframe_insert('lens', frame=f - 1)
        cam.location = loc
        cam.keyframe_insert('location', frame=f)
        tgt.location = t
        tgt.keyframe_insert('location', frame=f)
        cd.lens = lens
        cd.keyframe_insert('lens', frame=f)
        prev = (f, loc, t, lens, cut)
    # make the cuts hard: constant interpolation into each cut frame
    cut_frames = {f for f, *_r, c in shots if c}
    for o in (cam, tgt, cd):
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                if int(round(k.co.x)) + 1 in cut_frames:
                    k.interpolation = 'CONSTANT'
    return cam
