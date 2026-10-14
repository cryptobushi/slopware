#!/usr/bin/env python3
"""Post-hoc interrogation of the rolling-map pilot's fresh-map result. Conceived AFTER reading the pilot results: exploratory only.
Reads ONLY the preserved records (results/runs/*.jsonl) and the published summary; writes nothing outside results/interrogation/.
usage: python3 interrogation.py <results dir> <out dir>"""
import json, glob, os, sys, math, statistics as st, collections, itertools
import numpy as np
from scipy.stats import spearmanr
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
RES, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
ARMS = ['baseline', 'static', 'rolling8', 'rolling16', 'rolling32', 'rolling64']; H = [4, 8, 16, 32]
R = {}

# ---------------------------------------------------------------- 1. reproduce the published event set and correlations, by the published rules
runs = {}
for fn in sorted(glob.glob(f'{RES}/runs/*.jsonl')):
    L = [json.loads(l) for l in open(fn) if l.strip()]
    if not L or not L[-1].get('final'): continue
    h = L[0]; runs.setdefault((h['pair'], h['f'], h['replicate']), {})[h['arm']] = {'h': h, 'gens': [l for l in L if 'g' in l and 'B' in l], 'maps': [l for l in L if l.get('map')]}
keys = sorted(k for k, v in runs.items() if all(a in v for a in ARMS))
events = []
for k in keys:
    for a in ARMS[1:]:
        run = runs[k][a]; Bg = {g['g']: g['B'] for g in run['gens']}; b0 = math.log2(run['h']['founderLife'])
        for mi, m in enumerate(run['maps']):
            for e in m['events']:
                g = m['g']; base = Bg.get(g - 1, b0)
                ev = {'founder': f"{k[0]}{'P' if k[1] == 0 else 'N'}", 'key': k, 'arm': a, 'g': g, 'refresh': mi, 'acc': e['acc'], 'up': e['up'], 'any': 1 if e['up'] > 0 else 0, 'fit': e['fit'], 'log2fit': math.log2(e['fit']), 'distPrev': e['distPrev'], 'K': e['K']}
                for h in range(1, 33): ev[f'rise{h}'] = (Bg[g - 1 + h] - base) if (g - 1 + h) in Bg else None
                events.append(ev)
later = [e for e in events if e['refresh'] > 0]
def sp(xs, ys):
    xs, ys = np.array(xs, float), np.array(ys, float)
    if len(xs) < 5 or np.ptp(xs) == 0 or np.ptp(ys) == 0: return None
    return float(spearmanr(xs, ys).correlation)
def with_h(evs, h): return [e for e in evs if e[f'rise{h}'] is not None]
pub = json.load(open(f'{RES}/analysis/summary.json'))['fresh_map_prediction']['later refreshes']
repro = {}
for h in H:
    evs = with_h(later, h); r_ = sp([e['acc'] for e in evs], [e[f'rise{h}'] for e in evs])
    repro[f'+{h}'] = {'n': len(evs), 'rho': r_, 'published_n': pub[f'+{h}']['n'], 'published_rho': pub[f'+{h}']['rho'], 'match': len(evs) == pub[f'+{h}']['n'] and abs(r_ - pub[f'+{h}']['rho']) < 1e-9}
R['reproduction'] = {'complete_runs': len(keys), 'later_refresh_events': len(later), 'published_later_refresh_events': 6494, 'horizons': repro, 'all_match': len(later) == 6494 and all(v['match'] for v in repro.values())}
print(f"reproduction: {len(later)} later-refresh events (published 6,494) · " + ' · '.join(f"+{h}: n {v['n']} ρ {v['rho']:.4f} (published {v['published_rho']:.4f}) {'ok' if v['match'] else 'MISMATCH'}" for h, v in ((k[1:], v) for k, v in repro.items())))
if not R['reproduction']['all_match']: print('STOP: the published result does not reproduce from the preserved record'); json.dump(R, open(f'{OUT}/summary.json', 'w'), indent=1); sys.exit(1)
R['best_observed_gain'] = 'unavailable: the record keeps per-map counts (up, loops, unins, acc), not per-mutant fitness; not reconstructed, no mutations re-run (Model 4 omitted)'
R['dependency'] = 'events nest in runs (founder×replicate×arm), runs in founder×replicate (the four rolling arms share one proposal stream until they diverge), founder×replicate in 24 founders (12 pairs: P and N of a pair share a measured signature). The unit of resampling below is the founder (24 clusters); all events of a founder move together.'

# ---------------------------------------------------------------- clustered bootstrap (founder level)
rng = np.random.default_rng(20261014)
founders = sorted({e['founder'] for e in later}); by_f = {f: [e for e in later if e['founder'] == f] for f in founders}
def fboot(stat, evs, nb=1000):
    """stat(list of events) -> float or None; percentile 95% band over founder resamples (24 clusters)."""
    fs = sorted({e['founder'] for e in evs}); byf = {f: [e for e in evs if e['founder'] == f] for f in fs}
    v0 = stat(evs); vals = []
    for _ in range(nb):
        samp = [e for i in rng.integers(0, len(fs), len(fs)) for e in byf[fs[i]]]; v = stat(samp)
        if v is not None and not (isinstance(v, float) and math.isnan(v)): vals.append(v)
    return {'value': v0, 'ci95': [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else [None, None]}
rho_stat = lambda x, h: (lambda evs: sp([e[x] for e in evs], [e[f'rise{h}'] for e in evs]))

# ---------------------------------------------------------------- Q1. zero vs nonzero
def describe(v):
    v = np.array(v, float)
    return {'n': int(len(v)), 'median': float(np.median(v)), 'mean': float(v.mean()), 'q10': float(np.percentile(v, 10)), 'q25': float(np.percentile(v, 25)), 'q75': float(np.percentile(v, 75)), 'q90': float(np.percentile(v, 90)), 'frac_zero': float((v == 0).mean()), 'frac_pos': float((v > 0).mean())}
q1 = {}
for h in H:
    evs = with_h(later, h); z = [e[f'rise{h}'] for e in evs if e['up'] == 0]; p = [e[f'rise{h}'] for e in evs if e['up'] >= 1]
    q1[f'+{h}'] = {'zero_hits': describe(z), 'positive_hits': describe(p),
                   'rho_any': fboot(rho_stat('any', h), evs, 400), 'rho_acc': fboot(rho_stat('acc', h), evs, 400), 'rho_up': sp([e['up'] for e in evs], [e[f'rise{h}'] for e in evs]),
                   'mean_diff_pos_minus_zero': fboot(lambda ev: (np.mean([e[f'rise{h}'] for e in ev if e['up'] >= 1]) - np.mean([e[f'rise{h}'] for e in ev if e['up'] == 0])) if any(e['up'] == 0 for e in ev) and any(e['up'] >= 1 for e in ev) else None, evs, 400)}
    q1[f'+{h}']['share_of_rho_retained_by_one_bit'] = q1[f'+{h}']['rho_any']['value'] / q1[f'+{h}']['rho_acc']['value'] if q1[f'+{h}']['rho_acc']['value'] else None
R['Q1_zero_vs_positive'] = q1
fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
for ax, h in zip(axes, H):
    evs = with_h(later, h); z = [e[f'rise{h}'] for e in evs if e['up'] == 0]; p = [e[f'rise{h}'] for e in evs if e['up'] >= 1]
    ax.hist([z, p], bins=np.arange(0, 6.01, 0.25), label=[f'0 hits (n {len(z)})', f'≥1 hit (n {len(p)})'], density=True, alpha=0.8); ax.set_title(f'rise over +{h}'); ax.set_xlabel('doublings'); ax.legend(fontsize=7)
axes[0].set_ylabel('density'); fig.suptitle('Q1. future rise: maps with no upward hit vs at least one'); fig.tight_layout(); fig.savefig(f'{OUT}/Q1-zero-vs-positive.png', dpi=130); plt.close(fig)

# ---------------------------------------------------------------- Q2. within positive maps, does hit count matter?  bins 1, 2, 3, 4+ (merge upward if a bin has < 100 events: rule fixed here)
pos = [e for e in later if e['up'] >= 1]
q2 = {'n_positive': len(pos), 'hit_counts': dict(sorted(collections.Counter(min(e['up'], 8) for e in pos).items()))}
for h in H:
    evs = with_h(pos, h)
    q2[f'+{h}'] = {'rho_up': fboot(rho_stat('up', h), evs, 400), 'rho_acc': sp([e['acc'] for e in evs], [e[f'rise{h}'] for e in evs]), 'n': len(evs)}
    q2[f'+{h}']['rank_identity_up_acc'] = abs(q2[f'+{h}']['rho_up']['value'] - q2[f'+{h}']['rho_acc']) < 1e-12
    bins = {'1': [e for e in evs if e['up'] == 1], '2': [e for e in evs if e['up'] == 2], '3': [e for e in evs if e['up'] == 3], '4+': [e for e in evs if e['up'] >= 4]}
    if len(bins['4+']) < 100: bins['3+'] = bins.pop('3') + bins.pop('4+')
    q2[f'+{h}']['bins'] = {b: describe([e[f'rise{h}'] for e in v]) for b, v in bins.items() if v}
R['Q2_within_positive'] = q2
fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
for ax, h in zip(axes, H):
    evs = with_h(pos, h); labs = []; data = []
    for b, sel in (('1', lambda u: u == 1), ('2', lambda u: u == 2), ('3', lambda u: u == 3), ('4+', lambda u: u >= 4)):
        v = [e[f'rise{h}'] for e in evs if sel(e['up'])]
        if v: labs.append(f'{b}\n(n {len(v)})'); data.append(v)
    ax.boxplot(data, tick_labels=labs, showfliers=False); ax.set_title(f'rise over +{h} by hit count'); ax.set_xlabel('upward hits in the map')
axes[0].set_ylabel('doublings'); fig.suptitle('Q2. among maps that found at least one upward mutant'); fig.tight_layout(); fig.savefig(f'{OUT}/Q2-hit-count.png', dpi=130); plt.close(fig)

# ---------------------------------------------------------------- Q3. current-fitness strata (fixed power-of-two bins on the probe-A count)
FBINS = [(0, 8), (9, 16), (17, 32), (33, 64), (65, 128), (129, 10**9)]
q3 = {}
for lo, hi in FBINS:
    evs = [e for e in later if lo <= e['fit'] <= hi]; lab = f'{lo}–{hi}' if hi < 10**9 else f'≥{lo}'
    if not evs: continue
    row = {'n': len(evs), 'founders': len({e['founder'] for e in evs}), 'zero_hit_fraction': sum(e['up'] == 0 for e in evs) / len(evs), 'mean_up': st.mean(e['up'] for e in evs)}
    for h in H:
        eh = with_h(evs, h); z = [e[f'rise{h}'] for e in eh if e['up'] == 0]; p = [e[f'rise{h}'] for e in eh if e['up'] >= 1]
        row[f'+{h}'] = {'n': len(eh), 'rho_up': sp([e['up'] for e in eh], [e[f'rise{h}'] for e in eh]), 'rho_any': sp([e['any'] for e in eh], [e[f'rise{h}'] for e in eh]), 'rho_up_within_positive': sp([e['up'] for e in eh if e['up'] >= 1], [e[f'rise{h}'] for e in eh if e['up'] >= 1]), 'mean_rise_zero': float(np.mean(z)) if z else None, 'mean_rise_pos': float(np.mean(p)) if p else None, 'P_rise_pos_zero': float(np.mean(np.array(z) > 0)) if z else None, 'P_rise_pos_pos': float(np.mean(np.array(p) > 0)) if p else None}
    q3[lab] = row
R['Q3_fitness_strata'] = q3

# ---------------------------------------------------------------- Q4. nested simple models, founder-held-out (leave-one-founder-out, 24 folds)
def design(evs, cols):
    X = np.column_stack([np.ones(len(evs))] + [np.array([e[c] for e in evs], float) for c in cols]); return X
MODELS = {'M0: log2 fitness + generation': ['log2fit', 'g'], 'M1: + any_uphill': ['log2fit', 'g', 'any'], 'M2: + hit count': ['log2fit', 'g', 'up'], 'M3: + any_uphill + hit count': ['log2fit', 'g', 'any', 'up']}
def logistic_fit(X, y, iters=200):
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w)); W = p * (1 - p) + 1e-9
        g_ = X.T @ (y - p); Hm = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(Hm, g_); w += step
        if np.abs(step).max() < 1e-8: break
    return w
def auc(scores, y):
    order = np.argsort(scores); ranks = np.empty(len(scores)); ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    s = np.array(scores); uniq = np.unique(s)
    for u in uniq:
        idx = np.where(s == u)[0]
        if len(idx) > 1: ranks[idx] = ranks[idx].mean()
    n1 = y.sum(); n0 = len(y) - n1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else None
q4 = {}
for h in H:
    evs = with_h(later, h); y = np.array([e[f'rise{h}'] for e in evs]); yb = (y > 0).astype(float); fo = np.array([e['founder'] for e in evs])
    q4[f'+{h}'] = {}
    for name, cols in MODELS.items():
        X = design(evs, cols); pred = np.zeros(len(evs)); predb = np.zeros(len(evs))
        for f in founders:
            te = fo == f; tr = ~te
            beta, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None); pred[te] = X[te] @ beta
            w = logistic_fit(X[tr], yb[tr]); predb[te] = 1 / (1 + np.exp(-(X[te] @ w)))
        r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        q4[f'+{h}'][name] = {'heldout_R2_OLS_rise': float(r2), 'heldout_spearman_pred_vs_rise': sp(pred, y), 'heldout_AUC_logistic_rise_gt0': auc(predb, yb), 'heldout_RMSE': float(np.sqrt(((y - pred) ** 2).mean()))}
    q4[f'+{h}']['base_rate_rise_gt0'] = float(yb.mean()); q4[f'+{h}']['n'] = len(evs)
R['Q4_models_founder_heldout'] = q4

# ---------------------------------------------------------------- Q5. matched comparison: cells = fitness bin × generation bin (≤32, 33–64, 65–128) with any=1; compare 1 vs 2 vs 3+ hits; a cell qualifies if every hit-bin has ≥ 20 events (rule fixed here)
GBINS = [(1, 32), (33, 64), (65, 128)]
q5 = {}
for h in H:
    cells = []
    for lo, hi in FBINS:
        for glo, ghi in GBINS:
            evs = [e for e in with_h(pos, h) if lo <= e['fit'] <= hi and glo <= e['g'] <= ghi]
            b1 = [e[f'rise{h}'] for e in evs if e['up'] == 1]; b2 = [e[f'rise{h}'] for e in evs if e['up'] == 2]; b3 = [e[f'rise{h}'] for e in evs if e['up'] >= 3]
            if min(len(b1), len(b2), len(b3)) >= 20:
                m = [float(np.mean(b1)), float(np.mean(b2)), float(np.mean(b3))]; md = [float(np.median(b1)), float(np.median(b2)), float(np.median(b3))]
                cells.append({'fitness': f'{lo}–{hi}' if hi < 10**9 else f'≥{lo}', 'generation': f'{glo}–{ghi}', 'n': [len(b1), len(b2), len(b3)], 'mean_rise_1_2_3plus': m, 'median_rise_1_2_3plus': md, 'P_rise_pos_1_2_3plus': [float(np.mean(np.array(b1) > 0)), float(np.mean(np.array(b2) > 0)), float(np.mean(np.array(b3) > 0))], 'monotone_increasing_mean': m[0] < m[1] < m[2], 'three_plus_above_one_mean': m[2] > m[0]})
    q5[f'+{h}'] = {'qualifying_cells': len(cells), 'cells_monotone_increasing_mean': sum(c['monotone_increasing_mean'] for c in cells), 'cells_3plus_above_1_mean': sum(c['three_plus_above_one_mean'] for c in cells), 'cells': cells}
R['Q5_matched'] = q5

# ---------------------------------------------------------------- Q6. horizon curves 1..32 for any, up, acc (later refreshes), with founder bands at the published horizons
hz = {'any': [], 'up': [], 'acc': []}
for h in range(1, 33):
    evs = with_h(later, h)
    for x in hz: hz[x].append(sp([e[x] for e in evs], [e[f'rise{h}'] for e in evs]))
R['Q6_horizon'] = {x: {str(h): hz[x][h - 1] for h in (1, 2, 4, 8, 12, 16, 24, 32)} for x in hz}
R['Q6_horizon_bands'] = {x: {f'+{h}': fboot(rho_stat(x, h), with_h(later, h), 300) for h in (1, 4, 16, 32)} for x in ('any', 'acc')}
fig, ax = plt.subplots(figsize=(8, 4.2))
for x, lab, ls in (('acc', 'accessibility (published)', '-'), ('up', 'upward-hit count', '--'), ('any', 'any_uphill (one bit)', ':')):
    ax.plot(range(1, 33), hz[x], ls, lw=2 if x == 'any' else 1.4, label=lab)
ax.axhline(0, color='k', lw=0.8); ax.set_xlabel('generations after the map (h)'); ax.set_ylabel('Spearman ρ with rise over h'); ax.set_title('Q6. the horizon with one bit instead of the map'); ax.legend(); ax.set_ylim(-0.1, 0.8)
fig.tight_layout(); fig.savefig(f'{OUT}/Q6-horizon.png', dpi=130); plt.close(fig)

# ---------------------------------------------------------------- Q7. plateau / escape probabilities with founder bands
q7 = {}
for h in H:
    evs = with_h(later, h)
    P = lambda sel: (lambda ev: (float(np.mean([e[f'rise{h}'] > 0 for e in ev if sel(e['up'])])) if any(sel(e['up']) for e in ev) else None))
    q7[f'+{h}'] = {'P_rise_pos_given_0_hits': fboot(P(lambda u: u == 0), evs, 400), 'P_rise_pos_given_ge1_hit': fboot(P(lambda u: u >= 1), evs, 400), 'P_rise_pos_given_1_hit': fboot(P(lambda u: u == 1), evs, 400), 'P_rise_pos_given_2_hits': fboot(P(lambda u: u == 2), evs, 400), 'P_rise_pos_given_3plus_hits': fboot(P(lambda u: u >= 3), evs, 400),
                   'n_by_hits': {'0': sum(e['up'] == 0 for e in evs), '1': sum(e['up'] == 1 for e in evs), '2': sum(e['up'] == 2 for e in evs), '3+': sum(e['up'] >= 3 for e in evs)}}
R['Q7_plateau_escape'] = q7
# how often does a zero-hit map at generation g see the SAME best fitness h generations later (true plateau)?
R['Q7_distance_from_previous_map'] = {b: {'n': len([e for e in later if e['distPrev'] is not None and lo <= e['distPrev'] <= hi]), 'zero_hit_fraction': (sum(e['up'] == 0 for e in later if e['distPrev'] is not None and lo <= e['distPrev'] <= hi) / max(1, len([e for e in later if e['distPrev'] is not None and lo <= e['distPrev'] <= hi])))} for b, (lo, hi) in (('0', (0, 0)), ('1–2', (1, 2)), ('3–6', (3, 6)), ('7+', (7, 64)))}
json.dump(R, open(f'{OUT}/summary.json', 'w'), indent=1, default=str)

# ---------------------------------------------------------------- tables
f2 = lambda v: 'n/a' if v is None else f'{v:.2f}'
ci = lambda b: f"{f2(b['value'])} [{f2(b['ci95'][0])}, {f2(b['ci95'][1])}]"
T = ['# Interrogation — tables (generated by interrogation.py)', '', f"Reproduction: {len(later)} later-refresh events from {len(keys)} complete runs; " + ' · '.join(f"+{h}: n {v['n']}, ρ {v['rho']:.4f} = published {v['published_rho']:.4f}" for h, v in ((k[1:], v) for k, v in repro.items())) + f" · all match: {R['reproduction']['all_match']}", '', f"best_observed_gain: {R['best_observed_gain']}", '',
     '## Q1. zero hits vs at least one hit', '', '| horizon | group | n | median | mean | q25 | q75 | q90 | P(rise=0) | P(rise>0) |', '|---|---|---|---|---|---|---|---|---|---|']
for h in H:
    for grp in ('zero_hits', 'positive_hits'): d = q1[f'+{h}'][grp]; T.append(f"| +{h} | {grp.replace('_', ' ')} | {d['n']} | {d['median']:.2f} | {d['mean']:.2f} | {d['q25']:.2f} | {d['q75']:.2f} | {d['q90']:.2f} | {d['frac_zero']:.2f} | {d['frac_pos']:.2f} |")
T += ['', '| horizon | ρ(accessibility, rise) | ρ(any_uphill, rise) | one bit retains | ρ(hit count, rise) | mean rise ≥1 hit − 0 hits |', '|---|---|---|---|---|---|'] + [f"| +{h} | {ci(q1[f'+{h}']['rho_acc'])} | {ci(q1[f'+{h}']['rho_any'])} | {100*q1[f'+{h}']['share_of_rho_retained_by_one_bit']:.0f}% | {f2(q1[f'+{h}']['rho_up'])} | {ci(q1[f'+{h}']['mean_diff_pos_minus_zero'])} |" for h in H]
T += ['', f"## Q2. within the {q2['n_positive']} maps with at least one hit (hit counts: {q2['hit_counts']})", '', '| horizon | n | ρ(hit count, rise) | ρ(accessibility, rise) | identical ranks | ' + ' | '.join('bin: n, median, mean, P(rise>0)' for _ in range(3)) + ' |', '|---|---|---|---|---|---|---|---|']
for h in H:
    row = q2[f'+{h}']; T.append(f"| +{h} | {row['n']} | {ci(row['rho_up'])} | {f2(row['rho_acc'])} | {row['rank_identity_up_acc']} | " + ' | '.join(f"{b}: {d['n']}, {d['median']:.2f}, {d['mean']:.2f}, {d['frac_pos']:.2f}" for b, d in row['bins'].items()) + ' |')
T += ['', '## Q3. current-fitness strata (probe-A count, fixed power-of-two bins)', '', '| fitness | n | founders | zero-hit fraction | mean hits | ' + ' | '.join(f'+{h}: ρ(hits), ρ(any), ρ(hits | ≥1), mean rise 0 / ≥1, P(rise>0) 0 / ≥1' for h in H) + ' |', '|---|---|---|---|---|' + '---|' * len(H)]
for lab, row in q3.items(): T.append(f"| {lab} | {row['n']} | {row['founders']} | {row['zero_hit_fraction']:.2f} | {row['mean_up']:.2f} | " + ' | '.join(f"{f2(row[f'+{h}']['rho_up'])}, {f2(row[f'+{h}']['rho_any'])}, {f2(row[f'+{h}']['rho_up_within_positive'])}, {f2(row[f'+{h}']['mean_rise_zero'])} / {f2(row[f'+{h}']['mean_rise_pos'])}, {f2(row[f'+{h}']['P_rise_pos_zero'])} / {f2(row[f'+{h}']['P_rise_pos_pos'])}" for h in H) + ' |')
T += ['', '## Q4. nested simple models, leave-one-founder-out (24 folds)', '', 'OLS on the rise in doublings (held-out R² and Spearman of prediction with outcome) and logistic regression on rise > 0 (held-out AUC). Predictors enter linearly; no tuning.', '', '| horizon | model | held-out R² | held-out ρ(pred, rise) | held-out AUC (rise>0) | RMSE |', '|---|---|---|---|---|---|']
for h in H:
    for name, m in q4[f'+{h}'].items():
        if name.startswith('M'): T.append(f"| +{h} | {name} | {m['heldout_R2_OLS_rise']:.3f} | {f2(m['heldout_spearman_pred_vs_rise'])} | {f2(m['heldout_AUC_logistic_rise_gt0'])} | {m['heldout_RMSE']:.3f} |")
    T.append(f"| +{h} | base rate P(rise>0) | | | {q4[f'+{h}']['base_rate_rise_gt0']:.2f} | n {q4[f'+{h}']['n']} |")
T += ['', '## Q5. matched cells (fitness bin × generation bin, any_uphill = 1; every hit bin ≥ 20 events)', '', '| horizon | qualifying cells | cells with mean rise increasing 1 < 2 < 3+ | cells with 3+ above 1 | cells (fitness, generation: n per bin → mean rise 1 / 2 / 3+ → P(rise>0) 1 / 2 / 3+) |', '|---|---|---|---|---|']
for h in H:
    row = q5[f'+{h}']; T.append(f"| +{h} | {row['qualifying_cells']} | {row['cells_monotone_increasing_mean']} | {row['cells_3plus_above_1_mean']} | " + '; '.join(f"({c['fitness']}, g{c['generation']}: {c['n']} → {c['mean_rise_1_2_3plus'][0]:.2f} / {c['mean_rise_1_2_3plus'][1]:.2f} / {c['mean_rise_1_2_3plus'][2]:.2f} → {c['P_rise_pos_1_2_3plus'][0]:.2f} / {c['P_rise_pos_1_2_3plus'][1]:.2f} / {c['P_rise_pos_1_2_3plus'][2]:.2f})" for c in row['cells']) + ' |')
T += ['', '## Q6. horizon (Spearman ρ with rise over h, later refreshes)', '', '| predictor | ' + ' | '.join(f'+{h}' for h in (1, 2, 4, 8, 12, 16, 24, 32)) + ' |', '|---|' + '---|' * 8] + [f"| {x} | " + ' | '.join(f2(R['Q6_horizon'][x][str(h)]) for h in (1, 2, 4, 8, 12, 16, 24, 32)) + ' |' for x in ('acc', 'up', 'any')]
T += ['', 'Founder bands: ' + ' · '.join(f"{x} +{h}: {ci(b)}" for x in ('acc', 'any') for h, b in ((k[1:], v) for k, v in R['Q6_horizon_bands'][x].items())), '', '## Q7. plateau / escape: P(rise > 0 | hits), founder bands', '', '| horizon | 0 hits | ≥1 hit | 1 hit | 2 hits | 3+ hits | n (0 / 1 / 2 / 3+) |', '|---|---|---|---|---|---|---|']
for h in H: r = q7[f'+{h}']; T.append(f"| +{h} | {ci(r['P_rise_pos_given_0_hits'])} | {ci(r['P_rise_pos_given_ge1_hit'])} | {ci(r['P_rise_pos_given_1_hit'])} | {ci(r['P_rise_pos_given_2_hits'])} | {ci(r['P_rise_pos_given_3plus_hits'])} | {r['n_by_hits']['0']} / {r['n_by_hits']['1']} / {r['n_by_hits']['2']} / {r['n_by_hits']['3+']} |")
T += ['', 'Zero-hit fraction by distance from the previous mapped genome: ' + ' · '.join(f"{b}: {v['zero_hit_fraction']:.2f} (n {v['n']})" for b, v in R['Q7_distance_from_previous_map'].items())]
open(f'{OUT}/tables.md', 'w').write('\n'.join(T) + '\n'); print('\n'.join(T))
