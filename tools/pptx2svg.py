"""Convert pptx slides to standalone SVG (shapes, custom paths, connectors, text, pictures); usage: pptx2svg.py deck.pptx outdir [slide indices]."""
import sys, os, re, io, json, math, zipfile, colorsys, hashlib
from lxml import etree
from PIL import Image

A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'a': A, 'p': P, 'r': R}
EMU = 12700.0
FONT_MAP = {'Google Sans': "Inter, 'Google Sans', system-ui, sans-serif", 'Nimbus Sans': "Inter, 'Nimbus Sans', sans-serif", 'Cambria Math': "'Cambria Math', 'STIX Two Math', 'Times New Roman', serif", 'Nimbus Roman': "'Nimbus Roman', 'Times New Roman', serif", 'Calibri': 'Inter, Calibri, sans-serif', 'PT Sans': "Inter, 'PT Sans', sans-serif"}


def q(tag):
    p, t = tag.split(':')
    return '{%s}%s' % (NS[p], t)


class Deck:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        pres = etree.fromstring(self.z.read('ppt/presentation.xml'))
        sz = pres.find(q('p:sldSz'))
        self.w, self.h = int(sz.get('cx')), int(sz.get('cy'))
        rels = etree.fromstring(self.z.read('ppt/_rels/presentation.xml.rels'))
        rmap = {r.get('Id'): r.get('Target') for r in rels}
        self.slides = [('ppt/' + rmap[s.get(q('r:id'))]) for s in pres.find(q('p:sldIdLst'))]
        self.theme = self._theme()
        self.images = {}

    def _theme(self):
        t = etree.fromstring(self.z.read('ppt/theme/theme1.xml'))
        cs = t.find('.//' + q('a:clrScheme'))
        out = {}
        for c in cs:
            n = etree.QName(c).localname
            v = c[0].get('lastClr') or c[0].get('val')
            out[n] = v
        alias = {'tx1': 'dk1', 'bg1': 'lt1', 'tx2': 'dk2', 'bg2': 'lt2'}
        for k, v in alias.items():
            out[k] = out.get(v, '000000')
        return out

    def rels(self, slide):
        d, f = os.path.split(slide)
        p = f'{d}/_rels/{f}.rels'
        if p not in self.z.namelist():
            return {}
        rels = etree.fromstring(self.z.read(p))
        return {r.get('Id'): os.path.normpath(os.path.join(d, r.get('Target'))) for r in rels}


class Conv:
    def __init__(self, deck, outdir, name, imgdir='img'):
        self.d, self.out, self.name = deck, outdir, name
        self.imgdir = imgdir
        os.makedirs(os.path.join(outdir, imgdir), exist_ok=True)
        self.defs, self.body, self.nid = [], [], 0
        self.markers = {}
        self.emf_sub = {}

    def uid(self, p='e'):
        self.nid += 1
        return f'{p}{self.nid}'

    def color(self, el):
        if el is None:
            return None, 1.0
        c = None
        for ch in el:
            n = etree.QName(ch).localname
            if n == 'srgbClr':
                c = ch.get('val')
            elif n == 'schemeClr':
                c = self.d.theme.get(ch.get('val'), '000000')
            elif n == 'prstClr':
                c = {'black': '000000', 'white': 'FFFFFF'}.get(ch.get('val'), '808080')
            elif n == 'sysClr':
                c = ch.get('lastClr', '000000')
            if c is None:
                continue
            alpha = 1.0
            r, g, b = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            for m in ch:
                mn = etree.QName(m).localname
                v = m.get('val')
                if mn == 'alpha':
                    alpha = int(v) / 100000
                elif mn == 'lumMod':
                    l *= int(v) / 100000
                elif mn == 'lumOff':
                    l += int(v) / 100000
                elif mn == 'shade':
                    l *= int(v) / 100000
                elif mn == 'tint':
                    l = 1 - (1 - l) * int(v) / 100000
            l = min(max(l, 0), 1)
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return '#%02x%02x%02x' % (round(r * 255), round(g * 255), round(b * 255)), alpha
        return None, 1.0

    def fill(self, sp_pr, style=None):
        if sp_pr is None:
            return 'none', 1.0
        for ch in sp_pr:
            n = etree.QName(ch).localname
            if n == 'noFill':
                return 'none', 1.0
            if n == 'solidFill':
                return self.color(ch)
            if n == 'gradFill':
                return self.gradient(ch), 1.0
            if n == 'blipFill':
                return 'none', 1.0
        if style is not None:
            fr = style.find(q('a:fillRef'))
            if fr is not None and fr.get('idx') not in (None, '0'):
                return self.color(fr)
        return 'none', 1.0

    def gradient(self, gf):
        gid = self.uid('g')
        stops = []
        for gs in gf.find(q('a:gsLst')):
            c, a = self.color(gs)
            stops.append(f'<stop offset="{int(gs.get("pos")) / 100000:.3f}" stop-color="{c}" stop-opacity="{a:.3f}"/>')
        lin = gf.find(q('a:lin'))
        ang = int(lin.get('ang', '0')) / 60000 if lin is not None else 0
        x2, y2 = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        self.defs.append(f'<linearGradient id="{gid}" x1="{0.5 - x2 / 2:.3f}" y1="{0.5 - y2 / 2:.3f}" x2="{0.5 + x2 / 2:.3f}" y2="{0.5 + y2 / 2:.3f}">{"".join(stops)}</linearGradient>')
        return f'url(#{gid})'

    def stroke(self, sp_pr, style=None):
        ln = sp_pr.find(q('a:ln')) if sp_pr is not None else None
        if ln is None:
            if style is not None:
                lr = style.find(q('a:lnRef'))
                if lr is not None and lr.get('idx') not in (None, '0'):
                    c, a = self.color(lr)
                    return dict(color=c, alpha=a, w=0.75, dash=None, head=None, tail=None)
            return None
        w = int(ln.get('w', '9525')) / EMU
        col, alpha, dash = None, 1.0, None
        for ch in ln:
            n = etree.QName(ch).localname
            if n == 'noFill':
                return None
            if n == 'solidFill':
                col, alpha = self.color(ch)
            if n == 'gradFill':
                stops = ch.find(q('a:gsLst'))
                col, alpha = self.color(stops[len(stops) // 2])
            if n == 'prstDash':
                dash = ch.get('val')
        if col is None:
            if style is not None:
                col, alpha = self.color(style.find(q('a:lnRef')))
            if col is None:
                return None
        he, te = ln.find(q('a:headEnd')), ln.find(q('a:tailEnd'))
        return dict(color=col, alpha=alpha, w=w, dash=dash, head=he.get('type') if he is not None else None, tail=te.get('type') if te is not None else None)

    def marker(self, kind, col, w, start):
        key = (kind, col, start)
        if key in self.markers:
            return self.markers[key]
        mid = self.uid('m')
        s = 3.0
        d = f'M0,0 L{s * 2},{s} L0,{s * 2} z' if kind in ('triangle', 'stealth') else f'M0,0 L{s * 2},{s} L0,{s * 2} L{s * 0.6},{s} z'
        if kind == 'oval':
            d = None
        ref = f'refX="{s * 2}"' if not start else f'refX="0"'
        ori = 'auto-start-reverse' if start else 'auto'
        if kind in ('arrow',):
            m = f'<marker id="{mid}" markerWidth="{s * 2}" markerHeight="{s * 2}" {ref} refY="{s}" orient="{ori}" markerUnits="strokeWidth"><path d="M0,0 L{s * 2},{s} L0,{s * 2}" fill="none" stroke="{col}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></marker>'
        elif d:
            m = f'<marker id="{mid}" markerWidth="{s * 2}" markerHeight="{s * 2}" {ref} refY="{s}" orient="{ori}" markerUnits="strokeWidth"><path d="{d}" fill="{col}"/></marker>'
        else:
            m = f'<marker id="{mid}" markerWidth="{s * 2}" markerHeight="{s * 2}" refX="{s}" refY="{s}" orient="{ori}" markerUnits="strokeWidth"><circle cx="{s}" cy="{s}" r="{s * 0.8}" fill="{col}"/></marker>'
        self.defs.append(m)
        self.markers[key] = mid
        return mid

    def stroke_attrs(self, st, closed_shape=False):
        if not st:
            return 'stroke="none"'
        a = f'stroke="{st["color"]}" stroke-width="{st["w"]:.2f}"'
        if st['alpha'] < 1:
            a += f' stroke-opacity="{st["alpha"]:.3f}"'
        if st['dash'] and st['dash'] != 'solid':
            dd = {'dash': '4 3', 'sysDash': '3 1', 'dot': '1 2', 'sysDot': '1 1', 'lgDash': '8 3', 'dashDot': '4 3 1 3', 'lgDashDot': '8 3 1 3', 'sysDashDot': '3 1 1 1'}.get(st['dash'], '4 3')
            a += f' stroke-dasharray="{" ".join(str(float(x) * max(st["w"], 1)) for x in dd.split())}"'
        if not closed_shape:
            if st['head']:
                a += f' marker-start="url(#{self.marker(st["head"], st["color"] if st["color"].startswith("#") else "#333", st["w"], True)})"'
            if st['tail']:
                a += f' marker-end="url(#{self.marker(st["tail"], st["color"] if st["color"].startswith("#") else "#333", st["w"], False)})"'
        return a + ' stroke-linejoin="round" stroke-linecap="round"'

    def xfrm(self, el, ctx):
        x = el.find(q('a:xfrm'))
        if x is None:
            x = el.find('.//' + q('a:xfrm'))
        off, ext = x.find(q('a:off')), x.find(q('a:ext'))
        ox, oy = int(off.get('x')), int(off.get('y'))
        w, h = int(ext.get('cx')), int(ext.get('cy'))
        rot = int(x.get('rot', '0')) / 60000
        fh, fv = x.get('flipH') == '1', x.get('flipV') == '1'
        sx, sy, tx, ty = ctx
        return (tx + ox * sx) / EMU, (ty + oy * sy) / EMU, w * sx / EMU, h * sy / EMU, rot, fh, fv, x

    def transform(self, x, y, w, h, rot, fh, fv):
        t = f'translate({x:.2f},{y:.2f})'
        if rot:
            t += f' rotate({rot:.2f},{w / 2:.2f},{h / 2:.2f})'
        if fh or fv:
            t += f' translate({w / 2:.2f},{h / 2:.2f}) scale({-1 if fh else 1},{-1 if fv else 1}) translate({-w / 2:.2f},{-h / 2:.2f})'
        return t

    def geom_path(self, sp_pr, w, h):
        pg = sp_pr.find(q('a:prstGeom'))
        if pg is not None:
            prst = pg.get('prst')
            adj = {g.get('name'): int(g.get('fmla').split()[-1]) for g in pg.findall('.//' + q('a:gd'))}
            return self.preset(prst, adj, w, h)
        cg = sp_pr.find(q('a:custGeom'))
        if cg is not None:
            ds = []
            for path in cg.find(q('a:pathLst')):
                pw, ph = int(path.get('w') or 0), int(path.get('h') or 0)
                sx = w / pw if pw else 1
                sy = h / ph if ph else 1
                d = ''
                for cmd in path:
                    n = etree.QName(cmd).localname
                    pts = [(float(p.get('x')) * sx, float(p.get('y')) * sy) for p in cmd.findall(q('a:pt'))]
                    if n == 'moveTo':
                        d += f'M{pts[0][0]:.2f},{pts[0][1]:.2f} '
                    elif n == 'lnTo':
                        d += f'L{pts[0][0]:.2f},{pts[0][1]:.2f} '
                    elif n == 'cubicBezTo':
                        d += 'C' + ' '.join(f'{p[0]:.2f},{p[1]:.2f}' for p in pts) + ' '
                    elif n == 'quadBezTo':
                        d += 'Q' + ' '.join(f'{p[0]:.2f},{p[1]:.2f}' for p in pts) + ' '
                    elif n == 'arcTo':
                        wr, hr = float(cmd.get('wR')) * sx, float(cmd.get('hR')) * sy
                        st, sw = float(cmd.get('stAng')) / 60000, float(cmd.get('swAng')) / 60000
                        d += f'a{wr:.2f},{hr:.2f} 0 {1 if abs(sw) > 180 else 0} {1 if sw > 0 else 0} '
                        cx = math.cos(math.radians(st + sw)) - math.cos(math.radians(st))
                        cy = math.sin(math.radians(st + sw)) - math.sin(math.radians(st))
                        d += f'{wr * cx:.2f},{hr * cy:.2f} '
                    elif n == 'close':
                        d += 'Z '
                ds.append((d, path.get('fill') != 'none', path.get('stroke') != '0'))
            return ds, False
        return [(f'M0,0 L{w:.2f},0 L{w:.2f},{h:.2f} L0,{h:.2f} Z', True, True)], True

    def preset(self, prst, adj, w, h):
        closed = True
        if prst in ('rect', 'flowChartProcess'):
            d = f'M0,0 H{w:.2f} V{h:.2f} H0 Z'
        elif prst == 'roundRect':
            r = min(w, h) * adj.get('adj', 16667) / 100000
            d = f'M{r:.2f},0 H{w - r:.2f} A{r:.2f},{r:.2f} 0 0 1 {w:.2f},{r:.2f} V{h - r:.2f} A{r:.2f},{r:.2f} 0 0 1 {w - r:.2f},{h:.2f} H{r:.2f} A{r:.2f},{r:.2f} 0 0 1 0,{h - r:.2f} V{r:.2f} A{r:.2f},{r:.2f} 0 0 1 {r:.2f},0 Z'
        elif prst == 'ellipse':
            d = f'M{w / 2:.2f},0 A{w / 2:.2f},{h / 2:.2f} 0 1 1 {w / 2:.2f},{h:.2f} A{w / 2:.2f},{h / 2:.2f} 0 1 1 {w / 2:.2f},0 Z'
        elif prst == 'trapezoid':
            a = min(w, h) * adj.get('adj', 25000) / 100000
            d = f'M{a:.2f},0 H{w - a:.2f} L{w:.2f},{h:.2f} H0 Z'
        elif prst == 'triangle':
            d = f'M{w * adj.get("adj", 50000) / 100000:.2f},0 L{w:.2f},{h:.2f} H0 Z'
        elif prst == 'diamond':
            d = f'M{w / 2:.2f},0 L{w:.2f},{h / 2:.2f} L{w / 2:.2f},{h:.2f} L0,{h / 2:.2f} Z'
        elif prst in ('leftBracket', 'rightBracket'):
            r = min(w, h) * adj.get('adj', 8333) / 100000
            closed = False
            if prst == 'leftBracket':
                d = f'M{w:.2f},0 H{r:.2f} Q0,0 0,{r:.2f} V{h - r:.2f} Q0,{h:.2f} {r:.2f},{h:.2f} H{w:.2f}'
            else:
                d = f'M0,0 H{w - r:.2f} Q{w:.2f},0 {w:.2f},{r:.2f} V{h - r:.2f} Q{w:.2f},{h:.2f} {w - r:.2f},{h:.2f} H0'
        elif prst in ('line', 'straightConnector1'):
            d = f'M0,0 L{w:.2f},{h:.2f}'
            closed = False
        elif prst == 'bentConnector2':
            d = f'M0,0 H{w:.2f} V{h:.2f}'
            closed = False
        elif prst == 'bentConnector3':
            a = adj.get('adj1', 50000) / 100000
            d = f'M0,0 H{w * a:.2f} V{h:.2f} H{w:.2f}'
            closed = False
        elif prst in ('rightArrow', 'leftArrow', 'upArrow', 'downArrow'):
            a1 = adj.get('adj1', 50000) / 100000
            a2 = adj.get('adj2', 50000) / 100000
            if prst == 'rightArrow':
                hw = h * a1 / 2
                hl = min(w, h) * a2
                d = f'M0,{h / 2 - hw:.2f} H{w - hl:.2f} V0 L{w:.2f},{h / 2:.2f} L{w - hl:.2f},{h:.2f} V{h / 2 + hw:.2f} H0 Z'
            elif prst == 'downArrow':
                hw = w * a1 / 2
                hl = min(w, h) * a2
                d = f'M{w / 2 - hw:.2f},0 V{h - hl:.2f} H0 L{w / 2:.2f},{h:.2f} L{w:.2f},{h - hl:.2f} H{w / 2 + hw:.2f} V0 Z'
            else:
                d = f'M0,0 H{w:.2f} V{h:.2f} H0 Z'
        elif prst == 'chord':
            d = f'M{w / 2:.2f},0 A{w / 2:.2f},{h / 2:.2f} 0 0 1 {w:.2f},{h / 2:.2f} Z'
        elif prst == 'snip1Rect':
            s = min(w, h) * adj.get('adj', 16667) / 100000
            d = f'M0,0 H{w - s:.2f} L{w:.2f},{s:.2f} V{h:.2f} H0 Z'
        elif prst == 'cube':
            s = min(w, h) * adj.get('adj', 25000) / 100000
            d = f'M0,{s:.2f} H{w - s:.2f} V{h:.2f} H0 Z M0,{s:.2f} L{s:.2f},0 H{w:.2f} L{w - s:.2f},{s:.2f} Z M{w - s:.2f},{s:.2f} L{w:.2f},0 V{h - s:.2f} L{w - s:.2f},{h:.2f} Z'
        elif prst == 'wedgeRectCallout':
            d = f'M0,0 H{w:.2f} V{h:.2f} H0 Z'
        elif prst == 'flowChartMagneticDisk' or prst == 'can':
            ry = h * 0.12
            d = f'M0,{ry:.2f} A{w / 2:.2f},{ry:.2f} 0 0 1 {w:.2f},{ry:.2f} V{h - ry:.2f} A{w / 2:.2f},{ry:.2f} 0 0 1 0,{h - ry:.2f} Z M0,{ry:.2f} A{w / 2:.2f},{ry:.2f} 0 0 0 {w:.2f},{ry:.2f}'
        elif prst == 'plus':
            a = min(w, h) * adj.get('adj', 25000) / 100000
            d = f'M{a:.2f},0 H{w - a:.2f} V{a:.2f} H{w:.2f} V{h - a:.2f} H{w - a:.2f} V{h:.2f} H{a:.2f} V{h - a:.2f} H0 V{a:.2f} H{a:.2f} Z'
        elif prst == 'mathPlus':
            a = min(w, h) * adj.get('adj1', 23520) / 100000
            d = f'M{w / 2 - a / 2:.2f},{h * 0.15:.2f} H{w / 2 + a / 2:.2f} V{h / 2 - a / 2:.2f} H{w * 0.85:.2f} V{h / 2 + a / 2:.2f} H{w / 2 + a / 2:.2f} V{h * 0.85:.2f} H{w / 2 - a / 2:.2f} V{h / 2 + a / 2:.2f} H{w * 0.15:.2f} V{h / 2 - a / 2:.2f} H{w / 2 - a / 2:.2f} Z'
        elif prst == 'curvedConnector3':
            a = adj.get('adj1', 50000) / 100000
            d = f'M0,0 C{w * a:.2f},0 {w * a:.2f},{h:.2f} {w:.2f},{h:.2f}'
            closed = False
        elif prst == 'parallelogram':
            a = min(w, h) * adj.get('adj', 25000) / 100000
            d = f'M{a:.2f},0 H{w:.2f} L{w - a:.2f},{h:.2f} H0 Z'
        elif prst == 'hexagon':
            a = min(w, h) * adj.get('adj', 25000) / 100000
            d = f'M{a:.2f},0 H{w - a:.2f} L{w:.2f},{h / 2:.2f} L{w - a:.2f},{h:.2f} H{a:.2f} L0,{h / 2:.2f} Z'
        elif prst == 'arc':
            st, sw = adj.get('adj1', 16200000) / 60000, adj.get('adj2', 0) / 60000
            sweep = (sw - st) % 360
            x0, y0 = w / 2 + w / 2 * math.cos(math.radians(st)), h / 2 + h / 2 * math.sin(math.radians(st))
            x1, y1 = w / 2 + w / 2 * math.cos(math.radians(sw)), h / 2 + h / 2 * math.sin(math.radians(sw))
            d = f'M{x0:.2f},{y0:.2f} A{w / 2:.2f},{h / 2:.2f} 0 {1 if sweep > 180 else 0} 1 {x1:.2f},{y1:.2f}'
            closed = False
        else:
            d = f'M0,0 H{w:.2f} V{h:.2f} H0 Z'
        return [(d, closed, True)], closed

    def text(self, tx_body, w, h, rot_in_shape=0):
        if tx_body is None:
            return ''
        bp = tx_body.find(q('a:bodyPr'))
        ins = {k: int(bp.get(k, v)) / EMU for k, v in (('lIns', '91440'), ('tIns', '45720'), ('rIns', '91440'), ('bIns', '45720'))} if bp is not None else dict(lIns=7.2, tIns=3.6, rIns=7.2, bIns=3.6)
        anchor = bp.get('anchor', 't') if bp is not None else 't'
        vert = bp.get('vert') if bp is not None else None
        wrap = (bp.get('wrap', 'square') if bp is not None else 'square') != 'none'
        paras = tx_body.findall(q('a:p'))
        lines = []
        for p in paras:
            ppr = p.find(q('a:pPr'))
            algn = ppr.get('algn', 'l') if ppr is not None else 'l'
            dr = ppr.find(q('a:defRPr')) if ppr is not None else None
            runs = []
            for r in p:
                n = etree.QName(r).localname
                if n not in ('r', 'br', 'fld'):
                    continue
                if n == 'br':
                    runs.append(None)
                    continue
                rpr = r.find(q('a:rPr'))
                t = r.findtext(q('a:t')) or ''
                sz = None
                for src in (rpr, dr):
                    if src is not None and src.get('sz'):
                        sz = int(src.get('sz')) / 100
                        break
                sz = sz or 18
                b = (rpr is not None and rpr.get('b') == '1') or (dr is not None and dr.get('b') == '1' and (rpr is None or rpr.get('b') is None))
                i = (rpr is not None and rpr.get('i') == '1')
                col = None
                for src in (rpr, dr):
                    if src is not None and src.find(q('a:solidFill')) is not None:
                        col, _ = self.color(src.find(q('a:solidFill')))
                        break
                font = None
                for src in (rpr, dr):
                    if src is not None and src.find(q('a:latin')) is not None:
                        font = src.find(q('a:latin')).get('typeface')
                        break
                base = rpr.get('baseline') if rpr is not None else None
                runs.append(dict(t=t, sz=sz, b=b, i=i, col=col or '#000000', font=font, base=int(base) / 100000 if base else 0))
            if not runs:
                epr = p.find(q('a:endParaRPr'))
                sz = int(epr.get('sz')) / 100 if epr is not None and epr.get('sz') else (int(dr.get('sz')) / 100 if dr is not None and dr.get('sz') else 18)
                lines.append(dict(algn=algn, runs=[], sz=sz))
                continue
            cur = []
            for r in runs:
                if r is None:
                    lines.append(dict(algn=algn, runs=cur, sz=max(x['sz'] for x in cur) if cur else 18))
                    cur = []
                else:
                    cur.append(r)
            lines.append(dict(algn=algn, runs=cur, sz=max(x['sz'] for x in cur) if cur else 18))
        if not any(l['runs'] for l in lines):
            return ''
        if wrap:
            avail = w - ins['lIns'] - ins['rIns']
            wrapped = []
            for l in lines:
                words = []
                for r in l['runs']:
                    for tok in re.split(r'(\s+)', r['t']):
                        if tok:
                            words.append(dict(r, t=tok))
                cur, cw = [], 0
                for wd in words:
                    ww = len(wd['t']) * wd['sz'] * 0.52
                    if cur and cw + ww > avail and not wd['t'].isspace():
                        wrapped.append(dict(l, runs=cur))
                        cur, cw = [], 0
                        if wd['t'].isspace():
                            continue
                    cur.append(wd)
                    cw += ww
                wrapped.append(dict(l, runs=cur, sz=l['sz']))
            lines = wrapped
        lh = [l['sz'] * 1.2 for l in lines]
        total = sum(lh)
        box_w, box_h = (h, w) if vert in ('vert', 'vert270') else (w, h)
        if anchor == 'ctr':
            y0 = (box_h - total) / 2
        elif anchor == 'b':
            y0 = box_h - ins['bIns'] - total
        else:
            y0 = ins['tIns']
        out = []
        y = y0
        for l, lhh in zip(lines, lh):
            y += lhh
            if l['algn'] == 'ctr':
                x, ta = box_w / 2, 'middle'
            elif l['algn'] == 'r':
                x, ta = box_w - ins['rIns'], 'end'
            else:
                x, ta = ins['lIns'], 'start'
            spans = ''
            for r in l['runs']:
                st = f'font-size:{r["sz"]:.1f}px;fill:{r["col"]}'
                if r['b']:
                    st += ';font-weight:600'
                if r['i']:
                    st += ';font-style:italic'
                if r['font']:
                    st += f';font-family:{FONT_MAP.get(r["font"], r["font"])}'
                if r['base']:
                    st += f';baseline-shift:{r["base"] * 100:.0f}%;font-size:{r["sz"] * 0.65:.1f}px'
                t = r['t'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                spans += f'<tspan style="{st}">{t}</tspan>'
            out.append(f'<text x="{x:.2f}" y="{y - l["sz"] * 0.3:.2f}" text-anchor="{ta}" xml:space="preserve">{spans}</text>')
        g = ''.join(out)
        if vert == 'vert270':
            return f'<g transform="translate(0,{h:.2f}) rotate(-90)">{g}</g>'
        if vert == 'vert':
            return f'<g transform="translate({w:.2f},0) rotate(90)">{g}</g>'
        return g

    def picture(self, pic, rels, ctx):
        x, y, w, h, rot, fh, fv, _ = self.xfrm(pic.find(q('p:spPr')), ctx)
        blip = pic.find('.//' + q('a:blip'))
        rid = blip.get(q('r:embed')) if blip is not None else None
        if rid is None or rid not in rels:
            return ''
        src = rels[rid]
        alpha = 1.0
        am = blip.find(q('a:alphaModFix'))
        if am is not None:
            alpha = int(am.get('amt', '100000')) / 100000
        if src.lower().endswith('.emf'):
            hsh = hashlib.md5(self.d.z.read(src)).hexdigest()[:10]
            fn = self.emf_sub.get(hsh)
            name = pic.find('.//' + q('p:cNvPr')).get('name')
            return f'<g id="{self.uid("p")}" data-name="{self.esc(name)}" data-emf="{hsh}" data-bbox="{x:.1f} {y:.1f} {w:.1f} {h:.1f}" transform="{self.transform(x, y, w, h, rot, fh, fv)}">{fn(w, h) if fn else ""}</g>'
        href = self.save_image(src)
        sr = pic.find('.//' + q('a:srcRect'))
        name = pic.find('.//' + q('p:cNvPr')).get('name')
        st = self.stroke(pic.find(q('p:spPr')))
        gid = self.uid('p')
        inner = ''
        if sr is not None and any(sr.get(k) for k in ('l', 't', 'r', 'b')):
            l, t, r, b = [int(sr.get(k, '0')) / 100000 for k in ('l', 't', 'r', 'b')]
            cw, ch = w / (1 - l - r), h / (1 - t - b)
            self.defs.append(f'<clipPath id="{gid}c"><rect width="{w:.2f}" height="{h:.2f}"/></clipPath>')
            inner = f'<image clip-path="url(#{gid}c)" x="{-l * cw:.2f}" y="{-t * ch:.2f}" width="{cw:.2f}" height="{ch:.2f}" href="{href}" preserveAspectRatio="none"/>'
        else:
            inner = f'<image width="{w:.2f}" height="{h:.2f}" href="{href}" preserveAspectRatio="none"/>'
        op = f' opacity="{alpha:.3f}"' if alpha < 1 else ''
        border = f'<rect width="{w:.2f}" height="{h:.2f}" fill="none" {self.stroke_attrs(st, True)}/>' if st else ''
        return f'<g id="{gid}" data-name="{self.esc(name)}" data-bbox="{x:.1f} {y:.1f} {w:.1f} {h:.1f}" transform="{self.transform(x, y, w, h, rot, fh, fv)}"{op}>{inner}{border}</g>'

    def save_image(self, src):
        if src in self.d.images:
            return self.d.images[src]
        data = self.d.z.read(src)
        ext = os.path.splitext(src)[1].lower()
        hsh = hashlib.md5(data).hexdigest()[:10]
        if ext == '.svg':
            fn = f'{hsh}.svg'
            open(os.path.join(self.out, self.imgdir, fn), 'wb').write(data)
        else:
            im = Image.open(io.BytesIO(data))
            fn = f'{hsh}.webp' if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.gif') else f'{hsh}{ext}'
            if fn.endswith('.webp'):
                if max(im.size) > 1600:
                    im.thumbnail((1600, 1600))
                im.save(os.path.join(self.out, self.imgdir, fn), 'WEBP', quality=88, method=6)
            else:
                open(os.path.join(self.out, self.imgdir, fn), 'wb').write(data)
        self.d.images[src] = f'{self.imgdir}/{fn}'
        return self.d.images[src]

    @staticmethod
    def esc(s):
        return (s or '').replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')

    def shape(self, sp, rels, ctx):
        sp_pr = sp.find(q('p:spPr'))
        style = sp.find(q('p:style'))
        if sp_pr is None or sp_pr.find(q('a:xfrm')) is None:
            return ''
        x, y, w, h, rot, fh, fv, _ = self.xfrm(sp_pr, ctx)
        name = sp.find('.//' + q('p:cNvPr')).get('name')
        fill, fa = self.fill(sp_pr, style)
        st = self.stroke(sp_pr, style)
        paths, closed = self.geom_path(sp_pr, w, h)
        fattr = f'fill="{fill}"' + (f' fill-opacity="{fa:.3f}"' if fa < 1 and fill != 'none' else '')
        body = ''
        for d, pf, ps in paths:
            body += f'<path d="{d}" {fattr if pf else "fill=\"none\""} {self.stroke_attrs(st, closed) if ps else "stroke=\"none\""}/>'
        body += self.text(sp.find(q('p:txBody')), w, h)
        sh = ''
        for e in sp_pr.iter(q('a:outerShdw')):
            sh = ' filter="url(#shadow)"'
            break
        return f'<g id="{self.uid("s")}" data-name="{self.esc(name)}" data-bbox="{x:.1f} {y:.1f} {w:.1f} {h:.1f}" transform="{self.transform(x, y, w, h, rot, fh, fv)}"{sh}>{body}</g>'

    def group(self, grp, rels, ctx):
        gp = grp.find(q('p:grpSpPr'))
        x = gp.find(q('a:xfrm'))
        off, ext, cho, che = x.find(q('a:off')), x.find(q('a:ext')), x.find(q('a:chOff')), x.find(q('a:chExt'))
        sx, sy, tx, ty = ctx
        cw, ch = int(che.get('cx')) or 1, int(che.get('cy')) or 1
        nsx, nsy = sx * int(ext.get('cx')) / cw, sy * int(ext.get('cy')) / ch
        ntx = tx + sx * int(off.get('x')) - nsx * int(cho.get('x'))
        nty = ty + sy * int(off.get('y')) - nsy * int(cho.get('y'))
        rot = int(x.get('rot', '0')) / 60000
        name = grp.find('.//' + q('p:cNvPr')).get('name')
        inner = ''.join(self.walk(c, rels, (nsx, nsy, ntx, nty)) for c in grp)
        tr = ''
        if rot:
            cx, cy = (tx + sx * (int(off.get('x')) + int(ext.get('cx')) / 2)) / EMU, (ty + sy * (int(off.get('y')) + int(ext.get('cy')) / 2)) / EMU
            tr = f' transform="rotate({rot:.2f},{cx:.2f},{cy:.2f})"'
        bx, by = (tx + sx * int(off.get('x'))) / EMU, (ty + sy * int(off.get('y'))) / EMU
        bw, bh = sx * int(ext.get('cx')) / EMU, sy * int(ext.get('cy')) / EMU
        return f'<g id="{self.uid("grp")}" data-name="{self.esc(name)}" data-bbox="{bx:.1f} {by:.1f} {bw:.1f} {bh:.1f}"{tr}>{inner}</g>'

    def walk(self, el, rels, ctx):
        n = etree.QName(el).localname
        if n == 'sp':
            return self.shape(el, rels, ctx)
        if n == 'cxnSp':
            return self.shape(el, rels, ctx)
        if n == 'pic':
            return self.picture(el, rels, ctx)
        if n == 'grpSp':
            return self.group(el, rels, ctx)
        if n == 'graphicFrame':
            return ''
        return ''

    def slide(self, idx):
        path = self.d.slides[idx]
        root = etree.fromstring(self.d.z.read(path))
        rels = self.d.rels(path)
        tree = root.find(q('p:cSld')).find(q('p:spTree'))
        self.defs, self.body, self.markers = ['<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="1" dy="1.5" stdDeviation="1.5" flood-opacity="0.18"/></filter>'], [], {}
        body = ''.join(self.walk(c, rels, (1, 1, 0, 0)) for c in tree)
        W, H = self.d.w / EMU, self.d.h / EMU
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {H:.2f}" width="{W:.2f}" height="{H:.2f}" font-family="Inter, system-ui, sans-serif"><defs>{"".join(self.defs)}</defs>{body}</svg>'


def main():
    deck = Deck(sys.argv[1])
    out = sys.argv[2]
    name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    idxs = [int(a) for a in sys.argv[3:]] or list(range(len(deck.slides)))
    conv = Conv(deck, out, name)
    for i in idxs:
        svg = conv.slide(i)
        open(os.path.join(out, f'{name}_{i:02d}.svg'), 'w').write(svg)
        print(f'{name}_{i:02d}.svg', len(svg))


if __name__ == '__main__':
    main()
