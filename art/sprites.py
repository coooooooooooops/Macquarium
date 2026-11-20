"""Macquarium fish v3: hand-drawn silhouettes + shared shading.

Silhouette key (fish faces right):
  #  body          p  pectoral fin (over body)    e  eye     h  eye highlight
  d  dorsal fin    a  anal / pelvic fin           t  tail    m  mouth
  .  empty
Colours come from each species' ramps; patterns get (x, y, u, v) where u runs
tail->nose (0..1) and v back->belly (0..1) within the body.
"""
import math
import numpy as np
from PIL import Image
from fishgen2 import ramp, hx, smooth, hash2, vnoise

BLACK, WHITE = hx('#17171c'), hx('#f7f6ef')


def build(rows, body, belly=None, fin=None, tail=None, fin_alpha=0.7, pattern=None, finpat=None,
          noise=0.05, seed=1, eye='#0b0d12', outline=0.78, rays=True, belly_v=0.58):
    w = max(len(r) for r in rows); g = [r.ljust(w, '.') for r in rows]; h = len(g)
    B = ramp(body); BL = ramp(belly) if belly else None
    F = ramp(fin or body, lo=0.45, hi=1.25); T = ramp(tail or fin or body, lo=0.45, hi=1.25)
    isbody = lambda c: c in '#pemhg'
    xs = [x for y in range(h) for x in range(w) if isbody(g[y][x])]
    x0, x1 = min(xs), max(xs)
    cols = {}
    for x in range(w):
        ys = [y for y in range(h) if isbody(g[y][x])]
        if ys: cols[x] = (min(ys), max(ys))
    out = np.zeros((h, w, 4))
    n = len(B)
    for y in range(h):
        for x in range(w):
            c = g[y][x]
            if c == '.': continue
            jit = (hash2(x, y, seed) - 0.5) * 0.45
            if isbody(c):
                t0, t1 = cols[x]; v = (y - t0 + 0.5) / (t1 - t0 + 1); u = (x - x0) / max(1, x1 - x0)
                lum = 0.22 + 0.80 * smooth(0.0, 0.75, v) - 0.16 * smooth(0.88, 1.0, v)
                lum += 0.10 * math.exp(-((v - 0.28) / 0.12) ** 2)
                lum += (vnoise(x, y, 2.3, seed) - 0.5) * noise * 3 - 0.06 * smooth(0.92, 1, u)
                R = B
                if BL is not None and v > belly_v + jit * 0.15: R = BL; lum = 0.5 + 0.4 * v
                col = R[int(np.clip(round(lum * (n - 1) + jit), 0, n - 1))]
                if pattern:
                    r = pattern(x, y, u, v)
                    if r is not None:
                        col = r[int(np.clip(round(lum * (n - 1) + jit), 0, n - 1))] if isinstance(r, list) else \
                              r * np.clip(0.62 + lum * 0.6, 0.55, 1.12)
                a = 255
                if c == 'p': col = col * 0.55 + F[4] * 0.45
                if c == 'e': col = hx(eye)
                if c == 'h': col = hx('#eef3fb')
                if c == 'm': col = col * 0.5
                if c == 'g': col = B[1]
            else:
                R = T if c == 't' else F
                lum = 0.52 + jit * 0.3
                if rays and ((c == 't' and y % 2 == 0) or (c in 'da' and x % 2 == 0)): lum -= 0.15
                # fin edge (touching empty) is a touch darker and more opaque
                edge = any(not (0 <= y + dy < h and 0 <= x + dx < w) or g[y + dy][x + dx] == '.'
                           for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)))
                col = R[int(np.clip(round(lum * (n - 1)), 0, n - 1))]
                if finpat:
                    r = finpat(c, x, y, edge)
                    if r is not None: col = r
                a = 255 * min(1, fin_alpha + (0.18 if edge else 0) + (0.25 if c == 't' and x >= min(cols) - 1 else 0))
                if edge: col = col * 0.85
            out[y, x] = list(np.clip(col, 0, 255)) + [a]
    # outline around body only: dark on top/front, softer underneath
    res = np.zeros((h + 2, w + 2, 4)); res[1:-1, 1:-1] = out
    G = [('.' * (w + 2))] + ['.' + r + '.' for r in g] + [('.' * (w + 2))]
    fin_res = res.copy()
    for y in range(h + 2):
        for x in range(w + 2):
            if G[y][x] in '.da':
                nb = [(dy, dx) for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))
                      if 0 <= y + dy < h + 2 and 0 <= x + dx < w + 2 and isbody(G[y + dy][x + dx])]
                if not nb: continue
                under = all(dy == -1 for dy, dx in nb)
                oc = B[1] if under else B[0] * outline
                if G[y][x] == '.':
                    fin_res[y, x] = list(oc) + [255]
                else:
                    fin_res[y, x, :3] = fin_res[y, x, :3] * 0.4 + oc * 0.6; fin_res[y, x, 3] = 255
    return Image.fromarray(np.clip(fin_res, 0, 255).astype('uint8'), 'RGBA')


def cols_band(x, centers, white=WHITE, edge=BLACK):
    for c in centers:
        if x in c[0]: return white
        if x in c[1]: return edge
    return None


S = {}

# ----------------------------------------------------------------- clownfish 18px
S['Clownfish'] = lambda: build([
    "......ddddd.......",
    "....dddddddd......",
    "tt..###########...",
    "ttt#############..",
    "ttt###########eh#.",
    "ttt##############m",
    "ttt####pp#######..",
    "tt..###########...",
    "......aaa..aa.....",
    ".......a..........",
], body='#f27a1d', fin='#f58a2a', fin_alpha=0.9,
    pattern=lambda x, y, u, v: cols_band(x, [((4,), ()), ((8, 9), ()), ((12,), (13,))]),
    finpat=lambda c, x, y, e: BLACK if e and c != 't' or (c == 't' and x == 0) else None)

# ----------------------------------------------------------------- blue tang 26px
def _bt(x, y, u, v):
    if 0.05 < u < 0.86 and abs(v - (0.32 + 0.22 * math.sin(u * 3.1 + 0.5))) < 0.09: return BLACK
    if 0.08 < u < 0.42 and 0.52 < v < 0.68: return BLACK
S['Blue Tang'] = lambda: build([
    "..........ddddddd.........",
    ".......dddddddddddd.......",
    "t....################.....",
    "tt..###################...",
    "ttt#####################..",
    ".tt####################eh.",
    "..t######################m",
    ".tt#######pp############..",
    "ttt#####################..",
    "tt..###################...",
    "t....################.....",
    ".......aaaaaaaaa..a.......",
    "..........aaaaa...........",
], body='#2a62e6', fin='#2a55cc', tail='#ffd21f', fin_alpha=0.88, pattern=_bt,
    finpat=lambda c, x, y, e: BLACK if e and c == 'd' else None)

# ----------------------------------------------------------------- yellow tang 20px
S['Yellow Tang'] = lambda: build([
    ".........ddd........",
    ".......dddddd.......",
    ".....dddddddddd.....",
    "....dddddddddddd....",
    "....############....",
    "t..###############..",
    "tt.############eh#..",
    "tt##################",
    "tt###############mm#",
    "tt################..",
    "t..##pp##########...",
    "....############....",
    "....aaaaaaaaaaaa....",
    ".....aaaaaaaaaa.....",
    ".......aaaaaa.......",
    ".........aa.........",
], body='#ffd31c', fin='#f7c300', fin_alpha=0.85,
    pattern=lambda x, y, u, v: WHITE if x == 3 and y in (7, 8) else None)

# ----------------------------------------------------------------- copperband 20px
def _cb(x, y, u, v):
    for xs in ((5, 6), (9, 10), (13, 14)):
        if x in xs: return hx('#e9792b')
        if x in (xs[0] - 1, xs[1] + 1): return BLACK
S['Copperband'] = lambda: build([
    "......dddd..........",
    "....ddddddddd.......",
    "...ddddddddddd......",
    "..d###########......",
    "tt##############....",
    "tt#############eh...",
    "tt################mm",
    "tt###############...",
    "tt#####pp#######....",
    "..#############.....",
    "...aaaaaaaaaa.......",
    "....aaaaaaa.........",
], body='#eeece4', fin='#e8e3d6', fin_alpha=0.8, pattern=_cb,
    finpat=lambda c, x, y, e: BLACK if (c == 'd' and x in (4, 5) and y in (1, 2)) else (hx('#e9792b') if c == 't' and x == 1 else None))

# ----------------------------------------------------------------- moorish idol 20px
def _mi(x, y, u, v):
    if x <= 4 or x in (12, 13, 14): return BLACK
    if 5 <= x <= 8: return ramp('#ffd21a')
    if x >= 17 and y in (8, 9): return hx('#ff8c2a')
S['Moorish Idol'] = lambda: build([
    "dddd................",
    "...ddd..............",
    ".....dd.............",
    "......ddd...........",
    "......ddddd.........",
    ".....ddddddd........",
    "....###########.....",
    "t..##############...",
    "tt#############eh#..",
    "tt#################mm",
    "tt################..",
    "t..##############...",
    "....###########.....",
    ".....aaaaaaaa.......",
    "......aaaaa.........",
    "........aa..........",
], body='#f3f0e2', fin='#f1eee1', tail='#17171c', fin_alpha=0.85, pattern=_mi,
    finpat=lambda c, x, y, e: BLACK if c == 'a' and x > 9 else None)

# ----------------------------------------------------------------- royal gramma 13px
S['Royal Gramma'] = lambda: build([
    "...ddddddd...",
    "t.#########..",
    "tt#######eh#.",
    "tt##########m",
    "t.#########..",
    "...aaa.......",
], body='#8a3cd8', fin='#9b52e2', fin_alpha=0.85,
    pattern=lambda x, y, u, v: ramp('#ffc31d') if x <= 6 - (y > 2) else None,
    finpat=lambda c, x, y, e: ramp('#ffc31d')[4] if c == 't' or x <= 5 else None)

# ----------------------------------------------------------------- green chromis 11px
S['Green Chromis'] = lambda: build([
    "....ddd....",
    "t.#######..",
    "tt####eh##.",
    ".t#######m.",
    "tt######...",
    "t..aa......",
], body='#58cfa8', belly='#b6eedb', fin='#7fdcc0', fin_alpha=0.6)

# ----------------------------------------------------------------- anthias 13px
S['Anthias'] = lambda: build([
    "....dddddd...",
    "t..#########.",
    "tt#######eh#.",
    ".t##########m",
    "tt#########..",
    "t...aaa......",
], body='#ff7656', belly='#ffc4a6', fin='#ff9a70', fin_alpha=0.65,
    pattern=lambda x, y, u, v: hx('#c46aff') if (x, y) in ((10, 3), (9, 4), (8, 4)) else None)

# ----------------------------------------------------------------- cleaner wrasse 14px
S['Cleaner Wrasse'] = lambda: build([
    "...ddddddd....",
    "t.##########..",
    "tt#########eh.",
    "tt###########m",
    "t.##########..",
    "....aaaa......",
], body='#eaf2f7', fin='#a7d0ff', fin_alpha=0.6,
    pattern=lambda x, y, u, v: BLACK if (y == 2 and x < 11) or (y == 3 and x < 5) else (ramp('#4fb3ff') if y == 1 else None),
    finpat=lambda c, x, y, e: BLACK if c == 't' and y in (2, 3) else None)

# ----------------------------------------------------------------- parrotfish 30px
def _pf(x, y, u, v):
    if u > 0.9 and v > 0.45: return hx('#e9f6f1')
    if (x + (y % 2) * 3) % 6 == 0 and 0.06 < u < 0.86 and hash2(x, y, 3) < 0.7: return ramp('#d985a8')
S['Parrotfish'] = lambda: build([
    ".......dddddddddddddddd.......",
    "t...######################....",
    "tt.##########################.",
    "ttt#####################eh####",
    "ttt###########################",
    "ttt######pp##################m",
    "tt.##########################.",
    "t...######################....",
    "........aaaaaaa...aa..........",
], body='#29b597', fin='#ff86b4', tail='#ff86b4', fin_alpha=0.85, pattern=_pf)

# ----------------------------------------------------------------- grouper 36px
def _gr(x, y, u, v):
    n = vnoise(x, y, 2.8, 41)
    if n > 0.64: return ramp('#3b2b1b')
    if n < 0.24: return ramp('#b89c72')
S['Grouper'] = lambda: build([
    "........dddddddddddddddddd..........",
    "......dddddddddddddddddddddd........",
    "tt...###########################....",
    "ttt.##############################..",
    "ttt###########################eh###.",
    "ttt################################.",
    "ttt#################################",
    "ttt######ppp######################mm",
    "ttt###############################..",
    "tt..############################....",
    ".......aaaaaa.......aaa.............",
    "........aaaa........aa..............",
], body='#7a6447', fin='#6b573d', fin_alpha=0.9, pattern=_gr, noise=0.08)

# ----------------------------------------------------------------- trevally 28px
S['Trevally'] = lambda: build([
    "...............d............",
    "........ddd...ddd...........",
    "t.....###########...........",
    "tt...################.......",
    ".tt.#####################...",
    "..t#####################eh..",
    "..tt######################m.",
    "..t########pp############...",
    ".tt.####################....",
    "tt...################.......",
    "t.....##########............",
    "........aaa..aa.............",
], body='#7f909b', belly='#e2eaef', fin='#a7b8c3', tail='#c9a64a', fin_alpha=0.7)

# ----------------------------------------------------------------- sardine 10px / fusilier 13px
S['Sardine'] = lambda: build([
    "t...dd....",
    "tt######..",
    ".t######eh",
    "tt#######m",
    "t.......aa",
], body='#5b7c97', belly='#e7f0f6', fin='#a9bccb', fin_alpha=0.6, rays=False)
S['Fusilier'] = lambda: build([
    "....ddddd....",
    "t..#########.",
    "tt########eh.",
    ".t##########m",
    "tt#########..",
    "t....aaa.....",
], body='#3a7be0', belly='#e4ecff', tail='#ffcf1a', fin='#bcd0ff', fin_alpha=0.6, rays=False,
    pattern=lambda x, y, u, v: ramp('#ffcf1a') if y == 1 or (y == 2 and x < 6) else None)

# ----------------------------------------------------------------- barracuda 44px
def _ba(x, y, u, v):
    if y <= 2 and (x // 3) % 2 == 0 and 4 < x < 36: return ramp('#465460')
    if y >= 3 and hash2(x, y, 9) < 0.05 and x < 34: return BLACK
S['Barracuda'] = lambda: build([
    "ttt............ddd..............dd...............",
    ".ttt.....................................,.......".replace(',', '.'),
    "..ttt........##################################..",
    "...tt#############################eh#############",
    "....t##############pp############################",
    "...tt########################################mmm.",
    "..ttt........##################################..",
    ".ttt...........aa.......aaa......................",
    "ttt..............................................",
], body='#8a9aa6', belly='#e9eff3', fin='#7b8a96', fin_alpha=0.75, pattern=_ba)

# ----------------------------------------------------------------- reef shark 52px
S['Reef Shark'] = lambda: build([
    "tt..................................d.................",
    "ttt................................ddd................",
    ".ttt..............................dddd................",
    ".tttt............................ddddd................",
    "..tttt.................................................",
    "..ttttt..........###########################..........",
    "...ttttt################################################..".rstrip('.'),
    "....tttt#################################################",
    ".....ttt#####################################eh##########",
    "......tt#################################################m",
    ".....ttt################################################m",
    "....tttt######################aaaa#############ppp####...",
    "...tttt.......aa..............aaaaa...........aaaaa.......",
    "..ttt.........aaa..............aaaa..........aaaa........",
    ".tt...........................................aa.........",
], body='#8b969e', belly='#edf0f2', fin='#7c8790', tail='#7c8790', fin_alpha=0.95, rays=False,
    finpat=lambda c, x, y, e: BLACK if (c == 'd' and y <= 1) or (c == 't' and (y <= 1 or y >= 13)) or (c in 'ap' and e and y >= 13) else None)

# ----------------------------------------------------------------- lionfish 22px
def _lf(x, y, u, v):
    if (x + y // 2) % 3 != 0 and u < 0.92: return ramp('#9e3820')
S['Lionfish'] = lambda: build([
    "......d.d.d.d.d.......",
    ".....d.d.d.d.d.d......",
    "....dddddddddddd......",
    "t...############......",
    "tt.###############....",
    "tt###############eh#..",
    "tt####ppppp#########m.",
    "t..###pppppp######....",
    "......pppppppp........",
    "......aaaaaaaaaa......",
    ".......a.a.a.a........",
], body='#ecd9c6', fin='#dcae94', fin_alpha=0.6, pattern=_lf,
    finpat=lambda c, x, y, e: ramp('#9e3820')[3] if (x + y) % 2 == 0 else None)

# ----------------------------------------------------------------- dogface puffer 16px
S['Puffer'] = lambda: build([
    ".......ddd......",
    "t...########....",
    "tt.###########..",
    "tt###########eh#",
    "tt#############m",
    "tt##pp#########.",
    "t..###########..",
    "....#########...",
    ".......aa.......",
], body='#b5a383', belly='#f3eedc', fin='#c9b995', fin_alpha=0.65,
    pattern=lambda x, y, u, v: (hx('#4a3a26') if v < 0.55 and hash2(x, y, 5) < 0.2 else None))

NAMES = list(S)

def sheet(path, scale=8, cols=5, names=None, bg='#1e6f9c'):
    names = names or NAMES
    imgs = [S[n]() for n in names]
    cw = max(i.width for i in imgs) + 6; ch = max(i.height for i in imgs) + 6
    rows = (len(imgs) + cols - 1) // cols
    out = Image.new('RGBA', (cw * cols, ch * rows), bg)
    for k, im in enumerate(imgs):
        out.alpha_composite(im, ((k % cols) * cw + (cw - im.width) // 2, (k // cols) * ch + (ch - im.height) // 2))
    out.resize((out.width * scale, out.height * scale), Image.NEAREST).save(path)



# ----------------------------------------------------------------- polygon-built silhouettes for big animals
from PIL import ImageDraw
def shape_grid(w, h, body, fins):
    """body: list of (x, top, bottom) control points; fins: [(char, [(x, y), ...])]."""
    g = [['.'] * w for _ in range(h)]
    for ch, pts in fins:
        m = Image.new('L', (w, h)); ImageDraw.Draw(m).polygon(pts, fill=255)
        for y in range(h):
            for x in range(w):
                if m.getpixel((x, y)): g[y][x] = ch
    xs = [p[0] for p in body]
    for x in range(w):
        if x < xs[0] or x > xs[-1]: continue
        i = max(k for k in range(len(xs)) if xs[k] <= x)
        if i == len(xs) - 1: t0, b0 = body[i][1:]; t1, b1 = t0, b0; f = 0
        else:
            f = (x - xs[i]) / (xs[i + 1] - xs[i]); f = f * f * (3 - 2 * f)
            t0, b0 = body[i][1:]; t1, b1 = body[i + 1][1:]
        top = t0 + (t1 - t0) * f; bot = b0 + (b1 - b0) * f
        for y in range(h):
            if top <= y + 0.5 <= bot: g[y][x] = '#'
    return [''.join(r) for r in g]

def mark(rows, marks):
    g = [list(r) for r in rows]
    for (x, y), ch in marks.items(): g[y][x] = ch
    return [''.join(r) for r in g]

def _shark_rows():
    r = shape_grid(58, 17,
        body=[(12, 7.6, 10.6), (18, 6.4, 11.6), (28, 5.0, 12.6), (38, 4.6, 12.8), (47, 5.4, 12.0), (53, 6.8, 11.0), (57, 8.4, 10.0)],
        fins=[('t', [(17, 10), (12, 9), (1, 0), (5, 0), (11, 3), (16, 6)]), ('t', [(16, 10), (12, 11), (5, 16), (8, 16), (17, 11)]),
              ('d', [(30, 6), (34, 0), (36, 0), (39, 6)]), ('d', [(16, 8), (18, 5), (20, 7)]),
              ('a', [(41, 11), (36, 16), (38, 16), (45, 11)]), ('a', [(25, 11), (24, 14), (28, 12)]),
              ('a', [(15, 10), (14, 12), (17, 10)])])
    return mark(r, {(49, 8): 'e', (50, 8): 'h', (55, 10): 'm', (54, 10): 'm', (44, 9): 'g', (45, 10): 'g'})
S['Reef Shark'] = lambda: build(_shark_rows(), body='#8b969e', belly='#eef1f3', fin='#7c8790', tail='#768189',
    fin_alpha=1.0, rays=False,
    finpat=lambda c, x, y, e: BLACK if (c == 'd' and y <= 1) or (c == 't' and (y <= 1 or y >= 14)) or (c == 'a' and y >= 15) else None)

def _barra_rows():
    r = shape_grid(46, 11,
        body=[(6, 4.6, 6.4), (12, 3.6, 7.4), (30, 3.0, 7.8), (40, 3.4, 7.2), (45, 4.6, 6.4)],
        fins=[('t', [(9, 6), (5, 5), (0, 0), (3, 0), (9, 4)]), ('t', [(9, 5), (5, 6), (0, 11), (3, 11), (9, 7)]),
              ('d', [(28, 4), (30, 0), (33, 4)]), ('d', [(12, 4), (13, 1), (16, 4)]),
              ('a', [(12, 7), (12, 10), (15, 7)]), ('a', [(30, 7), (31, 9), (33, 7)])])
    return mark(r, {(40, 4): 'e', (41, 4): 'h', (44, 6): 'm', (43, 6): 'm'})
S['Barracuda'] = lambda: build(_barra_rows(), body='#8a9aa6', belly='#e9eff3', fin='#7b8a96', fin_alpha=0.85, pattern=_ba)

def _trev_rows():
    r = shape_grid(30, 15,
        body=[(6, 6.4, 8.6), (10, 5.0, 10.0), (18, 2.8, 12.0), (25, 3.4, 11.6), (29, 6.2, 9.4)],
        fins=[('t', [(9, 8), (5, 7), (0, 0), (3, 0), (10, 5)]), ('t', [(9, 7), (5, 8), (0, 15), (3, 15), (10, 10)]),
              ('d', [(18, 3), (21, 0), (22, 3)]), ('d', [(9, 6), (16, 2), (17, 3), (11, 6)]),
              ('a', [(9, 9), (15, 13), (16, 12), (12, 9)])])
    return mark(r, {(25, 6): 'e', (26, 6): 'h', (29, 8): 'm', (19, 8): 'p', (20, 8): 'p', (21, 9): 'p'})
S['Trevally'] = lambda: build(_trev_rows(), body='#7f909b', belly='#e2eaef', fin='#a7b8c3', tail='#c9a64a', fin_alpha=0.75)



# ----------------------------------------------------------------- detailed blacktip reef shark (100px)
def _shark2_rows():
    r = shape_grid(100, 40,
        body=[(20, 20.6, 23.4), (28, 18.6, 25.0), (40, 16.0, 27.2), (52, 14.2, 28.0), (64, 13.6, 27.8),
              (76, 14.4, 27.0), (86, 16.2, 25.6), (93, 18.4, 24.4), (97, 20.6, 23.2), (99, 21.8, 22.6)],
        fins=[('t', [(27, 20.5), (21, 17.5), (12, 9), (3, 1), (0, 0), (0, 4), (4, 9), (11, 16), (18, 22), (24, 23.5)]),
              ('t', [(24, 23), (18, 24), (10, 31), (8, 33), (12, 33), (19, 27), (25, 24.5)]),
              ('d', [(50, 15), (56, 6), (59, 2), (61, 2), (62, 5), (68, 14)]),
              ('d', [(27, 19.5), (30, 15.5), (32, 15.5), (33, 19)]),
              ('a', [(70, 27), (63, 33), (56, 38), (59, 39), (66, 35), (77, 27)]),
              ('a', [(41, 27), (37, 31), (40, 31.5), (45, 27.5)]),
              ('a', [(31, 25), (29, 28.5), (32, 28.5), (34, 25)])])
    marks = {(88, 19): 'e', (89, 19): 'h', (88, 20): 'e'}
    for gx in (74, 76, 78, 80, 82):
        for gy in range(20, 25): marks[(gx, gy)] = 'g'
    for mx, my in ((89, 24), (90, 24), (91, 24), (92, 24), (93, 23), (94, 23)): marks[(mx, my)] = 'm'
    return mark(r, marks)

def _shark2_pat(x, y, u, v):
    # faint lateral stripe (the pale "hip" flash of a blacktip)
    if 0.22 < u < 0.5 and 0.6 < v < 0.72 and v > 0.6 + (u - 0.22) * 0.3: return ramp('#cdd3d8')
S['Reef Shark'] = lambda: build(_shark2_rows(), body='#7f8b94', belly='#eef1f3', fin='#76828b', tail='#727e87',
    fin_alpha=1.0, rays=False, pattern=_shark2_pat, noise=0.04, belly_v=0.7,
    finpat=lambda c, x, y, e: BLACK if (c == 'd' and y <= 5) or (c == 't' and (y <= 3 or y >= 31)) or (c == 'a' and y >= 36) else None)


if __name__ == '__main__':
    sheet('fish_sheet.png', scale=6, cols=6)
    print('wrote fish_sheet.png')


# ----------------------------------------------------------------- blacktip reef shark v3: clean outlined pixel style
def toon_shark():
    rows = shape_grid(68, 30,
        body=[(14, 12.0, 14.8), (20, 10.2, 16.2), (30, 8.2, 17.8), (42, 7.4, 18.2), (52, 8.0, 17.6),
              (59, 9.6, 16.0), (63, 11.2, 14.8), (66, 12.4, 13.9)],
        fins=[('t', [(17, 12.4), (13, 10.8), (5, 3.5), (0, 0), (1, 2.5), (7, 8.5), (12, 13.3), (17, 14.3)]),   # upper lobe
              ('l', [(16, 13.4), (11, 14.2), (6, 19.5), (4, 23), (7, 23), (13, 17), (17, 14.6)]),            # lower lobe
              ('d', [(31, 9.2), (36, 3), (38.5, 0.4), (40, 1.2), (41, 4.5), (45, 9)]),                       # first dorsal
              ('d', [(19, 11.2), (21, 8.2), (22.4, 8.2), (23.5, 11)]),                                         # second dorsal
              ('p', [(45, 17), (41.5, 22.5), (39, 28.6), (41.5, 28.6), (47, 21.5), (52, 17)]),               # pectoral
              ('a', [(27, 16.6), (25, 19.6), (28, 19.6), (30.5, 16.9)]),                                       # pelvic
              ('a', [(19.5, 15.4), (18.5, 18.2), (21.5, 17.6), (22.5, 15.6)])])                                 # anal
    h, w = len(rows), len(rows[0])
    C = {'out': hx('#0c0e11'), 'D': hx('#4b565d'), 'M': hx('#76818a'), 'L': hx('#bcc6cc'), 'W': hx('#eef2f4'), 'B': hx('#16191c')}
    cols = {}
    for x in range(w):
        ys = [y for y in range(h) if rows[y][x] == '#']
        if ys: cols[x] = (min(ys), max(ys))
    a = np.zeros((h + 2, w + 2, 4))
    for y in range(h):
        for x in range(w):
            c = rows[y][x]
            if c == '.': continue
            if c == '#':
                t0, t1 = cols[x]; v = (y - t0 + 0.5) / (t1 - t0 + 1)
                col = C['D'] if v < 0.42 else C['M'] if v < 0.6 else C['L']
                if 0.6 <= v < 0.74 and 20 <= x <= 40 and v < 0.6 + (x - 20) * 0.01 + 0.04: col = C['W']   # pale flank flash
                if y == t0 and x > 16: col = C['D'] * 0.85
            else:
                col = C['D'] if c in 'tdl' else C['M']
                if c == 'p' and (x - 41) > (y - 17) * 0.2: col = C['D']            # leading edge darker
                if (c == 'd' and y <= 2) or (c == 'p' and y >= 26) or (c == 'l' and y >= 20) or (c == 't' and x <= 2): col = C['B']
                if c == 'd' and 19 <= x <= 23 and y <= 9: col = C['B'] * 1.6
            a[y + 1, x + 1] = list(col) + [255]
    # details: eye, gill slits, mouth line, nostril
    for (x, y), c in {(59, 12): 'B', (60, 12): 'B', (59, 13): 'D'}.items(): a[y + 1, x + 1, :3] = C[c]
    for gx in (49, 51, 53):
        for gy in range(11, 15): a[gy + 1, gx + 1, :3] = C['D'] * 0.8
    for mx in range(57, 63):
        if a[16, mx + 1, 3]: a[16, mx + 1, :3] = C['D'] * 0.7
    # crisp black outline around everything
    o = a.copy()
    for y in range(h + 2):
        for x in range(w + 2):
            if a[y, x, 3] == 0 and any(0 <= y + dy < h + 2 and 0 <= x + dx < w + 2 and a[y + dy, x + dx, 3] > 0
                                       for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))):
                o[y, x] = list(C['out']) + [255]
    return Image.fromarray(o.astype('uint8'), 'RGBA')

S['Reef Shark'] = toon_shark
