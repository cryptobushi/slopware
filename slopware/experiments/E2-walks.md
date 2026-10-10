# E2 — Walks on the living

**Pre-registration. Signed 2026-10-09 (see Sign-off). Anchored on Ethereum before the first attempt was placed (Amendment 1).**

E2 is the second pre-registered experiment of SLOPWARE and follows E1 (`E1-neighbourhoods.md`, record root `bed1b583…`). E1 found that almost all local mutation is neutral: 98.4% of one-byte changes leave behaviour identical, 0.37% lengthen a run, and the only never-seen behaviour came from a parent already standing two instructions from a `CREATE`. E1 asked what is next door. E2 asks whether there is a road: is that neutrality empty space, or navigable ground? Starting from the E1 programs that executed for three or more instructions, can a long sequence of single-byte changes move through byte-space without shortening a run, and does neutral movement change which improvements become reachable without changing the current behaviour?

"The living" in the title is the readings' figurative voice. In this document the parents are the programs that ran long enough to enter E2, and execution is not called life.

## 1. Questions

1. Under neutral acceptance, where does a walk go: only through the bytes the program never reads, or also through executed code?
2. Under persistence acceptance (never shorter), does probe-A lifespan climb, and how far?
3. Does E1's simple prefix predictor keep working as mutations accumulate?
4. Which behaviours do persistence walks reach, and when?
5. Do lengthening steps depend on the neutral steps that preceded them, or were they available from the parent all along?

## 2. Hypotheses and pre-specified measurements

**W1 (neutral movement and cryptic variation).** Two descriptions of the current genome's executed region are recorded for every attempted position: the **naive consumed prefix** (the first `consumedBytes` bytes, read off the disassembly and probe-A trace as in E1) and, within it, whether the position is an **executed opcode byte** or a byte of an executed `PUSH` **immediate**. *Prediction:* under arm A, accepted neutral steps almost never change an executed opcode byte: fewer than 1% of them do, and in at least 90% of arm-A walks every executed opcode byte of the final genome equals the parent's. Accepted neutral steps inside `PUSH` immediates are expected to be common and are reported as their own fraction. (The first draft predicted that fewer than 1% of accepted neutral steps would fall anywhere inside the naive prefix; the smoke test of 2026-10-09, 120 attempts on two parents, found 28%, nearly all in immediates, so the prediction was moved to opcode bytes before signing. The naive-prefix fraction is still reported, see W3.) Two neutralities are recorded separately: **local** (the child's signature equals the current genome's, which is the acceptance rule) and **ancestral** (the final genome's signature equals the original parent's). Under the acceptance rule ancestral neutrality is expected to follow from local neutrality; it is verified and reported rather than assumed, because the interesting case is thousands of locally neutral steps accumulating genotypic distance, including inside the bytes the program executes, while the ancestral phenotype holds. The deeper question, measured by W5: can neutral drift change which future behaviours are accessible without changing the current behaviour?

**W2 (persistence can climb).** Under arm B, probe-A lifespan grows. Arm B is a hill climb with neutral drift, not evolution: there is no population, no heredity between walks, no differential reproduction. What it can show is that non-decreasing mutational paths exist through genotype space under the persistence criterion. *Prediction, derived from E1:* the chance of a lengthening step per attempt for these parents is of order 0.5–1% (E1 measured 0.37% over all parents and about 1% for the longest-lived), so a 10,000-attempt walk should accept tens of lengthening steps. Pre-specified thresholds: **persistence can climb** if the population median of (final lifespan ÷ parent lifespan) is at least 2; **persistence can climb far** if any walk reaches 32 or more instructions on probe A, which exceeds anything in E1's 26 million children (maximum 12) and is the harness's loop threshold. The word "evolution" is reserved for a later experiment with heredity, variation and differential reproduction.

**W3 (two prefix models under accumulated mutation).** E1's H2 used the naive model: a step is neutral if and only if its position is at or beyond `consumedBytes`. The EVM breaks this through `PUSH` immediates, jumps, skipped regions, code inspection and changing control flow, so it is an approximation, not a definition of neutrality. E2 tests it and a second model, the **opcode model**: a step is neutral if and only if its position is not an executed opcode byte, so immediates count as neutral. *Predictions, informed by the smoke test:* the naive model's accuracy over attempted steps is below 98% in both arms, failing mostly at immediates (smoke: 73% and 62%); the opcode model's accuracy is at least 98% in both arms and in every attempt decile (smoke: 99% and 98%). Where the opcode model fails locates immediates that matter (jump targets, `CREATE` values, memory offsets) and opcode substitutions that happen to preserve behaviour.

**W4 (behavioural reach, a measurement).** Persistence walks may encounter behaviours absent or rare in their parents. The events of interest are fixed here: `clean_halt`, `returns_data`, `write_survives`, `create_executed`, `external_call`, `create_succeeds` (a `CREATE`/`CREATE2` that increments the creating program's nonce), `child_has_code` (a created account with non-empty code), `loop` (out of gas after more than 32 instructions). Their incidence per walk and the attempt of first appearance are reported. *Prediction, from E1:* clean halts become more frequent under persistence than in the parents (at least half of arm-B walks reach one). **No directional prediction is made for behaviours E1 never observed.** Any `child_has_code` or `external_call` event is replicated three times on fresh chains before being reported as anything but a candidate. What a replicated event means for the scorecard is in §9.

**W5 (is neutrality the road? a measurement).** Define the **plateau-start genome** as the genome immediately after the previous accepted lifespan increase; for the first increase in a walk it is the original parent. For every accepted lengthening step *X* = (position, value) in arm B the record holds: the number of accepted neutral steps since the plateau start, the Hamming distance from the plateau-start genome, and the Hamming distance from the original parent. Then the counterfactual: *X* is applied to the plateau-start genome, which is placed and probed. *X* is classified **(A) accessible without the intervening neutral drift** if it also lengthens the plateau-start genome's probe-A run, and **(B) enabled by intervening neutral drift** if it lengthens the current genome but not the plateau-start genome. Applying *X* to the original parent is recorded as a secondary, descriptive counterfactual and does not define the classes. The fraction of class B, overall and per parent, is the primary statistic, reported with a Wilson 95% interval. *No directional threshold is set*, because no prior data exist. Interpretation is fixed in advance by frequency: zero class-B events is no evidence in E2 that intervening neutral drift opened new improvements; a rare class-B event is an existence proof that neutral drift can open an improvement that was previously inaccessible; many class-B events mean neutral drift is an important route by which improvements become accessible in these walks. The question is a clean one about arbitrary computation and needs no biological metaphor: did phenotypically silent changes alter the program's future possibility space?

**Descriptives, pre-registered.** Hamming distance from parent at the end and every 1,000 attempts, by arm; the comparison of arms (whether persistence walks travel less far than neutral ones) is reported without a threshold.

Hypotheses are judged by the statistics in §7. Confirming or rejecting any is a result and is published either way.

## 3. Population

**Parents.** Every E1 parent, genesis or control, whose probe-A lifespan under world v0 was three or more instructions: 88 parents (42 genesis, 46 control), fixed in `E2/parents.json` (sha256 `0df39d8a510a11de5f783ed575eadb1343e93f10f5f36aa5eefb887789260b01`) from E1's sealed aggregates. Genesis and control parents are treated identically and reported pooled and by set; E1's H1 says they are the same material.

**No new controls.** The comparisons in E2 are between arms, within walks (W5), and against E1's measured rates.

## 4. Operators and the walk

Exactly one operator, as in E1: **single-byte substitution**, length fixed at 64 (constitution v1, decision 2).

A walk is a sequence of attempts. At attempt *t* the proposal is `position, value = stream(seed, parent, arm, walk, t)` with `position` uniform in 0..63 and `value` uniform over the 255 bytes other than the current byte at that position, from the lab's seeded stream (`keccak256(seed ‖ counter)`, seed `"E2-walks"`). The proposed child is evaluated (§5) and its signature (E1 §6, unchanged) and probe-A lifespan recorded; then:

- **Arm A, neutral:** accepted if and only if the child's full signature equals the current genome's.
- **Arm B, persistence:** accepted if and only if the child is instantiable and its probe-A lifespan is greater than or equal to the current genome's. This is selection, disclosed: *we select for not dying sooner.* Equal lifespans are accepted, so arm B is neutral drift with occasional uphill steps.

If accepted, the child becomes the current genome. Every attempt is recorded whether accepted or not. A child whose first byte is `0xEF` cannot be placed, is recorded `instantiable: false`, and is rejected in both arms.

**Budget and stopping rule (constitution v1, decision 7).** 10,000 attempts per walk; 5 walks per parent per arm; 88 × 2 × 5 × 10,000 = 8,800,000 attempts, plus the W5 counterfactual placements (two per lengthening step, expected in the tens of thousands). A walk stops at attempt 10,000 and nowhere else. Nothing is extended, restarted or pruned after looking at a trajectory. If the machine fails, an unfinished walk is re-run from its first attempt with the same stream, which reproduces the same attempts; its earlier partial lines are superseded and the analysis keeps one line per attempt.

## 5. Environment: world v0, frozen, and the same clean state for every genotype

World v0 is identical to E1 (`E2/world-v0.json`, sha256 `5a115d87c7ce9b31c0f0262e92bb7ee96e4c0a38a0b86d375a9fb10069f06190`): private Anvil, hardfork osaka, chain id 31337, the 11-byte loader, five probes A–E with E1's payloads, 1,000,000 gas per call, structLog tracing with the stack disabled, caller key index 9.

**Every genotype is evaluated from the same clean world state.** Before each placement the chain is reverted to a snapshot taken immediately after genesis (`evm_snapshot` / `evm_revert`), so no earlier genome's deployment, storage, balance or created account exists when a genotype is measured, and the deployer's nonce is the same every time, which puts every genotype at the same address. E2 measures the topology of genotype space; persistent environmental modification is for a later experiment. (E1 did not revert between placements; its triplicate noise of 0.06% suggests the drift was negligible, but E2 removes it rather than assuming it.)

**The W4 detectors.** After probes A–E, if any probe executed `CREATE` or `CREATE2` and halted cleanly, that probe is re-sent as a real transaction on the same reverted chain; the creating program's nonce and the code at its nonce-derived creation address are read; then the chain is reverted again. The detectors read state and change nothing that any later genotype can see.

## 6. Phenotype and its signature

E1 §6, unchanged. Behaviours reached as E1, plus `create_succeeds` and `child_has_code` from §5.

## 7. Analysis, pre-specified

1. **Per walk:** accepted steps; final genome; final and maximum probe-A lifespan; local and ancestral neutrality (arm A); Hamming distance from parent at the end and every 1,000 attempts; the attempt index of every lengthening step with its W5 fields; behaviours reached and the attempt of first appearance; prefix-predictor accuracy.
2. **W1:** fraction of accepted arm-A steps on executed opcode bytes, on immediates, and inside the naive prefix; fraction of arm-A walks whose executed opcode bytes are all unchanged at the end. Thresholds 1% (opcode bytes) and 90%.
3. **W2:** per parent, the median over its five arm-B walks of final lifespan ÷ parent lifespan; the population median of that; the maximum probe-A lifespan over all arm-B walks. Thresholds: median ≥ 2; any ≥ 32.
4. **W3:** per attempt, both models' predicted class versus observed; accuracy by model, arm and attempt decile. Thresholds: naive below 98%, opcode at least 98%.
5. **W4:** fraction of arm-B walks reaching each event; counts and first-appearance attempts; replication of `child_has_code` and `external_call` events.
6. **W5:** for every arm-B lengthening step, neutral steps since the plateau start, Hamming from the plateau-start genome, Hamming from parent, the classification (A or B) by applying the step to the plateau-start genome, and the secondary result of applying it to the original parent; fraction of class B with a Wilson 95% interval, overall and per parent. No threshold.
7. **Descriptives:** Hamming distance by arm; arm comparison without threshold.
8. **Noise:** one walk per parent per arm is re-run from the same seed on a fresh machine; trajectories must be identical. Any difference is reported and the parent flagged.

No analysis is added after the run without being labelled exploratory. Scripts: `scripts/e2_analysis.py`, frozen at the signing commit.

## 8. Record

`record/<arm>/walks-<from>-<to>.jsonl`: one line per attempt (parent, arm, walk, attempt, position, value, accepted, signature hash, probe-A lifespan, behaviours, and for accepted steps the new genome's bytes); `record/<arm>/summaries-<from>-<to>.jsonl`: one line per walk with the §7.1 statistics; `record/B/lengthening-<from>-<to>.jsonl`: one line per lengthening step with the W5 fields and direct-application results. Manifest, root hash and anchoring as E1 §8. Compute and cost as E1 §10–11: one droplet (c-32, about four hours at the smoke-tested 26 attempts per second per walker with 32 walkers; or c-16 in about eight), under $5. Each walk is sequential and every attempt reverts the chain, so walkers run in parallel on separate chains. The record (about 10 GB) is snapshotted and the machine destroyed, as E1.

## 9. Construction, heredity, reproduction: what a replicated event may move

These are kept apart, in this order of strength:

- **Construction.** A program's own execution causes another code-bearing account to exist (`child_has_code`). A replicated construction event moves a new scorecard row, **construction**, to CANDIDATE. It does not touch self-reproduction.
- **Heredity.** The created code contains information derived from the parent (shared bytes beyond chance). Not a W4 event; if `child_has_code` occurs, the shared-byte test is run and reported as exploratory.
- **Reproduction.** A hereditary descendant can itself produce a hereditary descendant. Nothing in E2 can show this; the self-reproduction row cannot move on E2's evidence.

A replicated `external_call` establishes only what it shows: a CALL-family instruction executed and completed. It moves the environment scale to the lowest level whose definition it meets, E1 "environment sensed" or, if the call changed state that persists, E3 "environment modified", and never to E4 "functional environmental interaction", which requires a benefit to the program that E2 cannot measure. An interesting opcode is not a life criterion satisfied. The construction row is added to the scorecard (roadmap Part VII) by amendment at signing, with its counterfeit named: "infrastructure copying; a created account with no code".

## 10. The research edition (constitution amendment 1)

**STEPS.** One strip per parent, 88 strips stacked in `parents.json` order. In each strip the x axis is the attempt, 0 to 10,000, and the y axis is probe-A lifespan from 0 to the smallest power of two that is greater than or equal to the maximum probe-A lifespan observed anywhere in the sealed E2 record (a maximum of 29 gives an axis to 32; 33 gives 64; 117 gives 128), the same axis for every strip. Arm A's five walks in faint grey; arm B's five in black, stepping up at every accepted lengthening step; a red mark where a walk first reaches a never-observed behaviour; the parent's lifespan as a hairline. THREADS asked what these programs contain and express; STEPS asks where they can go. If every line stays flat, that is the artwork; if one explodes upward, that is the artwork. Rules fixed in `scripts/e2_steps.py` (keccak256 at the signing commit recorded below), generated from the sealed record, not redesigned after the trajectories are seen except for explicitly labelled production fixes that cannot change interpretation. One 1/1, minted by the keeper on the research editions contract, offered on the E2 results page after publication, proceeds to the artist, no rights conferred.

## 11. What must not happen

- No step is chosen by anyone. The stream is the only source of proposals.
- No walk is extended, restarted or discarded after looking at it.
- No mechanism is added to the world. The detectors read state and change nothing a later genotype can see.
- Nothing is placed on a public chain. Everything runs on private chains (the lab's `connect()` refuses otherwise).
- The installer is not touched.

## 12. Publication

- `summaries/E2` and this document with results appended under a dated heading; a results page at `slopware.fun/e2` built as E1's was (static HTML, Markdown mirror, `llms.txt` updated); one line per E2 parent on the readings page saying how far its walks went.
- The scorecard changes only as §9 specifies.
- The headline follows the record: whether neutral movement stays in the unread tail or enters executed code (W1); whether persistence climbs and how far (W2); whether lengthening steps were available from the parent or opened by drift (W5). "There is nowhere to go" is a complete result and is published as such.

## 13. After E2

Nothing is guaranteed. If W2 and W5 show traversable ground, a population experiment with heredity, variation and disclosed selection (E3) is pre-registered with a stopping rule. If fixed-length single-byte substitution leaves the parents on isolated plateaus, that is reported, and the genome and mutation model (length, insertion, duplication) are reconsidered by constitutional amendment before any population experiment is run.

## 14. Design frozen

The smoke test (two parents, one 60-attempt walk per arm, 2026-10-09) was run before signing to check the harness; it changed W1's and W3's predictions as disclosed in those sections and nothing else. After draft 3 no measurement is added to this design. Whatever we later wish we had measured becomes an exploratory analysis, labelled as such, or a future experiment.

## Sign-off

Signed by the artist, Bushi, on 2026-10-09 at installer release 916 (block 26,156,564), with E1 published and no E2 attempt yet placed. The design, the 88-parent population, the two arms, the budget and stopping rule, the five hypotheses with their thresholds, the pre-specified analysis, the STEPS rules and the frozen scripts named below are fixed. Anything changed after this line is an amendment, dated and placed below it.

Frozen at signing: `src/e2.ts` keccak256 `0x6b1c2e2a1f704a40cb41ab1e307556ff3eb0999f34619d31fa31e9fcb9dda3cc`; `scripts/e2_analysis.py` `0x7a1a8911c3ee67fa5ee642f1b2e7f405964502c36c2acf51958032852e68757d`; `scripts/e2_steps.py` `0xc94740859034805f4c8161078b423fa78f2b5c3f0f0a7c10c6a72abc73e40dac`; `E2/parents.json` sha256 `0df39d8a510a11de5f783ed575eadb1343e93f10f5f36aa5eefb887789260b01`; `E2/world-v0.json` sha256 `5a115d87c7ce9b31c0f0262e92bb7ee96e4c0a38a0b86d375a9fb10069f06190`. Smoke-tested 2026-10-09 (two parents, one 60-attempt walk per arm; disclosed in W1, W3 and §14). The construction row was added to the scorecard (roadmap Part VII) at this signing, per §9.

The anchor transaction, sent by the keeper after this signing commit, is recorded in Amendment 1 below.

## Results — 2026-10-10

Run 2026-10-09 18:20 UTC to 2026-10-10 01:08 UTC on one DigitalOcean c-32 droplet, 32 walkers, each sequential with its own anvil, every genotype evaluated from the same post-genesis snapshot. Record sealed at 01:10 UTC: 113 files, 2.6 GB, root `15849149ca70177ef0a068a74b08134b757237a76be66b9f4e9de6b19b200552`, anchored on Ethereum from the keeper in transaction `0xefd700f6e43fdd68628861f09736010b495fc557d6d982390f8a686547cc4010` (block 26,158,653), kept as the volume snapshot `slopware-e2-record-20261010`. Compute about $7.

**Population as run.** 88 parents (42 genesis, 46 control), 440 neutral walks and 440 persistence walks, exactly 8,800,000 attempts, plus 13,738 counterfactual placements for W5. No harness failures. The two sets behaved alike (median final lifespan under persistence 24.5 for genesis parents, 25.0 for controls; 30 and 33 looping walks) and are pooled below.

**W1 (neutral movement and cryptic variation) — not held.** 0.77% of 4,194,592 accepted neutral steps changed an executed opcode byte, inside the 1% threshold, and 31.6% landed in `PUSH` immediates as expected. But only 6.8% of neutral walks ended with every executed opcode byte unchanged, against the 90% threshold: the rare opcode-level neutral changes (a median of 87 per walk) accumulate over ten thousand attempts. The neutral walks ended a median 63 of 64 bytes from their parents, and 100% of them still had their parent's exact signature (ancestral neutrality verified, not assumed). The neutral network is not only the unread tail: a program can be rewritten entirely, executed code included, without changing what it does.

**W2 (persistence can climb) — held, both thresholds.** The population median of (final lifespan ÷ parent lifespan) was 7.67; all 88 parents doubled; the longest run was 118,478 instructions. Lifespan is an instruction count under a 1,000,000-gas ceiling, and a loop that runs until the gas is gone is the degenerate way to never be shorter: 63 of 440 persistence walks found one (the `loop` flag: out of gas after more than 32 instructions), with a median first appearance at attempt 6,448. Excluding every looping walk, the median parent still multiplied its lifespan by 7.3, the median final lifespan was 23 instructions, 47 walks passed 32, and one (release 432, walk 1) reached 12,259 instructions and halted cleanly without a loop. Persistence climbs, and not only into loops. This is a hill climb with neutral drift, not evolution.

**W3 (two prefix models) — naive as predicted; opcode model not held under persistence.** Naive model accuracy 69.1% (arm A) and 28.5% (arm B), failing at immediates as predicted. Opcode model 99.3% in arm A, flat across deciles, but 95.7% in arm B, below the 98% threshold: once walks acquire jumps and loops, which bytes execute depends on more than their position. The model that works for programs that run straight does not survive control flow.

**W4 (behavioural reach) — the one prediction held; the rest reported.** Of 440 persistence walks: clean halt 100% (prediction: at least half; median first appearance attempt 318); returned data 86%; a storage write surviving to a clean halt 94%; `CREATE` executed 96% and succeeding 78%, every success an empty account; a CALL-family instruction executed 69%; loop 14%; a created account with code: none. Neutral walks reached these rarely (returned data in 62 walks, a succeeding `CREATE` in one, calls and loops in none). Replication (§7.5): all 304 walks' first `external_call` events were re-placed three times on fresh chains; 304 of 304 reproduced the event three times out of three and 304 had identical signatures across all three runs. The scorecard: no `child_has_code`, so the construction row stays NOT OBSERVED; a succeeding `CREATE` of an empty account is the counterfeit named at signing; the CALL executions move the environment scale to E1, environment sensed, and no further, because the harness's flag records the instruction executed and the replication found that in 248 of them no call entered code (the targets were accounts without code, which the EVM treats as completed calls) while in 56 the call entered code: on a clean chain the only account with code is the program itself, so these are self-calls. The deepest, a child of parent 29 (walk 3, attempt 3,439), begins `ADDRESS` and ends `DELEGATECALL`, and lets itself act in its own name 24 levels deep before halting cleanly (`w4-replications.jsonl`). A program calling itself is noted as an observation; it moves no scale, since no self-inspection, inherited information or benefit is involved

**W5 (is neutrality the road?) — "important route", by the reading fixed in advance.** 6,869 accepted lengthening steps under persistence, a median of 15 per walk. Re-applied to the plateau-start genome, 3,417 of them, 49.7% [48.6%, 50.9%], did not lengthen it: class B, enabled by the intervening neutral drift. A median of 130 accepted neutral steps and 50 changed bytes separated each improvement from the plateau it rose from. The secondary counterfactual is starker: only 6.5% of lengthening steps lengthen the original parent. Among the 440 first lengthening steps, whose plateau start is the parent itself, 151 were class B. Restricted to steps that did not produce a loop (final lifespan at most 100), the class-B fraction is 51.0%. Half of every improvement found was unavailable until phenotypically silent changes had altered the program's background.

**Descriptives.** Final Hamming distance from parent, median 63 in both arms; the persistence arm travelled less far than the neutral arm for 32% of parents, so climbing did not cost mobility in these walks. **Noise (§7.8) — the threshold was not met.** One walk per parent per arm (walk 0) was re-run from the same seed on a fresh c-32 droplet: 125 of 176 trajectories were identical attempt for attempt; 51 differed (21 neutral, 30 persistence). Most differences are a single attempt evaluated differently: 28 of the 51 final genomes differ from their counterpart in one byte and 16 differ by exactly one accepted step, and 41 of 51 ended at the same lifespan. Because a persistence walk is path-dependent, one differing attempt can redirect it, and 7 walks diverged by more than twenty bytes. The cause is transient instrumentation under load, not the programs: a probe that times out is recorded as an instrument error with a different signature, and the W4 detector's real transaction timed out 20 times across both runs (`detector_error` flags in the summaries). This is the same failure class as E1's 0.06% triplicate disagreement, at a rate of roughly one attempt in ten thousand. It cannot materially move statistics aggregated over 8,800,000 attempts and 880 walks, but it means the record is not reproducible bit for bit across machines, and every walk should be read as one sample of a harness that is deterministic in its stream and not quite in its measurement. The 51 differing walks are listed in `summaries/rerun/results-noise.json` and their parents are flagged there as the protocol requires. E3's harness must retry instrument errors rather than record them.

*Sensitivity check (exploratory, added 2026-10-10 at the artist's request).* The pre-specified statistics were recomputed on the re-run alone and on the matching walk-0 subset of the main run:

| | main, all 880 walks | main, walk 0 only | re-run, walk 0 |
|---|---|---|---|
| W1 neutral steps on executed opcodes | 0.77% | 0.75% | 0.75% |
| W1 walks with opcodes unchanged | 6.8% | 6.8% | 6.8% |
| W1 ancestral neutrality | 100% | 100% | 100% |
| W2 median parent ratio | 7.67 | 7.67 | 7.67 |
| W2 parents doubled | 88 | 88 | 88 |
| W2 looping walks | 63 of 440 | 11 of 88 | 11 of 88 |
| W2 walks reaching 32 | 110 | 22 | 20 |
| W5 lengthening steps | 6,869 | 1,349 | 1,344 |
| W5 class B | 3,417 (49.7% [48.6, 50.9]) | 658 (48.8% [46.1, 51.4]) | 658 (49.0% [46.3, 51.6]) |
| W5 lengthens the original parent | 6.5% | 6.4% | 6.6% |

The pre-registered trajectory-reproducibility threshold was not met, but this exploratory sensitivity analysis found that the aggregate findings reproduced despite the divergent trajectories: W5 was 48.8% class B in the original 176 walks and 49.0% in their re-runs, and both contained exactly 658 class-B improvements. The harness flaw is a flaw and the noise criterion stays not held; the findings do not depend on it. One observation is recorded without being elevated to a result, since nothing was pre-registered about it: the micro-history was unstable while the macro-statistics were stable. Fifty-one trajectories were perturbed by instrumentation noise, seven of them substantially, and the ensemble properties barely moved. Whether individual trajectories diverge while population-level properties converge is a question a future experiment could test deliberately (`IDEAS.md`).

**What this means, in three sentences.** A program can be rewritten one byte at a time until none of its sixty-four bytes is the one it was born with, and still do exactly what it did. Refuse every change that shortens a program's run and the run grows, from a median of three instructions to about twenty, and for some into loops that stop only when the gas is gone. Half of those gains were impossible until silent changes had rearranged the program's background first: the neutrality E1 found is not dead space, it is the road.

**What happens next.** Nothing changes in the installer. The scorecard moves one row by one level (environment sensed) and no other. W2 and W5 show traversable ground, so a population experiment with heredity, variation and disclosed selection (E3) may be pre-registered, with a stopping rule, and with the loop problem addressed in its design: a persistence criterion that counts instructions rewards loops, and E3 must say what it rewards before it runs, and its harness must retry transient instrument errors so that a re-run reproduces the record exactly. The post-E1 releases remain reserved for pre-registered work (roadmap Part X-C).

### Amendment 1 — 2026-10-09, anchor on Ethereum, before the first attempt

Anchored from the keeper in transaction `0xacb2614447721b5e959171c7e267301e0974be6d7cb691488d2578890ec85d7f` (block 26,156,572). The message (`E2/anchor.txt`) carries this document's keccak256 at the signing commit `50ad530` (`0xcfc6bd5918622a107c4b11c860b79c25c4dbf12afbe2a04653dd573b0afca63e`), the sha256 of `parents.json` and `world-v0.json`, and the keccak256 of the three frozen scripts. No attempt had been placed at that block.

### Note — 2026-10-09, during the run, before any trajectory was seen: STEPS left as signed

A synthetic mock of STEPS (random climbs at an assumed rate, not data) was rendered with the frozen script to preview the picture's form. It showed that with 88 strips and one shared power-of-two axis, modest climbs will be faint. Two amendments were offered (taller strips; taller strips with a log₂ axis). The artist declined both and left STEPS exactly as signed. No E2 trajectory had been looked at. This note changes nothing.

### The edition — 2026-10-10, after publication of the results above

STEPS (E2) was minted by the keeper as token 2 of `0x55540e5bcd1b0a1e2c00de4ae55ef007bde35664` ("SLOPWARE research editions"), image and metadata on Arweave (`ar://8Vz3GoUQ4zX5VTJZFRADQBAh26HAiK83Bg3Gf7mRg9Em`, `ar://8bh9Yk3kKZyCpvBYWWC4c7sjdmE6P9XPt9NP8uSSPzwJ`), mint tx `0x7f21836bfb55ca25206874609687a4e8ab6e7f5fbfbc465086c8ee4501062400`, and listed as Manifold marketplace listing 20931 (tx `0xab4603af161db1aa7cea92fee47ef4f476a98ef422608eb95c5df30564fbb5c4`, block 26,162,625) with a 0.05 ETH reserve and the artist as sole receiver, on the results page `slopware.fun/e2`. Constitution amendment 1 conditions 1–7 checked. The compute droplets were destroyed on 2026-10-10; the record lives on its volume and in the verified 2.79 GiB snapshot `slopware-e2-record-20261010`.
