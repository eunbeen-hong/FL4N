"""Recolour figure_ppts/mainarch.pptx into the project-page palette (slides, theme, SVG icons, PNG fallbacks, EMF latent tiles -> PNG)."""
import os, re, io, sys, json, zipfile, hashlib, subprocess, tempfile
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'figure_ppts', 'mainarch.pptx')
DST = os.path.join(ROOT, 'figure_ppts', 'mainarch_page.pptx')
PW = os.environ.get('PW', '/tmp/claude-1001/-home-cvlab20-project-eunbeen-LagerNVS4d/2029518d-9a2f-403f-a387-494dcea53f53/scratchpad/pw')

MAP = {
    '23303D': '231A12', '000000': '231A12', '646464': '7F6D5C', 'AEAEAE': 'A0917F', 'BFBFBF': 'E2D0B8', 'EFEFEF': 'F6F1E8',
    'D88B53': 'C96A2B', 'F1D5C4': 'F4D9C2', 'FDF3E6': 'FFF7DC',
    '98783F': 'C9961A', 'F7EBA8': 'FBE6A8', 'F8EBA8': 'FBE6A8', 'F5E6A6': 'FBE6A8',
    '6C59A4': 'B4591E', '9988CE': 'B4591E', '7563AA': 'B4591E', '6D5AA5': 'B4591E', '7A63BF': 'B4591E',
    'E5DEF3': 'F4D9C2', 'F1EDF8': 'FBF1E6', 'EBE8F2': 'FBF1E6', 'E8E1F6': 'FBF1E6',
    '381DA3': '8E4113', '36239A': '8E4113', '352695': '8E4113', '332B8F': '8E4113', '3D5696': '8E4113',
    '418F88': '7F9C95', 'E3EAED': 'EEF2F1', 'E9EDF0': 'EEF2F1', '8B98A5': '9FB3AD', '8A98A5': '9FB3AD', '7E8A95': '9FB3AD',
    'F5F5F5': 'F3F6F5', '3B7B97': '4E4033',
}
TEXT_MAP = {'98783F': '946F12', '418F88': '5C7370', '8B98A5': '5C7370', '7E8A95': '5C7370', '8A98A5': '5C7370', '3B7B97': '4E4033'}
THEME = {'dk1': '231A12', 'accent1': '231A12'}
YELLOW = [(2, 0), (1, 1), (2, 1), (2, 2), (3, 2)]
TILES = {
    'image3.emf': dict(fill='EEF2F1', grid='B5C5C0', border='9FB3AD', yellow=False),
    'image9.emf': dict(fill='F4D9C2', grid='C96A2B', border='B4591E', yellow=False),
    'image4.emf': dict(fill='F4D9C2', grid='C96A2B', border='B4591E', yellow=True),
    'image5.emf': dict(fill='EEF2F1', grid='C96A2B', border='9FB3AD', yellow=True),
}


def tile_png(fill, grid, border, yellow, size=600):
    im = Image.new('RGB', (size, size), '#' + fill)
    d = ImageDraw.Draw(im)
    n, c = 4, size / 4
    if yellow:
        for col, row in YELLOW:
            d.rectangle([col * c, row * c, (col + 1) * c, (row + 1) * c], fill='#FBE6A8')
    for i in range(1, n):
        d.line([(i * c, 0), (i * c, size)], fill='#' + grid, width=6)
        d.line([(0, i * c), (size, i * c)], fill='#' + grid, width=6)
    d.rectangle([0, 0, size - 1, size - 1], outline='#' + border, width=14)
    b = io.BytesIO()
    im.save(b, 'PNG', optimize=True)
    return b.getvalue()


def recolor(text, mapping):
    return re.sub(r'(?i)(srgbClr val="|#)([0-9A-F]{6})', lambda m: m.group(1) + mapping.get(m.group(2).upper(), m.group(2)), text)


def recolor_slide(x):
    x = re.sub(r'<a:rPr\b.*?</a:rPr>', lambda m: recolor(m.group(0), TEXT_MAP), x, flags=re.S)
    x = re.sub(r'<a:endParaRPr\b.*?</a:endParaRPr>', lambda m: recolor(m.group(0), TEXT_MAP), x, flags=re.S)
    return recolor(x, MAP)


def main():
    z = zipfile.ZipFile(SRC)
    names = z.namelist()
    out = {}
    svg_changed = {}
    for n in names:
        b = z.read(n)
        if re.match(r'ppt/slides/slide\d+\.xml$', n):
            out[n] = recolor_slide(b.decode()).encode()
        elif n == 'ppt/theme/theme1.xml':
            t = b.decode()
            for k, v in THEME.items():
                t = re.sub(rf'(<a:{k}>\s*<a:srgbClr val=")[0-9A-Fa-f]{{6}}', rf'\g<1>{v}', t)
            out[n] = t.encode()
        elif n.startswith('ppt/media/') and n.endswith('.svg'):
            s = recolor(b.decode(), MAP)
            if s.encode() != b:
                svg_changed[n] = s
            out[n] = s.encode()
        else:
            out[n] = b
    for emf, spec in TILES.items():
        out['ppt/media/' + emf.replace('.emf', '_tile.png')] = tile_png(**spec)
    for n in names:
        if re.match(r'ppt/slides/_rels/slide\d+\.xml\.rels$', n):
            r = out[n].decode()
            for emf in TILES:
                r = r.replace('../media/' + emf, '../media/' + emf.replace('.emf', '_tile.png'))
            out[n] = r.encode()
    pairs = {}
    for n in names:
        if re.match(r'ppt/slides/slide\d+\.xml$', n):
            rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', out[n.replace('slides/', 'slides/_rels/') + '.rels'].decode()))
            for p in re.findall(r'<p:pic>.*?</p:pic>', out[n].decode(), re.S):
                emb, sv = re.search(r'r:embed="(rId\d+)"', p), re.search(r'svgBlip[^>]*r:embed="(rId\d+)"', p)
                if emb and sv:
                    png, svg = 'ppt/' + rels[emb.group(1)].replace('../', ''), 'ppt/' + rels[sv.group(1)].replace('../', '')
                    if svg in svg_changed:
                        pairs[png] = svg
    tmp = tempfile.mkdtemp()
    jobs = []
    for png, svg in pairs.items():
        w, h = Image.open(io.BytesIO(out[png])).size
        sp = os.path.join(tmp, os.path.basename(svg))
        open(sp, 'w').write(svg_changed[svg])
        jobs.append(dict(svg=sp, out=os.path.join(tmp, os.path.basename(png)), w=w, h=h, key=png))
    js = os.path.join(tmp, 'rast.js')
    open(js, 'w').write("""const { chromium } = require('playwright'); const fs = require('fs');
(async () => { const jobs = JSON.parse(fs.readFileSync(process.argv[2])); const b = await chromium.launch();
for (const j of jobs) { const pg = await b.newPage({ viewport: { width: j.w, height: j.h }, deviceScaleFactor: 1 });
  await pg.setContent(`<html><body style="margin:0;background:transparent"><img src="file://${j.svg}" style="display:block;width:${j.w}px;height:${j.h}px"></body></html>`, { waitUntil: 'load' });
  await pg.waitForTimeout(100); await pg.screenshot({ path: j.out, omitBackground: true }); await pg.close(); }
await b.close(); })();""")
    open(os.path.join(tmp, 'jobs.json'), 'w').write(json.dumps(jobs))
    subprocess.run(['node', js, os.path.join(tmp, 'jobs.json')], check=True, env=dict(os.environ, NODE_PATH=os.path.join(PW, 'node_modules')))
    for j in jobs:
        out[j['key']] = open(j['out'], 'rb').read()
    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in names + [k for k in out if k not in names]:
            zo.writestr(n, out[n])
    print('wrote', DST, 'svg icons recoloured:', len(svg_changed), 'png fallbacks re-rendered:', len(pairs))
    print('tile md5:', {k: hashlib.md5(tile_png(**v)).hexdigest()[:10] for k, v in TILES.items()})


if __name__ == '__main__':
    main()
