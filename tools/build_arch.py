"""Build static/figures/arch.svg (interactive architecture figure) from figure_ppts/mainarch.pptx slide 3 using pptx2svg."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from pptx2svg import Deck, Conv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'figures')
SLIDE = 0
YELLOW = [(2, 0), (1, 1), (2, 1), (2, 2), (3, 2)]


def tile(fill, stroke, grid, yellow=False, sw=1.6):
    def f(w, h):
        n = 4
        cells = ''
        if yellow:
            cells = ''.join(f'<rect x="{c * w / n:.1f}" y="{r * h / n:.1f}" width="{w / n:.1f}" height="{h / n:.1f}" fill="#f5e6a6"/>' for c, r in YELLOW)
        lines = ''.join(f'<line x1="{i * w / n:.1f}" y1="0" x2="{i * w / n:.1f}" y2="{h:.1f}"/><line x1="0" y1="{i * h / n:.1f}" x2="{w:.1f}" y2="{i * h / n:.1f}"/>' for i in range(1, n))
        return f'<rect width="{w:.1f}" height="{h:.1f}" fill="{fill}"/>{cells}<g stroke="{grid}" stroke-width="0.9">{lines}</g><rect width="{w:.1f}" height="{h:.1f}" fill="none" stroke="{stroke}" stroke-width="{sw}"/>'
    return f


EMF = {
    '99933a9284': tile('#e6ecef', '#a3b4bd', '#c3cfd6'),
    '7d05ce4bda': tile('#e8e1f6', '#7a63bf', '#a797d9'),
    'deb914ec02': None,
    'deb914eb02': tile('#e8e1f6', '#7a63bf', '#a797d9', yellow=True),
    'a02e0bd318': tile('#e3e8f1', '#8fa3b5', '#a797d9', yellow=True),
}

STEPS = [
    dict(key='sample', no='00', title='Monocular sequence sampling', text='From synchronized multi-view video we sample context frames along one moving camera, each at its own timestamp, and a target frame at a different view and time. Asynchronous view-time sampling is what lets the model disentangle camera parallax from scene motion.'),
    dict(key='static', no='01', title='Frozen static prior', text='The pretrained static encoder (24 layers) and renderer stay frozen. Context frames become the static latent z_st, which already encodes geometry and viewpoint. On its own it can render any view, but it has no notion of time.'),
    dict(key='dyn', no='02', title='Lightweight dynamic encoder', text='Eight transformer layers take the same frames with learnable time tokens. Frame and global attention are followed by cross-attention into the frozen static features (static injection), so the branch explains only what the static prior cannot: true scene motion. It outputs a time-invariant residual latent z_res and a dynamic mask through a DPT mask head.'),
    dict(key='time', no='03', title='Target-time adaptation and rendering', text='For a target timestamp, adjacent time tokens are interpolated and drive an AdaLN time module with a zero-initialised residual gate. The adapted residual is added to the static latent, and the frozen renderer decodes the dynamic latent at the target view. Training uses only image losses and the mask loss.'),
]


def region(cx, cy):
    if cx > 16.4 and cy < 1.75:
        return 'sample static dyn time'
    if cx < 6.6:
        return 'sample'
    if cx < 9.05:
        return 'dyn' if cy < 2.35 else 'static dyn'
    if cx < 12.1:
        return 'dyn' if cy < 3.62 else 'static'
    if cx < 15.2:
        if cy < 1.95:
            return 'dyn'
        if cx < 13.1 and cy > 3.5:
            return 'static'
        if cx < 13.1 and 2.6 < cy < 3.5:
            return 'dyn time'
        return 'time'
    if cx < 17.2:
        return 'time'
    return 'static time'


def label(x, y, parts, size=14, color='#23303d', anchor='middle', weight=500):
    spans = ''
    for p in parts:
        if isinstance(p, str):
            spans += f'<tspan>{p}</tspan>'
        else:
            kind, t = p
            if kind == 'sub':
                spans += f'<tspan baseline-shift="sub" font-size="{size * 0.68:.1f}">{t}</tspan>'
            elif kind == 'sup':
                spans += f'<tspan baseline-shift="super" font-size="{size * 0.68:.1f}">{t}</tspan>'
            elif kind == 'b':
                spans += f'<tspan font-weight="700">{t}</tspan>'
            elif kind == 'i':
                spans += f'<tspan font-style="italic" font-family="Cambria Math, STIX Two Math, Times New Roman, serif">{t}</tspan>'
    return f'<text x="{x * 72:.1f}" y="{y * 72:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}" font-family="Inter, system-ui, sans-serif">{spans}</text>'


def main():
    deck = Deck(os.path.join(ROOT, 'figure_ppts', 'mainarch.pptx'))
    conv = Conv(deck, OUT, 'arch', imgdir='img')
    conv.emf_sub = EMF
    svg = conv.slide(SLIDE)
    head, body = svg.split('</defs>', 1)
    body = body[:-len('</svg>')]
    out, depth, pos = [], 0, 0
    for m in re.finditer(r'<g [^>]*>|</g>', body):
        if m.group(0) == '</g>':
            depth -= 1
            continue
        if depth == 0:
            t = m.group(0)
            bb = re.search(r'data-bbox="([^"]*)"', t)
            x, y, w, h = [float(v) / 72 for v in bb.group(1).split()]
            cls = region(x + w / 2, y + h / 2)
            nt = t.replace('<g ', f'<g class="st {cls}" ', 1)
            out.append(body[pos:m.start()])
            out.append(nt)
            pos = m.end()
        depth += 1
    out.append(body[pos:])
    body = ''.join(out)
    body = re.sub(r'(data-name="Picture 152"[^>]*>\s*<image[^>]*href=")img/[^"]+"', r'\1img/9677ee948a.webp"', body)
    extra = [
        label(9.56, 2.27, ['×8'], 13, '#4b4475', 'middle', 600), label(9.56, 2.48, ['layers'], 13, '#4b4475', 'middle', 600),
        label(9.56, 4.1, ['×24'], 13, '#3f5c5f', 'middle', 600), label(9.56, 4.31, ['layers'], 13, '#3f5c5f', 'middle', 600),
        label(12.62, 4.88, ['Static latent ', ('b', 'z'), ('sub', 'st')], 14, '#5f7681'),
        label(12.62, 3.67, ['Residual latent ', ('b', 'z'), ('sub', 'res')], 14, '#6a4fc4'),
        label(15.44, 3.42, [('b', 'z'), ('sub', 'res'), ('sup', 'tgt')], 15, '#6a4fc4'),
        label(17.02, 3.42, [('b', 'z'), ('sub', 'dyn'), ('sup', 'tgt')], 15, '#3a7a9c'),
        label(12.86, 2.24, ['Target time ', ('i', 'τ̂'), ('sub', 'tgt')], 13, '#8a6d2a'),
        label(17.0, 4.32, ['Target view ', ('i', 'π'), ('sub', 'tgt')], 13, '#8a6d2a'),
        label(15.45, 1.98, [('i', 'ℒ'), ('sub', 'mask')], 15, '#23303d', 'start'),
        label(20.42, 2.98, [('i', 'ℒ'), ('sub', 'rgb')], 15, '#23303d'),
        label(4.05, 3.38, [('b', 'I'), ('sub', 'tgt')], 13, '#8a6d2a'),
    ]
    extra_cls = ['dyn', 'dyn', 'static', 'static', 'static', 'dyn time', 'time', 'time', 'time', 'static time', 'dyn', 'static time', 'sample']
    body += ''.join(f'<g class="st {c}">{e}</g>' for e, c in zip(extra, extra_cls))
    W, H = deck.w / 12700, deck.h / 12700
    crop = (0.55 * 72, 0.35 * 72, W - 0.9 * 72, 5.45 * 72)
    head = re.sub(r'viewBox="[^"]*" width="[^"]*" height="[^"]*"', f'viewBox="{crop[0]:.1f} {crop[1]:.1f} {crop[2] - crop[0]:.1f} {crop[3] - crop[1]:.1f}"', head, count=1)
    svg = (head + '</defs>' + body + '</svg>').replace('href="img/', 'href="static/figures/img/')
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'arch.svg'), 'w').write(svg)
    json.dump(STEPS, open(os.path.join(OUT, 'arch_steps.json'), 'w'), indent=1, ensure_ascii=False)
    print('arch.svg', len(svg), 'bytes; crop', [round(c / 72, 2) for c in crop])


if __name__ == '__main__':
    main()
