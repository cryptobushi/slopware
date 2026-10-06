#!/usr/bin/env python3
"""Pull the rare behaviors out of a run: loops, persistent writes, executed calls/creates,
returns, input-dependence. Usage: python3 scripts/rare.py <run-id>"""
import json, sys, collections

run = sys.argv[1]
rows = [json.loads(l) for l in open(f"results/{run}/specimens.jsonl")]
born = [r for r in rows if r["birth"]["status"] == "deployed"]
print(f"{run}: {len(rows):,} specimens, {len(born):,} installed")

def trace(p, n=16):
    ops = p["ops"]
    return " ".join(ops[:n]) + (f" … (+{len(ops)-n})" if len(ops) > n else "")

def show(r, label):
    p = max(r["probes"], key=lambda p: p["instructionCount"])
    rd = p["returnData"]
    rd = (rd if len(rd) <= 40 else rd[:34] + f"…({p['returnDataLength']} B)") if p["returnDataLength"] else ""
    print(f"  #{r['id']} [{label}] {r['classification']['primary']} · {p['instructionCount']} instr · {p['outcome']} {rd}")
    print(f"      {r['bytecode']}")
    print(f"      {trace(p)}")
    if r.get("oog"):
        for g in r["oog"]:
            print(f"      sweep {g['gas']:>10,} → {g['outcome']} {('instr '+str(g['instructions'])) if g.get('instructions') is not None else ''} {('LOOP '+g['loopSignature']) if g.get('loopSignature') else ''}")

def has(r, t): return t in r["classification"]["traits"]

# loops: an OOG probe that executed many instructions (appetite OOGs die within a handful)
loops = [r for r in born if any(p["outcome"] == "out_of_gas" and p["instructionCount"] > 32 for p in r["probes"])]
print(f"\nLOOPS (OOG after >32 instructions): {len(loops)}")
for r in loops[:10]: show(r, "LOOP")

# persistent writes: SSTORE executed in a probe that then halted cleanly
pw = [r for r in born if any(p["outcome"] == "success" and p["opCounts"].get("SSTORE", 0) > 0 for p in r["probes"])]
print(f"\nPERSISTENT WRITES (SSTORE executed, clean halt): {len(pw)}")
for r in pw[:10]: show(r, "SSTORE+halt")

tw = [r for r in born if any(p["outcome"] == "success" and p["opCounts"].get("TSTORE", 0) > 0 for p in r["probes"])]
print(f"\nTRANSIENT WRITES with clean halt: {len(tw)}")

calls = [r for r in born if has(r, "EXTERNAL_CALL")]
print(f"\nEXECUTED CALLS: {len(calls)}")
for r in calls[:5]: show(r, "CALL")
creates = [r for r in born if has(r, "CONTRACT_CREATION_ATTEMPT")]
print(f"\nEXECUTED CREATE: {len(creates)}")
for r in creates[:5]: show(r, "CREATE")

ret = [r for r in born if has(r, "RETURNS_DATA")]
print(f"\nRETURNS DATA: {len(ret)}")
for r in ret[:10]: show(r, "RETURN")

def instrument_ok(r): return all(not (p.get("error") or "").startswith("instrument:") for p in r["probes"])
def sig(p): return (p["outcome"], p["instructionCount"], p["returnData"])
def dep(r, names):
    ps = [p for p in r["probes"] if p["name"][0] in names and not (p.get("error") or "").startswith("instrument:")]
    return len(ps) > 1 and len({sig(p) for p in ps}) > 1
cd = [r for r in born if dep(r, "ABCD")]
vd = [r for r in born if dep(r, "AE") and not dep(r, "ABCD")]
bad = [r for r in born if not instrument_ok(r)]
print(f"\nprobes lost to the instrument (BlockOutOfRange etc.): {len(bad)} specimens")
print(f"\nCALLDATA-DEPENDENT: {len(cd)}   VALUE-DEPENDENT: {len(vd)}")
for r in (cd + vd)[:10]:
    print(f"  #{r['id']} {r['bytecode']}")
    for p in r["probes"]: print(f"      {p['name']:18s} {p['outcome']:15s} {p['instructionCount']:>4} instr  ret {p['returnDataLength']} B  {trace(p, 10)}")

rev = [r for r in born if has(r, "REVERTS")]
logs = [r for r in born if has(r, "EMITS_LOG")]
br = [r for r in born if has(r, "BRANCHING")]
print(f"\nREVERTS: {len(rev)}  EMITS_LOG: {len(logs)}  BRANCHING: {len(br)}")
for r in br[:5]: show(r, "BRANCH")

lives = collections.Counter(r["probes"][0]["instructionCount"] for r in born if r["probes"])
tail = {k: v for k, v in sorted(lives.items()) if k >= 6}
print(f"\nlifespan tail (probe A, >=6 instructions): {tail}")
top = sorted(born, key=lambda r: -r["score"]["total"])[:5]
print("\nTOP SCORES")
for r in top: show(r, f"score {r['score']['total']}")
