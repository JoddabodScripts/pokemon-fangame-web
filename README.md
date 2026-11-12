# Star Region: Freeze and Flame

A Pokemon fan game prototype that runs in the browser. You walk around the star-shaped Star Region, meet the Pokemon from our notebook in tall grass, battle them and catch them.

There are two versions, Freeze and Flame. Right now the only difference is the legendary in the shrine south of Star City, and both legendaries are "???" stand-ins until someone designs them.

## How to play

Open `index.html` in a browser. There's no build step and nothing to install.

| Key | Does |
| --- | --- |
| Arrows or WASD | Move |
| Z, Space or Enter | A (talk, confirm) |
| X or Backspace | B (back). Hold it to run |
| Esc or M | Menu |
| ` or F2 | Debug panel |

On a phone you get on-screen buttons instead.

The game saves to your browser when you heal at a Pokemon Center, when you pick SAVE in the menu, and after every battle. Each version has its own save.

## What's in it

- 12 Pokemon from the notebook (001 to 012) and the 2 placeholder legendaries.
- Six areas: Star City in the middle and a route plus town on each point of the star. Each route has different wild Pokemon and levels.
- Battles with type matchups, catching, potions, switching, EXP, level ups, new moves and evolution.
- Signature moves. Flames of Health (Blazian) and Slime Split (Slimontoon) work the way the notebook describes them. Bog Chomp (Swampest) and Fierce Blast (Fiercebird) are made up for now.
- Unique Forms, the notebook's featured element. About 1 in 64 wild Pokemon is a Unique Form: different colors, 20% higher stats and a star next to its name.
- Pokedex with base stats, totals and signature move text. Press A on an entry's stats page to read its lore.

## Debug panel

Press ` or F2, or click DBG in the corner. You can also add `?debug` to the URL to open it on load. It has:

- Walk through walls and fast walk.
- A minimap you can click to teleport, plus buttons for every town and the shrine.
- Encounter rate slider, no encounters, and an "always Unique Form" switch.
- Fight any Pokemon at any level, or add it straight to your party.
- One-hit KOs, take no damage, 100% catch, 10x EXP and instant text.
- Win the current battle, heal the party, level up or evolve your lead Pokemon, fill your bag, reset the legendary.
- An info overlay (FPS, tile coordinates, zone) and a zone color overlay.
- Save, back to title, and delete save.

## Changing things

Almost everything lives in `js/data.js`:

- Pokemon names, types, base stats, evolution levels, catch rates and move lists are in the `S(...)` lines.
- Pokedex lore is the `lore` text on each Pokemon, and `height` is in cm.
- Moves are in `MOVES`. Signature moves have `sig: true` and a `desc`.
- Type matchups are in `CHART`.

Wild Pokemon per route and the town names are at the top of `js/map.js`. The sprites are drawn with code in `js/sprites.js`, one function per Pokemon.

## Things to check with the designers

These came from blurry photos, so some may be wrong:

- Names: 008 Slimarton, 009 Slimontoon and 012 Fiercebird are my best reading. 010 Peeplet and 011 Featherdash are made up.
- Stats for 002 Swamporiaer and all three birds were hard to read. The birds' stats are partly guesses.
- 005 Flamezion's stats add up to 485 but the page says 475. 007 Slimean's add up to 350 but the page says 370.
- Signature moves for Swampest and Fiercebird.
- Town names are placeholders.
- The robot with the hammer and the bee swarm aren't in yet because they don't have numbers or stats.

## Files

```
index.html      page + touch buttons
style.css       layout and debug panel styles
js/data.js      Pokemon, moves, types, stat formulas
js/sprites.js   pixel art for Pokemon, tiles, buildings and the player
js/map.js       builds the star map, towns, routes and wild encounter tables
js/battle.js    battle system
js/debug.js     debug panel and overlays
js/main.js      input, menus, overworld, save/load, title screen
```
