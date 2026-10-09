#!/usr/bin/env python3
"""E1 → the readings page. Writes slopware/site/descent.json (one summary per genesis release) and, for each
installed genesis release, a 64×255 neighbourhood map PNG in slopware/site/maps/<release>.png.

The map is the one-mutant neighbourhood: rows are positions 0..63, columns are replacement values 0..255
(the parent's own value at a position is left blank). Each cell is coloured by what the child did, relative to
its parent, under world v0. The palette is the only human choice and is fixed here:

  neutral     white      same signature as the parent
  shortened   black      died sooner than the parent
  altered     dark grey  same length, different signature
  lengthened  mid grey   lived longer than the parent
  clean halt  accent     the child halted cleanly (over any class)
  parent      blank      the position's own byte

Usage: python3 scripts/e1_descent.py <record dir, e.g. results/E1/record> [site dir]"""
import glob, json, os, struct, sys, zlib

rec = sys.argv[1]; site = sys.argv[2] if len(sys.argv) > 2 else "slopware/site"
PALETTE = {"neutral": (255, 255, 255), "shortened": (0, 0, 0), "altered": (90, 90, 90), "lengthened": (170, 170, 170), "clean": (200, 60, 30), "blank": (235, 235, 235), "none": (235, 235, 235)}

def png(width, height, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")

# parents: first complete summary per genotype
parents = {}
for f in sorted(glob.glob(f"{rec}/genesis/parents-*.jsonl")):
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l)
        parents.setdefault(r["genotypeId"], r)
print(f"{len(parents)} genesis parents")

# placements: cell colour per (parent, pos, val); stream the files once, dedupe by event id
cells = {}  # parentId -> dict[(pos,val)] -> class
seen = set()
for f in sorted(glob.glob(f"{rec}/genesis/placements-*.jsonl")):
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l)
        if r["e"] in seen: continue
        seen.add(r["e"])
        cls = "none" if r.get("instantiable") is False or r.get("failure") else r.get("cls", "none")
        if "clean_halt" in (r.get("reaches") or []): cls = "clean"
        cells.setdefault(r["p"], {})[(r["pos"], r["val"])] = cls
print(f"{len(seen):,} placements")

os.makedirs(f"{site}/maps", exist_ok=True)
out = []
for pid, p in parents.items():
    rel = p["release"]; bytes_ = bytes.fromhex(p["bytes"][2:])
    grid = cells.get(pid, {})
    if p["instantiable"] and grid:
        rows = []
        for pos in range(64):
            row = []
            for val in range(256):
                if val == bytes_[pos]: row += PALETTE["blank"]; continue
                row += PALETTE.get(grid.get((pos, val), "none"), PALETTE["none"])
            rows.append(row)
        open(f"{site}/maps/{rel:06d}.png", "wb").write(png(256, 64, rows))
    out.append({"release": rel, "genotypeId": pid, "instantiable": p["instantiable"], "lifespan": p["parent"]["lifespanA"], "consumedBytes": p["parent"]["consumedBytes"],
                "predictedNeutral": p["parent"]["predictedNeutral"], "noiseIdentical": p["parent"]["noiseIdentical"], "children": p["children"], "fractions": p["fractions"],
                "reaches": p["reaches"], "h5": len(p["h5"]), "map": f"maps/{rel:06d}.png" if (p["instantiable"] and grid) else None})
out.sort(key=lambda r: r["release"])
json.dump({"experiment": "E1", "world": "v0", "palette": {k: v for k, v in PALETTE.items() if k != "none"}, "releases": out}, open(f"{site}/descent.json", "w"), indent=0)
print(f"descent.json: {len(out)} releases · maps: {sum(1 for r in out if r['map'])}")
