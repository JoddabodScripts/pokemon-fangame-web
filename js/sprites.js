'use strict';
// Pixel art drawn with code. Each Pokemon is a 48x48 sprite based on the notebook drawings.
(function () {
  const OUTLINE = '#1c1a2b';

  function canvas(w, h) {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    return c;
  }

  // Small pixel painter. Everything snaps to whole pixels.
  class Painter {
    constructor(w, h) {
      this.c = canvas(w, h);
      this.g = this.c.getContext('2d');
      this.w = w; this.h = h;
    }
    rect(x, y, w, h, col) { this.g.fillStyle = col; this.g.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h)); }
    px(x, y, col) { this.rect(x, y, 1, 1, col); }
    ell(cx, cy, rx, ry, col) {
      for (let y = -ry; y <= ry; y++) {
        for (let x = -rx; x <= rx; x++) {
          if ((x * x) / (rx * rx + 0.3) + (y * y) / (ry * ry + 0.3) <= 1) this.px(cx + x, cy + y, col);
        }
      }
    }
    circ(cx, cy, r, col) { this.ell(cx, cy, r, r, col); }
    // shaded ellipse: dark edge, base fill, light spot up-left
    ell3(cx, cy, rx, ry, dark, base, light) {
      this.ell(cx, cy, rx, ry, dark);
      this.ell(cx - 1, cy - 1, Math.max(1, rx - 1), Math.max(1, ry - 1), base);
      if (light) this.ell(cx - Math.ceil(rx / 3), cy - Math.ceil(ry / 3), Math.max(1, Math.floor(rx / 3)), Math.max(1, Math.floor(ry / 3)), light);
    }
    line(x0, y0, x1, y1, col, t = 1) {
      const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0), 1);
      for (let i = 0; i <= n; i++) {
        const x = x0 + ((x1 - x0) * i) / n, y = y0 + ((y1 - y0) * i) / n;
        this.rect(Math.round(x - (t - 1) / 2), Math.round(y - (t - 1) / 2), t, t, col);
      }
    }
    poly(pts, col) {
      // scanline fill, no antialiasing
      let minY = Infinity, maxY = -Infinity;
      for (const [, y] of pts) { minY = Math.min(minY, y); maxY = Math.max(maxY, y); }
      for (let y = Math.floor(minY); y <= Math.ceil(maxY); y++) {
        const xs = [];
        for (let i = 0; i < pts.length; i++) {
          const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
          const yc = y + 0.5;
          if ((y0 <= yc && y1 > yc) || (y1 <= yc && y0 > yc)) xs.push(x0 + ((yc - y0) / (y1 - y0)) * (x1 - x0));
        }
        xs.sort((a, b) => a - b);
        for (let i = 0; i + 1 < xs.length; i += 2) {
          const a = Math.round(xs[i]), b = Math.round(xs[i + 1]);
          if (b > a) this.rect(a, y, b - a, 1, col);
        }
      }
    }
    text(str, x, y, size, col) {
      // draw text then snap alpha so it stays crisp
      this.g.fillStyle = col;
      this.g.font = `bold ${size}px monospace`;
      this.g.textAlign = 'center';
      this.g.textBaseline = 'middle';
      this.g.fillText(str, x, y);
      this.snapAlpha();
    }
    snapAlpha() {
      const d = this.g.getImageData(0, 0, this.w, this.h);
      for (let i = 3; i < d.data.length; i += 4) d.data[i] = d.data[i] >= 110 ? 255 : 0;
      this.g.putImageData(d, 0, 0);
    }
    // 5x5 snowflake, used as an eye on the Ice birds
    flake5(cx, cy, col) {
      ['X.X.X', '.XXX.', 'XX.XX', '.XXX.', 'X.X.X'].forEach((row, j) => {
        for (let i = 0; i < 5; i++) if (row[i] === 'X') this.px(cx + i - 2, cy + j - 2, col);
      });
    }
    outline(col = OUTLINE) {
      const d = this.g.getImageData(0, 0, this.w, this.h);
      const a = d.data, w = this.w, h = this.h;
      const solid = (x, y) => x >= 0 && y >= 0 && x < w && y < h && a[(y * w + x) * 4 + 3] > 0;
      const add = [];
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        if (!solid(x, y) && (solid(x - 1, y) || solid(x + 1, y) || solid(x, y - 1) || solid(x, y + 1))) add.push([x, y]);
      }
      for (const [x, y] of add) this.px(x, y, col);
    }
  }

  // ---------- Pokemon sprites ----------
  // All face left (toward the player's side when shown as a wild Pokemon).
  const DRAW = {
    swampidile(p) {
      // long lizard-centipede with a sprout on its head
      const dk = '#1f5a2e', md = '#3f9a4a', bs = '#5cbf5a', lt = '#9ee07a', hl = '#d4f7a8', belly = '#e6e8a8';
      // far legs
      for (let i = 0; i < 6; i++) { const x = 9 + i * 5; p.line(x + 1, 30, x + 3, 36, dk); p.px(x + 4, 36, dk); }
      // curled tail
      p.circ(6, 27, 3, md); p.circ(4, 23, 2, md); p.circ(4, 20, 2, bs); p.circ(6, 18, 1, bs); p.px(7, 19, dk); p.px(5, 23, lt);
      // body segments, each shaded
      for (let i = 0; i < 6; i++) {
        const x = 10 + i * 5;
        p.ell3(x, 28, 4, 4, md, bs, lt);
        p.px(x - 1, 25, hl);                    // shine on each segment
        p.px(x + 3, 26, dk); p.px(x + 3, 27, dk); // groove between segments
      }
      p.rect(7, 31, 30, 2, belly); p.rect(7, 32, 30, 1, '#c8c880');
      for (let i = 0; i < 6; i++) p.px(9 + i * 5, 31, '#b8b870');
      // near legs
      for (let i = 0; i < 6; i++) { const x = 8 + i * 5; p.line(x, 32, x - 1, 37, md); p.px(x - 2, 37, dk); p.px(x, 37, dk); }
      // head
      p.ell3(40, 27, 6, 5, md, bs, lt);
      p.ell3(44, 28, 3, 3, md, bs, lt);
      p.px(46, 27, dk);                          // nostril
      p.line(40, 30, 46, 30, dk); p.px(39, 29, dk);
      p.px(43, 31, '#f09ab0');                   // little blush
      p.circ(39, 25, 2, '#fff'); p.rect(39, 24, 2, 3, '#1a1a1a'); p.px(40, 24, '#fff');
      // sprout with two veined leaves
      p.line(37, 22, 36, 15, dk);
      p.poly([[36, 15], [28, 11], [30, 15], [34, 17]], bs); p.line(36, 15, 30, 13, md); p.px(31, 12, hl);
      p.poly([[36, 15], [45, 10], [43, 14], [38, 17]], lt); p.line(36, 15, 43, 12, md); p.px(42, 11, hl);
    },
    swamporiaer(p) {
      // crocodile with a sunny spot on its side and a curled tail
      const dk = '#1d5233', md = '#2f8a46', bs = '#45a856', lt = '#7cc96e', hl = '#bfe8a0', belly = '#dbe3a0', bellyDk = '#b2bc78';
      // tail curling up
      const tail = [[38, 30, 4], [42, 27, 4], [45, 23, 3], [46, 19, 3], [45, 15, 2], [42, 13, 2], [40, 15, 1]];
      for (const [x, y, r] of tail) p.circ(x + 1, y + 1, r, dk);
      for (const [x, y, r] of tail) p.circ(x, y, r, bs);
      for (const [x, y, r] of tail.slice(0, 5)) p.px(x - r + 1, y - 1, lt);
      // far legs
      p.rect(33, 33, 4, 7, dk); p.rect(21, 33, 4, 7, dk);
      p.px(32, 40, '#e8e8d8'); p.px(20, 40, '#e8e8d8');
      // body
      p.ell3(27, 29, 13, 7, md, bs, lt);
      p.ell(27, 33, 11, 3, belly);
      for (let x = 18; x <= 36; x += 3) p.line(x, 31, x, 35, bellyDk);
      // scales and back ridges
      for (let x = 17; x <= 37; x += 4) { p.poly([[x, 23], [x + 2, 18], [x + 4, 23]], md); p.px(x + 2, 19, lt); }
      for (const [x, y] of [[20, 26], [24, 25], [34, 26], [37, 28], [22, 29]]) p.px(x, y, hl);
      // sunny marking
      p.circ(30, 27, 3, '#e8c838'); p.circ(30, 27, 2, '#f8e870'); p.px(29, 26, '#fffbd0'); p.px(31, 28, '#c8a020');
      // near legs with claws
      p.rect(16, 33, 5, 8, md); p.rect(16, 33, 2, 8, bs); p.px(15, 41, '#f4f4e8'); p.px(17, 41, '#f4f4e8'); p.px(19, 41, '#f4f4e8');
      p.rect(28, 34, 5, 7, md); p.rect(28, 34, 2, 7, bs); p.px(27, 41, '#f4f4e8'); p.px(29, 41, '#f4f4e8'); p.px(31, 41, '#f4f4e8');
      // head: long snout, closed toothy mouth
      p.poly([[1, 25], [5, 22], [19, 20], [21, 28], [2, 28]], bs);
      p.line(5, 22, 18, 21, lt); p.px(3, 23, dk); p.px(5, 23, dk);   // nostrils
      p.poly([[2, 29], [20, 29], [20, 34], [6, 33]], md);
      p.rect(3, 28, 17, 1, '#3a1a1a');
      for (let x = 4; x < 19; x += 2) { p.px(x, 27, '#fff'); p.px(x + 1, 29, '#fff'); }
      // eye on a brow bump
      p.ell3(15, 19, 3, 3, md, bs, lt);
      p.circ(15, 19, 2, '#f8e870'); p.rect(15, 18, 1, 3, '#111'); p.px(14, 18, '#fff');
      p.line(12, 16, 17, 17, dk);
    },
    swampest(p) {
      // big open-mouthed croc with a flower on its tail
      const dk = '#164a2a', md = '#267a40', bs = '#3a9a50', lt = '#6cbf66', hl = '#a8e08a', belly = '#d4dc98', bellyDk = '#a8b270';
      // tall tail/neck with the flower
      const neck = [[34, 30, 5], [38, 26, 4], [41, 22, 4], [42, 18, 3], [42, 14, 3], [41, 11, 2]];
      for (const [x, y, r] of neck) p.circ(x + 1, y + 1, r, dk);
      for (const [x, y, r] of neck) p.circ(x, y, r, bs);
      for (const [x, y, r] of neck) p.px(x - r + 1, y, lt);
      p.poly([[40, 11], [34, 8], [37, 12]], lt); p.poly([[42, 11], [47, 7], [45, 12]], md); // leaves
      const petal = '#f08ac0', petalDk = '#c8508a';
      for (let k = 0; k < 5; k++) { const a = (k * 72 - 90) * Math.PI / 180; p.circ(41 + Math.cos(a) * 3, 6 + Math.sin(a) * 3, 2, petal); p.px(41 + Math.cos(a) * 4, 6 + Math.sin(a) * 4, petalDk); }
      p.circ(41, 6, 1, '#ffd84a'); p.px(41, 6, '#f08a20');
      // far legs
      p.rect(35, 35, 5, 8, dk); p.rect(23, 36, 5, 8, dk);
      // body
      p.ell3(26, 32, 13, 8, md, bs, lt);
      p.ell(26, 37, 11, 3, belly);
      for (let x = 17; x <= 35; x += 3) p.line(x, 35, x, 39, bellyDk);
      for (let x = 17; x <= 35; x += 5) { p.poly([[x, 26], [x + 2, 20], [x + 4, 26]], md); p.px(x + 2, 21, hl); }
      for (const [x, y] of [[20, 29], [27, 28], [32, 30], [23, 32]]) p.px(x, y, hl);
      p.line(20, 40, 20, 43, md); p.line(29, 40, 29, 42, md); // hanging moss
      // near legs with claws
      p.rect(15, 36, 6, 9, md); p.rect(15, 36, 2, 9, bs);
      p.rect(28, 37, 6, 8, md); p.rect(28, 37, 2, 8, bs);
      for (const x of [14, 16, 18, 20, 27, 29, 31, 33]) p.px(x, x < 25 ? 45 : 45, '#f4f4e8');
      // open jaws
      p.poly([[0, 16], [6, 14], [19, 17], [20, 25], [1, 22]], bs);
      p.line(6, 15, 18, 17, lt); p.px(2, 17, dk); p.px(4, 17, dk);
      p.poly([[1, 23], [19, 25], [19, 33], [2, 32]], '#6a1424');       // mouth
      p.ell(10, 31, 6, 2, '#e06080'); p.line(6, 31, 14, 31, '#b8406a');  // tongue
      p.poly([[2, 33], [19, 32], [20, 38], [5, 38]], md);
      p.line(5, 37, 18, 37, dk);
      for (let x = 2; x < 18; x += 3) { p.poly([[x, 22], [x + 2, 23], [x + 1, 26]], '#fff'); p.poly([[x + 1, 33], [x + 3, 33], [x + 2, 30]], '#fff'); }
      // angry eye
      p.ell3(14, 15, 3, 3, md, bs, lt);
      p.circ(14, 15, 2, '#f8d040'); p.rect(14, 14, 1, 3, '#111'); p.px(13, 14, '#fff');
      p.line(11, 12, 17, 14, dk);
    },
    flamber(p) {
      // little flame egg with one big eye
      const dk = '#a8221a', rd = '#d8452a', or = '#f07a2a', ye = '#ffc83a', pl = '#fff2a0';
      // flame on top, three layers
      p.poly([[15, 22], [17, 10], [20, 15], [23, 3], [26, 13], [29, 7], [31, 15], [33, 22]], rd);
      p.poly([[18, 22], [20, 13], [22, 16], [24, 8], [26, 16], [28, 12], [30, 22]], or);
      p.poly([[21, 22], [23, 14], [25, 18], [27, 15], [27, 22]], ye);
      // stubby flame arms
      p.poly([[14, 29], [8, 26], [10, 30], [7, 33], [14, 33]], rd); p.px(10, 29, or);
      p.poly([[34, 29], [40, 26], [38, 30], [41, 33], [34, 33]], rd); p.px(38, 29, or);
      // body bands
      p.ell(24, 31, 10, 12, dk);
      p.ell(23, 30, 9, 11, rd);
      p.ell(23, 31, 7, 9, or);
      p.ell(24, 35, 5, 6, ye);
      p.ell(24, 37, 3, 3, pl);
      p.px(17, 25, '#ff9a6a'); p.px(16, 27, '#ff9a6a'); // rim light
      // big eye
      p.circ(24, 27, 5, '#fff');
      p.circ(24, 28, 3, '#e8a020'); p.circ(24, 28, 2, '#7a3a10'); p.circ(24, 28, 1, '#1a1010');
      p.px(22, 25, '#fff'); p.px(23, 25, '#fff'); p.px(26, 30, '#fff');
      p.line(19, 22, 21, 21, dk); p.line(27, 21, 29, 22, dk); // lash flicks
      // tiny smile
      p.px(22, 34, dk); p.px(23, 35, dk); p.px(24, 35, dk); p.px(25, 35, dk); p.px(26, 34, dk);
      // feet
      p.ell(19, 43, 3, 1, dk); p.ell(29, 43, 3, 1, dk); p.px(18, 42, rd); p.px(28, 42, rd);
      // floating embers
      p.px(8, 15, ye); p.px(40, 12, ye); p.px(38, 19, or); p.px(10, 20, or);
    },
    flamezion(p) {
      // a flame with a crown of fire and a big grin
      const dk = '#9a1c14', rd = '#d8381f', or = '#f0702a', ye = '#ffc83a', pl = '#fff2a0', cheek = '#ff7a6a';
      // crown: five flame spikes, layered
      p.poly([[9, 22], [10, 8], [15, 15], [18, 2], [22, 13], [24, 0], [26, 13], [30, 2], [33, 15], [38, 8], [39, 22]], rd);
      p.poly([[13, 21], [14, 12], [17, 16], [19, 7], [22, 16], [24, 6], [26, 16], [29, 7], [31, 16], [34, 12], [35, 21]], or);
      p.poly([[17, 21], [19, 13], [22, 18], [24, 12], [26, 18], [29, 13], [31, 21]], ye);
      p.px(24, 2, pl); p.px(18, 5, pl); p.px(30, 5, pl);
      // side wisps
      p.poly([[11, 30], [3, 24], [6, 31], [2, 35], [11, 36]], rd); p.poly([[10, 31], [6, 28], [8, 33], [10, 34]], or);
      p.poly([[37, 30], [45, 24], [42, 31], [46, 35], [37, 36]], rd); p.poly([[38, 31], [42, 28], [40, 33], [38, 34]], or);
      // body
      p.ell(24, 31, 13, 13, dk);
      p.ell(23, 30, 12, 12, rd);
      p.ell(23, 30, 10, 10, or);
      p.ell(24, 35, 7, 6, ye);
      p.ell(20, 24, 3, 2, '#ffa060');
      // flickering base instead of feet
      p.poly([[13, 40], [16, 47], [19, 42], [22, 47], [25, 42], [28, 47], [31, 42], [34, 47], [35, 40]], rd);
      p.poly([[17, 41], [19, 45], [22, 42], [25, 45], [28, 42], [31, 45], [32, 41]], or);
      // face
      p.ell(19, 27, 2, 3, '#1a1010'); p.ell(29, 27, 2, 3, '#1a1010');
      p.px(18, 26, '#fff'); p.px(28, 26, '#fff');
      p.ell(15, 32, 2, 1, cheek); p.ell(33, 32, 2, 1, cheek);
      p.poly([[18, 32], [30, 32], [27, 37], [21, 37]], '#5a1010');
      p.ell(24, 36, 3, 1, '#ff6a7a');
      p.px(19, 32, '#fff'); p.px(20, 33, '#fff'); p.px(29, 32, '#fff'); p.px(28, 33, '#fff'); // fangs
    },
    blazian(p) {
      // sun spirit: a mane of flames around its head, a sun on its chest, fireballs for hands
      const dk = '#8a1e10', rd = '#d63a24', or = '#f0782a', orLt = '#ffa858', ye = '#ffd84a', pl = '#fff4b8';
      const face = '#ffe6a8', faceDk = '#f0b860';
      // floating embers
      for (const [x, y, c] of [[3, 30, ye], [44, 32, or], [6, 40, or], [42, 41, ye], [40, 3, ye]]) p.px(x, y, c);
      // legs with flame feet
      p.line(21, 35, 17, 42, or, 4); p.line(27, 35, 31, 42, or, 4);
      p.line(20, 36, 17, 40, orLt); p.line(26, 36, 29, 40, orLt);
      p.poly([[12, 43], [15, 39], [19, 41], [21, 46], [12, 46]], rd); p.poly([[14, 45], [16, 41], [19, 43], [19, 46]], ye);
      p.poly([[27, 41], [33, 39], [36, 43], [36, 46], [27, 46]], rd); p.poly([[29, 46], [30, 43], [33, 41], [34, 46]], ye);
      // arms up and out, with flame bands
      p.line(19, 27, 10, 21, or, 4); p.line(29, 27, 38, 21, or, 4);
      p.line(18, 26, 11, 21, orLt); p.line(30, 26, 37, 21, orLt);
      p.line(14, 22, 15, 26, rd, 2); p.line(34, 22, 33, 26, rd, 2);
      // fireball hands
      for (const x of [6, 42]) { p.circ(x, 19, 5, rd); p.circ(x, 19, 4, or); p.circ(x, 19, 2, ye); p.px(x - 1, 18, pl); }
      p.poly([[3, 15], [5, 9], [7, 14]], or); p.poly([[41, 14], [43, 8], [45, 15]], or);
      // torso with the sun on its chest
      p.ell3(24, 30, 6, 7, dk, or, orLt);
      p.rect(19, 35, 11, 2, rd);
      p.circ(24, 29, 3, ye); p.px(24, 29, pl); p.px(23, 28, pl);
      for (const [dx, dy] of [[0, -5], [5, 0], [0, 5], [-5, 0], [4, -4], [-4, -4], [4, 4], [-4, 4]]) p.px(24 + dx, 29 + dy, ye);
      // flame mane all the way around the head, like the sun
      for (let k = 0; k < 12; k++) {
        const a = (k * 30 - 90) * Math.PI / 180, a1 = a - 0.26, a2 = a + 0.26;
        const r = k % 2 ? 11 : 14;
        p.poly([[24 + Math.cos(a1) * 6, 13 + Math.sin(a1) * 6], [24 + Math.cos(a) * r, 13 + Math.sin(a) * r], [24 + Math.cos(a2) * 6, 13 + Math.sin(a2) * 6]], k % 2 ? or : rd);
      }
      p.circ(24, 13, 9, or);
      p.circ(24, 13, 8, ye);
      // glowing face
      p.ell3(24, 14, 6, 6, faceDk, face, pl);
      p.poly([[17, 15], [19, 14], [19, 16]], rd); p.poly([[31, 15], [29, 14], [29, 16]], rd);   // flame cheek marks
      p.rect(20, 12, 3, 3, '#2a0a06'); p.px(21, 13, '#ff8a2a'); p.px(20, 12, '#ffffff');
      p.rect(26, 12, 3, 3, '#2a0a06'); p.px(27, 13, '#ff8a2a'); p.px(26, 12, '#ffffff');
      p.line(19, 10, 22, 11, dk); p.line(26, 11, 29, 10, dk);
      p.poly([[21, 17], [27, 17], [25, 19], [23, 19]], '#7a1a10'); p.px(22, 17, '#ffffff'); p.px(26, 17, '#ffffff');
    },
    slimean(p) {
      // round slime with a ring inside (from the notebook)
      const dk = '#1e4f9a', md = '#2f6fc4', bs = '#4a8fe0', lt = '#8cc0ff', hl = '#e8f4ff';
      p.ell(24, 42, 12, 2, md);                                   // puddle under it
      p.rect(14, 38, 3, 5, bs); p.rect(32, 39, 2, 4, bs);         // drips
      p.ell3(24, 30, 14, 12, dk, bs, lt);
      p.ell(24, 31, 9, 8, md);
      p.ell(24, 31, 8, 7, '#6aa8f0');
      p.ell(23, 30, 5, 4, '#7cb6f6');
      p.circ(18, 37, 1, '#b8d8ff'); p.px(31, 35, '#b8d8ff'); p.px(29, 38, '#b8d8ff'); // bubbles
      p.rect(13, 23, 2, 5, hl); p.rect(15, 21, 3, 1, hl); p.px(15, 22, hl);       // gloss
      p.ell(20, 28, 2, 3, '#0e1a3a'); p.ell(28, 28, 2, 3, '#0e1a3a');
      p.px(19, 27, '#fff'); p.px(27, 27, '#fff'); p.px(21, 30, '#4a6aa0'); p.px(29, 30, '#4a6aa0');
      p.line(21, 33, 23, 34, '#0e1a3a'); p.line(23, 34, 25, 34, '#0e1a3a'); p.line(25, 34, 27, 33, '#0e1a3a');
      p.ell(16, 32, 1, 1, '#ff9ac0'); p.ell(32, 32, 1, 1, '#ff9ac0');
    },
    slimarton(p) {
      // slime body with five beaded arms
      const dk = '#1a4a90', md = '#2a64b8', bs = '#3d82d4', lt = '#8cc0ff', hl = '#e8f4ff', alt = '#6aa8f0';
      for (const a of [-90, -18, 54, 126, 198]) {
        const rad = (a * Math.PI) / 180;
        for (let j = 4; j >= 1; j--) {
          const x = Math.round(24 + Math.cos(rad) * (8 + j * 3.6)), y = Math.round(25 + Math.sin(rad) * (8 + j * 3.6));
          const r = j === 1 ? 3 : 2;
          p.circ(x + 1, y + 1, r, dk); p.circ(x, y, r, j % 2 ? alt : bs); p.px(x - 1, y - 1, hl);
        }
      }
      p.ell3(24, 25, 9, 9, dk, bs, lt);
      p.ell(24, 26, 6, 6, md); p.ell(24, 26, 5, 5, alt);
      p.rect(17, 19, 1, 4, hl); p.px(18, 18, hl);
      p.ell(21, 24, 1, 2, '#0e1a3a'); p.ell(27, 24, 1, 2, '#0e1a3a'); p.px(21, 23, '#fff'); p.px(27, 23, '#fff');
      p.line(21, 28, 23, 29, '#0e1a3a'); p.line(23, 29, 25, 29, '#0e1a3a'); p.line(25, 29, 27, 28, '#0e1a3a');
      p.px(18, 27, '#ff9ac0'); p.px(30, 27, '#ff9ac0');
    },
    slimontoon(p) {
      // huge slime with eight beaded arms and a glowing core
      const dk = '#15407e', md = '#2458a8', bs = '#2f6fc4', lt = '#7fb6ff', hl = '#e8f4ff', alt = '#5a98e8', glow = '#bfe4ff';
      for (let k = 0; k < 8; k++) {
        const rad = (k * 45 * Math.PI) / 180 - Math.PI / 2;
        for (let j = 5; j >= 1; j--) {
          const d = 6 + j * 3.3, x = Math.round(24 + Math.cos(rad) * d), y = Math.round(24 + Math.sin(rad) * d);
          const r = j >= 5 ? 1 : 2;
          p.circ(x + 1, y + 1, r, dk); p.circ(x, y, r, j % 2 ? alt : bs); p.px(x - 1, y - 1, j === 3 ? glow : hl);
        }
      }
      p.ell3(24, 24, 8, 8, dk, bs, lt);
      p.ell(24, 25, 5, 5, md); p.ell(24, 25, 4, 4, alt); p.circ(24, 26, 2, glow);
      p.rect(18, 19, 1, 3, hl);
      p.line(19, 20, 22, 21, '#0e1a3a'); p.line(26, 21, 29, 20, '#0e1a3a');      // stern brows
      p.rect(20, 22, 2, 2, '#0e1a3a'); p.rect(26, 22, 2, 2, '#0e1a3a'); p.px(20, 22, '#fff'); p.px(26, 22, '#fff');
      p.line(22, 27, 26, 27, '#0e1a3a');
    },
    peeplet(p) {
      // small brown songbird
      const t = '#d9a35b', td = '#a8743a', tdd = '#7a5228', tl = '#f0c888', c = '#fff2d8', cd = '#e8d0a8';
      p.poly([[31, 27], [41, 21], [43, 24], [38, 28], [43, 29], [41, 33], [31, 31]], td);   // tail
      p.line(33, 28, 40, 24, tdd); p.line(33, 30, 40, 30, tdd);
      p.line(22, 35, 21, 41, '#d08a10'); p.line(27, 35, 28, 41, '#d08a10');
      p.rect(18, 42, 4, 1, '#d08a10'); p.rect(27, 42, 4, 1, '#d08a10');
      p.ell3(25, 30, 9, 7, td, t, tl);
      p.ell(23, 33, 5, 3, c); p.line(19, 35, 27, 35, cd);
      p.ell(28, 29, 6, 4, td);                                                       // wing
      p.poly([[30, 26], [35, 27], [33, 30]], tdd);
      p.line(24, 30, 32, 29, tdd); p.line(25, 32, 33, 31, tdd); p.px(26, 27, tl);
      p.ell3(16, 22, 5, 5, td, t, tl);
      p.line(17, 17, 18, 14, td); p.px(19, 14, td); p.px(16, 15, td);              // head tuft
      p.ell(15, 25, 1, 1, '#ff9a8a');
      p.poly([[11, 20], [5, 22], [11, 23]], '#f0a020'); p.poly([[11, 23], [6, 23], [11, 25]], '#c87810');
      p.rect(14, 19, 2, 2, '#111'); p.px(14, 19, '#fff');
    },
    featherdash(p) {
      // halfway to snowy: brown bird with frost creeping in, red scarf
      const t = '#c98f4a', td = '#8c5a2a', tdd = '#653e1c', tl = '#e8b878', c = '#f6e6c8', snow = '#f4fbff', snowSh = '#c8e4f4', ice = '#9fdcf4';
      // long tail with icy eye-spots
      p.poly([[30, 25], [45, 25], [47, 30], [45, 35], [30, 31]], td);
      p.poly([[31, 27], [44, 27], [45, 30], [31, 30]], t);
      p.line(33, 28, 44, 29, tdd);
      for (const [x, y] of [[38, 26], [43, 31], [37, 34]]) { p.circ(x + 1, y + 1, 3, '#5a9ac0'); p.circ(x, y, 3, ice); p.circ(x, y, 1, '#2a6ac0'); p.px(x - 1, y - 1, '#fff'); }
      // legs
      p.line(19, 33, 18, 42, '#d08a10'); p.line(25, 33, 26, 42, '#d08a10');
      p.rect(15, 42, 4, 1, '#d08a10'); p.rect(25, 42, 4, 1, '#d08a10');
      // body
      p.ell3(23, 27, 11, 7, td, t, tl);
      p.ell(21, 30, 6, 4, c); p.line(16, 33, 26, 33, '#e0c8a0');
      p.ell(27, 26, 6, 3, td); p.line(23, 27, 32, 26, tdd); p.line(24, 29, 33, 28, tdd);
      // snow settling on the back and wing
      p.ell(29, 23, 4, 2, snow); p.line(26, 25, 32, 25, snowSh); p.rect(31, 26, 3, 1, snow); p.px(33, 27, snow);
      // head with frosty cap
      p.ell3(12, 19, 5, 5, td, t, tl);
      p.ell(12, 15, 4, 2, snow); p.line(9, 16, 15, 16, snowSh); p.px(10, 14, '#fff');
      // red scarf, tail fluttering back
      p.poly([[16, 22], [27, 18], [29, 21], [18, 26]], '#b81c26');
      p.poly([[25, 19], [30, 16], [31, 19], [28, 21]], '#c8202a'); p.px(31, 17, '#9a1820');
      p.poly([[7, 22], [17, 21], [18, 25], [8, 26]], '#e0303a');
      p.rect(8, 23, 10, 1, '#ff6a6a'); p.rect(9, 25, 9, 1, '#9a1820');
      // beak
      p.poly([[8, 18], [1, 20], [8, 21]], '#f0a020'); p.poly([[8, 21], [2, 21], [8, 22]], '#c87810');
      // slight snowflake eye
      p.px(12, 17, '#9fdcf4'); p.px(12, 19, '#9fdcf4'); p.px(11, 18, '#9fdcf4'); p.px(13, 18, '#9fdcf4');
      p.px(12, 18, '#1c2a4a');
      p.px(18, 31, ice); p.px(35, 22, '#fff'); p.px(6, 13, '#fff');                 // frost sparkles
    },
    fiercebird(p) {
      // fully snowy eagle with a red scarf and snowflake eye
      const w3 = '#5f9fc8', w2 = '#8fc4e6', w1 = '#bfe4f6', w0 = '#e8f6ff', body = '#f4fbff', shade = '#d0e6f4', ye = '#f0b828', yeD = '#c08810', ice = '#7fd8ff';
      const wingL = [[17, 22], [3, 6], [8, 18], [1, 20], [8, 26], [2, 32], [10, 33], [6, 40], [18, 34]];
      const wingR = wingL.map(([x, y]) => [48 - x, y]);
      p.poly(wingL, w3); p.poly(wingR, w3);
      p.poly([[16, 23], [6, 11], [10, 19], [5, 22], [10, 26], [6, 31], [12, 31], [17, 32]], w2);
      p.poly([[32, 23], [42, 11], [38, 19], [43, 22], [38, 26], [42, 31], [36, 31], [31, 32]], w2);
      p.poly([[16, 24], [9, 16], [12, 21], [9, 24], [13, 27], [16, 29]], w1);
      p.poly([[32, 24], [39, 16], [36, 21], [39, 24], [35, 27], [32, 29]], w1);
      p.line(8, 18, 15, 25, w3); p.line(8, 26, 15, 28, w3); p.line(40, 18, 33, 25, w3); p.line(40, 26, 33, 28, w3);
      p.px(5, 9, w0); p.px(43, 9, w0); p.px(4, 21, w0); p.px(44, 21, w0);
      // ice crystals on the right wing
      p.poly([[38, 22], [40, 25], [38, 28], [36, 25]], ice); p.px(38, 24, '#fff'); p.px(39, 26, '#4ab0e0');
      p.poly([[40, 28], [42, 31], [40, 34], [38, 31]], ice); p.px(40, 30, '#fff');
      // tail
      p.poly([[19, 38], [21, 46], [24, 40], [27, 46], [29, 38]], w3); p.poly([[21, 39], [24, 44], [27, 39]], w2);
      // body
      p.ell3(24, 30, 8, 10, shade, body, '#ffffff');
      p.ell(27, 33, 4, 6, shade);
      for (let i = 0; i < 4; i++) { p.circ(24, 25 + i * 4, 1, ice); p.px(23, 24 + i * 4, '#fff'); }
      p.line(19, 30, 21, 31, shade); p.line(26, 36, 28, 35, shade);
      // talons
      p.line(20, 40, 18, 45, ye, 2); p.line(28, 40, 30, 45, ye, 2);
      p.px(16, 46, '#333'); p.px(18, 47, '#333'); p.px(31, 46, '#333'); p.px(29, 47, '#333');
      // head
      p.ell3(24, 13, 7, 7, shade, body, '#ffffff');
      p.poly([[22, 6], [25, 0], [27, 7]], w1); p.poly([[27, 7], [32, 3], [30, 10]], w1); p.px(25, 1, w0); // crest
      // red scarf with one end hanging down
      p.poly([[28, 20], [32, 21], [34, 31], [30, 31]], '#b81c26');
      p.rect(30, 31, 1, 2, '#b81c26'); p.rect(32, 31, 1, 2, '#b81c26'); p.rect(34, 31, 1, 1, '#b81c26');
      p.poly([[16, 18], [32, 18], [31, 23], [17, 23]], '#e0303a');
      p.rect(17, 19, 15, 1, '#ff6a6a'); p.rect(18, 22, 13, 1, '#9a1820');
      // hooked beak
      p.poly([[17, 12], [10, 15], [13, 18], [18, 16]], ye); p.poly([[13, 16], [10, 15], [12, 18]], yeD); p.px(15, 13, '#fff2a0');
      // snowflake eye + brow
      p.circ(21, 12, 3, '#cfeeff'); p.flake5(21, 12, '#1e5ab8');
      p.line(17, 8, 25, 10, '#1c2a4a');
    },
    legend_freeze(p) {
      // faceted ice crystal with a question mark (design not made yet)
      p.poly([[24, 1], [36, 14], [46, 12], [40, 26], [46, 40], [32, 36], [24, 47], [16, 36], [2, 40], [8, 26], [2, 12], [12, 14]], '#1e3a5a');
      p.poly([[24, 5], [34, 16], [42, 15], [37, 26], [42, 37], [31, 33], [24, 43], [17, 33], [6, 37], [11, 26], [6, 15], [14, 16]], '#3a6a98');
      // light facets on the left, dark on the right
      p.poly([[24, 5], [14, 16], [24, 24]], '#8fc8ee'); p.poly([[6, 15], [14, 16], [11, 26]], '#6aa8d8');
      p.poly([[24, 5], [34, 16], [24, 24]], '#4d7da8'); p.poly([[42, 15], [34, 16], [37, 26]], '#2a5580');
      p.poly([[11, 26], [6, 37], [17, 33]], '#6aa8d8'); p.poly([[37, 26], [42, 37], [31, 33]], '#2a5580');
      p.poly([[17, 33], [24, 43], [24, 30]], '#5a90c0'); p.poly([[31, 33], [24, 43], [24, 30]], '#2e6090');
      p.line(24, 5, 24, 43, '#bfe8ff');
      for (const [x, y] of [[24, 2], [3, 12], [45, 12], [3, 40], [45, 40]]) p.px(x, y, '#ffffff');
      p.circ(24, 24, 9, '#2a5580'); p.circ(24, 24, 8, '#3a6a98');
      p.text('?', 24, 25, 18, '#e0faff');
    },
    legend_flame(p) {
      // roaring fire shape with a question mark (design not made yet)
      p.poly([[24, 1], [30, 12], [38, 4], [38, 20], [46, 16], [42, 34], [36, 46], [12, 46], [6, 34], [2, 16], [10, 20], [10, 4], [18, 12]], '#5a160e');
      p.poly([[24, 6], [29, 15], [35, 10], [35, 22], [42, 20], [39, 33], [33, 43], [15, 43], [9, 33], [6, 20], [13, 22], [13, 10], [19, 15]], '#a82a18');
      p.poly([[24, 12], [28, 19], [32, 16], [32, 26], [37, 26], [35, 35], [30, 41], [18, 41], [13, 35], [11, 26], [16, 26], [16, 16], [20, 19]], '#e0581f');
      p.poly([[24, 20], [27, 25], [30, 24], [31, 32], [28, 39], [20, 39], [17, 32], [18, 24], [21, 25]], '#ffa030');
      p.ell(24, 34, 5, 5, '#ffd84a');
      for (const [x, y] of [[24, 2], [38, 5], [10, 5], [46, 17], [2, 17]]) p.px(x, y, '#ffe680');
      p.text('?', 24, 29, 18, '#fff6d0');
    },
  };

  const cache = {};
  function getSprite(key, unique) {
    const id = key + (unique ? '*' : '');
    if (cache[id]) return cache[id];
    const p = new Painter(48, 48);
    (DRAW[key] || DRAW.legend_freeze)(p);
    if (unique) {
      // Unique form: swap color channels so it looks clearly different
      const d = p.g.getImageData(0, 0, 48, 48);
      for (let i = 0; i < d.data.length; i += 4) {
        const r = d.data[i], g = d.data[i + 1], b = d.data[i + 2];
        d.data[i] = b; d.data[i + 1] = r; d.data[i + 2] = g;
      }
      p.g.putImageData(d, 0, 0);
    }
    p.outline();
    cache[id] = p.c;
    return p.c;
  }

  function getSilhouette(key) {
    const id = key + '#sil';
    if (cache[id]) return cache[id];
    const src = getSprite(key, false);
    const p = new Painter(48, 48);
    p.g.drawImage(src, 0, 0);
    p.g.globalCompositeOperation = 'source-in';
    p.rect(0, 0, 48, 48, '#3a3a50');
    cache[id] = p.c;
    return p.c;
  }

  // ---------- tiles (16x16) ----------
  function hash(x, y) { let h = (x * 374761393 + y * 668265263) | 0; h = (h ^ (h >>> 13)) * 1274126177; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }

  function makeTiles() {
    const T = {};
    const mk = (fn) => { const p = new Painter(16, 16); fn(p); return p.c; };
    const rnd = (s, i) => hash(s * 31 + i, s * 7 + i * 13);
    const grassBase = (p, s = 0) => {
      p.rect(0, 0, 16, 16, '#7cc65a');
      for (let i = 0; i < 16; i++) p.px(Math.floor(rnd(s, i) * 16), Math.floor(rnd(s, i + 50) * 16), '#6cb84e');
      for (let i = 0; i < 6; i++) p.px(Math.floor(rnd(s, i + 100) * 16), Math.floor(rnd(s, i + 150) * 16), '#94d874');
      for (let k = 0; k < 3; k++) {
        const x = 1 + Math.floor(rnd(s, k + 200) * 12), y = 3 + Math.floor(rnd(s, k + 250) * 11);
        p.px(x, y, '#4e9a3c'); p.px(x + 1, y - 1, '#5fae46'); p.px(x + 2, y, '#4e9a3c'); p.px(x + 1, y - 2, '#a8e488');
      }
    };
    T.grass = [0, 1, 2, 3].map((s) => mk((p) => grassBase(p, s)));
    const blades = (p, y0) => {
      for (let i = 0; i < 5; i++) {
        const x = 1 + i * 3 + (y0 > 4 ? 1 : 0);
        p.line(x, y0 + 6, x, y0 + 1, '#2a722e'); p.line(x + 1, y0 + 6, x + 2, y0, '#4fae46'); p.px(x + 2, y0, '#a8e488');
        p.line(x + 2, y0 + 6, x + 3, y0 + 3, '#3d9440');
      }
    };
    T.tall = mk((p) => {
      p.rect(0, 0, 16, 16, '#3a9238'); p.rect(0, 13, 16, 3, '#2c7a2e');
      blades(p, 1); blades(p, 8);
    });
    T.tallTop = mk((p) => { p.rect(0, 14, 16, 2, '#2c7a2e'); blades(p, 8); });
    T.path = [0, 1, 2].map((s) => mk((p) => {
      p.rect(0, 0, 16, 16, '#d8bf88');
      for (let i = 0; i < 14; i++) p.px(Math.floor(rnd(s + 9, i) * 16), Math.floor(rnd(s + 9, i + 40) * 16), '#c8ad74');
      for (let i = 0; i < 6; i++) p.px(Math.floor(rnd(s + 9, i + 80) * 16), Math.floor(rnd(s + 9, i + 120) * 16), '#e8d4a4');
      for (let k = 0; k < 2; k++) {
        const x = 1 + Math.floor(rnd(s + 9, k + 300) * 13), y = 1 + Math.floor(rnd(s + 9, k + 330) * 13);
        p.rect(x, y, 2, 1, '#f0e2bc'); p.rect(x, y + 1, 2, 1, '#a89060');
      }
    }));
    T.floor = mk((p) => {
      p.rect(0, 0, 16, 16, '#d2cbb8');
      for (const [y, off] of [[0, 0], [8, 4]]) {
        for (let x = -off; x < 16; x += 8) {
          p.rect(x, y, 8, 1, '#e4ddcc'); p.rect(x, y, 1, 8, '#e4ddcc');
          p.rect(x, y + 7, 8, 1, '#ada48e'); p.rect(x + 7, y, 1, 8, '#ada48e');
          p.px(x + 3, y + 3, '#c4bca6');
        }
      }
    });
    T.sand = [0, 1].map((s) => mk((p) => {
      p.rect(0, 0, 16, 16, '#ecd99a');
      for (let i = 0; i < 14; i++) p.px(Math.floor(rnd(s + 20, i) * 16), Math.floor(rnd(s + 20, i + 40) * 16), '#dcc584');
      for (let i = 0; i < 8; i++) p.px(Math.floor(rnd(s + 20, i + 80) * 16), Math.floor(rnd(s + 20, i + 120) * 16), '#f8eabc');
      if (s === 1) { p.px(10, 10, '#f4b8c0'); p.px(11, 10, '#f4b8c0'); p.px(10, 11, '#d88a9a'); }
    }));
    T.water = [0, 1].map((f) => mk((p) => {
      p.rect(0, 0, 16, 16, '#3f86d8');
      for (let i = 0; i < 10; i++) p.px(Math.floor(hash(i, 61) * 16), Math.floor(hash(i, 62) * 16), '#3678c8');
      for (let i = 0; i < 3; i++) {
        const y = 2 + i * 5, x = (i * 6 + f * 3) % 12;
        p.rect(x, y, 4, 1, '#7cb8f0'); p.px(x + 1, y - 1, '#cfe8ff');
      }
      p.px(f ? 12 : 4, f ? 4 : 12, '#ffffff');
    }));
    T.sea = [0, 1].map((f) => mk((p) => {
      p.rect(0, 0, 16, 16, '#2a68b8');
      for (let i = 0; i < 12; i++) p.px(Math.floor(hash(i, 71) * 16), Math.floor(hash(i, 72) * 16), '#245ca8');
      for (let i = 0; i < 2; i++) {
        const y = 4 + i * 8, x = (i * 7 + f * 4) % 11;
        p.px(x, y + 1, '#5f9ae0'); p.rect(x + 1, y, 3, 1, '#5f9ae0'); p.px(x + 4, y + 1, '#5f9ae0'); p.px(x + 2, y - 1, '#d8ecff');
      }
    }));
    T.tree = mk((p) => {
      grassBase(p, 5);
      p.ell(8, 14, 6, 1, '#5ea848');
      p.rect(7, 10, 3, 5, '#7a4a24'); p.rect(9, 10, 1, 5, '#5a3418'); p.px(7, 12, '#9a6a3a');
      p.circ(8, 7, 7, '#1d4e26');
      p.circ(7, 6, 6, '#2e7d3a');
      p.circ(5, 5, 3, '#3f9a46'); p.circ(10, 4, 2, '#3f9a46'); p.circ(10, 9, 2, '#3a8e42');
      p.px(4, 3, '#7ccf6a'); p.px(5, 3, '#7ccf6a'); p.px(9, 2, '#7ccf6a'); p.px(3, 6, '#5fb85a');
      p.px(12, 10, '#163d1e'); p.px(6, 11, '#163d1e');
    });
    T.flower = [0, 1].map((s) => mk((p) => {
      grassBase(p, s + 7);
      const cols = s ? ['#ffffff', '#8ab0ff', '#fff07a'] : ['#ff7aa8', '#fff07a', '#ff9a5a'];
      [[4, 5], [11, 7], [6, 12]].forEach(([x, y], i) => {
        p.line(x, y + 2, x, y + 4, '#3d8a34');
        const c = cols[i];
        p.px(x, y - 1, c); p.px(x - 1, y, c); p.px(x + 1, y, c); p.px(x, y + 1, c); p.px(x, y, '#e8a020');
        p.px(x + 1, y - 1, '#ffffff');
      });
    }));
    T.sign = mk((p) => {
      p.rect(0, 0, 16, 16, '#d2cbb8');
      p.ell(8, 15, 4, 1, '#ada48e');
      p.rect(7, 9, 2, 6, '#6a4022'); p.px(7, 10, '#8a5a32');
      p.rect(1, 2, 14, 8, '#5a3418'); p.rect(2, 3, 12, 6, '#c99a5a');
      p.rect(2, 3, 12, 1, '#dcb070'); p.rect(2, 5, 12, 1, '#b8884a');
      p.rect(4, 4, 8, 1, '#4a2a12'); p.rect(4, 6, 6, 1, '#4a2a12');
      p.px(2, 3, '#888'); p.px(13, 3, '#888');
    });
    return T;
  }

  // ---------- buildings ----------
  function makeBuilding(kind, w, h, version) {
    const W = w * 16, H = h * 16;
    const p = new Painter(W, H);
    if (kind === 'center') {
      p.rect(0, 22, W, H - 22, '#f4f0ea');
      for (let y = 26; y < H - 4; y += 4) p.rect(0, y, W, 1, '#e4ded4');
      p.rect(0, H - 4, W, 4, '#b8b0a0');
      for (let x = 0; x < W; x += 8) p.rect(x, H - 4, 1, 4, '#9a9282');
      // roof with shingle rows
      p.rect(0, 0, W, 24, '#d8404a');
      for (let y = 4; y < 22; y += 4) {
        p.rect(0, y, W, 1, '#b8303a');
        for (let x = (y / 4) % 2 ? 0 : 4; x < W; x += 8) p.px(x, y + 1, '#b8303a');
      }
      p.rect(0, 0, W, 2, '#ec6a72'); p.rect(0, 22, W, 3, '#8a2028');
      // emblem plate
      p.rect(W / 2 - 9, 4, 18, 14, '#7a2028'); p.rect(W / 2 - 8, 5, 16, 12, '#ffffff');
      p.rect(W / 2 - 2, 6, 4, 10, '#d8404a'); p.rect(W / 2 - 6, 9, 12, 4, '#d8404a'); p.px(W / 2 - 7, 6, '#e8e8f0');
      // windows
      for (const wx of [6, W - 22]) {
        p.rect(wx, 30, 16, 12, '#5a6a80'); p.rect(wx + 1, 31, 14, 10, '#8ccaf0');
        p.rect(wx + 8, 31, 1, 10, '#5a6a80'); p.line(wx + 2, 39, wx + 6, 32, '#d8f0ff');
        p.rect(wx - 1, 42, 18, 2, '#c8c0b0');
      }
      // sliding door with awning
      p.rect(W / 2 - 11, H - 24, 22, 4, '#d8404a');
      for (let x = W / 2 - 11; x < W / 2 + 11; x += 4) p.rect(x, H - 24, 2, 4, '#ffffff');
      p.rect(W / 2 - 9, H - 20, 18, 20, '#5a6a80'); p.rect(W / 2 - 8, H - 19, 16, 19, '#8ccaf0');
      p.rect(W / 2 - 1, H - 19, 2, 19, '#5a6a80'); p.line(W / 2 - 6, H - 4, W / 2 - 3, H - 16, '#d8f0ff');
    } else if (kind === 'house') {
      const roof = version === 'flame' ? '#c8642a' : '#3a74c4';
      const roofDk = version === 'flame' ? '#8a3a14' : '#24508a';
      const roofLt = version === 'flame' ? '#e88a4a' : '#5a98e0';
      // walls of planks
      p.rect(0, 18, W, H - 18, '#efe2c8');
      for (let y = 22; y < H - 3; y += 4) p.rect(0, y, W, 1, '#dccba8');
      p.rect(0, H - 3, W, 3, '#a8a090'); for (let x = 0; x < W; x += 6) p.px(x, H - 2, '#8a8270');
      // chimney
      p.rect(W - 18, 2, 7, 14, '#9a5a3a'); p.rect(W - 19, 1, 9, 2, '#7a4028');
      for (let y = 5; y < 14; y += 3) p.px(W - 16 + (y % 2), y, '#7a4028');
      // roof with shingles
      p.poly([[-1, 22], [W / 2, 0], [W + 1, 22]], roof);
      for (let y = 5; y < 21; y += 4) {
        const half = (y / 22) * (W / 2 + 1);
        p.line(W / 2 - half, y, W / 2 + half, y, roofDk);
      }
      p.poly([[-1, 22], [W / 2, 0], [W / 2, 4], [4, 21]], roofLt);
      for (let y = 5; y < 21; y += 4) { const half = (y / 22) * (W / 2 + 1); p.line(W / 2 - half, y, W / 2, y, roof); }
      p.rect(0, 20, W, 3, roofDk);
      // window with shutters and a flower box
      p.rect(6, 27, 3, 10, roof); p.rect(21, 27, 3, 10, roof);
      p.rect(9, 27, 12, 10, '#6a5a48'); p.rect(10, 28, 10, 8, '#8ccaf0');
      p.rect(14, 28, 1, 8, '#6a5a48'); p.rect(10, 31, 10, 1, '#6a5a48'); p.px(11, 29, '#d8f0ff');
      p.rect(8, 37, 14, 3, '#8a5a34');
      for (const [x, c] of [[10, '#ff6a8a'], [13, '#fff07a'], [16, '#ff6a8a'], [19, '#ffffff']]) { p.px(x, 36, c); p.px(x, 37, '#3d8a34'); }
      // door
      p.rect(W / 2 + 3, H - 18, 14, 18, '#5a3418'); p.rect(W / 2 + 4, H - 17, 12, 17, '#8a5a34');
      p.rect(W / 2 + 6, H - 15, 3, 5, '#7a4a28'); p.rect(W / 2 + 11, H - 15, 3, 5, '#7a4a28');
      p.rect(W / 2 + 6, H - 8, 3, 5, '#7a4a28'); p.rect(W / 2 + 11, H - 8, 3, 5, '#7a4a28');
      p.px(W / 2 + 14, H - 9, '#f0d060');
    } else if (kind === 'shrine') {
      const freeze = version !== 'flame';
      const glow = freeze ? '#9ae8ff' : '#ff9a3a', glowLt = freeze ? '#e8fbff' : '#ffe08a';
      p.poly([[0, H], [3, 10], [W / 2, 0], [W - 3, 10], [W, H]], '#5a5a6a');
      p.poly([[4, H], [6, 12], [W / 2, 4], [W / 2, H]], '#9a9aaa');
      p.poly([[W / 2, 4], [W - 6, 12], [W - 4, H], [W / 2, H]], '#7a7a8a');
      for (let y = 14; y < H; y += 6) p.line(4, y, W - 4, y, '#6a6a7a');
      for (let y = 14; y < H; y += 6) for (let x = (y / 6) % 2 ? 8 : 12; x < W - 6; x += 9) p.line(x, y, x, y + 5, '#6a6a7a');
      // moss
      p.ell(8, H - 3, 4, 2, '#4e8a3c'); p.ell(W - 9, H - 2, 3, 2, '#4e8a3c'); p.px(6, H - 6, '#6aa84e');
      // cave mouth
      p.ell(W / 2, H - 9, 10, 13, '#3a3848');
      p.ell(W / 2, H - 8, 8, 12, '#14121e'); p.rect(W / 2 - 8, H - 8, 16, 8, '#14121e');
      p.ell(W / 2, H - 5, 5, 6, '#0a0910');
      // glowing gem
      p.circ(W / 2, 11, 5, freeze ? '#4ab0e0' : '#d8501a');
      p.circ(W / 2, 11, 3, glow); p.px(W / 2 - 1, 10, glowLt); p.px(W / 2, 11, '#ffffff');
      if (freeze) {
        p.poly([[W / 2 - 6, 2], [W / 2, -1], [W / 2 + 6, 2], [W / 2 + 3, 4], [W / 2 - 3, 4]], '#f4fbff');   // snow cap
        for (const x of [W / 2 - 7, W / 2 - 3, W / 2 + 2, W / 2 + 6]) p.line(x, H - 21, x, H - 17 + (x % 3), '#bfe8ff');
      } else {
        for (const x of [5, W - 6]) { p.rect(x, H - 14, 2, 6, '#5a3418'); p.poly([[x - 1, H - 14], [x + 1, H - 21], [x + 3, H - 14]], '#ff8a2a'); p.px(x + 1, H - 16, '#ffe680'); }
        p.px(W / 2 - 9, H - 22, '#ffb040'); p.px(W / 2 + 10, H - 26, '#ffb040');
      }
    }
    p.outline();
    return p.c;
  }

  // ---------- player (16x16, 4 directions x 3 frames) ----------
  function makePlayer(version) {
    const flame = version === 'flame';
    const cap = flame ? '#d83a2a' : '#2a7ad8', capDk = flame ? '#9a2016' : '#1a4e94', capLt = flame ? '#ff7a5a' : '#6aaeff';
    const shirt = flame ? '#f0a030' : '#5ad0e0', shirtDk = flame ? '#c07018' : '#3a9ab0';
    const skin = '#ffd7a0', skinDk = '#e8b080', hair = '#5a3a22', pants = '#3a3a5a', pantsDk = '#2a2a40', shoe = '#2a2a3a', bag = '#c8783a', bagDk = '#8a4a1a';
    const make = (dir, f) => {
      const p = new Painter(16, 16);
      const lA = f === 1 ? -1 : 0, rA = f === 2 ? -1 : 0;   // which leg/arm is forward
      if (dir === 'down' || dir === 'up') {
        // legs + shoes
        p.rect(5, 12 + lA, 2, 3, pants); p.rect(9, 12 + rA, 2, 3, pants); p.px(10, 12 + rA, pantsDk);
        p.rect(5, 15 + lA, 2, 1, shoe); p.rect(9, 15 + rA, 2, 1, shoe);
        // body + arms
        p.rect(4, 8, 8, 4, shirt); p.rect(10, 8, 2, 4, shirtDk); p.rect(4, 11, 8, 1, shirtDk);
        p.rect(3, 8 + rA, 1, 3, shirtDk); p.rect(12, 8 + lA, 1, 3, shirtDk);
        p.px(3, 11 + rA, skin); p.px(12, 11 + lA, skin);
        // head
        p.rect(4, 2, 8, 6, skin); p.rect(11, 3, 1, 5, skinDk); p.rect(5, 7, 6, 1, skinDk);
        if (dir === 'down') {
          p.rect(4, 3, 1, 3, hair); p.rect(11, 3, 1, 3, hair);
          p.rect(3, 0, 10, 3, cap); p.rect(4, 0, 4, 1, capLt); p.rect(4, 3, 8, 1, capDk);
          p.rect(6, 4, 1, 2, '#1a1a1a'); p.rect(9, 4, 1, 2, '#1a1a1a');
          p.px(5, 6, '#ffa8a0'); p.px(10, 6, '#ffa8a0'); p.px(7, 6, skinDk); p.px(8, 6, skinDk);
          p.rect(6, 8, 4, 1, shirtDk);   // collar
        } else {
          p.rect(4, 2, 8, 5, hair); p.rect(3, 0, 10, 3, cap); p.rect(4, 0, 4, 1, capLt); p.rect(6, 2, 4, 1, capDk);
          p.rect(5, 8, 6, 4, bag); p.rect(5, 8, 6, 1, bagDk); p.px(7, 10, '#f0d060');   // backpack
        }
      } else {
        // facing left (right is mirrored below)
        const back = f === 1 ? -2 : f === 2 ? 1 : 0;
        p.rect(6, 12, 2, 3, pants); p.rect(8 + back, 12, 2, 3, pantsDk);
        p.rect(5 + (f === 1 ? -1 : 0), 15, 3, 1, shoe); p.rect(8 + back, 15, 3, 1, shoe);
        p.rect(5, 8, 7, 4, shirt); p.rect(5, 11, 7, 1, shirtDk);
        p.rect(9, 8, 3, 4, bag); p.rect(11, 8, 1, 4, bagDk);                       // backpack
        const arm = 7 + (f === 1 ? 1 : f === 2 ? -1 : 0);
        p.rect(arm, 8, 2, 3, shirtDk); p.px(arm, 11, skin);
        p.rect(5, 2, 7, 6, skin); p.rect(9, 3, 3, 4, hair); p.rect(6, 7, 5, 1, skinDk);
        p.rect(4, 0, 8, 3, cap); p.rect(5, 0, 3, 1, capLt); p.rect(1, 2, 5, 1, capDk);
        p.rect(6, 4, 1, 2, '#1a1a1a'); p.px(5, 6, '#ffa8a0'); p.px(4, 5, skinDk);
      }
      p.outline();
      return p.c;
    };
    const out = {};
    for (const dir of ['down', 'up', 'left']) out[dir] = [0, 1, 2].map((f) => make(dir, f));
    out.right = out.left.map((src) => {
      const c = canvas(16, 16), g = c.getContext('2d');
      g.translate(16, 0); g.scale(-1, 1); g.drawImage(src, 0, 0);
      return c;
    });
    return out;
  }

  function makeBall() {
    const p = new Painter(12, 12);
    p.circ(6, 6, 5, '#e8e8ee');
    p.rect(1, 1, 11, 5, '#e8c02a');
    p.rect(1, 1, 11, 1, '#f8e070'); p.rect(8, 7, 3, 3, '#c8c8d0');
    p.rect(1, 6, 11, 1, '#1c1a2b');
    p.circ(6, 6, 1, '#fff'); p.px(3, 3, '#fff8c0');
    p.g.globalCompositeOperation = 'destination-in';
    p.circ(6, 6, 5, '#000');
    p.g.globalCompositeOperation = 'source-over';
    p.outline();
    return p.c;
  }

  window.SPRITES = { Painter, getSprite, getSilhouette, makeTiles, makeBuilding, makePlayer, makeBall, hash };
})();
