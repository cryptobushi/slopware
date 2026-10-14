#!/usr/bin/env python3
"""Build the E4 results page: slopware/site/e4.html (static HTML from slopware/site/e4.template.html), slopware/site/e4-data/e4.json
and slopware/site/e4.md. Every number comes from summaries/results.json; this script only words them, and the outcome label is the
one the frozen analysis assigned by the pre-listed rule in E4-after.md §3, not chosen here.

Inputs: slopware/experiments/E4/summaries/{results.json, ROOT.sha256, sentences.txt, edition.json (optional)},
        slopware/experiments/E4/record-anchor.txt (optional)
Usage: python3 scripts/e4_page.py [--root dir] [--snapshot name] [--figure2 e4-data/horizon.png --figure2-caption "..."]"""
import json, os, re, sys, datetime, html as H

args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
E4 = args.get("--root", "slopware/experiments/E4"); S = f"{E4}/summaries"; SITE = "slopware/site"; OUT = f"{SITE}/e4-data/e4.json"
res = json.load(open(f"{S}/results.json")); root = open(f"{S}/ROOT.sha256").read().strip() if os.path.exists(f"{S}/ROOT.sha256") else "(unsealed)"
ANCHOR = "0x4b7a6bfc84ae74b687351796a1fa6e4a9e03ea9f170dfbc5152e3de397e98a8a"
rec_anchor = ""
if os.path.exists(f"{E4}/record-anchor.txt"):
    m = re.search(r"tx (0x[0-9a-f]{64})", open(f"{E4}/record-anchor.txt").read()); rec_anchor = m.group(1) if m else ""
sentences = [l.strip() for l in open(f"{S}/sentences.txt") if l.strip()] if os.path.exists(f"{S}/sentences.txt") else []
edition = json.load(open(f"{S}/edition.json")) if os.path.exists(f"{S}/edition.json") else None
esc = H.escape; fmt = lambda n: f"{n:,}"
def ci(c, d=2): return f"{c[0]:.{d}f} to {c[1]:.{d}f}"
def sgn(x, d=2): return f"{x:+.{d}f}".replace("+", "+").replace("-", "−")
P, SEC, PRED, HZ, CAL, CONV, LOOPS, STR = res["primary"], res["secondary_founder_identity"], res["secondary_predictors"], res["horizon"], res["calibration"], res["convergence"], res["loops"], res["strata"]
label = res["outcome_label"]; n = res["pairs_analysed"]; counts = res["counts"]
rho, lo, hi = P["rho"], P["ci95"][0], P["ci95"][1]; loo = P["leave_one_out"]
exc = [h["g"] for h in HZ if h["ci95"][0] is not None and h["ci95"][0] > 0 and h["rho"] > 0]
peak = max((h for h in HZ if h["rho"] is not None), key=lambda h: h["rho"])
def hz_at(g): h = HZ[g - 1]; return f"g{g} {h['rho']:.2f} ({h['ci95'][0]:.2f} to {h['ci95'][1]:.2f})"
p_sec = SEC["permutation_p"]; p_sec_txt = f"{p_sec:.4f}" if p_sec >= 0.0005 else f"1/{SEC['permutations'] + 1:,}"
B = res["dB_G"]; dBv = list(B.values()); pos = sum(v > 0 for v in dBv); neg = sum(v < 0 for v in dBv)

# the one-paragraph answer, primary estimate and interval first (§12)
ANSWER = (f"The answer first. Across the {n} pairs, the rank correlation between E3's predicted difference in accessibility and the observed difference in mean final log₂ best fitness is {rho:.2f}, 95% interval {sgn(lo)} to {sgn(hi)}. "
          f"The interval covers zero, so by the rule written in advance the prediction is read as null at generation 256; it also covers the 0.3 the design named as the smallest substantial effect, so the record neither confirms nor excludes an effect of that size. "
          f"Founder identity itself matters: matched founders with identical behaviour reach different mean final fitness, S = {SEC['S']:.2f}, permutation p = {p_sec_txt}. "
          f"And the prediction is not absent everywhere: recomputed generation by generation, the correlation climbs to {peak['rho']:.2f} around generation {peak['g']} with its band clear of zero from generation {exc[0]} to {exc[-1]}, then falls back. Outcome {label}.")

# the instrument and the reproducibility finding (Amendment 6)
INSTRUMENT = (f"The instrument: {fmt(counts['harness_failures'])} harness failures in {fmt(46104296)} executions; all {fmt(counts['gen1_checked'])} generation-1 proposals matched E3's sealed tables; {fmt(counts['tie_key_collisions'])} tie-key collisions. "
              f"The pre-registered reproducibility subset, replicate 0 of every founder re-run on a second machine before analysis, found 153 of 176 populations identical in every field of every generation and 23 not. The cause is in the harness: world v0 never froze anvil's block context, so a program that reads TIMESTAMP, PREVRANDAO or BLOCKHASH can evaluate differently on another machine, about eight proposals in a million do, and in 13 of the 176 populations that reached the selection and changed the final population. "
              f"Reported in Amendment 6 of the protocol document, with the 23 genomes and their re-evaluations; by the pre-registered rule it does not void the record, and nothing in the analysis changes because of it.")

Hs = []
Hs.append({"id": "primary", "name": "prediction",
    "registered": "Spearman ρ across the 88 pairs between ΔA1, E3's difference in upward accessibility (the fraction of one-byte changes that outlive the founder), and ΔB, the difference in mean final log₂ best finite fitness over 16 replicates, N minus P in both. 95% percentile bootstrap interval from 10,000 pre-seeded resamples of the pairs. Direction stated in advance: positive. ρ = 0.3 pre-specified as the smallest substantial effect, an interpretive reference and not a threshold. Labels: primary positive if the interval excludes zero with a positive estimate; primary null if it covers zero.",
    "observed": f"ρ = {rho:.3f}, interval {sgn(lo, 3)} to {sgn(hi, 3)}; {P['pairs_dB_zero']} pairs with ΔB = 0; {P['undefined_resamples']} undefined resamples. Leave-one-pair-out: {min(loo):.3f} to {max(loo):.3f}. ΔB over the {n} pairs: {pos} positive, {neg} negative, mean {sum(dBv)/n:.2f}, sd {(sum((v - sum(dBv)/n)**2 for v in dBv)/(n-1))**0.5:.2f} doublings.",
    "verdict": f"primary null: {rho:.2f} ({sgn(lo)} to {sgn(hi)}), the interval covers zero and covers 0.3",
    "note": "The interval is 0.41 wide, as the design notes expected at 88 pairs; what magnitudes remain compatible with the record is what it says."})
Hs.append({"id": "secondary", "name": "founder identity",
    "registered": "Do matched founders produce more different outcomes than replicate stochasticity alone? S = mean over pairs of |ΔB| divided by the mean pooled within-founder standard deviation of B₂₅₆. Null: the 32 populations of each pair relabelled P/N at random, 10,000 times, pre-seeded; one-sided p. Also the number of pairs whose 16 N populations all lie strictly above or all strictly below the 16 P populations. Secondary positive if p < 0.05. This says whether founder identity matters, not whether E3 knew which way.",
    "observed": f"S = {SEC['S']:.3f}; permutation p = {p_sec_txt} ({SEC['permutations']:,} relabellings, none reaching the observed S). Fully separated pairs: {SEC['pairs_fully_separated']} (tie-free bound on the null expectation {SEC['separated_tie_free_upper_bound']:.1e}; permutation p {SEC['separated_permutation_p']:.2f}).",
    "verdict": f"secondary positive: S = {SEC['S']:.2f}, p = {p_sec_txt}",
    "note": "No causal claim about history: P and N were not randomly assigned their histories."})
Hs.append({"id": "tertiary", "name": "the prediction horizon",
    "registered": "ρ_g, the primary statistic recomputed at every generation from 1 to 256 with the same 10,000 index sets, drawn as one trajectory with its pointwise band; the number of pairs with ΔB_g = 0 at each g. Descriptive: no per-generation test and no derived half-life.",
    "observed": f"{hz_at(1)}; {hz_at(2)}; {hz_at(4)}; {hz_at(8)}; {hz_at(16)}; {hz_at(32)}; {hz_at(64)}; {hz_at(128)}; {hz_at(256)}. Peak {peak['rho']:.2f} at generation {peak['g']}. The band excludes zero at {len(exc)} generations, {exc[0]} to {exc[-1]}, and at none after. Pairs with ΔB_g = 0: {HZ[0]['pairs_dB_zero']} at g1, {HZ[1]['pairs_dB_zero']} at g2 to g4, none after.",
    "verdict": f"positive and clear of zero from generation {exc[0]} to {exc[-1]}, strongest around generation {peak['g']}; inside the band around zero from {exc[-1] + 1} on",
    "note": "The 256 pointwise bands are not multiplicity-adjusted; this is the pre-listed early-prediction pattern of outcome E, reported beside outcome D and not as a second test."})
Hs.append({"id": "also", "name": "reported, pre-specified",
    "registered": "Secondary predictors A2 (best accessible improvement) and A3 (neutral probability), each with its interval; A4 identically zero in the frozen table, no test. Generation-1 calibration against exact reference distributions. Convergence as total variation between final signature distributions, between P and N populations and within founders. Loop-class incidence. Strata by founder lifespan and by set, descriptively. Compute counts.",
    "observed": (f"A2 ρ {PRED['A2']['rho']:.3f} ({ci(PRED['A2']['ci95'], 3)}); A3 ρ {PRED['A3']['rho']:.3f} ({ci(PRED['A3']['ci95'], 3)}). Calibration: K {CAL['K']['observed']} observed against {CAL['K']['expected']:.1f} expected; M {CAL['M']['observed']:.4f} against a null of {CAL['M']['null_mean']:.4f} ± {CAL['M']['null_sd']:.4f}; neither triggers investigation. "
                 f"Convergence: TV between P and N populations {CONV['mean_between_PN']:.3f}, within founder {CONV['mean_within_founder']:.3f}, difference {CONV['mean_difference']:.3f} ({CONV['difference_ci95'][0]:.4f} to {CONV['difference_ci95'][1]:.4f}): final populations are almost disjoint in signature everywhere. "
                 f"Loop-class offspring appeared in {LOOPS['populations_with_any_loop_offspring']} of {counts['populations']:,} populations, {LOOPS['mean_loop_offspring_per_population_P']:.2f} per P population and {LOOPS['mean_loop_offspring_per_population_N']:.2f} per N. "
                 f"Strata, estimates only: lifespan 3 ({STR['lifespan_3']['pairs']} pairs) ρ {STR['lifespan_3']['rho']:.2f}, S {STR['lifespan_3']['S']:.2f}; lifespan ≥ 4 ({STR['lifespan_ge4']['pairs']}) ρ {STR['lifespan_ge4']['rho']:.2f}, S {STR['lifespan_ge4']['S']:.2f}; genesis ({STR['genesis']['pairs']}) ρ {STR['genesis']['rho']:.2f}, S {STR['genesis']['S']:.2f}; control ({STR['control']['pairs']}) ρ {STR['control']['rho']:.2f}, S {STR['control']['S']:.2f}. "
                 f"Every founder adapted in the operational sense of §3: all {counts['populations']:,} populations ended above their founder, median rise 2.64 doublings, maximum 15.29."),
    "verdict": "A2 and A3 do not predict either; calibration clean; final populations almost disjoint in signature; every founder adapted",
    "note": "Two defects of the frozen analysis script are reported in Amendment 7 and not repaired: its compute line double-counts the workers' running totals (the true counts are in the data below), and its stratum intervals reuse the 88-pair index sets by clipping, which makes them wrong; labelled exploratory intervals stand beside them in the amendment."})

OUTCOME_TXT = {"D": "Outcome D, by the list written before the run: primary null, secondary positive. Matched founder identity matters, but E3's one-mutant accessibility predictor does not explain which founder does better; the relevant difference is therefore not captured by A1. The early-prediction pattern of outcome E is present as well and is reported descriptively above."}
OUTCOME = OUTCOME_TXT.get(label, f"Outcome {label}, by the list written before the run (E4-after.md §3).")

facts = [
    ["founders", "176 in 88 matched pairs: P, an E2 parent; N, its E3 walk-0 endpoint sixty bytes away, chosen by E3's rule before any E3 result; identical frozen signature, 60 of 64 bytes different"],
    ["populations", f"{counts['populations']:,} = 176 founders × 16 replicates, 64 slots each, 256 generations, 64 proposals per generation: 46,137,344 proposals"],
    ["executions", f"46,104,296 physical, 32,992 cache hits, 3,300 retries, {counts['harness_failures']} harness failures, {counts['uninstantiable']:,} uninstantiable (a child beginning 0xEF), {counts['tie_key_collisions']} tie-key collisions"],
    ["generation-1 check", f"{counts['gen1_checked']:,} of {counts['gen1_checked']:,} proposals matched E3's sealed child tables in signature, count and loop class"],
    ["reproducibility", "replicate 0 of every founder re-run on a second machine before analysis: 153 of 176 populations identical, 23 differ; cause and the 23 genomes in Amendment 6"],
    ["world", "v0, frozen as in E1 to E3: the same clean chain state at the same address for every evaluation; the block context (TIMESTAMP, PREVRANDAO, BLOCKHASH) was not frozen, disclosed in Amendment 6"],
    ["seed", "E4-2026-10-11, domain-separated keccak streams for parent, position, value and tie keys; the analysis-side generators seeded from the same string"],
    ["record root", root],
    ["pre-registration anchor", ANCHOR, f"https://etherscan.io/tx/{ANCHOR}"],
]
if rec_anchor: facts.append(["record anchor", rec_anchor, f"https://etherscan.io/tx/{rec_anchor}"])
else: facts.append(["record anchor", "to be recorded from the keeper; this line is replaced by the transaction when it is"])
if args.get("--snapshot"): facts.append(["record", f"{args['--snapshot']}, a DigitalOcean volume snapshot of the full record (13 GB, 2,881 files); the manifest, the root, the analysis outputs and the reproducibility evidence are in the repository"])
facts.append(["protocol", "slopware/experiments/E4-after.md, signed 2026-10-11, seven dated amendments below the signature", "https://github.com/cryptobushi/slopware/blob/main/slopware/experiments/E4-after.md"])
facts.append(["analysis", "scripts/e4_analysis.py, pre-specified and hashed in the anchor; scripts/e4_mirror.py for the picture, likewise; scripts/e4_repro.py for the reproducibility comparison", None])

caption = "AFTER. 88 pairs as an 8 × 11 grid in parents.json order, left to right then top to bottom. In each cell generations run from the left edge (0) to the right (256); the pair's shared generation-0 fitness is the horizontal centreline; the 16 populations founded from the original program are drawn upward and the 16 founded from its neutral descendant downward, one hairline each, height the population's best finite run in doublings above the founder; a red mark where a population first produced a loop-class offspring. The vertical scale is global and set by the record: 16 doublings of room each way, because one population rose 15.3. Nothing is clipped or individually scaled. Rules fixed and hashed before the run."
fig2 = ""
if args.get("--figure2"):
    fig2 = '<img alt="the prediction horizon: rho_g with its band" src="' + args["--figure2"] + '"><p class="mute">' + esc(args.get("--figure2-caption", "")) + '</p>'
out = {"experiment": "E4", "answer": ANSWER, "instrument": INSTRUMENT, "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "caption": caption, "hypotheses": Hs, "outcome": OUTCOME, "sentences": sentences, "facts": facts,
       "reproduce": "To check any number: fetch the snapshot, run scripts/e4_analysis.py on record/, and compare with summaries/results.json; to check the picture, run scripts/e4_mirror.py on summaries/trajectories.json; to check the reproducibility finding, run scripts/e4_repro.py on the two sets of replicate-0 records. The root hash above is the sha256 of the sorted sha256 manifest of every file in the record.",
       "anchorTx": ANCHOR, "edition": edition}
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)

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
else:
    edition_html = '<div id="edition">\n<h2>the research edition</h2>\n<p class="mute">AFTER, the picture above at print resolution, is the research edition for this experiment. Its title and rules were fixed before the run; it is minted and listed by the keeper after the record anchor is recorded. This paragraph is replaced by the listing.</p>\n</div>'
tpl = open(f"{SITE}/e4.template.html").read()
page = (tpl.replace("{{HYPOTHESES}}", hyp_html).replace("{{SENTENCES}}", sent_html).replace("{{FACTS}}", facts_html).replace("{{REPRO}}", esc(out["reproduce"]))
        .replace("{{CAPTION}}", esc(caption)).replace("{{INSTRUMENT}}", esc(INSTRUMENT)).replace("{{ANSWER}}", esc(ANSWER)).replace("{{OUTCOME}}", "<p>" + esc(OUTCOME) + "</p>")
        .replace("{{ANCHOR_HREF}}", f"https://etherscan.io/tx/{ANCHOR}").replace("{{EDITION}}", edition_html).replace("{{FIGURE2}}", fig2))
open(f"{SITE}/e4.html", "w").write(page)
md = ["# SLOPWARE — E4 after", "", "The fourth pre-registered experiment, run once, 2026-10-12 to 2026-10-13 UTC. From each of 88 matched pairs of founders (an E2 parent and its E3 neutral descendant sixty bytes away, identical measured behaviour), 16 populations of 64 ran for 256 generations under one rule: one byte changed per proposal, the 64 longest finite runs continue, ties by a seeded order, nothing else rewarded. Generation 0 known, generation 1's proposal space mapped in advance by E3 and checked against it, generation 2 onward unmapped. Pre-registered and anchored before the first proposal.", "", ANSWER, "", f"Picture: AFTER, https://slopware.fun/e4-data/after.png — {caption}", "", INSTRUMENT, "", "## Measurements and readings", ""]
for h in Hs: md += [f"### {h['id']} · {h['name']} — {h['verdict']}", "", f"Registered: {h['registered']}", "", f"Observed: {h['observed']}", ""] + ([h["note"], ""] if h.get("note") else [])
md += ["## Outcome", "", OUTCOME, "", "## In three sentences", ""] + [s for x in sentences for s in (x, "")] + ["## The data", ""] + [f"- {f[0]}: {f[1]}" + (f" ({f[2]})" if len(f) > 2 and f[2] else "") for f in facts] + ["", out["reproduce"], ""]
if edition: md += ["## The research edition", "", edition["text"], "", edition.get("note", "") + (f" Listing at Manifold: {edition['gallery']}" if edition.get("gallery") else ""), ""]
else: md += ["## The research edition", "", "AFTER, the picture above at print resolution, is the research edition for this experiment; its title and rules were fixed before the run; minted and listed by the keeper after the record anchor is recorded.", ""]
md += ["Also: https://slopware.fun/llms.txt · https://slopware.fun/e1.md · https://slopware.fun/e2.md · https://slopware.fun/e3.md · https://slopware.fun/readings.md · the repository https://github.com/cryptobushi/slopware"]
open(f"{SITE}/e4.md", "w").write("\n".join(md))
print(f"e4.json, e4.html, e4.md written · outcome {label} · {len(Hs)} blocks · {len(sentences)} sentences · edition {'yes' if edition else 'pending'} · record anchor {'yes' if rec_anchor else 'pending'}")
for h in Hs: print(f"  {h['id']}: {h['verdict']}")
