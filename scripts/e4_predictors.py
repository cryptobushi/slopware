"""E4 predictor table from the sealed E3 record. Read-only over record/neighbourhoods/main/placements-*.jsonl and
summaries-*.jsonl. Founders: the 88 parents (P<p>) and the 88 walk-0 target-60 endpoints (E<p>.0.60).

Per founder, over its 16,320 one-byte proposals (16,319 placeable children + 1 uninstantiable), under fitness F2
(probe-A instruction count; loop class = out of gas after more than 32 instructions, E2's operational flag):
  A1 = u / 16320, u = placeable children that are finite and whose probe-A count exceeds the founder's
  A2 = log2(max finite child probe-A count)
  A3 = children with the founder's exact signature / 16320
  A4 = loop-class children / 16320
  F  = the complete proposal distribution: {"finite": {life: count}, "loop": count, "refused": count, "harnessFailure": count}
  tableHash = sha256 of the canonical child table "pos,val,cls,sigH,life,loop\n" sorted by (pos, val) (the record's own
             manifest convention)
Usage: python3 e4_predictors.py <record-dir> <out.json>
"""
import json, glob, sys, os, math, hashlib, collections
rec, out = sys.argv[1], sys.argv[2]
def kec(b): return hashlib.sha256(b).hexdigest()
summ = {}
for f in glob.glob(os.path.join(rec, 'neighbourhoods', 'main', 'summaries-*.jsonl')):
    for l in open(f):
        r = json.loads(l); summ[r['genomeId']] = r
parents = sorted(p for p in range(200) if f'P{p}' in summ)
founders = [f'P{p}' for p in parents] + [f'E{p}.0.60' for p in parents]
want = set(founders)
rows = {g: [] for g in founders}
n = 0
for f in sorted(glob.glob(os.path.join(rec, 'neighbourhoods', 'main', 'placements-*.jsonl'))):
    for l in open(f):
        i = l.find('"g":"'); g = l[i + 5:l.find('"', i + 5)]
        if g not in want: continue
        d = json.loads(l); rows[g].append(d); n += 1
print('placement rows read for founders:', n, file=sys.stderr)
table = {}
for g in founders:
    s = summ[g]; life0 = s['selfLifespan']; ch = rows[g]
    assert len(ch) == 16320, (g, len(ch))
    fin = collections.Counter(); loop = refused = hf = neutral = u = 0; best = 0
    canon = []
    for d in sorted(ch, key=lambda d: (d['pos'], d['val'])):
        reach = d.get('reach') or []
        is_loop = 'loop' in reach
        if d.get('hf'): hf += 1; cls = 'harness_failure'
        elif d.get('sigH') is None: refused += 1; cls = 'refused'
        elif is_loop: loop += 1; cls = d['cls']
        else:
            fin[d['life']] += 1; cls = d['cls']
            if d['life'] > life0: u += 1
            best = max(best, d['life'])
            if d['cls'] == 'neutral': neutral += 1
        canon.append(f"{d['pos']},{d['val']},{cls},{d.get('sigH') or ''},{d['life']},{int(is_loop)}")
    table[g] = {"kind": s['kind'], "parentIndex": s['parentIndex'], "set": s['set'], "label": s['label'], "bytes": s['bytes'],
                "founderLife": life0, "founderLog2": math.log2(life0), "proposals": 16320, "placeable": 16320 - refused - hf,
                "u": u, "A1": u / 16320, "A2": (math.log2(best) if best else None), "A3": neutral / 16320, "A4": loop / 16320,
                "F": {"finite": {str(k): v for k, v in sorted(fin.items())}, "loop": loop, "refused": refused, "harnessFailure": hf},
                "tableHash": kec(("\n".join(canon) + "\n").encode())}
pairs = []
for p in parents:
    P, N = table[f'P{p}'], table[f'E{p}.0.60']
    assert P['founderLife'] == N['founderLife']
    pairs.append({"parentIndex": p, "P": f'P{p}', "N": f'E{p}.0.60', "dA1": N['A1'] - P['A1'], "dA2": (N['A2'] or 0) - (P['A2'] or 0), "dA3": N['A3'] - P['A3'], "dA4": N['A4'] - P['A4']})
json.dump({"experiment": "E4", "source": "E3 record root " + open(os.path.join(rec, 'ROOT')).read().strip() if os.path.exists(os.path.join(rec, 'ROOT')) else "E3 record",
           "fitness": "F2: probe-A instruction count; loop class (out of gas after >32 instructions) ineligible; denominators 16,320 proposals",
           "founders": table, "pairs": pairs}, open(out, 'w'), indent=1)
print('wrote', out, len(table), 'founders', len(pairs), 'pairs', file=sys.stderr)
