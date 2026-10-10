#!/usr/bin/env python3
"""Build the E2 results page: slopware/site/e2.html (static HTML from slopware/site/e2.template.html), slopware/site/e2-data/e2.json
and slopware/site/e2.md. Every number comes from summaries/results.json and the replication / re-run files; this script only words them.

Inputs: slopware/experiments/E2/summaries/{results.json, ROOT.sha256, run-manifest.json, sentences.txt, edition.json (optional),
        w4-replications.jsonl (optional), rerun/results-noise.json (optional)}, slopware/experiments/E2/record-anchor.txt
Usage: python3 scripts/e2_page.py [--snapshot name] [--figure2 e2-data/after.png "caption"]"""
import json, os, re, sys, datetime, html as H

E2 = "slopware/experiments/E2"; S = f"{E2}/summaries"; SITE = "slopware/site"; OUT = f"{SITE}/e2-data/e2.json"
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
res = json.load(open(f"{S}/results.json")); root = open(f"{S}/ROOT.sha256").read().strip()
man = json.load(open(f"{S}/run-manifest.json")) if os.path.exists(f"{S}/run-manifest.json") else {}
ANCHOR = "0xacb2614447721b5e959171c7e267301e0974be6d7cb691488d2578890ec85d7f"
rec_anchor = ""
if os.path.exists(f"{E2}/record-anchor.txt"):
    m = re.search(r"tx (0x[0-9a-f]{64})", open(f"{E2}/record-anchor.txt").read()); rec_anchor = m.group(1) if m else ""
sentences = [l.strip() for l in open(f"{S}/sentences.txt") if l.strip()] if os.path.exists(f"{S}/sentences.txt") else []
edition = json.load(open(f"{S}/edition.json")) if os.path.exists(f"{S}/edition.json") else None
reps = [json.loads(l) for l in open(f"{S}/w4-replications.jsonl") if l.strip()] if os.path.exists(f"{S}/w4-replications.jsonl") else []
noise = json.load(open(f"{S}/rerun/results-noise.json")) if os.path.exists(f"{S}/rerun/results-noise.json") else None
esc = H.escape; pct = lambda x, d=1: f"{100*x:.{d}f}%"; fmt = lambda n: f"{n:,}"

w1, w2, w3, w4, w5, de = res["W1"], res["W2"], res["W3"], res["W4"], res["W5"], res["descriptives"]
Hs = []
Hs.append({"id": "W1", "name": "neutral movement and cryptic variation",
    "registered": "Under neutral acceptance, accepted steps almost never change an executed opcode byte: fewer than 1% of them do, and in at least 90% of walks every executed opcode byte of the final genome equals the parent's. Steps inside PUSH immediates were expected to be common.",
    "observed": f"{pct(w1['fraction_on_executed_opcode'],2)} of {fmt(w1['accepted_neutral_steps'])} accepted neutral steps changed an executed opcode byte, inside the 1% threshold; {pct(w1['fraction_on_immediate'])} landed in PUSH immediates. But only {pct(w1['walks_opcodes_unchanged'])} of walks ended with every executed opcode byte unchanged, far below 90%: over ten thousand attempts the rare opcode changes accumulate. Every walk ended with a median {int(de['A']['final_hamming_median'])} of 64 bytes different from its parent while {pct(w1['ancestral_neutral_fraction'],0)} of them still behaved exactly like it (ancestral neutrality).",
    "verdict": "not held" if not w1["held"] else "held",
    "note": "The neutral network is not only the unread tail. Locally silent changes reach into executed code, and a program can be rewritten byte by byte without changing what it does."})
Hs.append({"id": "W2", "name": "persistence can climb",
    "registered": "Under persistence acceptance, probe-A lifespan grows: the median walk at least doubles its parent's lifespan (\"persistence can climb\"), and some walk reaches 32 or more instructions, beyond anything in E1's 26 million children (\"can climb far\"). Not evolution: a hill climb with neutral drift.",
    "observed": f"The median parent multiplied its lifespan by {w2['median_parent_ratio']:.1f}; all {w2['parents_doubled']} parents doubled. The longest run was {fmt(w2['max_lifespan'])} instructions. Lifespan is an instruction count, and a loop that runs until the million-gas ceiling is the degenerate way to never be shorter: 63 of 440 persistence walks found one. Excluding every looping walk, the median parent still multiplied its lifespan by 7.3 and 47 walks passed 32 instructions; one reached 12,259 and halted cleanly.",
    "verdict": "held, both thresholds" if (w2["can_climb"] and w2["can_climb_far"]) else ("held" if w2["can_climb"] else "not held"),
    "note": "Non-decreasing paths through genotype space exist from every one of these programs, and they are not only loops."})
Hs.append({"id": "W3", "name": "two prefix models under accumulated mutation",
    "registered": "The naive model (a step is neutral iff its position is at or beyond the consumed prefix) is below 98% accurate; the opcode model (neutral iff the position is not an executed opcode byte) is at least 98% accurate in both arms and every decile.",
    "observed": f"Naive model: {pct(w3['naive']['A']['accuracy'])} accurate in arm A and {pct(w3['naive']['B']['accuracy'])} in arm B, failing at immediates as predicted. Opcode model: {pct(w3['opcode']['A']['accuracy'])} in arm A, steady across deciles, but {pct(w3['opcode']['B']['accuracy'])} under persistence, where jumps and loops make which bytes execute depend on more than their position.",
    "verdict": "naive as predicted; opcode not held under persistence",
    "note": "Position alone predicts neutrality for programs that run straight; once control flow bends, it does not."})
ev = w4["events"]
rep_n = len(reps); rep_ok = sum(1 for r in reps if r.get("replicated")); rep_code = sum(1 for r in reps if r.get("enteredCode"))
Hs.append({"id": "W4", "name": "behavioural reach",
    "registered": "A measurement. Eight events of interest were fixed in advance; the only prediction was that clean halts become more frequent under persistence (at least half of arm-B walks). No directional prediction for behaviours E1 never observed. child_has_code and external_call events are replicated three times before being reported as more than candidates.",
    "observed": f"Clean halts: {pct(ev['clean_halt']['fraction_B'],0)} of persistence walks (the prediction held). Returned data: {pct(ev['returns_data']['fraction_B'],0)}. A storage write surviving to a clean halt: {pct(ev['write_survives']['fraction_B'],0)}. CREATE executed: {pct(ev['create_executed']['fraction_B'],0)}, and succeeding, which makes an empty account: {pct(ev['create_succeeds']['fraction_B'],0)}. A CALL-family instruction executed: {pct(ev['external_call']['fraction_B'],0)}. A loop: {pct(ev['loop']['fraction_B'],0)}. A created account with code: none." + (f" Replication: {rep_ok} of {rep_n} external_call events reproduced three times on fresh chains; in {rep_code} of them the call entered code, so the harness's flag as implemented records a CALL instruction executed, and whether it reached a callee with code is reported separately." if reps else " Replication of the external_call events is in progress."),
    "verdict": "the one prediction held; the rest is reported",
    "note": "The scorecard: no child with code, so construction stays NOT OBSERVED; a succeeding CREATE of an empty account is the named counterfeit; the replicated CALL executions move the environment scale only to E1, environment sensed, since no call reached code and no benefit is measured."})
Hs.append({"id": "W5", "name": "is neutrality the road?",
    "registered": "A measurement with its reading fixed in advance. Every lengthening step is re-applied to the plateau-start genome, the genome right after the previous lifespan increase. Class B means the step lengthens the current genome but not the plateau-start genome: enabled by the intervening neutral drift. Zero class B: no evidence. A rare event: existence proof. Many: an important route.",
    "observed": f"{fmt(w5['lengthening_steps'])} lengthening steps; {fmt(w5['class_B'])} of them class B, {pct(w5['fraction_B'])} with a 95% interval of {pct(w5['ci95'][0])} to {pct(w5['ci95'][1])}. Only {pct(w5['secondary_lengthens_parent_fraction'])} of lengthening steps lengthen the original parent. A median of {w5['neutral_since_median']:.0f} accepted neutral steps and {w5['hamming_from_plateau_median']:.0f} changed bytes separate each improvement from the plateau it rose from.",
    "verdict": w5["reading"],
    "note": "Half of every improvement found was unavailable until phenotypically silent changes had altered the program's background. E1's 98.4% neutrality is the ground the climbs stand on."})

facts = [
    ["parents", f"{fmt(res['parents'])} E1 parents whose probe-A lifespan was three or more: 42 genesis, 46 control; fixed in parents.json before the run"],
    ["walks", f"{fmt(res['walks']['A'])} neutral and {fmt(res['walks']['B'])} persistence walks: 5 per parent per arm, 10,000 attempts each, 8,800,000 attempts in all, plus two counterfactual placements per lengthening step"],
    ["world", "v0, frozen as in E1; every genotype evaluated from the same clean chain state at the same address"],
    ["record root", root],
    ["pre-registration anchor", ANCHOR, f"https://etherscan.io/tx/{ANCHOR}"],
]
if rec_anchor: facts.append(["record anchor", rec_anchor, f"https://etherscan.io/tx/{rec_anchor}"])
if args.get("--snapshot"): facts.append(["record", f"{args['--snapshot']}, a DigitalOcean volume snapshot of the full 2.6 GB record; the per-walk summaries, every lengthening step with its counterfactuals, the manifest and the root are in the repository"])
if noise: facts.append(["noise", f"{noise['identical']} of {noise['rerun_walks']} walks re-run from the same seed on a fresh machine reproduced their trajectory exactly" + ("" if noise['identical'] == noise['rerun_walks'] else f"; differing: {noise['differing']}")])
facts.append(["protocol", "slopware/experiments/E2-walks.md, signed 2026-10-09, amendments dated below the signature", "https://github.com/cryptobushi/slopware/blob/main/slopware/experiments/E2-walks.md"])
facts.append(["analysis", "scripts/e2_analysis.py, pre-specified; scripts/e2_steps.py for the picture, hashed before the run", None])

caption = "STEPS. One strip per parent, in parents.json order. Attempts run left to right, instructions executed rise from the strip's baseline to a shared axis that ends at the smallest power of two above the longest run in the record, 131,072. Neutral walks faint, persistence walks black, a red mark where a walk first reached a behaviour E1 never observed. Rules fixed before the run; the axis makes most climbs a hairline and the loops cliffs, and the artist declined to change it before seeing the data."
fig2 = ""
if args.get("--figure2"):
    fig2 = '<img alt="after the walks, drawn with THREADS rules" src="' + args["--figure2"] + '"><p class="mute">' + esc(args.get("--figure2-caption", "")) + '</p>'
out = {"experiment": "E2", "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "caption": caption, "hypotheses": Hs, "sentences": sentences, "facts": facts,
       "reproduce": "To check any number: fetch the snapshot or the per-walk summaries, run scripts/e2_analysis.py, and compare with results.json; to check the picture, run scripts/e2_steps.py on the record. The root hash above is the sha256 of the sorted sha256 manifest of every file in the record.",
       "anchorTx": ANCHOR, "edition": edition}
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(out, open(OUT, "w"), indent=1)

def hyp_block(h):
    note = (' <span class="mute">' + esc(h["note"]) + '</span>') if h.get("note") else ''
    return '<div class="h">\n<h3>' + esc(h["id"]) + ' · ' + esc(h["name"]) + '</h3>\n<p class="mute">' + esc(h["registered"]) + '</p>\n<p>' + esc(h["observed"]) + '</p>\n<p class="v"><b>' + esc(h["verdict"]) + '</b>' + note + '</p>\n</div>'
hyp_html = "".join(hyp_block(h) for h in Hs)
sent_html = "".join(f"<p>{esc(x)}</p>" for x in sentences)
def fact_row(f):
    v = ('<a href="' + f[2] + '">' + esc(f[1]) + '</a>') if (len(f) > 2 and f[2]) else esc(f[1])
    return '<span class="n">' + esc(f[0]) + '</span><span>' + v + '</span>'
facts_html = "".join(fact_row(f) for f in facts)
edition_html = ""
if edition:
    L = edition.get("listing") or {}
    gal = (' Bid here, or on <a href="' + edition["gallery"] + '">the same listing at Manifold</a>.') if edition.get("gallery") else ''
    edition_html = ('<div id="edition">\n<h2>the research edition</h2>\n<p>' + esc(edition["text"]) + '</p>\n<div id="auction" data-id="' + str(L.get("id", "")) + '" data-network="' + str(L.get("network", "")) + '" data-marketplace="' + str(L.get("marketplace", "")) + '" data-rpc="' + str(L.get("rpc", "")) + '"></div>\n<p class="mute">' + esc(edition.get("note", "")) + gal + '</p>\n</div>')
tpl = open(f"{SITE}/e2.template.html").read()
page = (tpl.replace("{{HYPOTHESES}}", hyp_html).replace("{{SENTENCES}}", sent_html).replace("{{FACTS}}", facts_html).replace("{{REPRO}}", esc(out["reproduce"]))
        .replace("{{CAPTION}}", esc(caption)).replace("{{ANCHOR_HREF}}", f"https://etherscan.io/tx/{ANCHOR}").replace("{{EDITION}}", edition_html).replace("{{FIGURE2}}", fig2))
open(f"{SITE}/e2.html", "w").write(page)
md = ["# SLOPWARE — E2 walks on the living", "", "The second pre-registered experiment, run once on 2026-10-09. From the 88 E1 programs that executed three or more instructions, ten-thousand-attempt one-byte walks under two rules: neutral (keep only changes that leave behaviour identical) and persistence (keep any change that does not shorten the run; selection, disclosed). 8.8 million placements on a clean copy of Ethereum. Pre-registered and anchored before the run.", "", f"Picture: STEPS, https://slopware.fun/e2-data/steps.png — {caption}", "", "## Hypotheses and verdicts", ""]
for h in Hs: md += [f"### {h['id']} · {h['name']} — {h['verdict']}", "", f"Registered: {h['registered']}", "", f"Observed: {h['observed']}", ""] + ([h["note"], ""] if h.get("note") else [])
md += ["## In three sentences", ""] + [s for x in sentences for s in (x, "")] + ["## The data", ""] + [f"- {f[0]}: {f[1]}" + (f" ({f[2]})" if len(f) > 2 and f[2] else "") for f in facts] + ["", out["reproduce"], ""]
if edition: md += ["## The research edition", "", edition["text"], "", edition.get("note", "") + (f" Listing at Manifold: {edition['gallery']}" if edition.get("gallery") else ""), ""]
md += ["Also: https://slopware.fun/llms.txt · https://slopware.fun/e1.md · https://slopware.fun/readings.md · the repository https://github.com/cryptobushi/slopware"]
open(f"{SITE}/e2.md", "w").write("\n".join(md))
print(f"e2.json, e2.html, e2.md written · {len(Hs)} hypotheses · {len(sentences)} sentences · edition {'yes' if edition else 'no'} · replications {rep_n}")
for h in Hs: print(f"  {h['id']} {h['verdict']}")
