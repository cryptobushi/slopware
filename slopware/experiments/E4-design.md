# E4 — design notes, before the pre-registration

*2026-10-11, revised the same day after an outside review. This is a design document, not a pre-registration. Nothing here is frozen, nothing has run, no seed, hash or anchor exists. The pre-registration will be a separate document written from these notes after the artist's decisions, and only that document is signed and anchored.*

## 0. The question, and the series

E1, neutrality: most one-byte mutations leave measured behaviour unchanged. E2, travel: programs can move through that neutral space, and silent substitutions enabled about half of the lifespan improvements found under persistence selection (W5, 49.7%). E3, accessibility: neutral travel progressively rearranges which mutations are accessible next while the amount of adjacent variation stays approximately constant.

E4, consequence: **does accessibility measured before selection predict the response to selection?** The mechanism under test is stated mechanically and nowhere else: neutral history → a different genotype → a different one-mutant neighbourhood → possibly a different response to the same selection rule. Given identical bytes and identical environment, execution is deterministic; nothing remembers anything.

The important null is not "nothing evolves". It is: **neutral history does not predict subsequent selection outcomes.** And the interesting positive claim is not "two genomes sixty bytes apart eventually behave differently", which is already known. It is: *a quantity measured and frozen before selection predicts what happens during selection.* The design is built around that prediction.

## 1. The design: matched founder pairs, one contrast

**Founders.** For each of the 88 E3 parents *P*, the matched founder *N* is the walk-0, target-60 endpoint of E3 (genomeId `E<p>.0.60`; all 88 exist). *N* is chosen by a rule fixed in E3 before any result; no founder is chosen for how it looks. *P* and *N* have identical full frozen signatures by construction (E3 X2 re-verified this from the neighbourhood evaluation's own placement), so identical fitness under any fitness defined on the signature. They differ in 60 of 64 bytes, and E3 has already measured the exhaustive one-mutant neighbourhood of both.

**Scope: core only.** No triplets, no unrelated reference pairs, no distance series. E3's walk-1 and walk-2 endpoints are **preserved untouched** as an independent replication set for after E4 ("does the result reproduce across independent neutral histories from the same parents?"), which is worth more than spending them now.

**Populations.** From each founder, *R* independent replicate populations under an identical world (v0, E3's post-genesis snapshot and harness `e3-1`, unchanged), identical size *N*, operator, selection rule and generations *G*, with independent seeded randomness. 88 pairs × 2 founders × *R*.

**The process, stated plainly.** There is no exact-copy reproduction. Every offspring differs from its parent by exactly one byte. Persistence comes from survival: this is a surviving set of genotypes, one-mutant proposals, and truncation selection, closer to a population search than to a Wright–Fisher model, and it is described as such.

- Generation 0: *N* copies of the founder.
- Each generation: *N* offspring, each by choosing a parent uniformly at random among the *N* survivors and applying **exactly one single-byte substitution** (position uniform in 0..63, value uniform over the 255 other bytes: E1–E3's operator, length fixed at 64).
- **Candidate pool = finite survivors + finite offspring.** The best *N* finite candidates by fitness survive; **ties are broken by a seeded random order**, never by age or founder-likeness, so drift is unbiased. Since founders are finite and survivors remain candidates, at least *N* finite candidates always exist and the population is exactly *N* every generation.
- **Loop-class offspring** (§4) are evaluated, recorded and counted, and **never enter the survivor pool.**
- **Uninstantiable offspring** (first byte `0xEF`) are failed attempts: recorded, not evaluated, not candidates, not replaced.
- **Caching.** A genotype has one phenotype under world v0. Every distinct genotype is executed on the chain once; a genotype seen again is looked up, never re-executed and never counted as a second measurement. Logical evaluations and physical executions are both counted and both reported.

**Generation 1 is the bridge.** Every generation-1 offspring is one of the 16,319 children E3 placed and recorded for that founder (`placements-*.jsonl`: position, value, class, signature hash, probe-A count, reach flags). E4's first generation is an independent sample from a completely frozen empirical map. Then the populations leave the mapped neighbourhood.

## 2. Alternatives considered and set aside

- **Replicate hill climbs** (E2 arm-B walks from *P* and *N*). Cheapest and continuous with E2, but one lineage's outcome is dominated by its first accepted steps, nothing can converge or diverge, and the ≥ acceptance builds drift into selection. Fallback only.
- **Triplets** *P*, *N*₁, *N*₂, *N*₃. Separates descendant-versus-parent from one-history-versus-another. Doubles compute and triples comparisons. Preserved as the replication set instead.
- **Phenotype-matched unrelated pairs** (E1's 43-parent identical-signature group). A qualitatively different genetic contrast that muddies the causal question. Not for E4.
- **Distance series** at 8/16/32/48/60. Five times the compute and tests. Not for E4.

## 3. Confounds and their controls

1. **Harness drift between E3 and E4.** Control: the deterministic generation-1 check (§6). Any mismatch halts.
2. **Heavy-tailed fitness.** Loops run 10⁵ instructions; most programs under 30. Control: the loop class never reproduces; every statistic is on log₂ or ranks.
3. **Ties and drift.** Control: seeded random tie order.
4. **Pseudo-replication.** Control: the pair is the unit; replicates estimate within-founder spread only.
5. **Founder heterogeneity across pairs** (66 of 88 parents run three instructions). Removed by the within-pair contrast; reported as a stratum.
6. **Small expected effects.** At sixty bytes *P* and *N* still share 92.5% of their exact non-neutral mutations. The design must report a precise null: 88 pairs, a sealed predictor, a smallest effect of interest, and the precision stated in advance (§7).
7. **Convergence by strong selection** erasing founder differences: outcome E, a result.
8. **Analyst freedom.** One primary predictor, one primary outcome, one primary test, named now; no composite scores.

## 4. Fitness: F2, the longest finite run

Candidates and failure modes (unchanged from the first draft, summarised): raw instruction count (F1) selects for gas exhaustion; clean-halt-gated count (F3) puts every founder at 0 and makes the first clean halt trivial; coverage (F4) rewards touching bytes and saturates at 64; a cap (F5) is arbitrary and creates ties where selection should discriminate; multi-probe sums (F6) reward input-dependence by accident.

**Chosen: F2, with no cap.** The ordering is purely mechanical:

- a finite execution with probe-A instruction count *k* ranks above a finite execution with count *j* iff *k* > *j*;
- the **loop class** is ineligible to reproduce and never ranks above any finite execution;
- ties among finite executions are broken by seeded random order.

**Loop class, defined.** E2's frozen operational classification, inherited for continuity: probe A ends out of gas after more than 32 traced instructions. The name does not assert cycle detection; a finite but gas-expensive path that exhausts gas is also in the class, and the class is reported as "out of gas after more than 32 instructions" wherever precision matters. Disclosed as: *we select for the longest finite run.* Reported as log₂(instructions). Loop incidence per population and generation is a secondary outcome in its own right.

## 5. Mechanics, proposed values

- *N* = 64, *G* = 256, *R* chosen by the simulation in §7 (proposal: 16). Logical evaluations per population = 64 × 256 = 16,384 offspring; physical executions fewer, by caching.
- Operator, selection, pools, caching: §1.
- **Length rule.** Constitution Part X-A decision 2 expires with the first population design and requires a published length rule. Recommended: a dated amendment fixing length at 64 bytes for E4 **because E4's primary predictor is E3's exhaustive fixed-length one-mutant neighbourhood; insertion or deletion would introduce mutation classes E3 never measured and void the prospective test.** Not a convenience: a requirement of the prediction. Length change is deferred to a later experiment, not denied.
- Seeds: `keccak256("E4-<date>" ‖ pair ‖ founder ‖ replicate ‖ generation ‖ slot)` for parent choice, position, value and tie order; the seed string is in the anchored text.
- Harness: E3's exactly. Retries up to three with a fresh revert; a persistent failure is a harness failure, excluded, counted and listed; above 0.1% in any shard the shard halts.
- Record: every individual every generation (genome, fitness, class, signature hash), plus the cache table, sealed and anchored as E1–E3 were.

## 6. Generation 1: deterministic bridge and stochastic calibration, kept apart

**Deterministic check (halts on failure).** For every unique generation-1 (founder, position, value) across all populations, E4's evaluation is compared field by field with E3's placement record: genome bytes, signature (hash, and the full signature where E4 recomputes it), probe-A instruction count, class, loop flag, and the reach flags that enter fitness. Any disagreement means the harness is not E3's and nothing continues until the cause is written down. This is instrument validity, and it is not statistical.

**Stochastic calibration (reported, not a halt).** Because E3 holds every founder's complete one-mutant fitness distribution *F_f*, the distribution of any generation-1 statistic under 64 independent draws is known exactly before E4 runs. Two statistics are frozen now:
- *K*, the number of populations whose generation 1 contains at least one finite offspring longer than the founder. Population *i* has *p_i* = 1 − (1 − *u_i*/16,319)^64 with *u_i* from the predictor table, and *K* is **Poisson-binomial** over {*p_i*}, not binomial; its exact distribution is computed from the sealed table.
- the best generation-1 fitness per population, whose exact distribution under 64 draws from *F_f* is likewise computed per founder; the observed values are compared to it in aggregate (a pre-specified goodness-of-fit on the per-population quantiles, which are uniform under the model).
Both are reported against their exact sampling distributions. An ordinary tail event is not a halt: a correct experiment lands outside a 95% interval one time in twenty. A pre-registered stringent criterion (for example *K* beyond the 1-in-10,000 tails of its exact distribution) triggers investigation before analysis, and even then the first question is the instrument, since the deterministic check will already have passed or failed.

## 7. Inference

**Unit: the founder pair** (88). Replicates estimate within-founder spread and are never counted as independent tests.

Per population: *B_g* = log₂ of the best finite fitness at generation *g*. Per founder: *b_g*, the **mean** of *B_g* over its *R* replicates (the mean is proposed over the median because the loop class is already excluded and the log already tames the tail; the simulation below shows the mean buys about a third more power; the choice is made now, once). Per pair: Δ_g = *b_g*(*N*) − *b_g*(*P*).

**Primary.** Spearman ρ across the 88 pairs between the sealed predictor difference A1(*N*) − A1(*P*) (§8) and Δ_G, with a 95% bootstrap interval over pairs. Direction stated in advance: positive. **Smallest effect of interest: ρ = 0.3.** This is the one inferential test E4 is built to run.

**Secondary: founder identity.** Do matched founders produce more different outcomes than replicate stochasticity alone? Within each pair the 2*R* populations are relabelled *P*/*N* at random (*R* each) to build the null of a standardised separation statistic, defined now: *S* = mean over pairs of |Δ_G| ÷ pooled within-founder standard deviation of *B_G* (so *S* is in replicate-SD units). Also reported: the number of pairs whose *R* *N*-populations all lie above or all below the *R* *P*-populations (null expectation 88 × 2/C(2*R*,*R*)). Interpretation written now: this test says whether founder identity matters, not whether E3 knows which way; a signed mean Δ is not used because neutral history has no global direction.

**Tertiary: the prediction horizon.** ρ_g for every *g* from 1 to *G*, drawn as one trajectory with parent-bootstrap bands and interpreted descriptively. No per-generation tests, no "half-life" statistic. The prediction is expected to be most directly expressed early, because generation-1 offspring are sampled directly from the E3-measured neighbourhood; whether a finite population of 64 draws realises that expectation is itself empirical, and ρ₁ is predicted to be positive probabilistically, not by construction. If E3 predicts generations 1 to 20 and then nothing, that is the result.

**Also reported, pre-specified:** loop-class incidence per founder against predictor A4; convergence, as the signature distance between *P*-founded and *N*-founded final best genotypes against the distance between replicates of one founder; strata by parent lifespan (3; ≥4) and set (genesis; control); leave-one-pair-out on the primary ρ.

**Precision and power, from synthetic outcomes (`scripts/e4_power_sim.py`, 2026-10-11).** No E4 data exist; the simulation draws synthetic founder effects whose latent correlation with the predictor difference is ρ_true, adds replicate noise, and runs the primary test. The predictor stand-in is E3's recorded difference in longer-child counts (the real A1 comes from the placements). The founder-effect size is expressed as σ_f/σ_rep, the between-founder-within-pair standard deviation of the true outcome over the between-replicate standard deviation.

E2 calibrates the scale: under persistence, with loops excluded, the within-parent standard deviation of final log₂ lifespan across a parent's five walks was 0.34 and the between-parent standard deviation of parent means 0.29. A *P*-versus-*N* effect within a pair, two genomes with the same phenotype, is expected to be smaller than that between unrelated parents, so the realistic regime is σ_f/σ_rep ≤ 0.5.

| statistic | ρ_true | σ_f/σ_rep | R | power (interval excludes 0) | interval width |
|---|---|---|---|---|---|
| mean | 0.3 | 0.25 | 8 | 0.19 | 0.44 |
| mean | 0.3 | 0.25 | 16 | 0.31 | 0.43 |
| mean | 0.3 | 0.50 | 8 | 0.44 | 0.43 |
| mean | 0.3 | 0.50 | 16 | 0.55 | 0.42 |
| mean | 0.4 | 0.50 | 8 | 0.70 | 0.41 |
| mean | 0.4 | 0.50 | 16 | 0.84 | 0.40 |
| mean | 0.3 | 1.00 | 16 | 0.68 | 0.41 |
| median | 0.3 | 0.50 | 8 | 0.36 | 0.43 |
| median | 0.3 | 0.50 | 16 | 0.47 | 0.42 |
| any | 0.0 | any | any | 0.01–0.03 | 0.44 |

What this says, plainly. With 88 pairs the interval on ρ is about 0.44 wide whatever *R* is; the number of pairs is fixed by E3 and is the binding constraint. *R* matters through attenuation: replicate noise dilutes the observed correlation, and going from 8 to 16 replicates recovers a useful part of it when the founder effect is small. The false-positive rate is at the nominal level throughout. **Decision proposed: *R* = 16 and the mean.** Under that choice E4 detects ρ_true = 0.3 about half the time if the founder effect is half the replicate spread, and ρ_true = 0.4 about five times in six. A null result will be reported with its interval and will mean: if neutral history predicts selection outcomes here, the correlation is unlikely to exceed about 0.3 to 0.4. That is a meaningful bound, and it is written down before the run so that it cannot be softened after. *R* is not justified by cost.

## 8. The prospective prediction, sealed before the run

Computed from the sealed E3 record (root `70471484…`, snapshot `slopware-e3-record-20261011`) before E4's first placement, written to `E4/predictors.json`, hashed, and included in the pre-registration anchor. No E3-derived quantity defined after E4 starts is a predictor; anything else is exploratory and labelled.

For each founder (88 *P*, 88 *N*), from its 16,319 recorded children under F2:
- **A1 — accessible improvement fraction**, primary: the fraction of placeable children that are finite (not loop class) and whose probe-A count exceeds the founder's. Mechanical, exhaustive, noise-free at the neighbourhood level, directly tied to the selection rule. It measures the probability of an improving mutation, not its size, and that simplicity is why it is primary. **It is not replaced, combined or reweighted after E4.**
- **A2 — best accessible improvement:** the maximum finite child fitness (log₂).
- **A3 — neutral fraction:** children with the founder's exact signature.
- **A4 — loop accessibility:** the fraction of children in the loop class.
- **The full one-mutant fitness distribution *F_f***, for the generation-1 calibration of §6.

A2–A4 are secondary, each with its own ρ. The table also carries E3's published pair distances (*D*_sig, Jaccard(*M*)) so "how different were the neighbourhoods" sits beside "how different were the outcomes", descriptively.

Range already visible in E3's summaries: parents' counts of longer children run from 62 to 186 of 16,319; at target 60, 43 of 88 pairs differ by ten or more; the sign of the difference is not consistent across a parent's three walks (52 of 81 agree), as expected if the property belongs to the specific descendant. The exact A1 (which excludes loop-class children) needs the per-child records on the snapshot; the extraction is a small read-only step on a droplet made from the snapshot, done before the pre-registration is signed.

## 9. Compute

E3 placed 22,960,833 children in four hours on one c-32 droplet (about 1,600 per second; about $9 all in). E4 at *N* = 64, *G* = 256, *R* = 16: 88 × 2 × 16 × 16,384 = 46.1 million logical evaluations, fewer physical executions by caching; about eight hours on the same class, roughly $20, with the same seal-analyse-snapshot-destroy finish as E3. At *R* = 8, half. The predictor extraction is separate and costs about a dollar.

## 10. Failure and stop conditions

Halt for inspection (deterministic): any generation-1 field mismatch with the E3 record; harness failure rate above 0.1% in any shard; the pre-registered reproducibility subset (one replicate per founder re-run from its seeds on a second machine) failing to reproduce byte for byte. Investigate before analysis (stochastic, stringent): a calibration statistic beyond its pre-registered extreme tail. Never a stop: stagnation, convergence, loops, no adaptation, strong adaptation, any look of any result. Every population runs exactly *G* generations. Extinction cannot occur; the survivor pool always holds *N* finite individuals.

## 11. What every result would mean

"Adapt" below means only that *B_G* exceeds the founder's log₂ fitness.

- **A. Neither founder adapts.** Unexpected given E2. Points at the mechanics, which are examined and reported, not tuned.
- **B. Both adapt alike; the primary interval covers zero; founder identity does not exceed replicate noise.** The headline: *E3 showed that neutral history changes immediate accessibility; E4 found that those differences do not measurably affect adaptation under this selection regime,* with the bound from §7. Complete and publishable.
- **C. The sealed predictor predicts the outcome** at or above ρ = 0.3, with the horizon showing how long E3's information lasts. The series then reads: structure measured and frozen first, then shown to predict something that had not yet happened.
- **D. Founder identity matters but E3 does not predict which way.** Secondary positive, primary null. History acts through something the one-mutant neighbourhood does not measure. Not a success for the prediction; reported as such.
- **E. Early prediction, then convergence.** ρ_g positive early, gone by *G*. The horizon is the result.
- **F. Anything else.** Reported descriptively against this list, primary test unchanged.

## 12. The picture

Fixed and hashed before the run; independent of the result. One strip per pair, 88 strips in parents.json order, generations left to right. From a shared baseline the *P*-founded replicates are drawn upward and the *N*-founded downward, height log₂ of the best finite fitness, one hairline per replicate, a red mark where a replicate first produced a loop-class offspring. **The vertical scale is global:** one doubling is the same height in every strip, the baseline is each pair's shared founder fitness, and no strip is autoscaled; STEPS already showed that global scaling can be visually quiet and honest, and that discipline is kept. The figure is a mirror: identical trajectories give symmetry, no adaptation a flat line, divergence asymmetry, convergence a strip asymmetric on the left and symmetric on the right. Orientation (*P* up, *N* down) is fixed now. A draft renderer with a synthetic mock exists (`scripts/e4_mirror.py --mock`); the artist names the work after a synthetic mock and before any trajectory, as before. Title territory noted by the reviewer, for later and not from results: consequence rather than difference.

## 13. Vocabulary

Program, genotype, founder, population, generation, selection rule, fitness as §4, finite run, loop class, accessibility. Not life, organism, evolvability, open-ended evolution; adaptation only in the operational sense of §11. The claim is never that history changes deterministic programs; a silent history yields a different genotype whose neighbourhood differs, and that difference may or may not be visible under selection.

## 14. Before the pre-registration is written

1. Fitness F2, no cap — recommended, decide.
2. Mechanics: *N* = 64, *G* = 256, *R* = 16, truncation with seeded random ties, mean of log₂ as the per-founder statistic — decide.
3. Scope: core only; walks 1 and 2 preserved — decide.
4. Length amendment: 64 bytes for E4, justified by the predictor — decide.
5. Smallest effect of interest ρ = 0.3, and the stated precision — decide.
6. Then: extract and seal the predictor table from the E3 snapshot (a small droplet, about a dollar, the only step that spends anything before the run); render the synthetic mock at print scale; write the pre-registration; sign; anchor; run.
