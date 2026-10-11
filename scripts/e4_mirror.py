"""E4 picture, draft rules (design stage; frozen in the pre-registration). Usage:
  python3 scripts/e4_mirror.py <trajectories.json> <out.png> [size_px] [--mock]
88 founder pairs as an 8 x 11 grid in parents.json order, left to right then top to bottom, on a 1:1 square. Each cell is
one pair: generations left to right (0 at the left edge, 256 at the right), the pair's shared generation-0 fitness as the
horizontal centreline, the 16 P-founded replicates drawn upward and the 16 N-founded replicates downward, one hairline
per replicate, height log2 of the population's best finite fitness, a red mark at the first generation a replicate
produced a loop-class offspring. The vertical scale is global: one doubling is the same distance in every cell, and the
room per cell is the smallest whole number of doublings at or above the largest rise anywhere in the record (STEPS'
axis rule), so nothing is autoscaled and nothing is clipped. Geometry, ordering, scales, orientation, line weights, loop
mark and margins are fixed before the run.
Input: {"pairs":[{"label":..., "founderLog2":..., "P":[[B_1..B_G] per replicate], "N":[...], "loopP":[g or null per rep],
"loopN":[...]}]}. --mock draws synthetic trajectories from a toy model and makes no claim about anything.
"""
import json, math, sys, random
from PIL import Image, ImageDraw
args = [a for a in sys.argv[1:] if not a.startswith('--')]; mock = '--mock' in sys.argv
SIZE = int(args[2]) if len(args) > 2 else 2048
G = 256; R = 16; COLS, ROWS = 8, 11
if mock:
    rng = random.Random(4); pairs = []
    cases = ['flat', 'same', 'converge', 'diverge', 'runner', 'overlap']
    for i in range(88):
        kind = cases[i % len(cases)]
        def traj(bias, p0=0.02, steps=(0.2, 0.3, 0.5, 1.0)):
            b = 0.0; out = []
            for g in range(G):
                if rng.random() < p0 + bias * 0.015: b += rng.choice(steps)
                out.append(b)
            return out
        f0 = math.log2(rng.choice([3, 3, 3, 3, 4, 5, 6]))
        if kind == 'flat': P = [[0.0] * G for _ in range(R)]; N = [[0.0] * G for _ in range(R)]
        elif kind == 'same': P = [traj(0) for _ in range(R)]; N = [traj(0) for _ in range(R)]
        elif kind == 'diverge': P = [traj(0) for _ in range(R)]; N = [traj(1.5) for _ in range(R)]
        elif kind == 'converge':
            P = [traj(0) for _ in range(R)]; N = [traj(1.5) for _ in range(R)]; cap = max(t[-1] for t in P)
            for t in N:
                for g in range(G): t[g] = min(t[g], cap)
        elif kind == 'runner':
            P = [traj(0) for _ in range(R)]; N = [traj(0) for _ in range(R)]
            t = P[rng.randrange(R)]; g0 = rng.randrange(40, 200)
            for g in range(g0, G): t[g] = max(t[g], 7.5 + 0.002 * (g - g0))
        else:
            P = [traj(0, p0=0.01, steps=(0.5,)) for _ in range(R)]; N = [traj(0, p0=0.01, steps=(0.5,)) for _ in range(R)]
        loopP = [rng.randrange(G) if rng.random() < 0.1 else None for _ in range(R)]
        loopN = [rng.randrange(G) if rng.random() < 0.1 else None for _ in range(R)]
        pairs.append({"label": f"mock {i} {kind}", "founderLog2": f0, "P": P, "N": N, "loopP": loopP, "loopN": loopN})
else:
    pairs = json.load(open(args[0]))["pairs"]
out = args[1]
rise = max((max(max(t) for t in pr[side]) for pr in pairs for side in ("P", "N")), default=0.0)
D = max(1, math.ceil(rise - 1e-9))                       # doublings of room per half-cell, global
W = H = SIZE; M = SIZE * 0.04; GAP = SIZE * 0.012
cw = (W - 2 * M - (COLS - 1) * GAP) / COLS; ch = (H - 2 * M - (ROWS - 1) * GAP) / ROWS
UNIT = (ch / 2) / D                                      # pixels per doubling, the same in every cell
PX = cw / G                                               # pixels per generation
LW = max(1, round(SIZE / 2048))                           # hairline
img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
for i, pr in enumerate(pairs):
    r, c = divmod(i, COLS); x0 = M + c * (cw + GAP); yc = M + r * (ch + GAP) + ch / 2
    d.line([(x0, yc), (x0 + cw, yc)], fill=(205, 205, 205), width=LW)
    for side, sgn in (("P", -1), ("N", 1)):
        for k, t in enumerate(pr[side]):
            pts = [(x0 + g * PX, yc + sgn * t[g] * UNIT) for g in range(len(t))]
            d.line(pts, fill=(0, 0, 0), width=LW)
            lg = pr["loop" + side][k]
            if lg is not None:
                x = x0 + lg * PX; y = yc + sgn * t[lg] * UNIT; m = max(1.5, SIZE / 1024)
                d.rectangle([x - m, y - m, x + m, y + m], fill=(200, 60, 30))
img.save(out)
print(f"{out}: {W}x{H} · 8x11 cells of {cw:.0f}x{ch:.0f}px · room {D} doublings each way · {UNIT:.1f}px per doubling · {PX:.2f}px per generation")
