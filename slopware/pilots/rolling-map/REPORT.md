# Rolling-map pilot — report

**Exploratory pilot. Not E5, not pre-registered, not anchored, no publication claim. Nothing here touches E4 or world v0.** Protocol: `PROTOCOL.md` (written before the run). Data: `results/runs/` (1,150 arm-run records), `results/analysis/` (tables and plots from `analysis.py`, written before the results were read). Notes and the two operational incidents: `NOTES.md`.

## Verdict

**MAYBE — RUN ANOTHER PILOT.** Refreshing the map re-acquires short-range predictive information (a fresh map's accessibility correlates with the rise over the next 4 to 32 generations at ρ 0.45 to 0.67 over 6,494 events, where the founder's map at generation 1 predicts nothing, ρ within ±0.08). But the way this pilot *used* the map changed selection almost never, so the mapping arms differ from baseline only by the budget they burned: no arm beats baseline at equal compute, and the most frequent refresh is clearly worse. The information is there; this mechanism does not spend it.

**The three questions.**
1. *Does refreshing the map restore short-range predictive information?* Yes, descriptively and strongly in this record, with the caveat below: later refreshes ρ(+4) 0.45, ρ(+8) 0.59, ρ(+16) 0.64, ρ(+32) 0.60; first maps ρ ≈ 0 at every horizon; founder maps against the baseline arm's rise ρ ≈ 0 at every generation 1 to 255.
2. *Does using refreshed information improve search under equal compute?* No. Median paired final advantage against baseline: static 0.000 (176 of 191 exact ties), rolling-8 −0.234 doublings (50 wins, 124 losses), rolling-16 −0.078, rolling-32 −0.057, rolling-64 0.000. No arm's bootstrap band for the median advantage reaches above zero.
3. *If yes, how often is the map worth refreshing?* Not answerable from a mechanism that did not act. On cost alone the ranking is monotone: the less often an arm mapped, the closer it stayed to baseline.

## What was run

Pilot world with frozen block context (determinism proven on the 23 E4 context-reading genomes, `determinism.txt`), probe A only. 24 founders (both founders of 12 seeded E4 pairs), 8 replicates, population 64, K = 512 seeded one-byte mutants per map, one mapped genome per refresh, six arms with an identical budget of 16,384 logical evaluations each (rolling-8's mapping cost, 8,192, given to every arm as allowance), on a reused DigitalOcean c-32 (32 vCPU, 64 GB, $1.00/h) with 32 workers. Started 2026-10-14 02:49:54 UTC, stopped on the artist's word at 03:52 UTC with 1,150 of 1,152 arm-runs final (one founder-replicate missing one arm, dropped from the paired analysis: 191 of 192 complete). Benchmark, choices and the pre-run reasoning are in `PROTOCOL.md`.

## Results

**A. Final fitness at equal budget** (rise above founder, doublings; `results/analysis/A-final.png`)

| arm | median rise | mean rise | median paired vs baseline | wins / losses / ties | pair-bootstrap of the median |
|---|---|---|---|---|---|
| baseline | 2.663 | 3.034 | — | — | — |
| static | 2.632 | 3.025 | 0.000 | 0 / 15 / 176 | [0, 0] |
| rolling-8 | 2.415 | 2.577 | −0.234 | 50 / 124 / 17 | [−0.290, −0.138] |
| rolling-16 | 2.632 | 2.968 | −0.078 | 66 / 100 / 16 | [−0.123, 0] |
| rolling-32 | 2.632 | 2.866 | −0.057 | 55 / 102 / 34 | [−0.078, 0] |
| rolling-64 | 2.585 | 3.049 | 0.000 | 45 / 75 / 71 | [0, 0] |

**B. Paired advantage trajectories** (`B-advantage.png`). By budget spent, every mapping arm dips below baseline while it is paying for its first maps and recovers toward zero as baseline's extra generations stop paying off; rolling-8 never recovers. By generation the arms are indistinguishable: median advantage exactly 0 at generations 8, 16, 32, 64 and 128 for every arm. That is the key mechanical fact: at equal generation the mapping arms have the same per-generation progress as baseline, so the map did not change which candidates survived.

Why it did not act: at generation 1 all 64 slots hold the founder, so one map gives every lineage the same value; later, the lowest-slot top-class genome is re-measured and its descendants inherit one shared value while they dominate the top class, so the exact-tie rule rarely meets two candidates with *different* known values. "Unknown counts as 0" means a lineage with a positive value is preferred over an unmapped one, but almost everything in the top class is mapped-descended. The static arm is baseline plus a 512-evaluation tax (identical final populations in 176 of 191 runs).

**C. Fresh-map prediction** (`C-prediction.png`, `F-horizon.png`)

| events | n | ρ(+4) | ρ(+8) | ρ(+16) | ρ(+32) |
|---|---|---|---|---|---|
| first map, generation 1 (all mapping arms) | 955 | −0.08 | −0.01 | −0.01 | 0.00 |
| later refreshes (rolling arms) | 6,494 | 0.45 | 0.59 | 0.64 | 0.60 |
| rolling-8 | 3,056 | 0.45 | 0.58 | 0.62 | 0.57 |
| rolling-16 | 2,101 | 0.49 | 0.62 | 0.66 | 0.60 |
| rolling-32 | 1,337 | 0.53 | 0.65 | 0.71 | 0.66 |
| rolling-64 | 764 | 0.62 | 0.71 | 0.74 | 0.73 |
| later refreshes by distance from the previous map: 1–2 bytes | 103 | 0.41 | 0.49 | 0.56 | 0.56 |
| 3–6 bytes | 1,109 | 0.38 | 0.52 | 0.55 | 0.51 |
| 7 or more bytes | 5,281 | 0.43 | 0.57 | 0.63 | 0.58 |

The fresh-map horizon (F2) rises from ρ 0.20 at +1 to 0.64 at +16 and holds to +32; the founder-map horizon against the baseline arm (F1, the clean E4-style curve at this scale) is flat within ±0.1 across all 255 generations. Mapping events 7,449; a map found at least one upward mutant 50.7% of the time; mean 1.75 hits per 512. **Caveat, strongest skeptical reading:** a fresh map that samples an upward mutant among 512 says a step exists one byte away; ordinary search proposes 64 one-byte children per generation from the same neighbourhood and takes such a step within a few generations whether or not the map saw it. Much of the ρ ≈ 0.6 may be "a step exists" against "no step exists" (a population at a local plateau has accessibility 0 and rises 0), not a graded property of the neighbourhood. The disjoint-map pilot that follows is built to separate those.

**D. Founders** (`D-founders.png`, all 24 in `results/analysis/tables.md`). The rolling-8 loss is general, not driven by a few founders: its mean paired advantage is −0.457 with all founders and −0.458 without its two most extreme (45N, 1N). Rolling-16's mean flips sign without its two most extreme founders (−0.043 → +0.021), so its small loss is concentrated. Founder 2P shows a −4.4 doubling median loss under rolling-8: its baseline populations reach the one 15-doubling run of the pilot and rolling-8's 128 generations do not.

**E. Compute** (sums over 191 complete runs)

| arm | logical | physical | cache hits | mapping | search | hf | run-seconds |
|---|---|---|---|---|---|---|---|
| baseline | 3,124,293 | 3,123,643 | 650 | 0 | 3,124,293 | 0 | 14,990 |
| static | 3,124,418 | 3,121,469 | 2,949 | 97,785 | 3,026,633 | 0 | 13,785 |
| rolling-8 | 3,124,972 | 3,099,363 | 25,609 | 1,564,560 | 1,560,412 | 0 | 10,953 |
| rolling-16 | 3,124,857 | 3,106,787 | 18,070 | 1,075,643 | 2,049,214 | 0 | 11,926 |
| rolling-32 | 3,124,424 | 3,112,468 | 11,956 | 684,504 | 2,439,920 | 0 | 11,633 |
| rolling-64 | 3,124,297 | 3,116,750 | 7,547 | 391,143 | 2,733,154 | 0 | 11,642 |

Logical imbalance between arms, per run: 3.6 evaluations (the leftover below one generation). Physical executions per run relative to baseline: rolling-8 −127, rolling-16 −88, rolling-32 −59, rolling-64 −36, static −11: the mapping arms did slightly *less* physical work because mapped mutants later re-proposed were cache hits. Rolling did not secretly receive more compute; it received slightly less. Wall-clock 62 minutes on 32 workers (plus a 2-minute benchmark); droplet cost for the pilot about $1.10 at $1.00/h; 18.7 million logical evaluations.

## Failure modes, checked

- Rolling wins only through hidden compute: no; it lost, with less physical work.
- Mapping costs more than the information is worth: yes at this K and this mechanism; the cost is the whole story of arm A.
- Ordinary extra mutation beats mapping: yes.
- Static as good as rolling: static equals baseline (the map never discriminated).
- Results driven by a few founders: rolling-8's loss is general; rolling-16's small loss is concentrated in two founders.
- Interval barely matters: it matters only as cost; less mapping, less loss.
- Exact ties make A1 unusable as a secondary criterion: ties are abundant (the cut fell inside a tie in 99.8% of generations) but the *known-value* structure made them useless: lineages share inherited values.
- Preferring high-accessibility genomes sacrifices immediate fitness: not observed; per-generation progress identical to baseline.
- Accessibility predictive again after remapping: yes, descriptively, with the circularity caveat.
- Fresh-map prediction decays with distance or time: no decay with distance from the previous map (ρ similar at 1–2, 3–6, 7+ bytes); over time after the map, ρ rises to +16 then holds to +32 within the window measured.

## Operational record

Two incidents, both in `NOTES.md` and `results/relaunch.log`: worker memory growth (relaunched under a 1.5 GB heap cap at 03:00 UTC) and slow founders serialising six shards (remaining arm-runs re-sharded one per worker at 03:36 UTC; the first re-shard carried a harness bug that gave single-arm workers a smaller budget, its 51 files were deleted, the harness now takes `--budget` explicitly and every surviving file carries 16,384; the analysis asserts the equality). The benchmark had been run on founders other than the chosen ones, which is why the slow founders surprised; a real experiment benchmarks on the founders that will run and shards at the arm-run level from the start. One founder-replicate (one arm) was still running when the pilot was stopped and is excluded from the paired analysis.

## For a next pilot (not designed here)

See `NOTES.md`: a mechanism that can actually discriminate (several top genomes mapped per refresh at lower K, or measurement spent as proposals), inheritance with decay, and measure-only maps in the baseline arm to de-confound prediction from use. The disjoint-map pilot that follows addresses the circularity caveat first.
