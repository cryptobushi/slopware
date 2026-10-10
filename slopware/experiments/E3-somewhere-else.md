# E3 — Somewhere else

**Candidate pre-registration. Draft 1 of 2026-10-10, unsigned, for review. Nothing below is run until it is signed and anchored. No candidate endpoint's neighbourhood has been evaluated, and none will be until the endpoint rule and the analysis below are frozen.**

E3 follows E1 (`E1-neighbourhoods.md`) and E2 (`E2-walks.md`). E1 found that 98.4% of one-byte changes leave a program's measured behaviour identical. E2 found that this neutrality is navigable ground: neutral walks rewrote a median 63 of 64 bytes while preserving the exact signature, and under persistence half of all lifespan improvements (49.7%, 95% interval 48.6 to 50.9) were unavailable from the start of their plateau and became available only after intervening neutral changes. E3 asks the question that result raises and does not answer: does neutral history change what a program can become next, before it changes what the program does? Two programs can do the same thing without being in the same place.

E3 is not a population experiment. The roadmap's population-and-selection experiment waits until the structure E2 exposed has been measured directly. The sequence is neutrality (E1), traversability (E2), accessibility (E3), and only then selection.

## 1. Questions

1. **Divergence.** As neutral descendants of one program move farther from it in genotype while keeping its signature, do their one-mutant neighbourhoods become less similar to its own?
2. **Accessibility without phenotypic change.** Does the distribution of phenotypes reachable in one mutation change along a neutral trajectory, although the current phenotype does not?
3. **Accessible variation.** Does the amount of phenotypic variation adjacent to a genome change after neutral travel?
4. **Exact against aggregate.** When neighbourhoods differ, do the exact accessible mutations differ while the aggregate phenotype distributions stay the same, as E2's noise check hinted at the level of walks?

## 2. Design in one paragraph

For each parent *P*, independent neutral walks (E2's arm A rule, with the fixed harness of §6) produce descendants that keep *P*'s full signature. Each walk is frozen at the first accepted step at which its Hamming distance from *P* reaches each of five pre-registered targets, giving endpoints at distances 8, 16, 32, 48 and 60. Walking then stops. The one-mutant neighbourhood of *P* and of every endpoint is enumerated exhaustively (64 × 255 = 16,320 children, 16,319 placeable) and every child is evaluated from the same clean world state. The walks make the specimens; the exhaustive neighbourhoods are the measurement, as in E1.

## 3. Hypotheses and pre-specified measurements

Definitions used below are in §5. Outcomes are listed in advance; none is "success".

**X1 (neighbourhood divergence with neutral distance).** The dissimilarity *D*(N(*e*), N(*P*)) between an endpoint's neighbourhood and its parent's, measured on the class distribution (*D*₅) and on the signature distribution (*D*_sig), is reported against the endpoint's Hamming distance from *P* (overall, and within the executed region, §5.4). Statistic: Spearman's ρ between distance and *D*, over all endpoints, with a bootstrap interval over parents; and the mean *D* at each distance target, each against the replicate floor (§5.6) and against the far reference (§5.7). *No directional threshold.* Pre-listed readings: (a) *D* indistinguishable from the replicate floor at every distance: neutral endpoints have effectively the same futures; (b) *D* above the floor at the first target and flat afterwards: divergence immediate, then saturating; (c) *D* rising with distance (ρ positive, interval excluding zero): divergence grows with neutral travel; (d) *D* at or near the far reference by distance 60: a far neutral descendant's future is as different from its parent's as an unrelated program's with the same phenotype.

**X2 (accessibility without phenotypic change).** For each endpoint, the set of signatures reachable in one mutation, *S*(*e*), against *S*(*P*): Jaccard overlap of the sets, and *D*_sig of the frequency distributions, both reported against the replicate floor. The fraction of endpoints whose reachable-signature set differs from *P*'s by more than the floor, with a Wilson interval. *No threshold.* The question is how much neutral history reshapes the immediate possibility space; W5 showed that it does so for lifespan at least sometimes.

**X3 (accessible variation).** Three operational quantities per genome, reported as paired differences endpoint minus parent, by distance: the fraction of placeable children whose signature differs from the genome's (adjacent variation); the number of distinct child signatures (phenotypic richness); the fraction of children whose probe-A lifespan exceeds the genome's (upward accessibility). The word evolvability is not used. *No threshold.* Pre-listed readings: neutral travel leaves these unchanged; changes them in one direction across parents; changes them without a consistent direction (some neutral regions border more variation, some less).

**X4 (exact against aggregate).** For each endpoint–parent pair, the Jaccard overlap of the exact sets of non-neutral substitutions, *M*(*e*) and *M*(*P*) (sets of (position, value) pairs), beside *D*₅ and *D*_sig. Pre-listed readings: both low (exact and aggregate diverge); exact overlap low while aggregate distances stay at the floor (micro-history differs, macro-statistics stable, the pattern E2's noise check showed for walks); both at the floor.

**X5 (nothing new, observation only).** The detector set from E2, unchanged and fixed here: `clean_halt`, `returns_data`, `write_survives`, `create_executed`, `external_call` (with the entered-code witness recorded), `create_succeeds`, `child_has_code`, `loop`, plus the self-inspection detector (S1: `CODESIZE`, `CODECOPY`, `ADDRESS`, `EXTCODEHASH` of self executed) over every child. Incidence reported. Nothing is predicted and nothing is rewarded. `child_has_code` and `external_call` events that enter code are replicated three times before being reported as more than candidates; a replicated `child_has_code` runs the shared-byte test (E2 §9) as exploratory. The scorecard moves only as E2 §9 specified.

## 4. Population and the endpoint rule

**Parents.** The 88 E2 parents (`E2/parents.json`, sha256 `0df39d8a…`): the E1 parents that executed three or more instructions, 42 genesis and 46 control. Reported pooled and by set. Stratified by parent lifespan (3; 4 or more) because the executed region, where divergence can live, is small for most of them (median `consumedBytes` 24).

**Why not E2's existing endpoints.** E2's arm-A walks are neutral descendants of exactly these parents, but their per-attempt genomes live on the E2 snapshot, their harness had the measurement flaw of E2 §7.8, and only final genomes and Hamming at every thousandth attempt are in the repository. E3 generates fresh neutral walks under the fixed harness so that the endpoints are reproducible bit for bit, and so that no endpoint is chosen with any knowledge of its future. E2's final genomes are not used.

**Walks.** Three independent neutral walks per parent, seeds `keccak256("E3-walks" ‖ parent ‖ walk ‖ attempt)`, E2's arm-A acceptance rule: a step is accepted if and only if the child's full signature (E1 §6, probes A–E) equals the current genome's. Budget 2,000 attempts per walk, which under E2's measured acceptance (96%) reaches Hamming 60 in about 180 accepted steps; a walk that has not reached distance 60 by attempt 2,000 contributes the endpoints it did reach and is reported.

**Endpoints, mechanical.** For each walk and each target *t* ∈ {8, 16, 32, 48, 60}, the endpoint is the genome after the first accepted step at which Hamming(genome, *P*) ≥ *t*. Nothing else about an endpoint is known or used when it is chosen. 88 × 3 × 5 = 1,320 endpoints plus 88 parents = 1,408 neighbourhoods. Every endpoint has *P*'s signature by construction; §7.1 verifies it again from the neighbourhood evaluation's own re-placement.

**Why Hamming.** Overall Hamming distance is dominated by the unread tail. It is kept as the primary distance because it is the simplest and was fixed before any result; the executed-region distance (§5.4) is reported beside it as the one more likely to carry the signal.

## 5. Definitions, frozen

1. **Signature.** E1 §6, unchanged: per probe, outcome, instruction count, last opcode, return length, return-data hash, SSTORE and TSTORE counts, logs, creates, calls; joined over probes A–E.
2. **Neighbourhood N(*g*).** The 16,319 placeable one-byte substitutions of *g*, each with its signature, its class relative to *g* (neutral, altered, lengthened, shortened, lethal, as E1 §6), its probe-A lifespan and its detector flags.
3. **Distances between neighbourhoods.** *D*₅: total variation distance between the two five-class distributions. *D*_sig: total variation distance between the two distributions over child signatures (signatures hashed; the union of observed signatures is the support). Jaccard(*S*): overlap of the sets of reachable signatures. Jaccard(*M*): overlap of the sets of non-neutral (position, value) substitutions.
4. **Genetic distance.** Hamming(*e*, *P*) over 64 bytes; and executed-region Hamming, over the positions of *P*'s executed opcode bytes and their immediates (E2's opcode and immediate kinds for *P*).
5. **Accessible variation.** As X3.
6. **Replicate floor.** A pre-registered 10% of neighbourhoods (every tenth genome in a fixed order: parents first, then endpoints by parent, walk, target) is evaluated twice on separate fresh chains; the distribution of *D*₅, *D*_sig, Jaccard(*S*) and Jaccard(*M*) between a genome and itself is the floor against which every endpoint–parent comparison is read.
7. **Far reference.** For each parent, the neighbourhood distances to the other parents with the same probe-A lifespan (unrelated programs with the same coarse phenotype), which bounds how different two neighbourhoods can be when the genomes share nothing but a lifespan.
8. **Null for Jaccard(*M*).** The expected overlap of two independent random subsets of the 16,319 substitutions with the observed marginal non-neutral fractions; Jaccard(*M*) is reported against it.

## 6. Environment and the fixed harness

World v0, frozen as in E1 and E2 (`E2/world-v0.json`), with every genotype evaluated from the same post-genesis snapshot at the same address (E2 §5).

**Instrument errors are not phenotypes.** E2's re-run showed that a probe or receipt timeout recorded as an outcome can redirect a path-dependent walk. In E3: a probe or receipt timeout, an RPC error, or an instrumentation exception is retried up to three times with a fresh revert; a placement that still fails is recorded as a *harness failure* with no signature, is excluded from every statistic, is counted and listed, and in a walk the attempt is treated as rejected and flagged. The W4 detector's real transaction uses a longer receipt timeout and the same retry rule. A harness failure rate above 0.1% of placements in any shard halts that shard for inspection before the run continues.

**Reproducibility, three kinds, all checked.** (a) Endpoints: the walks are re-run from the same seeds on a fresh machine before any neighbourhood is evaluated; every endpoint must match bit for bit, or the run does not proceed. (b) Neighbourhoods: the replicate-floor subset (§5.6). (c) Conclusions: the pre-specified statistics recomputed on the replicate subset alone, as E2's sensitivity check did.

**A free cross-harness check.** E1 measured the one-mutant neighbourhood of all 88 parents under the E1 harness (no revert between placements). E3 measures them again under the fixed harness. The two are compared per parent (*D*₅ and Jaccard(*M*)) and reported as the harness-to-harness floor, exploratory.

## 7. Analysis, pre-specified

1. **Per genome:** signature re-verified against *P*; the five class counts; the reachable-signature set and distribution; the non-neutral substitution set; the X3 quantities; detector incidence; harness failures.
2. **X1:** *D*₅ and *D*_sig against Hamming and executed-region Hamming; Spearman ρ with a parent-level bootstrap interval (10,000 resamples); mean *D* per target against the replicate floor and the far reference.
3. **X2:** Jaccard(*S*) and *D*_sig per endpoint; the fraction of endpoints beyond the floor, Wilson interval, by target.
4. **X3:** paired differences by target, with bootstrap intervals; sign consistency across parents.
5. **X4:** Jaccard(*M*) against its null (§5.8), beside *D*₅ and *D*_sig, by target; the fraction of endpoint–parent pairs with exact overlap below the null while aggregate distances sit at the floor.
6. **X5:** incidence per detector; replications.
7. **Stratification:** every statistic by set (genesis, control) and by parent lifespan (3; ≥ 4).
8. **Floors and checks:** replicate floor; endpoint reproducibility; cross-harness comparison with E1.

No analysis is added after the run without being labelled exploratory. Script `scripts/e3_analysis.py`, frozen at the signing commit.

## 8. Compute, record, stopping rule

1,408 neighbourhoods × 16,320 = 22,978,560 placements, plus the replicate subset (141 neighbourhoods, 2,301,120) and the walks (88 × 3 × ≤ 2,000 = ≤ 528,000): about 25.8 million placements, the size of E1, which took 7.5 hours on a c-16 for about $5; one c-32 for about four hours. Record: one compact line per placement (genome id, position, value, signature hash, class, lifespan, flags; about 120 bytes), roughly 3 GB, plus per-genome summaries; manifest, root hash and anchoring as E1 §8; snapshot and teardown as E2. **Stopping rule (constitution decision 7):** the enumerations are exhaustive and finite; the walk budget is 2,000 attempts; nothing is extended, re-chosen or dropped after any neighbourhood is seen.

## 9. Confounders named in advance

- **Measurement noise** mimicking divergence: addressed by the replicate floor and the retry policy; every distance is read against the floor.
- **The tail.** Most neutral steps change unread bytes whose neighbourhoods are neutral everywhere, so overall Hamming can grow while the executed region barely moves; the executed-region distance is reported beside it.
- **Parent heterogeneity.** 66 of 88 parents execute exactly three instructions; stratification by lifespan.
- **Signature coarseness.** Two children with the same signature may differ in ways the signature does not record; *D*_sig is a lower bound on phenotypic difference and is said to be.
- **Position 0.** The `0xEF` replacement is unplaceable for every genome; neighbourhoods have 16,319 children and distributions are over those.
- **Endpoints that fail to reach a target.** Reported, and the analysis uses the targets reached.

## 10. The research edition

Defined before results, deterministic, meaningful if every neighbourhood is indistinguishable. **Working title: SOMEWHERE ELSE** (not fixed). Proposed form: one row per parent, 88 rows; in each row, *P* and its endpoints at the five distances drawn as THREADS walks (same pen, same palette, so genomes that do the same thing look different because their bytes are different), and beneath each genome a 64-cell bar, one cell per byte position, inked by the fraction of that position's 255 children that are non-neutral. If neutral history changes nothing, every bar in a row is the same bar under five different drawings; if it changes everything, the bars drift. Rules to be fixed in `scripts/e3_somewhere.py` and hashed before the run; the artist sees only a synthetic mock before signing, as with STEPS. The conceptual line, offered and not fixed: two programs can do the same thing without being in the same place.

## 11. What must not happen

- No endpoint is chosen, kept or dropped by anything but the Hamming rule. No candidate endpoint's neighbourhood is evaluated before signing.
- No step, child or behaviour is selected or rewarded. The detectors observe.
- No mechanism is added to the world.
- Nothing is placed on a public chain; the installer is not touched.
- Post-E1 releases are not in E3 (roadmap Part X-C); they remain reserved for pre-registered work decided on design, not on interest.

## 12. Publication

As E1 and E2: results under a dated heading here; a static results page at `slopware.fun/e3` with a Markdown mirror; `llms.txt` updated; one line per genesis parent on the readings page; the scorecard changed only as §3 X5 specifies.

## 13. After E3

If accessibility structure is substantial, a population experiment with heredity, variation and disclosed selection (E4) is motivated and is pre-registered next, with the loop problem and the reward definition settled in its text. If neutral endpoints have effectively indistinguishable futures, W5's result is read as local epistatic enabling rather than a general restructuring of the possibility space, and that is published as such. Either way the fixed-length question is decided by constitutional amendment before E4.

## Sign-off

*Unsigned. Before signing: review of this draft; harness changes of §6 implemented and smoke-tested with a bit-for-bit re-run; `scripts/e3_analysis.py` and `scripts/e3_somewhere.py` written and hashed; the synthetic mock shown to the artist; then signature, anchor, and the run.*
