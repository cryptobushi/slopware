#!/usr/bin/env python3
"""Rolling-map pilot analysis (PROTOCOL.md §Analysis). Descriptive; exploratory; written before the results were read.
usage: python3 analysis.py <results dir with runs/> <out dir>
Outputs: summary.json, tables.md, and plots A–E as PNG."""
import json, glob, os, sys, math, statistics as st, collections
import numpy as np
from scipy.stats import spearmanr
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
RES, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
ARMS = ['baseline', 'static', 'rolling8', 'rolling16', 'rolling32', 'rolling64']
runs = {}   # (pair,f,rep) -> arm -> dict(header, gens, maps, final)
for fn in sorted(glob.glob(f'{RES}/runs/*.jsonl')):
    L = [json.loads(l) for l in open(fn) if l.strip()]
    if not L or not L[-1].get('final'): continue
    h = L[0]; key = (h['pair'], h['f'], h['replicate']); arm = h['arm']
    runs.setdefault(key, {})[arm] = {'h': h, 'gens': [l for l in L if 'g' in l and 'B' in l], 'maps': [l for l in L if l.get('map')], 'final': L[-1]}
keys = sorted(k for k, v in runs.items() if all(a in v for a in ARMS))
BUDGET = next(iter(runs.values()))['baseline']['h']['budget']; K = next(iter(runs.values()))['baseline']['h']['K']
print(f'complete runs (all {len(ARMS)} arms): {len(keys)} of {len(runs)} founder×replicate · budget {BUDGET} · K {K}')
founder_label = lambda k: f"{k[0]}{'P' if k[1] == 0 else 'N'}"
founders = sorted({(k[0], k[1]) for k in keys}, key=lambda x: (x[0], x[1]))
S = {'runs': len(keys), 'budget': BUDGET, 'K': K, 'arms': ARMS}

# ---------------------------------------------------------------- E. compute per arm (first: the fairness check)
comp = {a: collections.Counter() for a in ARMS}; secs = {a: 0.0 for a in ARMS}; gens_run = {a: [] for a in ARMS}
for k in keys:
    for a in ARMS:
        c = runs[k][a]['final']['counts']; comp[a].update({x: c[x] for x in ('logical', 'physical', 'hits', 'map', 'search', 'hf', 'retries')}); secs[a] += runs[k][a]['final']['seconds']; gens_run[a].append(runs[k][a]['final']['generations'])
S['compute'] = {a: {**comp[a], 'seconds': round(secs[a]), 'generations_median': st.median(gens_run[a]), 'logical_per_run_mean': comp[a]['logical'] / len(keys)} for a in ARMS}
lg = [comp[a]['logical'] for a in ARMS]; S['compute']['logical_imbalance_max_minus_min_per_run'] = (max(lg) - min(lg)) / len(keys)
S['compute']['physical_imbalance_vs_baseline_per_run'] = {a: (comp[a]['physical'] - comp['baseline']['physical']) / len(keys) for a in ARMS}

# ---------------------------------------------------------------- A. final best fitness at equal budget
B0 = {k: math.log2(runs[k]['baseline']['h']['founderLife']) for k in keys}
finalB = {a: {k: runs[k][a]['gens'][-1]['B'] for k in keys} for a in ARMS}
rise = {a: {k: finalB[a][k] - B0[k] for k in keys} for a in ARMS}
S['final'] = {a: {'median_rise': st.median(rise[a].values()), 'mean_rise': st.mean(rise[a].values()), 'median_B': st.median(finalB[a].values())} for a in ARMS}
paired = {a: [finalB[a][k] - finalB['baseline'][k] for k in keys] for a in ARMS if a != 'baseline'}
S['paired_final_vs_baseline'] = {a: {'median': st.median(v), 'mean': st.mean(v), 'wins': sum(x > 0 for x in v), 'losses': sum(x < 0 for x in v), 'ties': sum(x == 0 for x in v), 'q25': float(np.percentile(v, 25)), 'q75': float(np.percentile(v, 75))} for a, v in paired.items()}
# seeded pair bootstrap of the median paired difference (descriptive uncertainty, not a test)
rng = np.random.default_rng(20261014)
for a, v in paired.items():
    v = np.array(v); bs = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)]
    S['paired_final_vs_baseline'][a]['median_boot95'] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
fig, ax = plt.subplots(figsize=(9, 4.5)); data = [[rise[a][k] for k in keys] for a in ARMS]
ax.boxplot(data, tick_labels=ARMS, showfliers=False);
for i, d in enumerate(data): ax.scatter(np.full(len(d), i + 1) + rng.uniform(-0.15, 0.15, len(d)), d, s=6, alpha=0.4, color='k')
ax.set_ylabel('final rise, doublings above founder (equal budget)'); ax.set_title('A. final fitness per arm'); fig.tight_layout(); fig.savefig(f'{OUT}/A-final.png', dpi=130); plt.close(fig)

# ---------------------------------------------------------------- B. paired advantage trajectories: by budget spent and by generation
grid = np.arange(0, BUDGET + 1, 128)
def B_by_spent(run):
    spent = [BUDGET - g['budgetLeft'] for g in run['gens']]; B = [g['B'] for g in run['gens']]; b0 = math.log2(run['h']['founderLife'])
    out = np.full(len(grid), b0); j = 0
    for i, x in enumerate(grid):
        while j < len(spent) and spent[j] <= x: j += 1
        out[i] = B[j - 1] if j else b0
    return out
adv_spent = {a: np.array([B_by_spent(runs[k][a]) - B_by_spent(runs[k]['baseline']) for k in keys]) for a in ARMS if a != 'baseline'}
GMAX = 128
def B_by_gen(run, n=GMAX): B = [g['B'] for g in run['gens']][:n]; return np.array(B + [B[-1]] * (n - len(B)))
adv_gen = {a: np.array([B_by_gen(runs[k][a]) - B_by_gen(runs[k]['baseline']) for k in keys]) for a in ARMS if a != 'baseline'}
S['advantage_by_spent_median_at'] = {a: {str(int(grid[i])): float(np.median(adv_spent[a][:, i])) for i in range(0, len(grid), len(grid) // 8)} for a in adv_spent}
S['advantage_by_generation_median_at'] = {a: {str(g): float(np.median(adv_gen[a][:, g - 1])) for g in (8, 16, 32, 64, 128)} for a in adv_gen}
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for a in adv_spent:
    m = np.median(adv_spent[a], axis=0); lo, hi = np.percentile(adv_spent[a], 25, axis=0), np.percentile(adv_spent[a], 75, axis=0)
    axes[0].plot(grid, m, label=a); axes[0].fill_between(grid, lo, hi, alpha=0.08)
    mg = np.median(adv_gen[a], axis=0); axes[1].plot(np.arange(1, GMAX + 1), mg, label=a)
axes[0].axhline(0, color='k', lw=0.8); axes[0].set_xlabel('logical evaluations spent'); axes[0].set_ylabel('median B(arm) − B(baseline), doublings'); axes[0].set_title('B1. advantage at equal compute (median, IQR band)'); axes[0].legend(fontsize=8)
axes[1].axhline(0, color='k', lw=0.8); axes[1].set_xlabel('generation'); axes[1].set_title('B2. advantage at equal generation (mapping arms have spent more)'); axes[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(f'{OUT}/B-advantage.png', dpi=130); plt.close(fig)

# ---------------------------------------------------------------- C. fresh-map prediction
H = [4, 8, 16, 32]
events = []   # one per mapping event in the mapping arms
for k in keys:
    for a in ARMS[1:]:
        run = runs[k][a]; Bg = {g['g']: g['B'] for g in run['gens']}; b0 = math.log2(run['h']['founderLife'])
        for mi, m in enumerate(run['maps']):
            for e in m['events']:
                g = m['g']; base = Bg.get(g - 1, b0)
                ev = {'arm': a, 'key': k, 'g': g, 'refresh': mi, 'acc': e['acc'], 'up': e['up'], 'fit': e['fit'], 'distFounder': e['distFounder'], 'distPrev': e['distPrev']}
                for h in H: ev[f'rise{h}'] = (Bg[g - 1 + h] - base) if (g - 1 + h) in Bg else None
                events.append(ev)
S['events'] = {'n': len(events), 'acc_positive_fraction': sum(e['acc'] > 0 for e in events) / max(1, len(events)), 'acc_mean': st.mean(e['acc'] for e in events) if events else None, 'up_mean': st.mean(e['up'] for e in events) if events else None}
def sp(xs, ys):
    xs, ys = np.array(xs, float), np.array(ys, float)
    if len(xs) < 5 or np.ptp(xs) == 0 or np.ptp(ys) == 0: return None
    return float(spearmanr(xs, ys).correlation)
pred = {}
for label, sel in [('all mapping arms, all refreshes', lambda e: True), ('first map (generation 1)', lambda e: e['refresh'] == 0), ('later refreshes', lambda e: e['refresh'] > 0)] + [(a, (lambda a: lambda e: e['arm'] == a)(a)) for a in ARMS[1:]]:
    row = {}
    for h in H:
        pts = [(e['acc'], e[f'rise{h}']) for e in events if sel(e) and e[f'rise{h}'] is not None]
        row[f'+{h}'] = {'n': len(pts), 'rho': sp([p[0] for p in pts], [p[1] for p in pts]), 'rise_if_acc_pos': (st.mean(p[1] for p in pts if p[0] > 0) if any(p[0] > 0 for p in pts) else None), 'rise_if_acc_zero': (st.mean(p[1] for p in pts if p[0] == 0) if any(p[0] == 0 for p in pts) else None)}
    pred[label] = row
# by distance from the previous map (later refreshes only), and by refresh index
for lo_, hi_ in [(0, 0), (1, 2), (3, 6), (7, 64)]:
    pts = {h: [(e['acc'], e[f'rise{h}']) for e in events if e['refresh'] > 0 and e['distPrev'] is not None and lo_ <= e['distPrev'] <= hi_ and e[f'rise{h}'] is not None] for h in H}
    pred[f'later refreshes, distance from previous map {lo_}–{hi_}'] = {f'+{h}': {'n': len(pts[h]), 'rho': sp([p[0] for p in pts[h]], [p[1] for p in pts[h]])} for h in H}
S['fresh_map_prediction'] = pred
# C0: the clean E4-like check at pilot scale: founder accessibility (generation-1 map, identical across mapping arms) against the BASELINE arm's rise over +h, +64, +128
c0 = {}; founder_acc = {}
for e in events:
    if e['refresh'] == 0 and e['arm'] == 'static': founder_acc[e['key']] = e['acc']
for h in H + [64, 128]:
    pts = [(founder_acc[k], runs[k]['baseline']['gens'][h - 1]['B'] - B0[k]) for k in keys if k in founder_acc and len(runs[k]['baseline']['gens']) >= h]
    c0[f'+{h}'] = {'n': len(pts), 'rho': sp([p[0] for p in pts], [p[1] for p in pts])}
S['founder_map_predicts_baseline'] = c0
fig, axes = plt.subplots(1, 4, figsize=(14, 3.6), sharey=True)
for ax, h in zip(axes, H):
    for lab, mk in (('first map', 'o'), ('later refreshes', 'x')):
        pts = [(e['acc'], e[f'rise{h}']) for e in events if e[f'rise{h}'] is not None and ((e['refresh'] == 0) == (lab == 'first map'))]
        ax.scatter([p[0] + rng.uniform(-0.0004, 0.0004) for p in pts], [p[1] for p in pts], s=7, alpha=0.35, marker=mk, label=lab)
    ax.set_title(f'C. fresh accessibility vs rise over +{h}'); ax.set_xlabel('accessibility (K mutants)');
axes[0].set_ylabel('rise, doublings'); axes[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(f'{OUT}/C-prediction.png', dpi=130); plt.close(fig)

# ---------------------------------------------------------------- D. founder-level
fl = {}
for fd in founders:
    ks = [k for k in keys if (k[0], k[1]) == fd]
    fl[f"{fd[0]}{'P' if fd[1] == 0 else 'N'}"] = {'founderLife': runs[ks[0]]['baseline']['h']['founderLife'], 'replicates': len(ks), **{a: {'median_rise': st.median(rise[a][k] for k in ks), 'median_paired_vs_baseline': (st.median(finalB[a][k] - finalB['baseline'][k] for k in ks) if a != 'baseline' else 0.0)} for a in ARMS}}
S['founders'] = fl
# how much of each arm's mean paired advantage comes from its top two founders (concentration check)
conc = {}
for a in ARMS[1:]:
    per_f = {f: v[a]['median_paired_vs_baseline'] for f, v in fl.items()}; tot = sum(paired[a]); top = sorted(per_f.items(), key=lambda kv: -abs(kv[1]))[:2]
    conc[a] = {'top2_founders': top, 'mean_paired_all': st.mean(paired[a]), 'mean_paired_without_top2': st.mean(finalB[a][k] - finalB['baseline'][k] for k in keys if f"{k[0]}{'P' if k[1] == 0 else 'N'}" not in dict(top))}
S['concentration'] = conc
fig, ax = plt.subplots(figsize=(10, 7)); names = list(fl.keys()); M = np.array([[fl[f][a]['median_paired_vs_baseline'] for a in ARMS[1:]] for f in names])
im = ax.imshow(M, cmap='RdBu', vmin=-max(0.5, abs(M).max()), vmax=max(0.5, abs(M).max()), aspect='auto'); ax.set_xticks(range(len(ARMS) - 1)); ax.set_xticklabels(ARMS[1:]); ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=7)
for i in range(len(names)):
    for j in range(len(ARMS) - 1): ax.text(j, i, f'{M[i, j]:+.2f}', ha='center', va='center', fontsize=6)
fig.colorbar(im, label='median paired final advantage vs baseline, doublings'); ax.set_title('D. every founder: median over replicates of B(arm) − B(baseline)'); fig.tight_layout(); fig.savefig(f'{OUT}/D-founders.png', dpi=130); plt.close(fig)

# ---------------------------------------------------------------- failure-mode checks that are numbers
# accessibility preference costing immediate fitness: per-generation (equal search spent) advantage at g = 8..32 in rolling arms
S['per_generation_cost_check'] = {a: {str(g): float(np.median(adv_gen[a][:, g - 1])) for g in (4, 8, 16, 32, 64, 128)} for a in adv_gen}
# how often a known positive accessibility actually ordered the chosen (knownAcc > 0 among chosen) in mapping arms
S['known_acc_among_chosen_mean'] = {a: st.mean(g['knownAcc'] for k in keys for g in runs[k][a]['gens']) for a in ARMS[1:]}
# compute: wall clock and cost
tot_secs = sum(secs.values()); S['wall'] = {'sum_of_run_seconds': round(tot_secs), 'note': 'runs executed 32 at a time; wall-clock in environment/log timestamps'}

# ---------------------------------------------------------------- F. the prediction horizon, pilot scale
# F1 (E4-style, clean): founder accessibility from the generation-1 map (identical in every mapping arm) against the BASELINE arm's
# rise at every generation g, Spearman over founder×replicate runs, with a seeded resample band of the runs (descriptive).
# F2: fresh maps in the rolling arms: accessibility measured at a refresh against the rise over the following h generations, h = 1..32,
# first maps (generation 1) and later refreshes separately. Both are confounded by use in the rolling arms; F1 is not.
hz_keys = [k for k in keys if k in founder_acc]
GB = max(len(runs[k]['baseline']['gens']) for k in hz_keys)
acc_f = np.array([founder_acc[k] for k in hz_keys])
riseM = np.array([[(runs[k]['baseline']['gens'][g]['B'] if g < len(runs[k]['baseline']['gens']) else runs[k]['baseline']['gens'][-1]['B']) - B0[k] for g in range(GB)] for k in hz_keys])
f1 = []; idxs = [rng.integers(0, len(hz_keys), len(hz_keys)) for _ in range(1000)]
for g in range(GB):
    r_ = sp(acc_f, riseM[:, g]); bs = [v for v in (sp(acc_f[ix], riseM[ix, g]) for ix in idxs) if v is not None]
    f1.append({'g': g + 1, 'rho': r_, 'band': [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if bs else [None, None]})
S['horizon_founder_map_vs_baseline'] = {str(x['g']): x for x in f1 if x['g'] in (1, 2, 4, 8, 16, 24, 32, 48, 64, 96, 128, 192, 255)}
def fresh_h(sel, hmax=32):
    out = []
    for h in range(1, hmax + 1):
        pts = []
        for k in keys:
            for a in ARMS[1:]:
                run = runs[k][a]; Bg = {x['g']: x['B'] for x in run['gens']}; b0 = math.log2(run['h']['founderLife'])
                for mi, m in enumerate(run['maps']):
                    if not sel(a, mi): continue
                    g = m['g']
                    if (g - 1 + h) in Bg: pts.append((m['events'][0]['acc'], Bg[g - 1 + h] - Bg.get(g - 1, b0)))
        out.append({'h': h, 'n': len(pts), 'rho': sp([p[0] for p in pts], [p[1] for p in pts])})
    return out
f2_first = fresh_h(lambda a, mi: mi == 0, 64); f2_later = fresh_h(lambda a, mi: mi > 0, 32)
f2_by_arm = {a: fresh_h((lambda a_: lambda a2, mi: a2 == a_ and mi > 0)(a), 32) for a in ARMS[2:]}
S['horizon_fresh_maps'] = {'first_map': {str(x['h']): x for x in f2_first if x['h'] in (1, 2, 4, 8, 16, 32, 64)}, 'later_refreshes': {str(x['h']): x for x in f2_later if x['h'] in (1, 2, 4, 8, 16, 32)}, 'later_by_arm': {a: {str(x['h']): x for x in v if x['h'] in (4, 8, 16, 32)} for a, v in f2_by_arm.items()}}
fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
gs = [x['g'] for x in f1 if x['rho'] is not None]; rs = [x['rho'] for x in f1 if x['rho'] is not None]
lo = [x['band'][0] for x in f1 if x['rho'] is not None]; hi = [x['band'][1] for x in f1 if x['rho'] is not None]
axes[0].fill_between(gs, lo, hi, color='0.85'); axes[0].plot(gs, rs, color='k', lw=1.6); axes[0].axhline(0, color='k', lw=0.8); axes[0].axhline(0.3, color='0.5', lw=0.8, ls='--')
axes[0].set_xlabel('generation (baseline arm)'); axes[0].set_ylabel('Spearman ρ'); axes[0].set_title(f'F1. founder map (K={K}) vs baseline rise · n={len(hz_keys)} runs'); axes[0].set_ylim(-0.6, 0.9)
for lab, series, st_ in (('first map (g1), mapping arms', f2_first, '-'), ('later refreshes, rolling arms', f2_later, '--')):
    hs = [x['h'] for x in series if x['rho'] is not None]; axes[1].plot(hs, [x['rho'] for x in series if x['rho'] is not None], st_, label=lab)
for a, v in f2_by_arm.items():
    hs = [x['h'] for x in v if x['rho'] is not None]; axes[1].plot(hs, [x['rho'] for x in v if x['rho'] is not None], ':', lw=1, label=f'later refreshes, {a}')
axes[1].axhline(0, color='k', lw=0.8); axes[1].set_xlabel('generations after the map (h)'); axes[1].set_title('F2. fresh-map horizon: accessibility at the map vs rise over the next h'); axes[1].legend(fontsize=7); axes[1].set_ylim(-0.6, 0.9)
fig.tight_layout(); fig.savefig(f'{OUT}/F-horizon.png', dpi=130); plt.close(fig)

json.dump(S, open(f'{OUT}/summary.json', 'w'), indent=1, default=str)
# ---------------------------------------------------------------- tables
T = [f'# Rolling-map pilot — tables (generated)', '', f'Complete founder×replicate runs: {len(keys)} · budget per arm-run {BUDGET} logical evaluations · K {K}', '', '## A. final rise above founder at equal budget (doublings)', '', '| arm | median rise | mean rise | median paired vs baseline | wins/losses/ties | paired median 95% pair-bootstrap |', '|---|---|---|---|---|---|']
for a in ARMS:
    p = S['paired_final_vs_baseline'].get(a); T.append(f"| {a} | {S['final'][a]['median_rise']:.3f} | {S['final'][a]['mean_rise']:.3f} | {p['median']:+.3f} | {p['wins']}/{p['losses']}/{p['ties']} | [{p['median_boot95'][0]:+.3f}, {p['median_boot95'][1]:+.3f}] |" if p else f"| {a} | {S['final'][a]['median_rise']:.3f} | {S['final'][a]['mean_rise']:.3f} | — | — | — |")
T += ['', '## B. median advantage vs baseline', '', '| arm | ' + ' | '.join(f'at {x} evals' for x in S['advantage_by_spent_median_at']['static']) + ' | ' + ' | '.join(f'g{g}' for g in (8, 16, 32, 64, 128)) + ' |', '|---|' + '---|' * (len(S['advantage_by_spent_median_at']['static']) + 5)]
for a in adv_spent: T.append(f'| {a} | ' + ' | '.join(f'{v:+.3f}' for v in S['advantage_by_spent_median_at'][a].values()) + ' | ' + ' | '.join(f"{S['advantage_by_generation_median_at'][a][str(g)]:+.3f}" for g in (8, 16, 32, 64, 128)) + ' |')
T += ['', '## C. fresh-map prediction (Spearman, descriptive)', '', '| events | ' + ' | '.join(f'+{h}: n, ρ' for h in H) + ' |', '|---|' + '---|' * len(H)]
for lab, row in pred.items(): T.append(f'| {lab} | ' + ' | '.join(f"{row[f'+{h}']['n']}, {row[f'+{h}']['rho']:.2f}" if row[f'+{h}']['rho'] is not None else f"{row[f'+{h}']['n']}, n/a" for h in H) + ' |')
T += ['', 'Founder (generation-1) accessibility against the baseline arm\'s rise (clean, unconfounded by use): ' + ' · '.join(f"+{h}: ρ {v['rho']:.2f} (n {v['n']})" if v['rho'] is not None else f"+{h}: n/a" for h, v in ((k[1:], v) for k, v in c0.items())), '', f"Mapping events: {S['events']['n']}; accessibility > 0 in {100*S['events']['acc_positive_fraction']:.1f}%; mean upward hits per map {S['events']['up_mean']:.2f} of K = {K}.", '', '## D. founders (median paired final advantage vs baseline, doublings)', '', '| founder | life | ' + ' | '.join(ARMS[1:]) + ' |', '|---|---|' + '---|' * (len(ARMS) - 1)]
for f, v in fl.items(): T.append(f"| {f} | {v['founderLife']} | " + ' | '.join(f"{v[a]['median_paired_vs_baseline']:+.2f}" for a in ARMS[1:]) + ' |')
T += ['', '## E. compute per arm (sums over all runs)', '', '| arm | logical | physical | cache hits | mapping evals | search evals | hf | retries | median generations | run-seconds |', '|---|---|---|---|---|---|---|---|---|---|']
for a in ARMS: c = S['compute'][a]; T.append(f"| {a} | {c['logical']:,} | {c['physical']:,} | {c['hits']:,} | {c['map']:,} | {c['search']:,} | {c['hf']} | {c['retries']} | {c['generations_median']:.0f} | {c['seconds']:,} |")
T += ['', f"Logical imbalance between arms, per run: {S['compute']['logical_imbalance_max_minus_min_per_run']:.1f} evaluations (should be below 64 + 1). Physical executions per run relative to baseline: " + ', '.join(f"{a} {v:+.0f}" for a, v in S['compute']['physical_imbalance_vs_baseline_per_run'].items() if a != 'baseline') + '.']
open(f'{OUT}/tables.md', 'w').write('\n'.join(T) + '\n'); print('\n'.join(T))
