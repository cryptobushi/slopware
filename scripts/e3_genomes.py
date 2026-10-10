#!/usr/bin/env python3
"""E3: the list of genomes whose neighbourhoods are enumerated, in the fixed order of E3-somewhere-else.md §5.6:
parents first (parents.json order), then endpoints by parent, walk, target. Every tenth genome in this order is also
in the reproducibility subset. Mechanical: built from parents.json and the walks' endpoints files and nothing else.
Usage: python3 scripts/e3_genomes.py <record dir> <parents.json> <out genomes.jsonl> <out reproducibility.jsonl>"""
import glob, json, sys
rec, parents_file, out, out_rep = sys.argv[1:5]
P = json.load(open(parents_file))["parents"]
rows = [{"genomeId": f"P{p['index']}", "kind": "parent", "parentIndex": p["index"], "set": p["set"], "label": p["label"], "bytes": p["bytes"], "hamming": 0} for p in P]
ends = []
for f in sorted(glob.glob(f"{rec}/walks/endpoints-*.jsonl")):
    for l in open(f):
        if l.strip():
            e = json.loads(l)
            if e.get("target") != "end": ends.append(e)
ends.sort(key=lambda e: (e["parentIndex"], e["walk"], e["target"]))
for e in ends: rows.append({"genomeId": f"E{e['parentIndex']}.{e['walk']}.{e['target']}", "kind": "endpoint", "parentIndex": e["parentIndex"], "set": e["set"], "label": e["label"], "walk": e["walk"], "target": e["target"], "attempt": e["attempt"], "bytes": e["bytes"], "hamming": e["hamming"]})
with open(out, "w") as f:
    for r in rows: f.write(json.dumps(r) + "\n")
rep = rows[::10]
with open(out_rep, "w") as f:
    for r in rep: f.write(json.dumps(r) + "\n")
print(f"{len(rows)} genomes ({len(P)} parents + {len(ends)} endpoints) → {out} · reproducibility subset {len(rep)} → {out_rep}")
