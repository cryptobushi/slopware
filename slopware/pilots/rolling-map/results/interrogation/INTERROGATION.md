# Interrogation of the rolling-map fresh-map result

**Status.** This analysis was conceived on 2026-10-14 *after* reading the rolling-map pilot's results and report. It is post-hoc and exploratory, on an exploratory pilot. It reads only the preserved records (`results/runs/*.jsonl`) and the published `results/analysis/summary.json`; it modifies nothing; the original analysis and report stand unchanged. Script: `interrogation.py`; numbers: `summary.json`, `tables.md`; figures: `Q1-zero-vs-positive.png`, `Q2-hit-count.png`, `Q6-horizon.png`. No new map metric, no structural feature, no opcode inspection, no flexible model, no re-run.

**Purpose.** Attack the fresh-map result with the simplest explanation: *the map is mostly detecting whether an immediate uphill mutation exists.*

## 1. Reproduction

From the 191 complete founder×replicate runs, by the published rules (mapping arms, refresh index > 0, rise over +h = B at generation g−1+h minus B at g−1): **6,494 later-refresh events**, ρ(accessibility, rise) = **0.4476 (+4, n 6,494), 0.5865 (+8, n 6,279), 0.6426 (+16, n 5,853), 0.6002 (+32, n 5,201)**, equal to the published values to four decimals with the published event counts. `best_observed_gain` is **unavailable**: the record keeps per-map counts (upward hits, loops, uninstantiable, accessibility) and not per-mutant fitness; nothing was re-run to obtain it, and Model 4 is omitted.

## 2. Zero hits against at least one hit (Q1)

3,654 events (56%) found no upward mutant among 512; 2,840 found at least one.

| horizon | 0 hits: median / mean / P(rise>0) | ≥1 hit: median / mean / P(rise>0) | mean difference [founder band] |
|---|---|---|---|
| +4 | 0.00 / 0.02 / 0.11 | 0.00 / 0.09 / 0.48 | 0.07 [0.06, 0.08] |
| +8 | 0.00 / 0.04 / 0.21 | 0.12 / 0.18 / 0.76 | 0.14 [0.12, 0.16] |
| +16 | 0.00 / 0.10 / 0.35 | 0.23 / 0.31 / 0.92 | 0.21 [0.18, 0.23] |
| +32 | 0.07 / 0.21 / 0.56 | 0.42 / 0.53 / 0.96 | 0.33 [0.29, 0.37] |

**The one bit retains 93 to 97% of the correlation:** ρ(any_uphill, rise) = 0.42, 0.56, 0.62, 0.58 against ρ(accessibility, rise) = 0.45, 0.59, 0.64, 0.60 at +4, +8, +16, +32 (founder bands in `tables.md`; the two bands overlap at every horizon). The distributions (`Q1-zero-vs-positive.png`) are a spike at zero for the no-hit maps and a mass displaced to the right for the hit maps.

## 3. One, two, three or more hits (Q2, Q7)

Among the 2,840 positive maps (703 with one hit, 505 with two, 467 with three, 1,165 with four or more; eight-plus is the top of the recorded range):

| horizon | P(rise>0) given 1 hit | 2 hits | 3+ hits | mean rise 1 / 2 / 3 / 4+ |
|---|---|---|---|---|
| +4 | 0.30 [0.27, 0.34] | 0.47 [0.41, 0.53] | 0.56 [0.53, 0.59] | 0.05 / 0.08 / 0.11 / 0.11 |
| +8 | 0.54 [0.49, 0.59] | 0.76 [0.71, 0.80] | 0.86 [0.84, 0.88] | 0.13 / 0.17 / 0.20 / 0.20 |
| +16 | 0.73 [0.68, 0.77] | 0.94 [0.92, 0.96] | 0.99 [0.98, 0.99] | 0.21 / 0.30 / 0.36 / 0.36 |
| +32 | 0.84 [0.80, 0.88] | 0.97 [0.96, 0.99] | 1.00 [0.99, 1.00] | 0.39 / 0.54 / 0.56 / 0.60 |

Hit count matters, in one specific way: **one hit is different from two or more**, and beyond three the means are flat (0.11 / 0.11 at +4, 0.20 / 0.20 at +8, 0.36 / 0.36 at +16). A single hit in 512 is the noisiest reading the instrument can give; two or more say the density of upward mutants is high enough that ordinary search, at 64 proposals a generation, will meet one.

## 4. Within positive maps, the hit-count correlation (Q2)

ρ(hit count, rise) among positive maps: **0.22 [0.18, 0.25] (+4), 0.26 [0.21, 0.31] (+8), 0.29 [0.25, 0.34] (+16), 0.26 [0.22, 0.30] (+32)**. Accessibility gives the identical values (K is fixed; the ranks are the same, confirmed to machine precision). The correlation does not collapse to zero; it falls from about 0.6 to about 0.25, and section 3 shows where it lives: in the step from one hit to two.

## 5. Current fitness (Q3)

Fixed power-of-two bins on the probe-A count. 95% of events sit at fitness 9–32 (3,117 at 9–16, 2,560 at 17–32); 643 at ≤8, 76 at 33–64, 98 at ≥129, none at 65–128. Zero-hit fraction rises with fitness (0.19 at ≤8, 0.55 at 9–16, 0.66 at 17–32, 0.85 at ≥129): higher programs have sparser uphill neighbourhoods, as expected. Within each well-populated stratum the pattern is the pooled pattern: ρ(hits) 0.42 / 0.44 and ρ(any) 0.39 / 0.42 at +4 in the two big strata, 0.62 / 0.61 and 0.60 / 0.58 at +16; P(rise>0 | 0 hits) against P(rise>0 | ≥1 hit) at +16 is 0.37 / 0.92 and 0.32 / 0.88. The within-positive hit-count correlation inside strata is 0.21–0.33. Current fitness does not create the signal and does not remove it; it sets the base rate of hits.

## 6. Founder-held-out simple models (Q4)

Leave-one-founder-out (24 folds), linear predictors, no tuning. OLS on the rise in doublings; logistic on rise > 0. Held-out values:

| horizon | model | R² | ρ(prediction, rise) | AUC (rise>0) |
|---|---|---|---|---|
| +4 | M0 fitness + generation | 0.048 | 0.36 | 0.69 |
| +4 | M1 + any_uphill | 0.066 | 0.45 | 0.77 |
| +4 | M2 + hit count | 0.069 | 0.44 | 0.77 |
| +4 | M3 + both | 0.071 | 0.46 | 0.78 |
| +16 | M0 | 0.037 | 0.59 | 0.73 |
| +16 | M1 | 0.048 | 0.71 | 0.85 |
| +16 | M2 | 0.048 | 0.69 | 0.85 |
| +16 | M3 | 0.050 | 0.71 | 0.85 |
| +32 | M0 | 0.048 | 0.64 | 0.73 |
| +32 | M1 | 0.059 | 0.72 | 0.82 |
| +32 | M2 | 0.059 | 0.71 | 0.83 |
| +32 | M3 | 0.061 | 0.72 | 0.83 |

M0 → M1: the one bit lifts the held-out rank correlation by about 0.1 and the AUC by 0.08 to 0.12 at every horizon. M1 → M2 or M3: at most +0.01 in AUC and +0.005 in R². In a linear model the count adds nothing the bit did not; the gradation of section 3 is a threshold at two hits, not a slope, which a linear count term cannot pick up and which this interrogation did not go looking for with a better model. The R² values are small everywhere: the rise over a fixed window is dominated by things none of these variables carries, and the heavy right tail (the few long-running lineages) sets the RMSE.

## 7. Matched cells (Q5)

Cells of fitness bin × generation bin (≤32, 33–64, 65–128) with any_uphill = 1, every hit bin (1, 2, 3+) holding at least 20 events; six cells qualify at every horizon. Mean rise increases monotonically 1 < 2 < 3+ in 6 of 6 cells at +4, 2 of 6 at +8, 3 of 6 at +16, 2 of 6 at +32; 3+ exceeds 1 in 6, 4, 6, 5 of 6. P(rise>0) is the cleaner reading: at +16 it is 0.71–0.92 for one hit, 0.87–1.00 for two, 0.98–1.00 for three or more in every cell. Comparable events with more sampled hits do improve more often; the size of the improvement does not grow reliably with the count.

## 8. The horizon with one bit (Q6)

| predictor | +1 | +2 | +4 | +8 | +12 | +16 | +24 | +32 |
|---|---|---|---|---|---|---|---|---|
| accessibility (published) | 0.20 | 0.30 | 0.45 | 0.59 | 0.63 | 0.64 | 0.62 | 0.60 |
| hit count | 0.20 | 0.30 | 0.45 | 0.59 | 0.63 | 0.64 | 0.62 | 0.60 |
| any_uphill | 0.19 | 0.28 | 0.42 | 0.56 | 0.60 | 0.62 | 0.60 | 0.58 |

The one bit reproduces the horizon's shape exactly (`Q6-horizon.png`: three curves within 0.03 of one another throughout). The rise toward +16 is therefore not a property of accessibility as a graded quantity. It is what a yes/no about a step one byte away looks like against a rise that takes a few generations to happen: at +1 the step has rarely been taken yet, by +16 nearly every map with a hit has risen (P 0.92) and most without have not (0.35), and after that the no-hit populations start finding steps the map missed, so the contrast fades.

## 9. Plateau and escape (Q7)

P(rise > 0 | 0 hits) = 0.11, 0.21, 0.35, 0.56 at +4, +8, +16, +32; P(rise > 0 | ≥1 hit) = 0.48, 0.76, 0.92, 0.96. Founder bands are a few hundredths wide (`tables.md`). A map with no hit among 512 says the population is probably on a plateau where uphill one-byte steps are rarer than about one in 500; it usually stays put for 16 generations and about half the time for 32. A map with a hit says a route exists; ordinary search, proposing 64 one-byte children a generation, takes it within 16 generations nine times in ten. Zero-hit fraction also tracks how far the mapped genome has moved since the previous map (0.28 within 1–2 bytes, 0.36 at 3–6, 0.61 at 7 or more): a population that moved far since the last refresh is one that climbed, and it is now higher and more often on a plateau.

## 10. Clustered uncertainty

Events are not independent: a run (founder × replicate × rolling arm) contributes 2 to 16 events in series; the four rolling arms of one founder-replicate share a proposal stream until they diverge; the two founders of a pair share a measured signature. Every band above resamples **founders** (24 clusters), the strictest grouping, so all events of a founder move together; the held-out models leave one founder out at a time for the same reason. Bands are percentile 95% from 300 to 1,000 resamples and are descriptive, not tests.

## 11. Strongest skeptical interpretation

A K = 512 map is a coarse yes/no detector for "is there an uphill one-byte step from here". When it says yes, ordinary search finds a step within a few generations because the same neighbourhood is what search samples; when it says no, the population is on a plateau and stays. Two or more hits mean the density is high enough that the yes is reliable; one hit is often noise. Everything measured here, the horizon shape, the fitness strata, the matched cells, the held-out models, is consistent with that and adds nothing beyond it: 93 to 97% of the correlation is the bit, the rest is the bit's reliability.

## Verdict

**A — SIMPLE EXPLANATION SUFFICIENT.** Most of the fresh-map relationship is explained by whether an immediate uphill mutation was observed, with the remainder explained by simple local beneficial-mutation density (one hit against two or more). There is no strong residual reason from this record to posit a richer mapping phenomenon.

## The simplest explanation still consistent with all of the data

The fresh map works as a plateau detector. Sampling 512 one-byte neighbours of the current best program and asking whether any runs longer is, in this record, almost the whole of the signal: the one-bit answer carries 93 to 97% of the rank correlation at every horizon and reproduces the horizon's rise toward +16 and fade thereafter; the count of hits adds a reliability grade, separating a single sampled hit, which is often a fluke of 512 draws, from two or more, which mean uphill steps are dense enough that search at 64 proposals a generation will take one within about 16 generations; and current fitness enters only by setting how often a program sits on a plateau at all. A population whose map says "no step" is usually on a plateau and stays; a population whose map says "a step" takes one, because ordinary search samples the same neighbourhood the map did. Nothing in the record requires a property of the neighbourhood beyond the local density of uphill one-byte mutations, and the founder maps' null result at every generation is the same statement read the other way: a stale yes/no about a place the population has left says nothing about where it is now.
