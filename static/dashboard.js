/* Hidden dashboard (behind "Edit"): what the last 7 / 30 days looked like. */
const Dashboard = (function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const TZ = new Date().getTimezoneOffset();
  const HOUR = 3600000;
  let days = 7;
  let data = null;
  let seq = 0;

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const n1 = (v) => (Math.abs(v - Math.round(v)) < 0.05 ? String(Math.round(v)) : v.toFixed(1));
  const bac = (v) => Number(v || 0).toFixed(3);
  const hrs = (h) => (h < 0.95 ? `${Math.round(h * 60)}m` : `${h.toFixed(1).replace(/\.0$/, '')}h`);
  const fmtTime = (ts) => new Date(ts).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const fmtDay = (ts) => new Date(ts).toLocaleDateString([], { weekday: 'short' });
  const fmtDate = (ts) => new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric' });
  const fmtWhen = (ts) => `${fmtDay(ts)} ${fmtTime(ts)}`;
  const level = (total) => (total <= 0.5 ? 0 : total < 7 ? 1 : total <= 12 ? 2 : 3);
  const hourLabel = (h) => (h === 0 ? '12 AM' : h < 12 ? `${h} AM` : h === 12 ? '12 PM' : `${h - 12} PM`);
  const STD_ULTRA = (12 * 29.5735 * 0.042 * 0.789) / 14;

  async function open(d) {
    if (d) days = d;
    $('dash-view').hidden = false;
    const scroll = $('dash-scroll');
    const mine = ++seq;
    if (!data) scroll.innerHTML = '<div class="dash-empty">Loading…</div>';
    else scroll.classList.add('loading');
    try {
      const r = await fetch(`/api/stats?days=${days}&tz=${TZ}`);
      const json = await r.json();
      if (mine !== seq) return;
      data = json;
      render();
    } catch (e) {
      if (mine === seq) scroll.innerHTML = '<div class="dash-empty">Couldn’t load stats.</div>';
    } finally {
      scroll.classList.remove('loading');
    }
  }
  function close() { $('dash-view').hidden = true; }

  /* ------------------------------------------------------------- rendering */
  function render() {
    const d = data;
    const t = d.totals;
    const scroll = $('dash-scroll');
    const plotW = Math.max(240, scroll.clientWidth - 28 - 32);
    const rangeLabel = `${fmtDate(d.window_start)} – ${fmtDate(d.now)}`;

    const diff = t.std - d.prev.std;
    const deltaHtml = d.prev.count || t.count
      ? `<span class="delta ${diff > 0.05 ? 'up' : diff < -0.05 ? 'down' : ''}">${diff >= 0 ? '+' : '−'}${n1(Math.abs(diff))} vs prior ${d.days} days</span>`
      : '';

    let nowCls = '', nowTxt = 'Sober right now';
    if (d.current.bac >= 0.08) { nowCls = 'hot'; nowTxt = `${bac(d.current.bac)} right now`; }
    else if (d.current.bac > 0.0005) { nowCls = 'buzz'; nowTxt = `${bac(d.current.bac)} right now`; }
    if (d.current.sober_at && d.current.bac > 0.0005) nowTxt += ` · back to zero around ${fmtTime(d.current.sober_at)}`;

    let html = `<div class="dash-h1">Last ${d.days} days</div><div class="dash-sub">${esc(rangeLabel)}</div>`;

    html += `<div class="card"><div class="card-title">Standard drinks</div>
      <div class="hero"><div class="hero-num">${n1(t.std)}</div><div class="hero-unit">standard<br>drinks</div>${deltaHtml}</div>
      <div class="card-note">${t.count} logged · ${t.sessions} session${t.sessions === 1 ? '' : 's'} · drank on ${t.drinking_days} of ${d.days} days</div>
      <div class="now-line"><span class="now-dot ${nowCls}"></span><span>${esc(nowTxt)}</span></div></div>`;

    if (!t.count) {
      html += `<div class="dash-empty">Nothing logged in the last ${d.days} days.<br>A quiet week. Your liver says thanks.</div>`;
      html += footer(d);
      scroll.innerHTML = html;
      return;
    }

    html += `<div class="kpis">
      ${kpi('Peak BAC', bac(t.peak_bac), '', t.peak_ts ? `${esc(fmtWhen(t.peak_ts))}${t.peak_session ? ' · ' + esc(t.peak_session) : ''}` : '')}
      ${kpi('Average BAC', bac(t.avg_bac), '', 'time-weighted, while above zero')}
      ${kpi('Time over 0.08', hrs(t.hours_over_08), '', t.hours_over_08 > 0 ? 'legally impaired to drive' : 'never crossed it')}
      ${kpi('Time buzzed', hrs(t.hours_buzzed), '', 'with any alcohol on board')}
      ${kpi('Per session', n1(t.avg_per_session), 'drinks', `${n1(t.avg_per_drinking_day)} per drinking day`)}
      ${kpi('Calories', Math.round(t.calories).toLocaleString(), 'kcal', `≈ ${n1(t.calories / 900)} burrito bowls`)}
    </div>`;

    html += `<div class="card"><div class="card-title">Drinks per day</div>${barChart(d.by_day, plotW)}
      <a class="table-toggle" data-toggle="daytable">Show table</a>
      <div id="daytable" hidden>${dayTable(d.by_day)}</div></div>`;

    html += `<div class="card"><div class="card-title">BAC over the ${d.days === 7 ? 'week' : 'month'}</div>${lineChart(d.curve, d, plotW)}
      <div class="card-note">Orange line is 0.08. Peak ${bac(t.peak_bac)}${t.peak_ts ? ' on ' + esc(fmtWhen(t.peak_ts)) : ''}.</div></div>`;

    html += `<div class="card"><div class="card-title">What you drank</div>${hbars(d.by_type)}
      ${d.favorites.length ? `<div class="card-note" style="margin-top:12px">Go-to: ${d.favorites.slice(0, 3).map((f) => `<b style="color:#fff;font-weight:600">${esc(f.raw)}</b> ×${f.count}`).join(' · ')}</div>` : ''}</div>`;

    html += `<div class="card"><div class="card-title">Sessions</div><div class="slist">${d.sessions.map(sessionRow).join('')}</div></div>`;

    html += `<div class="facts">${facts(d)}</div>`;
    html += footer(d);
    scroll.innerHTML = html;

    scroll.querySelectorAll('[data-toggle]').forEach((a) => {
      a.addEventListener('click', () => {
        const tgt = $(a.dataset.toggle);
        tgt.hidden = !tgt.hidden;
        a.textContent = tgt.hidden ? 'Show table' : 'Hide table';
      });
    });
    wireBarTips(scroll);
    wireLineTips(scroll, d);
  }

  function kpi(label, value, unit, sub) {
    return `<div class="kpi"><div class="kpi-label">${label}</div><div><div class="kpi-value">${value}${unit ? `<small>${unit}</small>` : ''}</div>${sub ? `<div class="kpi-sub">${sub}</div>` : ''}</div></div>`;
  }

  function footer(d) {
    const m = d.model;
    return `<div class="dash-foot">Widmark estimate for ${m.weight_kg} kg, r ${m.r}, burning ${m.metabolism}%/hr. Days follow this phone’s clock. Not a breathalyzer.</div>`;
  }

  /* ------------------------------------------------------------ bar chart */
  function niceMax(v) {
    if (v <= 0) return 4;
    const steps = [1, 2, 4, 5, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100];
    for (const s of steps) if (v <= s) return s;
    return Math.ceil(v / 50) * 50;
  }
  function barChart(rows, W) {
    const H = 170, padL = 26, padR = 6, padT = 18, padB = 24;
    const pw = W - padL - padR, ph = H - padT - padB;
    const max = niceMax(Math.max(...rows.map((r) => r.std)) * 1.05);
    const n = rows.length;
    const slot = pw / n;
    const bw = Math.min(24, slot * 0.62);
    const maxIdx = rows.reduce((m, r, i) => (r.std > rows[m].std ? i : m), 0);
    const ticks = max <= 4 ? [0, 2, 4].filter((v) => v <= max) : [0, max / 2, max];
    let s = `<svg class="chart" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Drinks per day">`;
    ticks.forEach((v) => {
      const y = padT + ph - (v / max) * ph;
      s += `<line class="${v === 0 ? 'base' : 'grid'}" x1="${padL}" x2="${W - padR}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"/>`;
      s += `<text x="${padL - 6}" y="${(y + 4).toFixed(1)}" text-anchor="end">${n1(v)}</text>`;
    });
    rows.forEach((r, i) => {
      const cx = padL + slot * i + slot / 2;
      const h = Math.max(r.std > 0 ? 2 : 0, (r.std / max) * ph);
      const y = padT + ph - h;
      const x = cx - bw / 2;
      if (h > 0) s += `<path class="bar" d="${roundTop(x, y, bw, h, 4)}"/>`;
      if (r.std > 0 && (i === maxIdx || r.today)) s += `<text class="lbl" x="${cx.toFixed(1)}" y="${(y - 5).toFixed(1)}" text-anchor="middle">${n1(r.std)}</text>`;
      const showLabel = n <= 7 || i % 5 === 0 || r.today;
      if (showLabel) s += `<text x="${cx.toFixed(1)}" y="${H - 8}" text-anchor="middle" ${r.today ? 'class="lbl"' : ''}>${esc(n <= 7 ? r.label.slice(0, 3) : r.date.slice(5).replace('-', '/'))}</text>`;
      s += `<rect class="bar hit" data-i="${i}" x="${(padL + slot * i).toFixed(1)}" y="${padT}" width="${slot.toFixed(1)}" height="${ph}"/>`;
    });
    s += '</svg>';
    return `<div class="chart-wrap" style="position:relative">${s}</div>`;
  }
  function roundTop(x, y, w, h, r) {
    r = Math.min(r, h, w / 2);
    return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`;
  }
  function wireBarTips(scroll) {
    const wrap = scroll.querySelector('.chart-wrap');
    if (!wrap) return;
    let tip = null;
    const show = (e) => {
      const hit = e.target.closest('rect.hit');
      if (!hit) { hide(); return; }
      const r = data.by_day[Number(hit.dataset.i)];
      if (!tip) { tip = document.createElement('div'); tip.className = 'tip'; wrap.appendChild(tip); }
      const dt = new Date(r.date + 'T12:00:00');
      tip.innerHTML = `<b>${esc(dt.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }))}</b><br>${n1(r.std)} drinks · ${r.count} logged${r.peak ? `<br>peak ${bac(r.peak)}` : ''}`;
      const b = hit.getBoundingClientRect(), wb = wrap.getBoundingClientRect();
      tip.style.left = `${b.left - wb.left + b.width / 2}px`;
      tip.style.top = `${Math.max(34, b.top - wb.top + 8)}px`;
    };
    const hide = () => { if (tip) { tip.remove(); tip = null; } };
    wrap.addEventListener('pointerdown', show);
    wrap.addEventListener('pointermove', (e) => { if (e.buttons || e.pointerType === 'mouse') show(e); });
    wrap.addEventListener('pointerleave', hide);
    wrap.addEventListener('pointerup', () => setTimeout(hide, 1200));
  }

  /* ----------------------------------------------------------- line chart */
  function lineChart(curve, d, W) {
    const H = 190, padL = 34, padR = 8, padT = 12, padB = 24;
    const pw = W - padL - padR, ph = H - padT - padB;
    const vals = curve.values;
    const peak = Math.max(0.1, ...vals) * 1.12;
    const yMax = Math.ceil(peak / 0.05) * 0.05;
    const x = (i) => padL + (i / Math.max(1, vals.length - 1)) * pw;
    const y = (v) => padT + ph - (v / yMax) * ph;
    let s = `<svg class="chart line-chart" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="BAC over time">`;
    for (let v = 0; v <= yMax + 1e-9; v += 0.05) {
      s += `<line class="${v === 0 ? 'base' : 'grid'}" x1="${padL}" x2="${W - padR}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`;
      s += `<text x="${padL - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v.toFixed(2)}</text>`;
    }
    // day ticks at local midnight
    const dayMs = 86400000;
    const firstMid = startOfLocalDay(curve.start);
    for (let t = firstMid; t <= d.now; t += dayMs) {
      if (t < curve.start) continue;
      const i = (t - curve.start) / curve.step_ms;
      const xx = x(i);
      s += `<line class="grid" x1="${xx.toFixed(1)}" x2="${xx.toFixed(1)}" y1="${padT}" y2="${padT + ph}"/>`;
      if (d.days <= 7 || new Date(t).getDate() % 5 === 1) s += `<text x="${(xx + 3).toFixed(1)}" y="${H - 8}">${esc(d.days <= 7 ? fmtDay(t) : fmtDate(t))}</text>`;
    }
    if (0.08 <= yMax) {
      s += `<line class="ref" x1="${padL}" x2="${W - padR}" y1="${y(0.08).toFixed(1)}" y2="${y(0.08).toFixed(1)}"/>`;
      s += `<text class="ref-t" x="${padL + 4}" y="${(y(0.08) - 4).toFixed(1)}">0.08</text>`;
    }
    let path = '', area = '';
    vals.forEach((v, i) => { path += `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`; });
    if (vals.length) area = `${path}L${x(vals.length - 1).toFixed(1)},${y(0).toFixed(1)}L${x(0).toFixed(1)},${y(0).toFixed(1)}Z`;
    s += `<path class="area" d="${area}"/><path class="line" d="${path}"/>`;
    s += `<g class="crosshair" style="display:none"><line class="cross" y1="${padT}" y2="${padT + ph}"/><circle class="dot" r="4"/></g>`;
    s += '</svg>';
    return `<div class="line-wrap" style="position:relative" data-padl="${padL}" data-pw="${pw}">${s}</div>`;
  }
  function startOfLocalDay(ts) { const d = new Date(ts); d.setHours(0, 0, 0, 0); return d.getTime(); }
  function wireLineTips(scroll, d) {
    const wrap = scroll.querySelector('.line-wrap');
    if (!wrap) return;
    const svg = wrap.querySelector('svg');
    const g = svg.querySelector('.crosshair');
    const line = g.querySelector('line'), dot = g.querySelector('circle');
    const padL = Number(wrap.dataset.padl), pw = Number(wrap.dataset.pw);
    const vals = d.curve.values;
    const H = 190, padT = 12, padB = 24, ph = H - padT - padB;
    const peak = Math.max(0.1, ...vals) * 1.12;
    const yMax = Math.ceil(peak / 0.05) * 0.05;
    let tip = null;
    const move = (e) => {
      const r = svg.getBoundingClientRect();
      const scale = r.width / svg.viewBox.baseVal.width;
      const px = (e.clientX - r.left) / scale;
      const frac = Math.min(1, Math.max(0, (px - padL) / pw));
      const i = Math.round(frac * (vals.length - 1));
      const xx = padL + (i / Math.max(1, vals.length - 1)) * pw;
      const yy = padT + ph - (vals[i] / yMax) * ph;
      g.style.display = '';
      line.setAttribute('x1', xx); line.setAttribute('x2', xx);
      dot.setAttribute('cx', xx); dot.setAttribute('cy', yy);
      if (!tip) { tip = document.createElement('div'); tip.className = 'tip'; wrap.appendChild(tip); }
      const t = d.curve.start + i * d.curve.step_ms;
      tip.innerHTML = `<b>${esc(fmtWhen(t))}</b><br>BAC ${bac(vals[i])}`;
      tip.style.left = `${Math.min(r.width - 60, Math.max(60, xx * scale))}px`;
      tip.style.top = `${Math.max(36, yy * scale - 6)}px`;
    };
    const hide = () => { g.style.display = 'none'; if (tip) { tip.remove(); tip = null; } };
    wrap.addEventListener('pointerdown', (e) => { e.preventDefault(); move(e); });
    wrap.addEventListener('pointermove', (e) => { if (e.buttons || e.pointerType === 'mouse') move(e); });
    wrap.addEventListener('pointerleave', hide);
    wrap.addEventListener('pointerup', () => setTimeout(hide, 1500));
    wrap.style.touchAction = 'pan-y';
  }

  /* -------------------------------------------------- bars / tables / rows */
  function hbars(types) {
    if (!types.length) return '<div class="card-note">Nothing yet.</div>';
    const max = Math.max(...types.map((t) => t.std));
    return types.map((t) => `<div class="hbar-row"><div class="hbar-name">${esc(t.type)}</div><div class="hbar-track"><div class="hbar-fill" style="width:${((t.std / max) * 100).toFixed(1)}%"></div></div><div class="hbar-val">${n1(t.std)}</div></div>`).join('')
      + '<div class="card-note">Standard drinks by type. One standard drink is 14 g of alcohol.</div>';
  }
  function dayTable(rows) {
    return `<table class="dtable"><tr><th>Day</th><th>Drinks</th><th>Logged</th><th>Peak</th></tr>${rows.map((r) => `<tr><td>${esc(r.label)} ${esc(r.date.slice(5).replace('-', '/'))}</td><td>${n1(r.std)}</td><td>${r.count}</td><td>${r.peak ? bac(r.peak) : '—'}</td></tr>`).join('')}</table>`;
  }
  function sessionRow(s) {
    const when = `${fmtDay(s.first_ts)} ${fmtDate(s.first_ts)}`;
    const span = `${fmtTime(s.first_ts)}–${fmtTime(s.last_ts)}`;
    return `<div class="srow"><div class="avatar lv${level(s.std)}"><span class="av-count">${Math.round(s.std)}</span></div>
      <div class="srow-main"><div class="srow-name"><span>${esc(s.name)}</span><span>${esc(when)}</span></div>
      <div class="srow-sub">${s.count} drink${s.count === 1 ? '' : 's'} · peak ${bac(s.peak)} · ${span}${s.hours_over_08 > 0 ? ` · ${hrs(s.hours_over_08)} over .08` : ''}</div></div></div>`;
  }

  function facts(d) {
    const t = d.totals;
    const out = [];
    out.push(fact('🍺', `${n1(t.std / STD_ULTRA)} Ultras`, 'your total, measured in 12 oz Michelob Ultras'));
    if (t.hours_buzzed > 0) out.push(fact('🧬', hrs(t.hours_buzzed), 'your liver was on the clock'));
    if (t.biggest_day) out.push(fact('📅', t.biggest_day, `biggest day · ${n1(t.biggest_day_std)} drinks`));
    out.push(fact('🧊', `${t.dry_days} dry day${t.dry_days === 1 ? '' : 's'}`, `out of the last ${d.days}`));
    const hourTotal = d.hours.reduce((a, b) => a + b, 0);
    if (hourTotal) {
      const h = d.hours.indexOf(Math.max(...d.hours));
      out.push(fact('⏰', hourLabel(h), 'the hour you log the most drinks'));
    }
    if (d.favorites.length) out.push(fact('🥇', d.favorites[0].raw, `ordered ${d.favorites[0].count} time${d.favorites[0].count === 1 ? '' : 's'}`));
    if (t.hours_over_08 > 0) out.push(fact('🚕', hrs(t.hours_over_08), 'spent over 0.08 · uber territory'));
    if (t.sessions > 1) out.push(fact('📊', `${n1(t.avg_per_session)} / session`, 'average drinks per session'));
    return out.join('');
  }
  function fact(emoji, big, text) {
    return `<div class="fact"><div class="fact-emoji">${emoji}</div><div><div class="fact-big">${esc(big)}</div><div class="fact-text">${esc(text)}</div></div></div>`;
  }

  return { open, close };
})();
