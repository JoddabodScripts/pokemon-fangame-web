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
                   desc: 'PLACEHOLDER signature move. 90 power, lowers the target\'s Speed.' },

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
                   desc: 'PLACEHOLDER signature move. 100 power, 90 accuracy.' },

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
      note: o.note || '',
      legendary: !!o.legendary,
      version: o.version || null,
      look: o.look || '',
    };
    ORDER.push(key);
  }

  const READ = 'Name and stats read from the notebook photo.';
  const GUESS = 'Name and stats are PLACEHOLDERS. Ask the designer.';

  // Grass starter line
  const swampLearn = [[1, 'tackle'], [1, 'growl'], [5, 'vinewhip'], [9, 'leer'], [13, 'razorleaf'], [20, 'gigadrain']];
  S('swampidile', 1, 'Swampidile', ['Grass'], [50, 50, 100, 50, 50, 80],
    { evo: ['swamporiaer', 16], rate: 45, xp: 64, learn: swampLearn, note: READ });
  S('swamporiaer', 2, 'Swamporiaer', ['Grass'], [120, 90, 125, 50, 50, 50],
    { evo: ['swampest', 32], rate: 45, xp: 142, learn: swampLearn, note: READ + ' Some stats were hard to read.' });
  S('swampest', 3, 'Swampest', ['Grass'], [130, 95, 140, 85, 80, 30],
    { rate: 45, xp: 236, learn: [...swampLearn, [36, 'bogchomp']], sig: 'bogchomp', note: READ + ' Signature move is a placeholder.' });

  // Fire starter line
  const flameLearn = [[1, 'scratch'], [1, 'growl'], [5, 'ember'], [9, 'quickattack'], [13, 'flamewheel'], [24, 'flamethrower']];
  S('flamber', 4, 'Flamber', ['Fire'], [40, 10, 40, 130, 40, 110],
    { evo: ['flamezion', 16], rate: 45, xp: 62, learn: flameLearn, note: READ });
  S('flamezion', 5, 'Flamezion', ['Fire'], [60, 20, 55, 160, 55, 125],
    { evo: ['blazian', 32], rate: 45, xp: 142, learn: flameLearn, note: READ + ' Page says total 475.' });
  S('blazian', 6, 'Blazian', ['Fire'], [80, 40, 60, 200, 60, 130],
    { rate: 45, xp: 240, learn: [...flameLearn, [36, 'flamesofhealth']], sig: 'flamesofhealth', note: READ + ' 200cm tall.' });

  // Water starter line
  const slimeLearn = [[1, 'tackle'], [1, 'growl'], [5, 'bubble'], [9, 'leer'], [12, 'slimeshot'], [24, 'slimeslam']];
  S('slimean', 7, 'Slimean', ['Water'], [60, 70, 65, 30, 65, 60],
    { evo: ['slimarton', 16], rate: 45, xp: 63, learn: slimeLearn, note: READ + ' Stats add to 350, page says 370. 40cm tall.' });
  S('slimarton', 8, 'Slimarton', ['Water'], [80, 100, 70, 70, 70, 40],
    { evo: ['slimontoon', 32], rate: 45, xp: 142, learn: slimeLearn, note: READ + ' 130cm tall.' });
  S('slimontoon', 9, 'Slimontoon', ['Water'], [100, 115, 100, 50, 100, 70],
    { rate: 45, xp: 239, learn: [...slimeLearn, [36, 'slimesplit']], sig: 'slimesplit', note: READ + ' 600cm tall.' });

  // Bird line (names are placeholders)
  const birdLearn = [[1, 'peck'], [1, 'growl'], [5, 'gust'], [9, 'quickattack'], [15, 'wingattack']];
  S('peeplet', 10, 'Peeplet', ['Normal', 'Flying'], [40, 60, 25, 35, 30, 40],
    { evo: ['featherdash', 14], rate: 255, xp: 50, learn: birdLearn, note: GUESS });
  S('featherdash', 11, 'Featherdash', ['Normal', 'Flying'], [60, 70, 55, 60, 55, 110],
    { evo: ['fiercebird', 30], rate: 120, xp: 122, learn: birdLearn, note: GUESS });
  S('fiercebird', 12, 'Fiercebird', ['Flying'], [100, 110, 90, 70, 80, 90],
    { rate: 45, xp: 216, learn: [...birdLearn, [34, 'fierceblast']], sig: 'fierceblast',
      note: 'Name is my best read of the page. Stats and signature move are placeholders.' });

  // Version legendaries (not designed yet)
  S('legend_freeze', 'L', '???', ['Ice'], [100, 90, 100, 130, 110, 100],
    { legendary: true, version: 'freeze', rate: 3, xp: 300,
      learn: [[1, 'icebeam'], [1, 'blizzard'], [1, 'gust'], [1, 'leer']],
      note: 'Freeze Version legendary. Not designed yet, this is a stand-in.' });
  S('legend_flame', 'L', '???', ['Fire'], [100, 130, 90, 110, 100, 100],
    { legendary: true, version: 'flame', rate: 3, xp: 300,
      learn: [[1, 'fireblast'], [1, 'flamethrower'], [1, 'wingattack'], [1, 'leer']],
      note: 'Flame Version legendary. Not designed yet, this is a stand-in.' });

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
