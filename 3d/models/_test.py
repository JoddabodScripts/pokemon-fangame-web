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
