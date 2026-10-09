#!/usr/bin/env python3
"""E1 aggregates for the essay and the readings. Streams the placements once and writes a few megabytes:

  aggregates.json
    parents[]              per parent: set, label, release, lifespanA, consumedBytes, fractions, reaches, trace of probe A,
                           perPosition: 64 × {neutral, altered, lengthened, shortened, clean}  (class counts per position)
    childLifespan          histogram of children's probe-A instruction counts, by set, with parent lifespan buckets
    firstByte              for position-0 children of parents that die at byte one: outcome by replacement opcode name
    reaches                totals per behaviour, by set
    totals                 placements, parents, dedupe counts

Usage: python3 scripts/e1_aggregate.py <record dir> <genesis.json> <out.json>"""
import glob, json, sys, collections

rec, genesis_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
OPS = {}
try:
    # opcode names from the lab's table, via a tiny node one-liner would be heavier; keep a static list of the 55 operand-free ones
    pass
except Exception: pass

genesis = {g["genotypeId"]: g for g in json.load(open(genesis_path))["genomes"]}

# parents: first complete summary per genotype
parents = {}
for s in ("genesis", "control"):
    for f in sorted(glob.glob(f"{rec}/{s}/parents-*.jsonl")):
        for l in open(f):
            if not l.strip(): continue
            r = json.loads(l)
            parents.setdefault(r["genotypeId"], r)
CLASSES = ["neutral", "altered", "lengthened", "shortened", "clean"]
per_pos = {pid: [[0] * len(CLASSES) for _ in range(64)] for pid in parents}
child_life = {"genesis": collections.Counter(), "control": collections.Counter()}
child_life_by_parent_life = collections.defaultdict(collections.Counter)  # (set, parentLife) -> childLife counts
first_byte = collections.defaultdict(collections.Counter)  # replacement value -> outcome class (parents dying at byte one)
reaches = {"genesis": collections.Counter(), "control": collections.Counter()}
seen = set(); dup = 0; total = 0; noninst = 0

for s in ("genesis", "control"):
    for f in sorted(glob.glob(f"{rec}/{s}/placements-*.jsonl")):
        for l in open(f):
            if not l.strip(): continue
            r = json.loads(l)
            if r["e"] in seen: dup += 1; continue
            seen.add(r["e"]); total += 1
            if r.get("instantiable") is False or r.get("failure"): noninst += 1; continue
            p = parents.get(r["p"])
            if p is None: continue
            cls = r.get("cls", "altered"); rs = r.get("reaches") or []
            if "clean_halt" in rs: cls = "clean"
            per_pos[r["p"]][r["pos"]][CLASSES.index(cls)] += 1
            pa = next((q for q in r["probes"] if q["n"] == "A"), None)
            if pa:
                child_life[s][pa["i"]] += 1
                child_life_by_parent_life[(s, p["parent"]["lifespanA"])][pa["i"]] += 1
                if r["pos"] == 0 and (p["parent"]["lifespanA"] or 0) <= 1:
                    first_byte[r["val"]][("clean" if "clean_halt" in rs else pa["o"]) + ("" if pa["i"] <= 1 else "|lives")] += 1
            for b in rs: reaches[s][b] += 1

out = {
    "experiment": "E1", "totals": {"placements": total, "duplicatesSkipped": dup, "notInstantiable": noninst, "parents": len(parents)},
    "classes": CLASSES,
    "parents": [
        {"set": p["set"], "label": p["label"], "release": p.get("release"), "controlIndex": p.get("controlIndex"), "genotypeId": pid,
         "bytes": p["bytes"], "lifespanA": p["parent"]["lifespanA"], "consumedBytes": p["parent"]["consumedBytes"], "predictedNeutral": p["parent"]["predictedNeutral"],
         "noiseIdentical": p["parent"]["noiseIdentical"], "fractions": p["fractions"], "children": p["children"], "reaches": p["reaches"], "h5": len(p["h5"]),
         "traceA": [o.split(" ")[0] for o in (p["parent"]["placements"][0].get("probes", [{}])[0].get("ops") or [])] if p["parent"]["placements"] else [],
         "perPosition": per_pos[pid]}
        for pid, p in parents.items()
    ],
    "childLifespan": {s: dict(sorted(c.items())) for s, c in child_life.items()},
    "childLifespanByParentLifespan": {f"{s}|{pl}": dict(sorted(c.items())) for (s, pl), c in child_life_by_parent_life.items()},
    "firstByte": {str(v): dict(c) for v, c in sorted(first_byte.items())},
    "reaches": {s: dict(c) for s, c in reaches.items()},
}
json.dump(out, open(out_path, "w"), separators=(",", ":"))
print(f"placements {total:,} · duplicates skipped {dup:,} · not instantiable {noninst:,} · parents {len(parents)} → {out_path}")
