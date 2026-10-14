#!/usr/bin/env python3
"""E4 reproducibility subset (E4-after.md §6): compare replicate-0 population records from the run with the second machine's.
Compared per generation: parent slot, position, value, child hash, class (the c / u keys and the presence of a fitness), fitness,
the 64 survivor slots in order (sel + fits), B_g; and the final survivors (bytes, signature hash, fitness). Excluded: cache-hit
flags and execution counts (logical, physical, cacheHits), retries, timestamps. A harness failure in either run is a difference.
usage: e4_repro.py <populations dir A: the run> <populations dir B: second machine> [--genomes out.json]
--genomes: replay each differing population from its founder and write the first differing proposal's child genome (64 bytes)
with both records' signature hash and probe-A count, for re-evaluation (scripts/e4_repro_probe.ts)."""
import json, os, sys, glob
A, B = sys.argv[1], sys.argv[2]
GENOMES = sys.argv[sys.argv.index('--genomes') + 1] if '--genomes' in sys.argv else None
def load(fn): return [json.loads(l) for l in open(fn) if l.strip()]
def prop_key(p): return (p['p'], p['pos'], p['val'], p.get('h'), p.get('c'), p.get('u'), p.get('l'), p.get('loop'))
files = sorted(glob.glob(os.path.join(B, '*.jsonl')))
pops = 0; identical = 0; diffs = []; gens = 0; props = 0; hfA = hfB = 0
for fb in files:
    name = os.path.basename(fb); fa = os.path.join(A, name)
    if not os.path.exists(fa): diffs.append((name, 'missing in the run')); continue
    a, b = load(fa), load(fb); pops += 1
    ha, hb = a[0], b[0]
    for k in ('pair', 'f', 'replicate', 'seed', 'founderBytes', 'founderLife', 'founderSigH', 'genomeLength', 'worldId', 'harnessVersion', 'protocol'):
        if ha.get(k) != hb.get(k): diffs.append((name, f'header {k}: {ha.get(k)} vs {hb.get(k)}'))
    ga = [l for l in a if 'g' in l]; gb = [l for l in b if 'g' in l]
    if len(ga) != len(gb): diffs.append((name, f'generations {len(ga)} vs {len(gb)}'))
    first = None
    for la, lb in zip(ga, gb):
        gens += 1; props += len(la['props'])
        hfA += la.get('hf', 0); hfB += lb.get('hf', 0)
        if la.get('hf') or lb.get('hf'): diffs.append((name, f'g{la["g"]}: harness failure(s) run {la.get("hf")} second {lb.get("hf")}'))
        if la['g'] != lb['g']: first = first or f'g order {la["g"]} vs {lb["g"]}'; break
        if [prop_key(p) for p in la['props']] != [prop_key(p) for p in lb['props']]:
            i = next(i for i, (p, q) in enumerate(zip(la['props'], lb['props'])) if prop_key(p) != prop_key(q))
            first = first or f'g{la["g"]} proposal {i}: {prop_key(la["props"][i])} vs {prop_key(lb["props"][i])}'; break
        if la['sel'] != lb['sel'] or la['fits'] != lb['fits']: first = first or f'g{la["g"]}: selection or fitness differs'; break
        if la['B'] != lb['B']: first = first or f'g{la["g"]}: B {la["B"]} vs {lb["B"]}'; break
    fa_, fb_ = a[-1], b[-1]
    if not (fa_.get('final') and fb_.get('final')): first = first or 'final line missing'
    elif fa_['survivors'] != fb_['survivors']: first = first or 'final survivors differ'
    if first: diffs.append((name, first))
    else: identical += 1
print(f'populations compared {pops} · identical {identical} · with differences {pops - identical} · generations {gens:,} · proposals {props:,} · harness failures run {hfA} second {hfB}')
for n, d in diffs[:50]: print(f'  {n}: {d}')
if GENOMES:
    out = []
    for name, _ in diffs:
        a, b = load(os.path.join(A, name)), load(os.path.join(B, name))
        ga = [l for l in a if 'g' in l]; gb = [l for l in b if 'g' in l]
        slots = [bytes.fromhex(a[0]['founderBytes'][2:])] * 64
        for la, lb in zip(ga, gb):
            children = []
            for p in la['props']: c = bytearray(slots[p['p']]); c[p['pos']] = p['val']; children.append(bytes(c))
            hit = next((i for i, (p, q) in enumerate(zip(la['props'], lb['props'])) if prop_key(p) != prop_key(q)), None)
            if hit is not None:
                p, q = la['props'][hit], lb['props'][hit]
                out.append({'pop': name[:-6], 'g': la['g'], 'slot': hit, 'genome': '0x' + children[hit].hex(), 'run': {'h': p.get('h'), 'l': p.get('l'), 'loop': p.get('loop')}, 'second': {'h': q.get('h'), 'l': q.get('l'), 'loop': q.get('loop')}, 'mut': {'p': p['p'], 'pos': p['pos'], 'val': p['val']}})
                break
            slots = [slots[int(r[1:])] if r[0] == 's' else children[int(r[1:])] for r in la['sel']]
    json.dump(out, open(GENOMES, 'w'), indent=1); print(f'wrote {len(out)} divergent genomes → {GENOMES}')
sys.exit(0 if (pops == identical and pops == 176) else 1)
