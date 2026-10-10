# E3 — design notes, not a pre-registration

**Status: notes, 2026-10-10, superseded the same day by the candidate pre-registration [`E3-somewhere-else.md`](E3-somewhere-else.md), which redirects E3 from population selection to accessibility (does neutral history change what is reachable next?). Kept for the record of how the question moved. Nothing here binds anything.** The pre-registration, when written, follows the E1/E2 form and is signed and anchored before a single placement.

## What E2 settled, and what it did not

E2 showed traversable ground: neutral walks can rewrite a program entirely while preserving behaviour (W1), persistence climbs from every parent (W2), and half of the improvements found were enabled by the neutral drift before them (W5). So a population experiment is justified. E2 also showed two things E3 must design around rather than inherit:

1. **Counting instructions rewards loops.** Under "never shorter", 63 of 440 walks found loops that run until the gas is gone; lifespans of 118,478 are gas exhaustion, not accomplishment. A population under a persistence fitness would be taken over by loops within a few generations. E3 must say what it rewards before it runs, and the reward must not be satisfiable by looping.
2. **The harness is deterministic in its stream and not quite in its measurement.** 51 of 176 re-run trajectories differed, through instrument timeouts under load recorded as outcomes. E3's harness retries transient instrument errors (bounded, logged) instead of recording them, so that a re-run reproduces the record exactly, which is what §7.8 should demand again.

## Open design questions, in the order they have to be decided

- **Population and heredity.** E3 is the first experiment with heredity between individuals: a population of genomes, each generation produced from the previous by copying (infrastructure, R1) with variation. Size, generations, and whether the population is one or several islands.
- **Variation.** Single-byte substitution again, at fixed length (constitution decision 2), or the first reopening of length (insertion, deletion, duplication) by amendment. E2's result that walks exhaust the 64 bytes argues for deciding this first.
- **Selection regimes, disclosed.** Drift as the null (uniform reproduction; required). A disclosed regime that is not "more instructions": candidates are clean halt under a bounded gas budget, returning data, a storage write that survives, or survival under a world perturbation. Each must be stated as "we select for X" and each must be checked for its degenerate solution the way loops were found here.
- **Fitness must not be reproduction.** The constitution forbids "fitness += reproduces" as a first move; it stays forbidden.
- **Stopping rule** (constitution decision 7): generations and placements fixed in advance; no extension after looking.
- **Cohort.** The parents could be E2's 88, the whole genesis population, or a post-E1 cohort under Part X-C's mechanical rule. Decide before looking at anything from the cohort.
- **Controls.** Drift against regime, as E2 used arm against arm; and E1's device of fresh random genomes beside collected ones if the cohort is collected programs.
- **Measurements fixed in advance.** Heritable phenotype change beyond drift (the scorecard's "evolution" row needs its definition stated here, and the word stays reserved until it is met); lineage depth; the contingency question from E2 (`IDEAS.md`: identical starts, replicate runs, do trajectories diverge while population properties converge).
- **Detectors.** E2's set, plus `child_has_code` with the shared-byte test ready, since populations will have many more CREATE executions.
- **The edition.** Fixed in the pre-registration before results, as THREADS and STEPS were; a form that draws lineages rather than individuals.
- **Compute.** E2 cost about $7 for 8.8 million placements. A population of 1,000 for 1,000 generations is a million placements per generation-step and must be budgeted before it is designed.

## Harness work before any E3 run

- Retry on instrument error (probe timeout, receipt timeout), bounded and logged; an attempt that still fails after retries is recorded as a harness failure, never as a program outcome.
- A W4 detector that does not depend on a real transaction's timing.
- Population bookkeeping: lineage ids as the constitution's ontology specifies (`childId = keccak256(parentIds ‖ operator ‖ seed ‖ experimentVersion)`).
- A re-run check that passes bit for bit on the smoke test before signing.

## Not before

No E3 pre-registration is written until the artist has read E2 as historical record and decided the length question. The dataset from E2 is rich; questions asked of it now are exploratory analyses or future experiments, not E2 and not E3.
