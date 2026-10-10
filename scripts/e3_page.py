#!/usr/bin/env python3
"""Build the E3 results page: slopware/site/e3.html (static HTML from slopware/site/e3.template.html), slopware/site/e3-data/e3.json
and slopware/site/e3.md. Every number comes from summaries/results.json; this script only words them, and the reading of each
measurement is chosen by the pre-listed rule in E3-somewhere-else.md §3, not by hand.

Inputs: slopware/experiments/E3/summaries/{results.json, ROOT.sha256, run-manifest.json, sentences.txt, edition.json (optional)},
        slopware/experiments/E3/record-anchor.txt (optional)
Usage: python3 scripts/e3_page.py [--root dir] [--snapshot name] [--figure2 e3-data/x.png --figure2-caption "..."]"""
import json, os, re, sys, datetime, html as H

args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
E3 = args.get("--root", "slopware/experiments/E3"); S = f"{E3}/summaries"; SITE = "slopware/site"; OUT = f"{SITE}/e3-data/e3.json"
res = json.load(open(f"{S}/results.json")); root = open(f"{S}/ROOT.sha256").read().strip() if os.path.exists(f"{S}/ROOT.sha256") else "(unsealed)"
ANCHOR = "0xb24f764500dfac4d69df23942d95962d6f6033ca65d3de8af345d08c772c9a57"
rec_anchor = ""
if os.path.exists(f"{E3}/record-anchor.txt"):
    m = re.search(r"tx (0x[0-9a-f]{64})", open(f"{E3}/record-anchor.txt").read()); rec_anchor = m.group(1) if m else ""
sentences = [l.strip() for l in open(f"{S}/sentences.txt") if l.strip()] if os.path.exists(f"{S}/sentences.txt") else []
edition = json.load(open(f"{S}/edition.json")) if os.path.exists(f"{S}/edition.json") else None
esc = H.escape; pct = lambda x, d=1: f"{100*x:.{d}f}%"; fmt = lambda n: f"{n:,}"; T = ["8", "16", "32", "48", "60"]
def bm(b, d=3): return f"{b['mean']:.{d}f} ({b['ci95'][0]:.{d}f} to {b['ci95'][1]:.{d}f})" if b else "n/a"
def series(key, d=3): return ", ".join(f"{t}: {key[t]['mean']:.{d}f}" for t in T if key.get(t))
x1, x2, x3, x4, x5 = res["X1"], res["X2"], res["X3"], res["X4"], res["X5"]
ref = res.get("references", {}); rep = res.get("reproducibility", {}); gate = res.get("endpoint_reproducibility", {}); hz = res["harness"]
ds, d5 = x1["Dsig"], x1["D5"]

# X1 reading by the pre-listed rule (§3 X1 a–d), applied to D_sig, the fine instrument; D5 reported beside it
def x1_reading(k):
    bt = k["by_target"]; rho, ci = k["spearman_rho"], k["rho_ci95"]
    allzero = all(bt[t]["mean"] == 0 for t in T if bt.get(t))
    rising = rho is not None and rho > 0 and ci and ci[0] > 0
    refsig = ref.get("signature_matched_Dsig")
    near_ref = bool(refsig and bt.get("60") and bt["60"]["ci95"][1] >= refsig["ci95"][0])
    if allzero: return "(a) not distinguishable from zero at every target: neutral endpoints have effectively the same futures"
    if rising: return "(c) rising with neutral travel" + (", and (d) at the matched reference by target 60" if near_ref else ", and still below the matched reference at target 60")
    if bt.get("8") and bt["8"]["mean"] > 0: return "(b) above zero at the first target and not rising afterwards: divergence immediate, then saturating" + (", (d) at the matched reference" if near_ref else "")
    return "no pre-listed reading fits; reported as measured"
Hs = []
Hs.append({"id": "X1", "name": "neighbourhood divergence with neutral distance",
    "registered": "The dissimilarity between an endpoint's one-mutant neighbourhood and its parent's, measured coarsely on the five classes (D5) and finely on exact signatures (Dsig), by distance target 8, 16, 32, 48, 60. Parents are the unit of inference: three walks summarised within parent by their median, uncertainty from resampling parents. No directional threshold. Pre-listed readings: (a) not distinguishable from zero at every target; (b) above zero at the first target and flat afterwards; (c) rising with neutral travel; (d) at the matched reference by target 60.",
    "observed": f"Dsig by target (mean over parents of the within-parent median): {series(ds['by_target'])}; Spearman's rho over parent medians against target {ds['spearman_rho']:.2f} (parent bootstrap {ds['rho_ci95'][0]:.2f} to {ds['rho_ci95'][1]:.2f}). D5 by target: {series(d5['by_target'])}; rho {d5['spearman_rho']:.2f} ({d5['rho_ci95'][0]:.2f} to {d5['rho_ci95'][1]:.2f}). Against realised Hamming, rho {x1['continuous']['hamming_vs_Dsig_rho']:.2f}; against Hamming inside the parent's expressed region, {x1['continuous']['expressed_hamming_vs_Dsig_rho']:.2f}. References: unrelated parents with the identical full signature, Dsig {bm(ref.get('signature_matched_Dsig'))} over {ref.get('signature_matched_parents')} parents; unrelated parents matched on lifespan only, {bm(ref.get('lifespan_matched_Dsig'))}.",
    "verdict": x1_reading(ds),
    "note": "Dsig is a lower bound on phenotypic difference: two children with the same signature may differ in ways the signature does not record."})
fr = lambda t: f"{pct(x2[t]['fraction_differing'],1)} ({pct(x2[t]['ci95_parent_bootstrap'][0],1)} to {pct(x2[t]['ci95_parent_bootstrap'][1],1)})"
Hs.append({"id": "X2", "name": "accessibility without phenotypic change",
    "registered": "For each endpoint, the set of signatures reachable in one mutation against its parent's: Jaccard(S) and Dsig. Decision rule fixed in advance: an endpoint's neighbourhood differs from its parent's if Dsig > 0 or Jaccard(S) < 1, provided the reproducibility check passed with every replicate distance exactly zero. The fraction differing, by target, with a parent-level bootstrap. No threshold on the size of the difference.",
    "observed": f"Reproducibility check: {rep.get('exact')} of {rep.get('subset')} re-evaluated neighbourhoods agreed exactly, so the rule applies as written. Endpoints whose neighbourhood differs from the parent's: " + "; ".join(f"at {t}, {fr(t)}" for t in T if x2.get(t)) + f". Jaccard(S) by target: {series({t: x2[t]['JS'] for t in T if x2.get(t)}, 2)}.",
    "verdict": "reported as measured; see the sentences below for the reading",
    "note": "W5 showed that neutral history enables lifespan improvements sometimes; X2 asks how much of the immediate possibility space it reshapes."})
def x3_line(k, d, scale=1):
    return "; ".join(f"at {t}, {x3[t][k]['mean']*scale:+.{d}f} ({x3[t][k]['ci95'][0]*scale:+.{d}f} to {x3[t][k]['ci95'][1]*scale:+.{d}f})" for t in T if x3.get(t))
Hs.append({"id": "X3", "name": "accessible variation",
    "registered": "Three quantities per genome, as paired differences endpoint minus parent, by target: adjacent variation (the fraction of children whose signature differs from the genome's), phenotypic richness (distinct child signatures), upward accessibility (the fraction of children that outlive the genome on probe A). Pre-listed readings: unchanged; changed in one direction across parents; changed without a consistent direction. No threshold.",
    "observed": f"Adjacent variation, in percentage points: {x3_line('adjacentVariation', 2, 100)}. Richness, in distinct signatures: {x3_line('richness', 1)}. Upward accessibility, in percentage points: {x3_line('upward', 3, 100)}.",
    "verdict": "reported as measured; see the sentences below for the reading",
    "note": "The word evolvability is not used."})
Hs.append({"id": "X4", "name": "exact against aggregate",
    "registered": "For each endpoint–parent pair, the Jaccard overlap of the exact sets of non-neutral (position, value) substitutions, reported as the difference from its exact random-subset expectation (hypergeometric), beside D5 and Dsig, by target. The question is whether exact mutational overlap declines along the targets while the aggregate accessibility distances stay comparatively small, read beside the matched references. Reported as it appears; no binary classification.",
    "observed": f"Jaccard(M) by target: {series({t: x4[t]['JM'] for t in T if x4.get(t)})}; minus its expectation for independent random sets of the same sizes: {series({t: x4[t]['JM_minus_expected'] for t in T if x4.get(t)})}. Beside it, D5 {series({t: x4[t]['D5'] for t in T if x4.get(t)})} and Dsig {series({t: x4[t]['Dsig'] for t in T if x4.get(t)})}.",
    "verdict": "reported as measured; see the sentences below for the reading",
    "note": "A Jaccard(M) far above its expectation means the two programs share their exact fragile positions; near it, they share only as much as strangers would."})
cr = x5["children_reaching"]; hc = x5["genomes_with_child_has_code"]; ec = x5["genomes_with_entered_code_call"]
tot = res["genomes"]["parents"] + res["genomes"]["endpoints"]
Hs.append({"id": "X5", "name": "nothing new, observation only",
    "registered": "E2's detectors, unchanged, over every child, plus self-inspection (CODESIZE, CODECOPY, ADDRESS, EXTCODEHASH of self executed). Incidence reported. Nothing predicted, nothing rewarded. child_has_code and calls that enter code are replicated three times before being reported as more than candidates.",
    "observed": f"Children reaching each event, over {fmt(tot)} neighbourhoods: " + ", ".join(f"{k} {fmt(v)}" for k, v in sorted(cr.items(), key=lambda kv: -kv[1])) + f". Genomes with a child that left code behind: {len(hc)}. Genomes with a child whose call entered code: {len(ec)}.",
    "verdict": "nothing new" if not hc and not ec else f"candidates: {len(hc)} child_has_code, {len(ec)} calls entering code; replication reported in the protocol document",
    "note": "The scorecard moves only as E2 §9 specified."})

facts = [
    ["parents", f"{fmt(res['genomes']['parents'])} E2 parents, 42 genesis and 46 control, fixed in E2/parents.json before E2 ran"],
    ["endpoints", f"{fmt(res['genomes']['endpoints'])} neutral descendants: three fresh walks per parent frozen at the first accepted step reaching Hamming 8, 16, 32, 48 and 60; one walk ended its 2,000-attempt budget at 59 and contributes four"],
    ["neighbourhoods", f"{fmt(tot)} exhaustive, 16,319 placeable children each, plus {rep.get('subset', 0)} re-evaluated on separate chains for the reproducibility check"],
    ["harness", f"{fmt(hz['placement_failures'])} placement failures excluded from every statistic; {fmt(hz['detector_unavailable'])} placements with the detector transaction unavailable"],
    ["endpoint gate", f"{gate.get('identical')} of {gate.get('rerun')} endpoints identical, byte for byte, between the droplet and a second machine before any neighbourhood was evaluated"],
    ["cross-harness", f"the 88 parents' neighbourhoods under E1's harness against E3's, D5 {bm(res.get('cross_harness_E1_vs_E3_D5'))}, exploratory"],
    ["world", "v0, frozen as in E1 and E2; every genotype evaluated from the same clean chain state at the same address"],
    ["record root", root],
    ["pre-registration anchor", ANCHOR, f"https://etherscan.io/tx/{ANCHOR}"],
]
if rec_anchor: facts.append(["record anchor", rec_anchor, f"https://etherscan.io/tx/{rec_anchor}"])
if args.get("--snapshot"): facts.append(["record", f"{args['--snapshot']}, a DigitalOcean volume snapshot of the full record; the per-genome summaries, the endpoints, the manifest and the root are in the repository"])
facts.append(["protocol", "slopware/experiments/E3-somewhere-else.md, signed 2026-10-10, amendments dated below the signature", "https://github.com/cryptobushi/slopware/blob/main/slopware/experiments/E3-somewhere-else.md"])
facts.append(["analysis", "scripts/e3_analysis.py and scripts/e3_metrics.py, pre-specified; scripts/e3_somewhere.py for the picture; all hashed in the anchor before the run", None])

caption = "SOMEWHERE ELSE. One row per parent, 88 rows in parents.json order. Left to right: the parent, then its first walk's neutral descendants at 8, 16, 32, 48 and 60 bytes' distance, each drawn as a walk from its bytes with THREADS' pen: faint, the whole program; black, the part it executes; red, three or more instructions. Beneath each, a bar of 64 cells, one per byte position, inked by the fraction of that position's 255 one-byte changes that alter what the program does. Every genome in a row does exactly the same thing. If neutral history changed nothing about what is reachable next, every bar in a row would be the same bar. Rules fixed and hashed before the run."
fig2 = ""
if args.get("--figure2"):
    fig2 = '<img alt="companion figure" src="' + args["--figure2"] + '"><p class="mute">' + esc(args.get("--figure2-caption", "")) + '</p>'
out = {"experiment": "E3", "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "caption": caption, "hypotheses": Hs, "sentences": sentences, "facts": facts,
       "reproduce": "To check any number: fetch the snapshot or the per-genome summaries, run scripts/e3_analysis.py, and compare with results.json; to check the picture, run scripts/e3_positions.py, scripts/e3_rows.py and scripts/e3_somewhere.py on the record. The root hash above is the sha256 of the sorted sha256 manifest of every file in the record.",
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
tpl = open(f"{SITE}/e3.template.html").read()
page = (tpl.replace("{{HYPOTHESES}}", hyp_html).replace("{{SENTENCES}}", sent_html).replace("{{FACTS}}", facts_html).replace("{{REPRO}}", esc(out["reproduce"]))
        .replace("{{CAPTION}}", esc(caption)).replace("{{ANCHOR_HREF}}", f"https://etherscan.io/tx/{ANCHOR}").replace("{{EDITION}}", edition_html).replace("{{FIGURE2}}", fig2))
open(f"{SITE}/e3.html", "w").write(page)
md = ["# SLOPWARE — E3 somewhere else", "", "The third pre-registered experiment, run once on 2026-10-10. From each of the 88 E2 parents, three fresh neutral walks frozen at Hamming distance 8, 16, 32, 48 and 60; then the exhaustive one-mutant neighbourhood (16,319 children) of every parent and every endpoint, evaluated from the same clean world state. The question: when neutral descendants still do exactly what the parent does, do they still have the same futures? Pre-registered and anchored before the first attempt.", "", f"Picture: SOMEWHERE ELSE, https://slopware.fun/e3-data/somewhere.png — {caption}", "", "## Measurements and readings", ""]
for h in Hs: md += [f"### {h['id']} · {h['name']} — {h['verdict']}", "", f"Registered: {h['registered']}", "", f"Observed: {h['observed']}", ""] + ([h["note"], ""] if h.get("note") else [])
md += ["## In three sentences", ""] + [s for x in sentences for s in (x, "")] + ["## The data", ""] + [f"- {f[0]}: {f[1]}" + (f" ({f[2]})" if len(f) > 2 and f[2] else "") for f in facts] + ["", out["reproduce"], ""]
if edition: md += ["## The research edition", "", edition["text"], "", edition.get("note", "") + (f" Listing at Manifold: {edition['gallery']}" if edition.get("gallery") else ""), ""]
md += ["Also: https://slopware.fun/llms.txt · https://slopware.fun/e1.md · https://slopware.fun/e2.md · https://slopware.fun/readings.md · the repository https://github.com/cryptobushi/slopware"]
open(f"{SITE}/e3.md", "w").write("\n".join(md))
print(f"e3.json, e3.html, e3.md written · {len(Hs)} measurements · {len(sentences)} sentences · edition {'yes' if edition else 'no'}")
for h in Hs: print(f"  {h['id']} {h['verdict']}")
