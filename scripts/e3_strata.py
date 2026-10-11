#!/usr/bin/env python3
"""E3 §7.7 stratification: every X1–X4 statistic by set (genesis, control) and by parent lifespan (3; 4 or more).
Pre-specified in the protocol but omitted from the frozen analysis script; computed afterwards from the same sealed
summaries with the same definitions (within-parent medians, parent bootstrap). Labelled as such in the results.
Usage: python3 scripts/e3_strata.py <E3 dir> > summaries/strata.json"""
import glob, json, os, random, statistics, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e3_metrics import total_variation, expected_jaccard
root = sys.argv[1]; TARGETS = [8, 16, 32, 48, 60]; CLASSES = ["neutral", "altered", "lengthened", "shortened", "lethal"]
S = {}
for f in sorted(glob.glob(f"{root}/summaries/neighbourhoods/main/summaries-*.jsonl")):
    for l in open(f):
        if l.strip(): s = json.loads(l); S[s["genomeId"]] = s
def hist(g): return dict(S[g]["signatureHistogram"])
def dist(a, b):
    pa = {c: S[a]["counts"][c] / S[a]["placeable"] for c in CLASSES}; pb = {c: S[b]["counts"][c] / S[b]["placeable"] for c in CLASSES}
    ha, hb = hist(a), hist(b); na, nb = sum(ha.values()), sum(hb.values())
    return {"D5": total_variation(pa, pb), "Dsig": total_variation({k: v / na for k, v in ha.items()}, {k: v / nb for k, v in hb.items()}),
            "JS": len(set(ha) & set(hb)) / len(set(ha) | set(hb))}
by = collections.defaultdict(lambda: collections.defaultdict(list))
for g, s in S.items():
    if s["kind"] != "endpoint": continue
    pg = f"P{s['parentIndex']}"; d = dist(g, pg)
    d["x3"] = {"adjacentVariation": (1 - s["counts"]["neutral"] / s["placeable"]) - (1 - S[pg]["counts"]["neutral"] / S[pg]["placeable"]), "richness": s["distinctSignatures"] - S[pg]["distinctSignatures"], "upward": s["upward"] / s["placeable"] - S[pg]["upward"] / S[pg]["placeable"]}
    by[s["parentIndex"]][s["target"]].append(d)
rnd = random.Random(3)
def boot(vals):
    ps = list(vals); n = 10000
    if not ps: return None
    means = sorted(sum(vals[rnd.choice(ps)] for _ in ps) / len(ps) for _ in range(n))
    return {"mean": sum(vals.values()) / len(ps), "ci95": [means[int(0.025 * n)], means[int(0.975 * n)]], "parents": len(ps)}
def med(PI, t, f): return {pi: statistics.median(f(m) for m in by[pi][t]) for pi in PI if by[pi].get(t)}
strata = {"genesis": [pi for pi in by if S[f"P{pi}"]["set"] == "genesis"], "control": [pi for pi in by if S[f"P{pi}"]["set"] == "control"],
          "lifespan3": [pi for pi in by if S[f"P{pi}"]["selfLifespan"] == 3], "lifespan4plus": [pi for pi in by if S[f"P{pi}"]["selfLifespan"] >= 4]}
out = {}
for name, PI in strata.items():
    out[name] = {"parents": len(PI), "by_target": {}}
    for t in TARGETS:
        out[name]["by_target"][t] = {"Dsig": boot(med(PI, t, lambda m: m["Dsig"])), "D5": boot(med(PI, t, lambda m: m["D5"])), "JS": boot(med(PI, t, lambda m: m["JS"])),
            "differing": sum(1 for pi in PI for m in by[pi][t] if m["Dsig"] > 0 or m["JS"] < 1) / max(1, sum(len(by[pi][t]) for pi in PI)),
            "x3": {k: boot(med(PI, t, lambda m, k=k: m["x3"][k])) for k in ("adjacentVariation", "richness", "upward")}}
json.dump(out, sys.stdout, indent=1)
