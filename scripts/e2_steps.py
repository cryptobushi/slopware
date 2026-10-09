#!/usr/bin/env python3
"""STEPS — the E2 research edition. Fixed by the artist before the run (E2 pre-registration §10).

One strip per parent, in parents.json order, stacked top to bottom. In each strip the x axis is the attempt (0 to the
budget) and the y axis is probe-A lifespan (0 at the strip's baseline to a shared ceiling). Arm A's walks (neutral)
are drawn in faint grey; arm B's walks (persistence) in black, as step functions that rise at every accepted
lengthening step. A red mark where a walk first reaches a never-observed behaviour. The parent's lifespan is a hairline
across the strip. Nothing is chosen after seeing the data: the order is parents.json, the y axis runs from 0 to the smallest
power of two >= the largest lifespan any walk reached (so the picture is scaled by the record itself, deterministically), the palette is the site's.

Input: the sealed E2 record, record/<arm>/summaries-*.jsonl, each line a walk with
  parentIndex, arm ("A"|"B"), walk, parentLifespan, budget, steps: [[attempt, lifespanAfter], ...] (lifespan after each
  accepted step), firstNovel: attempt index of the first never-seen behaviour or null.
Usage: python3 scripts/e2_steps.py <record dir> <out.png> [scale]
"""
import glob, json, sys
from PIL import Image, ImageDraw

rec, out = sys.argv[1], sys.argv[2]
SCALE = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

walks = []
for arm in ("A", "B"):
    for f in sorted(glob.glob(f"{rec}/{arm}/summaries-*.jsonl")):
        for l in open(f):
            if l.strip(): walks.append(json.loads(l))
parents = sorted({w["parentIndex"] for w in walks})
budget = max(w["budget"] for w in walks)
observed_max = max([max([lv for _, lv in w["steps"]] + [w["parentLifespan"]]) for w in walks])
ceiling = 1
while ceiling < observed_max: ceiling *= 2   # the smallest power of two >= the maximum lifespan in the record (pre-registration §10)
W = int(1600 * SCALE); strip = int(18 * SCALE); gap = int(4 * SCALE); pad = int(80 * SCALE)
H = pad * 2 + len(parents) * (strip + gap)
img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
x_of = lambda t: pad + (W - 2 * pad) * t / budget
for row, pi in enumerate(parents):
    y0 = pad + row * (strip + gap); base = y0 + strip
    y_of = lambda lv: base - strip * min(lv, ceiling) / ceiling
    mine = [w for w in walks if w["parentIndex"] == pi]
    pl = mine[0]["parentLifespan"]
    d.line([(x_of(0), y_of(pl)), (x_of(budget), y_of(pl))], fill=(200, 200, 200), width=1)
    for arm, col, wd in (("A", (0, 0, 0), 1), ("B", (0, 0, 0), max(1, int(1.5 * SCALE)))):
        for w in [m for m in mine if m["arm"] == arm]:
            pts = [(x_of(0), y_of(w["parentLifespan"]))]; lv = w["parentLifespan"]
            for t, nlv in w["steps"]:
                pts.append((x_of(t), y_of(lv))); pts.append((x_of(t), y_of(nlv))); lv = nlv
            pts.append((x_of(budget), y_of(lv)))
            if arm == "A":
                ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).line(pts, fill=(0, 0, 0, 40), width=wd)
                img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")); d = ImageDraw.Draw(img)
            else:
                d.line(pts, fill=col, width=wd)
            if w.get("firstNovel") is not None:
                x = x_of(w["firstNovel"]); r = 2 * SCALE
                d.ellipse((x - r, y0 - r, x + r, y0 + r), fill=(200, 60, 30))
img.save(out)
print(f"steps: {len(parents)} parents · {len(walks)} walks · ceiling {ceiling} instructions · {W}×{H} px → {out}")
