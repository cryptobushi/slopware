# E4 — design notes, before the pre-registration

*2026-10-11. This is a design document, not a pre-registration. Nothing here is frozen, nothing has run, and no seed, hash or anchor exists yet. The pre-registration will be a separate document written from these notes after the artist's decisions, and only that document is signed and anchored.*

## 0. The question

E1: almost all one-byte changes are neutral. E2: neutral space is traversable, and about half of the lifespan improvements found under persistence selection were enabled by prior neutral substitutions (W5, 49.7%). E3: neutral travel systematically changes which mutations matter (Jaccard(*M*) 0.996 at eight bytes, 0.925 at sixty; *D*_sig rising with distance) while the amount of adjacent variation stays approximately constant.

E4 asks the causal question those three imply: **do the differences created by neutral history have consequences under selection?** The mechanism under test is stated mechanically and nowhere else: neutral history → a different genotype → a different one-mutant neighbourhood → possibly a different response to the same selection rule. Given identical bytes and identical environment, execution is deterministic; nothing "remembers" anything.

The important null is not "nothing evolves". It is: **neutral history does not predict subsequent selection outcomes.**

## 1. The cleanest design: matched founder pairs

**Founders.** For each of the 88 E3 parents *P*, the matched founder *N* is the walk-0, target-60 endpoint of E3 (`E3/summaries/neighbourhoods/main`, genomeId `E<p>.0.60`). All 88 exist. *N* is chosen by a rule fixed in E3 before any result; no founder is chosen for how it looks. *P* and *N* have identical full frozen signatures by construction (E3 X2 verified this from the neighbourhood evaluation's own re-placement), so they have identical fitness under any fitness function defined on the signature. They differ in 60 of 64 bytes, and E3 has already measured the exhaustive one-mutant neighbourhood of both.

**Populations.** From each founder, *R* independent replicate populations. Every population: identical world (v0, the E3 post-genesis snapshot and harness, unchanged), identical size *N*, identical operator, identical selection rule, identical generations *G*, independent seeded randomness. 88 pairs × 2 founders × *R* replicates.

**Generation 0** is *N* copies of the founder. Each generation: every survivor is evaluated once (deterministic, so a genotype evaluated once is known), *N* offspring are produced, each by choosing a parent uniformly at random among the *N* survivors and applying **exactly one single-byte substitution** (position uniform in 0..63, value uniform over the 255 other bytes: E1–E3's operator, unchanged, length fixed at 64). The 2*N* individuals are ranked by fitness; the best *N* survive. **Ties are broken by a seeded random order**, never by age or by founder-likeness, so neutral drift occurs without bias toward or away from the founder. No crossover, no elitism beyond survival by rank, no fitness sharing, no environment change, no second objective.

**Why generation 1 is special.** Every generation-1 offspring is a one-byte substitution of the founder, so it is one of the 16,319 children E3 already placed and recorded (`placements-*.jsonl`: position, value, class, signature hash, probe-A count, reach flags). E4's generation 1 is therefore a byte-for-byte replication of a sample of the E3 record, under a harness that must be identical. This is both a free reproducibility check and the mechanical bridge from E3's measurement to E4's prediction.

## 2. Alternatives considered

**Alt 1 — replicate hill climbs instead of populations.** *R* independent E2 arm-B-style walks from *P* and from *N* (one lineage, accept if lifespan ≥ current). Cheapest, continuous with E2, trivially analysable. Weaknesses: a single lineage's outcome is dominated by its first few accepted steps; there is no population to converge or diverge; the acceptance rule (≥) builds drift into selection in a way the population design keeps separate. Keep as the fallback if the population design proves too expensive.

**Alt 2 — triplets, not pairs.** Founders *P*, *N*₁, *N*₂, *N*₃ (the three walks' target-60 endpoints). Separates "descendant versus parent" from "one neutral history versus another": if *N*₁, *N*₂, *N*₃ differ among themselves as much as from *P*, the effect is of genotype, not of being a descendant. Doubles compute. Recommended only if the budget allows; otherwise the walk-1 and walk-2 endpoints remain available for a later study.

**Alt 3 — phenotype-matched unrelated pairs as a reference arm.** E1's signature-matched group: 60 parents share a full signature with another parent (one group of 43). Pairs of unrelated programs with identical phenotype and no shared history bound how large a founder effect can be when genotypes differ entirely. Adds a reference, not a new question. Cheap if small (a dozen pairs); risk is scope creep.

**Alt 4 — the distance series.** Founders at targets 8, 16, 32, 48, 60 from the same walk: a dose-response of history length on consequences, mirroring E3's X1. Five times the compute and five times the tests. Not for E4.

## 3. Major confounds

Core design:
1. **Harness drift between E3 and E4.** If the E4 harness differs in any way, E3's neighbourhoods are not E4's generation-1 neighbourhoods and the prediction is void. Control: the generation-1 check (§6): every generation-1 offspring's signature hash must equal the E3 placement record for that (position, value). Any mismatch halts the run.
2. **Heavy-tailed fitness.** A looping program can run 100,000 instructions; most programs run under 30. Means are meaningless. Control: the loop class is excluded from reproduction (§4) and every statistic is on log₂ fitness or on ranks.
3. **Ties and drift.** Most mutations are neutral; most individuals tie. A tie rule that favours survivors freezes the population on the founder; one that favours offspring is E2's drift. Control: seeded random tie-breaking, stated in advance.
4. **Pseudo-replication.** Populations are nested in founders, founders in pairs. Control: the pair is the unit of inference; replicates estimate within-founder variance only.
5. **Founder heterogeneity across pairs.** 66 of 88 parents run exactly three instructions; the rest four to seven. Within-pair comparison removes this; it is reported as a stratum, not controlled away.
6. **Small expected effects.** At sixty bytes, *P* and *N* still share 92.5% of their exact non-neutral mutations. The founder effect, if any, is expected to be small. The design must be able to report a precise null, hence 88 pairs, a prospective predictor and a smallest effect of interest fixed in advance.
7. **Convergence by strong selection.** Truncation selection may drive every population toward the same few long-running structures, erasing founder differences. That is outcome E and is a result, not a failure.
8. **The choice of walk 0.** Mechanical, fixed in E3; walks 1 and 2 exist for sensitivity but are not run in E4.

Alt 1 adds: first-step dominance, drift-selection entanglement. Alt 2 adds: three times the comparisons per parent, a multiple-testing burden. Alt 3 adds: unrelated pairs differ in the expressed region as well as the tail, so "no history" also means "different code". Alt 4 adds: compute and tests, and a temptation to read a monotone series as a story.

## 4. Fitness: candidates and failure modes

All candidates are functions of the frozen signature, so each is exactly computable for every E3 child. The chosen one is frozen before execution and never changes.

| | fitness | failure modes |
|---|---|---|
| F1 | probe-A instruction count (E2's lifespan), raw | loops run until gas is gone and dominate: 14% of E2 persistence walks looped, and a loop is the degenerate way to never be shorter. Selection becomes selection for gas exhaustion. Rejected. |
| F2 | probe-A instruction count, **with out-of-gas as a separate terminal class** (E2's `loop` flag: out of gas after more than 32 instructions) that is recorded, reported and **excluded from reproduction** | a loop that reads `GAS` and halts before exhaustion is finite and legitimate, so the ceiling is the gas limit (about 10⁵ instructions); the distribution stays heavy-tailed, so report log₂ and ranks. The exclusion is a disclosed rule: *we select for the longest finite run.* |
| F3 | instruction count only if probe A ends in a clean halt (STOP/RETURN), else 0 | every founder scores 0 (most end in an invalid opcode) and the first clean halt is trivial (byte 0 → `STOP` runs one instruction cleanly). Fitness then has a cliff at the start and E3's classes no longer line up with it. Rejected. |
| F4 | distinct genome positions executed in probe A (coverage, ≤ 64) | loop-proof and bounded, but rewards touching bytes, not running; saturates at 64; ties everywhere. Rejected as primary. |
| F5 | F2 capped at a fixed *C* (e.g. 1,024) | tames the tail but *C* is arbitrary and saturation produces ties exactly where selection should discriminate. Only if F2's tail is judged unacceptable now, not after. |
| F6 | sum over probes A–E | rewards input-dependence by accident and makes the measure five times more complex. Rejected. |

**Recommended: F2.** It is E2's measure with the one lesson E2 taught applied: looping is a terminal class, not a high score. Individuals in the loop class never displace a finite individual; among finite individuals, longer wins; ties random. Reported as log₂(instructions). The class is counted per population per generation and is itself a secondary outcome (does neutral history predict falling into loops?).

## 5. Mechanics, proposed values

- Population *N* = 64. Generations *G* = 256. Replicates *R* = 8. Evaluations per population = 64 × 256 = 16,384 offspring, comparable to E2's 10,000 attempts per walk.
- Operator: exactly one single-byte substitution per offspring, length fixed at 64. **Constitution Part X-A decision 2 expires with this design and requires a length rule as a world parameter; the recommendation is a dated amendment fixing length at 64 for E4, on the ground that E3's predictor is a fixed-length one-mutant neighbourhood and would not apply to a variable-length population.** Length change is deferred to a later experiment, not denied.
- Selection: (μ + λ) truncation, μ = λ = 64, ties by seeded random order.
- Loop class: never reproduces while a finite individual exists; counted.
- Uninstantiable offspring (first byte `0xEF`): recorded, excluded, counted; the slot is not refilled.
- Seeds: `keccak256("E4-<date>" ‖ pair ‖ founder ‖ replicate ‖ generation ‖ slot)` for parent choice, position, value and tie order. Fixed in the pre-registration; the seed string is in the anchored text.
- Harness: E3's exactly (`harnessVersion e3-1`, world v0, same snapshot, retry up to three times with a fresh revert; a persistent failure is a harness failure, excluded, counted, listed). Harness failure rate above 0.1% in any shard halts the shard.
- Record: every individual every generation (genome, fitness, class, signature hash), sealed and anchored as E1–E3 were.

## 6. Statistical unit and analysis

**The unit is the founder pair** (88). Replicate populations estimate the within-founder spread and are never counted as independent tests of the P-versus-N effect.

Per population: *B_g* = log₂ of the best finite fitness in the population at generation *g*. Per founder: *b_g* = median of *B_g* over its *R* replicates. Per pair: Δ_g = *b_g*(*N*) − *b_g*(*P*).

**Primary endpoint:** Δ_G at the final generation.

**Test 1 — founder effect (is there any?).** Within each pair, the 2*R* populations are relabelled *P*/*N* at random (*R* each) to build the null distribution of *T* = mean over pairs of |Δ_G|. Reported: observed *T*, its permutation interval, and the number of pairs whose *R* *N*-populations all lie above or all below the *R* *P*-populations (under the null that is 2/C(2*R*,*R*) per pair, about 0.7 pairs of 88 at *R* = 8). Smallest effect of interest: the between-founder-within-pair standard deviation of *B_G* at least half the between-replicate standard deviation.

**Test 2 — the prediction (does E3 explain it?).** Spearman ρ between the pre-sealed E3 predictor difference (§7) and Δ_G across the 88 pairs, with a 95% bootstrap interval over pairs. Direction stated in advance: positive. Smallest effect of interest: ρ = 0.3 (the standard error at 88 pairs is about 0.1).

**Secondary, pre-specified:** the prediction horizon ρ_g for every *g* from 1 to *G*, expected positive at *g* = 1 by construction and the question being how fast it decays; the loop-class incidence per founder and its relation to the predictor; convergence, measured as the signature distance between *P*-founded and *N*-founded final best genotypes against the distance between replicates of the same founder; strata by parent lifespan (3; ≥ 4) and set (genesis, control). Bootstrap intervals over pairs throughout, as in E3. One primary test; everything else reported.

**Generation-1 calibration.** From E3's exact counts the probability that a population's first generation contains an improving offspring is 1 − (1 − *u*/16,319)^64, with *u* the founder's count of finite children longer than itself. The observed fraction across all 1,408 populations must agree with the sum of these probabilities (binomial). This is a check of the instrument, not a hypothesis; disagreement halts the run.

## 7. A genuinely prospective prediction from E3

Everything below is computed from the sealed E3 record (root `70471484…`, snapshot `slopware-e3-record-20261011`) before E4's first placement, written to a table, hashed, and included in the pre-registration anchor. No E3-derived quantity defined after E4 starts is a predictor; anything else is exploratory and labelled.

For each founder *f* (88 *P*, 88 *N*), from its 16,319 recorded children under the chosen fitness:
- **A1, accessible improvement fraction:** the fraction of placeable children whose fitness exceeds the founder's and that are not in the loop class. *This is the primary predictor.* Its pair difference A1(*N*) − A1(*P*) is what Test 2 correlates with Δ_G.
- **A2, best accessible improvement:** the maximum child fitness (log₂), excluding the loop class.
- **A3, neutral fraction:** the share of children with the founder's exact signature (robustness).
- **A4, loop accessibility:** the fraction of children in the loop class.

A2–A4 are secondary predictors, each reported with its own ρ; none replaces A1 after the fact. The same table records the E3 pair distances already published (*D*_sig, Jaccard(*M*)) so that "how different were the neighbourhoods" can be read beside "how different were the outcomes", descriptively.

What E3 already says about the predictor's range: among parents the count of longer children runs from 62 to 186 of 16,319; at target 60, 43 of 88 pairs differ by ten or more in that count; the differences are not consistent in sign across a parent's three walks (52 of 81 agree), which is as expected if the predictor is a property of the specific descendant and not of the parent. The predictor table has real variation to work with and no sampling noise, since the neighbourhoods are exhaustive.

## 8. Compute

E3 placed 22,960,833 children in four hours on one c-32 droplet (about 1,600 placements per second, about $9 for the whole run). E4 at the proposed values: 88 × 2 × 8 × 64 × 256 = 23.1 million offspring evaluations, plus 1,408 founder evaluations, plus the generation-1 cross-check, which is free because those placements are the first generation. About four hours of compute on the same droplet class, under $10, and the same seal-analyse-snapshot-destroy finish as E3. Halving *R* halves it; Alt 2 doubles it. The predictor table is extracted first from the E3 snapshot on a small read-only droplet, which is a separate, cheaper step.

## 9. Failure and stop conditions

Stop for inspection, never for results:
- any generation-1 offspring whose signature hash differs from the E3 record for that (founder, position, value): the harness is not E3's; nothing continues until the cause is written down;
- generation-1 calibration outside its binomial interval;
- harness failure rate above 0.1% in any shard;
- the walks' or populations' seeded streams failing to reproduce on a second machine for the pre-registered reproducibility subset (one replicate per founder re-run from seed; expected byte-for-byte agreement).

Not stop conditions: stagnation, convergence, loops, no adaptation, strong adaptation, a result that looks like anything. Every population runs exactly *G* generations. Extinction cannot occur under (μ + λ) survival; a population in which every individual is in the loop class is impossible because founders are finite and survive unless displaced by a longer finite individual.

## 10. What every result would mean

Written now, read later. "Adapt" below means only: *B_G* exceeds the founder's log₂ fitness.

- **A. Neither founder adapts.** Under this operator and this selection, 16,384 evaluations do not find longer finite programs from these founders. Unexpected given E2 (every parent doubled under a hill climb), and would point at the population mechanics, which would be examined and reported, not tuned.
- **B. Both adapt similarly; no founder effect; no prediction.** Test 1 null, Test 2 interval covering zero. The headline result is then: *E3 showed that neutral history changes immediate accessibility; E4 found that those differences do not measurably affect adaptation under this selection regime.* That is a complete, publishable answer. It would mean the accessibility differences at sixty bytes are small relative to what 256 generations of selection can find from either start.
- **C. Adaptation occurs and E3 predicts it.** Test 2 positive at or above ρ = 0.3, with the prediction horizon showing how many generations the one-mutant neighbourhood stays informative. The sequence E1 → E2 → E3 → E4 then reads: structure discovered, structure predicts consequences.
- **D. Founders lead reproducibly to different outcomes but E3 does not predict which.** Test 1 positive, Test 2 null. Neutral history matters through something the one-mutant neighbourhood does not measure (deeper structure, two or more mutations away). Reported as such; a later study may look there. Not a success for the prediction.
- **E. Early differences, then convergence.** ρ_g positive at small *g* and gone by *G*; Test 1 null at *G*. The prediction horizon is the result: E3's structure has consequences for a measurable number of generations and then selection erases them.
- **F. Anything else.** Reported descriptively, with the primary test unchanged and the pre-registered outcome list cited. Examples to expect: loop-class capture of whole populations; fitness plateaux shared across all pairs; a handful of pairs driving the correlation (reported with leave-one-out).

## 11. The picture, fixed before the run

The rendering is decided and hashed before the first generation and does not depend on the result. Proposal: one strip per pair, 88 strips in parents.json order, generations left to right. From a shared baseline, the *P*-founded replicates are drawn upward and the *N*-founded replicates downward, height log₂ of the best finite fitness, one hairline per replicate, the loop class marked where it appears. The figure is a mirror: identical trajectories give a symmetric strip, no adaptation gives a flat line, divergence gives asymmetry, convergence gives a strip that is asymmetric on the left and symmetric on the right. It reveals the trajectories and celebrates nothing. THREADS' pen, STEPS' axis discipline. The artist names it after seeing a synthetic mock and before seeing any trajectory, as before.

## 12. Vocabulary

Facts and this design use: program, genotype, founder, population, generation, selection rule, fitness as defined in §4, finite run, loop class, accessibility. They do not use life, organism, evolvability, open-ended evolution, or adaptation except in the operational sense of §10. The claim is never that history changes deterministic programs; it is that a silent history yields a different genotype whose neighbourhood differs, and that this difference may or may not be visible under selection.

## 13. Decisions needed before the pre-registration is written

1. Fitness: F2 as recommended, or F5 with a stated cap.
2. Mechanics: *N* = 64, *G* = 256, *R* = 8, truncation with random ties, or other values.
3. Scope: core only, or core plus Alt 2 (triplets) or Alt 3 (unrelated reference pairs).
4. Length rule: a dated amendment fixing 64 bytes for E4.
5. Smallest effects of interest: ρ = 0.3 for prediction; founder SD at least half the replicate SD.
6. The working title for the picture, after the mock.
