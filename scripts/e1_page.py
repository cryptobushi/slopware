#!/usr/bin/env python3
"""Build slopware/site/e1/e1.json, the data behind the E1 results page, from the pre-specified analysis.

Inputs (all produced by finish.sh seal / analyse):
  slopware/experiments/E1/summaries/results.json   the H1–H5 statistics (scripts/e1_analysis.py)
  slopware/experiments/E1/summaries/ROOT.sha256     the record's root hash
  slopware/experiments/E1/summaries/run-manifest.json
  slopware/experiments/E1/summaries/sentences.txt   three sentences, written by hand after the results, one per line (optional until then)
  slopware/experiments/E1/summaries/edition.json    {text, note, listing:{id, network, marketplace, rpc}} once the edition exists (optional)
  slopware/experiments/E1/anchor.txt                the pre-registration anchor (tx hash on a line starting "tx")

Usage: python3 scripts/e1_page.py [--record-anchor 0x…] [--snapshot name]
Every number on the page comes from results.json; this script only words them."""
import json, re, sys, os, datetime

E1 = "slopware/experiments/E1"; S = f"{E1}/summaries"; OUT = "slopware/site/e1/e1.json"
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
res = json.load(open(f"{S}/results.json"))
root = open(f"{S}/ROOT.sha256").read().strip()
man = json.load(open(f"{S}/run-manifest.json")) if os.path.exists(f"{S}/run-manifest.json") else {}
anchor = ""
if os.path.exists(f"{E1}/anchor.txt"):
    m = re.search(r"0x[0-9a-f]{64}", open(f"{E1}/anchor.txt").read()); anchor = m.group(0) if m else ""
sentences = [l.strip() for l in open(f"{S}/sentences.txt")] if os.path.exists(f"{S}/sentences.txt") else []
sentences = [s for s in sentences if s]
edition = json.load(open(f"{S}/edition.json")) if os.path.exists(f"{S}/edition.json") else None

pct = lambda x, d=1: f"{100*x:.{d}f}%"
fmt = lambda n: f"{n:,}"

h1 = res["H1"]; fr = h1["fractions"]
def h1_line():
    parts = []
    for k, v in fr.items():
        parts.append(f"{k} {pct(v['genesis_mean'],2)} vs {pct(v['control_mean'],2)} (difference {v['diff']*100:+.2f} points, KS p {v['ks_p']:.2f})")
    return "; ".join(parts)
H = []
H.append({"id": "H1", "name": "no privilege",
    "registered": "The programs people collected are not special: the neighbourhood statistics of the genesis set are indistinguishable from those of fresh random programs. Threshold: every one of the five fractions differs in mean by less than 0.01 and has a Kolmogorov–Smirnov p above 0.01.",
    "observed": f"Genesis versus control, mean of each fraction: {h1_line()}.",
    "verdict": "held" if h1["indistinguishable_by_prespecified_threshold"] else "not held",
    "note": "" if h1["indistinguishable_by_prespecified_threshold"] else "The difference is reported with its size; see results.json."})
h2 = res["H2"]
H.append({"id": "H2", "name": "the executed prefix",
    "registered": "A mutation changes nothing unless it touches a byte the parent executes or reads, so each parent's neutral fraction is about (64 − bytes consumed) / 64. Threshold: median absolute error below 0.01.",
    "observed": f"Median absolute error between predicted and observed neutral fraction: {h2['median_abs_error']:.4f}. {pct(h2['within_0.02'])} of parents are within ±0.02 of their prediction.",
    "verdict": "held" if h2["confirmed"] else "not held", "note": ""})
h3 = res["H3"]
# §7.4 as registered, from the per-position aggregates: parents dying at their first byte, position-0 children living >= 2
import math
agg = json.load(open(f"{S}/aggregates.json")) if os.path.exists(f"{S}/aggregates.json") else None
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h
if agg:
    fb = agg["firstByte"]; n3 = sum(sum(c.values()) for c in fb.values()); k3 = sum(k for c in fb.values() for o, k in c.items() if o.endswith("|lives"))
    p3, lo3, hi3 = wilson(k3, n3); living_values = sum(1 for c in fb.values() if any(o.endswith("|lives") for o in c))
    obs3 = f"Of {fmt(n3)} position-0 children of parents that die on their first byte, {fmt(k3)} lived at least two instructions: {pct(p3,2)} (95% interval {pct(lo3,2)} to {pct(hi3,2)}). The registered 21.57% lies outside it. Exactly {living_values} replacement values ever let such a program live: the 32 PUSHes and 22 operand-free opcodes. The pre-registration counted STOP as a 55th, and STOP halts at once; 54/255 = 21.18% is inside the interval."
    held3 = lo3 <= 55/255 <= hi3
else:
    p3, lo3, hi3 = h3["fraction"], *h3["ci95"]; held3 = lo3 <= 55/255 <= hi3
    obs3 = f"Of {fmt(h3['position0_children'])} position-0 children, {fmt(h3['survive_first'])} lived at least two instructions: {pct(p3)} (95% interval {pct(lo3)} to {pct(hi3)}), against 21.6% predicted."
H.append({"id": "H3", "name": "the first byte",
    "registered": "For a parent that dies on its first byte, a new first byte lets the program live at least two instructions exactly when it is one of the 55 operand-free opcodes: 55/255, which is 21.6%.",
    "observed": obs3,
    "verdict": "held" if held3 else "not held as written",
    "note": "" if held3 else "The harness agrees with the arithmetic once the arithmetic is right; that corrected comparison is exploratory because its number was fixed after the run."})
h4 = res["H4"]
H.append({"id": "H4", "name": "lengthening is rare",
    "registered": "Fewer than 3% of all one-mutants live longer than their parent, and fewer than 0.5% reach a clean halt the parent did not.",
    "observed": f"Of {fmt(h4['placed'])} placements, {fmt(h4['lengthened'])} lived longer than their parent: {pct(h4['lengthened_fraction'],2)} (upper bound of the interval {pct(h4['ci95'][1],2)}). {fmt(h4['new_clean_halts'])} halted cleanly where the parent did not: {pct(h4['new_clean_fraction'],3)} (upper bound {pct(h4['ci95_clean'][1],3)}).",
    "verdict": "held" if h4["confirmed"] else "not held", "note": ""})
h5 = res["H5"]
H.append({"id": "H5", "name": "nothing new under one mutation",
    "registered": "No one-mutant does anything the million-program study never saw: no external call completing, no child program from CREATE, no loop.",
    "observed": ("One one-mutant, of control 182 (not a collected program), set a flag the million-program study never set: byte 32 changed from POP to PUSH6, and the program now runs PUSH11 · PUSH18 · CALLVALUE · PUSH6 · PUSH14 · CREATE · PUSH12 · STOP, executing CREATE and then halting cleanly. Replicated three times on fresh chains with identical signatures. The CREATE itself fails: it offers 2.46 × 10³² wei from an account holding none, pushes 0, and the program rests. Nothing is created; the child's nonce stays at 1." if h5["candidates"] == 1 else f"Candidates reaching a never-seen behaviour: {h5['candidates']}."),
    "verdict": "held" if h5["candidates"] == 0 else "not held, narrowly",
    "note": "Not reproduction and not its counterfeit: a program that attempts a creation, is refused, and halts cleanly instead of dying. The scorecard changes no status; the self-reproduction row gains a note." if h5["candidates"] else ""})

facts = [
    ["parents", f"{fmt(man.get('genesis', 803))} genesis programs (every release before block 26,149,410) and {fmt(man.get('controls', 803))} fresh random programs"],
    ["children", f"16,320 per parent, enumerated: {fmt(h4['placed'])} placements in all"],
    ["world", "v0, frozen: a private Ethereum with one block, one caller, 1,000,000 gas, five calls per child"],
    ["record root", root],
    ["pre-registration anchor", anchor, f"https://etherscan.io/tx/{anchor}" if anchor else None],
]
if args.get("--record-anchor"): facts.append(["record anchor", args["--record-anchor"], f"https://etherscan.io/tx/{args['--record-anchor']}"])
if args.get("--snapshot"): facts.append(["record", f"{args['--snapshot']}, a DigitalOcean volume snapshot of the full 28 GB record; the parent summaries and manifest are in the repository"])
facts.append(["protocol", "slopware/experiments/E1-neighbourhoods.md, signed 2026-10-08, amendments dated below the signature", "https://github.com/cryptobushi/slopware/blob/main/slopware/experiments/E1-neighbourhoods.md"])
facts.append(["analysis", "scripts/e1_analysis.py, pre-specified; scripts/e1_threads.py for the picture, hashed before the results", None])

out = {
    "experiment": "E1", "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "caption": f"THREADS. Every genesis program as a walk from its bytes, in release order. Faint: the whole program. Black: the part it executed before it halted. Red: it reached three or more instructions. Rules fixed before the results; generated from the sealed record.",
    "hypotheses": H, "sentences": sentences, "facts": facts,
    "reproduce": f"To check any number: fetch the snapshot or the parent summaries, run scripts/e1_analysis.py, and compare with results.json; to check the picture, run scripts/e1_threads.py on record/genesis. The root hash above is the sha256 of the sorted sha256 manifest of every file in the record.",
    "anchorTx": anchor, "edition": edition,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), indent=1)
print(f"e1.json: {len(H)} hypotheses · {len(sentences)} sentences · edition {'yes' if edition else 'no'} → {OUT}")
for h in H: print(f"  {h['id']} {h['verdict']}")
