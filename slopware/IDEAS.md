# Ideas on hold

Things worth keeping that do not yet have a place. Each entry says where it might fit and what would have to be true first. Nothing here is a commitment.

## Neighbourhood maps (2026-10-08) — tried and set aside

**Outcome.** Rendered from E1 on 2026-10-08 for releases 1 and 51 with the palette below. Correct, and almost entirely white: a flat landscape makes a flat picture. Set aside by the artist the same day as the visual for the work. The generator stays in `scripts/e1_descent.py` because the data it draws is the right data; the presentation moves to a scrolling essay (next entry).


**The idea.** Every genome's one-mutant neighbourhood is a grid: 64 positions by 255 replacement values, each cell one child, each child with an outcome under world v0. Colour the cells by outcome class and the grid is an image of the territory around a program. A program that dies on its first byte is a flat field with one bright column at position zero. A program that executes five instructions has structure across its first columns. Nothing in the image is drawn; the only human choice is the palette, fixed and published once.

**Why it matters.** It would be the first visual object in the project that nobody designed, it is reproducible by anyone from the record, and it shows at a glance the thing the next phase of the experiment is about: what surrounds a program.

**Where it cannot go.** The installer's receipts. Their metadata is immutable, and the catalogue's promise is facts only; a map is the lab's observation of behaviour under one environment. Putting it on a receipt would collapse the three layers (catalogue states, lab records, readings interpret).

**Where it fits now.** The readings page, beside each release's life sentence, as the lab's territory view, generated from E1's record.

**Where it might fit later.** As the image of a future contract whose promise already includes observation, for example a fossil receipt ("chosen from the record; here is its ancestry and what the lab observed"). The receipt would say what the image is: the lab's observation, which world, which date.

**If it ever goes on chain.** 16,320 cells at two bits per outcome class is about 4 KB, storable as a blob for a few dollars at low gas; an SVG drawn from it on chain needs no off-chain dependency. The palette and the outcome classes would be frozen with the contract and the record's root hash anchored, so any image can be checked against the data that produced it.

**What has to be true first.** E1 complete and published; a palette chosen and written down once; the outcome classes frozen (they are, in the E1 protocol §6); a decision on fossils and fees (roadmap Part IX / Era 9).

**Palette, fixed 2026-10-08 by the artist** (in `scripts/e1_descent.py`): white for a child identical to its parent and for the parent's own byte; black for a child that died sooner; dark grey for a different death at the same length; mid grey for a child that lived longer; one red-brown accent for a clean halt. Rows are positions 0–63, top to bottom; columns are replacement values 0–255. First rendered from E1 on 2026-10-08 (releases 1 and 51).

**Open.** Whether a map of a *lineage* (many generations) has a natural form.

## THREADS — the E1 research edition (fixed 2026-10-08)

Every genesis program as a walk: the sixty-four bytes read in order turn and advance a pen; the whole walk in faint grey (what the program is), the executed prefix in black (how much of itself it lived), a red mark where a program reached three or more instructions. Grid in release order, genesis only. Rules fixed in `scripts/e1_threads.py` before E1's results were known (E1 amendment 6). The ghosts (below) stay for the readings page, one per release.

## Ghosts (2026-10-08)

A release's sixty-four bytes in Courier with all 16,320 one-byte siblings printed as a typographic field: 64 columns × 255 rows of hex, pale where a sibling behaves like the parent, dark where it lives longer, mid where it dies differently, red where it stops cleanly, the parent's own byte black. For the readings page, one per release, generated from the E1 record. Not for the receipts, which stay plain.

## The neighbourhoods essay (2026-10-08) — set aside

Judged confusing in prototype; replaced by a short results page per experiment (one image, five hypotheses with numbers, three sentences, the data) and one line per release on the readings page.



A scrolling, data-driven piece in the manner of pudding.cool, in the site's own register (Courier, black on white, one red accent, motion only for data), at `slopware.fun/neighbourhoods`. Eight moves: one program dying on its first byte · its first byte fanned into 255 siblings, 54 of which live a step longer and one of which stops cleanly (H3, watched) · the full 16,320-child grid where 63 rows do nothing (H2, felt) · 803 parents arranged by how many instructions they execute, the lively few growing as you scroll · genesis and control clouds overlaid and indistinguishable (H1) · a counter to twenty-six million with the "anything new" bar staying at zero (H5) · small multiples of the parents with texture, the hills · three plain sentences. Needs aggregates captured from the E1 record before the droplet is destroyed: per-parent per-position class counts, child-versus-parent lifespan distribution, first-byte outcomes by opcode.

## Random walks on the living (2026-10-08)

From the few genesis programs that execute more than one byte, take long random one-byte walks, keeping only steps that stay alive. How far can a program wander without dying? Are the living programs connected to one another or isolated islands? This is the single most important fact for whether evolution can move on this machine, and it is cheap to measure. A candidate for the second pre-registered experiment. Parents must be chosen by a stated rule written before looking at E1's results (for example, every genesis genome whose probe-A lifespan is at least three).

## Two-parent children (2026-10-08)

Recombination between two genesis programs, the catalogue's first children with two owned ancestors. Waits for the fixed-length rule to expire or for a crossover that preserves length.
