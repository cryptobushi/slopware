#!/usr/bin/env python3
"""E3 metrics (E3-somewhere-else.md §5) and their validation on synthetic neighbourhoods with known relationships.
This is instrument validation, not data: no E3 neighbourhood exists yet. Run: python3 scripts/e3_metrics.py

A neighbourhood is a list of children, each {"pos": 0..63, "val": 0..255, "sig": str, "cls": one of CLASSES}.
"""
import math, random, collections

CLASSES = ["neutral", "altered", "lengthened", "shortened", "lethal"]

def class_distribution(nb):
    c = collections.Counter(ch["cls"] for ch in nb); n = len(nb)
    return {k: c[k] / n for k in CLASSES}

def sig_distribution(nb):
    c = collections.Counter(ch["sig"] for ch in nb); n = len(nb)
    return {k: v / n for k, v in c.items()}

def total_variation(p, q):
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0) - q.get(k, 0)) for k in keys)

def D5(a, b): return total_variation(class_distribution(a), class_distribution(b))
def Dsig(a, b): return total_variation(sig_distribution(a), sig_distribution(b))
def reachable(nb): return {ch["sig"] for ch in nb}
def nonneutral(nb): return {(ch["pos"], ch["val"]) for ch in nb if ch["cls"] != "neutral"}
def jaccard(x, y): return len(x & y) / len(x | y) if (x | y) else 1.0
def JS(a, b): return jaccard(reachable(a), reachable(b))
def JM(a, b): return jaccard(nonneutral(a), nonneutral(b))
def expected_jaccard(na, nb_, total=16319):
    """Exact expected Jaccard of two independent uniformly random subsets of sizes na, nb_ of a set of size total:
    the intersection K is hypergeometric(total, na, nb_) and E[J] = sum_k P(K=k) k/(na+nb_-k). No plug-in approximation."""
    if na == 0 and nb_ == 0: return 1.0
    from math import comb
    lo, hi = max(0, na + nb_ - total), min(na, nb_)
    denom = comb(total, nb_)
    return sum(comb(na, k) * comb(total - na, nb_ - k) / denom * (k / (na + nb_ - k)) for k in range(lo, hi + 1))
def JM_null(a, b, total=16319): return expected_jaccard(len(nonneutral(a)), len(nonneutral(b)), total)
def JM_plugin(na, nb_, total=16319):
    inter = na * nb_ / total; return inter / (na + nb_ - inter) if (na + nb_) else 1.0

# ---------------------------------------------------------------- synthetic neighbourhoods
def synth(seed, n_nonneutral=600, sig_pool=40, positions=None, nonneutral_pairs=None):
    """A 16,319-child neighbourhood: a chosen set of (pos,val) pairs is non-neutral with signatures drawn from a pool."""
    rnd = random.Random(seed); nb = []
    pairs = nonneutral_pairs if nonneutral_pairs is not None else set()
    if nonneutral_pairs is None:
        poss = positions if positions is not None else list(range(64))
        while len(pairs) < n_nonneutral: pairs.add((rnd.choice(poss), rnd.randrange(256)))
    for pos in range(64):
        for val in range(256):
            if val == (pos * 7) % 256: continue          # the genome's own byte at this position (a stand-in parent)
            if pos == 0 and val == 0xEF: continue
            if (pos, val) in pairs:
                cls = rnd.choice(["altered", "altered", "lengthened", "shortened", "lethal"])
                nb.append({"pos": pos, "val": val, "sig": f"{cls}-{rnd.randrange(sig_pool)}", "cls": cls})
            else:
                nb.append({"pos": pos, "val": val, "sig": "SAME", "cls": "neutral"})
    return nb

if __name__ == "__main__":
    base = synth(1)
    print(f"children per neighbourhood: {len(base)}")
    # 1. identity: a neighbourhood against itself
    print(f"identical:        D5 {D5(base, base):.4f}  Dsig {Dsig(base, base):.4f}  JS {JS(base, base):.3f}  JM {JM(base, base):.3f}  JM_null {JM_null(base, base):.4f}")
    # 2. same aggregate, different exact set: regenerate with a different seed but the same parameters
    other = synth(2)
    print(f"same aggregate:   D5 {D5(base, other):.4f}  Dsig {Dsig(base, other):.4f}  JS {JS(base, other):.3f}  JM {JM(base, other):.3f}  JM_null {JM_null(base, other):.4f}   ← exact sets differ, aggregates near zero")
    # 3. partially shared exact set: 80% of the base pairs kept, 20% replaced
    rnd = random.Random(3); keep = set(rnd.sample(sorted(nonneutral(base)), int(0.8 * len(nonneutral(base)))))
    while len(keep) < len(nonneutral(base)): keep.add((rnd.randrange(64), rnd.randrange(256)))
    part = synth(3, nonneutral_pairs=keep)
    print(f"80% shared set:   D5 {D5(base, part):.4f}  Dsig {Dsig(base, part):.4f}  JS {JS(base, part):.3f}  JM {JM(base, part):.3f}  (expected JM ≈ 0.8/1.2 = 0.667)")
    # 4. different aggregate: twice as many non-neutral children
    more = synth(4, n_nonneutral=1200)
    print(f"2× non-neutral:   D5 {D5(base, more):.4f}  Dsig {Dsig(base, more):.4f}  JS {JS(base, more):.3f}  JM {JM(base, more):.3f}  JM_null {JM_null(base, more):.4f}   ← D5 ≈ 600/16319 = {600/16319:.4f}")
    # 5. different signature pool, same class mix: D5 near zero, Dsig high
    pool = synth(5, sig_pool=40); pool2 = [dict(ch, sig=ch["sig"].replace("-", "-x")) if ch["cls"] != "neutral" else ch for ch in synth(5, sig_pool=40)]
    print(f"relabelled sigs:  D5 {D5(pool, pool2):.4f}  Dsig {Dsig(pool, pool2):.4f}  JS {JS(pool, pool2):.3f}  JM {JM(pool, pool2):.3f}   ← same classes, disjoint exact signatures: Dsig = non-neutral fraction")
    # 6. localisation: non-neutral children confined to the first 24 positions vs spread
    loc = synth(6, positions=list(range(24)))
    print(f"localised vs spread: D5 {D5(base, loc):.4f}  JM {JM(base, loc):.3f}  JM_null {JM_null(base, loc):.4f}")
    na = len(nonneutral(base)); nb_ = len(nonneutral(other))
    print(f"\nnull check: exact hypergeometric E[J] {expected_jaccard(na, nb_):.5f} vs plug-in {JM_plugin(na, nb_):.5f} for sizes {na}, {nb_} of 16,319")
    print("\nreadings: identical → all zeros / ones; same-aggregate-different-set → D5≈0, Dsig≈0, JM≈null; shared set → JM tracks the shared fraction; aggregate change → D5 tracks the fraction changed; signature relabelling → Dsig high while D5 ≈ 0.")
