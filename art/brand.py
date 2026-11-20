"""Macquarium branding: app icon, logo, README banner and GitHub social preview.

Everything is drawn at a small pixel resolution and scaled up with nearest-neighbour,
so it matches the tank. Needs pillow + numpy; the pixel font comes from app/tank/fonts
(converted to TTF on the fly with fontTools if needed).
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sprites as SPR

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TANK = os.path.join(ROOT, 'app', 'tank')
DOCS = os.path.join(ROOT, 'docs')
os.makedirs(DOCS, exist_ok=True)


def font(size, weight='600'):
    ttf = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'.pixelify-{weight}.ttf')
    if not os.path.exists(ttf):
        from fontTools.ttLib import TTFont
        f = TTFont(os.path.join(TANK, 'fonts', f'pixelify-sans-latin-{weight}-normal.woff2')); f.flavor = None; f.save(ttf)
    return ImageFont.truetype(ttf, size)


def crisp_text(img, xy, text, size, fill, weight='600', shadow=(4, 14, 24, 255)):
    d = ImageDraw.Draw(img); d.fontmode = '1'                      # no anti-aliasing: real pixels
    f = font(size, weight)
    if shadow: d.text((xy[0] + 1, xy[1] + 1), text, font=f, fill=shadow)
    d.text(xy, text, font=f, fill=fill)
    return d.textbbox(xy, text, font=f)


def water(w, h):
    top, bot = np.array([44, 159, 214]), np.array([4, 32, 58])
    a = np.zeros((h, w, 4), 'uint8')
    for y in range(h):
        t = (y / h) ** 0.9; a[y, :, :3] = top * (1 - t) + bot * t; a[y, :, 3] = 255
    im = Image.fromarray(a, 'RGBA')
    rays = Image.new('RGBA', (w, h)); d = ImageDraw.Draw(rays)
    for x0 in range(-w, w, max(12, w // 5)):                      # soft light rays, blended on top
        d.polygon([(x0, 0), (x0 + max(3, w // 14), 0), (x0 + w // 3, h), (x0 + w // 4, h)], fill=(255, 255, 255, 16))
    im.alpha_composite(rays)
    return im


# ------------------------------------------------------------------ app icon / logo (64px pixel art)
def logo():
    N = 64
    im = water(N, N)
    reef = Image.open(os.path.join(TANK, 'reef.png')).convert('RGBA')
    im.alpha_composite(reef.crop((166, 172, 230, 210)), (0, 30))
    clown = SPR.S['Clownfish']()
    clown = clown.resize((clown.width * 2, clown.height * 2), Image.NEAREST)
    im.alpha_composite(clown, ((N - clown.width) // 2 + 3, 20))
    d = ImageDraw.Draw(im)
    P = (240, 252, 255, 255); S = (6, 30, 50, 255)
    for ox, oy, c in ((1, 1, S), (0, 0, P)):                     # ">_" with a little shadow
        for i in range(4):
            d.rectangle((8 + i * 2 + ox, 7 + i * 2 + oy, 9 + i * 2 + ox, 8 + i * 2 + oy), fill=c)
            d.rectangle((8 + i * 2 + ox, 19 - i * 2 + oy, 9 + i * 2 + ox, 20 - i * 2 + oy), fill=c)
        d.rectangle((18 + ox, 19 + oy, 26 + ox, 20 + oy), fill=c)
    for (x, y) in ((49, 14), (53, 9), (50, 5)):                  # bubbles
        d.point([(x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)], fill=(200, 238, 255, 255))
    # macOS-style rounded square with a dark rim
    mask = Image.new('L', (N, N)); md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, N - 1, N - 1), radius=14, fill=255)
    out = Image.new('RGBA', (N, N)); out.paste(im, (0, 0), mask)
    a = np.array(out)
    edge = np.zeros(a.shape[:2], bool)
    al = a[..., 3] > 0
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        edge |= al & ~np.roll(np.roll(al, dy, 0), dx, 1)
    a[edge] = [6, 26, 44, 255]
    return Image.fromarray(a, 'RGBA')


def save_icon(lg):
    big = lg.resize((1024, 1024), Image.NEAREST)
    # macOS icons sit inside a 1024 canvas with ~10% margin
    canvas = Image.new('RGBA', (1024, 1024)); inner = lg.resize((832, 832), Image.NEAREST)
    canvas.alpha_composite(inner, (96, 96))
    canvas.save(os.path.join(ROOT, 'app', 'AppIcon.icns'), sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
    big.resize((512, 512), Image.NEAREST).save(os.path.join(DOCS, 'logo.png'))
    lg.resize((128, 128), Image.NEAREST).save(os.path.join(DOCS, 'logo-128.png'))


# ------------------------------------------------------------------ banner / social preview
def scene(w, h, reef_y, fish):
    im = water(w, h)
    reef = Image.open(os.path.join(TANK, 'reef.png')).convert('RGBA')
    x = (reef.width - w) // 2
    im.alpha_composite(reef.crop((max(0, x), 110, max(0, x) + w, 210)), (0, reef_y))
    for name, fx, fy, flip in fish:
        s = SPR.S[name]()
        if flip: s = s.transpose(Image.FLIP_LEFT_RIGHT)
        im.alpha_composite(s, (fx, fy))
    return im


def banner(lg):
    W, H = 320, 100
    im = scene(W, H, 46, [('Reef Shark', 200, 6, True), ('Blue Tang', 262, 50, True), ('Yellow Tang', 196, 52, False),
                         ('Fusilier', 296, 30, True), ('Fusilier', 304, 36, True), ('Anthias', 170, 70, False)])
    shade = Image.new('RGBA', (178, 64), (4, 22, 36, 205))
    m = Image.new('L', shade.size); ImageDraw.Draw(m).rounded_rectangle((0, 0, 177, 63), radius=8, fill=255)
    im.paste(shade, (8, 18), m) if False else im.alpha_composite(Image.composite(shade, Image.new('RGBA', shade.size), m), (8, 18))
    im.alpha_composite(lg.resize((40, 40), Image.NEAREST), (14, 30))
    crisp_text(im, (60, 28), 'Macquarium', 20, (230, 251, 255, 255))
    crisp_text(im, (61, 53), 'a live pixel-art reef', 10, (127, 220, 255, 255), '400')
    crisp_text(im, (61, 65), 'behind your Mac terminal', 10, (127, 220, 255, 255), '400')
    im.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(DOCS, 'banner.png'))


def social(lg):
    W, H = 320, 160
    im = scene(W, H, 70, [('Reef Shark', 180, 14, True), ('Blue Tang', 30, 96, False), ('Yellow Tang', 250, 110, True),
                          ('Clownfish', 150, 132, False), ('Moorish Idol', 92, 18, False)])
    pane = Image.new('RGBA', (262, 64)); ImageDraw.Draw(pane).rounded_rectangle((0, 0, 261, 63), radius=8, fill=(4, 22, 36, 210))
    im.alpha_composite(pane, (12, 36))
    im.alpha_composite(lg.resize((48, 48), Image.NEAREST), (20, 44))
    crisp_text(im, (76, 46), 'Macquarium', 20, (230, 251, 255, 255))
    crisp_text(im, (77, 72), 'a live pixel-art reef behind your Mac terminal', 10, (200, 240, 255, 255), '400')
    im.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(DOCS, 'social-preview.png'))


if __name__ == '__main__':
    lg = logo()
    save_icon(lg); banner(lg); social(lg)
    print('wrote app/AppIcon.icns, docs/logo.png, docs/logo-128.png, docs/banner.png, docs/social-preview.png')
