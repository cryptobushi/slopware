#!/usr/bin/env python3
"""E3 analysis, pre-specified (E3-somewhere-else.md §3, §5, §7). Reads the sealed record:
  record/neighbourhoods/main/{summaries,placements}-*.jsonl, record/neighbourhoods/rep/... (reproducibility subset),
  record/walks/endpoints-*.jsonl, and optionally a re-run's endpoints for the endpoint reproducibility gate.
Writes summaries/results.json and prints the report. Parents are the inferential units throughout: for each target the
three walks are summarised within parent by their median, and uncertainty comes from resampling parents.

Usage: python3 scripts/e3_analysis.py <E3 dir with record/ and summaries/> [--rerun-endpoints <endpoints dir>] [--e1-aggregates <aggregates.json>]
"""
import glob, json, math, os, random, statistics, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e3_metrics import total_variation, expected_jaccard

root = sys.argv[1]; opts = dict(zip(sys.argv[2::2], sys.argv[3::2]))
TARGETS = [8, 16, 32, 48, 60]; CLASSES = ["neutral", "altered", "lengthened", "shortened", "lethal"]
P = {p["index"]: p for p in json.load(open(opts.get("--parents", "slopware/experiments/E2/parents.json")))["parents"]}

def load_summaries(tag):
    S = {}
    for f in sorted(glob.glob(f"{root}/record/neighbourhoods/{tag}/summaries-*.jsonl")):
        for l in open(f):
            if l.strip(): s = json.loads(l); S[s["genomeId"]] = s
    return S
def load_sets(tag, ids):
    """non-neutral (pos,val) sets and exact-signature multisets per genome, streamed from placements."""
    M = {g: set() for g in ids}; SIG = {g: collections.Counter() for g in ids}; HF = collections.Counter()
    for f in sorted(glob.glob(f"{root}/record/neighbourhoods/{tag}/placements-*.jsonl")):
        for l in open(f):
            if not l.strip(): continue
            r = json.loads(l); g = r["g"]
            if g not in M: continue
            if r["cls"] == "harness_failure": HF[g] += 1; continue
            if r["cls"] != "neutral": M[g].add((r["pos"], r["val"]))
            if r["sigH"]: SIG[g][r["sigH"]] += 1
    return M, SIG, HF

S = load_summaries("main"); ids = list(S)
M, SIG, HF = load_sets("main", ids)
def dist(a, b):
    pa = {c: S[a]["counts"][c] / S[a]["placeable"] for c in CLASSES}; pb = {c: S[b]["counts"][c] / S[b]["placeable"] for c in CLASSES}
    na, nb = sum(SIG[a].values()), sum(SIG[b].values())
    qa = {k: v / na for k, v in SIG[a].items()} if na else {}; qb = {k: v / nb for k, v in SIG[b].items()} if nb else {}
    return {"D5": total_variation(pa, pb), "Dsig": total_variation(qa, qb), "JS": (len(set(SIG[a]) & set(SIG[b])) / len(set(SIG[a]) | set(SIG[b]))) if (set(SIG[a]) | set(SIG[b])) else 1.0,
            "JM": (len(M[a] & M[b]) / len(M[a] | M[b])) if (M[a] | M[b]) else 1.0, "JM_expected": expected_jaccard(len(M[a]), len(M[b]), 16319)}

# endpoints → parent
parents = [g for g in ids if S[g]["kind"] == "parent"]; endpoints = [g for g in ids if S[g]["kind"] == "endpoint"]
by_parent = collections.defaultdict(lambda: collections.defaultdict(list))   # parentIndex -> target -> [(walk, metrics)]
for e in endpoints:
    s = S[e]; pg = f"P{s['parentIndex']}"
    if pg not in S: continue
    d = dist(e, pg); d["hamming"] = s["hamming"]
    ops = set(S[pg]["selfOps"]); # ancestral expressed region: executed opcode bytes and their immediates, from the parent's own disassembly is not stored; approximate with consumed prefix positions < selfConsumed
    pb = bytes.fromhex(S[pg]["bytes"][2:]); eb = bytes.fromhex(s["bytes"][2:])
    d["expressedHamming"] = sum(1 for i in range(S[pg]["selfConsumed"]) if pb[i] != eb[i])
    d["differs"] = d["Dsig"] > 0 or d["JS"] < 1
    x3 = {"adjacentVariation": 1 - S[e]["counts"]["neutral"] / S[e]["placeable"], "richness": S[e]["distinctSignatures"], "upward": S[e]["upward"] / S[e]["placeable"]}
    x3p = {"adjacentVariation": 1 - S[pg]["counts"]["neutral"] / S[pg]["placeable"], "richness": S[pg]["distinctSignatures"], "upward": S[pg]["upward"] / S[pg]["placeable"]}
    d["x3_diff"] = {k: x3[k] - x3p[k] for k in x3}
    by_parent[s["parentIndex"]][s["target"]].append((s["walk"], d))

rnd = random.Random(3); PI = sorted(by_parent)
def parent_medians(target, key, sub=None):
    out = {}
    for pi in PI:
        vals = [ (m[key] if sub is None else m[key][sub]) for _, m in by_parent[pi].get(target, [])]
        if vals: out[pi] = statistics.median(vals)
    return out
def boot_mean(values_by_parent, n=10000):
    ps = list(values_by_parent); if not ps: return None
    means = []
    for _ in range(n):
        smp = [values_by_parent[rnd.choice(ps)] for _ in ps]; means.append(sum(smp) / len(smp))
    means.sort(); return {"mean": sum(values_by_parent.values()) / len(ps), "ci95": [means[int(0.025 * n)], means[int(0.975 * n)]], "parents": len(ps)}
def spearman(xs, ys):
    # average ranks with ties
    def ranks(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
            for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys); n = len(xs)
    if n < 3: return None
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry)); den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None

res = {"genomes": {"parents": len(parents), "endpoints": len(endpoints)}, "harness": {"placement_failures": sum(HF.values()), "detector_unavailable": sum(S[g].get("detectorUnavailable", 0) for g in ids)}}
# X1
res["X1"] = {}
for key in ("D5", "Dsig"):
    per_t = {t: boot_mean(parent_medians(t, key)) for t in TARGETS}
    xs, ys = [], []
    for t in TARGETS:
        for pi, v in parent_medians(t, key).items(): xs.append(t); ys.append(v)
    rho = spearman(xs, ys)
    # parent bootstrap for rho
    rhos = []
    for _ in range(2000):
        smp = [rnd.choice(PI) for _ in PI]; bx, by = [], []
        for pi in smp:
            for t in TARGETS:
                m = parent_medians(t, key);
                if pi in m: bx.append(t); by.append(m[pi])
        r = spearman(bx, by);
        if r is not None: rhos.append(r)
    rhos.sort()
    res["X1"][key] = {"by_target": per_t, "spearman_rho": rho, "rho_ci95": [rhos[int(0.025 * len(rhos))], rhos[int(0.975 * len(rhos))]] if rhos else None}
# secondary: continuous
res["X1"]["continuous"] = {"hamming_vs_Dsig_rho": spearman([m["hamming"] for pi in PI for t in TARGETS for _, m in by_parent[pi].get(t, [])], [m["Dsig"] for pi in PI for t in TARGETS for _, m in by_parent[pi].get(t, [])]),
                           "expressed_hamming_vs_Dsig_rho": spearman([m["expressedHamming"] for pi in PI for t in TARGETS for _, m in by_parent[pi].get(t, [])], [m["Dsig"] for pi in PI for t in TARGETS for _, m in by_parent[pi].get(t, [])])}
# X2: fraction differing, parent bootstrap
res["X2"] = {}
for t in TARGETS:
    flags = {pi: [m["differs"] for _, m in by_parent[pi].get(t, [])] for pi in PI}
    allf = [f for v in flags.values() for f in v]
    fr = sum(allf) / len(allf) if allf else None
    bs = []
    for _ in range(10000):
        smp = [rnd.choice(PI) for _ in PI]; fl = [f for pi in smp for f in flags[pi]]
        if fl: bs.append(sum(fl) / len(fl))
    bs.sort()
    res["X2"][str(t)] = {"fraction_differing": fr, "ci95_parent_bootstrap": [bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs))]] if bs else None, "JS": boot_mean(parent_medians(t, "JS")), "Dsig": boot_mean(parent_medians(t, "Dsig"))}
# X3
res["X3"] = {t: {k: boot_mean(parent_medians(t, "x3_diff", k)) for k in ("adjacentVariation", "richness", "upward")} for t in TARGETS}
# X4
res["X4"] = {t: {"JM": boot_mean(parent_medians(t, "JM")), "JM_minus_expected": boot_mean({pi: statistics.median([m["JM"] - m["JM_expected"] for _, m in by_parent[pi][t]]) for pi in PI if by_parent[pi].get(t)}), "D5": boot_mean(parent_medians(t, "D5")), "Dsig": boot_mean(parent_medians(t, "Dsig"))} for t in TARGETS}
# X5 detectors
reach_tot = collections.Counter()
for g in ids:
    for k, v in S[g].get("reachCounts", {}).items(): reach_tot[k] += v
res["X5"] = {"children_reaching": dict(reach_tot), "genomes_with_child_has_code": [g for g in ids if S[g].get("reachCounts", {}).get("child_has_code")], "genomes_with_entered_code_call": [g for g in ids if S[g].get("reachCounts", {}).get("external_call_entered_code")]}
# references: signature-matched and lifespan-matched among parents
sig_of = {pi: S[f"P{pi}"]["selfSignature"] for pi in PI if f"P{pi}" in S}; life_of = {pi: S[f"P{pi}"]["selfLifespan"] for pi in sig_of}
ref_sig, ref_life = {}, {}
for pi in sig_of:
    same = [q for q in sig_of if q != pi and sig_of[q] == sig_of[pi]]; samel = [q for q in life_of if q != pi and life_of[q] == life_of[pi]]
    if same: ref_sig[pi] = statistics.median(dist(f"P{pi}", f"P{q}")["Dsig"] for q in same)
    if samel: ref_life[pi] = statistics.median(dist(f"P{pi}", f"P{q}")["Dsig"] for q in samel)
res["references"] = {"signature_matched_Dsig": boot_mean(ref_sig) if ref_sig else None, "signature_matched_parents": len(ref_sig), "lifespan_matched_Dsig": boot_mean(ref_life) if ref_life else None}
# reproducibility check: rep against main, exact agreement expected
R = load_summaries("rep")
if R:
    MR, SIGR, HFR = load_sets("rep", list(R)); mism = []
    for g in R:
        if g in S and (M[g] != MR[g] or SIG[g] != SIGR[g] or S[g]["counts"] != R[g]["counts"]): mism.append(g)
    res["reproducibility"] = {"subset": len(R), "exact": len(R) - len(mism), "mismatching": mism, "passed": not mism}
# endpoint reproducibility gate
if "--rerun-endpoints" in opts:
    def ends(d):
        E = {}
        for f in sorted(glob.glob(f"{d}/endpoints-*.jsonl")):
            for l in open(f):
                if l.strip(): e = json.loads(l);
                if l.strip() and e.get("target") != "end": E[(e["parentIndex"], e["walk"], e["target"])] = e["bytes"]
        return E
    A, B = ends(f"{root}/record/walks"), ends(opts["--rerun-endpoints"]); same = sum(1 for k in B if A.get(k) == B[k])
    res["endpoint_reproducibility"] = {"rerun": len(B), "identical": same, "passed": same == len(B) and len(B) == len(A)}
# cross-harness: E1's class counts for the parents against E3's (exploratory)
if "--e1-aggregates" in opts:
    agg = json.load(open(opts["--e1-aggregates"])); e1 = {q["genotypeId"]: q for q in agg["parents"]}; xs = {}
    for pi in PI:
        gid = P[pi]["genotypeId"]
        if gid in e1 and f"P{pi}" in S:
            tot = [sum(col[i] for col in e1[gid]["perPosition"]) for i in range(5)]; names = agg["classes"]; n1 = sum(tot)
            p1 = {names[i]: tot[i] / n1 for i in range(5)}; p1 = {("altered" if k == "clean" else k): p1.get(k, 0) + (p1.get("clean", 0) if k == "altered" else 0) for k in ("neutral", "altered", "lengthened", "shortened")}
            p3 = {c: S[f"P{pi}"]["counts"][c] / S[f"P{pi}"]["placeable"] for c in CLASSES}
            xs[pi] = total_variation(p1, p3)
    res["cross_harness_E1_vs_E3_D5"] = boot_mean(xs) if xs else None
os.makedirs(f"{root}/summaries", exist_ok=True); json.dump(res, open(f"{root}/summaries/results.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:5000])
