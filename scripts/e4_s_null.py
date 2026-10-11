"""E4 design: behaviour of the secondary founder-identity statistic S on synthetic NULL data (no founder effect) and
under a small effect, with its within-pair permutation null. S = (mean over pairs |b_N - b_P|) / (mean over pairs of the
pooled within-founder SD of B_G). Also the case of pairs whose replicates agree exactly (zero within-founder SD).
No E4 data exist; nothing here is a result."""
import numpy as np, math
rng = np.random.default_rng(7); PAIRS, R = 88, 16
def S(B):  # B: (PAIRS, 2, R)
    bP, bN = B[:, 0].mean(1), B[:, 1].mean(1)
    sd = np.sqrt((B[:, 0].var(1, ddof=1) + B[:, 1].var(1, ddof=1)) / 2)
    den = sd.mean(); return (np.abs(bN - bP).mean() / den) if den > 0 else float('nan')
def perm_p(B, n=2000):
    obs = S(B); cnt = 0
    for _ in range(n):
        Bp = B.copy()
        for i in range(PAIRS):
            pool = Bp[i].reshape(-1); rng.shuffle(pool); Bp[i] = pool.reshape(2, R)
        if S(Bp) >= obs: cnt += 1
    return obs, (cnt + 1) / (n + 1)
def gen(sigma_f, sigma_rep=0.34, frac_exact=0.0):
    B = np.zeros((PAIRS, 2, R))
    for i in range(PAIRS):
        mu = rng.normal(4.5, 0.3); d = rng.normal(0, sigma_f)
        B[i, 0] = mu + rng.normal(0, sigma_rep, R); B[i, 1] = mu + d + rng.normal(0, sigma_rep, R)
        if rng.random() < frac_exact: B[i] = np.round(B[i], 0)   # replicates collapse onto few values, many exact ties
    return B
print("null (sigma_f = 0): S and permutation p over 20 synthetic experiments")
ps = []
for k in range(20):
    obs, p = perm_p(gen(0.0), n=500); ps.append(p)
print("  S median %.3f · fraction of p < 0.05: %.2f (nominal 0.05) · p values: %s" % (np.median([perm_p(gen(0.0), 200)[0] for _ in range(20)]), np.mean([p < 0.05 for p in ps]), ' '.join('%.2f' % p for p in ps)))
for sf in (0.085, 0.17, 0.34):
    res = [perm_p(gen(sf), n=500) for _ in range(20)]
    print("  effect sigma_f/sigma_rep = %.2f: S median %.3f · power at p < 0.05: %.2f" % (sf / 0.34, np.median([r[0] for r in res]), np.mean([r[1] < 0.05 for r in res])))
res = [perm_p(gen(0.0, frac_exact=0.5), n=300) for _ in range(10)]
print("null with half the pairs collapsed to exact ties: S finite in all runs: %s · fraction p < 0.05: %.2f" % (all(math.isfinite(r[0]) for r in res), np.mean([r[1] < 0.05 for r in res])))
