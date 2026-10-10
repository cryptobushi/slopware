#!/usr/bin/env python3
"""After the walks, drawn with THREADS' rules (scripts/e1_threads.py): the 88 parents on the left, and on the right the
final genome of each parent's longest-running arm-B walk, same pen, same palette, same red mark at three or more
instructions. Drawn AFTER the run, labelled as such on the page; not the edition. Loops are drawn like any other run:
the black prefix is the bytes the program consumed, which for a loop is the loop body.
Usage: python3 scripts/e2_after.py <E2 record dir> <parents.json> <out.png> [scale]"""
import glob, json, math, sys
from PIL import Image, ImageDraw
rec, parents_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
SCALE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
P = json.load(open(parents_file))["parents"]
B = [json.loads(l) for f in sorted(glob.glob(f"{rec}/B/summaries-*.jsonl")) for l in open(f) if l.strip()]
best = {}
for s in B:
    if s["parentIndex"] not in best or s["finalLifespan"] > best[s["parentIndex"]]["finalLifespan"]: best[s["parentIndex"]] = s
def walk(hexs, consumed, life, cx, cy, df, di):
    b = bytes.fromhex(hexs[2:]); x, y, ang = cx, cy, -math.pi / 2; pts = [(x, y)]
    for v in b:
        ang += (v / 255.0 - 0.5) * math.pi * 0.9; step = (1.6 + (v % 16) * 0.12) * SCALE
        x += math.cos(ang) * step; y += math.sin(ang) * step; pts.append((x, y))
    df.line(pts, fill=(0, 0, 0, 40), width=max(1, int(1 * SCALE)))
    di.line(pts[:consumed + 1], fill=(0, 0, 0, 255), width=max(2, int(2 * SCALE)))
    if life >= 3:
        hx, hy = pts[consumed]; rr = 2 * SCALE; di.ellipse((hx - rr, hy - rr, hx + rr, hy + rr), fill=(200, 60, 30, 255))
cols = 8; cell = 46 * SCALE; pad = 60 * SCALE; gapx = 80 * SCALE
rows = math.ceil(len(P) / cols)
W = int(pad * 2 + cols * cell * 2 + gapx); H = int(pad * 2 + rows * cell)
img = Image.new("RGBA", (W, H), (255, 255, 255, 255)); faint = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
df, di = ImageDraw.Draw(faint), ImageDraw.Draw(ink)
for k, p in enumerate(P):
    cx = pad + (k % cols) * cell + cell / 2; cy = pad + (k // cols) * cell + cell / 2
    walk(p["bytes"], p["consumedBytes"] or 1, p["lifespanA"] or 1, cx, cy, df, di)
    s = best.get(p["index"])
    if s: walk(s["finalBytes"], s["finalConsumed"] or 1, s["finalLifespan"] or 1, cx + cols * cell + gapx, cy, df, di)
Image.alpha_composite(Image.alpha_composite(img, faint), ink).convert("RGB").save(out)
print(f"after: {len(P)} parents, left before and right after the longest persistence walk · {W}×{H} px → {out}")
