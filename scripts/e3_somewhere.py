#!/usr/bin/env python3
"""SOMEWHERE ELSE — candidate E3 research edition (draft, not yet fixed or hashed; E3-somewhere-else.md §10).

One row per parent, in parents.json order. In each row, left to right: the parent P and its endpoints at Hamming
8, 16, 32, 48, 60 (the first walk's), each drawn as a THREADS walk with THREADS' pen and palette (faint: the whole
genome; black: the executed prefix; red mark at three or more instructions). Beneath each genome a bar of 64 cells,
one per byte position, inked by the fraction of that position's 255 one-byte children whose signature differs from
the genome's (0 → white, 1 → black). Genomes that do the same thing look different because their bytes differ; if
neutral history changes nothing about what is reachable next, every bar in a row is the same bar.

Input: a JSON list of rows {label, genomes: [{bytes, consumed, life, nonneutral: [64 fractions]}, ...]} from the
sealed E3 record. Usage: python3 scripts/e3_somewhere.py <rows.json> <out.png> [scale]
"""
import json, math, sys
from PIL import Image, ImageDraw

rows = json.load(open(sys.argv[1])); out = sys.argv[2]; S = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
cell = 46 * S; bar_h = 6 * S; gap = 10 * S; pad = 40 * S; cols = max(len(r["genomes"]) for r in rows)
W = int(pad * 2 + cols * (cell + gap)); H = int(pad * 2 + len(rows) * (cell + bar_h + gap * 2))
img = Image.new("RGBA", (W, H), (255, 255, 255, 255)); faint = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
df, di = ImageDraw.Draw(faint), ImageDraw.Draw(ink)
for ri, r in enumerate(rows):
    y0 = pad + ri * (cell + bar_h + gap * 2)
    for gi, g in enumerate(r["genomes"]):
        x0 = pad + gi * (cell + gap); b = bytes.fromhex(g["bytes"][2:])
        x, y, ang = x0 + cell / 2, y0 + cell / 2, -math.pi / 2; pts = [(x, y)]
        for v in b:
            ang += (v / 255.0 - 0.5) * math.pi * 0.9; step = (1.6 + (v % 16) * 0.12) * S
            x += math.cos(ang) * step; y += math.sin(ang) * step; pts.append((x, y))
        df.line(pts, fill=(0, 0, 0, 40), width=max(1, int(S)))
        di.line(pts[:g["consumed"] + 1], fill=(0, 0, 0, 255), width=max(2, int(2 * S)))
        if g["life"] >= 3:
            hx, hy = pts[g["consumed"]]; rr = 2 * S; di.ellipse((hx - rr, hy - rr, hx + rr, hy + rr), fill=(200, 60, 30, 255))
        bw = cell / 64
        for pos, f in enumerate(g["nonneutral"]):
            v = int(255 * (1 - min(1, max(0, f))))
            di.rectangle((x0 + pos * bw, y0 + cell + gap, x0 + (pos + 1) * bw, y0 + cell + gap + bar_h), fill=(v, v, v, 255))
Image.alpha_composite(Image.alpha_composite(img, faint), ink).convert("RGB").save(out)
print(f"somewhere else: {len(rows)} rows × {cols} genomes · {W}×{H} px → {out}")
