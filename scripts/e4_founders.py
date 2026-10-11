"""E4 founders: the 88 E3 parents (P<p>) and their walk-0 target-60 endpoints (E<p>.0.60), from the E3 summaries,
in parents.json order. Writes E4/founders.json: {"pairs":[{"pair":q,"parentIndex":p,"set","label","founderLife",
"P":{"genomeId","bytes"},"N":{"genomeId","bytes","hamming"}}]}. Usage: python3 scripts/e4_founders.py"""
import json, glob, hashlib
S = 'slopware/experiments/E3/summaries/neighbourhoods/main'
rows = {}
for f in glob.glob(f'{S}/summaries-*.jsonl'):
    for l in open(f):
        r = json.loads(l); rows[r['genomeId']] = r
parents = json.load(open('slopware/experiments/E2/parents.json'))['parents']
pairs = []
for q, par in enumerate(parents):
    P, N = rows[f'P{q}'], rows[f'E{q}.0.60']
    assert P['parentIndex'] == q and N['parentIndex'] == q and P['selfSignature'] == N['selfSignature'] and N['hamming'] >= 60
    assert P['bytes'].lower() == par['bytes'].lower() if 'bytes' in par else True
    pairs.append({"pair": q, "parentIndex": q, "set": P['set'], "label": P['label'], "founderLife": P['selfLifespan'],
                  "P": {"genomeId": f'P{q}', "bytes": P['bytes']}, "N": {"genomeId": f'E{q}.0.60', "bytes": N['bytes'], "hamming": N['hamming']}})
out = {"experiment": "E4", "source": "E3 summaries (record root 70471484778c5c91a8e7a299524af13d127bf491d70a0a62e7e53cd2628b8205), parents.json order", "pairs": pairs}
json.dump(out, open('slopware/experiments/E4/founders.json', 'w'), indent=1)
print(len(pairs), 'pairs ·', sum(1 for p in pairs if p['set'] == 'genesis'), 'genesis ·', 'sha256', hashlib.sha256(open('slopware/experiments/E4/founders.json', 'rb').read()).hexdigest())
