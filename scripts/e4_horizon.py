#!/usr/bin/env python3
"""E4 horizon figure for the results page: rho_g (the primary Spearman correlation recomputed at every generation) as one
trajectory with its pointwise 95% bootstrap band, from summaries/results.json (the pre-specified tertiary analysis, §3).
Descriptive; the band is not multiplicity-adjusted. Usage: python3 scripts/e4_horizon.py <results.json> <out.png> [width]"""
import json, sys
from PIL import Image, ImageDraw
res = json.load(open(sys.argv[1])); out = sys.argv[2]; W = int(sys.argv[3]) if len(sys.argv) > 3 else 1680
H = int(W / 3); ML, MR, MT, MB = int(W * 0.05), int(W * 0.02), int(H * 0.08), int(H * 0.16)
hz = res['horizon']; G = len(hz); ref = res['primary']['reference_smallest_substantial']
YMIN, YMAX = -0.4, 0.8
def X(g): return ML + (g - 1) / (G - 1) * (W - ML - MR)
def Y(v): return MT + (YMAX - v) / (YMAX - YMIN) * (H - MT - MB)
im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
band = [(X(h['g']), Y(h['ci95'][0])) for h in hz if h['ci95'][0] is not None] + [(X(h['g']), Y(h['ci95'][1])) for h in reversed(hz) if h['ci95'][1] is not None]
if len(band) > 2: d.polygon(band, fill=(225, 225, 225))
d.line([(ML, Y(0)), (W - MR, Y(0))], fill='black', width=max(1, W // 1680))
for x in range(ML, W - MR, max(6, W // 140)): d.line([(x, Y(ref)), (min(x + max(3, W // 280), W - MR), Y(ref))], fill=(120, 120, 120), width=max(1, W // 1680))
pts = [(X(h['g']), Y(h['rho'])) for h in hz if h['rho'] is not None]
d.line(pts, fill='black', width=max(2, W // 560))
lw = max(1, W // 1680)
for g in (1, 32, 64, 96, 128, 160, 192, 224, 256):
    d.line([(X(g), H - MB), (X(g), H - MB + H * 0.02)], fill='black', width=lw); d.text((X(g) - 4, H - MB + H * 0.03), str(g), fill='black')
for v in (-0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8):
    d.line([(ML - W * 0.006, Y(v)), (ML, Y(v))], fill='black', width=lw); d.text((ML - W * 0.04, Y(v) - 6), f'{v:+.1f}' if v else ' 0', fill='black')
d.line([(ML, MT), (ML, H - MB)], fill='black', width=lw); d.line([(ML, H - MB), (W - MR, H - MB)], fill='black', width=lw)
d.text((ML + 8, MT), 'rho_g: Spearman correlation across the 88 pairs between the predicted accessibility difference (E3) and the observed fitness difference at generation g; grey band, pointwise 95% bootstrap; dashed, the pre-specified 0.3', fill=(80, 80, 80))
d.text((W - MR - 70, H - MB + H * 0.08), 'generation', fill=(80, 80, 80))
im.save(out, optimize=True)
peak = max((h for h in hz if h['rho'] is not None), key=lambda h: h['rho'])
exc = [h['g'] for h in hz if h['ci95'][0] is not None and h['ci95'][0] > 0]
print(f"{out}: {W}x{H} · peak rho {peak['rho']:.3f} at g{peak['g']} · band excludes zero at {len(exc)} generations ({exc[0]}..{exc[-1]})" if exc else f"{out}: {W}x{H}")
