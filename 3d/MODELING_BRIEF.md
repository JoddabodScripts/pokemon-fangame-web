# Modeling brief: Star Region Pokemon in Blender

You are building 3D prototype models of the Pokemon from our fan game. Each model is a Python file that builds the creature in Blender from primitives. The rendering, lighting, T-pose shot and battle animation are already written. Your job is the model only, and the model is what everyone will judge, so make it look good.

## Setup that already exists

- Blender: `/opt/blender-dl/blender-4.2.23-linux-x64/blender`
- Toolkit: `3d/lib.py`. Read it first. Do not edit `lib.py` or `render.py`. If you need a helper, define it inside your model file.
- A working example: `3d/models/_test.py` (a plain blob, only there to show the structure).
- The 2D pixel art for every Pokemon is the `DRAW` object in `js/sprites.js`. Lore, types, heights and stats are in `js/data.js`. Use both for colors and features.

## What to deliver per Pokemon

`3d/models/<key>.py` with `def build(lib): ... return rig`.

Check your work with the preview sheet (4 views: front 3/4, side, back, top):

```
cd 3d && /opt/blender-dl/blender-4.2.23-linux-x64/blender -b --factory-startup -P render.py -- <key> preview
```

It writes `3d/renders/preview_<key>.png`. Open it with your Read tool to look at it. Budget: about 3 previews per model. Fix what looks wrong, then move on. Don't render videos or T-pose shots; I render those afterwards.

## Conventions (the animation depends on these)

- Meters, Z up. The creature stands on z = 0, centered on the origin, and **faces -Y**.
- Build at display size: roughly 1.0 to 2.0 m tall or long, whatever its real height. Put the real height in `height_cm`.
- Every moving part hangs off a `lib.pivot` placed exactly at its joint (hip, shoulder, neck, tail base, wing root, jaw hinge). The animation only rotates, moves and scales pivots.
- Fill in the rig:
  - `rig.body`: torso pivot. Everything else should hang off it, directly or indirectly.
  - `rig.head`: head pivot at the neck.
  - `rig.jaw`: lower jaw pivot at the hinge, if the mouth opens. Rotating it +X must open the mouth.
  - `rig.legs`: `(pivot, phase)` with phases 0 and 0.5 for opposite legs. Swinging is rotation around local X.
  - `rig.arms`: same as legs.
  - `rig.wings`: `(pivot, side)`, with side -1 for the left (x < 0) and +1 for the right. Flapping is rotation around local Y.
  - `rig.tail`: a chain of pivots, base first, each one parented to the previous. They sway around local Z.
  - `rig.extras`: `(pivot, 'flicker' | 'spin' | 'sway' | 'pulse')` for flames, petals, glows and similar.
  - `rig.attack_origin`: where projectiles start (mouth or hands), in root space.
  - `rig.t_pose`: `{pivot_name: (rx, ry, rz)}` to spread the limbs, wings and tail for the T-pose shot. Absolute rotations in radians. For example, arms straight out to the sides, wings fully open, a curled tail held out.
- `gait`: `walk`, `hop`, `float` or `fly`. `attack`: `bite`, `slam`, `peck` or `cast`. The first value of `Rig(...)` is the display name.
- Name every object with a prefix unique to your Pokemon (for example `swi_`) so names never collide.

## Quality bar

Think of the 3D Pokemon in the modern games: smooth, appealing, readable shapes with a clear silhouette from every angle.

- Smooth forms: use subsurf, tubes for limbs and tails, and `extrude_shape` or `from_verts` for flames, leaves, feathers, teeth, petals, crests and scarves. Blocky primitives stuck together is not the goal.
- Parts must connect. No floating gaps, no limbs poking out the far side of the body, feet touching the ground.
- Faces sell the character. Use big, expressive eyes (`lib.eye`), placed and angled well, plus brows, mouths, teeth, cheeks and markings as the design needs.
- Give materials some life: a slight `coat` for shine, `sss` for slime and skin, emission for flames, glows and ice crystals. Use the colors from the pixel art.
- Keep it light enough to render: subsurf level 1 or 2, no huge vertex counts.

## The Pokemon

The keys match `js/data.js`.

| key | what it is |
| --- | --- |
| `swampidile` | Grass. A long, low lizard-centipede. Segmented green body (each segment a rounded bump) with a cream belly stripe and about 6 pairs of short legs. A curled tail at the back. A small lizard head with a cute face. A sprout with two veined leaves growing from its head. Gait `walk` with the legs' phases staggered down the body. Attack `cast` (leaves). |
| `swamporiaer` | Grass, 150 cm. A crocodile with a long snout and a closed mouth of interlocking white teeth. Yellow slit-pupil eyes sitting on brow bumps. Spiky ridges down the back, a cream striped belly and a yellow sun-shaped spot on its side. 4 legs with small white claws. The tail curls up and over. `walk`, `bite`. |
| `swampest` | Grass. A big croc with its jaws wide open: rows of white teeth, a dark red mouth, a pink tongue. An angry slit eye. Back spikes and moss hanging from its belly. 4 thick clawed legs. Its tail rises into a tall, thick neck-like curve topped with a pink five-petal flower and two leaves. `walk`, `bite` (its signature move is Bog Chomp). |
| `flamber` | Fire. A small egg-shaped flame creature. One big eye with an amber iris in the middle of its face. A layered flame (red, orange, yellow) on top, stubby little flame arms, tiny feet and a small smile. Embers. `hop` or `walk`, `cast`. |
| `flamezion` | Fire. A round flame body with a crown of five layered flame spikes, flame wisps out of its sides and a flickering flame base instead of feet. Big shiny eyes, rosy cheeks and a wide grin with two fangs. `float`, `cast`. |
| `blazian` | Fire, 200 cm. A humanoid sun spirit. A ring of flame spikes all around a glowing yellow face, like the sun. Dark fiery eyes, flame-shaped cheek marks and a fanged grin. An orange body with a sun emblem on the chest. Arms that end in fireballs instead of hands, and legs with flames for feet. `walk` on two legs with arms, `cast` (its signature move is Flames of Health). The T-pose is arms straight out. |
| `slimean` | Water, 40 cm. A round, glossy blue slime (`sss`, `coat`) with a lighter concentric ring inside it, shiny eyes, a smile and pink cheeks. A small puddle and drips at its base. `hop`, `slam`. |
| `slimarton` | Water, 130 cm. A slime core with a face and five beaded arms like a starfish, with the beads alternating two blues. Use `arms` or `extras` for the beaded arms. `hop`, `slam`. |
| `slimontoon` | Water, 600 cm. A large slime core with a glowing center, stern brows and eight long beaded arms. `float` or `hop`, `slam` (its signature move is Slime Split). |
| `peeplet` | Flying, 15 cm. A tiny brown songbird: head tuft, cream belly, darker wings and tail, orange two-tone beak, rosy cheek, little orange legs. `walk` (it hops on two legs) with folded wings that can flap, `peck`. |
| `featherdash` | Ice/Flying, 120 cm. A long-legged running bird, halfway to snowy. Brown body with a frosty white cap, snow patches on its back and a long tail with three ice-blue eye spots. A red scarf around its neck with one end blowing back. Its eye is a normal dark eye with a faint snowflake hint. `walk` (it runs better than it flies), `peck`. |
| `fiercebird` | Ice/Flying, 550 cm. A huge, fully snowy eagle. Big spiky pale-blue wings with ice crystals on them, a white body, a necklace of ice beads and a red scarf with one end hanging down. A hooked yellow beak, a snowflake-patterned eye under an angry brow, a frosty crest and yellow talons. `fly`, `cast` (its signature move is Brittle Blast, a freezing dive). In the T-pose its wings are fully spread. |

The 2D pixel art in `js/sprites.js` is the agreed look for all of these, so match it. Where the pixel art is vague about a detail, use your judgment to make it look like a real Pokemon.
