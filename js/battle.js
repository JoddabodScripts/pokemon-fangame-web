'use strict';
// Turn-based battles: fight, catch, switch, run. EXP, level ups, new moves and evolution.
(function () {
  const { SPECIES, MOVES, typeMult, makeMon, monName, expFor, calcStats, UNIQUE } = window.DATA;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const STAT_NAMES = { atk: 'ATTACK', def: 'DEFENSE', spa: 'SP. ATK', spd: 'SP. DEF', spe: 'SPEED' };
  const freshStages = () => ({ atk: 0, def: 0, spa: 0, spd: 0, spe: 0 });
  const stageMult = (s) => (s >= 0 ? (2 + s) / 2 : 2 / (2 - s));

  const B = { active: false };
  let ballImg = null;

  const G = () => window.G;
  const party = () => G().state.party;
  const me = () => party()[B.pi];
  const D = () => window.DEBUG.flags;

  function label(side) {
    if (side === 'p') return monName(me()).toUpperCase();
    return (B.opts.legendary ? 'The ' : 'Wild ') + monName(B.enemy).toUpperCase();
  }
  function effStat(mon, stat, side) {
    return mon.stats[stat] * stageMult(B.stages[side][stat]) * (B.split[side] || 1);
  }

  // ---------- wild encounters ----------
  function rollWild(zone) {
    const z = window.MAP.ZONES[zone];
    const total = z.mons.reduce((s, [, w]) => s + w, 0);
    let r = Math.random() * total, key = z.mons[0][0];
    for (const [k, w] of z.mons) { if ((r -= w) < 0) { key = k; break; } }
    const level = z.lv[0] + Math.floor(Math.random() * (z.lv[1] - z.lv[0] + 1));
    const unique = D().alwaysUnique || Math.random() < UNIQUE.chance;
    return makeMon(key, level, { unique });
  }
  async function wild(zone) { return start(rollWild(zone), {}); }

  // ---------- battle flow ----------
  async function start(enemy, opts = {}) {
    const g = G();
    if (!ballImg) ballImg = window.SPRITES.makeBall();
    const pi = party().findIndex((m) => m.hp > 0);
    if (pi < 0) { await g.say('All your Pokemon have fainted! Heal them at a Pokemon Center first.'); return 'run'; }
    Object.assign(B, {
      active: true, enemy, pi, opts,
      stages: { p: freshStages(), e: freshStages() },
      split: { p: null, e: null },
      disp: { p: party()[pi].hp, e: enemy.hp },
      flash: { p: 0, e: 0 },
      enemyHidden: false, ball: null, moveMenu: false, forceWin: false, intro: 1,
    });
    g.mode = 'battle';
    g.markSeen(enemy.key);
    window.DEBUG.log(`Battle: ${monName(enemy)} Lv${enemy.level}${enemy.unique ? ' (unique)' : ''}`);
    if (opts.legendary) await g.say(`The legendary Pokemon ${monName(enemy)} appeared!`);
    else await g.say(`A wild ${enemy.unique ? 'UNIQUE ' : ''}${monName(enemy).toUpperCase()} appeared!`);
    if (enemy.unique) await g.say('It\'s a Unique Form! It looks different and it\'s stronger than normal.');
    await g.say(`Go! ${monName(me()).toUpperCase()}!`);

    let result;
    try { result = await loop(); } catch (e) { console.error(e); result = 'run'; }

    // clean up after battle
    for (const m of party()) { if (m.hp > m.maxhp) m.hp = m.maxhp; }
    if (result === 'win' || result === 'caught') await evolutions();
    for (const m of party()) delete m._lvUp;
    if (result === 'lose') {
      await g.say('You have no Pokemon left that can fight!');
      await g.say('You hurried back to the last Pokemon Center...');
      g.healAll();
      g.placePlayer(g.state.lastHeal.x, g.state.lastHeal.y, 'down');
    }
    B.active = false;
    g.mode = 'overworld';
    g.saveGame();
    return result;
  }

  async function loop() {
    const g = G();
    for (;;) {
      if (B.forceWin) { B.forceWin = false; B.enemy.hp = 0; B.disp.e = 0; }
      if (B.enemy.hp <= 0) return enemyFainted();
      const c = await g.choose(['FIGHT', 'BAG', 'POKEMON', 'RUN'], {
        cols: 2, x: 120, y: g.SH - 48, w: 132, cancel: false, prompt: `What will ${monName(me()).toUpperCase()} do?`,
      });
      if (c === -2) continue;
      let action = null;
      if (c === 0) {
        B.moveMenu = true;
        const mi = await g.choose(me().moves.map((k) => MOVES[k].name.toUpperCase()), { cols: 2, x: 4, y: g.SH - 44, w: g.SW - 8 });
        B.moveMenu = false;
        if (mi < 0) continue;
        action = { kind: 'move', move: me().moves[mi] };
      } else if (c === 1) {
        const r = await battleBag();
        if (r === 'back') continue;
        if (r === 'caught') return 'caught';
        action = { kind: 'other' };
      } else if (c === 2) {
        const i = await g.pickPartyMember('Switch to which Pokemon?');
        if (i < 0 || i === B.pi) continue;
        if (party()[i].hp <= 0) { await g.say('That Pokemon has fainted and can\'t battle!'); continue; }
        await doSwitch(i);
        action = { kind: 'other' };
      } else if (c === 3) {
        const canRun = D().oneHit || effStat(me(), 'spe', 'p') >= effStat(B.enemy, 'spe', 'e') || Math.random() < 0.6;
        if (canRun) { await g.say('Got away safely!'); return 'run'; }
        await g.say('Couldn\'t get away!');
        action = { kind: 'other' };
      }
      const out = await turn(action);
      if (out) return out;
    }
  }

  function enemyMove() {
    const moves = B.enemy.moves;
    if (B.opts.legendary && Math.random() < 0.7) {
      return moves.reduce((best, k) => ((MOVES[k].power || 0) > (MOVES[best].power || 0) ? k : best), moves[0]);
    }
    return moves[Math.floor(Math.random() * moves.length)];
  }

  async function turn(action) {
    const acts = [];
    if (action.kind === 'move') acts.push({ side: 'p', move: action.move, user: me() });
    acts.push({ side: 'e', move: enemyMove(), user: B.enemy });
    if (acts.length === 2) {
      acts.sort((a, b) => {
        const pa = MOVES[a.move].priority || 0, pb = MOVES[b.move].priority || 0;
        if (pa !== pb) return pb - pa;
        const sa = effStat(a.user, 'spe', a.side), sb = effStat(b.user, 'spe', b.side);
        return sa !== sb ? sb - sa : Math.random() - 0.5;
      });
    }
    for (const a of acts) {
      if (a.user.hp <= 0) continue;
      if (a.side === 'p' && a.user !== me()) continue; // switched out after fainting
      await useMove(a.side, a.move);
      const r = await checkFaints();
      if (r === 'end') return null;
      if (r) return r;
    }
    for (const side of ['p', 'e']) {
      const s = B.split[side];
      if (s && s < 1) {
        B.split[side] = Math.min(1, s + 0.25);
        await G().say(B.split[side] >= 1
          ? `${label(side)}'s halves are back to full strength!`
          : `${label(side)}'s halves regrew a bit. (${Math.round(B.split[side] * 100)}% stats)`);
      }
    }
    return null;
  }

  async function checkFaints() {
    const g = G();
    if (B.enemy.hp <= 0) return enemyFainted();
    if (me().hp <= 0) {
      await g.say(`${label('p')} fainted!`);
      B.split.p = null;
      if (!party().some((m) => m.hp > 0)) return 'lose';
      for (;;) {
        const i = await g.pickPartyMember('Choose your next Pokemon.', { cancel: false });
        if (i >= 0 && party()[i].hp > 0) { await doSwitch(i, true); break; }
        await g.say('That Pokemon can\'t battle!');
      }
      return 'end';
    }
    return null;
  }

  async function doSwitch(i, afterFaint) {
    const g = G();
    if (!afterFaint) await g.say(`Come back, ${label('p')}!`);
    B.pi = i;
    B.stages.p = freshStages();
    B.split.p = null;
    B.disp.p = me().hp;
    await g.say(`Go! ${label('p')}!`);
  }

  function waitHp() {
    return new Promise((res) => {
      const check = () => {
        if (Math.abs(B.disp.p - me().hp) < 0.5 && Math.abs(B.disp.e - B.enemy.hp) < 0.5) { B.disp.p = me().hp; B.disp.e = B.enemy.hp; res(); }
        else setTimeout(check, 16);
      };
      check();
    });
  }

  async function changeStage(side, stat, stages) {
    const g = G();
    const cur = B.stages[side][stat];
    const next = Math.max(-6, Math.min(6, cur + stages));
    if (next === cur) { await g.say(`${label(side)}'s ${STAT_NAMES[stat]} won't go any ${stages < 0 ? 'lower' : 'higher'}!`); return; }
    B.stages[side][stat] = next;
    await g.say(`${label(side)}'s ${STAT_NAMES[stat]} ${stages < 0 ? 'fell' : 'rose'}!`);
  }

  function calcDamage(side, user, target, mv) {
    const tside = side === 'p' ? 'e' : 'p';
    const phys = mv.cat === 'phys';
    const A = effStat(user, phys ? 'atk' : 'spa', side);
    const Df = effStat(target, phys ? 'def' : 'spd', tside);
    const base = Math.floor(Math.floor(((2 * user.level) / 5 + 2) * mv.power * A / Df) / 50) + 2;
    const stab = SPECIES[user.key].types.includes(mv.type) ? 1.5 : 1;
    const mult = typeMult(mv.type, SPECIES[target.key].types);
    const crit = Math.random() < 1 / 16;
    let dmg = Math.floor(base * stab * mult * (crit ? 1.5 : 1) * (0.85 + Math.random() * 0.15));
    dmg = mult === 0 ? 0 : Math.max(1, dmg);
    if (side === 'p' && D().oneHit) dmg = Math.max(dmg, target.hp);
    if (side === 'e' && D().godMode) dmg = 0;
    return { dmg, mult, crit };
  }

  async function useMove(side, moveKey) {
    const g = G();
    const mv = MOVES[moveKey];
    const tside = side === 'p' ? 'e' : 'p';
    const user = side === 'p' ? me() : B.enemy;
    const target = () => (side === 'p' ? B.enemy : me());
    await g.say(`${label(side)} used ${mv.name.toUpperCase()}!`);

    if (mv.cat === 'status') {
      if (mv.effect.split) {
        if (B.split[side]) { await g.say('But it is already split!'); return; }
        B.split[side] = 0.5;
        await g.say(`${label(side)} split into two halves! Each half has 50% stats and both use the same move.`);
        return;
      }
      if (Math.random() * 100 >= mv.acc) { await g.say('But it missed!'); return; }
      const ef = mv.effect;
      await changeStage(ef.target === 'self' ? side : tside, ef.stat, ef.stages);
      return;
    }

    const hits = B.split[side] ? 2 : 1;
    let landed = 0;
    for (let h = 0; h < hits; h++) {
      const tgt = target();
      if (tgt.hp <= 0) break;
      const sure = side === 'p' && D().oneHit;
      if (!sure && Math.random() * 100 >= mv.acc) {
        await g.say(hits > 1 ? 'One half missed!' : `${label(side)}'s attack missed!`);
        continue;
      }
      const { dmg, mult, crit } = calcDamage(side, user, tgt, mv);
      tgt.hp = Math.max(0, tgt.hp - dmg);
      B.flash[tside] = 0.45;
      await waitHp();
      landed++;
      if (crit) await g.say('A critical hit!');
      if (h === 0 || hits === 1) {
        if (mult > 1) await g.say('It\'s super effective!');
        else if (mult < 1) await g.say('It\'s not very effective...');
      }
      if (mv.drain && dmg > 0 && user.hp > 0) {
        const heal = Math.max(1, Math.floor(dmg * mv.drain));
        user.hp = mv.overheal ? user.hp + heal : Math.min(user.maxhp, user.hp + heal);
        await waitHp();
        await g.say(user.hp > user.maxhp
          ? `${label(side)} healed ${heal} HP, going over its max HP!`
          : `${label(side)} healed ${heal} HP!`);
      }
      if (mv.effect && mv.effect.chance && tgt.hp > 0 && Math.random() * 100 < mv.effect.chance) {
        await changeStage(mv.effect.target === 'self' ? side : tside, mv.effect.stat, mv.effect.stages);
      }
    }
    if (hits > 1 && landed > 0) await g.say(`Both halves attacked! Hit ${landed} time${landed > 1 ? 's' : ''}.`);
  }

  async function enemyFainted() {
    const g = G(), foe = B.enemy;
    await g.say(`${label('e')} fainted!`);
    B.enemyHidden = true;
    const mon = me();
    if (mon && mon.hp > 0) {
      const gain = Math.max(1, Math.floor((SPECIES[foe.key].xp * foe.level) / 7 * (B.opts.legendary ? 1.5 : 1) * (D().expBoost ? 10 : 1)));
      await gainExp(mon, gain);
    }
    return 'win';
  }

  async function gainExp(mon, amount) {
    const g = G();
    if (mon.level >= 100) return;
    mon.exp += amount;
    await g.say(`${monName(mon).toUpperCase()} gained ${amount} EXP. Points!`);
    while (mon.level < 100 && mon.exp >= expFor(mon.level + 1)) await levelUp(mon);
  }

  async function levelUp(mon, silent) {
    const g = G();
    const oldMax = mon.maxhp;
    mon.level++;
    calcStats(mon);
    mon.hp += mon.maxhp - oldMax;
    mon._lvUp = true;
    if (mon === me() && B.active) B.disp.p = mon.hp;
    if (!silent) await g.say(`${monName(mon).toUpperCase()} grew to Lv. ${mon.level}!`);
    for (const [lv, mk] of SPECIES[mon.key].learn) if (lv === mon.level) await learnMove(mon, mk, silent);
  }

  async function learnMove(mon, mk, silent) {
    const g = G();
    if (mon.moves.includes(mk)) return;
    const name = monName(mon).toUpperCase(), mvName = MOVES[mk].name.toUpperCase();
    if (mon.moves.length < 4) {
      mon.moves.push(mk);
      if (!silent) await g.say(`${name} learned ${mvName}!`);
      return;
    }
    if (silent) { mon.moves.shift(); mon.moves.push(mk); return; }
    await g.say(`${name} wants to learn ${mvName}, but it already knows 4 moves.`);
    const i = await g.choose([...mon.moves.map((k) => MOVES[k].name.toUpperCase()), 'DON\'T LEARN'], { x: 100, y: 20, w: 152, cancel: false, prompt: `Forget which move for ${mvName}?` });
    if (i < 4) {
      const old = MOVES[mon.moves[i]].name.toUpperCase();
      mon.moves[i] = mk;
      await g.say(`${name} forgot ${old} and learned ${mvName}!`);
    } else await g.say(`${name} did not learn ${mvName}.`);
  }

  async function evolutions() {
    const g = G();
    for (const mon of party()) {
      if (!mon._lvUp) continue;
      const sp = SPECIES[mon.key];
      if (!sp.evo || mon.level < sp.evo[1]) continue;
      await evolve(mon);
    }
  }

  async function evolve(mon, silent) {
    const g = G();
    const sp = SPECIES[mon.key];
    if (!sp.evo) return false;
    const oldName = sp.name.toUpperCase(), newKey = sp.evo[0];
    if (!silent) {
      const t0 = g.time;
      g.overlay = (ctx) => {
        ctx.fillStyle = '#101018'; ctx.fillRect(0, 0, g.SW, g.SH);
        const e = g.time - t0;
        const showNew = Math.sin(e * (4 + e * 3)) > 0 && e > 0.5;
        g.drawSprite(showNew ? newKey : mon.key, mon.unique, 80, 30, 96, false, e < 3);
      };
      await g.say(`What? ${oldName} is evolving!`);
      await sleep(1600);
    }
    const oldMax = mon.maxhp;
    mon.key = newKey;
    calcStats(mon);
    mon.hp = Math.max(0, mon.hp + mon.maxhp - oldMax);
    g.markCaught(newKey);
    if (!silent) {
      g.overlay = (ctx) => { ctx.fillStyle = '#101018'; ctx.fillRect(0, 0, g.SW, g.SH); g.drawSprite(mon.key, mon.unique, 80, 30, 96); };
      await g.say(`Congratulations! ${oldName} evolved into ${SPECIES[newKey].name.toUpperCase()}!`);
    }
    for (const [lv, mk] of SPECIES[newKey].learn) if (lv === mon.level) await learnMove(mon, mk, silent);
    g.overlay = null;
    return true;
  }

  // ---------- bag ----------
  async function battleBag() {
    const g = G(), bag = g.state.bag;
    const i = await g.choose([`STAR BALL x${bag.balls}`, `POTION x${bag.potions}`], { x: 100, y: 60, w: 152 });
    if (i < 0) return 'back';
    if (i === 0) {
      if (bag.balls <= 0) { await g.say('You are out of Star Balls!'); return 'back'; }
      bag.balls--;
      return throwBall();
    }
    if (bag.potions <= 0) { await g.say('You are out of Potions!'); return 'back'; }
    const t = await g.pickPartyMember('Use a Potion on which Pokemon?');
    if (t < 0) return 'back';
    const m = party()[t];
    if (m.hp <= 0 || m.hp >= m.maxhp) { await g.say('It would have no effect.'); return 'back'; }
    const healed = Math.min(20, m.maxhp - m.hp);
    m.hp += healed; bag.potions--;
    await waitHp();
    await g.say(`${monName(m).toUpperCase()} got back ${healed} HP.`);
    return 'used';
  }

  async function throwBall() {
    const g = G(), foe = B.enemy;
    await g.say('You threw a STAR BALL!');
    B.ball = { t: 0, shake: 0 };
    B.enemyHidden = true;
    const M = foe.maxhp, H = foe.hp;
    let p = ((3 * M - 2 * H) * SPECIES[foe.key].rate * 2.5) / (3 * M * 255);
    if (foe.unique) p *= 0.8;
    p = Math.min(1, p);
    if (D().sureCatch) p = 1;
    const caught = Math.random() < p;
    const shakes = caught ? 3 : Math.floor(Math.random() * 3);
    window.DEBUG.log(`Catch chance ${(p * 100).toFixed(1)}% -> ${caught ? 'caught' : 'broke free'}`);
    for (let s = 0; s < shakes; s++) { B.ball.shake = 0.5; await sleep(700); }
    await sleep(300);
    if (caught) {
      await g.say(`Gotcha! ${monName(foe).toUpperCase()} was caught!`);
      delete foe.split;
      const where = g.addMon(foe);
      if (where === 'box') await g.say('Your party is full, so it was sent to the PC Box.');
      return 'caught';
    }
    B.ball = null;
    B.enemyHidden = false;
    await g.say(['Oh no! It broke free!', 'Aww! It looked caught!', 'Argh! So close!'][shakes]);
    return 'used';
  }

  // ---------- update + draw ----------
  function update(dt) {
    if (!B.active) return;
    for (const side of ['p', 'e']) {
      const mon = side === 'p' ? me() : B.enemy;
      if (!mon) continue;
      const target = mon.hp, step = Math.max(mon.maxhp * dt * 1.4, dt * 30);
      if (B.disp[side] < target) B.disp[side] = Math.min(target, B.disp[side] + step);
      else if (B.disp[side] > target) B.disp[side] = Math.max(target, B.disp[side] - step);
      if (B.flash[side] > 0) B.flash[side] -= dt;
    }
    if (B.ball && B.ball.shake > 0) B.ball.shake -= dt;
    if (B.intro > 0) B.intro = Math.max(0, B.intro - dt * 2.5);
  }

  function drawMon(ctx, mon, side, x, y, size, flip) {
    const g = G();
    if (B.flash[side] > 0 && Math.floor(g.time * 20) % 2) return;
    if (B.split[side]) {
      const s = Math.round(size * 0.66);
      g.drawSprite(mon.key, mon.unique, x - 8, y + size - s, s, flip);
      g.drawSprite(mon.key, mon.unique, x + size - s + 8, y + size - s - 6, s, flip);
    } else g.drawSprite(mon.key, mon.unique, x, y, size, flip);
    if (mon.unique) {
      for (let i = 0; i < 4; i++) {
        const a = g.time * 2 + i * 1.57;
        ctx.fillStyle = '#fff6a0';
        ctx.fillRect(Math.round(x + size / 2 + Math.cos(a) * size * 0.45), Math.round(y + size / 2 + Math.sin(a) * size * 0.4), 2, 2);
      }
    }
  }

  function infoBox(ctx, mon, side, x, y, w, full) {
    const g = G();
    const h = full ? 40 : 30;
    g.box(x, y, w, h);
    g.text((mon.unique ? '*' : '') + monName(mon).toUpperCase(), x + 6, y + 5);
    g.text('Lv' + mon.level, x + 6, y + 17, '#444');
    g.text('HP', x + 42, y + 17, '#c07020');
    g.hpBar(x + 58, y + 18, w - 64, B.disp[side], mon.maxhp);
    if (full) {
      g.text(`${Math.round(B.disp[side])}/${mon.maxhp}`, x + w - 6, y + 27, '#333', 'right');
      const lo = expFor(mon.level), hi = expFor(mon.level + 1);
      const f = Math.max(0, Math.min(1, (mon.exp - lo) / (hi - lo)));
      ctx.fillStyle = '#ccc'; ctx.fillRect(x + 6, y + h - 6, w - 12, 2);
      ctx.fillStyle = '#3a8ae0'; ctx.fillRect(x + 6, y + h - 6, Math.round((w - 12) * f), 2);
    }
    if (B.split[side]) {
      const by = y < 20 ? y + h + 1 : y - 13;
      ctx.fillStyle = '#2a6ac0'; ctx.fillRect(x + w - 82, by, 82, 12);
      g.text(`SPLIT ${Math.round(B.split[side] * 100)}%`, x + w - 3, by + 2, '#fff', 'right');
    }
  }

  function draw(ctx) {
    const g = G();
    if (!B.active) return;
    const flame = g.version === 'flame';
    const grad = ctx.createLinearGradient(0, 0, 0, g.SH);
    grad.addColorStop(0, flame ? '#ffd8b8' : '#cfeaff');
    grad.addColorStop(1, flame ? '#fff3e2' : '#f2fbff');
    ctx.fillStyle = grad; ctx.fillRect(0, 0, g.SW, g.SH);
    ctx.fillStyle = flame ? '#e8b48a' : '#a8d4a0';
    ctx.beginPath(); ctx.ellipse(196, 94, 50, 10, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(58, 138, 58, 10, 0, 0, Math.PI * 2); ctx.fill();

    const slide = Math.round(B.intro * 140);
    if (!B.enemyHidden) drawMon(ctx, B.enemy, 'e', 148 - slide, 4, 96, false);
    if (B.ball) {
      const wob = B.ball.shake > 0 ? Math.round(Math.sin(B.ball.shake * 30) * 3) : 0;
      ctx.drawImage(ballImg, 190 + wob, 78);
    }
    drawMon(ctx, me(), 'p', 8 + slide, 46, 96, true);

    infoBox(ctx, B.enemy, 'e', 6, 8, 128, false);
    infoBox(ctx, me(), 'p', 124, 102, 128, true);

    if (B.moveMenu && g.ui.menu) {
      const mv = MOVES[me().moves[g.ui.menu.idx]];
      if (mv) {
        g.box(g.SW - 132, g.SH - 64, 128, 20);
        const w = g.typeTag(mv.type, g.SW - 126, g.SH - 60);
        g.text(mv.power ? 'PWR ' + mv.power : 'STATUS', g.SW - 120 + w, g.SH - 58);
      }
    }
  }

  // debug helpers
  function debugWin() { if (!B.active) return; B.forceWin = true; G().ui.forceMenu(-2); }
  async function debugLevel(mon, n) { for (let i = 0; i < n && mon.level < 100; i++) { await levelUp(mon, true); } mon.exp = expFor(mon.level); }

  window.BATTLE = { start, wild, rollWild, update, draw, state: B, debugWin, debugLevel, evolve };
})();
