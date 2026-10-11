"""E4 analysis, pre-specified (E4-after.md §3, §7). Frozen at the signing commit; anything else is exploratory and labelled.

Inputs:  <record>/populations/<q>-<f>-<r>.jsonl (src/e4.ts), E4/predictors.json, E4/founders.json, E4/pair-distances.json
Outputs: <summaries>/results.json, report.txt, trajectories.json (renderer input), calibration-M.json (the 10,000 simulated M values)
Usage:   python3 scripts/e4_analysis.py <record-dir> <summaries-dir> [--generations 256] [--replicates 16] [--boot 10000] [--perm 10000] [--calib 10000]

Seeds (§7.0): numpy default_rng seeded with bytes 0..7 of keccak256 of a domain string, big-endian uint64:
  E4-2026-10-11-bootstrap    the pair-resample index sets, drawn once, reused for every bootstrap quantity
  E4-2026-10-11-permutation  the within-pair relabellings, reused for S and the strata
  E4-2026-10-11-calibration  the inverse-CDF draws of the calibration simulation
"""
import json, glob, os, sys, math, itertools, collections
import numpy as np
from scipy.stats import spearmanr
from Crypto.Hash import keccak

args = {a.lstrip('-'): v for a, v in zip(sys.argv[1:], sys.argv[2:]) if a.startswith('--')}
REC, SUM = sys.argv[1], sys.argv[2]
G = int(args.get('generations', 256)); R = int(args.get('replicates', 16))
NBOOT = int(args.get('boot', 10000)); NPERM = int(args.get('perm', 10000)); NCAL = int(args.get('calib', 10000))
D = 'slopware/experiments/E4'
PRED = json.load(open(f'{D}/predictors.json'))['founders']; FOUND = json.load(open(f'{D}/founders.json'))['pairs']
DSIG = {p['pair']: p['Dsig'] for p in json.load(open(f'{D}/pair-distances.json'))['pairs']} if os.path.exists(f'{D}/pair-distances.json') else {}
os.makedirs(SUM, exist_ok=True)
def seeded(domain):
    h = keccak.new(digest_bits=256); h.update(f'E4-2026-10-11-{domain}'.encode()); return np.random.default_rng(int.from_bytes(h.digest()[:8], 'big'))
rng_boot, rng_perm, rng_cal = seeded('bootstrap'), seeded('permutation'), seeded('calibration')

# ---------------------------------------------------------------- read the record
pops = {}; counts = collections.Counter(); per_worker_counts = {}
for fn in sorted(glob.glob(f'{REC}/populations/*.jsonl')):
    lines = [json.loads(l) for l in open(fn) if l.strip()]
    if not lines or not lines[-1].get('final'): counts['unfinished'] += 1; continue
    h = lines[0]; gens = [l for l in lines if 'g' in l]; fin = lines[-1]
    key = (h['pair'], h['f'], h['replicate'])
    g1 = gens[0]; fl = h['founderLife']
    best1 = max((p['l'] for p in g1['props'] if 'l' in p and not p.get('loop')), default=None)
    pops[key] = {'B': [l['B'] for l in gens], 'B0': math.log2(fl), 'loops': [l['loops'] for l in gens], 'hf': sum(l['hf'] for l in gens), 'unins': sum(l['unins'] for l in gens),
                 'gen1_best': best1, 'gen1_up': sum(1 for p in g1['props'] if 'l' in p and not p.get('loop') and p['l'] > fl),
                 'gen1_checked': sum(1 for p in g1['props'] if p.get('e3')), 'final_sigs': [s[1] for s in fin['survivors']], 'genomeId': h['genomeId'],
                 'logical': fin['logical'], 'physical': fin['physical'], 'cacheHits': fin['cacheHits'], 'collisions': sum(1 for l in lines if l.get('note') == 'tie-key collision')}
    counts['populations'] += 1; counts['gen1_checked'] += pops[key]['gen1_checked']; counts['harness_failures'] += pops[key]['hf']; counts['uninstantiable'] += pops[key]['unins']; counts['tie_key_collisions'] += pops[key]['collisions']
pairs = sorted({q for q, _, _ in pops})
def runs(q, f): return [pops[(q, f, r)] for r in range(R) if (q, f, r) in pops]
Q = [q for q in pairs if len(runs(q, 0)) == R and len(runs(q, 1)) == R]; n = len(Q)
if n != len(pairs): print(f'WARNING: {len(pairs) - n} pairs incomplete; analysis uses the {n} complete pairs', file=sys.stderr)
gid = {q: (FOUND[q]['P']['genomeId'], FOUND[q]['N']['genomeId']) for q in Q}
dA1 = np.array([PRED[gid[q][1]]['A1'] - PRED[gid[q][0]]['A1'] for q in Q])
dA2 = np.array([(PRED[gid[q][1]]['A2'] or 0) - (PRED[gid[q][0]]['A2'] or 0) for q in Q])
dA3 = np.array([PRED[gid[q][1]]['A3'] - PRED[gid[q][0]]['A3'] for q in Q])
Bmat = {q: np.array([[p['B'] for p in runs(q, f)] for f in (0, 1)]) for q in Q}           # (2, R, G)
def dB_at(g): return np.array([Bmat[q][1, :, g - 1].mean() - Bmat[q][0, :, g - 1].mean() for q in Q])  # §5.9: mean over replicates
dB = dB_at(G)

# ---------------------------------------------------------------- resampling index sets (§7.0), drawn once
BOOT_IDX = [rng_boot.integers(0, n, n) for _ in range(NBOOT)] if n else []
PERM = [[rng_perm.permutation(2 * R) for _ in Q] for _ in range(NPERM)]

# ---------------------------------------------------------------- primary (§3): Spearman, average ranks, fixed pair bootstrap
def rho(x, y):
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0: return None
    return float(spearmanr(x, y).correlation)
def boot(x, y):
    vals = []; undefined = 0
    for idx in BOOT_IDX:
        r_ = rho(x[idx], y[idx])
        if r_ is None: undefined += 1
        else: vals.append(r_)
    lo, hi = (float(np.percentile(vals, 2.5, method='linear')), float(np.percentile(vals, 97.5, method='linear'))) if vals else (None, None)
    return {'ci95': [lo, hi], 'undefined_resamples': undefined, 'resamples': len(BOOT_IDX)}
primary = {'rho': rho(dA1, dB), 'pairs': n, 'pairs_dB_zero': int(np.sum(dB == 0)), **boot(dA1, dB), 'reference_smallest_substantial': 0.3,
           'leave_one_out': [rho(np.delete(dA1, i), np.delete(dB, i)) for i in range(n)]}
secondary_pred = {'A2': {'rho': rho(dA2, dB), **boot(dA2, dB)}, 'A3': {'rho': rho(dA3, dB), **boot(dA3, dB)},
                  'A4': 'identically zero across all founders in the frozen predictor record; no correlation test'}

# ---------------------------------------------------------------- secondary (§3): founder identity, S with the within-pair permutation
BG = {q: Bmat[q][:, :, G - 1] for q in Q}                                                    # (2, R)
def S_of(mats):
    num = np.mean([abs(m[1].mean() - m[0].mean()) for m in mats])
    den = np.mean([math.sqrt((m[0].var(ddof=1) + m[1].var(ddof=1)) / 2) for m in mats])
    return (num / den) if den > 0 else None
def separated(mats): return sum(1 for m in mats if m[1].min() > m[0].max() or m[1].max() < m[0].min())   # strictly above / strictly below
obs_S = S_of([BG[q] for q in Q]); obs_sep = separated([BG[q] for q in Q]); ge = 0; undef = 0; sep_ge = 0
for perm in PERM:
    mats = [BG[q].reshape(-1)[perm[i]].reshape(2, R) for i, q in enumerate(Q)]
    s_ = S_of(mats)
    if s_ is None: undef += 1
    elif obs_S is not None and s_ >= obs_S: ge += 1
    if separated(mats) >= obs_sep: sep_ge += 1
secondary = {'S': obs_S, 'permutation_p': ((ge + 1) / (NPERM + 1)) if obs_S is not None else None, 'permutations': NPERM, 'undefined_permutations': undef,
             'pairs_fully_separated': obs_sep, 'separated_tie_free_upper_bound': n * 2 / math.comb(2 * R, R), 'separated_permutation_p': (sep_ge + 1) / (NPERM + 1),
             'positive': (obs_S is not None and (ge + 1) / (NPERM + 1) < 0.05)}

# ---------------------------------------------------------------- tertiary (§3): the horizon with the same index sets
horizon = []
for g in range(1, G + 1):
    d = dB_at(g); r_ = rho(dA1, d); bt = boot(dA1, d) if r_ is not None else {'ci95': [None, None], 'undefined_resamples': None}
    horizon.append({'g': g, 'rho': r_, 'ci95': bt['ci95'], 'pairs_dB_zero': int(np.sum(d == 0))})

# ---------------------------------------------------------------- generation-1 calibration (§7.5)
allpops = [pops[k] for k in sorted(pops) if k[0] in Q]
u = np.array([PRED[p['genomeId']]['u'] for p in allpops]); pK = 1 - (1 - u / 16320) ** 64
K_obs = int(sum(1 for p in allpops if p['gen1_up'] > 0))
pmf = np.array([1.0])
for pi in pK: pmf = np.convolve(pmf, [1 - pi, pi])
cdf = np.cumsum(pmf); K_lower = float(cdf[K_obs]); K_upper = float(1 - (cdf[K_obs - 1] if K_obs > 0 else 0.0))
def best64(F):                                   # [(category, P(best <= category))], categories ascending: 'none' then finite counts
    fin = {int(k): v for k, v in F['finite'].items()}; cum = F['loop'] + F['refused'] + F['harnessFailure']; lv = [('none', (cum / 16320) ** 64)]
    for k in sorted(fin): cum += fin[k]; lv.append((k, (cum / 16320) ** 64))
    return lv
def mid_p(lv, x):
    prev = 0.0
    for k, c in lv:
        if k == x: return prev + 0.5 * (c - prev)
        prev = c
    raise ValueError(f'observed {x} not in the distribution')
LV = [best64(PRED[p['genomeId']]['F']) for p in allpops]
M_obs = float(np.mean([mid_p(lv, p['gen1_best'] if p['gen1_best'] is not None else 'none') for lv, p in zip(LV, allpops)]))
CS = [np.array([c for _, c in lv]) for lv in LV]
M_null = np.empty(NCAL)
for k in range(NCAL):
    uu = rng_cal.random(len(CS)); tot = 0.0
    for cs, x in zip(CS, uu):
        j = min(int(np.searchsorted(cs, x, side='right')), len(cs) - 1); prev = cs[j - 1] if j > 0 else 0.0; tot += prev + 0.5 * (cs[j] - prev)
    M_null[k] = tot / len(CS)
json.dump({'domain': 'E4-2026-10-11-calibration', 'runs': NCAL, 'M': M_null.tolist()}, open(f'{SUM}/calibration-M.json', 'w'))
calibration = {'K': {'observed': K_obs, 'expected': float(pK.sum()), 'p_le': K_lower, 'p_ge': K_upper, 'investigate': K_lower <= 1e-4 or K_upper <= 1e-4, 'populations': len(allpops)},
               'M': {'observed': M_obs, 'null_mean': float(M_null.mean()), 'null_sd': float(M_null.std()), 'null_min': float(M_null.min()), 'null_max': float(M_null.max()), 'investigate': bool(M_obs < M_null.min() or M_obs > M_null.max()), 'runs': NCAL},
               'gen1_children_checked_against_E3': counts['gen1_checked'], 'note': 'given the anchored seed and the sealed tables, these detect a seed-stream or bookkeeping defect only'}

# ---------------------------------------------------------------- convergence (§3c)
def tv(a, b_):
    ca, cb = collections.Counter(a), collections.Counter(b_); return 0.5 * sum(abs(ca[k] / 64 - cb[k] / 64) for k in set(ca) | set(cb))
conv = []
for q in Q:
    P_, N_ = runs(q, 0), runs(q, 1)
    between = float(np.mean([tv(p['final_sigs'], nn['final_sigs']) for p in P_ for nn in N_]))
    within = float(np.mean([tv(a['final_sigs'], c['final_sigs']) for rs in (P_, N_) for a, c in itertools.combinations(rs, 2)]))
    conv.append({'pair': q, 'between_PN': between, 'within_founder': within})
bw = np.array([c['between_PN'] for c in conv]); wi = np.array([c['within_founder'] for c in conv]); diffs = bw - wi
bs = [float(np.mean(diffs[idx])) for idx in BOOT_IDX]
convergence = {'mean_between_PN': float(bw.mean()), 'mean_within_founder': float(wi.mean()), 'mean_difference': float(diffs.mean()),
               'difference_ci95': [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if bs else [None, None], 'per_pair': conv}

# ---------------------------------------------------------------- loops, strata, outcome, counts
first_loop = {(q, f): [next((g + 1 for g, c in enumerate(p['loops']) if c), None) for p in runs(q, f)] for q in Q for f in (0, 1)}
loops = {'mean_loop_offspring_per_population_P': float(np.mean([sum(p['loops']) for q in Q for p in runs(q, 0)])), 'mean_loop_offspring_per_population_N': float(np.mean([sum(p['loops']) for q in Q for p in runs(q, 1)])),
         'populations_with_any_loop_offspring': int(sum(1 for v in first_loop.values() for x in v if x is not None)), 'A4_note': 'A4 is identically zero across founders; no predictor test'}
def stratum(mask):
    idx = [i for i, q in enumerate(Q) if mask(q)]
    if len(idx) < 4: return {'pairs': len(idx)}
    x, y = dA1[idx], dB[idx]; vals = [rho(x[np.clip(ix, 0, len(idx) - 1) % len(idx)], y[np.clip(ix, 0, len(idx) - 1) % len(idx)]) for ix in BOOT_IDX]
    vals = [v for v in vals if v is not None]
    mats = [BG[Q[i]] for i in idx]; s_obs = S_of(mats); ge_ = sum(1 for perm in PERM if (s_ := S_of([BG[Q[i]].reshape(-1)[perm[i]].reshape(2, R) for i in idx])) is not None and s_obs is not None and s_ >= s_obs)
    return {'pairs': len(idx), 'rho': rho(x, y), 'ci95': [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else [None, None], 'S': s_obs, 'S_permutation_p': ((ge_ + 1) / (NPERM + 1)) if s_obs is not None else None}
strata = {'lifespan_3': stratum(lambda q: FOUND[q]['founderLife'] == 3), 'lifespan_ge4': stratum(lambda q: FOUND[q]['founderLife'] >= 4),
          'genesis': stratum(lambda q: FOUND[q]['set'] == 'genesis'), 'control': stratum(lambda q: FOUND[q]['set'] == 'control')}
adapts = {gid[q][f]: any(p['B'][G - 1] > p['B0'] for p in runs(q, f)) for q in Q for f in (0, 1)}
lo, hi = primary['ci95']; est = primary['rho']
prim_pos = est is not None and lo is not None and lo > 0 and est > 0; prim_null = est is None or lo is None or (lo <= 0 <= hi)
prim_neg = est is not None and hi is not None and hi < 0
early = any(h['rho'] is not None and h['ci95'][0] is not None and h['ci95'][0] > 0 and h['rho'] > 0 for h in horizon if h['g'] < G)
outcome = ('A' if not any(adapts.values()) else 'F' if prim_neg else 'C' if prim_pos else 'D' if (prim_null and secondary['positive']) else 'E' if (prim_null and early) else 'B' if prim_null else 'F')
results = {'experiment': 'E4', 'generations': G, 'replicates': R, 'pairs_analysed': n, 'counts': dict(counts),
           'compute': {'logical_proposals': int(sum(p['logical'] for p in allpops)), 'physical_executions': int(sum(p['physical'] for p in allpops)), 'cache_hits': int(sum(p['cacheHits'] for p in allpops))},
           'primary': primary, 'secondary_founder_identity': secondary, 'secondary_predictors': secondary_pred, 'horizon': horizon, 'calibration': calibration,
           'convergence': convergence, 'loops': loops, 'strata': strata, 'founders_adapted': {'P': int(sum(adapts[gid[q][0]] for q in Q)), 'N': int(sum(adapts[gid[q][1]] for q in Q))},
           'outcome_label': outcome, 'outcome_rules': 'E4-after.md §3', 'dB_G': {str(q): float(v) for q, v in zip(Q, dB)}, 'dA1': {str(q): float(v) for q, v in zip(Q, dA1)}, 'Dsig': {str(q): DSIG.get(q) for q in Q}}
json.dump(results, open(f'{SUM}/results.json', 'w'), indent=1)
traj = {'pairs': [{'label': f"pair {q} · {FOUND[q]['label']}", 'founderLog2': math.log2(FOUND[q]['founderLife']),
                   'P': [p['B'] for p in runs(q, 0)], 'N': [p['B'] for p in runs(q, 1)],
                   'loopP': [None if x is None else x - 1 for x in first_loop[(q, 0)]], 'loopN': [None if x is None else x - 1 for x in first_loop[(q, 1)]]} for q in Q]}
json.dump(traj, open(f'{SUM}/trajectories.json', 'w'))
fmt = lambda v: 'undefined' if v is None else f'{v:.3f}'
rep = [f"E4 analysis · {n} pairs · {counts['populations']} populations · G {G} · R {R} · outcome label {outcome}",
       f"compute: logical {results['compute']['logical_proposals']:,} · physical {results['compute']['physical_executions']:,} · cache hits {results['compute']['cache_hits']:,} · harness failures {counts['harness_failures']} · uninstantiable {counts['uninstantiable']} · tie-key collisions {counts['tie_key_collisions']}",
       f"PRIMARY rho(dA1, dB_{G}) = {fmt(primary['rho'])} [{fmt(lo)}, {fmt(hi)}] · reference 0.3 · pairs with dB = 0: {primary['pairs_dB_zero']} · undefined resamples {primary['undefined_resamples']}",
       f"SECONDARY S = {fmt(secondary['S'])} · permutation p {fmt(secondary['permutation_p'])} · fully separated pairs {obs_sep} (tie-free bound {secondary['separated_tie_free_upper_bound']:.2e}, permutation p {secondary['separated_permutation_p']:.4f})",
       f"predictors A2 rho {fmt(secondary_pred['A2']['rho'])} · A3 rho {fmt(secondary_pred['A3']['rho'])} · A4 none",
       f"calibration K {K_obs} observed vs {pK.sum():.1f} expected (p_le {K_lower:.4f}, p_ge {K_upper:.4f}) · M {M_obs:.4f} vs null {M_null.mean():.4f}±{M_null.std():.4f} [{M_null.min():.4f}, {M_null.max():.4f}] · gen-1 children checked {counts['gen1_checked']}",
       f"convergence TV between P-N {bw.mean():.3f} · within founder {wi.mean():.3f} · difference {diffs.mean():.3f} {convergence['difference_ci95']}",
       f"loops: populations with any loop offspring {loops['populations_with_any_loop_offspring']} · founders adapted P {results['founders_adapted']['P']} N {results['founders_adapted']['N']} of {n} each",
       "horizon rho_g: " + ' '.join(f"g{h['g']}={fmt(h['rho'])}" for h in horizon if h['g'] in (1, 2, 4, 8, 16, 32, 64, 128, 256))]
open(f'{SUM}/report.txt', 'w').write('\n'.join(rep) + '\n'); print('\n'.join(rep))
