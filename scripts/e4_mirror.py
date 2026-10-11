"""E4 picture, draft rules (design stage; to be frozen in the pre-registration). Usage:
  python3 scripts/e4_mirror.py <trajectories.json> <out.png> [scale] [--mock]
One strip per founder pair, 88 strips in parents.json order, generations left to right. From a shared baseline the
P-founded replicates are drawn upward and the N-founded replicates downward; height is log2 of the population's best
finite fitness; one hairline per replicate; a red mark at the first generation a replicate produced a loop-class
offspring. The vertical axis is shared by every strip: the baseline is log2 of the founders' own fitness per pair
(both founders have the same), and one unit of height is one doubling, the same in every strip; nothing is autoscaled.
Identical trajectories give a symmetric strip; no adaptation gives a flat line; divergence gives asymmetry.
Input: {"pairs":[{"label":..., "founderLog2":..., "P":[[B_1..B_G] per replicate], "N":[...], "loopP":[g or null per rep],
"loopN":[...]}]}. --mock draws synthetic trajectories from a toy model and writes no claim about anything.
"""
import json, math, sys, random
from PIL import Image, ImageDraw
args = [a for a in sys.argv[1:] if not a.startswith('--')]; mock = '--mock' in sys.argv
S = float(args[2]) if len(args) > 2 else 1.0
G = 256; R = 8
if mock:
    rng = random.Random(4)
    pairs = []
    for i in range(88):
        kind = rng.choice(['same', 'same', 'flat', 'diverge', 'converge'])
        def traj(bias):
            b = 0.0; out = []
            for g in range(G):
                p = 0.03 + bias * 0.02
                if rng.random() < p: b += rng.choice([0.2, 0.3, 0.5, 1.0])
                out.append(b)
            return out
        f0 = math.log2(rng.choice([3, 3, 3, 3, 4, 5, 6]))
        if kind == 'flat': P = [[0.0] * G for _ in range(R)]; N = [[0.0] * G for _ in range(R)]
        elif kind == 'same': P = [traj(0) for _ in range(R)]; N = [traj(0) for _ in range(R)]
        elif kind == 'diverge': P = [traj(0) for _ in range(R)]; N = [traj(1.5) for _ in range(R)]
        else:
            P = [traj(0) for _ in range(R)]; N = [traj(1.5) for _ in range(R)]
            cap = max(t[-1] for t in P)
            for t in N:                      # best fitness never falls under (mu + lambda) survival; the mock plateaus
                for g in range(G): t[g] = min(t[g], cap)
        loopP = [rng.randrange(G) if rng.random() < 0.15 else None for _ in range(R)]
        loopN = [rng.randrange(G) if rng.random() < 0.15 else None for _ in range(R)]
        pairs.append({"label": f"mock {i}", "founderLog2": f0, "P": P, "N": N, "loopP": loopP, "loopN": loopN})
else:
    pairs = json.load(open(args[0]))["pairs"]
out = args[1]
UNIT = 6 * S          # pixels per doubling, shared by every strip
HALF = 8 * UNIT       # room for eight doublings each way (E2's largest finite run was 2^13.6 from 2^1.6)
GAP = 3 * S; M = 24 * S
W = int(2 * M + G * 2 * S); H = int(2 * M + len(pairs) * (2 * HALF + GAP))
img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
def y_of(base, b, up): return base - (b * UNIT if up else -b * UNIT)
for i, pr in enumerate(pairs):
    base = M + HALF + i * (2 * HALF + GAP)
    d.line([(M, base), (W - M, base)], fill=(200, 200, 200), width=max(1, int(S)))
    for side, up in (("P", True), ("N", False)):
        for k, t in enumerate(pr[side]):
            pts = [(M + g * 2 * S, y_of(base, min(t[g], 8), up)) for g in range(len(t))]
            d.line(pts, fill=(0, 0, 0), width=max(1, int(S)))
            lg = pr["loop" + side][k]
            if lg is not None:
                x = M + lg * 2 * S; y = y_of(base, min(t[lg], 8), up)
                d.rectangle([x - S, y - S, x + S, y + S], fill=(200, 60, 30))
img.save(out); print(f"{out}: {W}x{H}, {len(pairs)} strips, unit {UNIT}px per doubling")
