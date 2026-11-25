"""Battle animation for the star fox line, one script for all three with a different attack each.

  blender -b --factory-startup -P v2/fox_anim.py -- <module> frames f1 f2 ...   contact sheet
  blender -b --factory-startup -P v2/fox_anim.py -- <module> video [w h samples] [first]

Beats (24 fps): Star Ball throw, pop out and land, a cry, idle, the attack, back home, taking a hit,
shaking it off. Attacks:
  twinkit  Quick Attack: crouch, dash in on a light streak, bump, flip back home.
  glimmvix Ice Shard: both tail stars charge and fire a volley of ice crystals.
  novalynx Starfall Pounce: a high leap that comes down like a falling star, a star-shaped shockwave,
           then a hop home with a gold Speed-up glow.
The opponent stands off screen at OPP, like in the Freezer Flock video.
"""
import importlib
import math
import os
import random
import sys
import time

import bpy
from mathutils import Euler, Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import render2  # noqa: E402
import render_line  # noqa: E402
import sv  # noqa: E402
from ffk_anim import (crystal_obj, kp, loc_keys, mat_glow, point_light, scale_keys, smooth,  # noqa: E402
                      sphere_obj, star_ball)

OUT = os.path.join(HERE, '..', 'renders')
FPS = 24
T = dict(throw=0, open=24, appear=26, land=46, idle=64, wind=120, strike=134, hit_t=150, home=188, hit=212,
         recover=232, end=276)
HEIGHT = {'twinkit': 1.75, 'glimmvix': 2.2, 'novalynx': 2.6}
rnd = random.Random(5)


def lerpv(a, b, t):
    return V(a).lerp(V(b), t)


def arc(a, b, h, t):
    return lerpv(a, b, t) + V((0, 0, h * 4 * t * (1 - t)))


# ------------------------------------------------------------------ poses
def gait(P, bones, phase, amp, side_lag=0.06):
    """Bounding run: front legs together, back legs together half a stride later."""
    for s, lag in (('L', 0.0), ('R', side_lag)):
        a = 2 * math.pi * (phase + lag)
        b = a + math.pi
        P['arm.' + s] = (amp * 0.55 * math.sin(a), 0, 0)
        P['fore.' + s] = (-amp * 0.9 * max(0.0, math.sin(a + math.pi / 2)), 0, 0)
        P['hand.' + s] = (amp * 0.35 * max(0.0, math.sin(a + math.pi / 2)), 0, 0)
        P['thigh.' + s] = (amp * 0.5 * math.sin(b), 0, 0)
        P['shin.' + s] = (amp * 0.7 * max(0.0, math.sin(b - math.pi / 2)), 0, 0)
        P['foot.' + s] = (-amp * 0.45 * max(0.0, math.sin(b - math.pi / 2)), 0, 0)
    P['chest'] = (0.08 * amp * math.sin(2 * math.pi * phase), 0, 0)
    P['hips'] = (-0.06 * amp * math.sin(2 * math.pi * phase), 0, 0)


def crouch(P, k):
    """Weight down and back, ready to spring."""
    for s in 'LR':
        P['arm.' + s] = (0.35 * k, 0, 0)
        P['fore.' + s] = (-0.55 * k, 0, 0)
        P['hand.' + s] = (0.25 * k, 0, 0)
        P['thigh.' + s] = (-0.45 * k, 0, 0)
        P['shin.' + s] = (0.7 * k, 0, 0)
        P['foot.' + s] = (-0.3 * k, 0, 0)
    P['head'] = (0.15 * k, 0, 0)


def tails(P, names, f, amp=0.2, speed=0.07, lift=0.0):
    for i, n in enumerate(names):
        k = int(n[4]) if n[4].isdigit() else 0
        sgn = -1 if n.endswith('.L') else 1
        side = 0.0 if '.' not in n else sgn * 0.05
        P[n] = (-lift * (0.5 if k == 0 else 0.25), 0, amp * (0.6 + 0.4 * k) * math.sin(speed * f - k * 0.7) + side)


# ------------------------------------------------------------------ effects
def star_mesh(name, R, mat, loc=(0, 0, 0), flat=False, depth=0.05):
    vs, fs = sv.star_geo(R, R * 0.47, depth)
    if flat:
        vs = [(x, z, y) for x, y, z in vs]          # lay it on the ground
        fs = [f[::-1] for f in fs]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    o.location = loc
    kit.link(o)
    return o


def burst(name, at, f0, n, color, reach, size=0.05, up=0.6):
    m = mat_glow(name + 'm', color, 14)
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.2, 0.2)
        d = V((math.cos(a), math.sin(a), rnd.uniform(0.2, up))).normalized() * reach * rnd.uniform(0.6, 1.1)
        o = star_mesh(f'{name}{i}', size * rnd.uniform(0.8, 1.4), m, at, depth=size * 0.4)
        o.rotation_euler = (math.pi / 2, rnd.uniform(0, 6), 0)
        loc_keys(o, [(f0, at), (f0 + 12, at + d), (f0 + 20, at + d * 1.15 + V((0, 0, -0.2)))])
        scale_keys(o, [(0, 0.0), (f0 - 1, 0.0), (f0, 1.0), (f0 + 12, 1.0), (f0 + 20, 0.0)])
        o.keyframe_insert('rotation_euler', frame=f0)
        o.rotation_euler.y += 4
        o.keyframe_insert('rotation_euler', frame=f0 + 20)


# ------------------------------------------------------------------ main
def animate(mod, rig, m):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, T['end']
    sc.render.fps = FPS
    H = HEIGHT[mod]
    k = H / 2.2
    arm, root = rig['arm'], rig['root']
    arm.scale = (1, 1, 1)                   # battle size: design scale, not the true height
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    tail_names = [b.name for b in arm.pose.bones if b.name.startswith('tail')]
    OPP = V((2.6, -6.2, 0.0)) * k
    HOME = V((0, 0, 0))
    yaw_opp = math.atan2(OPP.x, -OPP.y)

    # ---- Star Ball
    ball, top = star_ball()
    ball.scale = (k, k, k)
    p0, p1 = V((-3.4, -5.0, 0.6)) * k, V((0, -0.6, 0.55)) * k
    for f in range(T['throw'], T['open'] + 1, 2):
        t = (f - T['throw']) / (T['open'] - T['throw'])
        loc_keys(ball, [(f, arc(p0, p1, 1.6 * k, t))])
        ball.rotation_euler = (f * 0.5, 0, f * 0.2)
        ball.keyframe_insert('rotation_euler', frame=f)
    kp(top, 'rotation_euler', T['open'], Euler((0, 0, 0)))
    kp(top, 'rotation_euler', T['open'] + 5, Euler((math.radians(-110), 0, 0)))
    scale_keys(ball, [(T['open'] + 4, k), (T['open'] + 10, 0.0)])
    flash = sphere_obj('flash', 1.0, mat_glow('flashm', '#ffffff', 12, alpha=0.6), p1)
    scale_keys(flash, [(0, 0.0), (T['open'], 0.0), (T['open'] + 3, 0.45 * k), (T['open'] + 9, 0.0)])
    point_light('flash_light', p1 + V((0, -0.4, 0.4)), '#fff6e0', [(0, 0), (T['open'], 0), (T['open'] + 3, 4000 * k), (T['open'] + 14, 0)])
    burst('pop', p1 + V((0, 0, 0.2 * k)), T['open'] + 1, 12, '#fff2b0', 1.2 * k, 0.05 * k)

    # ---- per-frame root and pose
    eff = {}                                   # attack-specific values the effects need
    jump_h = 0.9 * H

    def root_at(f):
        """(location, (pitch, roll, yaw), scale) of the whole Pokemon at frame f."""
        loc, rot, scl = HOME.copy(), [0.0, 0.0, 0.0], V((1, 1, 1))
        # appear: grows out of the light, hops up and lands with a squash
        if f < T['appear']:
            return loc, rot, V((0, 0, 0))
        if f < T['land']:
            t = (f - T['appear']) / (T['land'] - T['appear'])
            g = min(1.0, t * 1.6)
            loc = V((0, -0.3 * k * (1 - t), 0.5 * H * 4 * t * (1 - t)))
            s = smooth(g) * (1 + 0.08 * math.sin(math.pi * t))
            return loc, rot, V((s, s, s))
        if f < T['land'] + 8:
            t = (f - T['land']) / 8
            sq = math.sin(math.pi * t) * 0.14
            return loc, rot, V((1 + sq * 0.5, 1 + sq * 0.5, 1 - sq))
        a = attack_root(f)
        if a:
            return a
        if T['hit'] <= f < T['recover']:
            t = (f - T['hit']) / (T['recover'] - T['hit'])
            back = math.sin(math.pi * min(1, t * 1.8)) * (1 - t * 0.3)
            loc = V((0, 0.35 * k * back, 0))
            rot = [-0.12 * back, 0.08 * math.sin(t * 20) * (1 - t), 0]
            sq = 0.1 * math.exp(-t * 4) * math.cos(t * 18)
            return loc, rot, V((1 + sq * 0.5, 1 + sq * 0.5, 1 - sq))
        if T['recover'] <= f < T['recover'] + 16:
            t = (f - T['recover']) / 16
            rot = [0, 0, 0.12 * math.sin(t * math.pi * 5) * (1 - t)]   # a full-body shake
        return loc, rot, scl

    def attack_root(f):
        if not (T['wind'] <= f < T['home']):
            return None
        if mod == 'twinkit':
            dash_end = T['strike'] + 8
            contact = OPP + V((-0.5, 0.9, 0)) * k
            if f < T['strike']:
                t = smooth((f - T['wind']) / (T['strike'] - T['wind']))
                return V((0, 0.12 * k * t, -0.04 * k * t)), [0, 0, yaw_opp * t], V((1 + 0.06 * t, 1 + 0.06 * t, 1 - 0.12 * t))
            if f < dash_end:
                t = (f - T['strike']) / (dash_end - T['strike'])
                return lerpv(HOME, contact, t * t * (3 - 2 * t) * 0.3 + t * 0.7), [-0.15, 0, yaw_opp], V((0.9, 1.25, 0.9))
            back_end = dash_end + 26
            if f < back_end:
                t = (f - dash_end) / (back_end - dash_end)
                p = arc(contact, HOME, jump_h * 0.75, smooth(t))
                yaw = yaw_opp * (1 - smooth(t))
                return p, [-2 * math.pi * smooth(min(1, t * 1.15)), 0, yaw], V((1, 1, 1))
            t = (f - back_end) / max(1, T['home'] - back_end)
            sq = 0.12 * math.sin(math.pi * min(1, t * 3))
            return HOME.copy(), [0, 0, 0], V((1 + sq * 0.5, 1 + sq * 0.5, 1 - sq))
        if mod == 'glimmvix':
            t = (f - T['wind']) / (T['home'] - T['wind'])
            yaw = yaw_opp * smooth(min(1, t * 4)) * (1 - smooth((t - 0.75) * 4))
            recoil = 0.0
            for i in range(eff.get('shots', 0)):
                df = f - (T['strike'] + i * 3)
                if 0 <= df < 6:
                    recoil = max(recoil, math.sin(math.pi * df / 6))
            return V((0, 0.06 * k * recoil, 0)), [0.05 * recoil, 0, yaw], V((1, 1, 1 - 0.04 * recoil))
        if mod == 'novalynx':
            land = OPP + V((-0.2, 0.7, 0)) * k
            apex_f = T['strike'] + 10
            hit_f = T['strike'] + 18
            if f < T['strike']:
                t = smooth((f - T['wind']) / (T['strike'] - T['wind']))
                return V((0, 0.2 * k * t, -0.08 * k * t)), [0.1 * t, 0, yaw_opp * t], V((1 + 0.05 * t, 1 + 0.05 * t, 1 - 0.14 * t))
            if f < hit_f:
                t = (f - T['strike']) / (hit_f - T['strike'])
                up = V((0, 0, 1.25 * H))
                if f < apex_f:
                    u = (f - T['strike']) / (apex_f - T['strike'])
                    p = lerpv(HOME, lerpv(HOME, land, 0.55) + up, 1 - (1 - u) ** 2)
                    pitch = -0.5 * u
                else:
                    u = (f - apex_f) / (hit_f - apex_f)
                    p = lerpv(lerpv(HOME, land, 0.55) + up, land, u * u)
                    pitch = -0.5 + 1.4 * u
                return p, [pitch, 0, yaw_opp], V((0.95, 1.12, 0.95))
            if f < hit_f + 6:
                t = (f - hit_f) / 6
                sq = 0.2 * math.sin(math.pi * t)
                return land, [0.25 * (1 - t), 0, yaw_opp], V((1 + sq * 0.5, 1 + sq * 0.5, 1 - sq))
            back0 = hit_f + 6
            back1 = back0 + 24
            if f < back1:
                t = (f - back0) / (back1 - back0)
                return arc(land, HOME, jump_h, smooth(t)), [-0.2 * math.sin(math.pi * t), 0, yaw_opp * (1 - smooth(t))], V((1, 1, 1))
            t = (f - back1) / max(1, T['home'] - back1)
            sq = 0.15 * math.sin(math.pi * min(1, t * 3))
            return HOME.copy(), [0, 0, 0], V((1 + sq * 0.5, 1 + sq * 0.5, 1 - sq))
        return None

    def pose_at(f):
        P = {}
        breath = math.sin(f * 0.2)
        P['chest'] = (0.02 * breath, 0, 0)
        P['head'] = (0.03 * math.sin(f * 0.11), 0.0, 0.18 * math.sin(f * 0.045))
        tails(P, tail_names, f)
        for s, sx in (('L', -1), ('R', 1)):
            tw = 1.0 if (f % 70) in range(sx * 9 + 40, sx * 9 + 44) else 0.0
            P['ear.' + s] = (-0.25 * tw, 0, 0)
        # cry after landing: head up, ears back, tail up
        if T['land'] + 4 <= f < T['idle']:
            t = math.sin(math.pi * (f - T['land'] - 4) / (T['idle'] - T['land'] - 4))
            P['head'] = (-0.45 * t, 0, 0)
            P['neck'] = (-0.2 * t, 0, 0)
            for s in 'LR':
                P['ear.' + s] = (0.35 * t, 0, 0)
            tails(P, tail_names, f, amp=0.35, speed=0.3, lift=0.4 * t)
        if T['appear'] <= f < T['land']:
            crouch(P, 0.4)
        # attack poses
        if T['wind'] <= f < T['home']:
            if mod == 'twinkit':
                if f < T['strike']:
                    crouch(P, smooth((f - T['wind']) / (T['strike'] - T['wind'])))
                elif f < T['strike'] + 8:
                    gait(P, None, (f - T['strike']) / 5, 1.2)
                    for s in 'LR':
                        P['ear.' + s] = (0.5, 0, 0)
                    tails(P, tail_names, f, amp=0.05, lift=-0.6)
                elif f < T['strike'] + 34:
                    crouch(P, 0.8)
                else:
                    crouch(P, 0.5 * (1 - smooth((f - T['strike'] - 34) / 10)))
            elif mod == 'glimmvix':
                t = (f - T['wind']) / (T['strike'] - T['wind'])
                lift = smooth(min(1, t)) * (1 - smooth((f - T['home'] + 14) / 14))
                crouch(P, 0.45 * lift)
                tails(P, tail_names, f, amp=0.08 + 0.15 * (f >= T['strike']), speed=0.5, lift=0.9 * lift)
                P['head'] = (0.12 * lift, 0, 0)
            elif mod == 'novalynx':
                if f < T['strike']:
                    crouch(P, 1.1 * smooth((f - T['wind']) / (T['strike'] - T['wind'])))
                elif f < T['strike'] + 18:
                    u = (f - T['strike']) / 18
                    # stretched out in the air: front legs reach, back legs trail
                    for s in 'LR':
                        P['arm.' + s] = (-0.7 + 0.5 * u, 0, 0)
                        P['fore.' + s] = (-0.2, 0, 0)
                        P['thigh.' + s] = (0.7, 0, 0)
                        P['shin.' + s] = (0.4, 0, 0)
                        P['ear.' + s] = (0.45, 0, 0)
                    tails(P, tail_names, f, amp=0.05, lift=-0.5)
                elif f < T['strike'] + 24:
                    crouch(P, 0.9)
                elif f < T['strike'] + 48:
                    gait(P, None, (f - T['strike'] - 24) / 12, 0.7)
                else:
                    crouch(P, 0.3 * (1 - smooth((f - T['strike'] - 48) / 6)))
        # taking a hit and shaking it off
        if T['hit'] <= f < T['recover']:
            t = (f - T['hit']) / (T['recover'] - T['hit'])
            b = math.sin(math.pi * min(1, t * 1.6))
            crouch(P, 0.6 * b)
            P['head'] = (0.3 * b, 0, -0.3 * b)
            for s in 'LR':
                P['ear.' + s] = (0.6 * b, 0, 0)
            tails(P, tail_names, f, amp=0.05, lift=-0.4 * b)
        if T['recover'] <= f < T['recover'] + 16:
            t = (f - T['recover']) / 16
            P['head'] = (0, 0, 0.45 * math.sin(t * math.pi * 6) * (1 - t))
        if f >= T['recover'] + 16:
            t = smooth((f - T['recover'] - 16) / 12)
            P['head'] = (-0.12 * t, 0, -0.2 * t + 0.1 * math.sin(f * 0.05))
            tails(P, tail_names, f, amp=0.25, speed=0.12, lift=0.25 * t)
        return P

    names = [pb.name for pb in arm.pose.bones]
    for f in range(T['end'] + 1):
        loc, rot, scl = root_at(f)
        root.location = loc
        root.rotation_euler = rot
        root.scale = scl
        for path in ('location', 'rotation_euler', 'scale'):
            root.keyframe_insert(path, frame=f)
        P = pose_at(f)
        for n in names:
            if n == 'root':
                continue
            arm.pose.bones[n].rotation_euler = P.get(n, (0, 0, 0))
            arm.pose.bones[n].keyframe_insert('rotation_euler', frame=f)

    # ---- attack effects
    if mod == 'twinkit':
        contact = OPP + V((-0.5, 0.9, 0)) * k
        streakm = mat_glow('streakm', '#ffe7a6', 4, alpha=0.22)
        d = (contact - HOME).normalized()
        for i in range(3):
            o = sphere_obj(f'streak{i}', 0.2 * k, streakm, (0, 0, 0), seg=16)
            o.rotation_euler = (0, 0, math.atan2(d.x, -d.y))
            for f in range(T['strike'], T['strike'] + 14):
                p, _, _ = root_at(min(f, T['strike'] + 8))
                loc_keys(o, [(f, p + d * (0.5 + 0.45 * i) * k + V((0, 0, (0.3 + 0.08 * i) * H)))])
            scale_keys(o, [(0, 0.0), (T['strike'] - 1, 0.0), (T['strike'] + 1, (0.7 - 0.15 * i, 3.2, 0.7 - 0.15 * i)),
                           (T['strike'] + 8, (0.6 - 0.15 * i, 3.6, 0.6 - 0.15 * i)), (T['strike'] + 13, 0.0)])
        hitp = contact + (contact - HOME).normalized() * 0.4 * k + V((0, 0, 0.5 * k))
        f0 = T['strike'] + 8
        fl = sphere_obj('bump', 1.0, mat_glow('bumpm', '#ffffff', 10, alpha=0.5), hitp)
        scale_keys(fl, [(0, 0.0), (f0 - 1, 0.0), (f0 + 2, 0.6 * k), (f0 + 8, 0.0)])
        point_light('bump_light', hitp + V((0, 0.6 * k, 0.3 * k)), '#fff2c8', [(0, 0), (f0 - 1, 0), (f0 + 1, 3000 * k), (f0 + 10, 0)])
        burst('bumpstar', hitp, f0, 10, '#ffd36a', 1.0 * k, 0.06 * k)
    elif mod == 'glimmvix':
        icem = kit.mat_ice('shardice', '#cdf3ff', emit=1.8)
        eff['shots'] = 8
        for i in range(8):
            f0 = T['strike'] + i * 3
            o = crystal_obj(f'shard{i}', 0.42, 0.075, icem)
            rl, rr_, rs = root_at(f0)
            src = rl + Euler(rr_).to_matrix() @ (V(m.TAIL['L' if i % 2 == 0 else 'R'][-1][:3]) + V((0, 0, 0.12)))
            dst = OPP + V((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(0.3, 1.0))) * k
            for j in range(0, 13):
                u = j / 12
                p = arc(src, dst, 0.9 * k, u)
                q = arc(src, dst, 0.9 * k, min(1, u + 0.05))
                d = (q - p).normalized()
                o.rotation_euler = V((0, 0, 1)).rotation_difference(d).to_euler()
                o.keyframe_insert('rotation_euler', frame=f0 + j)
                loc_keys(o, [(f0 + j, p)])
            scale_keys(o, [(0, 0.0), (f0 - 1, 0.0), (f0, 1.0), (f0 + 12, 1.0), (f0 + 13, 0.0)])
            burst(f'iceb{i}_', dst, f0 + 12, 6, '#dff6ff', 0.6 * k, 0.04 * k)
            point_light(f'icel{i}', dst + V((0, 0.4, 0.3)) * k, '#cdeeff', [(0, 0), (f0 + 11, 0), (f0 + 13, 1500 * k), (f0 + 20, 0)])
        # the tail stars brighten while charging
        sc.frame_set(T['idle'])              # rest position, so the glows can be pinned to the tail bones
        for s in m.SIDE:
            tip = V(m.TAIL[s][-1][:3]) + V((0, -0.06, 0.12))
            lt = point_light('charge.' + s, tip, '#ffc860', [(0, 0), (T['wind'], 0), (T['strike'], 900), (T['strike'] + 24, 900),
                                                       (T['home'] - 10, 0)])
            g = sphere_obj('chargeglow.' + s, 0.16, mat_glow('chargem', '#ffd36a', 6, alpha=0.35), tip)
            scale_keys(g, [(0, 0.0), (T['wind'], 0.0), (T['strike'], 1.0), (T['strike'] + 24, 1.3), (T['home'] - 10, 0.0)])
            bpy.context.view_layer.update()
            for o in (lt, g):
                kit.bind_rigid(o, arm, 'tail2.' + s)
    elif mod == 'novalynx':
        land = OPP + V((-0.2, 0.7, 0)) * k
        hit_f = T['strike'] + 18
        glowm = mat_glow('fallm', '#ffd36a', 3, alpha=0.12)
        aura = sphere_obj('fallaura', 1.0, glowm, (0, 0, 0))
        for f in range(T['strike'], hit_f + 2):
            p, _, _ = root_at(f)
            loc_keys(aura, [(f, p + V((0, 0, 0.55 * H)))])
        scale_keys(aura, [(0, 0.0)])                  # kept for the path keys; the light does the glowing
        trail = point_light('falllight', (0, 0, 0), '#ffcf70', [(0, 0), (T['strike'] + 4, 0), (T['strike'] + 10, 2500),
                                                              (hit_f, 4000), (hit_f + 6, 0)], 0.6)
        for f in range(T['strike'], hit_f + 6):
            p, _, _ = root_at(f)
            loc_keys(trail, [(f, p + V((0, 0, 0.6 * H)))])
        # sparkles left behind on the way down
        for i in range(14):
            f0 = T['strike'] + 6 + i // 1
            if f0 > hit_f:
                break
            p, _, _ = root_at(f0)
            burst(f'trail{i}_', p + V((0, 0, 0.5 * H)), f0, 3, '#ffe9a8', 0.35 * k, 0.05 * k, up=0.1)
        # star-shaped shockwave on the ground and a ring of light
        ring = star_mesh('shock', 1.0, mat_glow('shockm', '#ffd36a', 10, alpha=0.7), land + V((0, 0, 0.03)), flat=True, depth=0.01)
        scale_keys(ring, [(0, 0.0), (hit_f - 1, 0.0), (hit_f, 0.3 * k), (hit_f + 10, 2.6 * k), (hit_f + 16, 0.0)])
        ring.rotation_euler = (0, 0, 0)
        ring.keyframe_insert('rotation_euler', frame=hit_f)
        ring.rotation_euler = (0, 0, 0.6)
        ring.keyframe_insert('rotation_euler', frame=hit_f + 16)
        flash = sphere_obj('impact', 1.0, mat_glow('impactm', '#fff4d0', 10, alpha=0.45), land + V((0, 0, 0.3 * k)))
        scale_keys(flash, [(0, 0.0), (hit_f - 1, 0.0), (hit_f + 2, 0.7 * k), (hit_f + 8, 0.0)])
        point_light('impact_light', land + V((0, 0.8, 1.0)) * k, '#ffe2a0', [(0, 0), (hit_f - 1, 0), (hit_f + 1, 9000 * k),
                                                                             (hit_f + 14, 0)], 0.8)
        burst('impactstars', land + V((0, 0, 0.3 * k)), hit_f, 16, '#ffd36a', 2.2 * k, 0.08 * k)
        # Speed up: gold rings rise around it once it is home
        sp = T['strike'] + 50
        for i in range(3):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.7 * k, minor_radius=0.025 * k, major_segments=64,
                                             location=(0, 0.2 * k, 0.05))
            r = bpy.context.active_object
            r.name = f'speedring{i}'
            r.data.materials.append(mat_glow('speedm', '#ffd36a', 8, alpha=0.7))
            f0 = sp + i * 4
            loc_keys(r, [(f0, V((0, 0.2 * k, 0.05))), (f0 + 14, V((0, 0.2 * k, 1.3 * H)))])
            scale_keys(r, [(0, 0.0), (f0 - 1, 0.0), (f0, 1.0), (f0 + 10, 0.8), (f0 + 14, 0.0)])

    # ---- taking the hit: a white flash and sparks at the body
    hp = V((0.45, -0.75, 0.55 * H))
    fl = sphere_obj('hitflash', 1.0, mat_glow('hitm', '#ffffff', 12, alpha=0.5), hp)
    scale_keys(fl, [(0, 0.0), (T['hit'] - 1, 0.0), (T['hit'] + 1, 0.22 * k), (T['hit'] + 5, 0.0)])
    point_light('hit_light', hp + V((0.3, -0.8, 0.4)) * k, '#ffffff', [(0, 0), (T['hit'] - 1, 0), (T['hit'], 3500 * k), (T['hit'] + 8, 0)])
    burst('hitstars', hp, T['hit'], 10, '#ffffff', 0.9 * k, 0.04 * k)
    camera_moves(k, H, OPP, mod)


def camera_moves(k, H, OPP, mod):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('cam')
    cd.sensor_width = 36
    cam = bpy.data.objects.new('cam', cd)
    kit.link(cam)
    sc.camera = cam
    tgt = kit.empty('cam_target')
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    cd.dof.use_dof = True
    cd.dof.focus_object = tgt
    cd.dof.aperture_fstop = 5.6
    z = 0.45 * H
    wide = {'twinkit': ((-6.0, -6.6, 1.1), (1.2, -3.0, 0.55)), 'glimmvix': ((-5.6, -7.4, 1.3), (1.1, -3.2, 0.7)),
            'novalynx': ((-7.6, -7.6, 1.5), (1.3, -3.3, 2.0))}[mod]
    shots = [
        (0, (-3.4, -7.4, 0.8), (-1.0, -2.2, 0.6), 30, False),
        (T['open'], (-2.8, -7.0, 0.8), (0, -0.4, z / k), 30, False),
        (T['land'], (-2.4, -6.0, 0.75), (0, 0, z / k), 32, False),
        (T['idle'] + 20, (-1.9, -5.0, 0.75), (0, 0, z / k), 34, False),
        (T['wind'] - 4, (-1.4, -4.6, 0.6), (0, 0, z / k), 34, False),
        (T['wind'] + 4, wide[0], wide[1], 22 if mod == 'novalynx' else 26, True),
        (T['home'] - 6, (wide[0][0] + 0.4, wide[0][1] + 0.3, wide[0][2]), (wide[1][0] - 0.4, wide[1][1] + 0.6, wide[1][2]), 22 if mod == 'novalynx' else 26, False),
        (T['home'], (-2.2, -5.6, 0.8), (0, 0, z / k), 32, True),
        (T['hit'], (-1.8, -4.8, 0.8), (0, 0, z / k), 34, False),
        (T['recover'] + 10, (-2.0, -5.2, 0.8), (0, 0, z / k), 34, False),
        (T['end'], (-2.6, -6.0, 0.6), (0, 0, z / k + 0.05), 32, False),
    ]
    prev = None
    for f, loc, t, lens, cut in shots:
        loc = V(loc) * k
        t = V(t) * k
        if cut and prev:
            _, ploc, pt, plens = prev
            cam.location = ploc
            cam.keyframe_insert('location', frame=f - 1)
            tgt.location = pt
            tgt.keyframe_insert('location', frame=f - 1)
            cd.lens = plens
            cd.keyframe_insert('lens', frame=f - 1)
        cam.location = loc
        cam.keyframe_insert('location', frame=f)
        tgt.location = t
        tgt.keyframe_insert('location', frame=f)
        cd.lens = lens
        cd.keyframe_insert('lens', frame=f)
        prev = (f, loc, t, lens)
    cut_frames = {f for f, *_r, cut in shots if cut}
    for o in (cam, tgt, cd):
        for fc in o.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                if int(round(kf.co.x)) + 1 in cut_frames:
                    kf.interpolation = 'CONSTANT'


def setup(mod):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kit._M.clear()
    m = importlib.import_module(mod)
    rig = m.build()
    render_line.dusk_sky()
    render_line.meadow()
    animate(mod, rig, m)
    return m, rig


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    mod, mode = args[0], args[1]
    t0 = time.time()
    setup(mod)
    sc = bpy.context.scene
    print('BUILD seconds', round(time.time() - t0))
    if mode == 'frames':
        render2.settings(10, 480, 270)
        fr = [int(a) for a in args[2:]]
        paths = []
        for f in fr:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(OUT, f'_fx_{mod}_{f:03d}.png')
            bpy.ops.render.render(write_still=True)
            paths.append(sc.render.filepath)
        import subprocess
        cols = 4
        rows = (len(paths) + cols - 1) // cols
        inputs = []
        for p in paths:
            inputs += ['-i', p]
        filt = ''.join(f'[{i}]' for i in range(len(paths))) + f'xstack=inputs={len(paths)}:layout=' + '|'.join(
            f'{(i % cols) * 480}_{(i // cols) * 270}' for i in range(len(paths)))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y'] + inputs + ['-filter_complex', filt,
                        os.path.join(OUT, f'_fx_{mod}.png')])
        print('SHEET', rows, cols)
    else:
        w, h, s = (int(a) for a in (args[2:5] if len(args) >= 5 else (960, 540, 12)))
        render2.settings(s, w, h)
        d = os.path.join(OUT, f'{mod}_frames')
        os.makedirs(d, exist_ok=True)
        sc.frame_start = int(args[5]) if len(args) > 5 else 0
        sc.render.filepath = os.path.join(d, 'f_')
        sc.render.image_settings.file_format = 'PNG'
        sc.render.use_overwrite = False
        bpy.ops.render.render(animation=True)
        print('VIDEO DONE', round(time.time() - t0))


if __name__ == '__main__':
    main()
