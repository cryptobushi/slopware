#!/usr/bin/env python3
"""E3: per-position non-neutral fractions for every enumerated genome, streamed from the sealed placements
(record/neighbourhoods/<tag>/placements-*.jsonl). For each genome and each of the 64 byte positions: the fraction of
that position's placeable children (255, or 254 at position 0, less any harness failures) whose class is not neutral.
This is the input the edition renderer (scripts/e3_somewhere.py, frozen) and the position figures need; it is data
extraction, not analysis, and adds no statistic to the pre-specified set.
Usage: python3 scripts/e3_positions.py <E3 dir with record/> [tag=main] > summaries/positions.json"""
import glob, json, sys, collections
root = sys.argv[1]; tag = sys.argv[2] if len(sys.argv) > 2 else "main"
non = collections.defaultdict(lambda: [0] * 64); den = collections.defaultdict(lambda: [0] * 64); hf = collections.Counter()
for f in sorted(glob.glob(f"{root}/record/neighbourhoods/{tag}/placements-*.jsonl")):
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l); g, p = r["g"], r["pos"]
        if r["cls"] == "harness_failure": hf[g] += 1; continue
        den[g][p] += 1
        if r["cls"] != "neutral": non[g][p] += 1
out = {g: [round(non[g][p] / den[g][p], 6) if den[g][p] else None for p in range(64)] for g in den}
json.dump({"tag": tag, "genomes": len(out), "harnessFailures": dict(hf), "nonneutralByPosition": out}, sys.stdout)
print(f"\n{len(out)} genomes · {sum(sum(d) for d in den.values()):,} placements · harness failures {sum(hf.values())}", file=sys.stderr)
