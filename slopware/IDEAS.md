# Ideas on hold

Things worth keeping that do not yet have a place. Each entry says where it might fit and what would have to be true first. Nothing here is a commitment.

## Neighbourhood maps (2026-10-08)

**The idea.** Every genome's one-mutant neighbourhood is a grid: 64 positions by 255 replacement values, each cell one child, each child with an outcome under world v0. Colour the cells by outcome class and the grid is an image of the territory around a program. A program that dies on its first byte is a flat field with one bright column at position zero. A program that executes five instructions has structure across its first columns. Nothing in the image is drawn; the only human choice is the palette, fixed and published once.

**Why it matters.** It would be the first visual object in the project that nobody designed, it is reproducible by anyone from the record, and it shows at a glance the thing the next phase of the experiment is about: what surrounds a program.

**Where it cannot go.** The installer's receipts. Their metadata is immutable, and the catalogue's promise is facts only; a map is the lab's observation of behaviour under one environment. Putting it on a receipt would collapse the three layers (catalogue states, lab records, readings interpret).

**Where it fits now.** The readings page, beside each release's life sentence, as the lab's territory view, generated from E1's record.

**Where it might fit later.** As the image of a future contract whose promise already includes observation, for example a fossil receipt ("chosen from the record; here is its ancestry and what the lab observed"). The receipt would say what the image is: the lab's observation, which world, which date.

**If it ever goes on chain.** 16,320 cells at two bits per outcome class is about 4 KB, storable as a blob for a few dollars at low gas; an SVG drawn from it on chain needs no off-chain dependency. The palette and the outcome classes would be frozen with the contract and the record's root hash anchored, so any image can be checked against the data that produced it.

**What has to be true first.** E1 complete and published; a palette chosen and written down once; the outcome classes frozen (they are, in the E1 protocol §6); a decision on fossils and fees (roadmap Part IX / Era 9).

**Open.** Whether the map should colour by outcome class only, or also by how far the child's life differs from the parent's. Whether position 0 should be drawn at the left or the top. Whether a map of a *lineage* (many generations) has a natural form.

## Random walks on the living (2026-10-08)

From the few genesis programs that execute more than one byte, take long random one-byte walks, keeping only steps that stay alive. How far can a program wander without dying? Are the living programs connected to one another or isolated islands? This is the single most important fact for whether evolution can move on this machine, and it is cheap to measure. A candidate for the second pre-registered experiment. Parents must be chosen by a stated rule written before looking at E1's results (for example, every genesis genome whose probe-A lifespan is at least three).

## Two-parent children (2026-10-08)

Recombination between two genesis programs, the catalogue's first children with two owned ancestors. Waits for the fixed-length rule to expire or for a crossover that preserves length.
