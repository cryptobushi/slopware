#!/usr/bin/env python3
"""E3: the input rows for SOMEWHERE ELSE (scripts/e3_somewhere.py, frozen before the run). One row per parent in
parents.json order; in each row the parent and then the first walk's endpoints at Hamming 8, 16, 32, 48, 60, each
with its bytes, consumed prefix, probe-A lifespan and the 64 per-position non-neutral fractions from
summaries/positions.json. Mechanical: nothing is chosen, ordered or dropped here beyond what §10 fixed.
Usage: python3 scripts/e3_rows.py <E3 dir> <out rows.json> [walk=0]"""
import glob, json, sys
root, out = sys.argv[1], sys.argv[2]; WALK = int(sys.argv[3]) if len(sys.argv) > 3 else 0
P = json.load(open("slopware/experiments/E2/parents.json"))["parents"]
pos = json.load(open(f"{root}/summaries/positions.json"))["nonneutralByPosition"]
S = {}
for f in sorted(glob.glob(f"{root}/summaries/neighbourhoods/main/summaries-*.jsonl")):
    for l in open(f):
        if l.strip(): s = json.loads(l); S[s["genomeId"]] = s
def genome(gid):
    s = S[gid]; return {"id": gid, "bytes": s["bytes"], "consumed": s["selfConsumed"], "life": s["selfLifespan"], "nonneutral": [x if x is not None else 0.0 for x in pos[gid]]}
rows, missing = [], []
for p in P:
    g = [genome(f"P{p['index']}")]
    for t in (8, 16, 32, 48, 60):
        gid = f"E{p['index']}.{WALK}.{t}"
        if gid in S and gid in pos: g.append(genome(gid))
        else: missing.append(gid)
    rows.append({"label": p["label"], "set": p["set"], "genomes": g})
json.dump(rows, open(out, "w"))
print(f"{len(rows)} rows · {sum(len(r['genomes']) for r in rows)} genomes · missing {missing or 'none'}")
