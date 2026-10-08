# SLOPWARE

*software nobody wrote*

Software is written: someone decides what it should do and writes it, and it does that, more or less. Slopware is installed before it exists. You press install. In the next block, Ethereum fixes sixty-four bytes nobody chose, and those bytes become the whole of a program at an address of its own. Nothing reads them first. Nothing repairs them. Nothing tries again.

```
randomness → bytecode → EVM → ?
```

SLOPWARE began with random programs and asked what happens when the programmer leaves.

Every section below is marked **CURRENT** (built, deployed, verified) or **PROPOSED** (design only, in [`slopware/ROADMAP.md`](slopware/ROADMAP.md)). Nothing proposed is built.

---

## What SLOPWARE is today — CURRENT

**The installer.** One immutable ERC-721 on Ethereum mainnet, `0x44a64905069963b8321ee2b755a0b8b56d69cbc6`, source verified on Sourcify. `install()` takes the price and numbers a release; no bytecode exists yet. The hash of the *next* block, mixed with the release number, becomes sixty-four bytes. Anyone may then `complete` the release: the contract places those bytes, unchanged, as the entire runtime code of a new contract, or records that Ethereum refused them (first byte `0xEF`). The collector cannot see, choose, preview or retry. The artist's only power is `setPrice`. Details: [`slopware/README.md`](slopware/README.md), [`RANDOMNESS.md`](slopware/RANDOMNESS.md), [`SECURITY.md`](slopware/SECURITY.md).

**The invariant,** tested and verified on mainnet for every installed release:

```
eth_getCode(program) == bytecode        // sixty-four bytes, nothing before, nothing after
```

**The receipt.** Token id = release number, minted to the installer before the bytes exist. On-chain metadata states facts only; the behaviour attribute is the constant `UNKNOWN`. The NFT is not the machine. The program has no owner, no interface, no name.

**The keeper.** A scheduled function that completes installations for collectors who walk away. It cannot influence any outcome. About 60% of collectors complete their own.

**The site.** [slopware.fun](https://slopware.fun): the catalogue states facts and says `unknown`. [slopware.fun/readings](https://slopware.fun/readings): the lab's observations of each installed program, placed on a private chain and probed; explicitly observation, not record. Three layers around the same bytes: the catalogue states facts, the lab records what executed, the readings interpret.

**The lab** (`src/`, `scripts/`): places random bytes on a private chain behind the same loader, verifies the code, calls each program five ways under a 1,000,000-gas ceiling with every opcode traced, and records everything. Seeded runs reproduce to the byte. Local only.

## What has actually been observed — CURRENT

**Before launch, 1,000,000 programs of sixty-four random bytes** ([`BASELINE.md`](BASELINE.md) for the 40,000-program baselines at four lengths; the million is summarised on the site):

| | |
|---|---|
| refused by Ethereum (first byte 0xEF) | 4,064 |
| halted on their first instruction | 78.4% |
| longest life | 12 instructions |
| answered differently to what they were sent | 107 |
| wrote storage that survived | 5 |
| executed CREATE or CREATE2 | 17; no child program resulted |
| returned data | 25 |
| ran out of gas | 251, every one by memory appetite, never by looping |
| called another contract | 0 |

Lifespan is geometric: about one in five survives each instruction. Of 256 byte values, 55 are instructions that need no operands.

**On mainnet, at the time of writing:** 802 releases, 800 installed, 2 refused, 92 collectors. 80% died on their first instruction; three halt cleanly; the longest life is six instructions; none answers to input. The population tracks the million-program distribution. Nothing has ever been abandoned.

**What was deliberately not built:** evolution, mutation, breeding, reproduction, behaviour on the site, other lengths, weighting, repair, filtering, retries, chosen bytes, rarity, royalties, tokens. [`FUTURE.md`](slopware/FUTURE.md) is the record of refusals, and the reason the baseline is clean.

## This repository

| | |
|---|---|
| [`slopware/`](slopware/README.md) | the work: contract, tests, keeper, site, deploy page, documents |
| `src/`, `scripts/` | the lab |
| [`BASELINE.md`](BASELINE.md) | what the lab found before launch, reproducible from seeds |
| [`slopware/ROADMAP.md`](slopware/ROADMAP.md) | the proposed experiment: constitution, ontology, economics, eras, scorecards, open questions |

Local run: `./slopware/sim.sh` for the whole system on a private chain; `cd slopware/contracts && forge test` for the suite; `npm run explore -- --count 100 --bytes 64` for the lab.

---

## The question after this one — PROPOSED

The original question was: what happens if arbitrary bytes are treated as EVM programs? The 802 releases and the million-program study answer it for Era 0.

The larger question is: **what happens when arbitrary computation is given heredity, variation, an environment, selection, resources, interaction and time?** Not whether SLOPWARE is alive. Whether an open-ended, rigorously controlled experiment that begins from code nobody wrote can ever move any criterion of artificial life from *not observed* to *replicated*, without a programmer inserting the thing being looked for. Failure is a valid result and will be published as one.

The framework is the artificial-life analysis of computer viruses, whose central weakness was that every life-like capability of a virus was designed by its programmer. SLOPWARE starts from the other end.

### Constitution — PROPOSED

**We may design the universe. We must not design the organism.**

1. Original machines are immutable.
2. Humans design environments and experiments, never organisms.
3. Random mutation is permitted and is not evolution.
4. Desired function is never inserted. If it appears, it emerged.
5. Every selection pressure is disclosed, including implicit ones.
6. Lineages are auditable and mutation events reproducible.
7. Failure is preserved.
8. Observations require replication before any status changes.
9. SLOPWARE never declares itself alive.
10. Metaphor is labelled and kept out of datasets.
11. BIRTH never closes: anyone, at any time, may introduce unrelated random bytes into whatever world exists.
12. A fee is taken only at abiogenesis. Everything after birth belongs to the experiment.

### Ontology — PROPOSED

**Genotype** (the inherited bytes; identity `keccak256(bytes)`, already the on-chain checksum) · **instance** (one deployment) · **phenotype** (behaviour in a defined environment) · **lineage** (the recorded graph of mutation and reproduction events) · **environment** (a fully specified world; today, *world v0*: the lab's five probes) · **release** and **receipt** (the installer's record and its NFT, which refer to releases only) · **contract** (the permanent Ethereum instance) · **wild organism** (exists only in experimental worlds; no receipt, no owner) · **fossil** (a wild genotype preserved on Ethereum).

### Economics — PROPOSED, and consistent with CURRENT

SLOPWARE charges for creation. Evolution is free. The only payment is `install`; the artist's income rises only when new humans introduce new random material, so the artist has no stake in which lineages thrive. No reproduction fees, subscriptions, rarity, pay-to-win, or royalties on evolutionary activity. Whether preserving a wild specimen on Ethereum may ever carry a fee is unresolved and analysed in the roadmap.

### Criteria — PROPOSED

Each criterion carries a status, **NOT OBSERVED · CANDIDATE · REPLICATED · STRONG · DISPUTED**, that changes only with linked evidence: pattern in space-time, self-reproduction (R0–R5, with the line between infrastructure copying and an organism constructing its descendant drawn in words), self-representation (S0–S4), metabolism (M0–M5, where gas paid by a caller is M0), functional environmental interaction (E0–E5), interdependence, stability under perturbation, evolution, growth. Today every criterion is NOT OBSERVED except trivial pattern-in-space-time and candidate sensing (E1) in the million-program study. There is no percentage.

### Roadmap — PROPOSED

The brief's eras, in order: abiogenesis (current) · descent · swarm · selection · ecology · anatomy · metabolism · self-representation · reproduction · wild · autonomy. The roadmap argues the order should change: ablation and the lineage record come first; worlds must be defined before selection; swarm is capacity, not an era; self-representation and reproduction are detectors that run from the start; wild-versus-collected is a decision needed before the first descendant exists. The minimum next release is **neighbourhoods**: every single-byte mutant of every genesis genome, placed and probed on the lab chain, recorded in a reproducible lineage record, published in the readings' voice with the record's numbers beneath, and nothing changed on mainnet.

### Safety — binding

Organisms live in private EVMs with no host, filesystem or network access. Nothing self-propagating is ever released onto public infrastructure as a consequence of an experiment. The installer remains the only mainnet write path of the work, and it installs only what the chain chose.

### Unresolved

Vocabulary in public; fixed or variable genotype length; refused genomes in the population; collector-initiated descent; fossilisation and fees; where the record's root hashes live; first selection regimes; the `STOP` attractor; what "the same world" means across versions; price under future gas rules; whether a swarm is ever justified; a stopping rule. All in [`ROADMAP.md`](slopware/ROADMAP.md), Part XVI.

---

## Principle

Simple over clever. Preserve the bytecode over convenience. Never improve a random program. The artwork is not that slopware is good software. The artwork is that nobody knows what it is.
