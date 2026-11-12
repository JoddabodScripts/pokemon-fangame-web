'use strict';
// Debug panel. Open it with the ` key, F2, or the DBG button.
(function () {
  const DEFAULT_FLAGS = {
    noclip: false, fastWalk: false, noEncounters: false, encounterRate: 0.1,
    fastText: false, revealDex: false, alwaysUnique: false, sureCatch: false,
    oneHit: false, godMode: false, expBoost: false, showZones: false, showInfo: false,
  };
  let flags = { ...DEFAULT_FLAGS };
  try { Object.assign(flags, JSON.parse(localStorage.getItem('starRegionDebug') || '{}')); } catch (e) { /* ignore */ }
  const saveFlags = () => { try { localStorage.setItem('starRegionDebug', JSON.stringify(flags)); } catch (e) { /* ignore */ } };

  const logLines = [];
  let panel, logEl, mini, miniCtx, miniBase;
  let fps = 0, fpsAcc = 0, fpsN = 0, miniTimer = 0;

  const G = () => window.G;
  const ZONE_COLORS = { center: '#ffffff', arm0: '#ff5050', arm1: '#ffb030', arm2: '#40d0ff', arm3: '#60ff60', arm4: '#d070ff' };

  function log(msg) {
    logLines.push(msg);
    if (logLines.length > 40) logLines.shift();
    if (logEl) logEl.textContent = logLines.slice().reverse().join('\n');
    console.log('[debug]', msg);
  }

  function canAct() {
    const g = G();
    if (g.mode !== 'overworld' || g.busy) { log('Do that while walking around (not in a menu or battle).'); return false; }
    return true;
  }

  function teleport(x, y) {
    if (!canAct()) return;
    const map = G().map;
    // find the nearest walkable tile
    for (let r = 0; r < 8; r++) {
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= map.W || ny >= map.H) continue;
        if (!map.solid(nx, ny)) { G().placePlayer(nx, ny, 'down'); log(`Teleported to ${nx},${ny}`); return; }
      }
    }
  }

  function el(tag, attrs = {}, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (k === 'text') e.textContent = v;
      else e.setAttribute(k, v);
    }
    for (const kid of kids) if (kid) e.append(kid);
    return e;
  }
  const button = (label, fn) => el('button', { onclick: fn, text: label });
  function toggle(key, label) {
    const cb = el('input', { type: 'checkbox' });
    cb.checked = !!flags[key];
    cb.addEventListener('change', () => { flags[key] = cb.checked; saveFlags(); log(`${label}: ${cb.checked ? 'on' : 'off'}`); });
    return el('label', { class: 'tog' }, cb, ' ' + label);
  }
  function speciesSelect() {
    const s = el('select');
    for (const k of window.DATA.ORDER) {
      const sp = window.DATA.SPECIES[k];
      s.append(el('option', { value: k, text: `${sp.num} ${sp.name}${sp.legendary ? ' (' + sp.version + ' legendary)' : ''}` }));
    }
    return s;
  }

  function buildPanel() {
    panel = document.getElementById('debug');
    const D = window.DATA;

    const rate = el('input', { type: 'range', min: '0', max: '100', value: String(Math.round(flags.encounterRate * 100)) });
    const rateLbl = el('span', { text: Math.round(flags.encounterRate * 100) + '%' });
    rate.addEventListener('input', () => { flags.encounterRate = rate.value / 100; rateLbl.textContent = rate.value + '%'; saveFlags(); });

    const spSel = speciesSelect();
    const lvIn = el('input', { type: 'number', min: '1', max: '100', value: '5', class: 'num' });
    const uniq = el('input', { type: 'checkbox' });
    const getLv = () => Math.max(1, Math.min(100, parseInt(lvIn.value, 10) || 5));

    mini = el('canvas', { width: '160', height: '160', class: 'mini', title: 'Click to teleport' });
    miniCtx = mini.getContext('2d');
    mini.addEventListener('click', (e) => {
      const r = mini.getBoundingClientRect();
      teleport(Math.floor(((e.clientX - r.left) / r.width) * 160), Math.floor(((e.clientY - r.top) / r.height) * 160));
    });

    const townBtns = el('div', { class: 'row wrap' });
    const addTownButtons = () => {
      const map = G().map;
      if (!map) return;
      for (const t of map.towns) townBtns.append(button(t.name, () => teleport(t.spawn.x, t.spawn.y)));
      townBtns.append(button('Shrine', () => teleport(map.shrineSpot.x, map.shrineSpot.y + 1)));
    };

    logEl = el('pre', { class: 'log' });

    panel.append(
      el('div', { class: 'dhead' }, el('b', { text: 'DEBUG' }), el('span', { text: ' ` or F2 to toggle' }), button('X', () => toggleOpen(false))),
      el('h4', { text: 'Movement' }),
      el('div', { class: 'row wrap' }, toggle('noclip', 'Walk through walls'), toggle('fastWalk', 'Fast walk'), toggle('showInfo', 'Info overlay'), toggle('showZones', 'Show zones')),
      el('h4', { text: 'Teleport (click the map)' }),
      mini, townBtns,
      el('h4', { text: 'Encounters' }),
      el('div', { class: 'row' }, el('span', { text: 'Rate per grass step ' }), rate, rateLbl),
      el('div', { class: 'row wrap' }, toggle('noEncounters', 'No encounters'), toggle('alwaysUnique', 'Always Unique Form')),
      el('div', { class: 'row wrap' }, spSel, el('span', { text: 'Lv' }), lvIn, el('label', { class: 'tog' }, uniq, ' Unique')),
      el('div', { class: 'row wrap' },
        button('Fight it', () => {
          if (!canAct()) return;
          const key = spSel.value;
          G().runScript(() => window.BATTLE.start(D.makeMon(key, getLv(), { unique: uniq.checked }), { legendary: D.SPECIES[key].legendary }));
        }),
        button('Add to party', () => {
          if (!G().state) return log('Start a game first.');
          const where = G().addMon(D.makeMon(spSel.value, getLv(), { unique: uniq.checked }));
          log(`Added ${D.SPECIES[spSel.value].name} Lv${getLv()} to ${where}`);
        }),
        button('Random wild here', () => {
          if (!canAct()) return;
          const p = G().player;
          G().runScript(() => window.BATTLE.wild(G().map.zoneAt(p.x, p.y)));
        })),
      el('h4', { text: 'Battle' }),
      el('div', { class: 'row wrap' }, toggle('oneHit', 'One-hit KOs + never miss'), toggle('godMode', 'Take no damage'), toggle('sureCatch', '100% catch'), toggle('expBoost', '10x EXP'), toggle('fastText', 'Instant text')),
      el('div', { class: 'row wrap' },
        button('Win battle now', () => { window.BATTLE.debugWin(); log('Forced win'); }),
        button('Heal party', () => { if (G().state) { G().healAll(); if (window.BATTLE.state.active) { const B = window.BATTLE.state; B.disp.p = G().state.party[B.pi].hp; } log('Party healed'); } })),
      el('h4', { text: 'Party + items' }),
      el('div', { class: 'row wrap' },
        button('Lead +5 levels', () => {
          if (!canAct() || !G().state.party.length) return;
          const m = G().state.party[0];
          G().runScript(async () => {
            await window.BATTLE.debugLevel(m, 5);
            const sp = D.SPECIES[m.key];
            if (sp.evo && m.level >= sp.evo[1]) await window.BATTLE.evolve(m);
            log(`${D.monName(m)} is now Lv${m.level}`);
          });
        }),
        button('Evolve lead', () => {
          if (!canAct() || !G().state.party.length) return;
          G().runScript(async () => { if (!(await window.BATTLE.evolve(G().state.party[0]))) log('Lead has no evolution'); });
        }),
        button('99 balls + potions', () => { if (G().state) { G().state.bag.balls = 99; G().state.bag.potions = 99; log('Bag filled'); } }),
        button('Reset legendary', () => { if (G().state) { G().state.legendDone = false; log('Legendary can be fought again'); } })),
      el('div', { class: 'row wrap' }, toggle('revealDex', 'Reveal whole Pokedex')),
      el('h4', { text: 'Game' }),
      el('div', { class: 'row wrap' },
        button('Save now', () => { if (G().state && G().saveGame()) log('Saved'); }),
        button('Back to title', () => { if (G().state && G().mode === 'overworld') G().saveGame(); location.reload(); }),
        button('Delete this version\'s save', () => {
          if (!confirm(`Delete the ${G().version.toUpperCase()} save?`)) return;
          G().clearSave(G().version); G().state = null; location.reload();
        })),
      el('h4', { text: 'Log' }),
      logEl,
    );
    addTownButtons();
  }

  function renderMiniBase() {
    const map = G().map, T = window.MAP.T;
    const c = document.createElement('canvas');
    c.width = map.W; c.height = map.H;
    const g = c.getContext('2d');
    const COL = { [T.SEA]: '#2a68b8', [T.GRASS]: '#86cc62', [T.TALL]: '#3f9a3a', [T.PATH]: '#dcc48e', [T.TREE]: '#1f5a2a', [T.WATER]: '#3f86d8', [T.SAND]: '#ecd99a', [T.FLOWER]: '#86cc62', [T.FLOOR]: '#d6d0c0', [T.SIGN]: '#a8743a', [T.BLD]: '#c04040', [T.DOOR]: '#802020' };
    for (let y = 0; y < map.H; y++) for (let x = 0; x < map.W; x++) { g.fillStyle = COL[map.get(x, y)] || '#000'; g.fillRect(x, y, 1, 1); }
    miniBase = c;
  }

  function drawMini() {
    if (!miniBase) renderMiniBase();
    miniCtx.drawImage(miniBase, 0, 0);
    const p = G().player;
    miniCtx.fillStyle = '#ff2020';
    miniCtx.fillRect(p.x - 1, p.y - 1, 3, 3);
  }

  function toggleOpen(force) {
    const open = force !== undefined ? force : panel.hidden;
    panel.hidden = !open;
    document.body.classList.toggle('dbg-open', open);
    if (open && G().map) drawMini();
  }

  // ---------- canvas overlays ----------
  function drawWorld(ctx, camX, camY) {
    if (!flags.showZones) return;
    const map = G().map, T = window.MAP.T, TS = 16;
    const x0 = Math.floor(camX / TS), y0 = Math.floor(camY / TS);
    ctx.globalAlpha = 0.28;
    for (let ty = y0; ty <= y0 + 13; ty++) for (let tx = x0; tx <= x0 + 17; tx++) {
      const t = map.get(tx, ty);
      if (t === T.SEA) continue;
      ctx.fillStyle = ZONE_COLORS[map.zoneAt(tx, ty)];
      ctx.fillRect(tx * TS - camX, ty * TS - camY, TS, TS);
    }
    ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(0,0,0,0.15)';
    ctx.beginPath();
    for (let tx = x0; tx <= x0 + 17; tx++) { ctx.moveTo(tx * TS - camX + 0.5, 0); ctx.lineTo(tx * TS - camX + 0.5, 192); }
    for (let ty = y0; ty <= y0 + 13; ty++) { ctx.moveTo(0, ty * TS - camY + 0.5); ctx.lineTo(256, ty * TS - camY + 0.5); }
    ctx.stroke();
  }

  function drawHud(ctx) {
    const g = G();
    const badges = [];
    if (flags.noclip) badges.push('NOCLIP');
    if (flags.oneHit) badges.push('1HKO');
    if (flags.godMode) badges.push('GOD');
    if (flags.noEncounters) badges.push('NO-ENC');
    if (!flags.showInfo && !badges.length) return;
    ctx.font = '8px "Press Start 2P", monospace';
    ctx.textBaseline = 'top';
    ctx.textAlign = 'left';
    const lines = [];
    if (flags.showInfo) {
      lines.push(`FPS ${fps} ${g.mode}${g.busy ? ' busy' : ''}`);
      if (g.map && g.state) {
        const p = g.player, T = window.MAP.T;
        const tname = Object.keys(T).find((k) => T[k] === g.map.get(p.x, p.y));
        lines.push(`X${p.x} Y${p.y} ${tname}`);
        lines.push(`${g.map.zoneAt(p.x, p.y)} enc ${Math.round(flags.encounterRate * 100)}%`);
        lines.push(`steps ${g.state.steps}`);
      }
    }
    if (badges.length) lines.push(badges.join(' '));
    const w = Math.max(...lines.map((l) => ctx.measureText(l).width)) + 6;
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(256 - w - 2, 2, w, lines.length * 10 + 4);
    lines.forEach((l, i) => { ctx.fillStyle = '#7fff7f'; ctx.fillText(l, 256 - w + 1, 5 + i * 10); });
  }

  function tick(dt) {
    fpsAcc += dt; fpsN++;
    if (fpsAcc >= 0.5) { fps = Math.round(fpsN / fpsAcc); fpsAcc = 0; fpsN = 0; }
    if (panel && !panel.hidden && G().map) {
      miniTimer -= dt;
      if (miniTimer <= 0) { miniTimer = 0.25; drawMini(); }
    }
  }

  function init() {
    buildPanel();
    document.getElementById('dbgBtn').addEventListener('click', () => toggleOpen());
    if (/[?&]debug/.test(location.search)) toggleOpen(true);
    log('Debug ready. Press ` or F2 to open/close.');
  }

  window.DEBUG = { flags, init, toggle: () => toggleOpen(), drawWorld, drawHud, tick, log };
})();
