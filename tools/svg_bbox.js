// usage: node svg_bbox.js in.svg bbox.json [classes.json out.svg]  (second form writes the SVG with class attributes applied to the wrapper's children)
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const [,, src, bboxOut, clsIn, svgOut] = process.argv;
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 400 } });
  await p.goto('file://' + src); await p.waitForTimeout(500);
  const r = await p.evaluate((cls) => {
    const svg = document.querySelector('svg'); let root = svg;
    const kids = n => [...n.children].filter(c => c.tagName !== 'defs');
    while (kids(root).length === 1) root = kids(root)[0];
    const R = svg.getBoundingClientRect(); const vb = svg.viewBox.baseVal; const s = vb.width / R.width; const out = [];
    kids(root).forEach((c, i) => { const q = c.getBoundingClientRect();
      out.push({ i, tag: c.tagName, x: (q.left - R.left) * s + vb.x, y: (q.top - R.top) * s + vb.y, w: q.width * s, h: q.height * s, img: c.querySelectorAll('image').length, n: c.querySelectorAll('*').length });
      if (cls && cls.cls[i]) c.setAttribute('class', 'st ' + cls.cls[i]); });
    if (cls) { const ks = kids(root); cls.groups.forEach(ix => { const g = document.createElementNS('http://www.w3.org/2000/svg', 'g'); g.setAttribute('class', ks[ix[0]].getAttribute('class')); root.insertBefore(g, ks[ix[0]]); ix.forEach(k => { ks[k].removeAttribute('class'); g.appendChild(ks[k]); }); }); }
    return { bbox: out, svg: cls ? new XMLSerializer().serializeToString(svg) : null }; }, clsIn ? JSON.parse(fs.readFileSync(clsIn, 'utf8')) : null);
  fs.writeFileSync(bboxOut, JSON.stringify(r.bbox)); if (svgOut) fs.writeFileSync(svgOut, r.svg); await b.close();
})();
