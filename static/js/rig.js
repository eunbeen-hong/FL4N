(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const root = $('#rig');
  if (!root) return;

  const CONFIG = {
    base: 'static/videos/rig/',
    manifest: 'static/videos/rig/manifest.json',
    models: [
      { key: 'gt', label: 'Ground truth', optional: true }, { key: 'ours', label: 'FL4N (Ours)' }, { key: 'c4g', label: 'C4G' },
      { key: 'neoverse', label: 'NeoVerse' }, { key: 'movies', label: 'MoVieS' }, { key: '4dgt', label: '4DGT' },
    ],
    excludeDatasets: ['kubric4d', 'charge'],
    datasetOrder: ['nvidia', 'n3dv', 'camxtime'],
    sceneName: s => s.id.replace(/_/g, ' ').replace(/^(\w)/, c => c.toUpperCase()),
    maxCams: 8,
    pickCams: (n, k) => Array.from({ length: Math.min(n, k) }, (_, i) => Math.round(i * (n - 1) / (Math.min(n, k) - 1))),
    camSrc: (scene, model, k) => `${CONFIG.base}${scene.ds}_${scene.id}__${model}__c${String(k).padStart(2, '0')}.mp4`,
    inputSrc: scene => `${CONFIG.base}${scene.ds}_${scene.id}__input.mp4`,
    inputPoster: scene => `${CONFIG.base}${scene.ds}_${scene.id}__input.jpg`,
    geometry: { arcDeg: 120, tiltDeg: 36, radius: 0.3, region: 0.36, subjectW: 0.2, frustumLen: 0.075, frustumW: 0.085 },
  };
  const NS = 'http://www.w3.org/2000/svg';

  const stage = $('.rig-stage', root), world = $('.rig-world', root), thumbs = $('.rig-thumbs', root);
  const basebar = document.createElement('div');
  basebar.className = 'rig-basebar';
  stage.parentNode.insertBefore(basebar, stage.nextSibling);
  let manifest = null, scene = null, meta = null, baseline = 'c4g';
  let center = null, cols = [], vids = [], svg = null;

  function build() {
    world.innerHTML = '';
    svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('class', 'rig-svg');
    world.appendChild(svg);
    center = document.createElement('div');
    center.className = 'rig-center';
    center.innerHTML = `<video muted loop playsinline preload="auto" style="aspect-ratio:${meta.w}/${meta.h}" poster="${CONFIG.inputPoster(scene)}"></video><div class="rig-clabel">Input video</div>`;
    world.appendChild(center);
    const G = meta.grid, gap = G.gap, nc = G.cams.length, rowsAll = G.rows.concat([baseline]), nr = rowsAll.length;
    const GW = nc * meta.w + (nc - 1) * gap, GH = nr * meta.h + (nr - 1) * gap;
    const wrap = document.createElement('div');
    wrap.className = 'rig-gridwrap';
    const labels = document.createElement('div');
    labels.className = 'rig-labels';
    const box = document.createElement('div');
    box.className = 'rig-gridbox';
    box.style.aspectRatio = `${GW}/${GH}`;
    box.innerHTML = `<video class="rig-gridvideo" muted loop playsinline preload="auto"></video>`;
    cols = G.cams.map((k, i) => {
      const h = document.createElement('div');
      h.className = 'rig-colhead';
      h.textContent = `cam ${k + 1}`;
      h.style.left = `${(i * (meta.w + gap)) / GW * 100}%`;
      h.style.width = `${meta.w / GW * 100}%`;
      return h;
    });
    const heads = document.createElement('div');
    heads.className = 'rig-heads';
    cols.forEach(h => heads.appendChild(h));
    rowsAll.forEach((r, ri) => {
      const lab = document.createElement('div');
      lab.className = 'rig-rowlabel' + (r === 'ours' ? ' ours' : '') + (r === 'gt' ? ' gt' : '');
      lab.textContent = CONFIG.models.find(m => m.key === r).label;
      lab.style.top = `${(ri * (meta.h + gap)) / GH * 100}%`;
      lab.style.height = `${meta.h / GH * 100}%`;
      labels.appendChild(lab);
      G.cams.forEach((k, ci) => {
        const c = document.createElement('div');
        c.className = 'rig-cellbox' + (r === 'ours' ? ' ours' : '') + (r === 'gt' ? ' gt' : '');
        c.style.left = `${(ci * (meta.w + gap)) / GW * 100}%`;
        c.style.top = `${(ri * (meta.h + gap)) / GH * 100}%`;
        c.style.width = `${meta.w / GW * 100}%`;
        c.style.height = `${meta.h / GH * 100}%`;
        box.appendChild(c);
      });
    });
    wrap.appendChild(labels);
    const right = document.createElement('div');
    right.className = 'rig-right';
    right.appendChild(heads);
    right.appendChild(box);
    wrap.appendChild(right);
    world.appendChild(wrap);
    layout();
  }

  function layout() {
    const W = stage.clientWidth;
    if (!W || !meta || !center) return;
    const g = CONFIG.geometry, N = cols.length, asp = meta.w / meta.h, narrow = W < 700;
    $('.rig-labels', world).style.height = $('.rig-gridbox', world).offsetHeight + 'px';
    $('.rig-labels', world).style.marginTop = $('.rig-heads', world).offsetHeight + 'px';
    const region = Math.round((narrow ? 0.7 : g.region) * W);
    const wrap = $('.rig-gridwrap', world);
    wrap.style.top = region + 'px';
    const H = region + wrap.offsetHeight + 12;
    stage.style.height = H + 'px';
    const cx = W / 2, cy = region * 0.33, R = (narrow ? 0.4 : g.radius) * W, tilt = g.tiltDeg * Math.PI / 180;
    center.style.width = Math.round((asp < 1.5 ? 0.8 : 1) * (narrow ? 0.34 : g.subjectW) * W) + 'px';
    center.style.transform = `translate(${cx}px, ${cy}px) translate(-50%, -50%)`;
    const proj = ([x, y, z]) => [cx + x, cy - y * Math.cos(tilt) + z * Math.sin(tilt)];
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = '';
    const arc = [];
    for (let a = -g.arcDeg / 2; a <= g.arcDeg / 2; a += 2) { const r = a * Math.PI / 180; arc.push(proj([R * Math.sin(r), 0, R * Math.cos(r)])); }
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', 'M' + arc.map(p => p.map(v => v.toFixed(1)).join(',')).join(' L'));
    path.setAttribute('class', 'rig-traj');
    svg.appendChild(path);
    const L = g.frustumLen * W, bw = g.frustumW * W, bh = bw / asp;
    const sr = stage.getBoundingClientRect();
    cols.forEach((h, i) => {
      const a = (N === 1 ? 0 : -g.arcDeg / 2 + g.arcDeg * i / (N - 1)) * Math.PI / 180;
      const P = [R * Math.sin(a), 0, R * Math.cos(a)];
      const len = Math.hypot(...P), dir = P.map(v => -v / len);
      const right = [dir[2], 0, -dir[0]];
      const rl = Math.hypot(...right); right.forEach((v, j) => (right[j] = v / rl));
      const up = [dir[1] * right[2] - dir[2] * right[1], dir[2] * right[0] - dir[0] * right[2], dir[0] * right[1] - dir[1] * right[0]];
      const B = P.map((v, j) => v + dir[j] * L);
      const corners = [[1, 1], [-1, 1], [-1, -1], [1, -1]].map(([sx, sy]) => proj(B.map((v, j) => v + right[j] * sx * bw / 2 + up[j] * sy * bh / 2)));
      const apex = proj(P);
      const gfr = document.createElementNS(NS, 'g');
      gfr.setAttribute('class', 'rig-frustum');
      const base = document.createElementNS(NS, 'polygon');
      base.setAttribute('points', corners.map(c => c.map(v => v.toFixed(1)).join(',')).join(' '));
      gfr.appendChild(base);
      corners.forEach(c => { const l = document.createElementNS(NS, 'line'); l.setAttribute('x1', apex[0]); l.setAttribute('y1', apex[1]); l.setAttribute('x2', c[0]); l.setAttribute('y2', c[1]); gfr.appendChild(l); });
      const dot = document.createElementNS(NS, 'circle');
      dot.setAttribute('cx', apex[0]); dot.setAttribute('cy', apex[1]); dot.setAttribute('r', 3.2);
      gfr.appendChild(dot);
      svg.appendChild(gfr);
      const hr = h.getBoundingClientRect();
      const px = hr.left - sr.left + hr.width / 2, py = hr.top - sr.top;
      const y0 = apex[1] + 6, ym = (y0 + py) / 2;
      const link = document.createElementNS(NS, 'path');
      link.setAttribute('d', `M${apex[0].toFixed(1)},${y0.toFixed(1)} C${apex[0].toFixed(1)},${ym.toFixed(1)} ${px.toFixed(1)},${ym.toFixed(1)} ${px.toFixed(1)},${py.toFixed(1)}`);
      link.setAttribute('class', 'rig-link');
      svg.appendChild(link);
    });
  }

  function attach(v, src) {
    v.pause();
    v.src = src;
    v.load();
    v.oncanplay = () => { v.oncanplay = null; try { v.currentTime = vids[0] ? vids[0].currentTime : 0; } catch (e) {} v.play().catch(() => {}); };
  }

  function gridSrc(s) { return `${CONFIG.base}${s.ds}_${s.id}__grid_${baseline}.mp4`; }
  function show(s) {
    scene = s;
    meta = manifest[`${s.ds}_${s.id}`];
    if (!meta) return;
    build();
    const cv = $('video', center), gv = $('.rig-gridvideo', world);
    vids = [cv, gv];
    attach(cv, CONFIG.inputSrc(s));
    attach(gv, gridSrc(s));
    $$('.rig-thumb', thumbs).forEach(b => b.classList.toggle('active', b.dataset.key === `${s.ds}_${s.id}`));
  }
  function setBaseline(b) {
    baseline = b;
    $$('button', basebar).forEach(x => x.classList.toggle('active', x.dataset.key === b));
    if (!scene) return;
    const t = vids[0] ? vids[0].currentTime : 0;
    build();
    const cv = $('video', center), gv = $('.rig-gridvideo', world);
    const old = vids[0];
    vids = [cv, gv];
    cv.src = old && old.src ? old.src : CONFIG.inputSrc(scene);
    cv.oncanplay = () => { cv.oncanplay = null; try { cv.currentTime = t; } catch (e) {} cv.play().catch(() => {}); };
    attach(gv, gridSrc(scene));
  }
  basebar.innerHTML = '<span class="lbl">Compare FL4N with</span>';
  CONFIG.models.filter(m => !['gt', 'ours'].includes(m.key)).forEach(m => {
    const b = document.createElement('button');
    b.className = 'chip' + (m.key === baseline ? ' active' : '');
    b.dataset.key = m.key;
    b.textContent = m.label;
    b.addEventListener('click', () => setBaseline(m.key));
    basebar.appendChild(b);
  });

  setInterval(() => {
    const m = vids[0];
    if (!m || m.paused || !isFinite(m.duration)) return;
    vids.slice(1).forEach(v => { if (v.src && !v.oncanplay && Math.abs(v.currentTime - m.currentTime) > 0.12) v.currentTime = m.currentTime; });
  }, 400);

  new IntersectionObserver(es => es.forEach(e => vids.forEach(v => e.isIntersecting ? v.play().catch(() => {}) : v.pause())), { rootMargin: '100px 0px' }).observe(root);
  window.addEventListener('resize', layout);

  fetch(CONFIG.manifest).then(r => r.json()).then(j => {
    manifest = j;
    const scenes = Object.values(j).filter(e => e.grid && !CONFIG.excludeDatasets.includes(e.ds)).map(e => ({ ds: e.ds, id: e.id, name: CONFIG.sceneName(e) }))
      .sort((a, b) => CONFIG.datasetOrder.indexOf(a.ds) - CONFIG.datasetOrder.indexOf(b.ds) || a.name.localeCompare(b.name));
    thumbs.innerHTML = '';
    scenes.forEach(s => {
      const b = document.createElement('button');
      b.className = 'rig-thumb';
      b.dataset.key = `${s.ds}_${s.id}`;
      b.innerHTML = `<img src="${CONFIG.inputPoster(s)}" alt="" loading="lazy"><span class="ds">${FL4N_DS[s.ds]}</span><span class="nm">${s.name}</span>`;
      b.addEventListener('click', () => show(s));
      thumbs.appendChild(b);
    });
    if (scenes.length) show(scenes[0]);
  }).catch(() => {});
})();
