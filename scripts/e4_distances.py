"""E4 pair distances, descriptive (E4-after.md §3g): E3's D_sig between P and its walk-0 target-60 endpoint N, computed
from E3's published signature histograms (total variation distance between the two child-signature distributions over
placeable children, exactly as E3 §5.3). Writes E4/pair-distances.json. Usage: python3 scripts/e4_distances.py"""
import json, glob, hashlib
rows = {}
for f in glob.glob('slopware/experiments/E3/summaries/neighbourhoods/main/summaries-*.jsonl'):
    for l in open(f): r = json.loads(l); rows[r['genomeId']] = r
def dist(r): h = dict(r['signatureHistogram']); n = sum(h.values()); return {k: v / n for k, v in h.items()}
pairs = []
for q in range(88):
    P, N = dist(rows[f'P{q}']), dist(rows[f'E{q}.0.60'])
    tv = 0.5 * sum(abs(P.get(k, 0) - N.get(k, 0)) for k in set(P) | set(N))
    pairs.append({"pair": q, "Dsig": tv})
out = {"experiment": "E4", "source": "E3 summaries (record root 70471484778c5c91a8e7a299524af13d127bf491d70a0a62e7e53cd2628b8205); D_sig as E3 §5.3", "pairs": pairs}
json.dump(out, open('slopware/experiments/E4/pair-distances.json', 'w'), indent=1)
v = sorted(p['Dsig'] for p in pairs); print(f"88 pairs · D_sig min {v[0]:.4f} median {v[44]:.4f} max {v[-1]:.4f} · sha256 {hashlib.sha256(open('slopware/experiments/E4/pair-distances.json','rb').read()).hexdigest()}")
