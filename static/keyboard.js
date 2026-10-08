/* In-page iOS-style keyboard.
 *
 * Why this exists: on iPhone, WebKit shows its form accessory bar (the up/down
 * arrows + checkmark strip) above the system keyboard for *every* focusable text
 * element — input, textarea and contenteditable alike — and no attribute, meta
 * tag or CSS can switch it off. The only page-level way to never see that bar is
 * to never give iOS a text field to focus. So the composer is a plain div, this
 * keyboard draws itself, and the system keyboard is never summoned.
 */
(function (global) {
  'use strict';

  const LAYERS = {
    abc: [
      ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
      ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
      ['SHIFT', 'z', 'x', 'c', 'v', 'b', 'n', 'm', 'DEL'],
      ['NUM', 'SPACE', 'RET'],
    ],
    num: [
      ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
      ['-', '/', ':', ';', '(', ')', '$', '&', '@', '"'],
      ['SYM', '.', ',', '?', '!', "'", 'DEL'],
      ['ABC', 'SPACE', 'RET'],
    ],
    sym: [
      ['[', ']', '{', '}', '#', '%', '^', '*', '+', '='],
      ['_', '\\', '|', '~', '<', '>', '€', '£', '¥', '•'],
      ['NUM', '.', ',', '?', '!', "'", 'DEL'],
      ['ABC', 'SPACE', 'RET'],
    ],
  };

  const EMOJI = ('😂 😭 💀 🙏 🔥 👀 🍻 🍺 🥃 🍷 🍹 🥂 😎 🤝 🫡 👍 👎 🙌 💪 🤙 🫠 🤣 😅 😤 🥴 🤮 😴 🫶 ❤️ 💯 '
    + '🎉 🏈 ⚽ 🏀 ⛳ 🎮 🍕 🌮 🍔 🍗 🥩 🍟 ☕ 🚗 ✈️ 🏖️ 🎰 💸 🤑 😬 🙃 😏 🤷‍♂️ 🤦‍♂️ 👊 ✌️ 🤞 🫵 🥶 🥵 🤯 😈 👻 🎃 🐶 🦅 🍀 ⚡ ⭐ 🌙').split(' ');

  const COMMON = ['a', 'and', 'the', 'with', 'of', 'tall', 'double', 'pint', 'glass', 'bottle', 'can', 'half', 'small',
    'large', 'big', 'shot', 'shots', 'beer', 'beers', 'wine', 'drink', 'round', 'another', 'one', 'two', 'three', 'oz'];

  const isTouch = 'ontouchstart' in global || (navigator.maxTouchPoints || 0) > 0;

  class IOSKeyboard {
    constructor(el) {
      this.el = el;
      this.layer = 'abc';
      this.shift = false;
      this.caps = false;
      this.editor = null;
      this.open = false;
      this.vocab = [];
      this.freq = new Map();
      this.recent = [];
      this.onOpen = null;
      this.onClose = null;
      this._lastShiftTap = 0;
      this._delTimer = null;
      this._delInterval = null;
      this._delCount = 0;
      this._build();
      global.addEventListener('resize', () => { if (this.open) this._publishHeight(); });
    }

    /* ---------- public ---------- */
    setVocab(words) { this.vocab = words || []; }
    setHistory(raws) {
      this.freq = new Map();
      const seen = [];
      for (const r of raws) {
        const k = r.trim().toLowerCase();
        if (!k) continue;
        this.freq.set(k, (this.freq.get(k) || 0) + 1);
        if (!seen.includes(k)) seen.push(k);
      }
      this.recent = seen;
      if (this.open) this._updatePredict();
    }
    attach(editor) {
      this.editor = editor;
      this.shift = false; this.caps = false;
      if (this.layer === 'emoji') this.layer = 'abc';
      this._renderRows();
      this._updatePredict();
    }
    show(editor) {
      if (editor) this.attach(editor);
      if (!this.editor) return;
      this.el.classList.add('open');
      this.el.setAttribute('aria-hidden', 'false');
      this.open = true;
      this._publishHeight();
      this._updatePredict();
      if (this.onOpen) this.onOpen();
    }
    hide() {
      if (!this.open) return;
      this.open = false;
      this.el.classList.remove('open');
      this.el.setAttribute('aria-hidden', 'true');
      document.documentElement.style.setProperty('--kb', '0px');
      this._stopDelete();
      if (this.onClose) this.onClose();
    }
    height() { return this.el.offsetHeight; }

    /* ---------- build ---------- */
    _build() {
      this.el.innerHTML = '';
      this.predict = document.createElement('div');
      this.predict.className = 'kb-predict';
      this.rows = document.createElement('div');
      this.rows.className = 'kb-rows';
      this.bottom = document.createElement('div');
      this.bottom.className = 'kb-bottom';
      this.bottom.innerHTML =
        '<button type="button" data-k="EMOJI" aria-label="Emoji"><svg width="26" height="26"><use href="#i-emoji"/></svg></button>' +
        '<button type="button" data-k="MIC" aria-label="Dictate"><svg width="24" height="24"><use href="#i-mic"/></svg></button>';
      this.el.appendChild(this.predict);
      this.el.appendChild(this.rows);
      this.el.appendChild(this.bottom);

      // nothing on the keyboard may scroll, select, zoom or steal focus
      this.el.addEventListener('touchstart', (e) => { if (!e.target.closest('.kb-emoji')) e.preventDefault(); }, { passive: false });
      this.el.addEventListener('touchmove', (e) => { if (!e.target.closest('.kb-emoji')) e.preventDefault(); }, { passive: false });
      this.el.addEventListener('contextmenu', (e) => e.preventDefault());
      this.el.addEventListener('mousedown', (e) => e.preventDefault());

      const down = (e) => {
        const key = e.target.closest('[data-k]');
        if (!key) return;
        if (e.pointerType === 'mouse' && e.button !== 0) return;
        e.preventDefault();
        this._press(key, e);
      };
      const up = () => this._release();
      this.el.addEventListener('pointerdown', down);
      global.addEventListener('pointerup', up);
      global.addEventListener('pointercancel', up);
      this.el.addEventListener('pointerleave', up);
      this._renderRows();
    }

    _keyEl(k) {
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.k = k;
      b.className = 'key';
      switch (k) {
        case 'SHIFT': {
          b.classList.add('dark', 'shift');
          const ico = this.caps ? '#i-caps' : (this.shift ? '#i-shift-fill' : '#i-shift');
          if (this.shift || this.caps) b.classList.add('on');
          b.innerHTML = `<svg width="22" height="22"><use href="${ico}"/></svg>`;
          break;
        }
        case 'DEL': b.classList.add('dark', 'del'); b.innerHTML = '<svg width="26" height="19"><use href="#i-delete"/></svg>'; break;
        case 'NUM': b.classList.add('dark', 'num'); b.textContent = '123'; break;
        case 'ABC': b.classList.add('dark', 'abc'); b.textContent = 'ABC'; break;
        case 'SYM': b.classList.add('dark', 'num'); b.textContent = '#+='; break;
        case 'SPACE': b.classList.add('space'); b.textContent = 'space'; break;
        case 'RET': b.classList.add('dark', 'ret'); b.textContent = 'return'; break;
        default:
          b.textContent = (this.layer === 'abc' && (this.shift || this.caps)) ? k.toUpperCase() : k;
      }
      return b;
    }

    _renderRows() {
      this.rows.innerHTML = '';
      this.rows.className = 'kb-rows';
      this.bottom.style.display = '';
      if (this.layer === 'emoji') {
        const grid = document.createElement('div');
        grid.className = 'kb-emoji';
        for (const e of EMOJI) {
          const b = document.createElement('button');
          b.type = 'button'; b.dataset.k = 'CH:' + e; b.textContent = e;
          grid.appendChild(b);
        }
        const bar = document.createElement('div');
        bar.className = 'kb-emoji-bar';
        const abc = this._keyEl('ABC'); abc.textContent = 'ABC';
        const del = this._keyEl('DEL');
        bar.appendChild(abc); bar.appendChild(del);
        this.rows.appendChild(grid);
        this.rows.appendChild(bar);
        this.bottom.style.display = 'none';
        return;
      }
      LAYERS[this.layer].forEach((row, ri) => {
        const r = document.createElement('div');
        r.className = 'kb-row r' + (ri + 1);
        row.forEach((k) => r.appendChild(this._keyEl(k)));
        this.rows.appendChild(r);
      });
    }

    _publishHeight() {
      const h = this.el.offsetHeight;
      document.documentElement.style.setProperty('--kb', h + 'px');
    }

    /* ---------- key handling ---------- */
    _press(key, e) {
      const k = key.dataset.k;
      this._release();
      key.classList.add('pressed');
      this._pressed = key;
      if (!this.editor) return;

      if (k.startsWith('CH:')) { this._insert(k.slice(3)); return; }
      switch (k) {
        case 'SHIFT': {
          const now = Date.now();
          if (now - this._lastShiftTap < 320 && !this.caps) { this.caps = true; this.shift = false; }
          else if (this.caps) { this.caps = false; this.shift = false; }
          else this.shift = !this.shift;
          this._lastShiftTap = now;
          this._renderRows();
          return;
        }
        case 'DEL': this._deleteOnce(); this._startDeleteRepeat(); return;
        case 'NUM': this.layer = 'num'; this._renderRows(); return;
        case 'SYM': this.layer = 'sym'; this._renderRows(); return;
        case 'ABC': this.layer = 'abc'; this._renderRows(); return;
        case 'EMOJI': this.layer = (this.layer === 'emoji') ? 'abc' : 'emoji'; this._renderRows(); this._publishHeight(); return;
        case 'MIC': return;
        case 'SPACE': this._insert(' '); return;
        case 'RET': if (this.editor.onReturn) this.editor.onReturn(); this._updatePredict(); return;
        case 'SUG': this._applySuggestion(key.dataset.v, key.dataset.mode); return;
        default: {
          let ch = k;
          if (this.layer === 'abc' && (this.shift || this.caps)) ch = ch.toUpperCase();
          if (isTouch && this.layer !== 'emoji' && ch.length === 1) this._showPop(key, ch);
          this._insert(ch);
          if (this.shift && !this.caps) { this.shift = false; this._renderRows(); }
        }
      }
    }

    _release() {
      if (this._pressed) { this._pressed.classList.remove('pressed'); this._pressed = null; }
      if (this._pop) { this._pop.remove(); this._pop = null; }
      this._stopDelete();
    }

    _showPop(key, ch) {
      const pop = document.createElement('div');
      pop.className = 'key-pop';
      pop.textContent = ch;
      key.appendChild(pop);
      this._pop = pop;
      setTimeout(() => { if (this._pop === pop) { pop.remove(); this._pop = null; } }, 260);
    }

    _insert(ch) {
      const t = this.editor.get();
      this.editor.set(t + ch);
      this._updatePredict();
    }

    _deleteOnce() {
      const t = this.editor.get();
      if (!t) return;
      // after holding a while, eat whole words like iOS does
      if (this._delCount > 12) {
        const trimmed = t.replace(/\s+$/, '');
        const i = trimmed.lastIndexOf(' ');
        this.editor.set(i < 0 ? '' : trimmed.slice(0, i + 1));
      } else {
        // strip one grapheme (emoji are multi-unit)
        this.editor.set(Array.from(t).slice(0, -1).join(''));
      }
      this._updatePredict();
    }
    _startDeleteRepeat() {
      this._stopDelete();
      this._delCount = 0;
      this._delTimer = setTimeout(() => {
        this._delInterval = setInterval(() => { this._delCount++; this._deleteOnce(); }, 70);
      }, 420);
    }
    _stopDelete() {
      if (this._delTimer) { clearTimeout(this._delTimer); this._delTimer = null; }
      if (this._delInterval) { clearInterval(this._delInterval); this._delInterval = null; }
      this._delCount = 0;
    }

    /* ---------- QuickType ---------- */
    _candidates(text) {
      const full = text.toLowerCase();
      const trimmedEnd = /\s$/.test(text);
      const words = full.trim().split(/\s+/).filter(Boolean);
      const last = trimmedEnd ? '' : (words[words.length - 1] || '');
      const out = [];
      const push = (w, mode) => {
        if (!w || out.length >= 6) return;
        if (out.some((o) => o.w === w)) return;
        if (w === full.trim() && mode === 'full') return;
        out.push({ w, mode });
      };
      const byFreq = [...this.freq.entries()].sort((a, b) => b[1] - a[1]).map((e) => e[0]);
      if (!full.trim()) {
        for (const r of byFreq) push(r, 'full');
        return out.slice(0, 3);
      }
      // whole-draft matches first (history, then dictionary) — "mich" -> "michelob ultra"
      for (const r of byFreq) if (r.startsWith(full.trim()) && r !== full.trim()) push(r, 'full');
      for (const v of this.vocab) if (v.w.startsWith(full.trim()) && v.w !== full.trim()) push(v.w, 'full');
      // then the current word on its own — "2 coo" -> "coors light"
      if (last) {
        for (const r of byFreq) if (r.startsWith(last) && r !== last) push(r, 'word');
        for (const v of this.vocab) if (v.w.startsWith(last) && v.w !== last) push(v.w, 'word');
        for (const c of COMMON) if (c.startsWith(last) && c !== last) push(c, 'word');
        for (const v of this.vocab) {
          const parts = v.w.split(' ');
          if (parts.length > 1 && parts.some((p, i) => i > 0 && p.startsWith(last))) push(v.w, 'word');
        }
      }
      return out.slice(0, 3);
    }

    _updatePredict() {
      if (!this.editor) { this.predict.innerHTML = ''; return; }
      const text = this.editor.get();
      const cands = this._candidates(text);
      const cells = [];
      const literal = text.trim();
      if (literal && !/\s$/.test(text)) {
        cells.push({ label: '“' + literal.split(/\s+/).pop() + '”', lit: true });
      }
      for (const c of cands) { if (cells.length < 3) cells.push({ label: c.w, v: c.w, mode: c.mode }); }
      while (cells.length && cells.length < 3) cells.push({ label: '' });
      this.predict.innerHTML = '';
      for (const c of cells) {
        const s = document.createElement('button');
        s.type = 'button';
        s.className = 'kb-sug' + (c.lit ? ' lit' : '');
        s.textContent = c.label;
        if (c.v) { s.dataset.k = 'SUG'; s.dataset.v = c.v; s.dataset.mode = c.mode; }
        else if (c.lit) { s.dataset.k = 'SUG'; s.dataset.v = literal.split(/\s+/).pop(); s.dataset.mode = 'word'; }
        this.predict.appendChild(s);
      }
    }

    _applySuggestion(v, mode) {
      const t = this.editor.get();
      let next;
      if (mode === 'full' || !t.trim()) next = v + ' ';
      else if (/\s$/.test(t)) next = t + v + ' ';
      else {
        const i = t.lastIndexOf(' ');
        next = (i < 0 ? '' : t.slice(0, i + 1)) + v + ' ';
      }
      this.editor.set(next);
      if (this.shift && !this.caps) { this.shift = false; this._renderRows(); }
      this._updatePredict();
    }
  }

  global.IOSKeyboard = IOSKeyboard;
})(window);
