# Rolling-map pilot — protocol, written before the run

**Status: exploratory pilot.** Not E5. Not pre-registered in the sense of the experiments (no signature, no Ethereum anchor), not a publication claim. It does not touch E4, its sealed record, its record volume or world v0. Everything about it lives under `slopware/pilots/rolling-map/`. Written 2026-10-14 before the run started; the choices below were fixed from the pre-run benchmark alone and are not changed after any pilot outcome is seen.

## Question

E4's horizon (E4-after.md Amendment 7) was descriptive: the generation-0 one-mutant accessibility map (E3's A1) said nothing at generation 1, became informative over the next few dozen generations, peaked near generation 31, and was no longer distinguishable from zero from generation 64 on. Does periodically **refreshing** a local accessibility map, and using it as a secondary search signal, improve evolutionary search **under an equal total evaluation budget**? And is predictive information **re-acquired** by a fresh map after the original has gone stale?

## World: `world-pilot.json` (PILOT world, not v0)

E4 found that world v0 never froze the block context (Amendment 6). The pilot world fixes it: anvil 1.8.5 started with `--timestamp 1700000000 --no-mining --base-fee 1000000000 --gas-price 2000000000 --gas-limit 30000000 --hardfork osaka --chain-id 31337`; the program is placed with `anvil_setCode` at the fixed address `0x…0e4000` instead of a deployment transaction, so no block is ever mined; every probe is a `debug_traceCall` against block 0 from the same caller (anvil key 9) with 1,000,000 gas, as in v0. TIMESTAMP, NUMBER (0), PREVRANDAO (0), BLOCKHASH(0), BASEFEE, GASPRICE, COINBASE, GASLIMIT, CHAINID, ADDRESS and the balances are therefore constants of the world file. A program whose first byte is 0xEF is uninstantiable and never evaluated, as in v0. **Fitness is read from probe A only** (the F2 concept: instruction count of a finite run; out of gas after more than 32 traced instructions is the loop class and never continues); the other probes are not run, which is what makes the pilot about 30× faster per evaluation than E4.

**Determinism proof (before the run):** `scripts/pilot_world_test.ts` evaluated the 23 E4 genomes that read TIMESTAMP / PREVRANDAO / BLOCKHASH and had differed between machines (Amendment 6), 3 times on each of 3 fresh anvil instances started seconds apart, plus a program that returns twelve context values. **23 of 23 identical; context bytes identical.** Output: `determinism.txt`.

## Pre-run benchmark (`bench.txt`)

Static arm (one K = 256 mapping) for 64 generations, one founder per worker, W workers at once, on the pilot droplet:

| workers | aggregate while running | per-worker median | harness failures | retries | memory |
|---|---|---|---|---|---|
| 8 | 507 exec/s (wall incl. start-up) | 620 exec/s | 0 | 0 | 3 of 62 GB |
| 16 | 963 exec/s | 445 exec/s | 0 | 0 | 6 of 62 GB |
| 32 | 1,727 exec/s | 257 exec/s | 0 | 0 | 10 of 62 GB |

Steady state at 32 workers is about 32 × 257 ≈ 8,000 exec/s; the wall-clock aggregate is lower because each worker spends about a minute starting. **Chosen: 32 workers** (the highest aggregate measured, no failures, no memory pressure). Sizing assumes 6,000 exec/s to leave margin.

**Tie statistics from the benchmark (2,026 generations):** the top fitness class had more than one candidate in 84% of generations, the selection cut fell inside an exact fitness tie in 99.8%, and the top class held a median of 17 distinct genomes. **Exact fitness ties are common; the equivalence rule is exact equality of fitness.** No wider rule is needed or used.

## Pilot size (fixed from the benchmark)

- **Founders:** 24 = the first 12 pairs of the seeded order of E4's 88 pairs (keccak256 of `PILOT-rolling-map-2026-10-14-pairs` ‖ uint32 q, ascending), both *P* and *N* of each: pairs **45, 81, 2, 83, 52, 32, 22, 75, 1, 21, 58, 84** (5 genesis, 7 control). Chosen without looking at any E4 outcome; `founders.json` is E4's, unchanged.
- **Replicates:** 8 per founder (seeds 0..7). **Population:** 64. **Generations of search:** G = 128 for the arm with the most mapping; the others run more generations on the same budget (below).
- **Mapping sample K = 512** one-byte mutants per mapped genome, seeded (`mappos`, `mapval` streams), uninstantiable mutants counted in K and not evaluated, as A1's denominator counts them. Exhaustive mapping (16,320) was not used: at ~8,000 exec/s one exhaustive map costs 2 seconds and the rolling-8 arm would need 16 per run, 2 million evaluations per run, 60 hours in all. K = 512 gives an expected 3 to 4 upward hits per map at E4's median A1 of 0.0066; coarse, and that coarseness is part of what the pilot measures.
- **Mapped genomes per refresh S = 1:** the lowest-slot genome of the top fitness class.
- **Budget per (founder, replicate, arm):** E = G × 64 + A, A = rolling-8's mapping cost = ⌈128/8⌉ × 512 = 8,192, so **E = 16,384 logical evaluations**, identical for every arm; a run stops when the remainder cannot pay for a full generation of 64. So rolling-8 runs 128 generations; rolling-16 about 192; rolling-32 about 224; rolling-64 about 240; static about 248; baseline 255. The founder's own evaluation is paid by every arm alike.
- **Total:** 24 × 8 × 6 arms × 16,384 = 18.9 million logical evaluations; at 6,000 exec/s about 52 minutes, at 8,000 about 40. Target was 1 to 2 hours; the size was kept at the brief's initial aim because it fits.
- **Workers:** 32 shards, one anvil each, runs assigned round-robin over (pair, founder, replicate); each shard runs all six arms of a run consecutively.

## Arms

All arms use E4's operator and rule otherwise: 64 proposals per generation, parent slot uniform, one byte changed to a uniformly different value, candidates = 64 survivors + finite offspring, 64 kept, *B_g* non-decreasing.

1. **baseline** — no mapping; the whole budget is proposals.
2. **static** — one map at generation 1; the value persists through inheritance.
3. **rolling8 / rolling16 / rolling32 / rolling64** — a map at generations 1, 1+I, 1+2I, … The intervals are exploratory; 32 is included because E4's horizon peaked near there, not as a predicted optimum.

## "Use the map", fixed now

Fitness is always primary. Candidates sort by fitness descending; **among exact fitness ties only**, by accessibility descending, where a candidate's accessibility is its own measurement if it was mapped, else the value inherited from its parent (offspring of a mapped genome carry the parent's value and the generation it was measured), and **an unknown accessibility counts as 0**, so only positive information ever discriminates; remaining ties by E4's seeded tie key, then survivor before offspring, lower slot first. Mapped mutants are measurement only: they never enter the population. They are cached, so an identical later proposal is a cache hit; that is counted and reported as the arms' effective-compute imbalance. Nothing here is tuned after the run.

## Seeds

Domain-separated keccak streams as E4 §5.7 with the seed string `PILOT-rolling-map-2026-10-14`; domains `parent`, `position`, `value`, `tie`, `tie-survivor`, `mappos`, `mapval`. The arm is not part of the seed, so all arms of a run share one proposal stream for as long as their populations agree (common random numbers).

## Compute accounting (the main control)

Per run: logical evaluations (the budget unit, cache hits included, as E4 counted), physical executions, cache hits, mapping evaluations, search evaluations, harness failures, retries, wall-clock. Reported per arm in total and as paired differences. Any arm that received more logical evaluations than another is a bug and voids the comparison.

## Record

`results/runs/<pair>-<f>-<replicate>-<arm>.jsonl`: a header; one line per generation (*B_g*, best, median fitness, loop and uninstantiable counts, tie statistics, known-accessibility count among the chosen, budget left, cumulative counters); one line per mapping event (genome, generation, fitness, accessibility, upward and loop counts, Hamming distance from the founder and from the previous mapped genome, cost); a final line (survivors with fitness and accessibility, counters, seconds). `results/logs/shard-*.log`. `environment.json`.

## Analysis (`analysis.py`, written before the results are read; descriptive)

A. Final best fitness (log₂) per arm at equal budget: median, mean, paired distributions; per founder. B. Paired advantage trajectories, arm − baseline, by cumulative logical evaluations spent (the fair axis) and by generation (the familiar one). C. Fresh-map prediction: for every mapping event, the fresh accessibility against the subsequent rise of *B* over +4, +8, +16, +32 generations (Spearman, descriptive, pooled and by refresh index), and against distance travelled since the previous map. D. Founder-level results, every founder shown. E. Compute per arm. Failure modes checked explicitly: more compute for rolling, mapping cost dominating, extra mutation beating mapping, static as good as rolling, a few founders driving the result, interval irrelevance, ties unusable, accessibility preference costing immediate fitness, information re-acquired or not, fresh-map prediction decaying with distance and time. No p-values as confirmatory evidence; one verdict from the four allowed; the three questions answered plainly.

## What is not done

No change to these choices after the run starts; no rerun with an improvement folded in (ideas go to `NOTES.md`); no claim of discovery; nothing anchored, minted or published.
