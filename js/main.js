'use strict';
(function () {
  const { SPECIES, MOVES, TYPE_COLORS, ORDER, STARTERS, makeMon, monName } = window.DATA;
  const SW = 256, SH = 192, TS = 16;
  const FONT = '8px "Press Start 2P", monospace';

  const canvas = document.getElementById('screen');
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;

  // ---------------- game state ----------------
  const G = (window.G = {
    mode: 'loading',      // loading | title | starter | overworld | battle
    version: 'freeze',
    busy: false,          // true while a scripted sequence (menu, battle, dialog) runs
    time: 0,
    map: null,
    tiles: null,
    playerSprites: null,
    buildingImgs: {},
    state: null,          // saved stuff: party, bag, position...
    player: { x: 0, y: 0, dir: 'down', moving: false, fx: 0, fy: 0, t: 0, frame: 0, stepFrame: 0 },
    zoneBanner: { text: '', t: 0, zone: null },
    overlay: null,        // function(ctx) drawn on top of the scene
  });

  function freshState() {
    const city = G.map.towns[0];
    return {
      version: G.version,
      party: [], box: [],
      bag: { balls: 10, potions: 5 },
      dex: { seen: {}, caught: {} },
      pos: { x: city.heal.x, y: city.heal.y, dir: 'down' },
      lastHeal: { x: city.heal.x, y: city.heal.y },
      legendDone: false,
      steps: 0,
    };
  }

  // ---------------- input ----------------
  const Input = (G.input = { held: new Set(), pressed: new Set(), lastDir: null });
  const KEYMAP = {
    ArrowUp: 'up', KeyW: 'up', ArrowDown: 'down', KeyS: 'down', ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right',
    KeyZ: 'a', Space: 'a', Enter: 'a', KeyJ: 'a',
    KeyX: 'b', Backspace: 'b', KeyK: 'b', ShiftLeft: 'b', ShiftRight: 'b',
    Escape: 'start', KeyM: 'start', KeyP: 'start',
  };
  function press(k) { if (!Input.held.has(k)) Input.pressed.add(k); Input.held.add(k); if (['up', 'down', 'left', 'right'].includes(k)) Input.lastDir = k; }
  function release(k) { Input.held.delete(k); }
  window.addEventListener('keydown', (e) => {
    const tag = (e.target && e.target.tagName) || '';
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(tag)) return;
    if (e.code === 'Backquote' || e.code === 'F2') { e.preventDefault(); window.DEBUG.toggle(); return; }
    const k = KEYMAP[e.code];
    if (!k) return;
    e.preventDefault();
    if (e.repeat) return;
    press(k);
  });
  window.addEventListener('keyup', (e) => { const k = KEYMAP[e.code]; if (k) release(k); });
  window.addEventListener('blur', () => Input.held.clear());
  document.querySelectorAll('[data-key]').forEach((btn) => {
    const k = btn.dataset.key;
    const down = (e) => { e.preventDefault(); press(k); btn.classList.add('on'); };
    const up = (e) => { e.preventDefault(); release(k); btn.classList.remove('on'); };
    btn.addEventListener('pointerdown', down);
    btn.addEventListener('pointerup', up);
    btn.addEventListener('pointerleave', up);
    btn.addEventListener('pointercancel', up);
  });
  const consume = (k) => (Input.pressed.has(k) ? (Input.pressed.delete(k), true) : false);
  G.consume = consume;

  // ---------------- text + UI ----------------
  function text(str, x, y, col = '#222', align = 'left') {
    ctx.font = FONT;
    ctx.textBaseline = 'top';
    ctx.textAlign = align;
    ctx.fillStyle = col;
    ctx.fillText(str, Math.round(x), Math.round(y));
  }
  function wrap(str, maxW) {
    ctx.font = FONT;
    const out = [];
    for (const para of String(str).split('\n')) {
      let line = '';
      for (const word of para.split(' ')) {
        const test = line ? line + ' ' + word : word;
        if (ctx.measureText(test).width > maxW && line) { out.push(line); line = word; } else line = test;
      }
      out.push(line);
    }
    return out;
  }
  function box(x, y, w, h, fill = '#fbfbf4', border = '#2a2a3a') {
    ctx.fillStyle = border; ctx.fillRect(x, y, w, h);
    ctx.fillStyle = fill; ctx.fillRect(x + 2, y + 2, w - 4, h - 4);
    ctx.fillStyle = G.version === 'flame' ? '#e07040' : '#5aa0e0';
    ctx.fillRect(x + 2, y + 2, w - 4, 1);
  }
  function cursor(x, y) {
    ctx.fillStyle = '#222';
    for (let i = 0; i < 4; i++) ctx.fillRect(x + i, y + i, 1, 7 - i * 2);
  }
  function hpBar(x, y, w, hp, max) {
    const f = Math.max(0, Math.min(1, hp / max));
    ctx.fillStyle = '#333'; ctx.fillRect(x, y, w, 5);
    ctx.fillStyle = '#ddd'; ctx.fillRect(x + 1, y + 1, w - 2, 3);
    ctx.fillStyle = f > 0.5 ? '#3ac04a' : f > 0.2 ? '#f0c020' : '#e03a2a';
    ctx.fillRect(x + 1, y + 1, Math.round((w - 2) * f), 3);
  }
  function typeTag(t, x, y) {
    ctx.fillStyle = TYPE_COLORS[t] || '#888';
    ctx.font = FONT;
    const w = ctx.measureText(t.toUpperCase()).width + 6;
    ctx.fillRect(x, y, w, 11);
    text(t.toUpperCase(), x + 3, y + 2, '#fff');
    return w;
  }
  function drawSprite(key, unique, x, y, size, flip = false, sil = false) {
    const img = sil ? window.SPRITES.getSilhouette(key) : window.SPRITES.getSprite(key, unique);
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    if (flip) { ctx.translate(x + size, y); ctx.scale(-1, 1); ctx.drawImage(img, 0, 0, size, size); }
    else ctx.drawImage(img, x, y, size, size);
    ctx.restore();
  }

  const UI = (G.ui = { box: null, menu: null });

  // Show a message. Resolves when the player presses A.
  function say(str, opts = {}) {
    return new Promise((res) => {
      UI.box = { lines: wrap(str, SW - 24), shown: opts.instant ? 9999 : 0, res, wait: opts.wait || 0 };
    });
  }
  // Show a choice menu. Resolves with the picked index, or -1 when cancelled.
  function choose(options, o = {}) {
    return new Promise((res) => {
      UI.menu = {
        options, idx: o.start || 0, cols: o.cols || 1, res,
        cancel: o.cancel !== false, hidden: !!o.hidden,
        x: o.x, y: o.y, w: o.w, prompt: o.prompt ? wrap(o.prompt, (o.x != null ? o.x : SW) - 24) : null,
        onMove: o.onMove || null,
      };
    });
  }
  // Force-close whatever menu is open (used by debug tools).
  UI.forceMenu = (val) => { if (UI.menu) { const m = UI.menu; UI.menu = null; m.res(val); } };

  function updateUI(dt) {
    if (UI.box) {
      const b = UI.box;
      const total = b.lines.join('').length;
      b.shown += dt * (window.DEBUG.flags.fastText ? 2000 : 90);
      if (b.wait > 0) { b.wait -= dt; if (b.wait <= 0 && b.shown >= total) { UI.box = null; b.res(); } return; }
      if (consume('a') || consume('b')) {
        if (b.shown < total) b.shown = total;
        else { UI.box = null; b.res(); }
      }
      return;
    }
    if (UI.menu) {
      const m = UI.menu, n = m.options.length, c = m.cols;
      let moved = false;
      if (consume('down')) { if (m.idx + c < n) m.idx += c; else if (c === 1) m.idx = 0; moved = true; }
      if (consume('up')) { if (m.idx - c >= 0) m.idx -= c; else if (c === 1) m.idx = n - 1; moved = true; }
      if (c > 1 && consume('right')) { if (m.idx % c < c - 1 && m.idx + 1 < n) m.idx++; moved = true; }
      if (c > 1 && consume('left')) { if (m.idx % c > 0) m.idx--; moved = true; }
      if (moved && m.onMove) m.onMove(m.idx);
      if (consume('a')) { UI.menu = null; m.res(m.idx); }
      else if ((consume('b') || consume('start')) && m.cancel) { UI.menu = null; m.res(-1); }
      return;
    }
    if (UI.page && (consume('a') || consume('b') || consume('start'))) {
      const pg = UI.page;
      UI.page = null; G.overlay = null; pg.res();
    }
  }

  function drawUI() {
    if (UI.box) {
      box(4, SH - 48, SW - 8, 44);
      let left = Math.floor(UI.box.shown);
      UI.box.lines.slice(0, 3).forEach((ln, i) => {
        const part = ln.slice(0, Math.max(0, left));
        left -= ln.length;
        text(part, 12, SH - 40 + i * 12);
      });
      if (UI.box.shown >= UI.box.lines.join('').length && Math.floor(G.time * 3) % 2 && !UI.box.wait) {
        ctx.fillStyle = '#c03030'; ctx.fillRect(SW - 18, SH - 14, 5, 3); ctx.fillRect(SW - 17, SH - 11, 3, 2);
      }
    }
    if (UI.menu && !UI.menu.hidden) {
      const m = UI.menu;
      if (m.prompt) { box(4, SH - 48, SW - 8, 44); m.prompt.slice(0, 3).forEach((ln, i) => text(ln, 12, SH - 40 + i * 12)); }
      ctx.font = FONT;
      const colW = Math.max(...m.options.map((o) => ctx.measureText(String(o)).width)) + 18;
      const rows = Math.ceil(m.options.length / m.cols);
      const w = m.w || colW * m.cols + 12;
      const h = rows * 14 + 12;
      const x = m.x != null ? m.x : SW - w - 4;
      const y = m.y != null ? m.y : m.prompt ? SH - 50 - h : SH - h - 4;
      box(x, y, w, h);
      const cw = (w - 12) / m.cols;
      m.options.forEach((o, i) => {
        const cx = x + 8 + (i % m.cols) * cw, cy = y + 8 + Math.floor(i / m.cols) * 14;
        text(String(o), cx + 8, cy);
        if (i === m.idx) cursor(cx, cy);
      });
    }
  }

  // Show a custom full-screen page until A/B is pressed.
  function showPage(drawFn) {
    return new Promise((res) => {
      G.overlay = drawFn;
      UI.page = { res };
    });
  }

  Object.assign(G, { say, choose, text, box, hpBar, typeTag, drawSprite, wrap, cursor, showPage, SW, SH });

  // ---------------- save / load ----------------
  const saveKey = (v) => 'starRegionSave_' + v;
  function saveGame() {
    const s = G.state;
    s.pos = { x: G.player.x, y: G.player.y, dir: G.player.dir };
    try { localStorage.setItem(saveKey(G.version), JSON.stringify(s)); return true; } catch (e) { return false; }
  }
  function loadSave(v) {
    try { const raw = localStorage.getItem(saveKey(v)); return raw ? JSON.parse(raw) : null; } catch (e) { return null; }
  }
  function clearSave(v) { try { localStorage.removeItem(saveKey(v)); } catch (e) { /* ignore */ } }
  Object.assign(G, { saveGame, loadSave, clearSave, freshState });

  // ---------------- dex helpers ----------------
  G.markSeen = (key) => { G.state.dex.seen[key] = true; };
  G.markCaught = (key) => { G.state.dex.seen[key] = true; G.state.dex.caught[key] = true; };
  G.addMon = (mon) => {
    G.markCaught(mon.key);
    if (G.state.party.length < 6) { G.state.party.push(mon); return 'party'; }
    G.state.box.push(mon); return 'box';
  };
  G.healAll = () => { for (const m of G.state.party) { m.hp = m.maxhp; delete m.split; } };

  // ---------------- overworld ----------------
  function setVersionAssets() {
    G.playerSprites = window.SPRITES.makePlayer(G.version);
    G.buildingImgs = {};
    for (const b of G.map.buildings) {
      const id = b.kind + b.w + 'x' + b.h;
      if (!G.buildingImgs[id]) G.buildingImgs[id] = window.SPRITES.makeBuilding(b.kind, b.w, b.h, G.version);
    }
  }

  function placePlayer(x, y, dir = 'down') {
    Object.assign(G.player, { x, y, dir, moving: false, t: 0 });
    G.zoneBanner.zone = null;
  }
  G.placePlayer = placePlayer;

  const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

  function heldDir() {
    if (Input.lastDir && Input.held.has(Input.lastDir)) return Input.lastDir;
    for (const d of ['up', 'down', 'left', 'right']) if (Input.held.has(d)) return d;
    return null;
  }

  function updateOverworld(dt) {
    const p = G.player, D = window.DEBUG.flags;
    if (!p.moving) {
      if (consume('start')) { runScript(overworldMenu); return; }
      if (consume('a')) { const [dx, dy] = DIRS[p.dir]; interact(p.x + dx, p.y + dy); return; }
      const d = heldDir();
      if (d) {
        const [dx, dy] = DIRS[d];
        const nx = p.x + dx, ny = p.y + dy;
        if (p.dir !== d && !p.turnGrace) { p.dir = d; p.turnGrace = 0.08; return; }
        p.dir = d;
        const inBounds = nx >= 0 && ny >= 0 && nx < G.map.W && ny < G.map.H;
        if (inBounds && (D.noclip || !G.map.solid(nx, ny))) {
          p.moving = true; p.fx = p.x; p.fy = p.y; p.x = nx; p.y = ny; p.t = 0; p.stepFrame ^= 1;
        } else if (inBounds && G.map.doors[nx + ',' + ny] && consume('up')) {
          interact(nx, ny);
        }
      }
      if (p.turnGrace) { p.turnGrace -= dt; if (p.turnGrace <= 0 || !d) p.turnGrace = 0; }
    }
    if (p.moving) {
      const speed = (Input.held.has('b') ? 8.5 : 5.2) * (D.fastWalk ? 3 : 1);
      p.t += dt * speed;
      if (p.t >= 1) { p.t = 0; p.moving = false; onStep(); }
    }
    const zone = G.map.zoneAt(p.x, p.y);
    if (zone !== G.zoneBanner.zone) {
      G.zoneBanner = { zone, text: window.MAP.ZONES[zone].name, t: 2.2 };
    }
    if (G.zoneBanner.t > 0) G.zoneBanner.t -= dt;
  }

  function onStep() {
    const p = G.player, D = window.DEBUG.flags;
    G.state.steps++;
    if (G.map.get(p.x, p.y) === window.MAP.T.TALL && !D.noEncounters && !D.noclip) {
      if (Math.random() < D.encounterRate) runScript(() => window.BATTLE.wild(G.map.zoneAt(p.x, p.y)));
    }
  }

  function interact(x, y) {
    const key = x + ',' + y;
    if (G.map.signs[key]) { runScript(() => say(G.map.signs[key])); return; }
    const door = G.map.doors[key];
    if (!door) return;
    if (door.kind === 'center') {
      runScript(async () => {
        await say('Welcome to the Pokemon Center! Let me heal your team.');
        G.healAll();
        G.state.lastHeal = { x: G.player.x, y: G.player.y };
        saveGame();
        await say('Your Pokemon are fully healed. (Game saved.)');
      });
    } else if (door.kind === 'house') {
      runScript(() => say('Nobody is home. (Houses are coming later!)'));
    } else if (door.kind === 'shrine') {
      runScript(shrineEvent);
    }
  }

  async function shrineEvent() {
    if (G.state.legendDone) { await say('The shrine is quiet now.'); return; }
    const key = G.version === 'freeze' ? 'legend_freeze' : 'legend_flame';
    await say(G.version === 'freeze' ? 'A freezing wind blows out of the shrine...' : 'Scorching heat pours out of the shrine...');
    await say('Something is inside! (This legendary is a placeholder until it gets designed.)');
    const result = await window.BATTLE.start(makeMon(key, 40), { legendary: true });
    if (result === 'win' || result === 'caught') G.state.legendDone = true;
  }

  async function runScript(fn) {
    if (G.busy) return;
    G.busy = true;
    try { await fn(); } catch (e) { console.error(e); }
    G.busy = false;
    Input.pressed.clear();
  }
  G.runScript = runScript;

  function drawOverworld() {
    const p = G.player, map = G.map, T = window.MAP.T, tiles = G.tiles;
    const px = (p.moving ? p.fx + (p.x - p.fx) * p.t : p.x) * TS;
    const py = (p.moving ? p.fy + (p.y - p.fy) * p.t : p.y) * TS;
    let camX = Math.round(px - SW / 2 + TS / 2), camY = Math.round(py - SH / 2 + TS / 2);
    camX = Math.max(0, Math.min(map.W * TS - SW, camX));
    camY = Math.max(0, Math.min(map.H * TS - SH, camY));
    const f = Math.floor(G.time * 2) % 2;
    const x0 = Math.floor(camX / TS), y0 = Math.floor(camY / TS);
    for (let ty = y0; ty <= y0 + SH / TS + 1; ty++) {
      for (let tx = x0; tx <= x0 + SW / TS + 1; tx++) {
        const t = map.get(tx, ty);
        let img;
        switch (t) {
          case T.SEA: img = tiles.sea[f]; break;
          case T.WATER: img = tiles.water[f]; break;
          case T.TALL: img = tiles.tall; break;
          case T.PATH: img = tiles.path; break;
          case T.SAND: img = tiles.sand; break;
          case T.TREE: img = tiles.tree; break;
          case T.FLOWER: img = tiles.flower; break;
          case T.FLOOR: case T.BLD: case T.DOOR: img = tiles.floor; break;
          case T.SIGN: img = tiles.sign; break;
          default: img = tiles.grass;
        }
        ctx.drawImage(img, tx * TS - camX, ty * TS - camY);
      }
    }
    for (const b of map.buildings) {
      const bx = b.x * TS - camX, by = b.y * TS - camY;
      if (bx > SW || by > SH || bx + b.w * TS < 0 || by + b.h * TS < 0) continue;
      ctx.drawImage(G.buildingImgs[b.kind + b.w + 'x' + b.h], bx, by);
    }
    const frame = p.moving ? (p.t < 0.5 ? 1 + p.stepFrame : 0) : 0;
    const sx = Math.round(px - camX), sy = Math.round(py - camY) - 2;
    ctx.drawImage(G.playerSprites[p.dir][frame], sx, sy);
    if (map.get(p.x, p.y) === T.TALL && !(p.moving && p.t < 0.4)) ctx.drawImage(tiles.tallTop, p.x * TS - camX, p.y * TS - camY);

    window.DEBUG.drawWorld(ctx, camX, camY);

    if (G.zoneBanner.t > 0) {
      ctx.font = FONT;
      const w = ctx.measureText(G.zoneBanner.text).width + 16;
      const y = G.zoneBanner.t > 2 ? -20 + (2.2 - G.zoneBanner.t) * 100 : G.zoneBanner.t < 0.2 ? -20 + G.zoneBanner.t * 100 : 0;
      box(4, Math.round(4 + y), w, 18);
      text(G.zoneBanner.text, 12, Math.round(9 + y));
    }
  }

  // ---------------- menus ----------------
  async function overworldMenu() {
    for (;;) {
      const i = await choose(['POKEMON', 'POKEDEX', 'BAG', 'SAVE', 'EXIT'], { x: SW - 84, y: 4, w: 80 });
      if (i === 0) await partyMenu(false);
      else if (i === 1) await dexMenu();
      else if (i === 2) await bagMenu();
      else if (i === 3) { saveGame(); await say('Game saved.'); }
      else return;
    }
  }

  function drawPartyList(title, idx, party) {
    ctx.fillStyle = G.version === 'flame' ? '#5a2a1e' : '#1e3a5a';
    ctx.fillRect(0, 0, SW, SH);
    text(title, 8, 6, '#fff');
    party.forEach((m, i) => {
      const y = 18 + i * 28;
      box(4, y, SW - 8, 26, i === idx ? '#fff8c8' : '#fbfbf4');
      drawSprite(m.key, m.unique, 6, y + 1, 24);
      text((m.unique ? '*' : '') + monName(m).toUpperCase(), 34, y + 5);
      text('Lv' + m.level, 34, y + 15, '#555');
      hpBar(130, y + 7, 70, m.hp, m.maxhp);
      text(`${m.hp}/${m.maxhp}`, 204, y + 6, '#333');
      if (m.hp <= 0) text('FNT', 130, y + 15, '#c03030');
    });
  }

  // Lets the player pick a party member. Returns the index or -1.
  async function pickPartyMember(title, opts = {}) {
    const party = G.state.party;
    G.overlay = () => drawPartyList(title, UI.menu ? UI.menu.idx : -1, party);
    const i = await choose(party.map((m) => monName(m)), { hidden: true, cancel: opts.cancel !== false });
    G.overlay = null;
    return i;
  }
  G.pickPartyMember = pickPartyMember;

  async function partyMenu() {
    for (;;) {
      const i = await pickPartyMember('POKEMON  (A: select, B: back)');
      if (i < 0) return;
      G.overlay = () => drawPartyList('POKEMON', i, G.state.party);
      const c = await choose(['SUMMARY', 'MAKE LEAD', 'CANCEL'], { x: SW - 100, y: SH - 60, w: 96 });
      G.overlay = null;
      if (c === 0) await showPage(() => drawSummary(G.state.party[i]));
      if (c === 1) { const [m] = G.state.party.splice(i, 1); G.state.party.unshift(m); }
    }
  }

  function drawSummary(m) {
    const sp = SPECIES[m.key];
    ctx.fillStyle = '#f4f1e6'; ctx.fillRect(0, 0, SW, SH);
    drawSprite(m.key, m.unique, 4, 4, 96);
    text(`No.${String(sp.num).padStart(3, '0')}`, 104, 6, '#666');
    text((m.unique ? 'UNIQUE ' : '') + sp.name.toUpperCase(), 104, 18);
    text('Lv' + m.level, 104, 30);
    let tx = 104; for (const t of sp.types) tx += typeTag(t, tx, 42) + 3;
    text(`HP ${m.hp}/${m.maxhp}`, 104, 58);
    const st = m.stats;
    const rows = [['ATK', st.atk], ['DEF', st.def], ['SP.ATK', st.spa], ['SP.DEF', st.spd], ['SPEED', st.spe]];
    rows.forEach(([k, v], j) => { text(k, 104, 70 + j * 10, '#555'); text(String(v), 200, 70 + j * 10); });
    text('MOVES', 8, 108, '#555');
    m.moves.forEach((mk, j) => {
      const mv = MOVES[mk];
      typeTag(mv.type, 8, 120 + j * 13);
      text(mv.name.toUpperCase() + (mv.sig ? ' *' : ''), 70, 122 + j * 13);
      if (mv.power) text(String(mv.power), 226, 122 + j * 13, '#555');
    });
    const need = window.DATA.expFor(m.level + 1) - m.exp;
    text(`EXP to next: ${Math.max(0, need)}`, 8, 176, '#555');
  }

  async function dexMenu() {
    const list = ORDER.filter((k) => !SPECIES[k].legendary || SPECIES[k].version === G.version);
    const names = list.map((k) => k);
    let top = 0;
    const draw = () => {
      const idx = UI.menu ? UI.menu.idx : 0;
      if (idx < top) top = idx; if (idx > top + 10) top = idx - 10;
      ctx.fillStyle = G.version === 'flame' ? '#7a2a1a' : '#1a4a7a'; ctx.fillRect(0, 0, SW, SH);
      const seenN = Object.keys(G.state.dex.seen).length, caughtN = Object.keys(G.state.dex.caught).length;
      text(`POKEDEX  seen ${seenN}  caught ${caughtN}`, 6, 5, '#fff');
      box(4, 16, 148, SH - 20);
      for (let r = 0; r < 11 && top + r < list.length; r++) {
        const k = list[top + r], sp = SPECIES[k];
        const known = G.state.dex.seen[k] || window.DEBUG.flags.revealDex;
        const y = 22 + r * 14;
        text(`${String(sp.num).padStart(3, '0')} ${known ? sp.name.toUpperCase().slice(0, 11) : '-----'}`, 18, y, known ? '#222' : '#888');
        if (G.state.dex.caught[k]) { ctx.fillStyle = '#d03030'; ctx.fillRect(142, y + 2, 4, 4); }
        if (top + r === idx) cursor(10, y);
      }
      const k = list[idx], known = G.state.dex.seen[k] || window.DEBUG.flags.revealDex;
      box(154, 16, 100, 100, '#e8f0f8');
      drawSprite(k, false, 156, 18, 96, false, !known);
      text('A: info', 160, 122, '#fff');
    };
    for (;;) {
      G.overlay = draw;
      const i = await choose(names, { hidden: true });
      G.overlay = null;
      if (i < 0) return;
      const k = list[i];
      if (!G.state.dex.seen[k] && !window.DEBUG.flags.revealDex) { await say('You have not seen this Pokemon yet.'); continue; }
      await showPage(() => drawDexEntry(k));
    }
  }

  function drawDexEntry(k) {
    const sp = SPECIES[k], b = sp.base;
    ctx.fillStyle = '#f4f1e6'; ctx.fillRect(0, 0, SW, SH);
    drawSprite(k, false, 4, 4, 96);
    text(`No.${String(sp.num).padStart(3, '0')}`, 104, 6, '#666');
    text(sp.name.toUpperCase(), 104, 18);
    let tx = 104; for (const t of sp.types) tx += typeTag(t, tx, 30) + 3;
    const rows = [['HP', b.hp], ['ATK', b.atk], ['DEF', b.def], ['SP.ATK', b.spa], ['SP.DEF', b.spd], ['SPEED', b.spe]];
    rows.forEach(([n, v], j) => {
      text(n, 104, 46 + j * 10, '#555');
      ctx.fillStyle = v >= 100 ? '#3ac04a' : v >= 60 ? '#f0c020' : '#e07040';
      ctx.fillRect(160, 47 + j * 10, Math.min(60, v * 0.3), 6);
      text(String(v), 224, 46 + j * 10);
    });
    const total = b.hp + b.atk + b.def + b.spa + b.spd + b.spe;
    text('TOTAL ' + total, 104, 108);
    let y = 122;
    if (sp.evo) { text(`Evolves into ${SPECIES[sp.evo[0]].name} at Lv${sp.evo[1]}`, 6, y, '#333'); y += 12; }
    if (sp.sig) {
      const mv = MOVES[sp.sig];
      for (const ln of wrap(`Signature: ${mv.name}. ${mv.desc}`, SW - 12)) { text(ln, 6, y, '#7a2a6a'); y += 10; }
    }
    for (const ln of wrap(sp.note, SW - 12)) { if (y > SH - 10) break; text(ln, 6, y, '#777'); y += 10; }
  }

  async function bagMenu() {
    for (;;) {
      const bag = G.state.bag;
      const i = await choose([`POTION x${bag.potions}`, `STAR BALL x${bag.balls}`, 'CLOSE'], { x: 96, y: 60, w: 156 });
      if (i === 0) {
        if (bag.potions <= 0) { await say('You have no Potions.'); continue; }
        const t = await pickPartyMember('Use a Potion on which Pokemon?');
        if (t < 0) continue;
        const m = G.state.party[t];
        if (m.hp <= 0 || m.hp >= m.maxhp) { await say('It would have no effect.'); continue; }
        const healed = Math.min(20, m.maxhp - m.hp);
        m.hp += healed; bag.potions--;
        await say(`${monName(m)} got back ${healed} HP.`);
      } else if (i === 1) await say('Star Balls are for catching wild Pokemon in battle.');
      else return;
    }
  }

  // ---------------- title + new game ----------------
  function drawTitle() {
    const idx = UI.menu ? UI.menu.idx : G.version === 'flame' ? 1 : 0;
    const flame = idx === 1;
    const g = ctx.createLinearGradient(0, 0, 0, SH);
    g.addColorStop(0, flame ? '#4a0e08' : '#06203f');
    g.addColorStop(1, flame ? '#e0602a' : '#5ab4ee');
    ctx.fillStyle = g; ctx.fillRect(0, 0, SW, SH);
    // star
    ctx.fillStyle = flame ? '#ffcf4a' : '#e6f8ff';
    ctx.beginPath();
    for (let k = 0; k < 10; k++) {
      const a = ((-90 + k * 36) * Math.PI) / 180 + Math.sin(G.time) * 0.05, r = k % 2 ? 16 : 36;
      ctx.lineTo(128 + Math.cos(a) * r, 52 + Math.sin(a) * r);
    }
    ctx.fill();
    text('STAR REGION', SW / 2, 96, '#fff', 'center');
    text(flame ? 'FLAME VERSION' : 'FREEZE VERSION', SW / 2, 110, flame ? '#ffd27a' : '#bff4ff', 'center');
    text('fan-made prototype', SW / 2, 178, 'rgba(255,255,255,0.6)', 'center');
    // a few particles: snow or embers
    for (let i = 0; i < 24; i++) {
      const s = window.SPRITES.hash(i, 7), t = (G.time * (0.1 + s * 0.15) + s) % 1;
      const x = (i * 37 + Math.sin(G.time + i) * 8) % SW;
      const y = flame ? SH - t * SH : t * SH;
      ctx.fillStyle = flame ? '#ffb040' : '#fff';
      ctx.fillRect(Math.round(x), Math.round(y), 2, 2);
    }
  }

  let starterIdx = 0;
  function drawStarter() {
    ctx.fillStyle = G.version === 'flame' ? '#3a1a14' : '#14283a'; ctx.fillRect(0, 0, SW, SH);
    text('Choose your partner!', SW / 2, 10, '#fff', 'center');
    const idx = UI.menu ? UI.menu.idx : starterIdx;
    STARTERS.forEach((k, i) => {
      const x = 8 + i * 82, y = 30;
      box(x, y, 76, 100, i === idx ? '#fff8c8' : '#e8e8e0');
      const bob = i === idx ? Math.round(Math.sin(G.time * 6) * 2) : 0;
      drawSprite(k, false, x + 14, y + 10 + bob, 48);
      typeTag(SPECIES[k].types[0], x + 14, y + 74);
    });
    if (!UI.box && UI.menu) {
      const k = STARTERS[idx];
      box(4, SH - 48, SW - 8, 44);
      text(SPECIES[k].name.toUpperCase(), 12, SH - 40);
      text('Left/Right to look, A to pick', 12, SH - 24, '#666');
    }
  }

  async function titleFlow() {
    G.mode = 'title';
    const v = await choose(['FREEZE', 'FLAME'], { x: 64, y: 128, w: 128, cols: 2, cancel: false, start: G.version === 'flame' ? 1 : 0 });
    G.version = v === 1 ? 'flame' : 'freeze';
    setVersionAssets();
    const save = loadSave(G.version);
    if (save) {
      const c = await choose(['CONTINUE', 'NEW GAME'], { x: 64, y: 128, w: 128, cancel: false });
      if (c === 0) { startFromSave(save); return; }
    }
    await newGame();
  }

  function startFromSave(save) {
    G.state = save;
    for (const m of [...save.party, ...save.box]) window.DATA.calcStats(m);
    placePlayer(save.pos.x, save.pos.y, save.pos.dir);
    G.mode = 'overworld';
  }
  G.startFromSave = startFromSave;

  async function newGame() {
    G.state = freshState();
    G.mode = 'starter';
    await say(`Welcome to the Star Region! This is ${G.version === 'flame' ? 'FLAME' : 'FREEZE'} VERSION.`);
    await say('Before you head out, pick a partner Pokemon.');
    let pick = -1;
    while (pick < 0) {
      const i = await choose(STARTERS.map((k) => SPECIES[k].name), { hidden: true, cols: 3, cancel: false, start: starterIdx, onMove: (j) => { starterIdx = j; } });
      starterIdx = i;
      const sure = await choose(['YES', 'NO'], { prompt: `${SPECIES[STARTERS[i]].name}, the ${SPECIES[STARTERS[i]].types[0]} type. Is that your pick?`, cancel: false });
      if (sure === 0) pick = i;
    }
    G.addMon(makeMon(STARTERS[pick], 5));
    const city = G.map.towns[0];
    placePlayer(city.heal.x, city.heal.y, 'down');
    G.mode = 'overworld';
    await say(`You and ${SPECIES[STARTERS[pick]].name} set off! Wild Pokemon hide in the tall grass.`);
    await say('Arrows/WASD move, Z/Enter = A, X = B (hold to run), Esc = menu, ` = debug panel.');
    saveGame();
  }
  G.newGame = newGame;
  G.titleFlow = titleFlow;
  G.setVersionAssets = setVersionAssets;

  // ---------------- main loop ----------------
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    G.time += dt;
    window.DEBUG.tick(dt);

    if (UI.box || UI.menu || UI.page) updateUI(dt);
    else if (G.mode === 'overworld' && !G.busy && !G.overlay) updateOverworld(dt);
    if (G.mode === 'battle') window.BATTLE.update(dt);

    ctx.imageSmoothingEnabled = false;
    if (G.mode === 'title') drawTitle();
    else if (G.mode === 'starter') drawStarter();
    else if (G.mode === 'overworld') drawOverworld();
    else if (G.mode === 'battle') window.BATTLE.draw(ctx);
    else { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, SW, SH); text('Loading...', 8, 8, '#fff'); }
    if (G.overlay) G.overlay(ctx);
    drawUI();
    window.DEBUG.drawHud(ctx);

    Input.pressed.clear();
    requestAnimationFrame(frame);
  }

  function resize() {
    const pad = document.getElementById('pad');
    const padH = getComputedStyle(pad).display === 'none' ? 0 : pad.offsetHeight;
    const availW = window.innerWidth - 8, availH = window.innerHeight - padH - 8;
    let s = Math.min(availW / SW, availH / SH);
    if (s >= 2) s = Math.floor(s);
    canvas.style.width = Math.floor(SW * s) + 'px';
    canvas.style.height = Math.floor(SH * s) + 'px';
  }
  window.addEventListener('resize', resize);

  async function boot() {
    resize();
    G.map = window.MAP.build();
    G.tiles = window.SPRITES.makeTiles();
    setVersionAssets();
    try { await Promise.race([document.fonts.load(FONT), new Promise((r) => setTimeout(r, 2500))]); } catch (e) { /* use fallback font */ }
    window.DEBUG.init();
    requestAnimationFrame(frame);
    runScript(titleFlow);
  }
  boot();
})();
