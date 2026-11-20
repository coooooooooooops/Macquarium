"""Macquarium fish renderer v2: small, realistic reef fish.

Faces right. Body shaded with countershading (dark back, pale belly), quantised
to a hue-shifted ramp. Fins are translucent with visible rays. Outline is
selective (dark along the back, softer along the belly, none on fin tips).
"""
import colorsys, math
import numpy as np
from PIL import Image


def hx(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)

def _toward(h, target, amt):
    d = ((target - h + 0.5) % 1) - 0.5
    return h + max(-abs(amt), min(abs(amt), d))

def ramp(base, n=7, lo=0.30, hi=1.30):
    """Dark->light ramp; shadows lean blue, highlights lean warm."""
    r, g, b = hx(base) / 255
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    out = []
    for i in range(n):
        t = i / (n - 1)
        if t < 0.5:
            k = (0.5 - t) * 2
            hh = _toward(h, 0.64, 0.06 * k); vv = v * (lo + (1 - lo) * (1 - k)); ss = min(1, s * (1 + 0.15 * k))
        else:
            k = (t - 0.5) * 2
            hh = _toward(h, 0.13, 0.04 * k); vv = min(1, v * (1 + (hi - 1) * k)); ss = s * (1 - 0.35 * k)
        out.append(np.array(colorsys.hsv_to_rgb(hh % 1, np.clip(ss, 0, 1), np.clip(vv, 0, 1))) * 255)
    return out

def smooth(a, b, x):
    if b == a: return 0.0
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def hash2(x, y, s=0):
    n = (x * 374761393 + y * 668265263 + s * 1442695041) & 0xffffffff
    n = (n ^ (n >> 13)) * 1274126177 & 0xffffffff
    return ((n ^ (n >> 16)) & 0xffff) / 65535.0

def vnoise(x, y, sc, s=0):
    fx, fy = x / sc, y / sc; x0, y0 = int(math.floor(fx)), int(math.floor(fy)); tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = hash2(x0, y0, s) * (1 - tx) + hash2(x0 + 1, y0, s) * tx
    b = hash2(x0, y0 + 1, s) * (1 - tx) + hash2(x0 + 1, y0 + 1, s) * tx
    return a * (1 - ty) + b * ty


class Fish:
    D = dict(L=20, H=7.0, peak=0.6, full=0.7, mf=2.2, mr=1.6, snout_len=0.0, snout_h=0.2, ped=0.22, nose=0.0, belly=1.1, snout=0.0,
             tail='fork', tail_len=0.2, tail_h=1.0, notch=0.6,
             dorsal=(0.25, 0.75, 0.35, 'round', 0.6), dorsal2=None, anal=(0.15, 0.4, 0.3, 'round', 0.6),
             pelvic=(0.62, 0.35), pectoral=0.32, filament=None,
             body='#888888', belly_c=None, fin=None, fin_alpha=0.62, fin_rays=True,
             pattern=None, finpat=None, eye=0.86, eye_v=0.40, eye_size=1, eye_ring=None,
             gill=0.76, lateral=False, noise=0.05, seed=1)

    def __init__(self, **k):
        self.__dict__.update(self.D); self.__dict__.update(k)

    def scaled(self, s):
        f = Fish(**{k: getattr(self, k) for k in self.D}); f.L = max(6, int(round(self.L * s))); f.H = max(2.5, self.H * s)
        f.eye_size = 1 if f.L < 26 else self.eye_size; return f

    # ------------------------------------------------------------------
    def render(self):
        L, H = self.L, self.H
        tl = self.tail_len
        fin_room = max([0] + [f[2] for f in (self.dorsal, self.dorsal2) if f]) * H + (self.filament[1] if self.filament else 0)
        bot_room = max([0] + [f[2] for f in (self.anal,) if f] + ([self.pelvic[1]] if self.pelvic else [])) * H
        tail_room = max(0, H * self.tail_h * (1.0 if self.tail != 'shark' else 1.3) - H) / 2 + 1
        pt = int(math.ceil(max(fin_room, tail_room))) + 2
        pb = int(math.ceil(max(bot_room, tail_room))) + 2
        Wc = L + 4; Hc = int(math.ceil(H * (1 + self.belly) / 2)) + pt + pb + 2
        cy = pt + H / 2 + 0.5
        kind = np.zeros((Hc, Wc), int)     # 1 body, 2 fin, 3 tail
        U = np.zeros((Hc, Wc)); V = np.zeros((Hc, Wc)); E = np.zeros((Hc, Wc))
        top, bot = {}, {}
        p = self.peak; a_ = self.full; b_ = a_ * (1 - p) / p
        for xi in range(Wc - 2):
            t = (xi + 0.5) / L
            if t > 1.0: break
            x = xi + 1
            if t >= tl:
                u = (t - tl) / (1 - tl)
                ub = u / (1 - self.snout_len) if self.snout_len else u
                if ub >= 1: f = 0.0
                elif ub >= p:
                    w = (ub - p) / (1 - p); f = (1 - w ** self.mf) ** (1 / self.mf)
                else:
                    w = (p - ub) / p; f = self.ped + (1 - self.ped) * (1 - w ** self.mr) ** (1 / self.mr)
                if self.snout_len and u > 1 - self.snout_len - 0.12: f = max(f, self.snout_h)
                if f <= 0: continue
                tp = cy - H / 2 * f + (self.snout * H * 0.12 * smooth(1 - self.snout_len, 1, u))
                bt = cy + H / 2 * f * self.belly + (self.snout * H * 0.12 * smooth(1 - self.snout_len, 1, u))
                top[x], bot[x] = tp, bt
                for y in range(Hc):
                    yc = y + 0.5
                    if tp <= yc <= bt:
                        kind[y, x] = 1; U[y, x] = u; V[y, x] = (yc - tp) / max(1e-6, bt - tp)
            else:
                s = 1 - t / tl                     # 1 at tail tip
                half0 = self.ped * H / 2 + 0.4
                th = H * self.tail_h / 2
                for y in range(Hc):
                    dy = y + 0.5 - cy; ad = abs(dy)
                    if self.tail == 'shark':
                        upper = -(half0 + (th * 1.35) * s ** 0.9); lower = half0 + th * 0.55 * s ** 1.2
                        ins = upper <= dy <= lower and not (s > 0.5 and -th * 0.2 * s < dy < th * 0.3 * s)
                    else:
                        half = half0 + (th - half0) * s ** 0.85
                        ins = ad <= half
                        if self.tail == 'fork': ins = ins and not (s > 0.3 and ad < half * self.notch * (s - 0.3) / 0.7)
                        elif self.tail == 'lunate': ins = ins and not (s > 0.55 and ad < half * 0.75 * ((s - 0.55) / 0.45) ** 0.7)
                        elif self.tail == 'round': ins = ad <= half * math.sqrt(max(0, 1 - (max(0, s - 0.55) / 0.45) ** 2) * 0.85 + 0.15)
                        elif self.tail == 'truncate': ins = ad <= half
                    if ins:
                        kind[y, x] = 3; U[y, x] = s; V[y, x] = (dy + th) / (2 * th)
        xs = sorted(top)

        def add_fin(spec, side):
            u0, u1, hgt, shape, sweep = spec
            hpx = hgt * H
            for x in xs:
                u = ((x - 0.5) / L - tl) / (1 - tl)
                if not (u0 <= u <= u1): continue
                k = (u - u0) / (u1 - u0)
                if shape == 'round': h = hpx * math.sin(math.pi * k) ** 0.55
                elif shape == 'tri': h = hpx * min(1, k * 3) * (1 - k) ** 0.8
                elif shape == 'spike': h = hpx * max(0, 1 - abs(k - 0.3) / 0.7) ** 1.3 * min(1, k * 5)
                elif shape == 'sail': h = hpx * min(1, k * 1.6) * (1 - k) ** 0.2
                elif shape == 'long': h = hpx * (0.55 + 0.45 * math.sin(math.pi * k)) * min(1, k * 4) * min(1, (1 - k) * 6)
                else: h = hpx * (1 - k)
                edge = top[x] if side < 0 else bot[x]
                n = int(math.ceil(h))
                for d in range(1, n + 1):
                    yy = int(math.floor(edge - d)) if side < 0 else int(math.floor(edge + d - 1)) + 1
                    xx = int(round(x - sweep * d))
                    if 0 <= yy < Hc and 0 <= xx < Wc and kind[yy, xx] == 0:
                        kind[yy, xx] = 2; U[yy, xx] = k; V[yy, xx] = d / max(1, h); E[yy, xx] = 1 if d >= h - 1 else 0
        if self.dorsal: add_fin(self.dorsal, -1)
        if self.dorsal2: add_fin(self.dorsal2, -1)
        if self.anal: add_fin(self.anal, 1)
        if self.pelvic:
            pu, pl = self.pelvic; add_fin((pu - 0.05, pu + 0.02, pl, 'tri', 1.2), 1)
        if self.filament:
            fu, fl = self.filament
            x0 = min(xs, key=lambda x: abs(((x - 0.5) / L - tl) / (1 - tl) - fu))
            y0 = int(top[x0]) - int(self.dorsal[2] * H * 0.7)
            for i in range(int(fl)):
                xx = int(round(x0 - i * 0.9)); yy = y0 - int(i * 0.35)
                if 0 <= yy < Hc and 0 <= xx < Wc and kind[yy, xx] == 0:
                    kind[yy, xx] = 2; V[yy, xx] = 1; E[yy, xx] = 1

        bodyR = ramp(self.body); bellyR = ramp(self.belly_c) if self.belly_c else None
        finR = ramp(self.fin or self.body, lo=0.45, hi=1.25)
        n = len(bodyR)
        rgba = np.zeros((Hc, Wc, 4))
        for y in range(Hc):
            for x in range(Wc):
                k = kind[y, x]
                if not k: continue
                u, v = U[y, x], V[y, x]
                jit = (hash2(x, y, self.seed) - 0.5) * 0.5
                if k == 1:
                    lum = 0.20 + 0.78 * smooth(0.0, 0.72, v) - 0.18 * smooth(0.86, 1.0, v)
                    lum += 0.10 * math.exp(-((v - 0.3) / 0.1) ** 2)
                    lum += (vnoise(x, y, 2.5, self.seed) - 0.5) * self.noise * 3
                    lum -= 0.08 * smooth(0.9, 1.0, u)
                    R = bodyR
                    if bellyR is not None:
                        m = smooth(0.5, 0.78, v)
                        if m > 0.5 + jit * 0.3: R = bellyR; lum = 0.55 + 0.35 * v
                    c = R[int(np.clip(round(lum * (n - 1) + jit), 0, n - 1))]
                    if self.pattern:
                        r = self.pattern(u, v, x, y, lum)
                        if r is not None:
                            if isinstance(r, list): c = r[int(np.clip(round(lum * (n - 1) + jit), 0, n - 1))]
                            else: c = r * np.clip(0.55 + lum * 0.7, 0.5, 1.15)
                    if self.gill and abs(u - self.gill + 0.04 * (v - 0.5) ** 2 * 4) < 0.7 / L and 0.2 < v < 0.85: c = c * 0.8
                    if self.lateral and abs(v - 0.38 - 0.08 * math.sin(u * 3)) < 0.5 / H and 0.1 < u < 0.8: c = c * 0.88
                    rgba[y, x] = list(np.clip(c, 0, 255)) + [255]
                else:
                    lum = 0.5 + 0.25 * (1 - v) + jit * 0.2
                    if self.fin_rays and ((k == 3 and y % 2 == 0) or (k == 2 and x % 2 == 0)): lum -= 0.14
                    c = finR[int(np.clip(round(lum * (n - 1)), 0, n - 1))]
                    if self.finpat:
                        r = self.finpat(k, u, v, x, y)
                        if r is not None: c = r
                    al = self.fin_alpha * (1.0 if k == 3 and u < 0.35 else 0.9) + (0.25 if E[y, x] else 0)
                    if k == 3 and u < 0.2: al = 1.0
                    rgba[y, x] = list(np.clip(c, 0, 255)) + [255 * min(1, al)]
        # pectoral fin: translucent fan just behind the gill
        if self.pectoral:
            gx = int(1 + tl * L + (1 - tl) * L * (self.gill - 0.03)); gy = int(cy + H * 0.08)
            ln = max(2, int(H * self.pectoral))
            for i in range(ln):
                for j in range(0, 1 + i // 2):
                    xx, yy = gx - i, gy + j
                    if 0 <= yy < Hc and kind[yy, xx] == 1:
                        rgba[yy, xx, :3] = rgba[yy, xx, :3] * 0.55 + finR[4] * 0.45
        # eye
        ex = int(round(1 + tl * L + (1 - tl) * L * self.eye))
        col = [y for y in range(Hc) if kind[y, ex] == 1]
        if col:
            ey = int(col[0] + (col[-1] - col[0]) * self.eye_v)
            s = self.eye_size
            if self.eye_ring:
                for dy in range(-1, s + 1):
                    for dx in range(-1, s + 1):
                        if kind[ey + dy, ex + dx] == 1: rgba[ey + dy, ex + dx, :3] = hx(self.eye_ring)
            for dy in range(s):
                for dx in range(s): rgba[ey + dy, ex + dx, :3] = hx('#0b0d12')
            if s >= 2: rgba[ey, ex + s - 1, :3] = hx('#e8eef8')
        # mouth
        xn = xs[-1]; my = int(top[xn] + (bot[xn] - top[xn]) * 0.62)
        if kind[my, xn] == 1: rgba[my, xn, :3] *= 0.5
        # selective outline around body + tail
        out = np.zeros((Hc + 2, Wc + 2, 4)); out[1:-1, 1:-1] = rgba
        kk = np.zeros((Hc + 2, Wc + 2), int); kk[1:-1, 1:-1] = kind
        res = out.copy()
        dark, soft = bodyR[0] * 0.8, bodyR[1]
        for y in range(1, Hc + 1):
            for x in range(1, Wc + 1):
                if kk[y, x] in (0, 2):
                    nb = [(dy, dx) for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)) if kk[y + dy, x + dx] in (1, 3)]
                    if not nb: continue
                    below_body = any(dy == -1 for dy, dx in nb) and not any(dy == 1 for dy, dx in nb)
                    tailish = all(kk[y + dy, x + dx] == 3 for dy, dx in nb)
                    c = soft if below_body else dark
                    if tailish: c = finR[1]
                    a = 255 if not tailish else 220
                    if kk[y, x] == 2:   # pixel is fin: darken it instead
                        res[y, x, :3] = res[y, x, :3] * 0.6 + c * 0.4; res[y, x, 3] = max(res[y, x, 3], 230)
                    else:
                        res[y, x, :3] = c; res[y, x, 3] = a
        ys, xs_ = np.where(res[..., 3] > 0)
        res = res[ys.min():ys.max() + 1, xs_.min():xs_.max() + 1]
        return Image.fromarray(np.clip(res, 0, 255).astype('uint8'), 'RGBA')


