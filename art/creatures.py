"""Turtle, eagle ray and seahorse sprites."""
import math
import numpy as np
from PIL import Image
from fishgen2 import ramp, hx
nrs = np.random.RandomState(11)
def blank(w, h): return np.zeros((h, w, 4))
def to_img(a): return Image.fromarray(np.clip(a, 0, 255).astype('uint8'), 'RGBA')
def outline(a, f=0.42):
    h, w = a.shape[:2]; o = np.zeros((h + 2, w + 2, 4)); o[1:-1, 1:-1] = a; r = o.copy()
    for y in range(h + 2):
        for x in range(w + 2):
            if o[y, x, 3] == 0:
                nb = [o[y + dy, x + dx] for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))
                      if 0 <= y + dy < h + 2 and 0 <= x + dx < w + 2 and o[y + dy, x + dx, 3] > 0]
                if nb: r[y, x, :3] = np.mean([n[:3] for n in nb], 0) * f; r[y, x, 3] = 255
    return r

def eagle_ray():
    w, h = 40, 24; a = blank(w, h); cx, cy = 18, 10
    R = ramp('#3b4a5c'); belly = hx('#e9eef2')
    for y in range(h):
        for x in range(w):
            dx, dy = x - cx, y - cy + 0.012 * (x - cx) ** 2 - 1
            if abs(dx) / 17 + abs(dy) / 5.5 <= 1 and dx > -17:
                t = (dy + 5) / 10
                c = R[int(np.clip(round(1 + 3.5 * (1 - abs(dx) / 18) - t + nrs.rand() * .6), 0, 5))]
                if dy > 2.2: c = belly
                if dy <= 2 and (x * 7 + y * 11) % 13 == 0: c = hx('#f2f5f8')
                a[y, x] = list(c) + [255]
    for i in range(16):  # tail
        x, y = cx - 14 - i, cy + 1 + i // 6
        if 0 <= x < w: a[y, x] = list(hx('#2c3846')) + [255]
    for x, y in ((cx + 16, cy), (cx + 17, cy)): a[y, x] = list(R[2]) + [255]
    a[cy - 1, cx + 13] = [12, 14, 20, 255]
    return outline(a)

def turtle():
    w, h = 36, 20; a = blank(w, h)
    shell, skin = ramp('#6b7f3a'), ramp('#9a8f5a')
    def put(x, y, c):
        if 0 <= x < w and 0 <= y < h: a[y, x] = list(c) + [255]
    # rear flipper, front flipper (behind shell first)
    for i in range(7): put(7 - i // 2, 12 + i // 2, skin[2]); put(6 - i // 2, 12 + i // 2, skin[3])
    for i in range(12):
        for k in range(3): put(22 - i // 3 + k - 2, 12 + i // 2 + (k == 0), skin[3 if k else 2])
    for y in range(h):
        for x in range(w):
            dx, dy = (x - 16) / 12, (y - 9) / 6.5
            if dx * dx + dy * dy <= 1 and y <= 13:
                t = (y - 3) / 10
                c = shell[int(np.clip(round(4 - 3 * t + nrs.rand() * .5), 0, 5))]
                if ((x // 4 + (y // 3) % 2 * 2) % 2 == 0 and x % 4 == 0) or y % 3 == 0 and nrs.rand() < .5: c = shell[1]
                put(x, y, c)
            if y in (12, 13) and 6 <= x <= 26: put(x, y, hx('#d9cf9a'))
    for y in range(7, 13):  # head
        for x in range(27, 34):
            if ((x - 30) / 3.8) ** 2 + ((y - 10) / 2.6) ** 2 <= 1:
                put(x, y, skin[3 if (x + y) % 3 else 2])
    put(31, 9, (12, 14, 20)); put(32, 9, (240, 240, 230))
    return outline(a)

def seahorse(color='#ffb02e'):
    m = ["....oo..", "...oOOo.", "..oOOOOO", ".oOOo.o.", ".oOOo...", "..oOOo..", "..oOOOo.",
         "...oOOo.", "...oOOo.", "..oOOo..", ".oOOo...", ".oOo....", "..oOo.o.", "...ooo.."]
    R = ramp(color); a = blank(8, len(m))
    for y, row in enumerate(m):
        for x, ch in enumerate(row):
            if ch == 'O': a[y, x] = list(R[3 + (x + y) % 2]) + [255]
            elif ch == 'o': a[y, x] = list(R[2]) + [255]
    a[2, 4] = [12, 14, 20, 255]
    return outline(a)

def jelly():
    w, h = 13, 20; a = blank(w, h); R = ramp('#f2a7ff')
    for y in range(7):
        for x in range(w):
            if ((x - 6) / 6.3) ** 2 + ((y - 6.5) / 6.3) ** 2 <= 1:
                a[y, x] = list(R[4 if (x < 5 and y < 4) else 3]) + [200]
    for i, tx in enumerate(range(1, 12, 2)):
        for k in range(13):
            x = tx + int(round(math.sin(k / 2.2 + i) * 0.9))
            if 0 <= x < w: a[7 + k, x] = list(R[2 + k % 2]) + [170]
    return a

