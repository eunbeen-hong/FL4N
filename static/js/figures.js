(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const F = 'static/figures/';
  const D = window.FL4N_FIG || {};
  const MODEL_NAMES = { ours: 'FL4N (Ours)', gt: 'Ground truth', c4g: 'C4G', neoverse: 'NeoVerse', movies: 'MoVieS', '4dgt': '4DGT' };
  const lb = (srcs, cap) => window.FL4N_lightbox && window.FL4N_lightbox(srcs, cap);

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  function btn(cls, html, on) { const b = el('button', cls, html); b.type = 'button'; if (on) b.addEventListener('click', on); return b; }
  function pick(container, items, on, active = 0, cls = 'chip') {
    container.innerHTML = '';
    const bs = items.map((it, k) => {
      const b = btn(cls + (k === active ? ' active' : ''), it.label, () => { bs.forEach(x => x.classList.remove('active')); b.classList.add('active'); on(it, k); });
      container.appendChild(b);
      return b;
    });
    return bs;
  }
  function mount(root, ...els) { const cap = root.querySelector(':scope > figcaption'); els.forEach(e => (cap ? root.insertBefore(e, cap) : root.appendChild(e))); }
  function enlarge(get, cap) { return btn('fig-enlarge', '<span>⤢</span> Enlarge', () => lb(get(), typeof cap === 'function' ? cap() : cap)); }

  function wipe(opts) {
    const root = el('div', 'wipe');
    const L = el('img', 'wl'), R = el('img', 'wr');
    L.alt = opts.leftLabel; R.alt = opts.rightLabel;
    const line = el('div', 'wipe-line'), handle = btn('wipe-handle', '<span>↔</span>');
    handle.setAttribute('role', 'slider'); handle.setAttribute('aria-label', 'comparison divider'); handle.setAttribute('aria-valuemin', 0); handle.setAttribute('aria-valuemax', 100);
    const labL = el('span', 'wipe-lab l', opts.leftLabel), labR = el('span', 'wipe-lab r', opts.rightLabel);
    mount(root, L, R, line, handle, labL, labR);
    let p = 50, drag = false;
    function set(v) {
      p = Math.max(0, Math.min(100, v));
      R.style.clipPath = `inset(0 0 0 ${p}%)`;
      line.style.left = handle.style.left = p + '%';
      handle.setAttribute('aria-valuenow', Math.round(p));
      labL.style.opacity = p < 12 ? 0 : 1; labR.style.opacity = p > 88 ? 0 : 1;
      ctrl.forEach((b, i) => b.classList.toggle('active', (i === 0 && p >= 99) || (i === 1 && p > 1 && p < 99) || (i === 2 && p <= 1)));
    }
    function fromEvent(e) { const r = root.getBoundingClientRect(); set((e.clientX - r.left) / r.width * 100); }
    root.addEventListener('pointerdown', e => { drag = true; root.setPointerCapture(e.pointerId); fromEvent(e); });
    root.addEventListener('pointermove', e => { if (drag) fromEvent(e); });
    root.addEventListener('pointerup', () => (drag = false));
    root.addEventListener('pointercancel', () => (drag = false));
    handle.addEventListener('keydown', e => { if (e.key === 'ArrowLeft') { set(p - 4); e.preventDefault(); } if (e.key === 'ArrowRight') { set(p + 4); e.preventDefault(); } });
    const ctrls = el('div', 'wipe-ctrl');
    const ctrl = [btn('', opts.leftLabel + ' only', () => set(100)), btn('', 'Split view', () => set(50)), btn('', opts.rightLabel + ' only', () => set(0))];
    ctrl.forEach(b => ctrls.appendChild(b));
    set(50);
    return {
      root, ctrls, set,
      left: (src) => { L.src = src; }, right: (src) => { R.src = src; },
      labels: (l, r) => { labL.textContent = l; labR.textContent = r; ctrl[0].textContent = l + ' only'; ctrl[2].textContent = r + ' only'; },
      srcs: () => [L.src, R.src],
    };
  }

  function preload(srcs) { srcs.forEach(s => { const i = new Image(); i.src = s; }); }

  function archFig(root) {
    const stage = el('div', 'arch-stage'), cards = el('div', 'arch-steps'), cap = el('div', 'arch-cap');
    mount(root, cards, stage, cap);
    Promise.all([fetch(F + 'arch.svg').then(r => r.text()), fetch(F + 'arch_steps.json').then(r => r.json())]).then(([svg, steps]) => {
      stage.innerHTML = svg;
      const all = { key: 'all', no: '', title: 'Full pipeline', text: 'Context frames feed a frozen static encoder and a small trainable dynamic encoder. The residual is adapted to the target time, added to the static latent and decoded by the frozen renderer at the target view. Click a stage to isolate it.' };
      const items = [all, ...steps];
      let cur = 'all';
      function apply(k) { cur = k; root.dataset.step = k; const s = items.find(i => i.key === k); cap.innerHTML = `<strong>${s.no ? s.no + ' · ' : ''}${s.title}</strong><p>${s.text}</p>`; bs.forEach((b, i) => b.setAttribute('aria-pressed', items[i].key === k)); }
      const bs = items.map(s => {
        const b = btn('arch-step', `<span class="no">${s.no || '●'}</span><span class="t">${s.title}</span>`, () => apply(cur === s.key && s.key !== 'all' ? 'all' : s.key));
        b.addEventListener('mouseenter', () => { if (cur === 'all') root.dataset.step = s.key; });
        b.addEventListener('mouseleave', () => { root.dataset.step = cur; });
        cards.appendChild(b);
        return b;
      });
      apply('all');
    }).catch(() => { stage.innerHTML = '<img src="static/images/mainarch_0926.webp" alt="FL4N architecture">'; });
  }

  function teaserFig(root) {
    fetch(F + 'teaser/teaser.json').then(r => r.json()).then(m => {
      const ctrls = el('div', 'tz-ctrl'), chips = el('div', 'chips'), grid = el('div', 'tz-grid');
      const padWrap = el('div', 'tz-padwrap'), pad = el('div', 'tz-pad'), info = el('div', 'tz-info'), panels = el('div', 'tz-panels');
      const padHead = el('div', 'tz-axes', `<span class="ax-t">Time →</span><span class="ax-v">View ↓</span>`);
      info.innerHTML = `<span class="k"><i class="sw obs"></i>observed input frame (one per camera)</span><span class="k"><i class="sw"></i>never observed: rendered</span><span class="k"><i class="sw cur"></i>current cell</span><span class="k hint">Hover the grid to pick a cell; it auto-plays otherwise.</span>`;
      padWrap.append(padHead, pad, info);
      const P = {};
      [['ours', 'FL4N (Ours)'], ['gt', 'Ground truth'], ['c4g', 'C4G'], ['neoverse', 'NeoVerse'], ['movies', 'MoVieS'], ['4dgt', '4DGT']].forEach(([k, lab]) => {
        const f = el('figure', 'tz-panel ' + k); const i = el('img'); i.alt = lab;
        f.append(i, el('figcaption', '', lab)); panels.appendChild(f); P[k] = { f, i, cap: f.lastChild, lab };
      });
      grid.append(padWrap, panels);
      ctrls.append(chips, enlarge(() => [P.ours.i.src, P.gt.i.src], () => `${P.ours.cap.textContent} (left) vs. ground truth (right)`));
      mount(root, ctrls, grid);
      let sc = null, keep = [], cells = [], cur = [0, 0], timer = null, hover = false, step = 0;
      const src = (model, v, t) => `${F}teaser/${sc.id}/${v === t ? 'gt' : model}_v${String(v).padStart(2, '0')}_f${String(t).padStart(2, '0')}.webp`;
      function go(v, t) {
        cur = [v, t];
        cells.forEach(c => c.classList.toggle('cur', +c.dataset.v === v && +c.dataset.t === t));
        const obs = v === t;
        Object.entries(P).forEach(([k, p]) => { p.i.src = src(k, v, t); p.f.classList.toggle('dim', obs && k !== 'gt'); });
        P.ours.cap.textContent = obs ? `Observed input frame · view ${v + 1}, time ${t + 1}` : `FL4N (Ours) · view ${v + 1}, time ${t + 1}`;
        P.gt.cap.textContent = obs ? `Ground truth (= input) · view ${v + 1}, time ${t + 1}` : `Ground truth · view ${v + 1}, time ${t + 1}`;
      }
      function tick() { const n = keep.length; step = (step + 1) % (n * n); go(keep[Math.floor(step / n)], keep[step % n]); }
      function start() { if (!timer) timer = setInterval(() => { if (!hover) tick(); }, 420); }
      function stop() { clearInterval(timer); timer = null; }
      function pickScene(s) {
        sc = s; keep = s.keep; cells = []; pad.innerHTML = ''; pad.style.setProperty('--n', keep.length);
        keep.forEach(v => keep.forEach(t => {
          const c = el('button', 'tz-cell' + (v === t ? ' obs' : '')); c.type = 'button'; c.dataset.v = v; c.dataset.t = t;
          c.title = v === t ? `Observed input: view ${v + 1} at time ${t + 1}` : `Render view ${v + 1} at time ${t + 1}`;
          c.addEventListener('mouseenter', () => { step = keep.indexOf(v) * keep.length + keep.indexOf(t); go(v, t); });
          c.addEventListener('click', () => go(v, t));
          pad.appendChild(c); cells.push(c);
        }));
        preload(keep.flatMap(v => keep.map(t => src('ours', v, t))));
        step = 0; go(keep[0], keep[0]);
      }
      pad.addEventListener('mouseenter', () => (hover = true));
      pad.addEventListener('mouseleave', () => (hover = false));
      pick(chips, m.scenes.map(s => ({ label: s.name, s })), it => pickScene(it.s), Math.max(0, m.scenes.findIndex(s => s.id === 'Skating')));
      pickScene(m.scenes.find(s => s.id === 'Skating') || m.scenes[0]);
      new IntersectionObserver(es => es.forEach(e => (e.isIntersecting ? start() : stop())), { threshold: 0.05 }).observe(root);
    });
  }

  function evalFig(root) {
    const data = D.evalsettings || [];
    const DESC = {
      nvs: 'Novel view synthesis: context frames come from one camera per timestamp (the diagonal). Held-out cameras are rendered at the observed timestamps only.',
      ctvs: 'Cross-time view synthesis: the same monocular sweep, but every camera must be rendered at every timestamp, so most targets are unobserved in both view and time.',
      nts: 'Novel time synthesis: on moving-camera monocular videos the context is temporally strided and the model interpolates the skipped frames along the same trajectory.',
    };
    const wrap = el('div', 'ev-wrap'), cap = el('div', 'ev-cap'), legend = el('div', 'ev-legend', `<button type="button" data-hl="ctx"><i class="sw ctx"></i>Context frame (input)</button><button type="button" data-hl="tgt"><i class="sw tgt"></i>Evaluation target</button>`);
    data.forEach(p => {
      const panel = el('div', 'ev-panel');
      const g = el('div', 'ev-grid'); g.style.setProperty('--n', p.rows[0].length);
      p.rows.forEach((r, vi) => r.forEach((c, ti) => { const i = el('img', 'ev-cell ' + c.role); i.src = `${F}evalsettings/${c.img}`; i.alt = ''; i.title = `view ${vi + 1}, time ${ti + 1}${c.role === 'ctx' ? ' · input' : c.role === 'tgt' ? ' · target' : ''}`; g.appendChild(i); }));
      panel.append(el('div', 'ev-axes', `<span class="ax-t">Time →</span><span class="ax-v">View ↓</span>`), g, el('div', 'ev-title', p.title));
      panel.addEventListener('mouseenter', () => { cap.textContent = DESC[p.key]; $$('.ev-panel', wrap).forEach(x => x.classList.toggle('active', x === panel)); });
      panel.addEventListener('click', () => { cap.textContent = DESC[p.key]; $$('.ev-panel', wrap).forEach(x => x.classList.toggle('active', x === panel)); });
      wrap.appendChild(panel);
    });
    $$('button', legend).forEach(b => { b.addEventListener('mouseenter', () => (root.dataset.hl = b.dataset.hl)); b.addEventListener('mouseleave', () => (root.dataset.hl = '')); b.addEventListener('click', () => (root.dataset.hl = root.dataset.hl === b.dataset.hl ? '' : b.dataset.hl)); });
    cap.textContent = 'Hover a protocol to read how its context and targets are sampled.';
    mount(root, legend, wrap, cap);
  }

  function compareStaticFig(root) {
    const scenes = D.comparestatic || [];
    const tabs = el('div', 'tabs'), strip = el('div', 'cs-strip'), row = el('div', 'cs-row');
    const staticCard = el('figure', 'cs-static'); const sImg = el('img'); staticCard.append(sImg, el('figcaption', '', '<b>Static latent only</b><span>no target time: the frozen prior cannot place the moving subject</span>'));
    const w = wipe({ leftLabel: 'FL4N (static + residual)', rightLabel: 'Ground truth' });
    const right = el('div', 'cs-right'); const chips = el('div', 'chips');
    right.append(w.root, chips, w.ctrls);
    row.append(staticCard, right);
    let cur = scenes[0], t = 0;
    function show() {
      sImg.src = `${F}compare_static/${cur.static}`;
      w.left(`${F}compare_static/${cur.ours[t]}`); w.right(`${F}compare_static/${cur.gt[t]}`);
      $$('.cs-thumb', strip).forEach(x => x.classList.remove('cur'));
    }
    function pickScene(it) { cur = it.s; t = 0; strip.innerHTML = '<span class="cs-lab">Context frames →</span>'; cur.inputs.forEach(src => { const i = el('img', 'cs-thumb'); i.src = `${F}compare_static/${src}`; strip.appendChild(i); }); pick(chips, cur.gt.map((_, k) => ({ label: `Target time ${k + 1}`, k })), it => { t = it.k; show(); }); show(); }
    pick(tabs, scenes.map(s => ({ label: s.title, s })), pickScene, 0, 'tab');
    pickScene({ s: scenes[0] });
    const tools = el('div', 'fig-tools'); tools.append(tabs, enlarge(() => [sImg.src, ...w.srcs()], 'Static latent only · FL4N · ground truth'));
    mount(root, tools, strip, row);
  }

  function scrubFig(root, kind) {
    const d = kind === 'gate' ? D.gatefeature : D.dynfeature;
    if (!d) return;
    const dir = kind === 'gate' ? 'gatefeature/' : 'dynfeature/';
    const n = d.rows[0].length;
    const panels = el('div', 'sc-panels'), strip = el('div', 'sc-strip'), ctrl = el('div', 'sc-ctrl');
    const imgs = d.rows.map((_, ri) => { const f = el('figure', 'sc-panel'); const i = el('img'); f.append(i, el('figcaption', '', d.labels[ri])); panels.appendChild(f); return i; });
    let ov = null, ovGate = null, ovRange = null;
    if (kind === 'gate') {
      const f = el('figure', 'sc-panel sc-overlay'); ov = el('img'); ovGate = el('img', 'ov'); ovRange = el('input'); ovRange.type = 'range'; ovRange.min = 0; ovRange.max = 100; ovRange.value = 55;
      ovRange.addEventListener('input', () => (ovGate.style.opacity = ovRange.value / 100));
      const lab = el('label', '', 'Overlay opacity '); lab.appendChild(ovRange);
      f.append(ov, ovGate, el('figcaption', '', 'Gate over frame'), lab); panels.appendChild(f); ovGate.style.opacity = .55;
    }
    let t = 0, timer = null;
    const thumbs = d.rows[0].map((src, k) => { const b = btn('sc-thumb', `<img src="${F}${dir}${src}" alt=""><span>t${k + 1}</span>`, () => { stop(); set(k); }); b.addEventListener('mouseenter', () => { if (!timer) set(k); }); strip.appendChild(b); return b; });
    function set(k) { t = k; imgs.forEach((i, ri) => (i.src = `${F}${dir}${d.rows[ri][t]}`)); if (ov) { ov.src = `${F}${dir}${d.rows[0][t]}`; ovGate.src = `${F}${dir}${d.rows[1][t]}`; } thumbs.forEach((b, i) => b.classList.toggle('cur', i === t)); }
    const play = btn('chip', '▶ Play', () => (timer ? stop() : start()));
    function start() { play.textContent = '❚❚ Pause'; play.classList.add('active'); timer = setInterval(() => set((t + 1) % n), 650); }
    function stop() { clearInterval(timer); timer = null; play.textContent = '▶ Play'; play.classList.remove('active'); }
    ctrl.append(play, el('span', 'sc-hint', 'Hover or click a context frame to move through time.'), enlarge(() => imgs.map(i => i.src), () => `${d.labels.join(' · ')} at t${t + 1}`));
    preload(d.rows.flat().map(s => `${F}${dir}${s}`));
    mount(root, panels, strip, ctrl);
    set(0);
    new IntersectionObserver(es => es.forEach(e => { if (!e.isIntersecting) stop(); })).observe(root);
  }

  function staticFeatFig(root) {
    const d = D.staticfeat; if (!d) return;
    const grid = el('div', 'sf-grid'); grid.style.setProperty('--n', d.rows[0].length);
    const cells = [];
    d.rows.forEach((r, ri) => {
      grid.appendChild(el('div', 'sf-lab', d.labels[ri]));
      r.forEach((src, ci) => { const c = el('div', 'sf-cell'); const i = el('img'); i.src = `${F}supp_staticfeat/${src}`; c.appendChild(i); c.dataset.c = ci; grid.appendChild(c); cells.push(c); });
    });
    d.boxes.forEach(b => { const c = cells[b.r * d.rows[0].length + b.c]; const box = el('i', 'sf-box'); box.style.cssText = `left:${b.l * 100}%;top:${b.t * 100}%;width:${b.w * 100}%;height:${b.h * 100}%`; c.appendChild(box); });
    cells.forEach(c => { c.addEventListener('mouseenter', () => (grid.dataset.col = c.dataset.c)); c.addEventListener('mouseleave', () => (grid.dataset.col = '')); });
    const tg = btn('chip active', 'Show overlap boxes', () => { root.classList.toggle('noboxes'); tg.classList.toggle('active'); });
    const ctrl = el('div', 'fig-tools'); ctrl.append(tg, el('span', 'sc-hint', 'Hover a column to pair a context frame with its static latent.'));
    mount(root, grid, ctrl);
  }

  function residualGridFig(root) {
    const d = D.residualgrid; if (!d) return;
    const n = d.rgb[0].length;
    const grid = el('div', 'rg-grid'); grid.style.setProperty('--n', n);
    d.rgb.forEach((r, vi) => r.forEach((src, ti) => { const c = el('div', 'rg-cell'); const a = el('img', 'a'), b = el('img', 'b'); a.src = `${F}supp_nn_residualfeat/${src}`; b.src = `${F}supp_nn_residualfeat/${d.res[vi][ti]}`; c.title = `view ${vi + 1}, time ${ti + 1}`; c.append(a, b); grid.appendChild(c); }));
    const range = el('input'); range.type = 'range'; range.min = 0; range.max = 100; range.value = 0;
    range.addEventListener('input', () => root.style.setProperty('--mix', range.value / 100));
    const ctrl = el('div', 'rg-ctrl');
    const bA = btn('chip active', 'RGB + dynamic mask', () => { range.value = 0; root.style.setProperty('--mix', 0); bA.classList.add('active'); bB.classList.remove('active'); });
    const bB = btn('chip', 'Residual latent', () => { range.value = 100; root.style.setProperty('--mix', 1); bB.classList.add('active'); bA.classList.remove('active'); });
    range.addEventListener('input', () => { bA.classList.toggle('active', range.value == 0); bB.classList.toggle('active', range.value == 100); });
    ctrl.append(bA, range, bB, el('span', 'sc-hint', 'Drag to blend, or hover a cell to flip it.'));
    const axes = el('div', 'tz-axes', `<span class="ax-t">Time →</span><span class="ax-v">View ↓</span>`);
    const wrap = el('div', 'rg-wrap'); wrap.append(axes, grid);
    root.style.setProperty('--mix', 0);
    mount(root, ctrl, wrap);
  }

  function dynmaskFig(root) {
    const d = D.dynmask; if (!d) return;
    const n = d.rows[0].length;
    const strip = el('div', 'dm-strip'), w = wipe({ leftLabel: 'VGGT4D', rightLabel: 'FL4N (Ours)' });
    let s = 0, left = 0;
    const thumbs = d.rows[1].map((src, k) => btn('dm-thumb', `<img src="${F}dynmask/${src}" alt="">`, () => { s = k; show(); }));
    thumbs.forEach(b => strip.appendChild(b));
    const chips = el('div', 'chips');
    pick(chips, [{ label: 'Compare with VGGT4D', k: 0 }, { label: 'Compare with ground truth', k: 2 }], it => { left = it.k; w.labels(d.labels[left], d.labels[1]); show(); });
    function show() { w.left(`${F}dynmask/${d.rows[left][s]}`); w.right(`${F}dynmask/${d.rows[1][s]}`); thumbs.forEach((b, i) => b.classList.toggle('cur', i === s)); }
    const tools = el('div', 'fig-tools'); tools.append(chips, enlarge(() => w.srcs(), () => `${d.labels[left]} (left) vs. FL4N (right)`));
    mount(root, strip, w.root, w.ctrls, tools);
    show();
  }

  function qualFig(root) {
    const d = D.qual; if (!d) return;
    const gtIdx = d.models.indexOf('GT'), oursIdx = d.models.findIndex(m => /ours/i.test(m));
    const tabs = el('div', 'tabs'), strip = el('div', 'ql-strip'), w = wipe({ leftLabel: d.models[oursIdx], rightLabel: 'Ground truth' });
    let ds = 0, m = oursIdx;
    const thumbs = d.models.map((name, k) => { const b = btn('ql-thumb' + (k === gtIdx ? ' gt' : ''), `<img alt=""><span>${name}</span>`, () => { if (k !== gtIdx) { m = k; show(); } }); strip.appendChild(b); return b; });
    function show() { thumbs.forEach((b, k) => { $('img', b).src = `${F}qual/${d.rows[ds][k]}`; b.classList.toggle('cur', k === m); }); w.labels(d.models[m], 'Ground truth'); w.left(`${F}qual/${d.rows[ds][m]}`); w.right(`${F}qual/${d.rows[ds][gtIdx]}`); }
    pick(tabs, d.datasets.map((name, k) => ({ label: name, k })), it => { ds = it.k; show(); }, 0, 'tab');
    const tools = el('div', 'fig-tools'); tools.append(tabs, enlarge(() => w.srcs(), () => `${d.models[m]} (left) vs. ground truth (right) on ${d.datasets[ds]}`));
    mount(root, tools, strip, w.root, w.ctrls);
    show();
  }

  function nframeFig(root) {
    const raw = [[3, 21.29], [4, 21.29], [5, 21.45], [6, 21.92], [7, 22.41], [8, 23.17], [9, 23.44], [10, 23.06], [11, 22.79], [12, 22.68], [13, 22.68], [14, 22.72], [15, 22.72], [16, 22.83], [17, 22.95], [18, 22.79], [19, 22.79], [20, 22.79], [21, 22.79], [22, 22.79], [23, 22.79], [24, 22.79], [25, 22.79], [26, 22.72], [27, 22.63], [28, 22.63], [29, 22.57], [30, 22.63], [31, 22.68], [32, 22.68], [33, 22.68]];
    const data = raw.map(([n, v]) => [n, n <= 9 ? 20.35 + (v - 21.29) * (23.44 - 20.35) / (23.44 - 21.29) : 23.44 - (23.44 - v) * (23.44 - 22.93) / (23.44 - 22.68)]);
    const W = 640, H = 300, L = 54, R = 16, T = 18, B = 44, x0 = 2, x1 = 34, y0 = 18, y1 = 24.5;
    const X = n => L + (n - x0) / (x1 - x0) * (W - L - R), Y = v => T + (y1 - v) / (y1 - y0) * (H - T - B);
    let s = `<svg class="nf-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="PSNR versus number of context frames on CamxTime">`;
    for (let v = 18; v <= 24; v += 1) s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text class="tick" x="${L - 8}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`;
    for (let n = 4; n <= 32; n += 4) s += `<text class="tick" x="${X(n)}" y="${H - B + 18}" text-anchor="middle">${n}</text>`;
    s += `<rect class="train" x="${X(8) - 1}" y="${T}" width="2" height="${H - T - B}"/><text class="note" x="${X(8) + 6}" y="${T + 12}">trained with 8 frames</text>`;
    s += `<path class="line" d="M${data.map(([n, v]) => `${X(n).toFixed(1)},${Y(v).toFixed(1)}`).join(' L')}"/>`;
    data.forEach(([n, v], i) => { s += `<circle class="pt" data-i="${i}" cx="${X(n)}" cy="${Y(v)}" r="4.5"/>`; });
    s += `<text class="axis" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">Number of context frames at inference</text><text class="axis" transform="translate(14 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle">PSNR (dB)</text>`;
    s += `<g class="tip" visibility="hidden"><rect rx="5" width="118" height="40"/><text class="t1" x="10" y="17"></text><text class="t2" x="10" y="33"></text></g></svg>`;
    root.innerHTML = s;
    const tip = $('.tip', root), t1 = $('.t1', tip), t2 = $('.t2', tip);
    $$('.pt', root).forEach(c => {
      c.addEventListener('mouseenter', () => { const [n, v] = data[+c.dataset.i]; const x = Math.min(X(n) + 10, W - 130), y = Math.max(Y(v) - 48, T); tip.setAttribute('transform', `translate(${x} ${y})`); t1.textContent = `${n} context frames`; t2.textContent = `${v.toFixed(2)} dB PSNR`; tip.setAttribute('visibility', 'visible'); $$('.pt', root).forEach(p => p.classList.toggle('hot', p === c)); });
    });
    root.addEventListener('mouseleave', () => { tip.setAttribute('visibility', 'hidden'); $$('.pt', root).forEach(p => p.classList.remove('hot')); });
  }

  $$('[data-fig]').forEach(root => {
    const k = root.dataset.fig;
    try {
      ({ arch: archFig, teaser: teaserFig, evalsettings: evalFig, comparestatic: compareStaticFig, dynfeature: r => scrubFig(r, 'dyn'), gatefeature: r => scrubFig(r, 'gate'), staticfeat: staticFeatFig, residualgrid: residualGridFig, dynmask: dynmaskFig, qual: qualFig, nframe: nframeFig })[k](root);
    } catch (e) { console.error('figure', k, e); }
  });
})();
