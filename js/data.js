'use strict';
// All Pokemon, moves and type data. Edit this file to fix names, stats and moves.
(function () {
  const TYPE_COLORS = {
    Normal: '#a8a77a', Grass: '#5fbd58', Fire: '#ee7f30',
    Water: '#4f8fe6', Flying: '#8fa8ee', Ice: '#6fd0d0',
  };

  // attacking type -> defending type -> multiplier (missing = 1)
  const CHART = {
    Normal: {},
    Fire: { Grass: 2, Ice: 2, Fire: 0.5, Water: 0.5 },
    Water: { Fire: 2, Water: 0.5, Grass: 0.5 },
    Grass: { Water: 2, Fire: 0.5, Grass: 0.5, Flying: 0.5 },
    Flying: { Grass: 2 },
    Ice: { Grass: 2, Flying: 2, Fire: 0.5, Water: 0.5, Ice: 0.5 },
  };

  function typeMult(atkType, defTypes) {
    let m = 1;
    for (const t of defTypes) {
      const v = (CHART[atkType] || {})[t];
      if (v !== undefined) m *= v;
    }
    return m;
  }

  // cat: phys | spec | status
  // effect: { target: 'foe'|'self', stat, stages, chance }
  const MOVES = {
    tackle:      { name: 'Tackle',       type: 'Normal', cat: 'phys', power: 40, acc: 100 },
    scratch:     { name: 'Scratch',      type: 'Normal', cat: 'phys', power: 40, acc: 100 },
    quickattack: { name: 'Quick Attack', type: 'Normal', cat: 'phys', power: 40, acc: 100, priority: 1 },
    growl:       { name: 'Growl',        type: 'Normal', cat: 'status', acc: 100, effect: { target: 'foe', stat: 'atk', stages: -1 } },
    leer:        { name: 'Leer',         type: 'Normal', cat: 'status', acc: 100, effect: { target: 'foe', stat: 'def', stages: -1 } },

    vinewhip:    { name: 'Vine Whip',    type: 'Grass', cat: 'phys', power: 45, acc: 100 },
    razorleaf:   { name: 'Razor Leaf',   type: 'Grass', cat: 'phys', power: 55, acc: 95 },
    gigadrain:   { name: 'Giga Drain',   type: 'Grass', cat: 'spec', power: 70, acc: 100, drain: 0.5 },
    bogchomp:    { name: 'Bog Chomp',    type: 'Grass', cat: 'phys', power: 90, acc: 95, sig: true,
                   effect: { target: 'foe', stat: 'spe', stages: -1, chance: 100 },
                   desc: 'A crushing bite from muddy jaws. 90 power, 95 accuracy. Lowers the target\'s Speed.' },

    ember:       { name: 'Ember',        type: 'Fire', cat: 'spec', power: 40, acc: 100 },
    flamewheel:  { name: 'Flame Wheel',  type: 'Fire', cat: 'phys', power: 60, acc: 100 },
    flamethrower:{ name: 'Flamethrower', type: 'Fire', cat: 'spec', power: 90, acc: 100 },
    fireblast:   { name: 'Fire Blast',   type: 'Fire', cat: 'spec', power: 110, acc: 85 },
    flamesofhealth: { name: 'Flames of Health', type: 'Fire', cat: 'spec', power: 60, acc: 100, sig: true,
                   drain: 0.5, overheal: true,
                   desc: '60 damage, 100 accuracy. Heals 1/2 of the damage done and ignores the HP cap.' },

    bubble:      { name: 'Bubble',       type: 'Water', cat: 'spec', power: 40, acc: 100 },
    slimeshot:   { name: 'Slime Shot',   type: 'Water', cat: 'phys', power: 65, acc: 100 },
    slimeslam:   { name: 'Slime Slam',   type: 'Water', cat: 'phys', power: 90, acc: 90 },
    surf:        { name: 'Surf',         type: 'Water', cat: 'spec', power: 90, acc: 100 },
    slimesplit:  { name: 'Slime Split',  type: 'Water', cat: 'status', sig: true, effect: { split: true },
                   desc: 'Splits into 2 Pokemon with half stats. They gain 1/4 of their stats back every turn until complete. Both halves use the same move.' },

    peck:        { name: 'Peck',         type: 'Flying', cat: 'phys', power: 35, acc: 100 },
    gust:        { name: 'Gust',         type: 'Flying', cat: 'spec', power: 40, acc: 100 },
    wingattack:  { name: 'Wing Attack',  type: 'Flying', cat: 'phys', power: 60, acc: 100 },
    fierceblast: { name: 'Fierce Blast', type: 'Flying', cat: 'phys', power: 100, acc: 90, sig: true,
                   desc: 'A dive so fast the air bursts around it. 100 power, 90 accuracy.' },

    icebeam:     { name: 'Ice Beam',     type: 'Ice', cat: 'spec', power: 90, acc: 100 },
    blizzard:    { name: 'Blizzard',     type: 'Ice', cat: 'spec', power: 110, acc: 70 },
  };

  const SPECIES = {};
  const ORDER = [];
  // base = [hp, atk, def, spa, spd, spe]
  function S(key, num, name, types, base, o) {
    const [hp, atk, def, spa, spd, spe] = base;
    SPECIES[key] = {
      key, num, name, types,
      base: { hp, atk, def, spa, spd, spe },
      evo: o.evo || null,          // [intoKey, level]
      rate: o.rate || 45,          // catch rate, 3 (hard) to 255 (easy)
      xp: o.xp || 60,              // base EXP yield
      learn: o.learn || [],        // [level, moveKey]
      sig: o.sig || null,
      lore: o.lore || '',
      height: o.height || null,    // in cm, only where the notebook gives one
      legendary: !!o.legendary,
      version: o.version || null,
      look: o.look || '',
    };
    ORDER.push(key);
  }

  // Designer notes (not shown in game). Stats were read from blurry notebook photos:
  // - Swamporiaer and the three birds were hard to read; bird stats are partly guesses.
  // - Flamezion adds to 485, page says 475. Slimean adds to 350, page says 370.
  // - Peeplet and Featherdash names are placeholders. Fiercebird is a best reading.
  // - Bog Chomp and Fierce Blast are placeholder signature moves.
  // - Both legendaries are stand-ins until they get designed.

  // Grass starter line
  const swampLearn = [[1, 'tackle'], [1, 'growl'], [5, 'vinewhip'], [9, 'leer'], [13, 'razorleaf'], [20, 'gigadrain']];
  S('swampidile', 1, 'Swampidile', ['Grass'], [50, 50, 100, 50, 50, 80],
    { evo: ['swamporiaer', 16], rate: 45, xp: 64, learn: swampLearn,
      lore: 'It lives in the warm mud along Star Region riverbanks. The sprout on its head drinks in sunlight, so it can lie still for a whole day without eating. When something scares it, it curls up its tail and pretends to be a twig.' });
  S('swamporiaer', 2, 'Swamporiaer', ['Grass'], [120, 90, 125, 50, 50, 50],
    { evo: ['swampest', 32], rate: 45, xp: 142, learn: swampLearn,
      lore: 'It waits in shallow swamp water with only its eyes and the yellow spot on its cheek showing. Fish think the spot is a floating seed and swim right up to it. Its jaws can snap a fallen log in half.' });
  S('swampest', 3, 'Swampest', ['Grass'], [130, 95, 140, 85, 80, 30],
    { rate: 45, xp: 236, learn: [...swampLearn, [36, 'bogchomp']], sig: 'bogchomp',
      lore: 'The flower on its tail only opens when it is calm. People in Mossmire say that if the flower snaps shut, you should walk away slowly. One bite from its mud-soaked jaws leaves legs too heavy to run.' });

  // Fire starter line
  const flameLearn = [[1, 'scratch'], [1, 'growl'], [5, 'ember'], [9, 'quickattack'], [13, 'flamewheel'], [24, 'flamethrower']];
  S('flamber', 4, 'Flamber', ['Fire'], [40, 10, 40, 130, 40, 110],
    { evo: ['flamezion', 16], rate: 45, xp: 62, learn: flameLearn,
      lore: 'Its one big eye sees heat instead of light, so it can find a warm rock to sleep on even in total darkness. The flame on its head flickers faster when it is happy. It sulks for days if it gets rained on.' });
  S('flamezion', 5, 'Flamezion', ['Fire'], [60, 20, 55, 160, 55, 125],
    { evo: ['blazian', 32], rate: 45, xp: 142, learn: flameLearn,
      lore: 'The flames on its head form a crown that grows a little taller every time it wins a battle. Wild Flamber around Ember Point follow the Flamezion with the biggest crown and copy everything it does.' });
  S('blazian', 6, 'Blazian', ['Fire'], [80, 40, 60, 200, 60, 130],
    { rate: 45, xp: 240, learn: [...flameLearn, [36, 'flamesofhealth']], sig: 'flamesofhealth', height: 200,
      lore: 'The sun on its chest soaks up heat from every hit it lands, and Blazian turns that heat into healing. It has been seen walking into forest fires and walking out again with the fire gone and the trees still standing.' });

  // Water starter line
  const slimeLearn = [[1, 'tackle'], [1, 'growl'], [5, 'bubble'], [9, 'leer'], [12, 'slimeshot'], [24, 'slimeslam']];
  S('slimean', 7, 'Slimean', ['Water'], [60, 70, 65, 30, 65, 60],
    { evo: ['slimarton', 16], rate: 45, xp: 63, learn: slimeLearn, height: 40,
      lore: 'It bounces along the beach soaking up seawater to stay round and squishy. If it dries out it shrinks to the size of a pebble. Kids in Tidepool Town use sleeping Slimean as pillows, and the Slimean do not seem to mind.' });
  S('slimarton', 8, 'Slimarton', ['Water'], [80, 100, 70, 70, 70, 40],
    { evo: ['slimontoon', 32], rate: 45, xp: 142, learn: slimeLearn, height: 130,
      lore: 'Its five beaded arms grip rocks so tightly that storm waves cannot pull it loose. Every bead holds a ball of sticky slime. When it gets angry it flicks the beads off one at a time, and they grow back by morning.' });
  S('slimontoon', 9, 'Slimontoon', ['Water'], [100, 115, 100, 50, 100, 70],
    { rate: 45, xp: 239, learn: [...slimeLearn, [36, 'slimesplit']], sig: 'slimesplit', height: 600,
      lore: 'At 600cm across it is the biggest Pokemon ever recorded in the Star Region. When it is hurt it pulls itself in two, and both halves keep fighting while they grow back. Sailors have watched the two halves swim apart and move in perfect time, as if they still share one mind.' });

  // Bird line
  const birdLearn = [[1, 'peck'], [1, 'growl'], [5, 'gust'], [9, 'quickattack'], [15, 'wingattack']];
  S('peeplet', 10, 'Peeplet', ['Normal', 'Flying'], [40, 60, 25, 35, 30, 40],
    { evo: ['featherdash', 14], rate: 255, xp: 50, learn: birdLearn,
      lore: 'You can find it almost anywhere in the Star Fields. Flocks of Peeplet start chirping the second the sun comes up, which is why nobody in Star City has ever needed an alarm clock.' });
  S('featherdash', 11, 'Featherdash', ['Normal', 'Flying'], [60, 70, 55, 60, 55, 110],
    { evo: ['fiercebird', 30], rate: 120, xp: 122, learn: birdLearn,
      lore: 'The eye shapes on its tail feathers scare off Pokemon much bigger than it. It runs faster than it flies. Featherdash love to race trainers down the routes, and they sulk when they lose.' });
  S('fiercebird', 12, 'Fiercebird', ['Flying'], [100, 110, 90, 70, 80, 90],
    { rate: 45, xp: 216, learn: [...birdLearn, [34, 'fierceblast']], sig: 'fierceblast',
      lore: 'It nests on the highest cliffs above Galecrest. Each bead on its necklace is a stone it took from a rival it beat. When it dives, it moves so fast that the air bursts behind it with a bang you can hear across the whole route.' });

  // Version legendaries
  S('legend_freeze', 'L', '???', ['Ice'], [100, 90, 100, 130, 110, 100],
    { legendary: true, version: 'freeze', rate: 3, xp: 300,
      learn: [[1, 'icebeam'], [1, 'blizzard'], [1, 'gust'], [1, 'leer']],
      lore: 'Old stories say a frozen star once fell into the shrine south of Star City. Nobody who has gone inside can describe what they saw. They only remember the cold.' });
  S('legend_flame', 'L', '???', ['Fire'], [100, 130, 90, 110, 100, 100],
    { legendary: true, version: 'flame', rate: 3, xp: 300,
      learn: [[1, 'fireblast'], [1, 'flamethrower'], [1, 'wingattack'], [1, 'leer']],
      lore: 'Old stories say a burning star once fell into the shrine south of Star City. Nobody who has gone inside can describe what they saw. They only remember the heat.' });

  const STARTERS = ['swampidile', 'flamber', 'slimean'];

  // Unique forms: rare, recolored, 20% stronger. (Featured element from the notebook.)
  const UNIQUE = { chance: 1 / 64, statBoost: 1.2 };

  // ---------- monster instances ----------
  const expFor = (lv) => lv * lv * lv;

  function calcStats(mon) {
    const b = SPECIES[mon.key].base;
    const L = mon.level;
    const boost = mon.unique ? UNIQUE.statBoost : 1;
    const st = (v) => Math.floor((Math.floor((2 * v * L) / 100) + 5) * boost);
    mon.maxhp = Math.floor((Math.floor((2 * b.hp * L) / 100) + L + 10) * boost);
    mon.stats = { atk: st(b.atk), def: st(b.def), spa: st(b.spa), spd: st(b.spd), spe: st(b.spe) };
  }

  function movesAtLevel(key, level) {
    const list = [];
    for (const [lv, mv] of SPECIES[key].learn) if (lv <= level && !list.includes(mv)) list.push(mv);
    return list.slice(-4);
  }

  function makeMon(key, level, opts = {}) {
    const mon = {
      key, level, exp: expFor(level), unique: !!opts.unique,
      moves: movesAtLevel(key, level), hp: 0,
    };
    calcStats(mon);
    mon.hp = mon.maxhp;
    return mon;
  }

  const monName = (mon) => SPECIES[mon.key].name;

  window.DATA = {
    TYPE_COLORS, typeMult, MOVES, SPECIES, ORDER, STARTERS, UNIQUE,
    expFor, calcStats, movesAtLevel, makeMon, monName,
  };
})();
