#!/usr/bin/env python3
"""THREADS — the E1 research edition. Fixed 2026-10-08 by the artist, before the results of E1 were known.

Every genesis program of E1 is drawn as a walk. The sixty-four bytes are read in order; each byte turns the
pen by (byte/255 − 1/2) × 0.9π and advances it by 1.6 + (byte mod 16) × 0.12 units. The whole walk is drawn
in faint grey: it is what the program is. The first `consumedBytes` steps are drawn in black: it is how much
of itself the program lived before it halted, as measured under world v0 (E1 protocol §5). A program that
executed three or more instructions ends in a red mark.

Programs are laid out in a grid in release order, one cell each, each walk starting at its cell's centre
pointing up. Genesis only. Nothing in the image is chosen after seeing the data: the layout is release order,
the rules are these, the palette is the site's (black, grey, one red).

Reproducible from the sealed E1 record: input is record/genesis/parents-*.jsonl (first summary per genotype).
Usage: python3 scripts/e1_threads.py <record dir> <out.png> [scale]
"""
import glob, json, math, sys
from PIL import Image, ImageDraw

rec, out = sys.argv[1], sys.argv[2]
SCALE = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0   # 1.0 → cell 46 px; 4.0 → print resolution

rows = {}
for f in sorted(glob.glob(f"{rec}/genesis/parents-*.jsonl")):
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l)
        if r["genotypeId"] in rows or not r["instantiable"]: continue
        rows[r["genotypeId"]] = (r["release"], r["bytes"][2:], r["parent"]["consumedBytes"] or 1, r["parent"]["lifespanA"] or 1)
walks = sorted(rows.values())
n = len(walks)
cols = int(math.ceil(math.sqrt(n * 1.4)))
cell = 46 * SCALE; pad = 120 * SCALE
W = int(pad * 2 + cols * cell); H = int(pad * 2 + math.ceil(n / cols) * cell)
img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
faint = Image.new("RGBA", (W, H), (0, 0, 0, 0)); df = ImageDraw.Draw(faint)
ink = Image.new("RGBA", (W, H), (0, 0, 0, 0)); di = ImageDraw.Draw(ink)
for k, (rel, hexs, consumed, life) in enumerate(walks):
    b = bytes.fromhex(hexs)
    x = pad + (k % cols) * cell + cell / 2; y = pad + (k // cols) * cell + cell / 2; ang = -math.pi / 2; pts = [(x, y)]
    for v in b:
        ang += (v / 255.0 - 0.5) * math.pi * 0.9
        step = (1.6 + (v % 16) * 0.12) * SCALE
        x += math.cos(ang) * step; y += math.sin(ang) * step; pts.append((x, y))
    df.line(pts, fill=(0, 0, 0, 40), width=max(1, int(1 * SCALE)))
    di.line(pts[:consumed + 1], fill=(0, 0, 0, 255), width=max(2, int(2 * SCALE)))
    if life >= 3:
        hx, hy = pts[consumed]; rr = 2 * SCALE
        di.ellipse((hx - rr, hy - rr, hx + rr, hy + rr), fill=(200, 60, 30, 255))
Image.alpha_composite(Image.alpha_composite(img, faint), ink).convert("RGB").save(out)
print(f"threads: {n} genesis programs · {cols} columns · {W}×{H} px → {out}")
