#!/usr/bin/env python3
"""Write slopware/site/lab.json from the runs in results/. Facts only; the site renders them.
Usage: python3 scripts/lab_json.py <run-id> [<run-id> ...]   (the first is the headline run)"""
import json, sys, collections, os

runs = sys.argv[1:] or ["deep-1m-64b"]
def load(run):
    rows = []
    with open(f"results/{run}/specimens.jsonl") as f:
        for l in f:
            r = json.loads(l)
            # keep only what the summary needs; records can be millions
            rows.append({
                "born": r["birth"]["status"] == "deployed",
                "reason": r["birth"].get("reason", ""),
                "probes": [{"o": p["outcome"], "n": p["instructionCount"], "ret": p["returnDataLength"], "err": p.get("error") or "", "sstore": (p.get("opCounts") or {}).get("SSTORE", 0), "tstore": (p.get("opCounts") or {}).get("TSTORE", 0)} for p in r["probes"]],
                "traits": r["classification"]["traits"],
            })
    return rows

head = runs[0]
rows = load(head)
born = [r for r in rows if r["born"]]
observed = len(rows)
probes = [p for r in born for p in r["probes"]]
first_instr = sum(1 for r in born if r["probes"] and r["probes"][0]["n"] <= 1 and r["probes"][0]["o"] != "success")
def has(t): return sum(1 for r in born if t in r["traits"])
def dep(r, names):
    ps = [p for p in r["probes"] if p and not p["err"].startswith("instrument:")]
    sig = lambda p: (p["o"], p["n"], p["ret"])
    return len(ps) > 1 and len({sig(p) for p in ps}) > 1
listened = sum(1 for r in born if dep(r, "ABCD"))
remembered = sum(1 for r in born if any(p["o"] == "success" and p["sstore"] > 0 for p in r["probes"]))
reproduced = has("CONTRACT_CREATION_ATTEMPT")
external_calls = has("EXTERNAL_CALL")
returned = has("RETURNS_DATA")
oog = has("OUT_OF_GAS")
longest = max((p["n"] for p in probes), default=0)
lives = collections.Counter(r["probes"][0]["n"] for r in born if r["probes"])
survive1 = 1 - first_instr / len(born)
rejected = sum(1 for r in rows if not r["born"])
success = sum(1 for p in probes if p["o"] == "success")
fm = collections.Counter(p["o"] for p in probes)
pct = lambda a, b: f"{100*a/b:.1f}%" if b else "—"

# numbers only; the words live on the site
out = {"observed": observed, "run": head, "installed": len(born), "rejected": rejected,
       "numbers": {"first_instruction_deaths": first_instr, "listened": listened, "remembered": remembered, "reproduced": reproduced, "external_calls": external_calls, "returned": returned, "out_of_gas": oog, "longest_life": longest, "calls": len(probes), "clean_halts": success, "failure_modes": dict(fm), "lifespan": {str(k): v for k, v in sorted(lives.items())}}}
os.makedirs("slopware/site", exist_ok=True)
with open("slopware/site/lab.json", "w") as f: json.dump(out, f, indent=1)
print(json.dumps(out, indent=1))
