"""Macquarium coral reef: deliberately drawn, shaded coral colonies over warm reef rock."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from fishgen2 import ramp, hx, hash2, vnoise, smooth

W, H = 420, 210
rs = random.Random(5)

def canvas(w, h): return np.zeros((h, w, 4))
def img(a):
    ys, xs = np.where(a[..., 3] > 0)
    if len(ys) == 0: return Image.new('RGBA', (1, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8'), 'RGBA')
def put(a, x, y, c, al=255):
    h, w = a.shape[:2]
    if 0 <= x < w and 0 <= y < h: a[int(y), int(x)] = list(np.clip(c, 0, 255)) + [al]
def shade(R, lum, j=0.0):
    return R[int(np.clip(round(lum * (len(R) - 1) + j), 0, len(R) - 1))]
def outline(a, R, f=0.75):
    h, w = a.shape[:2]; o = a.copy()
    for y in range(h):
        for x in range(w):
            if a[y, x, 3] == 0:
                if any(0 <= y + dy < h and 0 <= x + dx < w and a[y + dy, x + dx, 3] > 0 for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))):
                    o[y, x] = list(R[0] * f) + [255]
    return o

# ------------------------------------------------------------------ coral types
def brain(r, col):
    R = ramp(col, 7); w, h = 2 * r + 3, int(r * 1.25) + 3; a = canvas(w, h); cx, cy = r + 1, h - 2
    for y in range(h):
        for x in range(w):
            dx, dy = (x - cx) / (r + 0.5), (y - cy) / (r * 1.15)
            d = dx * dx + dy * dy
            if d <= 1 and y <= cy:
                nz = math.sqrt(max(0, 1 - d)); lum = 0.25 + 0.55 * nz - 0.25 * dx - 0.15 * dy * -1
                groove = math.sin(x * 1.25 + math.sin(y * 0.9 + x * 0.3) * 2.2 + y * 0.35)
                if groove > 0.55: lum -= 0.3
                elif groove < -0.7: lum += 0.12
                put(a, x, y, shade(R, lum, (hash2(x, y, 7) - .5) * .4))
    return outline(a, R)

def table(w, col, stem='#8d7a62'):
    R = ramp(col, 7); S = ramp(stem); h = 9 + w // 6; a = canvas(w + 2, h)
    st = w // 2
    for y in range(4, h):
        for x in range(st - 1, st + 2): put(a, x, y, shade(S, 0.35 + (x - st) * -0.15))
    for x in range(1, w + 1):
        e = 1 if hash2(x, 0, 3) < 0.3 else 0
        put(a, x, 1 - e if e else 1, shade(R, 0.95)); put(a, x, 2, shade(R, 0.75 + (hash2(x, 2, 1) - .5) * .3))
        put(a, x, 3, shade(R, 0.45)); put(a, x, 4, shade(R, 0.15 if 2 < x < w - 1 else 0.3))
        if x % 3 == 0: put(a, x, 2, shade(R, 1.0))
        if x % 4 == 2: put(a, x, 3, shade(R, 0.7))                     # polyp texture on the rim
        if x % 5 == 1 and 2 < x < w - 1: put(a, x, 1, shade(R, 0.6))
    for y in range(5, h, 2): put(a, st - 1, y, shade(S, 0.6))           # stem texture
    return outline(a, R)

def staghorn(col, size=1.0):
    R = ramp(col, 7); w, h = int(30 * size), int(24 * size); a = canvas(w, h)
    def br(x, y, ang, ln, d):
        for i in range(int(ln)):
            xx, yy = x + math.cos(ang) * i, y - math.sin(ang) * i
            t = i / ln
            put(a, xx, yy, shade(R, 0.35 + 0.2 * t)); put(a, xx + 1, yy, shade(R, 0.15 + 0.2 * t))
            put(a, xx - 1, yy, shade(R, 0.6 + 0.2 * t))
        ex, ey = x + math.cos(ang) * ln, y - math.sin(ang) * ln
        if d > 0:
            for da in (0.45, -0.45): br(ex, ey, ang + da + rs.uniform(-.2, .2), ln * 0.75, d - 1)
            if rs.random() < 0.5: br(ex, ey, ang + rs.uniform(-.1, .1), ln * 0.6, d - 1)
        else:
            put(a, ex, ey, ramp('#f0e0ff')[5]); put(a, ex - 0.5, ey + 1, shade(R, 0.95))
    for k in range(3):
        br(w / 2 + (k - 1) * 3 * size, h - 1, math.pi / 2 + (k - 1) * 0.35, 6 * size, 3)
    return outline(a, R)

def fan(r, col):
    R = ramp(col, 7); w, h = 2 * r + 3, r + 6; a = canvas(w, h); cx, cy = r + 1, r + 2
    for y in range(h):
        for x in range(w):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy * 1.05)
            if d <= r and dy <= 0:
                ang = math.atan2(-dy, dx)
                rib = abs(math.sin(ang * 8)) < 0.32 or abs(math.sin(d * 1.0)) < 0.3
                edge = d > r - 1.2
                if rib or edge:
                    put(a, x, y, shade(R, 0.45 + 0.4 * (1 - d / r) * 0 + (0.35 if edge else 0.2) - 0.15 * (dx / r)))
    for y in range(cy, h): put(a, cx, y, shade(R, 0.2)); put(a, cx + 1, y, shade(R, 0.1))
    return outline(a, R, 0.6)

def plates(col, n=4):
    R = ramp(col, 7); w, h = 28, 16; a = canvas(w, h)
    for k in range(n):
        cx, cy, rx = 6 + k * 5 + rs.randint(-1, 1), 12 - k * 2 - rs.randint(0, 2), rs.randint(6, 9)
        for x in range(cx - rx, cx + rx + 1):
            t = (x - cx) / rx; yy = cy - int(round((1 - t * t) * 3))
            for th in range(3):
                put(a, x, yy + th, shade(R, (0.95, 0.6, 0.25)[th] - 0.1 * t + (hash2(x, k, 4) - .5) * .2))
    return outline(a, R)

def tubes(col, n=3):
    R = ramp(col, 7); w, h = 4 * n + 6, 20; a = canvas(w, h)
    for k in range(n):
        x0 = 2 + k * 4; ht = rs.randint(9, 18); top = h - ht
        for y in range(top, h):
            for x in range(x0, x0 + 3):
                put(a, x, y, shade(R, (0.75, 0.5, 0.25)[x - x0] + (hash2(x, y, 2) - .5) * .25))
        put(a, x0 + 1, top, R[0] * 0.5); put(a, x0, top, shade(R, 0.9)); put(a, x0 + 2, top, shade(R, 0.6))
        put(a, x0 + 1, top + 1, R[0] * 0.7)
    return outline(a, R)

def barrel(col):
    R = ramp(col, 7); w, h = 18, 18; a = canvas(w, h)
    for y in range(2, h):
        t = (y - 2) / (h - 3); half = 6 + 2.5 * math.sin(t * math.pi * 0.9)
        for x in range(w):
            dx = x - w / 2 + 0.5
            if abs(dx) <= half:
                lum = 0.55 - 0.35 * dx / half + (0.12 if y % 3 == 0 else 0) - 0.2 * t
                put(a, x, y, shade(R, lum))
    for x in range(4, 14): put(a, x, 2, R[0] * 0.6); put(a, x, 3, R[1])
    return outline(a, R)

def softcoral(col, stalk='#f2e6ea'):
    R = ramp(col, 7); S = ramp(stalk); w, h = 20, 20; a = canvas(w, h)
    def lobe(x, y, r):
        for yy in range(-r, r + 1):
            for xx in range(-r, r + 1):
                if xx * xx + yy * yy <= r * r:
                    put(a, x + xx, y + yy, shade(R, 0.55 - 0.12 * xx / r - 0.2 * yy / r + (hash2(x + xx, y + yy, 6) - .5) * .5))
    for i in range(10):
        put(a, 10 + int(math.sin(i / 3)), h - 1 - i, shade(S, 0.6)); put(a, 11 + int(math.sin(i / 3)), h - 1 - i, shade(S, 0.35))
    for _ in range(rs.randint(6, 9)):
        lobe(10 + rs.randint(-6, 6), 4 + rs.randint(0, 9), rs.randint(2, 3))
    return outline(a, R)

def anemone(col, tip='#ffffff', sway=0.0):
    R = ramp(col, 7); T = ramp(tip); w, h = 24, 14; a = canvas(w, h)
    for x in range(5, 17):
        for y in range(10, 14): put(a, x, y, shade(R, 0.3 + 0.1 * (y == 10)))
    for i in range(16):
        bx = 3 + i * 1.05; ln = 6 + (hash2(i, 1, 2) * 4)
        for k in range(int(ln)):
            x = 1 + bx + math.sin(k / 2 + i) * 1.1 + (bx - 11) * 0.05 * k + sway * 1.6 * (k / ln) ** 1.4; y = 10 - k
            put(a, x, y, shade(R, 0.5 + 0.35 * k / ln))
        put(a, 1 + bx + math.sin(ln / 2 + i) * 1.1 + (bx - 11) * 0.05 * ln + sway * 1.6, 10 - ln, shade(T, 0.9))
    return a

def mushrooms(col):
    R = ramp(col, 7); w, h = 18, 8; a = canvas(w, h)
    for cx in (3, 8, 13):
        r = rs.randint(2, 3)
        for y in range(-r, 1):
            for x in range(-r - 1, r + 2):
                if (x / (r + 1)) ** 2 + (y / r) ** 2 <= 1:
                    put(a, cx + x, h - 2 + y, shade(R, 0.6 - 0.1 * x / r + 0.2 * (y == -r)))
        put(a, cx, h - 2 - r + 1, R[0])
    return outline(a, R)

def seagrass(n=7, col='#3aa66a', sway=0.0, seed=1):
    R = ramp(col); w, h = 22, 30; a = canvas(w, h); lr = random.Random(seed)
    for i in range(n):
        x0 = 5 + i * 1.8; ln = lr.randint(12, 28); ph = lr.random() * 6
        for k in range(ln):
            put(a, x0 + math.sin(k / 6 + ph) * 2 + sway * 3 * (k / 28) ** 1.6, h - 1 - k, shade(R, 0.35 + 0.4 * k / ln))
    return a

# ------------------------------------------------------------------ rock base

# ------------------------------------------------------------------ small reef life (fills the rock)
fr = random.Random(31)          # separate stream so the big colonies keep their layout

def zoanthids(col):
    R = ramp(col, 7); C = ramp(fr.choice(['#7fff9a', '#ffe14a', '#ff7ad9', '#7fe8ff'])); a = canvas(11, 6)
    for _ in range(fr.randint(5, 8)):
        x, y = fr.randint(1, 8), fr.randint(1, 3)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)): put(a, x + dx, y + dy, shade(R, 0.55 + 0.2 * (dy == 0)))
        put(a, x, y, shade(C, 0.9))
    return a

def xmas_worm():
    cols = fr.choice([('#ff3b3b', '#ffd0d0'), ('#3b7bff', '#cfe0ff'), ('#ffcf1a', '#fff3b0'), ('#f2f2f2', '#9ad0ff')])
    a = canvas(7, 6)
    for k, x0 in enumerate((0, 4)):
        for y in range(5):
            w = 3 - y // 2
            for x in range(w): put(a, x0 + x + (2 - w) // 2 + y // 3, y, hx(cols[(y + x) % 2]))
    return a

def feather_duster():
    stalk = ramp('#b49a74'); crown = [hx(fr.choice(['#b06ad8', '#e05a8a', '#e8c05a'])), hx('#f6f0ff')]
    a = canvas(9, 10); h = fr.randint(4, 6)
    for y in range(10 - h, 10): put(a, 4, y, shade(stalk, 0.5))
    top = 10 - h
    for i, (dx, dy) in enumerate(((-4, -1), (-3, -2), (-2, -3), (-1, -3), (0, -4), (1, -3), (2, -3), (3, -2), (4, -1))):
        for k in range(1, 4):
            put(a, 4 + dx * k / 4, top + dy * k / 4, crown[(i + k) % 2])
    return a

def urchin():
    a = canvas(9, 7); body = hx('#1a1424'); hi = hx('#4a3a6a')
    for dy in range(-1, 2):
        for dx in range(-1, 2): put(a, 4 + dx, 4 + dy, body)
    put(a, 3, 3, hi)
    for ang in range(0, 360, 30):
        r = math.radians(ang); ln = 3 if ang % 60 == 0 else 2
        if math.sin(r) > 0.5: continue
        for k in range(2, ln + 2): put(a, 4 + math.cos(r) * k, 4 - math.sin(r) * k * 0.9, body if k < ln + 1 else hi)
    return a

def clam():
    lip = ramp(fr.choice(['#2fd0ff', '#4a6aff', '#2fe0a0', '#b04aff'])); shell = ramp('#d8d0b8')
    a = canvas(10, 5)
    for x in range(10):
        for y in range(2, 5): put(a, x, y, shade(shell, 0.4 + 0.25 * (y == 2) + (0.15 if x % 2 else 0)))
        wave = 1 if (x // 2) % 2 else 0
        put(a, x, 1 + wave, shade(lip, 0.7 + 0.25 * (x % 3 == 0))); put(a, x, 2 + wave, shade(lip, 0.45))
    return a

def starfish(col=None):
    R = ramp(col or fr.choice(['#ff7a3a', '#3a7aff', '#e04a6a', '#ffb02e'])); a = canvas(9, 9)
    for i in range(5):
        ang = i * 2 * math.pi / 5 - math.pi / 2 + 0.2
        for k in range(5): put(a, 4 + math.cos(ang) * k, 4 + math.sin(ang) * k, shade(R, 0.75 - k * 0.08 + (0.15 if k % 2 else 0)))
    put(a, 4, 4, shade(R, 1.0))
    return a

def sea_whip(col=None):
    R = ramp(col or fr.choice(['#ffcf1a', '#ff6b3a', '#d84a8a'])); a = canvas(11, 22)
    for st in range(3):
        x0 = 3 + st * 2; ln = fr.randint(12, 21); ph = fr.random() * 3
        for k in range(ln): put(a, x0 + math.sin(k / 5 + ph) * 1.6 + (st - 1) * k * 0.12, 21 - k, shade(R, 0.4 + 0.45 * k / ln))
    return a

def pillar(col='#d8c8a0'):
    R = ramp(col, 7); a = canvas(14, 20)
    for c in range(fr.randint(2, 3)):
        x0 = 1 + c * 4; ht = fr.randint(10, 19)
        for y in range(20 - ht, 20):
            for x in range(x0, x0 + 3):
                put(a, x, y, shade(R, (0.8, 0.55, 0.3)[x - x0] + (hash2(x, y, 4) - .5) * .35))
            if hash2(x0, y, 8) < 0.5: put(a, x0 - 1, y, shade(R, 0.95))          # fuzzy polyps
            if hash2(x0 + 3, y, 9) < 0.4: put(a, x0 + 3, y, shade(R, 0.45))
        put(a, x0 + 1, 20 - ht - 1, shade(R, 1.0))
    return outline(a, R, 0.7)

def elkhorn(col='#d0a060'):
    R = ramp(col, 7); a = canvas(26, 14)
    def br(x, y, ang, ln, w, d):
        for i in range(int(ln)):
            xx, yy = x + math.cos(ang) * i, y - math.sin(ang) * i
            for k in range(w): put(a, xx, yy + k, shade(R, (0.85 if k == 0 else 0.5 - 0.1 * k)))
        if d: br(x + math.cos(ang) * ln, y - math.sin(ang) * ln, ang + fr.uniform(-0.6, 0.6), ln * 0.7, max(1, w - 1), d - 1)
        else: put(a, x + math.cos(ang) * ln, y - math.sin(ang) * ln, shade(R, 1.0))
    for ang in (2.5, 1.9, 1.2, 0.6): br(13, 12, ang, fr.randint(4, 6), 3, 2)
    return outline(a, R, 0.7)

FILL = [zoanthids, zoanthids, xmas_worm, xmas_worm, feather_duster, urchin, clam, starfish, sea_whip]

def build_reef():
    out = Image.new('RGBA', (W, H))
    nrs = np.random.RandomState(4)
    yy, xx = np.mgrid[0:H, 0:W]
    field = np.full((H, W), -9.0)
    mounds = [(70, 205, 75, 42), (200, 210, 95, 80), (215, 140, 40, 30), (330, 205, 80, 55), (400, 210, 40, 30), (150, 175, 40, 30)]
    for cx, cy, rx, ry in mounds:
        field = np.maximum(field, 1 - ((xx - cx) / rx) ** 2 - ((yy - cy) / ry) ** 2)
    noise = np.array([[vnoise(x, y, 9, 3) * 0.6 + vnoise(x, y, 4, 8) * 0.4 for x in range(W)] for y in range(H)])
    mask = (field + (noise - 0.5) * 0.5) > 0.05
    RK = ramp('#8a6a5e', 7)
    rock = np.zeros((H, W, 4))
    for y in range(H):
        for x in range(W):
            if not mask[y, x]: continue
            top_edge = y > 0 and not mask[y - 1, x]
            lum = 0.3 + 0.35 * noise[y, x] + (0.35 if top_edge else 0) - 0.25 * (y / H)
            crev = abs(vnoise(x, y, 6, 51) - 0.5) < 0.035
            if crev: lum -= 0.35
            elif abs(vnoise(x, y - 1, 6, 51) - 0.5) < 0.035: lum += 0.15     # lit lip above a crevice
            c = shade(RK, lum, (hash2(x, y, 1) - .5) * .5)
            if vnoise(x, y, 5, 22) > 0.62 and not crev: c = shade(ramp('#b0607e'), lum)   # coralline algae
            elif vnoise(x, y, 4, 61) > 0.7 and not crev: c = shade(ramp('#6f8a4a'), lum)  # turf algae
            rock[y, x] = list(c) + [255]
    out.alpha_composite(Image.fromarray(rock.astype('uint8'), 'RGBA'))

    # sand
    sand = np.zeros((H, W, 4)); SR = ramp('#e3c48e', 7)
    for x in range(W):
        top = 197 + int(math.sin(x / 23) * 2 + math.sin(x / 7))
        for y in range(top, H):
            sand[y, x] = list(shade(SR, 0.75 - (y - top) * 0.04 + (hash2(x, y, 9) - .5) * .5 + (0.2 if y == top else 0))) + [255]
    out.alpha_composite(Image.fromarray(sand.astype('uint8'), 'RGBA'))

    # carpet the rock with small life before the big colonies go on
    fill_pts = [(x, y) for y in range(60, 197, 2) for x in range(2, W - 2, 2) if mask[y, x]]
    fr.shuffle(fill_pts); taken_f = []
    zo_cols = ['#8a5a9a', '#4a8a6a', '#a86a4a']
    for (x, y) in fill_pts:
        if any(abs(x - a) < 11 and abs(y - b) < 7 for a, b in taken_f): continue
        # patches: neighbouring spots share a type, like real reef carpets
        region = vnoise(x, y, 26, 77)
        if region < 0.32: continue                              # leave some bare, textured rock
        kinds = [zoanthids, zoanthids, zoanthids, feather_duster, clam, urchin, sea_whip, xmas_worm]
        f = kinds[int(vnoise(x, y, 18, 78) * 999) % len(kinds)]
        taken_f.append((x, y))
        im = img(f(zo_cols[int(region * 10) % 3]) if f is zoanthids else f())
        out.alpha_composite(im, (x - im.width // 2, y - im.height + 2))

    # place colonies on the rock surface, back to front
    surf = []
    for x in range(2, W - 2):
        col = np.where(mask[:, x])[0]
        if len(col): surf.append((x, col[0]))
    placements = []
    palette_hard = ['#c9a65a', '#9bbf6a', '#d98fb2', '#7fb0e0', '#e0a070', '#b8d470', '#e6c25a']
    palette_soft = ['#ff7aa8', '#c77dff', '#ff9a5a', '#5ee6c8', '#ffd166', '#ff6b6b', '#7aa8ff']
    # tops: tables, staghorn, fans, soft corals
    x = 4
    while x < W - 4:
        sx, sy = min(surf, key=lambda p: abs(p[0] - x))
        k = rs.random()
        if k < 0.2: sp = table(rs.randint(14, 24), rs.choice(palette_hard)) if fr.random() < 0.75 else elkhorn()
        elif k < 0.5: sp = staghorn(rs.choice(['#d98fb2', '#8fb8e0', '#e0b070', '#b48be0']), rs.uniform(0.8, 1.15))
        elif k < 0.66: sp = fan(rs.randint(8, 13), rs.choice(['#b0306a', '#9a3cc8', '#e05a3a', '#d0408a']))
        elif k < 0.76: sp = softcoral(rs.choice(palette_soft))
        elif k < 0.9: sp = img(brain(rs.randint(5, 8), rs.choice(['#c9a65a', '#8fbf6a', '#d6a0a0']))) if False else brain(rs.randint(5, 8), rs.choice(['#c9a65a', '#8fbf6a', '#d6a0a0']))
        else: sp = tubes(rs.choice(['#e07a2a', '#a04ad0', '#2a9ad0']))
        im = sp if isinstance(sp, Image.Image) else img(sp)
        placements.append((sy, sx - im.width // 2, sy - im.height + 3, im))
        x += rs.randint(9, 17)
    # faces: brain, plates, sponges, mushrooms, anemones lower down
    pts = [(x, y) for y in range(70, 196, 3) for x in range(3, W - 3, 3) if mask[y, x] and mask[max(0, y - 6), x]]
    rs.shuffle(pts)
    taken = []
    for (x, y) in pts:
        if any(abs(x - a) < 13 and abs(y - b) < 9 for a, b in taken): continue
        taken.append((x, y))
        k = rs.random()
        if y > 175 and k < 0.3: sp = anemone(rs.choice(['#ff9fc0', '#ffcf9a', '#9ad0ff']), '#ffffff')
        elif k < 0.3: sp = brain(rs.randint(4, 8), rs.choice(['#c9a65a', '#8fbf6a', '#d6a0a0', '#b0c46a']))
        elif k < 0.5: sp = plates(rs.choice(['#8fbf6a', '#d9c06a', '#c98fb2']))
        elif k < 0.56: sp = barrel(rs.choice(['#c46a4a', '#a8763a', '#8a5ac0'])) if fr.random() < 0.35 else plates(rs.choice(['#c9a65a', '#8fbf6a']))
        elif k < 0.64: sp = staghorn(rs.choice(['#d98fb2', '#8fb8e0', '#e0b070']), 0.8)
        elif k < 0.74: sp = tubes(rs.choice(['#e07a2a', '#a04ad0', '#2a9ad0', '#e0c03a']), rs.randint(2, 4))
        elif k < 0.86: sp = mushrooms(rs.choice(['#5ee6c8', '#ff7aa8', '#c77dff'])) if fr.random() < 0.6 else pillar()
        else: sp = softcoral(rs.choice(palette_soft))
        im = sp if isinstance(sp, Image.Image) else img(sp)
        placements.append((y, x - im.width // 2, y - im.height + 3, im))
    for _, x, y, im in sorted(placements, key=lambda p: p[0]):
        # soft contact shadow so each colony sits on the reef instead of floating on it
        a = np.array(im).astype(float); sh = np.zeros_like(a); sh[..., 3] = a[..., 3] * 0.32
        out.alpha_composite(Image.fromarray(sh.astype('uint8'), 'RGBA'), (int(x) + 1, int(y) + 2))
        out.alpha_composite(im, (int(x), int(y)))
    # a few starfish and urchins on top of everything, on the sand edge
    for x in range(8, W - 8, 37):
        im = img(fr.choice([starfish, urchin, clam])()); out.alpha_composite(im, (x + fr.randint(-6, 6), 196 - im.height + fr.randint(1, 3)))
    return out

DECOR = [('Seagrass', x, 170, s) for s, x in enumerate(list(range(0, 30, 9)) + list(range(370, 416, 9)))] + \
        [('Anemone', 119, 188, 0), ('Anemone', 299, 188, 1)]

def decor_frames(name, seed):
    """Four sway frames for a swaying plant/animal."""
    out = []
    for sw in (0.0, 0.7, 1.0, 0.7, 0.0, -0.7, -1.0, -0.7):
        if name == 'Seagrass': out.append(img(seagrass(sway=sw, seed=seed + 3)))
        else: out.append(img(anemone(('#ff9fc0', '#ffb07a')[seed % 2], '#ffffff', sway=sw)))
    return out

def caustics(w=128, h=64, cells=(8, 4), seed=9):
    """Tileable rippling light pattern (bright cell edges)."""
    r = random.Random(seed); cw, ch = w / cells[0], h / cells[1]
    pts = [((i + r.random()) * cw, (j + r.random()) * ch) for i in range(cells[0]) for j in range(cells[1])]
    a = np.zeros((h, w, 4))
    for y in range(h):
        for x in range(w):
            ds = sorted(min((px - x + ox) ** 2 + (py - y + oy) ** 2 for ox in (-w, 0, w) for oy in (-h, 0, h)) ** 0.5 for px, py in pts)
            edge = ds[1] - ds[0]
            v = max(0.0, 1 - edge / 2.2)
            a[y, x] = [200, 240, 255, 255 * v ** 1.5]
    return Image.fromarray(a.astype('uint8'), 'RGBA')

def build_water():
    a = np.zeros((H, W, 4)); a[..., 3] = 255
    top, bot = hx('#2c9fd6'), hx('#04203a')
    for y in range(H):
        t = (y / H) ** 0.9; a[y, :, :3] = top * (1 - t) + bot * t
    # distant reef silhouettes for depth
    for x in range(W):
        h1 = 150 + 18 * vnoise(x, 0, 30, 2) + 8 * vnoise(x, 0, 8, 5)
        for y in range(int(h1), H):
            a[y, x, :3] = a[y, x, :3] * 0.82 + hx('#1d5f86') * 0.18
    im = Image.fromarray(a.clip(0, 255).astype('uint8'), 'RGBA')
    br = random.Random(77)
    global rs
    keep = rs; rs = br                       # don't disturb the main reef's random stream
    far = Image.new('RGBA', (W, H))
    x = -6
    while x < W:
        k = br.random()
        if k < 0.3: sp = staghorn('#8fb8e0', br.uniform(0.7, 1.0))
        elif k < 0.55: sp = fan(br.randint(7, 11), '#9a7ac8')
        elif k < 0.75: sp = table(br.randint(12, 20), '#a0b8a0')
        else: sp = brain(br.randint(4, 7), '#a0a080')
        c = sp if isinstance(sp, Image.Image) else img(sp)
        y0 = int(158 + 14 * vnoise(x, 0, 30, 2)) - c.height + 4
        far.alpha_composite(c, (int(x), y0))
        x += br.randint(10, 18)
    rs = keep
    fa = np.array(far).astype(float)
    for y in range(H):
        wc = top * (1 - (y / H) ** 0.9) + bot * (y / H) ** 0.9
        fa[y, :, :3] = fa[y, :, :3] * 0.28 + wc * 0.72      # heavy water haze = far away
    im.alpha_composite(Image.fromarray(fa.clip(0, 255).astype('uint8'), 'RGBA'))
    a = np.array(im).astype(float)
    # god rays
    for x0 in range(0, W, 60):
        for y in range(0, 160):
            for dx in range(16):
                x = x0 + dx + y // 3
                if 0 <= x < W and hash2(x, y, 3) < 0.35 * (1 - y / 160): a[y, x, :3] = a[y, x, :3] * 0.9 + 25.5
    return Image.fromarray(a.clip(0, 255).astype('uint8'), 'RGBA')

if __name__ == '__main__':
    reef = build_reef(); water = build_water()
    import os; OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'tank') + '/'
    water.save(OUT + 'water.png'); reef.save(OUT + 'reef.png')
    caustics().save(OUT + 'caustics.png')
    print('ok')
