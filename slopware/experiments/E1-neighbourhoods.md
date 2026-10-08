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
