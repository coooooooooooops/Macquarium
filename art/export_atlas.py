"""Pack every creature into one atlas: 4 swim frames x 3 depth tints each."""
import json
import numpy as np
from PIL import Image
import sprites as SPR
import creatures as SC

import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'tank') + '/'
WATER = np.array([31, 120, 170], float)
DEPTHS = [0.0, 0.22, 0.48]

def wag(im, shift):
    """Swim frame: bend the tail region up/down by one pixel."""
    a = np.array(im); h, w = a.shape[:2]; tw = max(2, int(w * 0.2)); b = a.copy()
    for x in range(tw):
        s = shift if x < tw * 0.6 else (shift if shift == 0 else int(np.sign(shift)))
        b[:, x] = np.roll(a[:, x], s, axis=0)
        if s > 0: b[:s, x] = 0
        elif s < 0: b[s:, x] = 0
    return Image.fromarray(b, 'RGBA')

def tint(im, d):
    a = np.array(im).astype(float); a[..., :3] = a[..., :3] * (1 - d) + WATER * d
    return Image.fromarray(a.clip(0, 255).astype('uint8'), 'RGBA')

creatures = {n: SPR.S[n]() for n in SPR.S}
creatures['Sea Turtle'] = Image.fromarray(SC.turtle().astype('uint8'), 'RGBA')
creatures['Eagle Ray'] = Image.fromarray(SC.eagle_ray().astype('uint8'), 'RGBA')
creatures['Seahorse'] = Image.fromarray(SC.seahorse('#ffb02e').astype('uint8'), 'RGBA')

frames = []
for name, im in creatures.items():
    pad = Image.new('RGBA', (im.width, im.height + 2)); pad.alpha_composite(im, (0, 1))
    seq = [pad, wag(pad, -1), pad, wag(pad, 1)] if name not in ('Seahorse',) else [pad] * 4
    for di, d in enumerate(DEPTHS):
        for fi, fr in enumerate(seq):
            frames.append((name, di, fi, tint(fr, d)))

# swaying decor (8 frames each, depth 0 only)
import reef as RF
decor_meta = []
for i, (kind, x, y, seed) in enumerate(RF.DECOR):
    key = f'Decor{i}'
    for fi, fr in enumerate(RF.decor_frames(kind, seed)):
        frames.append((key, 0, fi, fr))
    decor_meta.append({'k': key, 'x': x, 'y': y})

# shelf-pack
W = 1024; x = y = rowh = 0; meta = {}
for name, di, fi, im in sorted(frames, key=lambda f: -f[3].height):
    if x + im.width + 1 > W: x = 0; y += rowh + 1; rowh = 0
    meta.setdefault(name, {'w': im.width, 'h': im.height, 'f': {}})['f'][f'{di}_{fi}'] = [x, y]
    x += im.width + 1; rowh = max(rowh, im.height)
H = y + rowh + 1
atlas = Image.new('RGBA', (W, H))
for name, di, fi, im in frames:
    px, py = meta[name]['f'][f'{di}_{fi}']; atlas.alpha_composite(im, (px, py))
atlas.save(OUT + 'atlas.png')
json.dump(meta, open(OUT + 'atlas.json', 'w'))
print('atlas', atlas.size, len(meta), 'creatures')

# reef surface data for the engine
import json
r = Image.open(OUT + 'reef.png'); a = r.split()[3].load(); RW, RH = r.size
top = [next((y for y in range(40, RH) if a[x, y] > 0), 200) for x in range(RW)]
with open(OUT + 'atlas.js', 'w') as f:
    f.write('window.ATLAS=' + json.dumps(meta) + ';\n')
    f.write('window.REEF=' + json.dumps({'w': RW, 'h': RH, 'top': top, 'anemones': [[131, 190], [311, 190]], 'decor': decor_meta}) + ';\n')
os.remove(OUT + 'atlas.json')
