# E2 — Walks on the living

**Pre-registration. Draft of 2026-10-09, unsigned. Nothing below is run until it is signed and anchored.**

E2 is the second pre-registered experiment of SLOPWARE and follows E1 (`E1-neighbourhoods.md`, record root `bed1b583…`). E1 found a flat landscape: 98.4% of one-byte changes are neutral, 0.37% lengthen a life, and the only new behaviour came from a parent already standing two instructions from a `CREATE`. E2 asks the question E1 could not: starting from the programs that live, can a program wander through byte-space without dying, and can lifespan grow by accumulating rare lengthening steps? Whether there is connected ground under the living programs, or only islands, decides whether any population experiment is worth running.

## 1. Question

From a living program, what does a long sequence of single-byte substitutions do, when (a) only changes that leave behaviour identical are kept, and (b) only changes that do not shorten the program's life are kept? Is there a neutral network, and does it extend beyond the bytes the program never reads? Does a walk that refuses to die climb, and how far?

## 2. Hypotheses, stated before the run

**W1 (the neutral network is the tail).** Under arm A (neutral), accepted steps almost never touch a byte the current program executes or reads. *Prediction:* fewer than 1% of accepted neutral steps change a byte at a position below the current genome's `consumedBytes`; the executed prefix of a walk's final genome is identical to its parent's in at least 90% of walks. If false, there is neutral variation inside executed code, which is where cryptic variation would come from.

**W2 (climbing).** Under arm B (persistence: steps that do not shorten probe-A lifespan are kept), lifespan grows. *Prediction, derived from E1:* per attempt, the chance of a lengthening step for a living parent is of order 0.5–1% (E1 measured 0.37% over all parents and about 1% for the longest-lived), so a 10,000-attempt walk should accept tens of lengthening steps. Pre-specified thresholds: "evolution can move" if the median walk at least doubles its parent's lifespan; "evolution can move far" if any walk reaches 32 or more instructions on probe A, which exceeds anything in E1's 26 million children (maximum 12) and is the harness's loop threshold.

**W3 (prefix prediction holds along the walk).** E1's H2 keeps working off the parent's current state: a step is neutral if and only if its position is at or beyond the current genome's `consumedBytes`, with exceptions below 2%. *Prediction:* at least 98% of attempted steps are classified correctly by this rule, in both arms, at every stage of the walk.

**W4 (what climbing reaches).** Along arm B walks, behaviours appear that E1 saw rarely: clean halts, returned data, surviving storage writes, `CREATE` executed. *Prediction:* clean halts and returned data become common (reached by at least half of arm-B walks); `CREATE` is executed in at least one walk. The never-seen set is updated after E1 and fixed here: `external_call` (a CALL-family instruction executed and the call completing), `create_succeeds` (a `CREATE`/`CREATE2` that increments the creating program's nonce), `child_has_code` (a created account with non-empty code), `loop` (out of gas after more than 32 instructions). *Prediction:* `create_succeeds` occurs; `child_has_code` does not. Any occurrence of `child_has_code` or `external_call` is replicated three times on fresh chains before being reported as anything but a candidate, and if replicated moves the scorecard's self-reproduction row to CANDIDATE (`child_has_code`) or the environment row to CANDIDATE (`external_call`).

**W5 (the two arms differ).** Arm B walks end with longer lifespans than arm A walks from the same parent (trivially true if W2 holds) and travel less far in Hamming distance from the parent, because accepted lengthening steps constrain later neutrality. *Prediction:* median Hamming distance from parent after 10,000 attempts is lower in arm B than in arm A for at least 75% of parents. This is the first measurement of the cost of climbing.

Hypotheses are judged by the pre-specified statistics in §7. Confirming or rejecting any is a result and is published either way.

## 3. Population

**Parents.** Every E1 parent, genesis or control, whose probe-A lifespan under world v0 was three or more instructions: 88 parents (42 genesis, 46 control), fixed in `E2/parents.json` (sha256 `0df39d8a510a11de5f783ed575eadb1343e93f10f5f36aa5eefb887789260b01`) from E1's sealed aggregates. Genesis and control parents are treated identically and reported both pooled and by set; E1's H1 says they are the same material.

**No new controls.** The comparison in E2 is between arms, and against E1's measured rates.

## 4. Operators and the walk

Exactly one operator, as in E1: **single-byte substitution**, length fixed at 64 (constitution v1, decision 2).

A walk is a sequence of attempts. At attempt *t* the proposal is `position, value = stream(seed, parent, arm, walk, t)` with `position` uniform in 0..63 and `value` uniform over the 255 bytes other than the current byte at that position, from the lab's seeded stream (`keccak256(seed ‖ counter)`, seed `"E2-walks"`). The proposed child is placed and probed; its signature (E1 §6, unchanged) and probe-A lifespan are recorded; then:

- **Arm A, neutral:** the step is accepted if and only if the child's full signature equals the current genome's.
- **Arm B, persistence:** the step is accepted if and only if the child is instantiable and its probe-A lifespan is greater than or equal to the current genome's. This is selection, disclosed: *we select for not dying sooner.*

If accepted, the child becomes the current genome. Every attempt is recorded whether accepted or not. A child whose first byte is `0xEF` cannot be placed, is recorded `instantiable: false`, and is rejected in both arms.

**Budget and stopping rule (constitution v1, decision 7).** 10,000 attempts per walk; 5 walks per parent per arm; 88 × 2 × 5 × 10,000 = 8,800,000 attempts. The walk stops at attempt 10,000 and nowhere else. Nothing is extended, restarted or pruned after looking at a trajectory. If the machine fails, a walk is resumed from its last recorded attempt using the same stream, which makes the record identical to an uninterrupted run.

## 5. Environment: world v0, frozen

Identical to E1 (`E2/world-v0.json`, sha256 `5a115d87c7ce9b31c0f0262e92bb7ee96e4c0a38a0b86d375a9fb10069f06190`): one private Anvil chain per shard, hardfork osaka, chain id 31337, the 11-byte loader, five probes A–E with E1's payloads, 1,000,000 gas per call, structLog tracing with the stack disabled, caller key index 9. A fresh chain every 10 accepted genomes or 1,000 attempts, whichever comes first, so nonce and state drift cannot accumulate.

One addition for W4: after probes A–E, if any probe executed `CREATE` or `CREATE2` and halted cleanly, the probe is re-sent as a real transaction on the same chain, and the creating program's nonce and the code at its nonce-derived creation address are read. This is the `create_succeeds` / `child_has_code` detector. It is a measurement, not a mechanism.

## 6. Phenotype and its signature

E1 §6, unchanged. Behaviours reached, as E1, plus the two detectors above.

## 7. Analysis, pre-specified

1. **Per walk:** accepted steps, final genome, final lifespan, maximum lifespan reached, Hamming distance from parent at the end and every 1,000 attempts, the attempt index of every lengthening step, behaviours reached and the attempt at which each was first reached, prefix-rule accuracy.
2. **W1:** fraction of accepted arm-A steps at positions below the current `consumedBytes`; fraction of arm-A walks whose final executed prefix equals the parent's. Thresholds 1% and 90%.
3. **W2:** per parent, the median over its five arm-B walks of final lifespan ÷ parent lifespan; the population median of that; the maximum probe-A lifespan over all arm-B walks. Thresholds: median ≥ 2; any ≥ 32.
4. **W3:** per attempt, predicted class (neutral iff position ≥ current `consumedBytes`) versus observed; accuracy by arm and by attempt decile. Threshold 98%.
5. **W4:** fraction of arm-B walks reaching each behaviour; count of `create_succeeds`, `child_has_code`, `external_call`, `loop` events; each `child_has_code` or `external_call` event replicated three times.
6. **W5:** per parent, median final Hamming distance in arm B versus arm A; fraction of parents with B < A. Threshold 75%.
7. **Noise:** one walk per parent per arm is re-run from the same seed on a fresh machine; trajectories must be identical. Any difference is reported and the affected parent flagged.

No analysis is added after the run without being labelled exploratory. Scripts: `scripts/e2_analysis.py`, frozen at the signing commit.

## 8. Record

`record/<arm>/walks-<from>-<to>.jsonl`: one line per attempt (parent, arm, walk, attempt, position, value, accepted, signature hash, probe-A lifespan, behaviours, and for accepted steps the new genome's bytes); `record/<arm>/summaries-<from>-<to>.jsonl`: one line per walk with the §7.1 statistics. Manifest, root hash, and anchoring as E1 §8. Compute and cost as E1 §10–11: one c-16 droplet, about three hours, under $5. The record (about 10 GB) is snapshotted and the machine destroyed, as E1.

## 9. The research edition (constitution amendment 1)

**STEPS.** One strip per parent, 88 strips stacked in `parents.json` order. In each strip the x axis is the attempt, 0 to 10,000, and the y axis is probe-A lifespan. Arm A's five walks are drawn in faint grey (they should be flat); arm B's five walks in black, stepping up at every accepted lengthening step. A red mark where a walk first reaches a never-seen behaviour. The parent's lifespan is a hairline. Rules fixed in `scripts/e2_steps.py` (keccak256 of the script at the signing commit recorded below), generated from the sealed record, one 1/1, minted by the keeper on the research editions contract, offered on the E2 results page after publication, proceeds to the artist, no rights conferred.

## 10. What must not happen

- No step is chosen by anyone. The stream is the only source of proposals.
- No walk is extended, restarted or discarded after looking at it.
- No mechanism is added to the world. The detectors read traces and state; they change nothing.
- Nothing is placed on a public chain. Everything runs on private chains (the lab's `connect()` refuses otherwise).
- The installer is not touched.

## 11. Publication

- `summaries/E2` and this document with results appended under a dated heading; a results page at `slopware.fun/e2` built the way E1's was (static, Markdown mirror, `llms.txt` updated); one line per living release on the readings page saying how far its walks went.
- The scorecard changes only as §2 W4 specifies.
- If every hypothesis holds as predicted, the headline is that the neutral network under a living program is its unread tail, that persistence can climb, and how far. If W2 fails, the headline is that lifespan does not accumulate under single-byte substitution at fixed length, and E5 (length change) is the next question.

## 12. After E2

If W2 holds and the climb is real, E3 (a population under disclosed selection) is pre-registered with a stopping rule. If not, the fixed-length rule is reopened by constitutional amendment before anything else is run.

## Sign-off

*To be signed by the artist. Script hashes to be filled at signing: `scripts/e2_steps.py`, `scripts/e2_analysis.py`, `src/e2.ts`. Then anchored on Ethereum from the keeper, with `parents.json`, `world-v0.json` and this document's hash in the message, before the first attempt is placed.*
