# Experiment E1 — Neighbourhoods

**Status:** pre-registered and signed, not run. No code exists for it yet.
**Constitution:** version 1 (2026-10-08). **Roadmap:** Part XI, "the minimum next release."
**Written:** 2026-10-08, at release 803. **Signed:** 2026-10-08 by the artist.

This document is written before the experiment so that the hypotheses, the protocol, and the analysis cannot be shaped by the results. Once signed, it is frozen; anything learned during the run that requires a change is recorded as a dated amendment below the sign-off, and the run is restarted if the change affects results.

---

## 1. Question

What is the one-mutant neighbourhood of a program nobody wrote?

For every genesis genome, we generate every program that differs from it in exactly one byte, place each on the lab chain under the frozen environment, and record what it does. This gives heredity (every mutant has a parent) and variation (one byte) their first appearance in SLOPWARE, with the infrastructure openly doing the copying (reproduction level **R1**). It also gives the robustness baseline that every later comparison needs.

## 2. Hypotheses, stated before the run

**H1 (no privilege).** Genesis genomes are not special. The distribution of neighbourhood statistics (neutral, altered, lengthened, shortened, clean-halt fractions) for the genesis set is indistinguishable from the same statistics for matched fresh random genomes. *Prediction:* no difference beyond sampling error. A difference would mean the mainnet population is biased relative to the lab's distribution, which would itself be a finding about the chain's randomness.

**H2 (the executed prefix).** A mutation is neutral unless it touches a byte the parent executes or reads. For a parent that halts at instruction *k*, mutations at positions beyond the bytes consumed by those *k* instructions change nothing. *Prediction:* the neutral fraction per genome is approximately `(64 − consumedBytes) / 64`, where `consumedBytes` is read off the parent's disassembly and trace. Since 80% of parents die on their first byte, the predicted population-wide neutral fraction is roughly 0.95.

**H3 (the first byte).** For a parent that dies on its first byte, a substitution at position 0 produces a program that survives its first instruction exactly when the new byte is one of the 55 operand-free opcodes. *Prediction:* 55/255 = 21.6% of position-0 mutants of such parents live at least two instructions; (8 + 55)/255 ≈ 24.7% halt cleanly or live, counting the eight immediate `STOP`-like outcomes. This is arithmetic; the experiment tests whether the harness agrees with it.

**H4 (lengthening is rare).** Fewer than 3% of all one-mutants live longer than their parent, and fewer than 0.5% reach a clean halt the parent did not. *Prediction:* from H2 and H3, lengthening requires hitting an executed byte with a surviving replacement; the bound is derived, not fitted.

**H5 (nothing new under one mutation).** No one-mutant exhibits any behaviour absent from the million-program study: no external call completing, no child program resulting from CREATE, no loop. *Prediction:* true. If false, the neighbourhood of a specific genesis genome contains something the uniform distribution did not show in a million draws, which would be the first result of heredity worth the name.

Hypotheses are judged with the pre-specified statistics in Section 7. Rejecting or confirming any of them is a result and is published either way.

## 3. Population

**Genesis set.** Every installer release requested at or before the **snapshot block *S***, recorded at the start of the run. Releases after *S* are not in E1; they are generation 0 of a later era. *S* becomes the roadmap's block *G* if E1's first mutation event is the first ever recorded; otherwise *G* is already fixed.

Both installed and refused releases are included (constitution v1, decision 5). Refused genomes are placeable only when the position-0 mutation changes `0xEF`; their other mutants are recorded as `instantiable: false` without placement.

**Control set.** One fresh random genome of 64 bytes per genesis genome, drawn from the lab's seeded stream (`seed = "E1-control"`), subjected to the identical protocol. The control set is generated before any genesis neighbourhood is run.

**Expected size.** About 805 genesis genomes and 805 controls, 1,610 parents; 16,320 one-mutants each; about 26.3 million placements plus 1,610 unmutated re-placements in triplicate for noise.

## 4. Operators

Exactly one: **single-byte substitution**. Every position 0..63, every value ≠ the parent's byte: 64 × 255 = 16,320 children per parent, enumerated, not sampled. Length is fixed at 64 (constitution v1, decision 2). No insertion, deletion, duplication, or recombination in E1.

Mutation events are deterministic and need no seed: `child = parent with byte[position] := value`.

## 5. Environment: world v0, frozen

| parameter | value |
|---|---|
| chain | Anvil, hardfork `osaka`, chain id 31337, fresh state per placement batch |
| placement | the installer's 11-byte loader, verified `extcodehash == keccak(bytes)` |
| gas per call | 1,000,000 |
| probes | A empty calldata · B 32 zero bytes · C 32 fixed random bytes · D fixed 4-byte selector + 32-byte argument · E empty calldata with 1 wei |
| probe payloads | drawn once from `seed = "E1-world-v0"` and held constant for every placement in E1 |
| tracer | `debug_traceCall` struct logs, stack disabled, depth tracked from the instruction stream |
| caller | Anvil account 9 |

World v0 is named, hashed (`worldId = keccak256(canonical JSON of this table)`), and never changed. A later experiment with different probes is a different world.

**Known environmental confounders, recorded not removed:** programs that read `ADDRESS`, `BALANCE`, `NUMBER`, `TIMESTAMP`, or `BLOCKHASH` see lab values, not mainnet values; placements at different addresses see different `ADDRESS`. The triplicate re-placements of each unmutated parent measure how much phenotype varies from these alone.

## 6. Phenotype and its signature

For each placement, five probe results. The **signature** of a placement is the tuple, over probes A–E, of `(outcome class, instruction count, last opcode executed, return data length, return data hash, SSTORE count, TSTORE count, LOG count, CREATE/CREATE2 count, CALL-family count)`.

Two placements have the **same phenotype** when their signatures are identical. A child is:

- **neutral** if its signature equals its parent's (parent's signature taken from the parent's own placement in E1, not from `readings.json`);
- **lethal** if the parent reaches a clean halt in some probe and the child does not;
- **lengthened** if the child's probe-A instruction count exceeds the parent's;
- **shortened** if it is lower;
- **altered** otherwise (same length, different signature).

A child **reaches** a behaviour (clean halt, state write that survives, data returned, CREATE executed, external call executed, out of gas, input-dependence across probes) if any probe shows it; reaching is recorded per behaviour regardless of the parent.

These definitions are frozen with this document.

## 7. Analysis, pre-specified

1. **Per parent:** neutral, altered, lengthened, shortened, lethal fractions; count of children reaching each behaviour; `consumedBytes` from the parent's trace; predicted neutral fraction under H2.
2. **H1:** for each fraction, the genesis-set distribution versus the control-set distribution, compared with a two-sample Kolmogorov–Smirnov test and the difference in means with a 95% bootstrap interval (10,000 resamples). Pre-specified threshold for "indistinguishable": |difference in means| < 0.01 and KS p > 0.01 for all five fractions. Anything else is reported as a difference, with its size.
3. **H2:** observed versus predicted neutral fraction per parent; report the median absolute error and the fraction of parents within ±0.02 of prediction. Pre-specified threshold: median absolute error < 0.01.
4. **H3:** among parents dying at their first byte, the fraction of position-0 children living ≥ 2 instructions; 95% interval; compared with 0.216.
5. **H4:** population-wide lengthened fraction and new-clean-halt fraction with intervals; compared with the stated bounds.
6. **H5:** a list, possibly empty, of every child reaching a behaviour the million-program study never showed, each replicated three times on fresh chains before being reported as anything but a candidate.
7. **Noise:** the fraction of triplicate re-placements with identical signatures; any parent whose own re-placements disagree is flagged `environment-sensitive` and its neighbourhood statistics are reported with and without it.

No analysis is added after the run without being labelled exploratory.

## 8. Record

Appended to the evolutionary record (roadmap Part XII), content-addressed, with this document's hash in every entry.

```
experiments/E1  { id, constitutionVersion: 1, protocolHash, snapshotBlock: S, worldId, harnessVersion, anvilVersion, gitCommit, startedAt, finishedAt }
genotypes/      { id: keccak(bytes), bytes, length: 64, firstSeen: { kind: 'birth', release } | { kind: 'control', seed, index } | { kind: 'mutation', eventId } }
events/         { id: keccak(parentId ‖ 'substitute' ‖ position ‖ value ‖ 'E1'), kind: 'mutation', operator: 'substitute', parent, position, value, child, experiment: 'E1' }
placements/     { genotypeId, worldId, address, codeMatches, probes: [ ...full ProbeResult... ], signature, experiment: 'E1' }
summaries/E1    { per-parent fractions; per-hypothesis statistics; the H5 list }
```

Everything in `placements/` for a dead-at-first-byte child is small; the full record is estimated at 10–20 GB and lives outside the repository with its root hash committed. Summaries and the H5 list live in the repository.

## 9. Reproducibility

Anyone with the repository can regenerate every child from `(parent bytes, position, value)`, re-run any placement under world v0 on their own Anvil of the recorded version, and compare signatures. The control set regenerates from its seed. The root hash of the record is committed, and published on-chain as calldata once the run completes (venue: an open question in the roadmap; for E1, the commit hash alone is the minimum).

## 10. Compute and time

About 26 million placements at the lab's measured 400 per second is roughly 18 hours on one machine with ten workers, plus retries. Run overnight twice, or on a second machine. No swarm. If the full enumeration proves infeasible, the pre-specified fallback is a stratified sample of every position with 16 of 255 values chosen by the seeded stream, recorded as such; hypotheses are then judged on the sample with wider intervals.

## 11. Cost

Zero on mainnet. No contract, no transaction, no fee, no token. The installer is untouched; births continue throughout and enter the genesis set only if requested at or before *S*.

## 12. What must not happen

- Choosing which parents to run first by interest; the order is release number, ascending, then controls.
- Adding an operator, a probe, or a gas ceiling mid-run.
- Changing the signature or the fraction definitions after seeing data.
- Publishing the lively neighbourhoods first or only.
- Letting the readings' vocabulary into `placements/` or `summaries/`.
- Deploying any child to any public chain.

## 13. Publication

- `summaries/E1` and this document, with results appended under a dated heading, in the repository.
- A `descent` view on the readings page: for each release, its neighbourhood fractions and any children on the H5 list, in the readings' voice, with the record's numbers beneath, and one sentence stating that these children were made by infrastructure (R1) and exist only on the lab's chain.
- The scorecard: no status changes unless H5 produces a replicated candidate, in which case the relevant criterion moves to CANDIDATE with the placement linked.
- If every hypothesis is confirmed, the headline is that one mutation of a random program is, statistically, another random program, and the first heredity experiment found nothing heredity could carry. That is published as the result.

## 14. After E1

E1 does not advance any era by itself. It establishes the record's habits and the baseline. The next pre-registration, for populations and selection regimes, is written only after E1's results are published, and must include the stopping rule required by constitution v1, decision 7.

---

## Sign-off

Artist: Bushi (@bushibuilds) · date: 2026-10-08 · protocol frozen at commit 20d23d1

Amendments after sign-off are listed here with dates.

### Amendment 1 — 2026-10-08, before the run

- **Snapshot block *S* = 26149410.** The genesis set is the 803 releases requested at or before it (801 installed, 2 refused). `genesis.json`, `controls.json` and `world-v0.json` (worldId `0x7d9128756067823a0cc0fdc092f9880d49be94e01f62a3d7d412389628f5b50c`) are committed beside this document.
- **Storage compaction, no effect on results.** §8 said every placement stores the full probe result. For a child whose signature is identical to its parent's, the record stores the signature and the compact per-probe fields but not the opcode list; the parent's own placements store everything. Children that differ from their parent, or that reach any behaviour, store the full opcode list. Any placement can be regenerated from `(parent bytes, position, value)` under world v0.
- **Noise probe.** A parent's three unmutated placements are the reference; the first is the reference signature for classification, as §6 says.

### Amendment 2 — 2026-10-08, during the run

- **Execution.** Run on a rented 16-vCPU machine (Ubuntu 24.04, Node v24.21.0, Anvil 1.8.5, repository commit `1a2d70b`), as eight shards of ten workers each, four per set, each shard owning its own Anvil restarted every ten parents. The record is on an attached volume; its root hash is committed when the run completes.
- **Restart.** The run began as two shards, was stopped after four parents to widen to eight, and the widened shards resumed one parent early. Releases 2 and 404 therefore have two complete summaries and two parents (releases 3 and 405) have partial duplicate placements from the stopped shards. The analysis keeps the first complete summary per genotype and dedupes placements by event id. No placement result is altered by this.

### Amendment 3 — 2026-10-08, anchor on Ethereum

The frozen protocol and its three data files were hashed and the hashes written to Ethereum mainnet as calldata, from the keeper wallet to itself, in transaction `0x43cf98936519c7d068b631a15144d16a405680308cea9bc4edb9fe0bd85829ec`, block 26149568. The calldata is the UTF-8 text in `E1/anchor.txt`:

| file | keccak256 at commit `1d7a407` |
|---|---|
| `E1-neighbourhoods.md` (this document, before this amendment) | `0xbaa09001fae948bbe026225401043f7bb0433e56b336e6527a2fc460bbe4c631` |
| `E1/genesis.json` | `0x59daa8d4c5b44c44c9a17b12dfcd3568d29fcad3ee725da35f2a90601437b9ba` |
| `E1/controls.json` | `0x6d22dc0cc555cf219c249103108ea7eda38f3a5b4d11ae6f3a350cbf036e267b` |
| `E1/world-v0.json` | `0x7c4b04d9a8e9981c03a793a4f78c839ed855f9e2bdaf0f83f0fa445b3131f327` |

To verify: check out commit `1d7a407`, hash each file with keccak256, and compare with the calldata of that transaction. The anchor was sent after the run started but before any results existed; for every later experiment the anchor transaction precedes the first placement. The record's root hash will be anchored the same way when the run completes.

### Amendment 4 — 2026-10-08, during the run

One shard (genesis indices 1–200) exited at 23:4x UTC after 140 parents when its Anvil did not answer within the runner's ten-second start window under a machine load of about 14; the error is preserved in `logs/genesis-1-200.crashed.txt`. The runner was changed to wait up to a minute and retry three times (commit `57b1e58`), and the shard was resumed from index 141 as `genesis-141-200`. Parent 141's partial placements from the crashed shard are duplicates by event id and are deduplicated in analysis. No placement result is altered.

### Amendment 5 — 2026-10-09 00:16 UTC, during the run

Two more shards still running the original ten-second start code exited the same way (genesis indices 201–401 after index 360; 403–602 after index 562); their logs are preserved as `*.crashed.txt`. Both were resumed from the next index with the patched runner (`genesis-361-401`, `genesis-563-602`). As before, the partial placements of indices 361 and 563 are duplicates by event id and are deduplicated in analysis. The record itself (about 27 GB) will remain on a snapshot of the droplet's volume; the manifest, root hash, parent summaries, logs, analysis and readings artefacts are brought into the repository or `results/`.

### Amendment 6 — 2026-10-08 20:55 ET, before results: the E1 research edition

Under constitution amendment 1 (roadmap Part X-B), E1 has one research edition, **THREADS**, defined here before any result is known. It is generated from the sealed record by `scripts/e1_threads.py` (keccak256 of the script at this commit: `0x67bd975b34a16877b3c31de91c78887eaa4c368a6f9f64bf0d366a334e9a97e6`), genesis programs only, in release order, with the red mark at three or more executed instructions. The rules are stated in the script's header and are not changed after this amendment. The edition's metadata will carry the record's root hash, the anchor transaction, and this script hash. It is offered only after the results below are published, on the E1 results page, and confers no rights over anything.

### Amendment 7 — 2026-10-08 21:30 ET, before results: who mints the edition

THREADS is minted from the keeper's wallet (`0xB847754313D6320f43396F885d168b0B433b913f`) on a creator contract separate from the installer, with the artist's wallet as a second admin; the keeper is the creator of record and proceeds are swept to the artist (roadmap Part X-B, "Who signs"). This changes nothing about what the edition depicts or when it is offered.

### Amendment 8 — 2026-10-09 02:30 UTC, after the run, before publication: a defect in the pre-specified analysis code

The run finished at 01:57 UTC with 1,608 parent summaries (1,600 distinct instantiable genotypes after de-duplication: 801 genesis, 799 control; the 2 refused genesis and 4 refused control genomes have no neighbourhood) and 26,110,350 placements; record root `bed1b583ca6f51919bb2d5f967e2153d64e113a13dd8fdff7a21318822f1dd1d`.

The first run of `scripts/e1_analysis.py` reported H1 as *not* indistinguishable: every difference in means was far inside the 0.01 threshold, but the Kolmogorov–Smirnov p-values were effectively zero with D between 0.39 and 0.996. Inspection showed the two-sample KS implementation advanced one sample at a time through tied values and took the maximum ECDF difference inside tie groups, which on these heavily tied data (most parents share exactly the same fractions) produces a spurious D. The function was corrected to compare the ECDFs only after consuming all equal values on both sides, and to return p = 1 when D = 0. Nothing else in the script changed. Both results files are kept: `summaries/results-before-ks-fix.json` and `summaries/results.json`. With the corrected test, H1's five KS p-values are 0.94, 0.99, 0.61, 1.00 and 1.00 and the pre-specified threshold is met. This is a correction of an implementation defect, not a change of statistic or threshold; it is recorded here because the protocol says no analysis changes after the run go unlabelled.

Two further notes from the same reading of the results, before any exploratory work: (1) the script's H3 statistic uses all position-0 children as its denominator, where §7.4 specifies children of parents that die at their first byte; the §7.4 statistic is computed from the per-position aggregates and reported in the results section below, with the script's broader figure beside it. (2) One parent, release 16, is flagged `environment-sensitive` under §7.7 (its triplicate re-placements disagreed; 99.94% of all triplicates were identical) and its statistics are reported with and without it as the protocol requires.

## Results — 2026-10-09

Run 2026-10-08 18:30 UTC to 2026-10-09 01:57 UTC on one DigitalOcean c-16 droplet, eight shards, each with its own anvil under world v0. Record sealed at 02:00 UTC: 43 files, 28 GB, root `bed1b583ca6f51919bb2d5f967e2153d64e113a13dd8fdff7a21318822f1dd1d`, anchored on Ethereum from the keeper in transaction `0xad4f7470be6f337111dd651e97621cb60d5c8c39ae33ecd71d0efc46c624e07c` (block 26,151,785) and kept as the volume snapshot `slopware-e1-record-20261009`. Compute cost about $6. The droplet and its volume were destroyed on 2026-10-09 after the snapshot was verified at 28.15 GiB; the snapshot (`slopware-e1-record-20261009`, DigitalOcean, about $1.70 a month) is the only full copy of the record, and the parent summaries, manifest and root are in the repository.

**Population as run.** 803 genesis genotypes (every release before block 26,149,410; 2 refused by Ethereum and therefore without a neighbourhood) and 803 controls (4 refused), so 801 and 799 neighbourhoods. 26,110,350 placements after de-duplication (38,626 placements and 8 parent summaries were recorded twice because of shard restarts and are counted once). Triplicate re-placements agreed in 99.94% of cases; one parent, release 16, disagreed with itself and is flagged environment-sensitive; the genesis means are identical to six decimals with and without it.

**H1 (no privilege) — held.** Genesis versus control, mean of each fraction (difference in percentage points, 95% bootstrap interval, corrected KS p): neutral 98.387% vs 98.333% (+0.055, [−0.044, +0.154], p 0.94); altered 0.906% vs 0.915% (−0.009, [−0.042, +0.022], p 0.99); lengthened 0.369% vs 0.374% (−0.006, [−0.015, +0.004], p 0.61); shortened 0.338% vs 0.378% (−0.040, [−0.127, +0.044], p 1.00); lethal 0.011% vs 0.009% (+0.002, [−0.017, +0.022], p 1.00). Every difference is inside the 0.01 threshold and every KS p is above 0.01. The programs people collected are statistically the programs the lab would have drawn. (The KS implementation was corrected after the run; amendment 8.)

**H2 (the executed prefix) — held.** Median absolute error between the predicted neutral fraction, (64 − bytes consumed) / 64, and the observed one: 0.0062, below the 0.01 threshold. 87% of parents are within ±0.02 of their prediction. Bytes a program never reaches can be anything.

**H3 (the first byte) — not held as written; the harness agrees with the corrected arithmetic exactly.** As registered (§7.4: parents dying at their first byte, position-0 children living at least two instructions): 1,275 such parents, 323,850 placeable position-0 children (254 per parent, since the `0xEF` replacement cannot be placed), of which 68,849 lived at least two instructions: 21.26% [21.12%, 21.40%], against the registered 21.57% (55/255), which lies outside the interval. The discrepancy is two counting errors in the pre-registration, not in the harness. First, exactly 54 replacement values ever let such a program live, the 32 PUSHes and 22 operand-free opcodes; `STOP` was wrongly counted as a 55th, and it halts at once. Second, the denominator is 254, not 255, because one replacement is unplaceable. 54/254 = 21.26%, inside the interval and equal to the observed fraction to three decimals. The registered "eight immediate STOP-like outcomes" were also wrong: only `0x00` halts cleanly as a first byte, and the clean-or-live fraction is 21.65% [21.51%, 21.80%], against 55/254 = 21.65% with the corrected count (the registered 63/255 = 24.71% is far outside). The script's broader figure over all position-0 children of all parents, 21.18% [21.05%, 21.31%], is reported for completeness. The corrected comparisons are labelled exploratory because their numbers were fixed after the run.

**H4 (lengthening is rare) — held.** 97,062 of 26,110,350 one-mutants lived longer than their parent: 0.372% (upper bound 0.374%), against the 3% bound. 5,400 halted cleanly where the parent did not: 0.021% (upper bound 0.021%), against the 0.5% bound. Both bounds were loose by an order of magnitude.

**H5 (nothing new under one mutation) — not held, narrowly.** One one-mutant reached a flag the million-program study never set. Parent: control 182 (genotype `0xf8524bc5…`), not a collected program. Child: byte 32 changed from `0x50` (`POP`) to `0x65` (`PUSH6`); event `0xccea0c3a…`. Under probes A–D it executes `PUSH11 · PUSH18 · CALLVALUE · PUSH6 · PUSH14 · CREATE · PUSH12 · STOP` and halts cleanly; the flag is `child_may_exist`, defined in the harness as "`CREATE` executed inside a call that halts cleanly". Replicated three times on fresh chains with identical signatures (`src/e1-replicate.ts`), so per §7.6 it is reported as a result, not a candidate. What the `CREATE` does: it offers 2.46 × 10³² wei of value from an account holding none, so the creation fails, pushes 0, and the program rests. Nothing is created, not even an empty account: a real transaction on a fresh chain leaves the child's nonce at 1 (exploratory check; a creation would have made it 2). The parent, with `POP` in place of `PUSH6`, reaches the same `CREATE` with a different stack and the same failure. So the new thing is not reproduction and not its counterfeit; it is a program that attempts a creation, is refused, and then halts cleanly instead of dying, a combination a million random draws never produced. The scorecard's self-reproduction row stays NOT OBSERVED and gains a note; no scale moves.

**Descriptives, exploratory.** Children lived at most 11 instructions (genesis) and 12 (control); 5.25% of genesis children and 5.75% of control children reached three. Among 26 million one-mutants: 100,650 clean halts, 27 that returned data, 16 whose storage write survived to a clean halt, 10 that executed `CREATE`, 432 that ran out of gas, none that called another contract, none that looped. The parent with the most longer-lived children is release 462, with 186.

**What this means, in three sentences.** One byte changed at random in a random program is, with 98.4% certainty, the same program; the rest is almost entirely a different way to die. The programs people bought behave under mutation exactly like programs nobody bought, so there is nothing in the catalogue that the lab's distribution does not already contain. The single new thing in twenty-six million tries was a program that tries to create another, is refused for offering money it does not have, and then rests instead of dying, which is not reproduction, and is still more than anything in the million-program study did.

**What happens next.** Nothing changes in the installer. The scorecard changes no status; one row gains a note. Any second experiment is pre-registered first; the obvious candidate is random walks on the parents that live three or more instructions (IDEAS.md), with the parent rule written before looking further at these results.
