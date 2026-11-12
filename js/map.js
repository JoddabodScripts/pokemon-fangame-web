'use strict';
// The Star Region: a 5-pointed star island with a town on each point and Star City in the middle.
(function () {
  const W = 160, H = 160, CX = 80, CY = 84, R_OUT = 76, R_IN = 34;
  const T = { SEA: 0, GRASS: 1, TALL: 2, PATH: 3, TREE: 4, WATER: 5, SAND: 6, FLOWER: 7, FLOOR: 8, SIGN: 9, BLD: 10, DOOR: 11 };
  const SOLID = new Set([T.SEA, T.TREE, T.WATER, T.SIGN, T.BLD, T.DOOR]);

  // Arm k points at angle -90 + 72k degrees (0 = top, then clockwise).
  const ARM_ANGLES = [-90, -18, 54, 126, 198];
  const TOWN_NAMES = ['Apex Town', 'Ember Point', 'Tidepool Town', 'Mossmire', 'Galecrest'];

  // Wild Pokemon per area: [speciesKey, weight]
  const ZONES = {
    center: { name: 'Star Fields',          lv: [2, 5],   mons: [['peeplet', 40], ['swampidile', 20], ['flamber', 20], ['slimean', 20]] },
    arm0:   { name: 'Route 1 (North)',      lv: [3, 7],   mons: [['swampidile', 45], ['peeplet', 35], ['slimean', 20]] },
    arm1:   { name: 'Route 2 (East)',       lv: [6, 11],  mons: [['flamber', 50], ['peeplet', 30], ['featherdash', 20]] },
    arm2:   { name: 'Route 3 (South-East)', lv: [10, 16], mons: [['slimean', 45], ['slimarton', 25], ['featherdash', 30]] },
    arm3:   { name: 'Route 4 (South-West)', lv: [14, 20], mons: [['swamporiaer', 35], ['flamezion', 30], ['slimarton', 35]] },
    arm4:   { name: 'Route 5 (West)',       lv: [18, 26], mons: [['featherdash', 40], ['swamporiaer', 20], ['flamezion', 20], ['fiercebird', 8], ['slimarton', 12]] },
  };

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const deg = (d) => (d * Math.PI) / 180;
  const starPts = [];
  for (let k = 0; k < 10; k++) {
    const a = deg(-90 + k * 36), r = k % 2 ? R_IN : R_OUT;
    starPts.push([CX + Math.cos(a) * r, CY + Math.sin(a) * r]);
  }
  function inStar(x, y) {
    let inside = false;
    for (let i = 0, j = starPts.length - 1; i < starPts.length; j = i++) {
      const [xi, yi] = starPts[i], [xj, yj] = starPts[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  function zoneAt(x, y) {
    const dx = x - CX, dy = y - CY;
    if (Math.hypot(dx, dy) < 27) return 'center';
    const a = (Math.atan2(dy, dx) * 180) / Math.PI;
    let best = 0, bestD = 999;
    ARM_ANGLES.forEach((arm, k) => {
      let d = Math.abs(((a - arm) % 360 + 540) % 360 - 180);
      if (d < bestD) { bestD = d; best = k; }
    });
    return 'arm' + best;
  }

  function build() {
    const rng = mulberry32(20261112);
    const tiles = new Uint8Array(W * H);
    const idx = (x, y) => y * W + x;
    const ok = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
    const get = (x, y) => (ok(x, y) ? tiles[idx(x, y)] : T.SEA);
    const set = (x, y, t) => { if (ok(x, y)) tiles[idx(x, y)] = t; };

    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) set(x, y, inStar(x + 0.5, y + 0.5) ? T.GRASS : T.SEA);
    // beach
    const beach = [];
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (get(x, y) !== T.GRASS) continue;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) if (get(x + dx, y + dy) === T.SEA) { beach.push([x, y]); break; }
    }
    for (const [x, y] of beach) set(x, y, T.SAND);

    const blob = (cx, cy, r, t, only) => {
      for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) {
        if (x * x + y * y > r * r + rng() * r) continue;
        const cur = get(cx + x, cy + y);
        if (only.includes(cur)) set(cx + x, cy + y, t);
      }
    };

    // towns
    const towns = [{ name: 'Star City', x: CX, y: CY, kind: 'city' }];
    ARM_ANGLES.forEach((a, k) => {
      towns.push({ name: TOWN_NAMES[k], x: Math.round(CX + Math.cos(deg(a)) * 50), y: Math.round(CY + Math.sin(deg(a)) * 50), kind: 'town', arm: k });
    });

    // paths from Star City to each town, and down to the shrine
    const pathLine = (x0, y0, x1, y1) => {
      const n = Math.ceil(Math.hypot(x1 - x0, y1 - y0));
      for (let i = 0; i <= n; i++) {
        const x = Math.round(x0 + ((x1 - x0) * i) / n), y = Math.round(y0 + ((y1 - y0) * i) / n);
        for (let oy = -1; oy <= 1; oy++) for (let ox = -1; ox <= 0; ox++) if (get(x + ox, y + oy) !== T.SEA) set(x + ox, y + oy, T.PATH);
      }
    };
    for (const t of towns.slice(1)) pathLine(CX, CY, t.x, t.y);
    const shrine = { x: CX - 1, y: CY + 20, w: 3, h: 3 };
    pathLine(CX, CY, CX, shrine.y - 1);

    // tall grass along each route, plus one patch on the path itself so you can't avoid it
    ARM_ANGLES.forEach((a) => {
      const ax = Math.cos(deg(a)), ay = Math.sin(deg(a));
      const px = -ay, py = ax;
      for (let s = 14; s <= 42; s += 4) {
        for (const side of [-1, 1]) {
          if (rng() < 0.25) continue;
          const off = side * (4 + rng() * 5);
          blob(Math.round(CX + ax * s + px * off), Math.round(CY + ay * s + py * off), 2 + Math.floor(rng() * 2), T.TALL, [T.GRASS]);
        }
      }
      blob(Math.round(CX + ax * 27), Math.round(CY + ay * 27), 3, T.TALL, [T.GRASS, T.PATH]);
    });
    for (let i = 0; i < 18; i++) {
      const a = rng() * Math.PI * 2, r = 16 + rng() * 14;
      blob(Math.round(CX + Math.cos(a) * r), Math.round(CY + Math.sin(a) * r), 2, T.TALL, [T.GRASS]);
    }

    const nearType = (x, y, r, types) => {
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) if (types.includes(get(x + dx, y + dy))) return true;
      return false;
    };
    const nearTown = (x, y, r) => towns.some((t) => Math.abs(t.x - x) <= r + 8 && Math.abs(t.y - y) <= r + 7) ||
      (Math.abs(x - (shrine.x + 1)) < r + 5 && Math.abs(y - (shrine.y + 1)) < r + 5);

    // ponds (south arms are wetter)
    for (let i = 0; i < 7; i++) {
      const arm = [2, 3, 2, 3, 0, 1, 4][i];
      const a = deg(ARM_ANGLES[arm]) + (rng() - 0.5) * 0.5, r = 22 + rng() * 18;
      const x = Math.round(CX + Math.cos(a) * r), y = Math.round(CY + Math.sin(a) * r);
      if (nearType(x, y, 5, [T.PATH]) || nearTown(x, y, 3)) continue;
      blob(x, y, 2 + Math.floor(rng() * 2), T.WATER, [T.GRASS, T.TALL]);
    }
    // forests
    for (let i = 0; i < 260; i++) {
      const x = Math.floor(rng() * W), y = Math.floor(rng() * H);
      if (get(x, y) !== T.GRASS || nearType(x, y, 3, [T.PATH]) || nearTown(x, y, 2)) continue;
      const r = 1 + Math.floor(rng() * 3);
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
        if (dx * dx + dy * dy > r * r) continue;
        if (get(x + dx, y + dy) === T.GRASS && !nearType(x + dx, y + dy, 2, [T.PATH])) set(x + dx, y + dy, T.TREE);
      }
    }
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (get(x, y) === T.GRASS && rng() < 0.025) set(x, y, T.FLOWER);

    // town plazas and buildings
    const buildings = [];
    const doors = {};
    const signs = {};
    const place = (kind, x, y, w, h, doorDx, info) => {
      buildings.push({ kind, x, y, w, h });
      for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) set(x + i, y + j, T.BLD);
      const dx = x + doorDx, dy = y + h - 1;
      set(dx, dy, T.DOOR);
      doors[dx + ',' + dy] = { kind, ...info };
    };
    for (const t of towns) {
      const hw = t.kind === 'city' ? 8 : 5, hh = t.kind === 'city' ? 6 : 4;
      for (let y = t.y - hh; y <= t.y + hh; y++) for (let x = t.x - hw; x <= t.x + hw; x++) if (get(x, y) !== T.SEA) set(x, y, T.FLOOR);
      if (t.kind === 'city') {
        place('center', t.x - 6, t.y - 5, 5, 4, 2, { town: t.name });
        place('house', t.x + 2, t.y - 5, 4, 3, 2, {});
        place('house', t.x + 2, t.y + 2, 4, 3, 2, {});
        t.heal = { x: t.x - 4, y: t.y - 1 };
        set(t.x - 2, t.y + 3, T.SIGN); signs[(t.x - 2) + ',' + (t.y + 3)] = `STAR CITY. The center of the Star Region. The shrine is to the south.`;
      } else {
        place('center', t.x - 5, t.y - 4, 5, 4, 2, { town: t.name });
        place('house', t.x + 1, t.y - 4, 4, 3, 2, {});
        t.heal = { x: t.x - 3, y: t.y };
        set(t.x - 1, t.y + 2, T.SIGN); signs[(t.x - 1) + ',' + (t.y + 2)] = `${t.name.toUpperCase()}. ${ZONES['arm' + t.arm].name} leads back to Star City.`;
      }
      t.spawn = { x: t.heal.x, y: t.heal.y };
    }
    // shrine for the version legendary
    for (let y = shrine.y - 2; y <= shrine.y + shrine.h + 2; y++) for (let x = shrine.x - 3; x <= shrine.x + shrine.w + 2; x++) {
      const cur = get(x, y);
      if (cur === T.TREE || cur === T.TALL || cur === T.WATER) set(x, y, T.GRASS);
    }
    place('shrine', shrine.x, shrine.y, shrine.w, shrine.h, 1, {});
    for (let x = shrine.x - 2; x <= shrine.x + shrine.w + 1; x++) set(x, shrine.y + shrine.h, T.PATH);
    for (let y = shrine.y - 1; y <= shrine.y + shrine.h; y++) { set(shrine.x - 2, y, T.PATH); }

    return {
      W, H, tiles, buildings, doors, signs, towns,
      shrineSpot: { x: shrine.x + 1, y: shrine.y + shrine.h },
      get, set,
      solid: (x, y) => SOLID.has(get(x, y)),
      zoneAt,
    };
  }

  window.MAP = { T, ZONES, build, inStar, zoneAt };
})();
