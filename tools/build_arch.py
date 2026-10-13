"""Build static/figures/arch.svg from figure_ppts/mainarch.pdf (MuPDF vector export, glyphs as paths) and tag every element with the pipeline stages it belongs to, using element bounding boxes measured in headless Chromium (tools/svg_bbox.js)."""
import os, re, sys, json, subprocess, tempfile
import fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'figures')
PW = os.environ.get('PW', '/tmp/claude-1001/-home-cvlab20-project-eunbeen-LagerNVS4d/2029518d-9a2f-403f-a387-494dcea53f53/scratchpad/pw')

STEPS = [
    dict(key='sample', no='00', title='Monocular sequence sampling', text='Context frames come from one moving camera, each at its own instant; the target is another view and time. Sampling view and time asynchronously separates camera parallax from scene motion.'),
    dict(key='static', no='01', title='Frozen static encoder', text='The pretrained static encoder (24 layers) and renderer stay frozen. They turn the context frames into a static latent that knows geometry and viewpoint, but not time.'),
    dict(key='dyn', no='02', title='Dynamic encoder', text='Eight layers with learnable time tokens, anchored to the frozen static features through cross-attention, output a time-invariant residual latent and a dynamic mask.'),
    dict(key='time', no='03', title='Target-time adaptation and rendering', text='A time module adapts the residual to the target time. Residual plus static latent is decoded by the frozen renderer at the target view.'),
]


def region(x, y, w, h):
    cx, cy = x + w / 2, y + h / 2
    if w > 1400:
        return ''
    if cx > 1010 and cy < 90:
        return 'sample static dyn time'
    if cx < 360:
        return 'sample'
    if cx < 517:
        return 'dyn' if cy < 120 else 'static dyn'
    if cx < 680:
        return 'dyn' if cy < 215 else 'static'
    if cx < 780:
        if cy < 95:
            return 'dyn'
        if cy < 140 or (h < 12 and w > 40 and x > 730):
            return 'time'
        return 'dyn time' if cy < 215 else 'static'
    if cx < 1065:
        if cy < 110:
            return 'dyn'
        if cy < 215:
            return 'static time' if w > 100 and h > 60 else 'time'
        return 'static' if cx < 1000 else 'static time'
    return 'static time'


def main():
    page = fitz.open(os.path.join(ROOT, 'figure_ppts', 'mainarch.pdf'))[0]
    svg = page.get_svg_image()
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, 'pdf.svg')
    open(src, 'w').write(svg)
    subprocess.run(['node', os.path.join(ROOT, 'tools', 'svg_bbox.js'), src, os.path.join(tmp, 'bbox.json')], cwd=PW, env=dict(os.environ, NODE_PATH=os.path.join(PW, 'node_modules')), check=True)
    bb = json.load(open(os.path.join(tmp, 'bbox.json')))
    cls = [region(e['x'], e['y'], e['w'], e['h']) for e in bb]
    groups, run = [], [0]
    hit = lambda a, b: a['x'] < b['x'] + b['w'] + 2 and b['x'] < a['x'] + a['w'] + 2 and a['y'] < b['y'] + b['h'] + 2 and b['y'] < a['y'] + a['h'] + 2
    for i in range(1, len(bb)):
        if cls[i] and cls[i] == cls[run[-1]] and any(hit(bb[i], bb[j]) for j in run):
            run.append(i)
        else:
            if len(run) > 1:
                groups.append(run)
            run = [i]
    if len(run) > 1:
        groups.append(run)
    json.dump(dict(cls=cls, groups=groups), open(os.path.join(tmp, 'cls.json'), 'w'))
    subprocess.run(['node', os.path.join(ROOT, 'tools', 'svg_bbox.js'), src, os.path.join(tmp, 'bbox.json'), os.path.join(tmp, 'cls.json'), os.path.join(tmp, 'out.svg')], cwd=PW, env=dict(os.environ, NODE_PATH=os.path.join(PW, 'node_modules')), check=True)
    res = open(os.path.join(tmp, 'out.svg')).read()
    res = re.sub(r' width="[^"]*" height="[^"]*" viewBox=', ' viewBox=', res, count=1)
    res = res.replace('id="', 'id="ar-').replace('xlink:href="#', 'xlink:href="#ar-').replace('url(#', 'url(#ar-')
    res = re.sub(r'(\d+\.\d{3})\d+', r'\1', res)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'arch.svg'), 'w').write(res)
    json.dump(STEPS, open(os.path.join(OUT, 'arch_steps.json'), 'w'), indent=1, ensure_ascii=False)
    n = {c: cls.count(c) for c in set(cls)}
    print('arch.svg', len(res) // 1024, 'KB;', len(cls), 'elements', n, len(groups), 'groups')


if __name__ == '__main__':
    main()
