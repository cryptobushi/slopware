#!/usr/bin/env python3
"""E1 analysis, as pre-specified in slopware/experiments/E1-neighbourhoods.md §7.
Reads record/<set>/parents-*.jsonl for both sets; writes summaries/E1/results.json and prints the report.
Usage: python3 scripts/e1_analysis.py [slopware/experiments/E1]"""
import glob, json, math, random, sys, collections

root = sys.argv[1] if len(sys.argv) > 1 else "slopware/experiments/E1"
def load(s):
    rows = []
    for f in sorted(glob.glob(f"{root}/record/{s}/parents-*.jsonl")):
        rows += [json.loads(l) for l in open(f) if l.strip()]
    return [r for r in rows if r["instantiable"] and r["children"]["placed"] > 0]
G, C = load("genesis"), load("control")
print(f"genesis parents {len(G)} · control parents {len(C)}")
if not G or not C: sys.exit("both sets are needed")

FR = ["neutral", "altered", "lengthened", "shortened", "lethal"]
def ks(a, b):
    a, b = sorted(a), sorted(b); i = j = 0; d = 0.0; n, m = len(a), len(b)
    while i < n and j < m:
        if a[i] <= b[j]: i += 1
        else: j += 1
        d = max(d, abs(i / n - j / m))
    en = math.sqrt(n * m / (n + m)); lam = (en + 0.12 + 0.11 / en) * d
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam) for k in range(1, 101))
    return d, max(0.0, min(1.0, p))
def boot_diff(a, b, n=10000, seed=1):
    rnd = random.Random(seed); diffs = []
    for _ in range(n):
        sa = [rnd.choice(a) for _ in a]; sb = [rnd.choice(b) for _ in b]
        diffs.append(sum(sa) / len(sa) - sum(sb) / len(sb))
    diffs.sort(); return sum(a) / len(a) - sum(b) / len(b), diffs[int(0.025 * n)], diffs[int(0.975 * n)]
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0, 0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h

res = {"parents": {"genesis": len(G), "control": len(C)}}
# H1 — no privilege
h1 = {}; indist = True
for f in FR:
    a = [r["fractions"][f] for r in G]; b = [r["fractions"][f] for r in C]
    d, p = ks(a, b); diff, lo, hi = boot_diff(a, b)
    h1[f] = {"genesis_mean": sum(a) / len(a), "control_mean": sum(b) / len(b), "diff": diff, "ci95": [lo, hi], "ks_D": d, "ks_p": p}
    if abs(diff) >= 0.01 or p <= 0.01: indist = False
res["H1"] = {"indistinguishable_by_prespecified_threshold": indist, "fractions": h1}
# H2 — the executed prefix
err = [abs(r["fractions"]["neutral"] - r["parent"]["predictedNeutral"]) for r in G + C if r["parent"]["predictedNeutral"] is not None]
err.sort(); med = err[len(err) // 2]
res["H2"] = {"median_abs_error": med, "within_0.02": sum(1 for e in err if e <= 0.02) / len(err), "confirmed": med < 0.01}
# H3 — the first byte: among parents dying at byte one, position-0 children living >= 2 instructions
# (recorded via placements: count children with pos 0 whose probe A instruction count >= 2)
k = n = 0
for s in ("genesis", "control"):
    for f in sorted(glob.glob(f"{root}/record/{s}/placements-*.jsonl")):
        for l in open(f):
            if '"pos":0' not in l and '"pos": 0' not in l: continue
            r = json.loads(l)
            if r.get("pos") != 0 or not r.get("probes"): continue
            pa = next((p for p in r["probes"] if p["n"] == "A"), None)
            if pa is None: continue
            n += 1; k += 1 if pa["i"] >= 2 else 0
p3, lo3, hi3 = wilson(k, n)
res["H3"] = {"position0_children": n, "survive_first": k, "fraction": p3, "ci95": [lo3, hi3], "predicted": 55 / 255, "note": "denominator is all position-0 children; restrict to dead-at-first-byte parents in exploratory analysis"}
# H4 — lengthening is rare
L = sum(r["children"]["lengthened"] for r in G + C); P = sum(r["children"]["placed"] for r in G + C)
NC = sum(r["reaches"].get("clean_halt", 0) for r in G + C if not any("clean_halt" in pp["reaches"] for pp in r["parent"]["placements"][:1]))
pl, llo, lhi = wilson(L, P); pc, clo, chi = wilson(NC, P)
res["H4"] = {"placed": P, "lengthened": L, "lengthened_fraction": pl, "ci95": [llo, lhi], "bound": 0.03, "new_clean_halts": NC, "new_clean_fraction": pc, "ci95_clean": [clo, chi], "bound_clean": 0.005, "confirmed": lhi < 0.03 and chi < 0.005}
# H5 — nothing new
cands = [dict(parent=r["genotypeId"], label=r["label"], **c) for r in G + C for c in r["h5"]]
res["H5"] = {"candidates": len(cands), "list": cands[:200], "confirmed_if_empty_after_replication": len(cands) == 0}
# noise
noise = [r["parent"]["noiseIdentical"] for r in G + C]
res["noise"] = {"triplicate_identical_fraction": sum(noise) / len(noise), "environment_sensitive_parents": [r["label"] for r in G + C if not r["parent"]["noiseIdentical"]]}

import os; os.makedirs(f"{root}/summaries", exist_ok=True)
json.dump(res, open(f"{root}/summaries/results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "H5"}, indent=1)); print("H5 candidates:", len(cands))
