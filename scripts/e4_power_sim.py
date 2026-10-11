"""E4 design: precision and power of the primary test (Spearman rho across 88 matched pairs between the E3 predictor
difference and the E4 outcome difference) on SYNTHETIC outcomes. No E4 data exist; nothing here is an E4 result.

Model. Pair i has a frozen predictor difference x_i (here the stand-in is E3's recorded difference in longer-child counts,
N60 minus P, over 16,319; the real A1 table comes from the placements). The true founder-level outcome difference d_i is
drawn so that its latent correlation with x_i is rho_true (Gaussian copula on the rank-normal scores of x). Each founder
has R replicate populations whose final log2 best fitness is founder mean + N(0, sigma_rep); the per-founder statistic is
the replicate median; the pair outcome is Delta_i = median_N - median_P. The true founder effect has sd sigma_f, expressed
as the ratio sigma_f / sigma_rep. The test is Spearman on (x_i, Delta_i) with a Fisher-z 95% interval.
"""
import json, glob, math, random, statistics as st
from scipy.stats import spearmanr, norm, rankdata
import numpy as np
rows = {}
for f in glob.glob('slopware/experiments/E3/summaries/neighbourhoods/main/*.jsonl'):
    for l in open(f):
        r = json.loads(l); rows[r['genomeId']] = r
P = {r['parentIndex']: r for r in rows.values() if r['kind'] == 'parent'}
x = np.array([rows[f'E{p}.0.60']['upward'] - P[p]['upward'] for p in sorted(P)]) / 16319.0
n = len(x); z = norm.ppf((rankdata(x) - 0.5) / n)
rng = np.random.default_rng(20261011)
def sim(rho, R, ratio, sigma_rep=1.0, reps=2000, stat='median'):
    hits = 0; widths = []; rhos = []
    med_sd = sigma_rep * (1.2533 if stat == 'median' else 1.0) / math.sqrt(R)  # sd of the per-founder statistic over R replicates
    for _ in range(reps):
        d = rho * z + math.sqrt(1 - rho * rho) * rng.standard_normal(n)
        delta = d * ratio * sigma_rep + rng.normal(0, med_sd * math.sqrt(2), n)
        r_obs = spearmanr(x, delta).correlation; rhos.append(r_obs)
        se = 1.06 / math.sqrt(n - 3); zr = math.atanh(r_obs)
        lo, hi = math.tanh(zr - 1.96 * se), math.tanh(zr + 1.96 * se); widths.append(hi - lo)
        if lo > 0: hits += 1
    return hits / reps, st.median(widths), st.median(rhos)
print("E2 calibration (persistence walks, loops excluded, log2 final lifespan): within-parent SD 0.34, between-parent SD 0.29.")
print(f"{'stat':>6} {'rho_true':>8} {'sigma_f/rep':>11} {'R':>3} {'power':>6} {'CI width':>9} {'median rho_obs':>15}")
for stat in ('median', 'mean'):
    for ratio in (0.25, 0.5, 1.0):
        for R in (8, 16):
            for rho in (0.0, 0.3, 0.4):
                pw, w, mr = sim(rho, R, ratio, stat=stat)
                print(f"{stat:>6} {rho:8.1f} {ratio:11.2f} {R:3d} {pw:6.2f} {w:9.2f} {mr:15.2f}")
