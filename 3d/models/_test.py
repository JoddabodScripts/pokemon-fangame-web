import math

def build(lib):
    rig = lib.Rig('Test', '_test', 'Fire', height_cm=100, gait='walk', attack='cast')
    m = lib.mat('t_body', '#f07a2a', 0.5)
    rig.body = lib.pivot('t_bodyp', (0, 0, 0.45), rig.root)
    lib.sphere('t_body', (0, 0, 0.1), (0.35, 0.3, 0.38), m, rig.body)
    rig.head = lib.pivot('t_headp', (0, -0.05, 0.5), rig.body)
    lib.sphere('t_head', (0, 0, 0.15), 0.25, m, rig.head)
    lib.eye('t_eyeL', (-0.1, -0.2, 0.2), 0.06, rig.head)
    lib.eye('t_eyeR', (0.1, -0.2, 0.2), 0.06, rig.head)
    for i, x in enumerate((-0.15, 0.15)):
        leg = lib.pivot(f't_leg{i}', (x, 0, 0.05), rig.body)
        lib.tube(f't_legm{i}', [(0, 0, 0), (0, 0, -0.25), (0, -0.05, -0.48)], [0.08, 0.07, 0.06], m, leg)
        rig.legs.append((leg, i * 0.5))
    rig.attack_origin = (0, -0.4, 0.9)
    return rig


def animate(A):
    """Example of a custom animation (see MODELING_BRIEF.md)."""
    import math
    r, T, s = A.rig, A.T, A.size
    A.key(r.root, 0, scale=0.001); A.key(r.root, T['OUT'], scale=0.001)
    A.key(r.root, T['OUT'] + 8, scale=1.1); A.key(r.root, T['OUT'] + 12, scale=1.0)
    A.key(r.root, T['WALK'], loc=(0, 0, 0), rot=(0, 0, 0))
    A.key(r.root, T['WALK'] + 6, rot=(0, 0, math.pi / 2))
    A.key(r.root, T['WALK_END'] - 6, loc=(1.5 * s, 0, 0), rot=(0, 0, math.pi / 2))
    A.key(r.root, T['WALK_END'], rot=(0, 0, 0))
    for f in A.frames(T['WALK'], T['WALK_END'], 2):
        for leg, ph in r.legs:
            A.key(leg, f, rot=(A.wave(f, 12, ph) * 0.5, 0, 0))
    here = A.world(r.root, T['ATTACK'], (0, -0.4, 0.9))
    ball = A.lib.pivot('t_fx')
    A.lib.sphere('t_fxm', (0, 0, 0), 0.1 * s, A.lib.mat('t_fx', '#ff6a00', emit=3), ball)
    A.key(ball, 0, loc=here, scale=0.001, absolute=True); A.key(ball, T['ATTACK'] + 10, loc=here, scale=0.001, absolute=True)
    A.key(ball, T['ATTACK'] + 11, loc=here, scale=1, absolute=True)
    A.key(ball, T['ATTACK'] + 24, loc=A.opponent(here), scale=1.5, absolute=True)
    A.key(ball, T['ATTACK'] + 26, loc=A.opponent(here), scale=0.001, absolute=True)
