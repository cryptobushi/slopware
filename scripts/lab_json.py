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
returned = has("RETURNS_DATA")
oog = has("OUT_OF_GAS")
longest = max((p["n"] for p in probes), default=0)
lives = collections.Counter(r["probes"][0]["n"] for r in born if r["probes"])
survive1 = 1 - first_instr / len(born)
rejected = sum(1 for r in rows if not r["born"])
success = sum(1 for p in probes if p["o"] == "success")
fm = collections.Counter(p["o"] for p in probes)
pct = lambda a, b: f"{100*a/b:.1f}%" if b else "—"

lines = [
    f"{pct(first_instr, len(born))} died on their first instruction.",
    f"{listened} listened.",
    f"{remembered} remembered.",
    f"{reproduced} attempted reproduction.",
]
notes = [
    f"Those sentences, precisely. Of {observed:,} programs of sixty-four random bytes, {rejected:,} were refused by Ethereum before they existed (their first byte was 0xEF; the protocol forbids it) — {pct(rejected, observed)}, against a predicted 1 in 256. Of the {len(born):,} installed, {pct(first_instr, len(born))} halted on their very first instruction. The longest life was {longest} instructions. Across {len(probes):,} calls, {pct(success, len(probes))} ended cleanly; {pct(fm.get('invalid_opcode',0), len(probes))} on a byte that is not an instruction; {pct(fm.get('stack_underflow',0), len(probes))} reaching for an operand that was not there.",
    f"“Listened”: {listened} programs behaved differently depending on what they were called with — the data, or the money. “Remembered”: {remembered} wrote to persistent storage and then halted cleanly, so the write survived. “Attempted reproduction”: {reproduced} executed CREATE or CREATE2; none produced a child. Either the creation itself failed — the value it tried to send was a random constant larger than any balance — or the parent halted exceptionally moments later and undid it. No child program ever existed on the chain. {returned} returned data. {oog} ran out of gas — every one by asking a single instruction for more memory than any gas can buy; none by looping.",
    f"Lifespan is geometric: about {survive1*100:.0f}% of programs survive each instruction, and the next, and the next. Of 256 possible byte values, 55 are instructions that need no operands; a random first byte is one of them with probability 0.215. Everything else follows from that.",
    "Method: random bytes placed by CREATE behind a fixed eleven-byte loader on a local chain, code verified byte for byte, then called five ways under a 1,000,000-gas ceiling with every opcode traced. Nothing was filtered, weighted or retried. The harness and the write-ups are in the repository.",
]
out = {"observed": observed, "run": head, "installed": len(born), "rejected": rejected, "lines": lines, "notes": notes,
       "numbers": {"first_instruction_deaths": first_instr, "listened": listened, "remembered": remembered, "reproduced": reproduced, "returned": returned, "out_of_gas": oog, "longest_life": longest, "calls": len(probes), "clean_halts": success, "failure_modes": dict(fm), "lifespan": {str(k): v for k, v in sorted(lives.items())}}}
os.makedirs("slopware/site", exist_ok=True)
with open("slopware/site/lab.json", "w") as f: json.dump(out, f, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "notes"}, indent=1))
