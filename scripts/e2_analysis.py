#!/usr/bin/env python3
"""E2 analysis, pre-specified (E2-walks.md §7). Reads record/<arm>/summaries-*.jsonl, record/B/lengthening-*.jsonl and
streams record/<arm>/walks-*.jsonl; writes summaries/results.json and prints the report.

Usage: python3 scripts/e2_analysis.py <E2 dir with record/ and summaries/> [--rerun <dir with record/ of the noise re-run>]
One line per (parent, arm, walk, attempt) is kept: a walk re-run after a machine failure supersedes its partial lines."""
import glob, json, math, statistics, sys, collections

root = sys.argv[1]; rerun = sys.argv[sys.argv.index("--rerun") + 1] if "--rerun" in sys.argv else None
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0, 0.0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h
def load_summaries(base):
    S = {}
    for arm in ("A", "B"):
        for f in sorted(glob.glob(f"{base}/record/{arm}/summaries-*.jsonl")):
            for l in open(f):
                if l.strip(): s = json.loads(l); S[(s["parentIndex"], arm, s["walk"])] = s   # the last complete summary wins
    return S
S = load_summaries(root)
A = [s for s in S.values() if s["arm"] == "A"]; B = [s for s in S.values() if s["arm"] == "B"]
res = {"walks": {"A": len(A), "B": len(B)}, "parents": len({k[0] for k in S})}

# W1 — neutral movement: accepted arm-A steps on executed opcode bytes / inside the naive prefix; executed opcodes unchanged at the end; local vs ancestral neutrality
acc = sum(s["accepted"] for s in A); below = sum(s["acceptedBelowPrefix"] for s in A); on_op = sum(s["acceptedOnOpcode"] for s in A); on_imm = sum(s["acceptedOnImmediate"] for s in A)
res["W1"] = {"accepted_neutral_steps": acc, "accepted_on_executed_opcode": on_op, "fraction_on_executed_opcode": on_op / acc if acc else None,
             "accepted_on_immediate": on_imm, "fraction_on_immediate": on_imm / acc if acc else None, "accepted_below_naive_prefix": below, "fraction_below_naive_prefix": below / acc if acc else None,
             "walks_opcodes_unchanged": sum(1 for s in A if s["opcodesUnchanged"]) / len(A) if A else None, "walks_naive_prefix_unchanged": sum(1 for s in A if s["prefixUnchanged"]) / len(A) if A else None,
             "ancestral_neutral_fraction": sum(1 for s in A if s["ancestralNeutral"]) / len(A) if A else None,
             "held": bool(A) and acc > 0 and on_op / acc < 0.01 and sum(1 for s in A if s["opcodesUnchanged"]) / len(A) >= 0.90}
# W2 — persistence can climb
per_parent = collections.defaultdict(list)
for s in B: per_parent[s["parentIndex"]].append(s["finalLifespan"] / s["parentLifespan"])
ratios = [statistics.median(v) for v in per_parent.values()]
res["W2"] = {"median_parent_ratio": statistics.median(ratios) if ratios else None, "max_lifespan": max((s["maxLifespan"] for s in B), default=None),
             "parents_doubled": sum(1 for r in ratios if r >= 2), "can_climb": bool(ratios) and statistics.median(ratios) >= 2, "can_climb_far": any(s["maxLifespan"] >= 32 for s in B),
             "final_lifespans_B": sorted(collections.Counter(s["finalLifespan"] for s in B).items())}
# W3 — two prefix models, from the per-walk counters (every attempt) and by decile: naive (neutral iff pos >= consumed) and opcode (neutral iff pos is not an executed opcode byte)
tot = {m: {"A": [0, 0], "B": [0, 0]} for m in ("naive", "opcode")}; dec = {m: {"A": [[0, 0] for _ in range(10)], "B": [[0, 0] for _ in range(10)]} for m in ("naive", "opcode")}
for s in S.values():
    a = s["arm"]; tot["naive"][a][0] += s["prefixPredictorRight"]; tot["opcode"][a][0] += s["opcodePredictorRight"]; tot["naive"][a][1] += s["budget"]; tot["opcode"][a][1] += s["budget"]
    for i, d in enumerate(s["prefixPredictorByDecile"]): dec["naive"][a][i][0] += d["right"]; dec["opcode"][a][i][0] += d["right2"]; dec["naive"][a][i][1] += d["n"]; dec["opcode"][a][i][1] += d["n"]
res["W3"] = {m: {a: {"accuracy": tot[m][a][0] / tot[m][a][1] if tot[m][a][1] else None, "by_decile": [r / n if n else None for r, n in dec[m][a]]} for a in ("A", "B")} for m in ("naive", "opcode")}
ok = lambda m: all((tot[m][a][1] and tot[m][a][0] / tot[m][a][1] >= 0.98) for a in ("A", "B")) and all((n == 0 or r / n >= 0.98) for a in ("A", "B") for r, n in dec[m][a])
res["W3"]["naive_held"] = ok("naive"); res["W3"]["opcode_held"] = ok("opcode")
# W4 — behavioural reach (a measurement)
EVENTS = ["clean_halt", "returns_data", "write_survives", "create_executed", "external_call", "create_succeeds", "child_has_code", "loop"]
w4 = {}
for e in EVENTS:
    reached = [s for s in B if e in s["firstReach"]]
    w4[e] = {"walks_B": len(reached), "fraction_B": len(reached) / len(B) if B else None, "first_attempt_median": statistics.median(s["firstReach"][e] for s in reached) if reached else None,
             "walks_A": sum(1 for s in A if e in s["firstReach"])}
res["W4"] = {"events": w4, "clean_halt_in_half_of_B": bool(B) and w4["clean_halt"]["fraction_B"] >= 0.5,
             "replicate": [{"parent": s["parentIndex"], "walk": s["walk"], "event": e, "attempt": s["firstReach"][e]} for s in B for e in ("child_has_code", "external_call") if e in s["firstReach"]]}
# W5 — is neutrality the road: class B among lengthening steps (plateau-start counterfactual)
L = {}
for f in sorted(glob.glob(f"{root}/record/B/lengthening-*.jsonl")):
    for l in open(f):
        if l.strip(): r = json.loads(l); L[(r["p"], r["w"], r["t"])] = r
L = list(L.values()); nB = sum(1 for r in L if r["cls"] == "B"); p5, lo5, hi5 = wilson(nB, len(L))
per = collections.defaultdict(lambda: [0, 0])
for r in L: per[r["p"]][1] += 1; per[r["p"]][0] += r["cls"] == "B"
res["W5"] = {"lengthening_steps": len(L), "class_B": nB, "fraction_B": p5 if L else None, "ci95": [lo5, hi5] if L else None,
             "per_parent_fraction_B": {str(k): v[0] / v[1] for k, v in sorted(per.items())},
             "secondary_lengthens_parent_fraction": sum(1 for r in L if r["lengthensParent"]) / len(L) if L else None,
             "neutral_since_median": statistics.median(r["neutralSince"] for r in L) if L else None,
             "hamming_from_plateau_median": statistics.median(r["hammingFromPlateau"] for r in L) if L else None,
             "reading": "no evidence" if nB == 0 else ("existence proof" if nB <= 2 else "important route")}
# Descriptives — Hamming by arm
res["descriptives"] = {arm: {"final_hamming_median": statistics.median(s["hammingFromParent"] for s in X) if X else None,
                             "hamming_by_thousand": [(statistics.median(v) if (v := [h[i][1] for h in (s["hammingSeries"] for s in X) if len(h) > i]) else None) for i in range(10)] if X else None}
                       for arm, X in (("A", A), ("B", B))}
pairs = [(statistics.median(s["hammingFromParent"] for s in A if s["parentIndex"] == pi), statistics.median(s["hammingFromParent"] for s in B if s["parentIndex"] == pi)) for pi in per_parent if any(s["parentIndex"] == pi for s in A)]
res["descriptives"]["parents_B_travels_less"] = sum(1 for a, b in pairs if b < a) / len(pairs) if pairs else None
# Noise — the re-run walks must match
if rerun:
    R = load_summaries(rerun); same = [k for k in R if k in S and R[k]["finalBytes"] == S[k]["finalBytes"] and R[k]["steps"] == S[k]["steps"]]
    res["noise"] = {"rerun_walks": len(R), "identical": len(same), "differing": [list(k) for k in R if k not in same]}
import os; os.makedirs(f"{root}/summaries", exist_ok=True)
json.dump(res, open(f"{root}/summaries/results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("W4",)}, indent=1)[:6000]); print("W4:", json.dumps(res["W4"]["events"], indent=0)[:1500])
