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
      // fire hero: flame hair, sun on its chest, arms out
      const skin = '#ffd7a0', skinDk = '#e0a068', dk = '#9a2a14', rd = '#d63a24', or = '#f0802e', orLt = '#ffa858', ye = '#ffd84a', pl = '#fff2a0';
      // flame hair, three layers
      p.poly([[12, 14], [10, 3], [15, 8], [16, 0], [21, 6], [24, 0], [27, 6], [32, 0], [33, 8], [38, 3], [36, 14]], rd);
      p.poly([[14, 13], [14, 6], [18, 9], [20, 3], [23, 8], [26, 3], [28, 8], [31, 4], [32, 9], [35, 6], [34, 13]], or);
      p.poly([[17, 12], [19, 6], [22, 9], [24, 5], [26, 9], [29, 6], [31, 12]], ye);
      // legs with flame boots
      p.line(21, 34, 16, 43, or, 4); p.line(27, 34, 32, 43, or, 4);
      p.line(20, 35, 16, 41, orLt); p.line(26, 35, 30, 41, orLt);
      p.poly([[11, 42], [19, 41], [19, 46], [10, 46]], rd); p.poly([[29, 41], [37, 42], [38, 46], [29, 46]], rd);
      p.px(12, 43, ye); p.px(36, 43, ye);
      // arms with cuffs and round hands
      p.line(19, 27, 9, 21, or, 4); p.line(29, 27, 39, 21, or, 4);
      p.line(19, 26, 10, 20, orLt); p.line(29, 26, 38, 20, orLt);
      p.rect(9, 20, 3, 4, rd); p.rect(36, 20, 3, 4, rd);
      p.ell3(6, 19, 3, 3, skinDk, skin, '#fff0d0'); p.ell3(42, 19, 3, 3, skinDk, skin, '#fff0d0');
      p.px(4, 17, skinDk); p.px(44, 17, skinDk);
      // torso with belt and sun emblem
      p.ell3(24, 29, 7, 7, dk, or, orLt);
      p.rect(18, 34, 13, 2, dk); p.rect(23, 34, 3, 2, ye);
      p.circ(24, 28, 3, ye); p.px(24, 28, pl);
      for (const [dx, dy] of [[0, -5], [5, 0], [0, 5], [-5, 0], [4, -4], [-4, -4], [4, 4], [-4, 4]]) p.px(24 + dx, 28 + dy, ye);
      // neck + head
      p.rect(22, 20, 5, 3, skinDk);
      p.ell3(24, 15, 7, 7, skinDk, skin, '#fff0d0');
      p.px(17, 15, skinDk); p.px(31, 15, skinDk);
      // face
      p.rect(20, 13, 3, 3, '#1a1010'); p.px(20, 13, '#fff');
      p.rect(26, 13, 3, 3, '#1a1010'); p.px(26, 13, '#fff');
      p.line(19, 11, 22, 11, dk); p.line(26, 11, 29, 11, dk);
      p.ell(18, 17, 1, 1, '#ff9a8a'); p.ell(30, 17, 1, 1, '#ff9a8a');
      p.poly([[21, 18], [28, 18], [26, 20], [23, 20]], '#7a1a10'); p.rect(22, 18, 5, 1, '#fff');
    },
    slimean(p) {
      const b = '#4a8fe0', l = '#9cc8ff', d = '#2a5ea8';
      p.ell(24, 30, 14, 12, b);
      p.ell(24, 30, 9, 8, l);
      p.ell(24, 31, 6, 5, b);
      p.circ(21, 26, 1, '#111'); p.circ(27, 26, 1, '#111');
      p.line(21, 33, 23, 35, d); p.line(23, 35, 25, 35, d); p.line(25, 35, 27, 33, d);
      p.rect(16, 23, 3, 2, '#fff');
    },
    slimarton(p) {
      const b = '#3d82d4', l = '#8cc0ff';
      for (const a of [-90, -18, 54, 126, 198]) {
        const rad = (a * Math.PI) / 180;
        for (let j = 1; j <= 4; j++) p.circ(24 + Math.cos(rad) * (8 + j * 3.6), 24 + Math.sin(rad) * (8 + j * 3.6), 2, j % 2 ? l : b);
      }
      p.circ(24, 24, 9, b);
      p.circ(24, 24, 6, l);
      p.circ(21, 22, 1, '#111'); p.circ(27, 22, 1, '#111');
      p.line(21, 27, 23, 28, '#111'); p.line(23, 28, 25, 28, '#111'); p.line(25, 28, 27, 27, '#111');
    },
    slimontoon(p) {
      const b = '#2f6fc4', l = '#7fb6ff';
      for (let k = 0; k < 8; k++) {
        const rad = (k * 45 * Math.PI) / 180 - Math.PI / 2;
        for (let j = 1; j <= 5; j++) p.circ(24 + Math.cos(rad) * (6 + j * 3.4), 24 + Math.sin(rad) * (6 + j * 3.4), 2, j % 2 ? l : b);
      }
      p.circ(24, 24, 8, b);
      p.circ(24, 24, 5, l);
      p.px(22, 22, '#111'); p.px(26, 22, '#111'); p.px(22, 21, '#111'); p.px(26, 21, '#111');
      p.line(22, 26, 26, 26, '#111');
    },
    peeplet(p) {
      const t = '#d9a35b', d = '#a8743a', c = '#fff2d8';
      p.line(32, 29, 40, 24, d, 2); p.line(32, 31, 40, 28, d, 2);   // tail
      p.line(22, 36, 21, 42, '#e0a020'); p.line(27, 36, 28, 42, '#e0a020');
      p.ell(25, 30, 9, 7, t);
      p.ell(24, 32, 5, 4, c);
      p.ell(28, 29, 5, 3, d);                                        // wing
      p.circ(16, 22, 5, t);
      p.poly([[11, 21], [6, 23], [11, 25]], '#f0a020');
      p.px(15, 21, '#111');
    },
    featherdash(p) {
      // halfway to snowy: brown bird with frost creeping in
      const t = '#c98f4a', d = '#8c5a2a', c = '#f6e6c8', snow = '#f4fbff', ice = '#9fdcf4';
      p.line(30, 28, 44, 30, d, 3);
      p.line(36, 29, 44, 30, snow, 1);
      for (const [x, y] of [[38, 26], [43, 32], [37, 34]]) { p.circ(x, y, 3, ice); p.circ(x, y, 1, '#2a6ac0'); }
      p.line(19, 33, 18, 42, '#e0a020'); p.line(25, 33, 26, 42, '#e0a020');
      p.rect(15, 42, 4, 1, '#e0a020'); p.rect(25, 42, 4, 1, '#e0a020');
      p.ell(23, 27, 11, 7, t);
      p.ell(22, 29, 6, 4, c);
      p.ell(27, 26, 6, 3, d);
      p.ell(29, 24, 4, 2, snow);                      // snow settling on the back
      p.rect(31, 26, 3, 1, snow);
      p.circ(12, 19, 5, t);
      p.ell(12, 15, 4, 2, snow);                      // frosty cap
      // red scarf, tail fluttering back over the body
      p.poly([[16, 22], [27, 18], [29, 21], [18, 26]], '#c8202a');
      p.poly([[25, 19], [30, 16], [31, 19], [28, 21]], '#c8202a');
      p.poly([[7, 22], [17, 21], [18, 25], [8, 26]], '#e0303a');
      p.rect(8, 23, 10, 1, '#ff6a6a'); p.rect(9, 25, 9, 1, '#9a1820');
      p.poly([[8, 18], [1, 21], [8, 22]], '#f0a020');
      // slight snowflake eye: a normal dark eye with a faint frosty cross
      p.px(12, 17, '#9fdcf4'); p.px(12, 19, '#9fdcf4'); p.px(11, 18, '#9fdcf4'); p.px(13, 18, '#9fdcf4');
      p.px(12, 18, '#1c2a4a');
      p.px(18, 24, ice); p.px(20, 33, ice); p.px(33, 22, '#fff');
    },
    fiercebird(p) {
      // fully snowy
      const wing = '#bfe4f6', wingDk = '#7fbfe0', body = '#f4fbff', shade = '#d6ecf8', ye = '#f0b828', ice = '#7fd8ff';
      p.poly([[17, 22], [3, 6], [8, 18], [1, 20], [8, 26], [2, 32], [10, 33], [6, 40], [18, 34]], wingDk); // left wing
      p.poly([[16, 23], [6, 11], [10, 19], [5, 22], [10, 26], [6, 31], [12, 31], [17, 32]], wing);
      p.poly([[31, 22], [45, 6], [40, 18], [47, 20], [40, 26], [46, 32], [38, 33], [42, 40], [30, 34]], wingDk); // right wing
      p.poly([[32, 23], [42, 11], [38, 19], [43, 22], [38, 26], [42, 31], [36, 31], [31, 32]], wing);
      p.poly([[38, 22], [40, 25], [38, 28], [36, 25]], ice); p.px(38, 24, '#fff');         // ice crystals on the wing
      p.poly([[40, 28], [42, 31], [40, 34], [38, 31]], ice);
      p.poly([[19, 38], [24, 46], [29, 38]], wingDk);   // tail spikes
      p.ell(24, 30, 8, 10, body);
      p.ell(26, 33, 4, 6, shade);
      for (let i = 0; i < 4; i++) p.circ(24, 24 + i * 4, 1, ice); // necklace of ice beads
      p.line(20, 40, 18, 45, ye, 2); p.line(28, 40, 30, 45, ye, 2);
      p.circ(24, 13, 7, body);
      // red scarf with one end hanging down
      p.poly([[28, 20], [32, 21], [34, 31], [30, 31]], '#c8202a');
      p.rect(30, 31, 1, 2, '#c8202a'); p.rect(32, 31, 1, 2, '#c8202a'); p.rect(34, 31, 1, 1, '#c8202a');
      p.poly([[16, 18], [32, 18], [31, 23], [17, 23]], '#e0303a');
      p.rect(17, 19, 15, 1, '#ff6a6a'); p.rect(18, 22, 13, 1, '#9a1820');
      p.poly([[17, 13], [11, 16], [14, 18], [18, 16]], ye); // hooked beak
      p.circ(21, 13, 3, '#cfeeff'); p.flake5(21, 13, '#1e5ab8');   // snowflake eye
      p.line(18, 8, 25, 10, '#1c2a4a');                               // angry brow
      p.poly([[22, 6], [25, 0], [27, 7]], wing); p.poly([[27, 7], [32, 3], [30, 10]], wing); // frosty crest
    },
    legend_freeze(p) {
      p.poly([[24, 1], [36, 14], [46, 12], [40, 26], [46, 40], [32, 36], [24, 47], [16, 36], [2, 40], [8, 26], [2, 12], [12, 14]], '#2a4a6a');
      p.poly([[24, 8], [32, 18], [38, 18], [34, 26], [38, 35], [30, 32], [24, 40], [18, 32], [10, 35], [14, 26], [10, 18], [16, 18]], '#4d7da8');
      p.text('?', 24, 25, 22, '#bff4ff');
    },
    legend_flame(p) {
      p.poly([[24, 1], [30, 12], [38, 6], [38, 20], [46, 18], [42, 34], [36, 46], [12, 46], [6, 34], [2, 18], [10, 20], [10, 6], [18, 12]], '#5a1e14');
      p.poly([[24, 10], [29, 18], [34, 14], [34, 24], [39, 24], [36, 36], [31, 42], [17, 42], [12, 36], [9, 24], [14, 24], [14, 14], [19, 18]], '#9a3320');
      p.text('?', 24, 28, 22, '#ffd27a');
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
    const grassBase = (p) => {
      p.rect(0, 0, 16, 16, '#86cc62');
      for (let i = 0; i < 6; i++) { const x = Math.floor(hash(i, 3) * 15), y = Math.floor(hash(i, 9) * 14); p.px(x, y, '#6cb850'); p.px(x + 1, y + 1, '#6cb850'); }
    };
    T.grass = mk(grassBase);
    T.tall = mk((p) => {
      p.rect(0, 0, 16, 16, '#4fa846');
      for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) {
        const x = 1 + i * 4, y = 2 + j * 7;
        p.line(x, y + 5, x + 1, y, '#2f7a32'); p.line(x + 2, y + 5, x + 1, y + 1, '#3d9440'); p.px(x + 1, y, '#9ee07a');
      }
    });
    T.tallTop = mk((p) => { // drawn over the player's legs
      for (let i = 0; i < 4; i++) { const x = 1 + i * 4, y = 9; p.line(x, y + 5, x + 1, y, '#2f7a32'); p.line(x + 2, y + 5, x + 1, y + 1, '#3d9440'); p.px(x + 1, y, '#9ee07a'); p.rect(x - 1, 14, 4, 2, '#4fa846'); }
    });
    T.path = mk((p) => {
      p.rect(0, 0, 16, 16, '#dcc48e');
      for (let i = 0; i < 5; i++) p.px(Math.floor(hash(i, 21) * 16), Math.floor(hash(i, 22) * 16), '#c4aa72');
    });
    T.floor = mk((p) => {
      p.rect(0, 0, 16, 16, '#d6d0c0');
      p.rect(0, 0, 16, 1, '#c2bba8'); p.rect(0, 0, 1, 16, '#c2bba8');
    });
    T.sand = mk((p) => {
      p.rect(0, 0, 16, 16, '#ecd99a');
      for (let i = 0; i < 4; i++) p.px(Math.floor(hash(i, 31) * 16), Math.floor(hash(i, 32) * 16), '#d8c27e');
    });
    T.water = [0, 1].map((f) => mk((p) => {
      p.rect(0, 0, 16, 16, '#3f86d8');
      for (let i = 0; i < 3; i++) { const y = 3 + i * 5, x = (i * 5 + f * 4) % 12; p.rect(x, y, 4, 1, '#8cc4f4'); }
    }));
    T.sea = [0, 1].map((f) => mk((p) => {
      p.rect(0, 0, 16, 16, '#2a68b8');
      for (let i = 0; i < 2; i++) { const y = 4 + i * 8, x = (i * 7 + f * 5) % 12; p.rect(x, y, 5, 1, '#5f9ae0'); }
    }));
    T.tree = mk((p) => {
      grassBase(p);
      p.rect(7, 11, 3, 5, '#7a4a24');
      p.circ(8, 7, 6, '#2e7d3a'); p.circ(7, 6, 3, '#4a9e4a'); p.px(6, 4, '#7ccf6a');
      p.outline('#163d1e');
    });
    T.flower = mk((p) => {
      grassBase(p);
      for (const [x, y, c] of [[3, 4, '#ff7aa8'], [11, 6, '#fff07a'], [6, 11, '#ffffff'], [12, 12, '#ff7aa8']]) {
        p.px(x, y - 1, c); p.px(x - 1, y, c); p.px(x + 1, y, c); p.px(x, y + 1, c); p.px(x, y, '#e8a020');
      }
    });
    T.sign = mk((p) => {
      p.rect(0, 0, 16, 16, '#d6d0c0');
      p.rect(7, 9, 2, 6, '#6a4022'); p.rect(2, 3, 12, 7, '#a8743a'); p.rect(3, 4, 10, 5, '#c99a5a');
      p.rect(4, 5, 8, 1, '#6a4022'); p.rect(4, 7, 6, 1, '#6a4022');
    });
    return T;
  }

  // ---------- buildings ----------
  function makeBuilding(kind, w, h, version) {
    const p = new Painter(w * 16, h * 16);
    const W = w * 16, H = h * 16;
    if (kind === 'center') {
      p.rect(0, 20, W, H - 20, '#f4f0ea');
      p.rect(0, 0, W, 24, '#d8404a'); p.rect(0, 22, W, 3, '#a82a34');
      for (let x = 0; x < W; x += 6) p.rect(x, 2, 3, 18, '#e65a62');
      p.rect(W / 2 - 8, 4, 16, 14, '#fff'); p.rect(W / 2 - 2, 6, 4, 10, '#d8404a'); p.rect(W / 2 - 6, 9, 12, 4, '#d8404a');
      p.rect(8, 34, 14, 10, '#7cc4f0'); p.rect(W - 22, 34, 14, 10, '#7cc4f0');
      p.rect(W / 2 - 8, H - 18, 16, 18, '#7cc4f0'); p.rect(W / 2 - 1, H - 18, 2, 18, '#4a8ac0');
    } else if (kind === 'house') {
      const roof = version === 'flame' ? '#c8642a' : '#3a74c4';
      p.rect(0, 18, W, H - 18, '#efe2c8');
      p.poly([[-1, 22], [W / 2, 0], [W + 1, 22]], roof);
      p.rect(0, 18, W, 4, roof);
      p.rect(8, 28, 10, 8, '#7cc4f0');
      p.rect(W / 2 + 4, H - 16, 12, 16, '#8a5a34'); p.px(W / 2 + 13, H - 8, '#f0d060');
    } else if (kind === 'shrine') {
      const glow = version === 'flame' ? '#ff9a3a' : '#9ae8ff';
      p.poly([[0, H], [4, 10], [W / 2, 0], [W - 4, 10], [W, H]], '#7a7a8a');
      p.poly([[6, H], [8, 14], [W / 2, 6], [W - 8, 14], [W - 6, H]], '#9a9aaa');
      p.ell(W / 2, H - 6, 8, 12, '#14121e');
      p.rect(W / 2 - 8, H - 6, 16, 6, '#14121e');
      p.circ(W / 2, 12, 4, glow); p.px(W / 2, 12, '#fff');
    }
    p.outline();
    return p.c;
  }

  // ---------- player (16x16, 4 directions x 3 frames) ----------
  function makePlayer(version) {
    const cap = version === 'flame' ? '#d83a2a' : '#2a7ad8';
    const shirt = version === 'flame' ? '#f0a030' : '#5ad0e0';
    const out = {};
    for (const dir of ['down', 'up', 'left', 'right']) {
      out[dir] = [0, 1, 2].map((f) => {
        const p = new Painter(16, 16);
        const step = f === 1 ? 1 : f === 2 ? -1 : 0;
        // legs
        p.rect(5, 12 + (step > 0 ? -1 : 0), 2, 3, '#3a3a5a');
        p.rect(9, 12 + (step < 0 ? -1 : 0), 2, 3, '#3a3a5a');
        p.rect(4, 7, 8, 6, shirt);
        if (dir === 'left' || dir === 'right') {
          p.rect(dir === 'left' ? 7 : 6, 8, 3, 4, '#ffd7a0');
        } else {
          p.rect(3, 8, 1, 3, '#ffd7a0'); p.rect(12, 8, 1, 3, '#ffd7a0');
        }
        p.rect(4, 2, 8, 6, '#ffd7a0');
        p.rect(3, 1, 10, 3, cap);
        if (dir === 'down') { p.rect(3, 4, 10, 1, cap); p.px(6, 5, '#111'); p.px(9, 5, '#111'); }
        if (dir === 'up') p.rect(4, 4, 8, 3, '#5a3a22');
        if (dir === 'left') { p.rect(1, 3, 4, 1, cap); p.px(5, 5, '#111'); p.rect(9, 4, 3, 3, '#5a3a22'); }
        if (dir === 'right') { p.rect(11, 3, 4, 1, cap); p.px(10, 5, '#111'); p.rect(4, 4, 3, 3, '#5a3a22'); }
        p.outline();
        return p.c;
      });
    }
    return out;
  }

  function makeBall() {
    const p = new Painter(12, 12);
    p.circ(6, 6, 5, '#f4f4f4');
    p.rect(1, 1, 11, 5, '#e8c02a');
    p.rect(1, 6, 11, 1, '#1c1a2b');
    p.circ(6, 6, 1, '#fff');
    p.g.globalCompositeOperation = 'destination-in';
    p.circ(6, 6, 5, '#000');
    p.g.globalCompositeOperation = 'source-over';
    p.outline();
    return p.c;
  }

  window.SPRITES = { Painter, getSprite, getSilhouette, makeTiles, makeBuilding, makePlayer, makeBall, hash };
})();
