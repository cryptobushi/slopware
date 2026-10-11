"""Canonical E3 child tables for E4's generation-1 deterministic check (E4-after.md §6). Read-only over the E3 record.
Writes <out>/<genomeId>.tsv, lines "pos,val,cls,sigH,life,loop" sorted by (pos, val), for the 176 E4 founders, and prints
each table's sha256 beside predictors.json's tableHash; exits non-zero on any mismatch.
Usage: python3 scripts/e4_tables.py <e3-record-dir> <predictors.json> <out-dir>"""
import json, glob, sys, os, hashlib
rec, predf, out = sys.argv[1:4]; os.makedirs(out, exist_ok=True)
pred = json.load(open(predf))['founders']; want = set(pred)
rows = {g: [] for g in want}
for f in sorted(glob.glob(os.path.join(rec, 'neighbourhoods', 'main', 'placements-*.jsonl'))):
    for l in open(f):
        i = l.find('"g":"'); g = l[i + 5:l.find('"', i + 5)]
        if g in want: rows[g].append(json.loads(l))
bad = 0
for g in sorted(want):
    canon = []
    for d in sorted(rows[g], key=lambda d: (d['pos'], d['val'])):
        reach = d.get('reach') or []; is_loop = 'loop' in reach
        cls = 'harness_failure' if d.get('hf') else 'refused' if d.get('sigH') is None else d['cls']
        canon.append(f"{d['pos']},{d['val']},{cls},{d.get('sigH') or ''},{d['life']},{int(is_loop)}")
    text = "\n".join(canon) + "\n"; h = hashlib.sha256(text.encode()).hexdigest()
    open(os.path.join(out, g + '.tsv'), 'w').write(text)
    if h != pred[g]['tableHash']: bad += 1; print('MISMATCH', g, h, pred[g]['tableHash'])
print(f"{len(want)} tables written to {out} · hash mismatches {bad}")
sys.exit(1 if bad else 0)
