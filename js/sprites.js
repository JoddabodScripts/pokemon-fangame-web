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
      const g = '#5cb85a', d = '#2f7d3a', l = '#a6e08a';
      p.line(5, 30, 2, 24, g, 2); p.circ(3, 22, 2, g);              // curled tail
      for (let i = 0; i < 6; i++) {
        const x = 7 + i * 5;
        p.line(x, 31, x - 2, 37, d); p.line(x + 2, 31, x + 4, 37, d); // little legs
      }
      for (let i = 0; i < 6; i++) p.ell(7 + i * 5, 29, 3, 3, i % 2 ? g : '#4ea94d');
      p.rect(6, 31, 30, 1, l);
      p.ell(39, 28, 5, 4, g);                                        // head
      p.px(41, 27, '#111'); p.px(43, 30, d);
      p.line(38, 24, 38, 19, d); p.ell(36, 18, 2, 1, l); p.ell(40, 18, 2, 1, l); // sprout
    },
    swamporiaer(p) {
      const g = '#3f9a4a', d = '#24663a', l = '#8fd07a';
      p.line(40, 31, 45, 25, g, 3); p.line(45, 25, 44, 17, g, 3); p.circ(42, 15, 2, g); // tail curls up
      p.rect(19, 34, 3, 7, d); p.rect(31, 34, 3, 7, d); p.rect(25, 35, 3, 6, d); p.rect(37, 34, 3, 6, d);
      p.ell(28, 30, 13, 6, g);
      p.rect(18, 33, 22, 2, l);
      for (let i = 0; i < 6; i++) p.px(21 + i * 3, 23, d);          // back ridges
      p.poly([[3, 25], [18, 23], [18, 29], [3, 28]], g);            // upper jaw
      p.poly([[3, 30], [18, 30], [18, 34], [5, 33]], g);            // lower jaw
      for (let x = 4; x < 18; x += 2) { p.px(x, 29, '#fff'); p.px(x + 1, 30, '#fff'); }
      p.circ(15, 22, 2, '#fff'); p.px(15, 22, '#111');
      p.circ(19, 28, 2, '#e9e36a'); p.px(19, 28, '#7a6a20');        // round marking from drawing
    },
    swampest(p) {
      const g = '#2f8a46', d = '#1d5a30', l = '#7cc96e';
      p.line(36, 30, 42, 20, g, 4); p.line(42, 20, 40, 10, g, 3);   // tall tail/neck
      for (const [dx, dy] of [[0, -3], [3, 0], [0, 3], [-3, 0]]) p.circ(40 + dx, 7 + dy, 2, '#f08ac0');
      p.circ(40, 7, 1, '#ffe14a');                                   // flower
      p.line(20, 36, 16, 44, d, 3); p.line(30, 36, 34, 44, d, 3);
      p.line(24, 37, 23, 44, d, 3); p.line(36, 35, 40, 43, d, 3);
      p.ell(27, 31, 12, 8, g);
      p.rect(18, 35, 18, 2, l);
      p.rect(25, 22, 3, 6, l); p.px(24, 26, d);                      // spike on back
      p.poly([[1, 18], [17, 22], [17, 27], [2, 25]], g);            // upper jaw
      p.poly([[2, 32], [17, 32], [17, 38], [4, 38]], g);            // lower jaw
      p.rect(4, 26, 13, 6, '#8a2335');                               // open mouth
      for (let x = 3; x < 17; x += 3) { p.poly([[x, 25], [x + 2, 25], [x + 1, 28]], '#fff'); p.poly([[x + 1, 32], [x + 3, 32], [x + 2, 29]], '#fff'); }
      p.circ(13, 19, 2, '#fff'); p.px(12, 19, '#111');
    },
    flamber(p) {
      const o = '#f07a2a', y = '#ffd34a', r = '#d8452a';
      p.poly([[17, 22], [22, 6], [25, 14], [28, 9], [31, 24]], r);
      p.ell(24, 30, 9, 12, o);
      p.ell(24, 34, 5, 7, y);
      p.circ(24, 28, 4, '#fff'); p.circ(23, 28, 2, '#111'); p.px(22, 27, '#fff');
      p.rect(19, 41, 3, 3, r); p.rect(26, 41, 3, 3, r);
    },
    flamezion(p) {
      const o = '#ea5a26', y = '#ffcf3e', r = '#c3321f';
      p.poly([[12, 22], [14, 6], [18, 14], [21, 4], [24, 13], [27, 4], [30, 14], [34, 6], [36, 22]], r); // crown of flames
      p.poly([[16, 20], [18, 12], [21, 17], [24, 10], [27, 17], [30, 12], [32, 20]], y);
      p.ell(24, 30, 12, 13, o);
      p.ell(24, 33, 7, 8, '#ff9a4a');
      p.circ(20, 27, 2, '#111'); p.circ(28, 27, 2, '#111'); p.px(19, 26, '#fff'); p.px(27, 26, '#fff');
      p.line(19, 33, 21, 35, '#111'); p.line(21, 35, 27, 35, '#111'); p.line(27, 35, 29, 33, '#111');
    },
    blazian(p) {
      const skin = '#ffd7a0', o = '#f0802e', r = '#d63a24', y = '#ffd84a';
      p.poly([[13, 12], [12, 2], [17, 7], [19, 0], [23, 6], [26, 0], [29, 6], [33, 1], [34, 8], [37, 4], [35, 13]], r); // spiky hair
      p.poly([[16, 11], [18, 5], [21, 9], [24, 4], [27, 9], [30, 5], [32, 11]], y);
      p.line(20, 28, 9, 22, o, 3); p.line(28, 28, 39, 22, o, 3);     // arms
      p.circ(8, 21, 3, skin); p.circ(40, 21, 3, skin);
      p.line(21, 34, 15, 44, o, 3); p.line(27, 34, 33, 44, o, 3);    // legs
      p.rect(12, 44, 5, 2, r); p.rect(32, 44, 5, 2, r);
      p.circ(24, 15, 7, skin);
      p.circ(21, 14, 1, '#111'); p.circ(27, 14, 2, '#111'); p.px(26, 13, '#fff');
      p.line(21, 18, 23, 19, '#111'); p.line(23, 19, 27, 18, '#111');
      p.circ(24, 29, 6, o);
      p.circ(24, 29, 3, y);                                         // sun emblem
      for (const [dx, dy] of [[0, -5], [5, 0], [0, 5], [-5, 0]]) p.px(24 + dx, 29 + dy, y);
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
