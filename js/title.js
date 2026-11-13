'use strict';
// Animated title screen. Freeze has falling snow, icicles and frost. Flame has fire and rising embers.
(function () {
  const SW = 256, SH = 192;
  const hash = (a, b) => window.SPRITES.hash(a, b);
  const FONT_BIG = '16px "Press Start 2P", monospace';
  const FONT = '8px "Press Start 2P", monospace';

  function px(ctx, x, y, w, h, col) { ctx.fillStyle = col; ctx.fillRect(Math.round(x), Math.round(y), w, h); }

  function starPath(ctx, cx, cy, rOut, rIn, rot, wobble) {
    ctx.beginPath();
    for (let k = 0; k < 10; k++) {
      const a = ((-90 + k * 36) * Math.PI) / 180 + rot;
      const r = (k % 2 ? rIn : rOut) + (wobble ? wobble(k) : 0);
      ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
    }
    ctx.closePath();
  }

  function shadowText(ctx, str, x, y, font, col, shadow) {
    ctx.font = font; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    ctx.fillStyle = shadow;
    for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [2, 2]]) ctx.fillText(str, x + dx, y + dy);
    ctx.fillStyle = col; ctx.fillText(str, x, y);
  }

  // ---------------- Freeze ----------------
  function snowflake(ctx, x, y, size, col) {
    x = Math.round(x); y = Math.round(y);
    if (size === 1) { px(ctx, x, y, 1, 1, col); return; }
    if (size === 2) { px(ctx, x - 1, y, 3, 1, col); px(ctx, x, y - 1, 1, 3, col); return; }
    // classic 7x7 pixel snowflake
    const rows = ['...X...', '.X.X.X.', '..XXX..', 'XXX.XXX', '..XXX..', '.X.X.X.', '...X...'];
    rows.forEach((row, j) => { for (let i = 0; i < 7; i++) if (row[i] === 'X') px(ctx, x + i - 3, y + j - 3, 1, 1, col); });
  }

  const icicles = [];
  for (let x = 2; x < SW; x += 7 + Math.floor(hash(x, 1) * 6)) icicles.push({ x, w: 3 + Math.floor(hash(x, 2) * 3), len: 5 + Math.floor(hash(x, 3) * 16), drip: hash(x, 4) });

  function frostBranch(ctx, x, y, ang, len, depth) {
    if (depth <= 0 || len < 2) return;
    const x2 = x + Math.cos(ang) * len, y2 = y + Math.sin(ang) * len;
    const n = Math.ceil(len);
    for (let i = 0; i <= n; i++) px(ctx, x + ((x2 - x) * i) / n, y + ((y2 - y) * i) / n, 1, 1, 'rgba(225,248,255,0.55)');
    frostBranch(ctx, x + (x2 - x) * 0.5, y + (y2 - y) * 0.5, ang - 0.9, len * 0.45, depth - 1);
    frostBranch(ctx, x + (x2 - x) * 0.5, y + (y2 - y) * 0.5, ang + 0.9, len * 0.45, depth - 1);
    frostBranch(ctx, x2, y2, ang + (hash(depth, len | 0) - 0.5) * 0.6, len * 0.6, depth - 1);
  }

  function drawFreeze(ctx, t) {
    const g = ctx.createLinearGradient(0, 0, 0, SH);
    g.addColorStop(0, '#04112a'); g.addColorStop(0.55, '#123d6e'); g.addColorStop(1, '#5aaee8');
    ctx.fillStyle = g; ctx.fillRect(0, 0, SW, SH);

    // aurora
    for (let band = 0; band < 2; band++) {
      for (let x = 0; x < SW; x += 2) {
        const y = 26 + band * 14 + Math.sin(x * 0.03 + t * 0.6 + band * 2) * 8 + Math.sin(x * 0.011 - t * 0.3) * 6;
        const a = 0.12 + 0.08 * Math.sin(x * 0.05 + t + band);
        ctx.fillStyle = band ? `rgba(120,255,220,${a})` : `rgba(110,190,255,${a})`;
        ctx.fillRect(x, y, 2, 10 + band * 4);
      }
    }

    // back snow (small, slow)
    for (let i = 0; i < 40; i++) {
      const s = hash(i, 11), speed = 10 + s * 10;
      const y = (t * speed + s * SH * 3) % (SH + 10) - 5;
      const x = (hash(i, 12) * SW + Math.sin(t * 0.8 + i) * 6 + SW) % SW;
      snowflake(ctx, x, y, 1, 'rgba(255,255,255,0.6)');
    }

    // star: icy, with glints
    const sx = 128, sy = 50, rot = Math.sin(t * 0.7) * 0.06;
    ctx.fillStyle = 'rgba(160,230,255,0.25)'; starPath(ctx, sx, sy, 44, 20, rot); ctx.fill();
    ctx.fillStyle = '#bfefff'; starPath(ctx, sx, sy, 37, 16, rot); ctx.fill();
    ctx.fillStyle = '#eefbff'; starPath(ctx, sx, sy, 28, 12, rot); ctx.fill();
    ctx.strokeStyle = 'rgba(80,170,230,0.7)'; ctx.lineWidth = 1;
    for (let k = 0; k < 5; k++) {
      const a = ((-90 + k * 72) * Math.PI) / 180 + rot;
      ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(sx + Math.cos(a) * 26, sy + Math.sin(a) * 26); ctx.stroke();
    }
    const glint = Math.floor(t * 1.5) % 5, gp = (t * 1.5) % 1;
    if (gp < 0.6) {
      const a = ((-90 + glint * 72) * Math.PI) / 180 + rot;
      const gx = sx + Math.cos(a) * 37, gy = sy + Math.sin(a) * 37, L = Math.round(2 + Math.sin(gp * Math.PI / 0.6) * 4);
      px(ctx, gx - L, gy, L * 2 + 1, 1, '#fff'); px(ctx, gx, gy - L, 1, L * 2 + 1, '#fff');
    }

    // icicles along the top, with drips
    for (const ic of icicles) {
      for (let r = 0; r < ic.len; r++) {
        const w = Math.max(1, Math.round(ic.w * (1 - r / ic.len)));
        px(ctx, ic.x + Math.floor((ic.w - w) / 2), r, w, 1, r < 2 ? '#e8f8ff' : '#9fd8f0');
        if (w > 1) px(ctx, ic.x + Math.floor((ic.w - w) / 2), r, 1, 1, '#ffffff');
      }
      const cycle = (t * 0.35 + ic.drip) % 1;
      if (cycle > 0.75) {
        const dy = ic.len + ((cycle - 0.75) / 0.25) * 70;
        px(ctx, ic.x + Math.floor(ic.w / 2), dy, 1, 2, 'rgba(200,240,255,0.9)');
      }
    }
    px(ctx, 0, 0, SW, 2, '#e8f8ff');

    // snowdrift and frost in the corners
    ctx.fillStyle = '#e9f6ff';
    for (let x = 0; x < SW; x += 2) {
      const h = 12 + Math.sin(x * 0.045) * 5 + Math.sin(x * 0.13 + 1) * 2;
      ctx.fillRect(x, SH - h, 2, h);
    }
    ctx.fillStyle = '#c5e4f6';
    for (let x = 0; x < SW; x += 2) { const h = 12 + Math.sin(x * 0.045) * 5 + Math.sin(x * 0.13 + 1) * 2; ctx.fillRect(x, SH - h, 2, 1); }
    frostBranch(ctx, 0, SH - 8, -0.9, 30, 4);
    frostBranch(ctx, 2, SH - 30, -0.3, 24, 4);
    frostBranch(ctx, SW - 1, SH - 8, Math.PI + 0.9, 30, 4);
    frostBranch(ctx, SW - 3, SH - 30, Math.PI + 0.3, 24, 4);

    // front snow (big flakes, faster, drifting)
    for (let i = 0; i < 26; i++) {
      const s = hash(i, 21), speed = 22 + s * 22;
      const y = (t * speed + s * SH * 5) % (SH + 20) - 10;
      const x = (hash(i, 22) * SW + Math.sin(t * 1.3 + i * 1.7) * 10 + t * 6 + SW * 2) % SW;
      snowflake(ctx, x, y, i % 3 === 0 ? 3 : 2, '#ffffff');
    }

    shadowText(ctx, 'POKEMON', SW / 2, 96, FONT_BIG, '#ffffff', '#1d5a9e');
    shadowText(ctx, 'FREEZE VERSION', SW / 2, 116, FONT, '#bff4ff', '#0b2a50');
    shadowText(ctx, 'fan-made prototype', SW / 2, 182, FONT, '#5a8ab8', '#e9f6ff');
  }

  // ---------------- Flame ----------------
  function drawFlame(ctx, t) {
    const g = ctx.createLinearGradient(0, 0, 0, SH);
    g.addColorStop(0, '#1a0404'); g.addColorStop(0.5, '#5a140a'); g.addColorStop(1, '#c8401a');
    ctx.fillStyle = g; ctx.fillRect(0, 0, SW, SH);

    // heat glow from the bottom
    const glow = ctx.createRadialGradient(SW / 2, SH + 30, 10, SW / 2, SH + 30, 160);
    glow.addColorStop(0, `rgba(255,170,60,${0.45 + Math.sin(t * 7) * 0.05})`); glow.addColorStop(1, 'rgba(255,120,40,0)');
    ctx.fillStyle = glow; ctx.fillRect(0, 0, SW, SH);

    // far embers
    for (let i = 0; i < 30; i++) {
      const s = hash(i, 31), p = (t * (0.06 + s * 0.06) + s) % 1;
      const y = SH - p * (SH + 10);
      const x = (hash(i, 32) * SW + Math.sin(t * 1.5 + i) * 8 + SW) % SW;
      ctx.fillStyle = `rgba(255,140,60,${0.5 * (1 - p)})`;
      ctx.fillRect(Math.round(x), Math.round(y), 1, 1);
    }

    // star: burning, with a flickering halo
    const sx = 128, sy = 50, rot = Math.sin(t * 0.9) * 0.05;
    const flick = (k) => Math.sin(t * 13 + k * 2.1) * 2.5 + Math.sin(t * 7.7 + k) * 1.5;
    ctx.fillStyle = 'rgba(255,90,20,0.55)'; starPath(ctx, sx, sy, 47, 23, rot, (k) => flick(k) * 1.6); ctx.fill();
    ctx.fillStyle = '#ff8a2a'; starPath(ctx, sx, sy, 41, 19, rot, flick); ctx.fill();
    ctx.fillStyle = '#ffcf4a'; starPath(ctx, sx, sy, 34, 15, rot); ctx.fill();
    ctx.fillStyle = '#fff2b0'; starPath(ctx, sx, sy, 20, 9, rot); ctx.fill();
    // little flames licking off each point
    for (let k = 0; k < 5; k++) {
      const a = ((-90 + k * 72) * Math.PI) / 180 + rot;
      const tipX = sx + Math.cos(a) * 42, tipY = sy + Math.sin(a) * 42;
      const h = 9 + Math.round((Math.sin(t * 11 + k * 3) + 1) * 4);
      for (let r = 0; r < h; r++) {
        const w = Math.max(1, Math.round(6 * (1 - r / h)));
        px(ctx, tipX - Math.floor(w / 2) + Math.round(Math.sin(t * 9 + r + k) * 0.8), tipY - r, w, 1, r < h / 3 ? '#ff7a20' : r < (2 * h) / 3 ? '#ffb040' : '#ffe680');
      }
    }

    shadowText(ctx, 'POKEMON', SW / 2, 96, FONT_BIG, '#fff3c0', '#a01e0a');
    shadowText(ctx, 'FLAME VERSION', SW / 2, 116, FONT, '#ffd27a', '#3a0a04');

    // fire along the bottom, three layers
    const layers = [['#b8200c', 1.0], ['#f06418', 0.72], ['#ffc030', 0.46], ['#fff0a0', 0.22]];
    for (let x = 0; x < SW; x += 4) {
      const n = Math.sin(t * 3.1 + x * 0.15) * 9 + Math.sin(t * 5.7 + x * 0.37) * 6 + Math.sin(t * 9.3 + x * 0.71) * 3;
      const H = 44 + n * 1.3 + hash(x, Math.floor(t * 8)) * 8;
      for (const [col, f] of layers) {
        const h = Math.round((H * f) / 2) * 2;
        px(ctx, x, SH - h, 4, h, col);
      }
    }

    // near embers, bigger and brighter
    for (let i = 0; i < 22; i++) {
      const s = hash(i, 41), p = (t * (0.12 + s * 0.1) + s) % 1;
      const y = SH - 20 - p * (SH - 10);
      const x = (hash(i, 42) * SW + Math.sin(t * 2.3 + i * 1.3) * 12 + SW) % SW;
      const on = Math.sin(t * 20 + i * 5) > -0.6;
      if (!on) continue;
      ctx.fillStyle = p < 0.4 ? '#ffe680' : p < 0.7 ? '#ffa030' : `rgba(220,70,20,${1 - p})`;
      ctx.fillRect(Math.round(x), Math.round(y), 2, 2);
    }

    shadowText(ctx, 'fan-made prototype', SW / 2, 182, FONT, '#fff0c0', '#7a1a08');
  }

  function draw(ctx, flame, t) {
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    if (flame) drawFlame(ctx, t); else drawFreeze(ctx, t);
    ctx.restore();
  }

  window.TITLE = { draw };
})();
