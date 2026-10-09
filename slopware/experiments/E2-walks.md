# E2 — Walks on the living

**Pre-registration. Draft 2 of 2026-10-09, unsigned. Nothing below is run until it is signed and anchored.**

E2 is the second pre-registered experiment of SLOPWARE and follows E1 (`E1-neighbourhoods.md`, record root `bed1b583…`). E1 found that almost all local mutation is neutral: 98.4% of one-byte changes leave behaviour identical, 0.37% lengthen a run, and the only never-seen behaviour came from a parent already standing two instructions from a `CREATE`. E1 asked what is next door. E2 asks whether there is a road: is that neutrality empty space, or navigable ground? Starting from the E1 programs that executed for three or more instructions, can a long sequence of single-byte changes move through byte-space without shortening a run, and does neutral movement change which improvements become reachable without changing the current behaviour?

"The living" in the title is the readings' figurative voice. In this document the parents are the programs that ran long enough to enter E2, and execution is not called life.

## 1. Questions

1. Under neutral acceptance, where does a walk go: only through the bytes the program never reads, or also through executed code?
2. Under persistence acceptance (never shorter), does probe-A lifespan climb, and how far?
3. Does E1's simple prefix predictor keep working as mutations accumulate?
4. Which behaviours do persistence walks reach, and when?
5. Do lengthening steps depend on the neutral steps that preceded them, or were they available from the parent all along?

## 2. Hypotheses and pre-specified measurements

**W1 (neutral movement and cryptic variation).** Under arm A, accepted steps almost never touch a byte the current program executes or reads. *Prediction:* fewer than 1% of accepted neutral steps change a byte at a position below the current genome's `consumedBytes`; in at least 90% of arm-A walks the final genome's executed prefix is byte-identical to the parent's. The deeper question, measured whether or not the prediction holds: can neutral drift change which future behaviours are accessible without changing the current behaviour? Genotypes with the same measured phenotype but different accessible futures would be the analogue of cryptic variation. W5 measures this directly.

**W2 (persistence can climb).** Under arm B, probe-A lifespan grows. Arm B is a hill climb with neutral drift, not evolution: there is no population, no heredity between walks, no differential reproduction. What it can show is that non-decreasing mutational paths exist through genotype space under the persistence criterion. *Prediction, derived from E1:* the chance of a lengthening step per attempt for these parents is of order 0.5–1% (E1 measured 0.37% over all parents and about 1% for the longest-lived), so a 10,000-attempt walk should accept tens of lengthening steps. Pre-specified thresholds: **persistence can climb** if the population median of (final lifespan ÷ parent lifespan) is at least 2; **persistence can climb far** if any walk reaches 32 or more instructions on probe A, which exceeds anything in E1's 26 million children (maximum 12) and is the harness's loop threshold. The word "evolution" is reserved for a later experiment with heredity, variation and differential reproduction.

**W3 (the naive prefix model under accumulated mutation).** E1's H2 used a simple predictor: a step is neutral if and only if its position is at or beyond the current genome's `consumedBytes`. The EVM can break this through `PUSH` immediates, jumps, skipped regions, code inspection and changing control flow, so it is a naive model, not a definition of neutrality. *Prediction:* the predictor remains at least 98% accurate over attempted steps in both arms and in every attempt decile. Its failure would be informative: it would locate where the EVM's structure makes neutrality non-local.

**W4 (behavioural reach, a measurement).** Persistence walks may encounter behaviours absent or rare in their parents. The events of interest are fixed here: `clean_halt`, `returns_data`, `write_survives`, `create_executed`, `external_call`, `create_succeeds` (a `CREATE`/`CREATE2` that increments the creating program's nonce), `child_has_code` (a created account with non-empty code), `loop` (out of gas after more than 32 instructions). Their incidence per walk and the attempt of first appearance are reported. *Prediction, from E1:* clean halts become more frequent under persistence than in the parents (at least half of arm-B walks reach one). **No directional prediction is made for behaviours E1 never observed.** Any `child_has_code` or `external_call` event is replicated three times on fresh chains before being reported as anything but a candidate. What a replicated event means for the scorecard is in §9.

**W5 (is neutrality the road? a measurement).** For every accepted lengthening step in arm B the record holds: the number of accepted neutral steps since the previous lifespan increase, the Hamming distance from the previous plateau genome, and the Hamming distance from the original parent. Then the direct-application test: the same substitution (position, value) is applied to the original parent and to the previous plateau genome, each placed and probed. A lengthening step is classified **(A) already accessible** if applying it to the original parent also lengthens the parent's run, and **(B) enabled by drift** if it does not. The fraction of class B, overall and per parent, is the primary statistic, reported with a 95% interval. *No directional threshold is set*, because no prior data exist. If class B is non-empty, E1's 98.4% neutrality is not dead space but the ground that later improvements stand on; if it is empty, the walks only harvested what the parent already had.

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

**Budget and stopping rule (constitution v1, decision 7).** 10,000 attempts per walk; 5 walks per parent per arm; 88 × 2 × 5 × 10,000 = 8,800,000 attempts, plus the W5 direct-application placements (two per lengthening step, expected in the tens of thousands). A walk stops at attempt 10,000 and nowhere else. Nothing is extended, restarted or pruned after looking at a trajectory. If the machine fails, a walk is resumed from its last recorded attempt using the same stream, which makes the record identical to an uninterrupted run.

## 5. Environment: world v0, frozen, and the same clean state for every genotype

World v0 is identical to E1 (`E2/world-v0.json`, sha256 `5a115d87c7ce9b31c0f0262e92bb7ee96e4c0a38a0b86d375a9fb10069f06190`): private Anvil, hardfork osaka, chain id 31337, the 11-byte loader, five probes A–E with E1's payloads, 1,000,000 gas per call, structLog tracing with the stack disabled, caller key index 9.

**Every genotype is evaluated from the same clean world state.** Before each placement the chain is reverted to a snapshot taken immediately after genesis (`evm_snapshot` / `evm_revert`), so no earlier genome's deployment, storage, balance or created account exists when a genotype is measured, and the deployer's nonce is the same every time, which puts every genotype at the same address. E2 measures the topology of genotype space; persistent environmental modification is for a later experiment. (E1 did not revert between placements; its triplicate noise of 0.06% suggests the drift was negligible, but E2 removes it rather than assuming it.)

**The W4 detectors.** After probes A–E, if any probe executed `CREATE` or `CREATE2` and halted cleanly, that probe is re-sent as a real transaction on the same reverted chain; the creating program's nonce and the code at its nonce-derived creation address are read; then the chain is reverted again. The detectors read state and change nothing that any later genotype can see.

## 6. Phenotype and its signature

E1 §6, unchanged. Behaviours reached as E1, plus `create_succeeds` and `child_has_code` from §5.

## 7. Analysis, pre-specified

1. **Per walk:** accepted steps; final genome; final and maximum probe-A lifespan; Hamming distance from parent at the end and every 1,000 attempts; the attempt index of every lengthening step with its W5 fields; behaviours reached and the attempt of first appearance; prefix-predictor accuracy.
2. **W1:** fraction of accepted arm-A steps at positions below the current `consumedBytes`; fraction of arm-A walks whose final executed prefix equals the parent's. Thresholds 1% and 90%.
3. **W2:** per parent, the median over its five arm-B walks of final lifespan ÷ parent lifespan; the population median of that; the maximum probe-A lifespan over all arm-B walks. Thresholds: median ≥ 2; any ≥ 32.
4. **W3:** per attempt, predicted class (neutral iff position ≥ current `consumedBytes`) versus observed; accuracy by arm and by attempt decile. Threshold 98%.
5. **W4:** fraction of arm-B walks reaching each event; counts and first-appearance attempts; replication of `child_has_code` and `external_call` events.
6. **W5:** for every arm-B lengthening step, neutral steps since the previous increase, Hamming from the previous plateau, Hamming from parent, and the direct-application classification (A or B) against both the original parent and the previous plateau; fraction of class B with a Wilson 95% interval, overall and per parent. No threshold.
7. **Descriptives:** Hamming distance by arm; arm comparison without threshold.
8. **Noise:** one walk per parent per arm is re-run from the same seed on a fresh machine; trajectories must be identical. Any difference is reported and the parent flagged.

No analysis is added after the run without being labelled exploratory. Scripts: `scripts/e2_analysis.py`, frozen at the signing commit.

## 8. Record

`record/<arm>/walks-<from>-<to>.jsonl`: one line per attempt (parent, arm, walk, attempt, position, value, accepted, signature hash, probe-A lifespan, behaviours, and for accepted steps the new genome's bytes); `record/<arm>/summaries-<from>-<to>.jsonl`: one line per walk with the §7.1 statistics; `record/B/lengthening-<from>-<to>.jsonl`: one line per lengthening step with the W5 fields and direct-application results. Manifest, root hash and anchoring as E1 §8. Compute and cost as E1 §10–11: one c-16 droplet, about three to four hours, under $5. The record (about 10 GB) is snapshotted and the machine destroyed, as E1.

## 9. Construction, heredity, reproduction: what a replicated event may move

These are kept apart, in this order of strength:

- **Construction.** A program's own execution causes another code-bearing account to exist (`child_has_code`). A replicated construction event moves a new scorecard row, **construction**, to CANDIDATE. It does not touch self-reproduction.
- **Heredity.** The created code contains information derived from the parent (shared bytes beyond chance). Not a W4 event; if `child_has_code` occurs, the shared-byte test is run and reported as exploratory.
- **Reproduction.** A hereditary descendant can itself produce a hereditary descendant. Nothing in E2 can show this; the self-reproduction row cannot move on E2's evidence.

A replicated `external_call` moves the environment row (E-scale E3/E4) to CANDIDATE. The construction row is added to the scorecard (roadmap Part VII) by amendment at signing, with its counterfeit named: "infrastructure copying; a created account with no code".

## 10. The research edition (constitution amendment 1)

**STEPS.** One strip per parent, 88 strips stacked in `parents.json` order. In each strip the x axis is the attempt, 0 to 10,000, and the y axis is probe-A lifespan, scaled to the largest lifespan any walk reached. Arm A's five walks in faint grey; arm B's five in black, stepping up at every accepted lengthening step; a red mark where a walk first reaches a never-observed behaviour; the parent's lifespan as a hairline. THREADS asked what these programs contain and express; STEPS asks where they can go. If every line stays flat, that is the artwork; if one explodes upward, that is the artwork. Rules fixed in `scripts/e2_steps.py` (keccak256 at the signing commit recorded below), generated from the sealed record, not redesigned after the trajectories are seen except for explicitly labelled production fixes that cannot change interpretation. One 1/1, minted by the keeper on the research editions contract, offered on the E2 results page after publication, proceeds to the artist, no rights conferred.

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

## Sign-off

*To be signed by the artist. Hashes to be filled at signing: `scripts/e2_steps.py`, `scripts/e2_analysis.py`, `src/e2.ts`. Then anchored on Ethereum from the keeper, with `parents.json`, `world-v0.json` and this document's keccak256 in the message, before the first attempt is placed.*
