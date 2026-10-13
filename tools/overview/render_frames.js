const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const html = path.resolve(process.argv[2]), out = path.resolve(process.argv[3]);
  const fps = +(process.argv[4] || 30), total = +(process.argv[5] || 41.5), only = process.argv[6] ? process.argv[6].split(',').map(Number) : null;
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1920, height: 840 } });
  pg.on('pageerror', e => console.error('pageerror', e.message));
  const arch = fs.readFileSync(path.resolve(__dirname, '../../static/figures/arch.svg'), 'utf8');
  await pg.addInitScript(() => { window.__noAutoSetup = true; });
  await pg.goto('file://' + html, { waitUntil: 'load' });
  await pg.evaluate(s => setup(s), arch);
  await pg.evaluate(() => Promise.all([document.fonts.ready, ...Array.from(document.images).map(im => im.complete ? 1 : new Promise(r => { im.onload = im.onerror = r; }))]));
  await pg.waitForTimeout(300);
  const times = only ? only : Array.from({ length: Math.round(total * fps) }, (_, i) => i / fps);
  for (let i = 0; i < times.length; i++) {
    await pg.evaluate(t => render(t), times[i]);
    const name = only ? `t${times[i].toFixed(2)}.png` : `f${String(i).padStart(5, '0')}.jpg`;
    await pg.screenshot({ path: path.join(out, name), type: only ? 'png' : 'jpeg', quality: only ? undefined : 94 });
    if (i % 300 === 0) console.log('frame', i, '/', times.length);
  }
  await b.close();
})();
