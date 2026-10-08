/* Messages — app logic: conversation list, thread, composer, sheets. */
(function () {
  'use strict';

  const API = '/api';
  const $ = (id) => document.getElementById(id);
  const TZ = new Date().getTimezoneOffset();
  const HOUR = 3600000;
  const MIN = 60000;

  let sessions = [];
  let cur = null;                  // open session id
  let revealed = null;             // { id, side } caption currently shown
  let pendingBackdateTs = null;    // next drink gets this timestamp
  const replyState = new Map();    // drink id -> { shown, typing } while the "friend" is typing
  let replyTimers = [];
  let paintRaf = 0;

  const kb = new IOSKeyboard($('keyboard'));

  /* ------------------------------------------------------------------ utils */
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtTime = (ts) => new Date(ts).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const startOfDay = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x.getTime(); };
  function dayDiff(ts) { return Math.round((startOfDay(Date.now()) - startOfDay(ts)) / 86400000); }
  function fmtListTime(ts) {
    const dd = dayDiff(ts);
    if (dd <= 0) return fmtTime(ts);
    if (dd === 1) return 'Yesterday';
    if (dd < 7) return new Date(ts).toLocaleDateString([], { weekday: 'long' });
    return new Date(ts).toLocaleDateString([], { month: 'numeric', day: 'numeric', year: '2-digit' });
  }
  function fmtDivider(ts) {
    const dd = dayDiff(ts);
    const d = new Date(ts);
    let day;
    if (dd <= 0) day = 'Today';
    else if (dd === 1) day = 'Yesterday';
    else if (dd < 7) day = d.toLocaleDateString([], { weekday: 'long' });
    else day = d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
    return { day, time: fmtTime(ts) };
  }
  const level = (total) => (total <= 0.5 ? 0 : total < 7 ? 1 : total <= 12 ? 2 : 3);
  const getSession = () => sessions.find((s) => s.id === cur);
  function currentBac(s) {
    if (!s) return 0;
    const met = s.metabolism != null ? s.metabolism : 0.015;
    const since = Date.now() - (s.fetchedAt || Date.now());
    return Math.max(0, (s.bac || 0) - met * since / HOUR);
  }
  function lastActivity(s) { return s.drinks.length ? s.drinks[s.drinks.length - 1].ts : s.start; }

  async function api(path, opts) {
    const r = await fetch(API + path, opts);
    if (!r.ok) throw new Error('api ' + r.status);
    return r.json();
  }
  const post = (path, body, method = 'POST') => api(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

  /* --------------------------------------------------------------- loading */
  async function loadSessions() {
    const list = await api(`/sessions?tz=${TZ}`);
    const now = Date.now();
    list.forEach((s) => { s.fetchedAt = now; s.drinks.sort((a, b) => a.ts - b.ts); });
    sessions = list;
    kb.setHistory(sessions.flatMap((s) => s.drinks.map((d) => d.raw)));
    renderList();
    if (cur !== null) updateHeader();
  }
  async function loadVocab() {
    try { kb.setVocab(await api('/vocab')); } catch (e) { /* suggestions are optional */ }
  }

  /* ------------------------------------------------------------------ list */
  function previewFor(s) {
    const d = s.drinks[s.drinks.length - 1];
    if (!d) return 'No messages yet';
    const st = replyState.get(d.id);
    const bubbles = d.reply || [];
    if (st) return st.shown ? bubbles[st.shown - 1] : d.raw;
    return bubbles.length ? bubbles[bubbles.length - 1] : d.raw;
  }
  function renderList() {
    const list = $('sessions-list');
    list.innerHTML = '';
    if (!sessions.length) {
      list.appendChild(el('div', 'empty-state', 'No conversations yet.\nTap the compose button to start one.'));
      return;
    }
    const sorted = [...sessions].sort((a, b) => lastActivity(b) - lastActivity(a));
    sorted.forEach((s) => {
      const row = el('div', 'session-row');
      row.innerHTML =
        `<div class="avatar lv${level(s.total_std)}"><span class="av-count">${Math.round(s.total_std)}</span></div>` +
        `<div class="session-info"><div class="session-line"><div class="session-name">${esc(s.name)}</div>` +
        `<div class="session-time">${esc(fmtListTime(lastActivity(s)))}<svg class="ic" width="14" height="14"><use href="#i-chevron-right"/></svg></div></div>` +
        `<div class="session-preview">${esc(previewFor(s))}</div></div>`;
      attachPress(row, () => openSession(s.id), () => sessionSheet(s));
      list.appendChild(row);
    });
  }

  /* ---------------------------------------------------------------- thread */
  function openSession(id) {
    cur = id;
    revealed = null;
    $('list-view').hidden = true;
    $('chat-view').hidden = false;
    updateHeader();
    renderMessages();
    requestAnimationFrame(() => { $('messages').scrollTop = $('messages').scrollHeight; });
  }
  function closeSession() {
    kb.hide();
    cur = null;
    $('chat-view').hidden = true;
    $('list-view').hidden = false;
    composerEditor.set('');
    pendingBackdateTs = null;
    updatePlusState();
    loadSessions();
  }
  function updateHeader() {
    const s = getSession();
    if (!s) return;
    $('header-count').textContent = Math.round(s.total_std);
    $('header-bac').textContent = currentBac(s).toFixed(3);
    $('header-avatar').className = 'avatar avatar-lg lv' + level(s.total_std);
    $('header-name').textContent = s.name;
  }
  setInterval(() => { if (cur !== null) updateHeader(); }, 15000);

  function dividerEl(ts) {
    const { day, time } = fmtDivider(ts);
    const d = el('div', 'divider');
    d.innerHTML = `<b>${esc(day)}</b> ${esc(time)}`;
    return d;
  }
  function typingEl() {
    const t = el('div', 'typing');
    t.innerHTML = '<i></i><i></i><i></i>';
    return t;
  }
  function captionEl(d, side) {
    const n = Math.round(d.std_total || 0);
    const txt = d.pending ? `${fmtTime(d.ts)}` : `${fmtTime(d.ts)}  ·  ${Number(d.bac || 0).toFixed(3)}  ·  ${n} drink${n === 1 ? '' : 's'}`;
    return el('div', 'caption reveal ' + side, txt);
  }

  function renderMessages(keepScroll) {
    const s = getSession();
    if (!s) return;
    const c = $('messages');
    const nearBottom = c.scrollHeight - c.scrollTop - c.clientHeight < 90;
    c.innerHTML = '';
    const frag = document.createDocumentFragment();
    frag.appendChild(el('div', 'divider service', 'iMessage'));
    frag.appendChild(dividerEl(s.drinks.length ? s.drinks[0].ts : s.start));
    let prevTs = null;
    s.drinks.forEach((d, i) => {
      if (prevTs !== null && d.ts - prevTs > HOUR) frag.appendChild(dividerEl(d.ts));
      prevTs = d.ts;
      const sent = el('div', 'msg sent tail gs', d.raw);
      sent.dataset.id = d.id;
      if (!d.pending) attachPress(sent, () => toggleCaption(d.id, 'r'), () => drinkSheet(d));
      frag.appendChild(sent);
      const isLast = i === s.drinks.length - 1;
      if (revealed && revealed.id === d.id && revealed.side === 'r') frag.appendChild(captionEl(d, 'r'));
      else if (isLast) frag.appendChild(el('div', 'caption r', 'Delivered'));

      const st = replyState.get(d.id);
      const bubbles = d.reply || [];
      const shown = st ? Math.min(st.shown, bubbles.length) : bubbles.length;
      for (let j = 0; j < shown; j++) {
        const isTail = j === shown - 1 && !(st && st.typing);
        const r = el('div', 'msg recv' + (j === 0 ? ' gs' : '') + (isTail ? ' tail' : ''), bubbles[j]);
        r.dataset.id = d.id;
        attachPress(r, () => toggleCaption(d.id, 'l'), null);
        frag.appendChild(r);
      }
      if (st && st.typing) frag.appendChild(typingEl());
      if (revealed && revealed.id === d.id && revealed.side === 'l' && shown) frag.appendChild(captionEl(d, 'l'));
    });
    c.appendChild(frag);
    if (!keepScroll || nearBottom) c.scrollTop = c.scrollHeight;
    paintBubbles();
    updateHeader();
  }
  function toggleCaption(id, side) {
    revealed = (revealed && revealed.id === id && revealed.side === side) ? null : { id, side };
    renderMessages(true);
  }
  function rerender(sessionId) {
    if (cur === sessionId) renderMessages(true);
    renderList();
  }

  // sent bubbles get a little lighter toward the top of the screen, like Messages
  function paintBubbles() {
    const c = $('messages');
    const cr = c.getBoundingClientRect();
    const H = cr.height || 1;
    const top = [52, 152, 255], bot = [10, 118, 236];
    c.querySelectorAll('.msg.sent').forEach((b) => {
      const r = b.getBoundingClientRect();
      const t = Math.min(1, Math.max(0, (r.top + r.height / 2 - cr.top) / H));
      const col = top.map((v, i) => Math.round(v + (bot[i] - v) * t));
      b.style.setProperty('--bub', `rgb(${col.join(',')})`);
    });
  }
  $('messages').addEventListener('scroll', () => {
    if (!paintRaf) paintRaf = requestAnimationFrame(() => { paintRaf = 0; paintBubbles(); });
  }, { passive: true });

  /* ------------------------------------------------- tap / long-press helper */
  function attachPress(node, onTap, onLong) {
    let timer = null, moved = false, sx = 0, sy = 0, active = false;
    const clear = () => { if (timer) { clearTimeout(timer); timer = null; } };
    node.addEventListener('pointerdown', (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      active = true; moved = false; sx = e.clientX; sy = e.clientY;
      clear();
      if (onLong) timer = setTimeout(() => { timer = null; if (active && !moved) { active = false; onLong(); } }, 480);
    });
    node.addEventListener('pointermove', (e) => {
      if (!active) return;
      if (Math.abs(e.clientX - sx) > 10 || Math.abs(e.clientY - sy) > 10) { moved = true; clear(); }
    });
    node.addEventListener('pointerup', (e) => {
      if (!active) return;
      active = false;
      const wasPending = !!timer || !onLong;
      clear();
      if (!moved && wasPending && onTap) { e.preventDefault(); onTap(); }
    });
    node.addEventListener('pointercancel', () => { active = false; clear(); });
    node.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  /* -------------------------------------------------------------- composer */
  let draft = '';
  const composerEditor = {
    get: () => draft,
    set: (t) => { draft = t; renderField($('field'), $('field-text'), draft); },
    onReturn: () => sendDrink(),
  };
  function renderField(field, textEl, text) {
    textEl.textContent = text;
    const caret = el('span', 'caret');
    textEl.appendChild(caret);
    field.classList.toggle('has-text', text.length > 0);
  }
  renderField($('field'), $('field-text'), '');

  function focusComposer() {
    if (cur === null) return;
    document.querySelectorAll('.field.focused').forEach((f) => f.classList.remove('focused'));
    $('field').classList.add('focused');
    kb.show(composerEditor);
  }
  kb.onOpen = () => {
    if (cur !== null) {
      $('chat-view').classList.add('kb-open');
      const c = $('messages');
      c.scrollTop = c.scrollHeight;
      setTimeout(() => { c.scrollTop = c.scrollHeight; paintBubbles(); }, 270);
    }
  };
  kb.onClose = () => {
    $('chat-view').classList.remove('kb-open');
    document.querySelectorAll('.field.focused').forEach((f) => f.classList.remove('focused'));
    setTimeout(paintBubbles, 270);
  };
  $('field').addEventListener('pointerdown', (e) => { e.preventDefault(); focusComposer(); });
  $('send-btn').addEventListener('pointerdown', (e) => { e.preventDefault(); e.stopPropagation(); sendDrink(); });
  $('audio-btn').addEventListener('pointerdown', (e) => { e.preventDefault(); e.stopPropagation(); focusComposer(); });
  // tapping into the thread puts the keyboard away, like dragging it down would
  $('messages').addEventListener('pointerdown', (e) => { if (!e.target.closest('.msg')) kb.hide(); });
  $('back-btn').addEventListener('click', closeSession);
  $('header-center').addEventListener('click', () => { if (cur !== null) renameSheet(getSession()); });
  $('plus-btn').addEventListener('click', () => backdateSheet());
  $('video-btn').addEventListener('click', () => {});

  function updatePlusState() {
    $('plus-btn').classList.toggle('pending', !!pendingBackdateTs);
    $('field-placeholder').textContent = pendingBackdateTs ? `iMessage · ${fmtTime(pendingBackdateTs)}` : 'iMessage';
  }

  async function sendDrink() {
    const raw = draft.trim();
    const s = getSession();
    if (!raw || !s) return;
    composerEditor.set('');
    const ts = pendingBackdateTs || Date.now();
    pendingBackdateTs = null;
    updatePlusState();
    const temp = { id: 'tmp' + Date.now(), raw, ts, reply: [], bac: s.bac, std_total: s.total_std, pending: true };
    s.drinks.push(temp);
    s.drinks.sort((a, b) => a.ts - b.ts);
    revealed = null;
    renderMessages();
    try {
      const drink = await post(`/sessions/${s.id}/drinks`, { raw, ts, tz: TZ });
      scheduleReply(drink, s.id);
      await loadSessions();
      renderMessages(true);
    } catch (e) {
      s.drinks = s.drinks.filter((d) => d !== temp);
      renderMessages(true);
    }
  }

  function scheduleReply(d, sessionId) {
    const bubbles = d.reply || [];
    if (!bubbles.length) return;
    const st = { shown: 0, typing: false };
    replyState.set(d.id, st);
    let t = 900 + Math.random() * 2000;                      // he reads it first
    bubbles.forEach((b, j) => {
      const typeMs = Math.min(5200, 700 + b.length * 42 + Math.random() * 700);
      replyTimers.push(setTimeout(() => { st.typing = true; rerender(sessionId); }, t));
      t += typeMs;
      replyTimers.push(setTimeout(() => {
        st.typing = false; st.shown = j + 1;
        if (st.shown >= bubbles.length) replyState.delete(d.id);
        rerender(sessionId);
      }, t));
      t += 500 + Math.random() * 1200;                       // pause between bubbles
    });
  }

  /* ---------------------------------------------------------------- sheets */
  let sheetEditor = null;
  function openSheet(html) {
    const sh = $('sheet');
    sh.innerHTML = html;
    sh.hidden = false;
    $('scrim').hidden = false;
    return sh;
  }
  function closeSheet() {
    $('sheet').hidden = true;
    $('scrim').hidden = true;
    $('sheet').innerHTML = '';
    if (sheetEditor) { sheetEditor = null; kb.hide(); }
  }
  $('scrim').addEventListener('pointerdown', (e) => { e.preventDefault(); closeSheet(); });

  function drinkSheet(d) {
    const sh = openSheet(
      `<div class="sheet-title"><b>${esc(d.raw)}</b>${esc(fmtTime(d.ts))} · ${Number(d.bac).toFixed(3)} · ${esc(d.type)} ${d.oz} oz at ${d.abv}%</div>` +
      '<button class="sheet-btn" data-a="time">Edit Time</button>' +
      '<button class="sheet-btn" data-a="text">Edit Message</button>' +
      '<button class="sheet-btn danger" data-a="del">Delete</button>' +
      '<button class="sheet-btn cancel" data-a="cancel">Cancel</button>');
    sh.onclick = async (e) => {
      const a = e.target.closest('[data-a]')?.dataset.a;
      if (!a) return;
      if (a === 'cancel') return closeSheet();
      if (a === 'time') return timeSheet({ title: 'Edit Time', sub: d.raw, ts: d.ts, onPick: async (ts) => {
        await post(`/drinks/${d.id}`, { ts }, 'PATCH'); await loadSessions(); renderMessages(true);
      } });
      if (a === 'text') return textSheet({ title: 'Edit Message', value: d.raw, onSave: async (v) => {
        await post(`/drinks/${d.id}`, { raw: v }, 'PATCH'); await loadSessions(); renderMessages(true);
      } });
      if (a === 'del') {
        const c = openSheet(`<div class="sheet-title">Delete “${esc(d.raw)}”?<br>The BAC and count update to match.</div>` +
          '<button class="sheet-btn danger" data-a="yes">Delete Message</button><button class="sheet-btn cancel" data-a="no">Cancel</button>');
        c.onclick = async (ev) => {
          const b = ev.target.closest('[data-a]')?.dataset.a;
          if (b === 'yes') { await api(`/drinks/${d.id}`, { method: 'DELETE' }); closeSheet(); await loadSessions(); renderMessages(true); }
          else if (b === 'no') closeSheet();
        };
      }
    };
  }

  function sessionSheet(s) {
    const sh = openSheet(`<div class="sheet-title"><b>${esc(s.name)}</b>${s.drinks.length} message${s.drinks.length === 1 ? '' : 's'}</div>` +
      '<button class="sheet-btn" data-a="open">Open</button>' +
      '<button class="sheet-btn" data-a="rename">Rename</button>' +
      '<button class="sheet-btn danger" data-a="del">Delete Conversation</button>' +
      '<button class="sheet-btn cancel" data-a="cancel">Cancel</button>');
    sh.onclick = (e) => {
      const a = e.target.closest('[data-a]')?.dataset.a;
      if (!a) return;
      if (a === 'cancel') return closeSheet();
      if (a === 'open') { closeSheet(); return openSession(s.id); }
      if (a === 'rename') return renameSheet(s);
      if (a === 'del') {
        const c = openSheet(`<div class="sheet-title">Delete “${esc(s.name)}” and everything in it?</div>` +
          '<button class="sheet-btn danger" data-a="yes">Delete Conversation</button><button class="sheet-btn cancel" data-a="no">Cancel</button>');
        c.onclick = async (ev) => {
          const b = ev.target.closest('[data-a]')?.dataset.a;
          if (b === 'yes') { await api(`/sessions/${s.id}`, { method: 'DELETE' }); closeSheet(); if (cur === s.id) cur = null; await loadSessions(); }
          else if (b === 'no') closeSheet();
        };
      }
    };
  }

  function renameSheet(s) {
    textSheet({ title: 'Name', value: s.name, onSave: async (v) => {
      await post(`/sessions/${s.id}`, { name: v }, 'PATCH');
      s.name = v; updateHeader(); renderList();
    } });
  }

  // a text sheet is the composer's twin: a plain div fed by the in-page keyboard
  function textSheet({ title, value, onSave }) {
    const sh = openSheet(`<div class="sheet-title"><b>${esc(title)}</b></div>` +
      '<div class="field glass focused" id="sheet-field"><div class="field-text" id="sheet-field-text"></div><span class="field-placeholder" id="sheet-ph">Type here</span></div>' +
      '<div class="sheet-row"><button class="sheet-btn cancel" data-a="cancel">Cancel</button><button class="sheet-btn primary" data-a="save">Save</button></div>');
    let text = value || '';
    const field = $('sheet-field'), textEl = $('sheet-field-text');
    const save = async () => { const v = text.trim(); if (v) await onSave(v); closeSheet(); };
    sheetEditor = { get: () => text, set: (t) => { text = t; renderField(field, textEl, text); }, onReturn: save };
    renderField(field, textEl, text);
    document.querySelectorAll('.field.focused').forEach((f) => { if (f !== field) f.classList.remove('focused'); });
    field.classList.add('focused');
    kb.show(sheetEditor);
    field.addEventListener('pointerdown', (e) => { e.preventDefault(); field.classList.add('focused'); kb.show(sheetEditor); });
    sh.onclick = (e) => {
      const a = e.target.closest('[data-a]')?.dataset.a;
      if (a === 'cancel') closeSheet();
      if (a === 'save') save();
    };
  }

  /* ---------------------------------------------------------- time picking */
  function backdateSheet() {
    timeSheet({
      title: 'Log for a different time',
      sub: 'The next message is stamped with this time',
      ts: pendingBackdateTs || Date.now(),
      allowNow: true,
      onPick: (ts) => { pendingBackdateTs = ts; updatePlusState(); },
      onNow: () => { pendingBackdateTs = null; updatePlusState(); },
    });
  }

  function timeSheet({ title, sub, ts, onPick, allowNow, onNow }) {
    const sh = openSheet(`<div class="sheet-title"><b>${esc(title)}</b>${sub ? esc(sub) : ''}</div>` +
      '<div class="picker-live" id="picker-live"></div><div id="wheel-slot"></div>' +
      '<div class="chips" id="chips"><button class="chip" data-m="0">Now</button><button class="chip" data-m="15">15m ago</button><button class="chip" data-m="30">30m ago</button><button class="chip" data-m="60">1h ago</button><button class="chip" data-m="120">2h ago</button></div>' +
      `<div class="sheet-row">${allowNow ? '<button class="sheet-btn" data-a="now">Just Now</button>' : '<button class="sheet-btn cancel" data-a="cancel">Cancel</button>'}<button class="sheet-btn primary" data-a="use">Use This Time</button></div>`);
    const picker = wheelPicker(ts, () => { $('picker-live').textContent = describe(picker.get()); });
    $('wheel-slot').appendChild(picker.el);
    requestAnimationFrame(() => { picker.scrollTo(ts); $('picker-live').textContent = describe(ts); });
    sh.onclick = (e) => {
      const chip = e.target.closest('.chip');
      if (chip) { picker.scrollTo(Date.now() - Number(chip.dataset.m) * MIN); return; }
      const a = e.target.closest('[data-a]')?.dataset.a;
      if (a === 'cancel') closeSheet();
      if (a === 'now') { if (onNow) onNow(); closeSheet(); }
      if (a === 'use') { const v = picker.get(); closeSheet(); onPick(v); }
    };
  }
  function describe(ts) {
    const { day, time } = fmtDivider(ts);
    const ago = Date.now() - ts;
    let rel = '';
    if (ago > -MIN && ago < MIN) rel = 'now';
    else if (ago > 0 && ago < 36 * HOUR) rel = ago < HOUR ? `${Math.round(ago / MIN)} min ago` : `${(ago / HOUR).toFixed(1).replace(/\.0$/, '')} h ago`;
    else if (ago < 0) rel = 'in the future';
    return `${day}, ${time}${rel ? ` · ${rel}` : ''}`;
  }

  // iOS-style drum picker: day / hour / minute / am-pm columns with scroll-snap
  function wheelPicker(initialTs, onChange) {
    const ITEM = 34;
    const DAYS = 30;
    const root = el('div', 'wheel');
    const today0 = startOfDay(Date.now());
    const dayItems = [];
    for (let i = DAYS - 1; i >= 0; i--) {
      const t = today0 - i * 86400000;
      dayItems.push({ v: t, label: i === 0 ? 'Today' : i === 1 ? 'Yesterday' : new Date(t).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }) });
    }
    const hourItems = Array.from({ length: 12 }, (_, i) => ({ v: i, label: String(i === 0 ? 12 : i) }));
    const minItems = Array.from({ length: 60 }, (_, i) => ({ v: i, label: String(i).padStart(2, '0') }));
    const apItems = [{ v: 0, label: 'AM' }, { v: 1, label: 'PM' }];
    const cols = {};
    const mk = (name, items) => {
      const c = el('div', 'wheel-col ' + name);
      c.appendChild(el('div', 'wheel-pad'));
      items.forEach((it) => c.appendChild(el('div', 'wheel-item', it.label)));
      c.appendChild(el('div', 'wheel-pad'));
      c.addEventListener('scroll', () => { clearTimeout(c._t); c._t = setTimeout(() => onChange && onChange(), 80); }, { passive: true });
      cols[name] = { el: c, items };
      root.appendChild(c);
    };
    mk('day', dayItems); mk('hour', hourItems); mk('min', minItems); mk('ampm', apItems);
    const idx = (name) => Math.max(0, Math.min(cols[name].items.length - 1, Math.round(cols[name].el.scrollTop / ITEM)));
    const setIdx = (name, i) => { cols[name].el.scrollTop = i * ITEM; };
    const api = {
      el: root,
      get() {
        const day = cols.day.items[idx('day')].v;
        const h12 = cols.hour.items[idx('hour')].v;
        const m = cols.min.items[idx('min')].v;
        const pm = cols.ampm.items[idx('ampm')].v;
        const d = new Date(day);
        d.setHours(h12 + (pm ? 12 : 0), m, 0, 0);
        return d.getTime();
      },
      scrollTo(ts) {
        const d = new Date(ts);
        const day0 = startOfDay(ts);
        let di = cols.day.items.findIndex((it) => it.v === day0);
        if (di < 0) di = cols.day.items.length - 1;
        setIdx('day', di);
        setIdx('hour', d.getHours() % 12);
        setIdx('min', d.getMinutes());
        setIdx('ampm', d.getHours() >= 12 ? 1 : 0);
        if (onChange) onChange();
      },
    };
    return api;
  }

  /* ------------------------------------------------------------- top level */
  $('new-btn').addEventListener('click', async () => {
    const s = await post('/sessions', { start: Date.now() });
    s.fetchedAt = Date.now();
    s.drinks = s.drinks || [];
    sessions.unshift(s);
    renderList();
    openSession(s.id);
    setTimeout(focusComposer, 350);
  });
  $('edit-btn').addEventListener('click', () => Dashboard.open());
  $('dash-done').addEventListener('click', () => Dashboard.close());
  $('dash-seg').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-days]');
    if (!b) return;
    $('dash-seg').querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
    Dashboard.open(Number(b.dataset.days));
  });

  document.addEventListener('visibilitychange', () => { if (!document.hidden) loadSessions(); });
  // keep the keyboard from leaving stale state behind if a system gesture interrupts a press
  window.addEventListener('blur', () => kb._release && kb._release());

  loadVocab();
  loadSessions();
})();
