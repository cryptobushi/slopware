# SLOPWARE — the experiment after the programmer leaves

*A design document. Nothing in it is built. It describes what exists today, exactly, and then designs what might come next in a way that could honestly fail.*

Status of every section is marked **CURRENT** (exists, verified against the repository and the chain) or **PROPOSED** (design only).

---

## Part I — What exists today (CURRENT)

### I.1 The installer, exactly

One immutable contract on Ethereum mainnet, `0x44a64905069963b8321ee2b755a0b8b56d69cbc6`, deployed 2026-10-06 from the artist's wallet. Solady ERC-721, about 350 lines, no proxy, no owner function except `setPrice`. Source verified on Sourcify (exact match).

**Installing.** `install()` or `installMany(count ≤ 100)`, paying exactly `price × count`. For each release the contract: increments `releases`; records `{installer, requestedAt = block.number, status = Installing, paid}`; mints token `release` to the installer with `_mint` (no receiver callback); emits `Installing`. **No bytecode exists at this point.** The collector has committed to a program that has not been decided.

**Deciding.** The bytecode of release *n* is fixed the moment block *R+1* is mined, where *R* is the request block:

```
bytecode = keccak256(blockhash(R+1), n, 0) ‖ keccak256(blockhash(R+1), n, 1)     // 64 bytes
```

Nobody chooses it: not the collector (who committed before the block existed), not the artist (who has no input), not the keeper. The block's proposer could in principle grind the hash; this is disclosed in `RANDOMNESS.md` and accepted at this price.

**Completing.** `complete(n)` or `completeMany([...])`, callable by anyone from block *R+2*. The contract computes the bytecode, checks the one rule Ethereum imposes (a program may not begin with `0xEF`, EIP-3541), and:

- if refused: records `Rejected`, stores the 64 bytes inside the installer (there is no program to hold them), emits `Rejected(…, "EIP-3541")`. The collector keeps the token.
- otherwise: `CREATE` with an 11-byte loader (`PUSH1 0x40 · DUP1 · PUSH1 0x0b · PUSH1 0 · CODECOPY · PUSH1 0 · RETURN`) followed by the bytecode, so that the new contract's runtime code **is** the 64 bytes, nothing before, nothing after. Verifies `extcodehash == keccak(bytecode)`. Records `Installed`, `program`, `installedAt`, `checksum`. Emits `Installed(…, bytecode)`.
- if the blockhash has expired (256 blocks, about 51 minutes, with nobody completing): records `Abandoned`, credits a refund. **Nothing is ever substituted.**

**The invariant,** tested in Foundry and verified on mainnet for every installed release: `eth_getCode(program) == bytecode`.

**The installer never calls a program.** Not during installation, not in `tokenURI`, never. Programs are untrusted by design.

**What the artist can do:** `setPrice`. That is the whole list. Every change emits `PriceSet`. The price was 0.0004 ETH at launch and was raised to 0.001 ETH at block 26148735.

**What anyone can do:** `complete`, `completeMany`, `withdraw` (pays the artist only), `claimRefund` (pays the installer of an abandoned release).

### I.2 Ownership and the NFT

Token id = release number. Minted to the installer at request time, before the bytecode exists. Transferable; standard ERC-721. `tokenURI` is fully on-chain: base64 JSON with a base64 SVG card showing release number, status, program address, the 64 bytes, and the installer. Attributes are facts only; the one behavioural attribute reads `"Observed behavior": "UNKNOWN"` and is a constant.

The program itself has no owner, no interface, no name, no reference to the token. The token records who installed it and who holds it. **The NFT is not the machine; it is the receipt.** Rejected releases also receive a token.

### I.3 The keeper

A scheduled function on Vercel, every minute, from wallet `0xB847…913f`. It reads the installer, finds releases past their deciding block, and calls `complete`/`completeMany`. It has no power over outcomes. It defers when base fee exceeds 3 gwei unless a release is within 20 blocks of expiry, in which case it completes at any price. About 60% of collectors complete their own installs from the page before the keeper gets there.

### I.4 The site

`slopware.fun`, one static document in Courier, black on white. The catalogue states facts: installer, releases, installed, refused, a registry of releases with program addresses, and a record page per release that says `status unknown` for installed programs. The lab section reports the million-program study. A separate page, `slopware.fun/readings`, is the lab's interpretive observation of each installed program, placed on a private chain and probed; it is explicitly "observation, not record." Reads go through a cached API; installs go straight to the chain.

**Three epistemic layers around the same 64 bytes:** the catalogue states facts (`unknown`); the lab records what executed (`SSTORE then halted`); the readings interpret (`remembered something for an instant`).

### I.5 The lab

A local instrument (`src/`): generate uniform random bytes, place them on a private Anvil chain behind the same loader, verify the code byte for byte, call each program five ways under a 1,000,000-gas ceiling with every opcode traced, classify, record. Seeded runs are reproducible to the byte (`keccak256(seed ‖ counter)`). It refuses any RPC that is not localhost and chain 31337, and holds only Anvil's published test keys.

### I.6 What has actually been observed

**Before the installer existed: 1,000,000 programs of 64 random bytes** (run `deep-1m-64b`), plus baselines at 16/32/64/128 bytes (seeds `slopware-baseline-<L>`, 10,000 each) and a 100,000-program study.

| the million-program study | |
|---|---|
| refused by Ethereum (first byte 0xEF) | 4,064 (0.41%, predicted 1/256) |
| installed | 995,936 |
| halted on their first instruction | 78.4% |
| longest life | 12 instructions |
| halted cleanly, any probe | 37,574 of 4,979,680 calls (0.75%) |
| answered differently to calldata or value | 107 |
| wrote persistent storage and then halted cleanly | 5 |
| executed CREATE or CREATE2 | 17 — none produced a child: the creation itself failed, or the parent's exceptional halt undid it |
| returned data | 25 |
| ran out of gas | 251 — every one by a single instruction's memory appetite; **no loops in a million** |
| executed an external call | 0 |

Lifespan is geometric and independent of length: about one program in five survives each instruction. Of 256 byte values, 55 are instructions needing no operands; a random first byte is one with probability 0.215. Everything follows from that.

**On mainnet, at the time of writing: 802 releases, 800 installed, 2 refused, 92 collectors.** 80% died on their first instruction; three halt cleanly (two begin with `STOP`; one walks off the end of its code after a `TIMESTAMP`); longest life six instructions; none answers to input; one executed `SSTORE` (then died, undoing it); one died of memory appetite. The population is tracking the million-program distribution.

### I.7 What was deliberately not built

`FUTURE.md` records the exclusions: evolution, mutation, breeding, reproduction; behaviour on the site; other lengths; weighting, repair, filtering, retries; collector-chosen bytes or salts; rarity, traits, scores; royalties; VRF; tokens, DAO, treasury; AI generation; calling programs from the site. These were refusals of design, and they are the reason the baseline is clean.

---

## Part II — Where the description and the implementation differ

The brief for this roadmap describes the present system in a few ways that are not how it works. These matter because the roadmap's integrity depends on the baseline being described exactly.

1. **Nothing is tested or selected before installation.** The brief says random bytes are "tested against the EVM… some execute… a subset are installed." On mainnet, every release is installed unfiltered, and nobody, including the contract, has run the program before or after installation. The testing happened in the lab, on different random bytes, before launch, to learn the distribution. The installed population is an unselected sample.

2. **Collectors install nothing "selected."** The brief says "humans install selected/random specimens." A collector cannot see, choose, preview, or retry the bytes. They commit to a release number; a future block decides the rest.

3. **The bytes do not come from the lab's generator.** On mainnet they come from `keccak256(blockhash, release, i)`. The lab's seeded generator is a different source with the same distribution (uniform bytes). The statistics transfer; the bytes do not.

4. **The word is "install," not "birth."** The contract, events, site and documents use install / release / installer / program / refused / abandoned. "Birth" and organism vocabulary were considered and rejected during the design for the catalogue. The roadmap below uses *abiogenesis* and *birth* as conceptual terms for the same act, but the on-chain and catalogue vocabulary stays. Whether the roadmap's public face adopts biological language is an open decision (see Part X).

5. **The current contract cannot host heredity.** It is immutable, has no notion of parent or child, and installs only bytes the chain chose. Any heredity, mutation, or fossilisation must live in new infrastructure beside it, never in it. The 802 releases are evidence; the installer is a sealed instrument.

6. **The 17 "reproductions" in the million-program study never produced a child.** The brief cites "CREATE/CREATE2 execution." Correct, with the qualifier: in every case either the creation itself failed (value larger than any balance) or the parent's halt undid it. No child program ever existed. The catalogue's wording, "executed CREATE or CREATE2; no child program resulted," is the observation; "attempted reproduction" is a reading.

7. **"Hundreds" is now 800 and rising**, with 92 collectors, two refusals, and a price that has already changed once.

8. **Receipts for refused releases exist.** A rejected release has a token and the 64 bytes are kept, but no program. The brief's "deployed contract is the machine" holds for installed releases only; refused releases are machines Ethereum would not let exist, and the roadmap must decide whether they are in the population (see Part X).

9. **The keeper is not part of the organism's world.** It completes installations and nothing else. It is infrastructure, and it cannot affect any outcome.

---

## Part III — Constitution (PROPOSED, to be ratified by the artist)

1. **Original machines are immutable.** Every installer release remains exactly what the chain produced. Nothing is retrofitted into them.
2. **Humans may design environments, not organisms.** We may provide execution, state, resources, other organisms, mutation mechanisms, environmental variation, execution opportunities, and constraints. We may not insert desired function into any genome.
3. **Humans may define experiments** and must publish them before running them.
4. **Random mutation is permitted** and is not evolution.
5. **Desired function is never inserted.** No `reproduce()`, no self-inspection stub, no resource routine. If these appear, they emerge.
6. **Every selection pressure is disclosed**, including the implicit ones: gas ceilings, probe design, environment choice, which runs get published, which specimens get fossilised.
7. **Lineages are auditable.** Every descendant traces to a genesis genome through recorded, reproducible mutation events.
8. **Failure is preserved.** Dead ends, extinctions, and null results are published with the same care as findings.
9. **Observations require replication** under controlled conditions before they change a scorecard status, and independent replication before they are called strong.
10. **SLOPWARE never declares itself alive.** It reports observations. Humans argue about meaning.
11. **Metaphor is labelled.** The readings may say "remembered"; the record says `SSTORE persisted`. The two are never confused in a dataset.
12. **BIRTH never closes.** Any person, at any time, may introduce unrelated random bytes into whatever world exists.
13. **The installer is the only place a fee is taken.** Everything after abiogenesis is free apart from unavoidable network and computation cost.

The constitution is amendable only by the artist, in public, with the amendment recorded in this document's history. Experiments begun under an earlier version cite the version they ran under.

---

## Part IV — Ontology (PROPOSED)

| term | definition | today's instance |
|---|---|---|
| **genotype** | the inherited computational information: a byte string that is, or becomes, EVM runtime code | 64 bytes; identity `keccak256(bytes)`, which is exactly the on-chain `checksum` |
| **instance** | one deployment of a genotype in some world | an installed program at an address on mainnet; or a placement on a lab chain |
| **phenotype** | what an instance does when executed in a defined environment | the five probes' outcomes, traces, state effects |
| **environment** | a fully specified world: chain rules, gas ceiling, calldata, value, state, neighbours, execution opportunities | *world v0*: Osaka rules, fresh state, 1,000,000 gas, probes A–E |
| **lineage** | the directed acyclic graph of genotypes connected by recorded mutation or reproduction events | none yet; every genotype is generation 0 |
| **release** | an entry in the installer's numbered record | releases 1..N |
| **NFT / receipt** | ownership and provenance of a *release* | token id = release number |
| **contract** | the permanent Ethereum instance of a genotype | `program` of an installed release |
| **wild organism** | a genotype and its instances that exist only in experimental worlds, with no release, no receipt, no owner | none yet |
| **fossil** | a wild genotype permanently instantiated on Ethereum for preservation | none yet |

Rules: a genotype may have many instances. An instance has exactly one genotype. A release has exactly one genotype (even when refused: the bytes are kept). A receipt refers to a release, never to a genotype or a lineage. The same genotype could in principle be born twice; the lineage record treats these as two genesis events of one genotype.

---

## Part V — Economics (PROPOSED, and consistent with CURRENT)

**SLOPWARE charges at abiogenesis. Everything after birth belongs to the experiment.**

Today this is literally true: the only payment in the system is `install`, and the only mutable parameter is its price. The roadmap keeps it true:

- No reproduction fees, subscriptions, rarity tiers, legendary genomes, pay-to-win evolution, or royalties on evolutionary activity.
- The artist's income rises only when new humans introduce new random material. The artist therefore has no financial stake in which lineages thrive, which is the condition under which a disclosed experiment can be believed.
- The keeper's gas is a cost of abiogenesis, paid from the fee. During the first two days it ran at about 12% of sales.

**Unresolved: fossilisation.** Installing a wild genotype on Ethereum is not abiogenesis; the genotype already exists. Charging a SLOPWARE fee for it would violate the principle. Not charging means anyone can fossilise anything for gas alone, which is honest but means fossil receipts might have no value the market recognises, or might compete with births. Three positions are analysed in Era 9; none is adopted here.

**Unresolved: price under future gas rules.** When mainnet adopts the Amsterdam repricing (already live on Sepolia), an install costs about 590k gas and a completion about as much; the keeper subsidy per walk-away release rises roughly fourfold. `setPrice` is the only lever and it is public.

---

## Part VI — The eras (PROPOSED)

A note on names: "era" implies sequence, but several of these are measurement programmes that run alongside others. Part VIII argues for a different ordering. The eras are kept here in the order given so the argument can be followed.

Common to every era:

- **BIRTH continues unchanged.** The installer, its price, and its receipts are the same object throughout. New releases are generation 0 with no parent.
- **Genesis vs later generation 0.** Releases requested before the first heredity experiment's first mutation event (a block number, recorded once, in this document) are the *genesis population*. Later births are *generation 0, era k*. Both have no parent; neither is biologically privileged; they differ only in provenance, and the record says which is which.
- **Nothing is built into the installer.** Ever.
- **Every experiment is sandboxed**: a private EVM, no network access, no host access, no persistence outside the record. Mainnet is touched only by `install` (anyone) and, if Era 9 adopts it, a separate fossil contract.

### ERA 0 — ABIOGENESIS (CURRENT)

**Purpose.** Establish what arbitrary EVM bytecode does before heredity, variation, or selection, and begin an unselected population on a public chain.

**Scientific question.** What behaviour occurs naturally in arbitrary EVM bytecode?

**Participant experience.** Press install, pay, sign once, walk away. A program exists within two blocks.

**Collector experience.** A receipt per release; a record page that says unknown; a readings page that interprets.

**Organism experience.** Placed once. Never called by the installer. Called by anyone who chooses to, at their own expense and risk.

**System behaviour.** Described in Part I.

**Technical requirements.** Met.

**Data recorded.** On-chain: installer, request block, completion block, status, program address, checksum, the bytes (in the `Installed`/`Rejected` event). Lab: `readings.json` per release (disassembly, five probes with traces, traits), reproducible from the bytes.

**Experimental controls.** The million-program study is the control population for mainnet: same distribution, no selection, five probes, one gas ceiling.

**Failure modes.** Proposer grinding (disclosed); abandonment (never occurred); keeper economics under high gas (observed, managed by price).

**Success criteria.** Met: the mainnet population's statistics match the study within sampling error; the invariant holds for every installed release; nothing was abandoned.

**Must not be implemented.** Anything in `FUTURE.md`. Any behavioural data in the catalogue or the token.

**How births interact with the population.** They are the population.

**Observations that justify advancing.** None needed from the organisms. Advancing is a decision to start a new experiment beside this one, not a graduation.

### ERA 1 — DESCENT (assisted heredity)

**Purpose.** Give arbitrary computation ancestry for the first time, with the infrastructure openly doing the copying.

**Scientific question.** What happens when arbitrary computational structures acquire heredity and variation? More precisely: what is the shape of the mutational neighbourhood of random programs? How often does a one-byte change kill, spare, or alter a phenotype?

**What changes.** A lineage record exists. Descendant genotypes exist, off-chain, in the lab. Nothing on mainnet changes.

**Participant experience.** The readings page gains a *descent* view: for a release, its descendants' lives. Anyone may run the open-source mutation and probing tools on any public genome; results submitted with a seed are reproducible by anyone else.

**Collector experience.** Unchanged ownership. A collector sees that their release has descendants in the record. They do not own them (Part IX). They are not asked to pay. Whether a collector may *request* descent of their release before the systematic run reaches it is an open question; the default is that descent is systematic and the same for every genesis genome.

**Organism experience.** Copied with one or more byte changes; each copy placed on a private chain and probed under world v0.

**System behaviour.** A mutation engine with a small, enumerated set of operators (substitution, insertion, deletion, duplication, recombination of two genomes), each deterministic given `(operator, parent id(s), seed)`. A lineage record: append-only, content-addressed, versioned. A probing run per descendant identical to the lab's. No on-chain action.

**Mild technical requirements.** A `mutate` module beside `src/`; an event schema; a `lineage.jsonl`; a descendant id scheme (Part X); readings extended to render lineage; the generator kept deterministic so any event is replayable from its record.

**Data model.** `MutationEvent { id, experimentVersion, operator, parents[], seed, position(s), childGenotype, childId, createdAt, environmentId }`, `Phenotype { genotypeId, environmentId, probes[], traits, harnessVersion }`, `Genotype { id = keccak(bytes), bytes, length, firstSeen: {kind: birth|mutation|recombination, ref} }`.

**Experimental controls.** Each genesis genome's neighbourhood is compared with the neighbourhood of a fresh random genome of the same length, so "heredity" can be distinguished from "another random draw." Unmutated re-placements establish measurement noise (address-dependent programs will differ).

**Success criteria.** Every genesis genome has a recorded, reproducible neighbourhood. The neutral/lethal/altering fractions are measured with confidence intervals. The record replays bit-for-bit.

**Failure conditions.** Mutation events not reproducible; descendants indistinguishable from random (which would itself be a finding, reported); lineage ids colliding.

**Contamination risks.** Choosing which genomes to mutate by interest. Choosing operators that favour viability. Reporting only the lively neighbourhoods. Letting readings' metaphors leak into the record.

**Safety.** Private chain only; no descendant is deployed to any public chain in this era.

**Economic effect.** None. No fee, no token.

**Website changes.** A descent view per release on the readings page; a lineage count in the readings summary; a plain statement that descendants are assisted copies made by infrastructure, not reproduction.

**Unresolved.** Byte-length changes (insertion/deletion) break the "64 bytes" identity of the work; is length a free variable for descendants? Do refused genomes get descendants? Does recombination belong in Era 1 or Era 3?

**Requirements to advance.** A complete, replayed, published neighbourhood map, and a decision on which selection pressures Era 3 will apply, written before Era 3 begins.

### ERA 2 — SWARM (distributed computation)

**Purpose.** Scale evaluation beyond one machine when, and only when, the experiments require it.

**Scientific question.** None of its own. It is infrastructure. The honest question is "which experiments are compute-bound?" The lab evaluates about 400 specimens a second on a laptop: a million in seventy minutes. Era 1 is not compute-bound. Era 3 populations of 10⁴ over 10³ generations are 10⁷ evaluations: hours, not days. A swarm is justified at 10⁹ evaluations or when many environments must run concurrently.

**Participant experience.** `npx slopware` runs a node: it fetches a signed job (genotypes, environment, seeds), runs them in an embedded EVM with no network or filesystem access beyond the job, returns observations, and exits. Nodes are credited in the record by public key. No payment.

**Collector experience.** None specific.

**Organism experience.** Executed on strangers' hardware inside the same sandbox.

**System behaviour.** A coordinator issues jobs; results from untrusted nodes are *candidate* observations until replicated by at least two unrelated nodes or by the lab. Disagreement is recorded, not resolved by vote.

**Technical requirements.** A deterministic EVM in process (not a spawned Anvil), job signing, result signing, replication scheduling, a node that cannot be made to run anything but EVM bytecode in a sandbox.

**Data model.** `Job`, `Result { nodeKey, jobId, observations, signature }`, `Replication { resultIds[], agreement }`.

**Controls.** Every job includes known-answer genomes; nodes failing them are excluded. All results carry node identity so bias per node can be measured.

**Success.** Replicated results match lab results; throughput exceeds the lab's by an order of magnitude.

**Failure.** Node fraud; non-determinism across EVM implementations; the experiment not needing the capacity.

**Contamination.** Treating unreplicated swarm results as evidence. Any gamification of node contribution that becomes a selection pressure on which jobs get run.

**Safety.** The node runs EVM bytecode only, in an interpreter, with no native execution, no persistence, no network beyond the coordinator. No organism can touch the host. Honest statement to participants about what runs.

**Economics.** None. No token for compute.

**Website.** A swarm panel: nodes, jobs, replication rate.

**Unresolved.** Whether to build this at all before Era 3 shows a need.

**Advance when.** Not a gate. Build when a measured experiment is compute-bound.

### ERA 3 — SELECTION

**Purpose.** Introduce differential reproductive success without steering it toward any particular outcome.

**Scientific question.** Can persistent functional change emerge through selection rather than programmer design?

**What changes.** Populations, not chains. Generations. Reproduction of genotypes into the next generation is decided by a disclosed rule applied to phenotypes in a disclosed environment.

**Participant experience.** Watch populations run: generation counts, lineage births and extinctions, phenotype distributions over time, with the selection rule printed above the chart.

**Collector experience.** Genesis genomes seed the first populations. A collector may see "release 166 has 4,000 living descendants in world A and is extinct in world B."

**Organism experience.** Executed each generation; copied with variation in proportion to a rule it cannot see.

**System behaviour.** Candidate selection regimes, each run as a separate, labelled experiment:

- **drift**: uniform reproduction. The null model. Required.
- **persistence**: reproduction weighted by instructions executed before halting. Disclosed as "we select for living longer."
- **novelty**: reproduction weighted by distance of phenotype from the archive of previously seen phenotypes. Disclosed as "we select for being unlike what we have seen."
- **environmental**: reproduction only if the instance halts cleanly in the environment (nothing else rewarded). Disclosed as "the environment kills exceptional halts."
- **reproductive**: reproduction weighted by whether the instance's own execution created a child contract containing inherited bytes. Only legitimate once Era 7/8 observations exist; before that it is "fitness += reproduces," which the constitution forbids as a first move.

**Technical requirements.** Population runner; generation scheduler; phenotype archive for novelty; per-generation snapshots; the mutation engine from Era 1.

**Data model.** `Population { id, worldId, regime, seedGenotypes[], generation, size }`, `Generation { populationId, n, members[], offspring events }`, `Extinction { lineageRoot, generation }`.

**Controls.** Drift runs beside every regime. Identical seeds across regimes. Repeat runs with different RNG seeds. Report effect sizes with intervals.

**Success.** A regime produces a measurable, replicated shift in phenotype distribution across generations that drift does not, and the shift is explained by heritable changes in genotypes.

**Failure.** No regime moves the population beyond drift; or populations collapse to trivial phenotypes (e.g. everything becomes `STOP`); both are results.

**Contamination.** Tuning regimes after seeing results. Rewarding what we hope to find. Letting novelty archives be curated by hand.

**Safety.** Private chains.

**Economics.** None.

**Website.** Population dashboards with the regime stated; a generation counter; an extinctions list.

**Unresolved.** Population size; mutation rate; whether recombination is allowed; how to prevent the `STOP` attractor without designing against it.

**Advance when.** At least one non-drift regime shows replicated heritable change; the environment vocabulary of Era 4 is specified.

### ERA 4 — ECOLOGY

**Purpose.** Let instances encounter defined environments and each other.

**Scientific question.** Do ecological relationships emerge when evolved computational organisms share environments?

**What changes.** The environment is a first-class, versioned object. Worlds differ in state, calldata, value, gas, neighbours, and the order and frequency of execution opportunities. Instances can read each other (`EXTCODESIZE`, `BALANCE`, `CALL`) if their bytes happen to do so.

**Participant experience.** Multiple worlds side by side; divergence charts; transplant experiments.

**Collector experience.** As Era 3, per world.

**Organism experience.** Placed alongside others; called with world-specific inputs; may be called by neighbours.

**System behaviour.** World definitions; population seeding; execution scheduling that gives every instance opportunities; a transplant operation moving a population between worlds; perturbation operations.

**Technical requirements.** A world schema; an execution scheduler; state snapshots.

**Data model.** `World { id, version, rules, initialState, inputDistribution, gas, scheduler }`, `Interaction { caller, callee, outcome }`, `Transplant`, `Perturbation`.

**Controls.** Identical populations in different worlds; the same world with shuffled neighbours; worlds with no neighbours.

**Success.** Replicated divergence attributable to environment; any replicated instance of one lineage's presence changing another's persistence.

**Failure.** No sensing (E1) ever appears; interactions are all accidental and non-heritable.

**Contamination.** Designing worlds that reward specific opcodes. Writing neighbour "prey" contracts that are not organisms.

**Safety.** Private chains. Neighbours are organisms or inert fixtures, never contracts with privileged abilities.

**Economics.** None.

**Website.** World list; divergence view.

**Unresolved.** What counts as "the same" world across versions; whether mainnet state (real contracts) can ever be a world (see safety: no).

**Advance when.** E2 or E3 replicated.

### ERA 5 — ANATOMY (robustness and interdependence)

**Purpose.** Map which parts of a genotype matter, and whether that map changes under evolution.

**Scientific question.** Does evolution produce increasingly interdependent computational anatomy? Can robustness emerge without being programmed?

**Note on ordering.** Ablation is a measurement, not a stage; it should begin in Era 1 on the genesis population so that later eras have a baseline (Part VIII).

**Participant experience.** For any genome, an anatomy view: each byte coloured by what happens when it is removed or replaced (nothing, death, change), with the same view for a matched random genome beside it.

**Collector experience.** Their release's anatomy is public like everything else about it. No ownership change.

**Organism experience.** Copied thousands of times with one region altered each time; each copy probed; none deployed anywhere public.

**System behaviour.** Systematic ablation: every byte substituted (with every value or a sample), every byte deleted, every window of 2–8 bytes removed or duplicated; phenotype distance per ablation under world v0 and, later, under evolved worlds. Environmental perturbation trials: gas ceiling halved and doubled, state pre-seeded, inputs varied, neighbours shuffled, noise injected into calldata. Persistence of phenotype measured per trial.

**Mild technical requirements.** An ablation enumerator; a phenotype distance function published and versioned (trace edit distance plus outcome class plus state-effect set); batch probing; a per-genome anatomy summary.

**Data model.** `Ablation { genotypeId, operation, position(s), resultGenotypeId, environmentId, phenotypeDistance, harnessVersion }`, `PerturbationTrial { genotypeId, worldId, perturbation, persisted: bool, distance }`, `AnatomySummary { genotypeId, neutralFraction, lethalFraction, plasticFraction, interactionMatrixRef }`.

**Experimental controls.** Random genomes of the same length under the identical protocol; re-placement without ablation to measure noise; evolved genomes compared with their own genesis ancestors.

**Success criteria.** A replicated difference in ablation sensitivity or perturbation persistence between evolved and random populations, in either direction, with intervals.

**Failure conditions.** No detectable difference; or evolved genomes more fragile. Both reported.

**Contamination risks.** Choosing which genomes to ablate by interest; defining "function" after seeing results; a distance function tuned to make evolved genomes look structured.

**Safety.** Private chains only.

**Economic effect.** None.

**Website changes.** Anatomy view per genome on the readings page; robustness distributions on the scorecard page.

**Unresolved.** The distance function; whether neutrality in world v0 means anything about neutrality in other worlds.

**Requirements to advance.** Not a gate: anatomy runs continuously from Era 1 and feeds the robustness criterion.

### ERA 6 — METABOLISM (resource ecology)

**Purpose.** Introduce scarce, real resources into worlds and see whether heritable resource use appears.

**Scientific question.** Can evolved computational structures develop heritable mechanisms for acquiring and using scarce environmental resources?

**What counts as a resource.** Only quantities the EVM itself scarcifies: gas, ETH balance, storage slots, execution opportunities. No invented food points. Gas paid by the environment to execute an instance is M0; it becomes metabolism only when the instance's own action changes what resources it or its descendants can later use.

**Participant experience.** Resource flows per world: balances held by instances over generations, execution opportunities earned versus granted, storage occupied.

**Collector experience.** As Era 3, per world. No resource is ever owned by a collector.

**Organism experience.** Placed in worlds where executing again depends on holding balance, where fixtures or neighbours can be called for value, where storage is finite and shared.

**System behaviour.** World rules such as: an instance is executed only while its balance exceeds a threshold, and execution deducts it; fixtures that transfer value to callers under published conditions; a storage budget per world. The scheduler enforces rules uniformly; it never pays an instance for a behaviour.

**Mild technical requirements.** World rules expressible as a scheduler policy; balance accounting; fixture contracts that are inert except for published, condition-based transfers; resource-flow logging.

**Data model.** `ResourceFlow { worldId, generation, from, to, kind: gas|value|storage|opportunity, amount, cause: eventRef }`, `MetabolismLevel { lineageRoot, worldId, level: M0..M5, evidence[] }`.

**Experimental controls.** Identical worlds without scarcity; worlds where resources are granted uniformly regardless of behaviour; drift populations in scarce worlds.

**Success criteria.** M3 replicated: an instance's execution acquires a resource that its lineage subsequently depends on, in more than one run and world.

**Failure conditions.** Resources only ever consumed by the environment on the organism's behalf; or acquisition appears but does not persist across generations.

**Contamination risks.** Paying organisms for behaviours we like (Era 3 fitness in disguise); fixtures that are effectively prey written to be eaten; counting a `CALLVALUE` read as acquisition.

**Safety.** Private chains; fixtures hold only test value.

**Economic effect.** None. No real ETH enters any world.

**Website changes.** Resource-flow view per world; the M-scale on the scorecard.

**Unresolved.** Whether gas can be a resource inside a world at all, since the environment always pays it; what a "scarce execution opportunity" is when the scheduler decides who runs.

**Requirements to advance.** M2 replicated before autonomy worlds are attempted.

### ERA 7 — SELF-REPRESENTATION

**Purpose.** Observe whether an organism's own information comes to participate in making descendants.

**Scientific question.** Can arbitrary computation evolve a heritable representation of itself that participates in reproduction?

**Observation, not construction.** This era builds no mechanism. It defines detectors over traces that already exist: self-inspection (`CODESIZE`, `CODECOPY`, `ADDRESS`, `EXTCODEHASH` of self, `EXTCODECOPY` of self) executed (S1); self-copied bytes used as `CREATE`/`CREATE2` input (S2); a resulting child whose code shares inherited bytes with the parent (S3); the child doing the same (S4).

**Participant experience.** The S-scale on the scorecard, each level linking to the traces that justify its status.

**Collector experience.** None specific.

**Organism experience.** Unchanged; only observed.

**System behaviour.** Detectors run over every probe trace in the record, retroactively over Era 0 and 1 data.

**Mild technical requirements.** Trace queries; a byte-overlap measure between parent and child code; detector versioning.

**Data model.** `Detection { genotypeId, eventRef, scale: S, level, evidence: traceRef, detectorVersion }`.

**Experimental controls.** Detectors run over random control populations to measure the base rate of accidental self-inspection (`CODESIZE` appears by chance about 1 in 256 first bytes).

**Success criteria.** S2 replicated under any regime. Status changes only with linked traces.

**Failure conditions.** Never observed; reported as such with the base rates.

**Contamination risks.** Writing S1-triggering opcodes into any genome; counting accidental `CODESIZE` as representation; selecting for S-levels in Era 3 before they have appeared on their own.

**Safety.** None beyond the standing rules.

**Economic effect.** None.

**Website changes.** S-scale with evidence links.

**Unresolved.** How much shared information between parent and child counts as a template rather than coincidence.

**Requirements to advance.** Not a gate; detectors run from Era 1 onward.

### ERA 8 — REPRODUCTION

**Purpose.** Distinguish, permanently and publicly, infrastructure copying from organisms reproducing.

**Scientific question.** Can an evolutionary process beginning with arbitrary EVM bytecode discover a heritable self-reproducing structure without a human designing it?

**The Xerox objection.** In Eras 1–6 every descendant is made by infrastructure reading a parent and writing a child. That is R1. R3 requires that the parent's execution constructs the descendant. R5 requires the descendant to carry the mechanism and vary.

**Participant experience.** The R-scale on the scorecard with the Xerox line drawn in words; a reproduction-events view listing every executed creation with what, if anything, resulted.

**Collector experience.** None specific. An R3 event descending from a collected release is a fact about provenance only.

**Organism experience.** Unchanged; only observed.

**System behaviour.** Detectors: `CREATE`/`CREATE2` executed (17 times in a million so far, never yielding a child); child code non-empty; child code shares inherited information with the parent; child itself executes a creation. In autonomy worlds (Era 10), the scheduler executes the child as a member of the population.

**Mild technical requirements.** Call-tracer capture of child code at creation; inheritance measure shared with Era 7; linkage of child instances to parent events in the lineage record as a new event kind, `intrinsic-reproduction`.

**Data model.** `ReproductionEvent { parentInstance, worldId, generation, childCodeHash, inheritedBytes, level: R0..R5, traceRef }`.

**Experimental controls.** Base rate of `CREATE` execution in random populations; the number of accidental non-empty children expected by chance (near zero, since random init code almost never returns code).

**Success criteria.** R3 replicated in more than one world and run.

**Failure conditions.** Never observed. "This may never happen" is written into the experiment and would be reported as its central negative result.

**Contamination risks.** Any helper contract, fixture, or world rule that constructs children on an instance's behalf and is then counted as R3; selecting for `CREATE` execution in Era 3 before R3 has appeared.

**Safety.** Children exist only in private worlds. No child is ever deployed to a public chain by the experiment.

**Economic effect.** None. No receipts for children.

**Website changes.** R-scale with evidence; the reproduction-events view.

**Unresolved.** Whether an R2 world rule (the environment copies an instance when a published condition holds) is a legitimate stepping stone or a disguised Xerox.

**Requirements to advance.** R3 replicated before any autonomy world is run.

### ERA 9 — WILD (existence, reproduction and ownership separated)

**Purpose.** Let the population be mostly unowned and ephemeral, and define preservation.

**Scientific question.** What happens when existence, reproduction, and ownership become separate concepts?

**Participant experience.** A wild population counter, likely in the millions, beside the collected count in the hundreds or thousands; a fossil register if fossils exist.

**Collector experience.** A collected release is a genesis genotype with a receipt. Wild descendants of it are not theirs. A fossil, if it exists, is a separate release in a separate contract with its own receipt rules.

**Organism experience.** Most organisms exist only in worlds, for generations, and are gone. A few are instantiated permanently on Ethereum.

**System behaviour.** Fossilisation requires a new contract: the installer cannot install chosen bytes without breaking its one invariant. A fossil contract installs a specified genotype with a lineage reference and a different, stated promise: "these bytes were chosen from the record; here is their ancestry."

**Mild technical requirements.** A fossil contract (not designed here); a lineage reference format verifiable against the record's root hashes; a decision process for what is fossilised, published.

**Data model.** `Fossil { genotypeId, lineageRootHash, fossilRelease, contract, program, installedBy, reason }`.

**Experimental controls.** None; this is governance, not experiment. The record must show that fossilisation never feeds back into selection (fossilised lineages receive no extra opportunities in worlds).

**Success criteria.** Wild and collected are distinct in every dataset and on every page; no fossil has influenced a world.

**Failure conditions.** Fossil selection becomes a selection pressure on which lineages the public sees; fossil receipts become a market that distorts what gets studied.

**Contamination risks.** Curation. Fossilising the lively ones.

**Safety.** The fossil contract is audited before deployment; it installs ordinary contracts whose code is known in advance.

**Economic effect.** The central open question. Three positions, none adopted: free apart from gas with a receipt to the payer; free apart from gas with no receipt; a fee justified as a different work. The second is cleanest for the principle and the science and weakest for sustaining the practice.

**Website changes.** Wild population count; fossil register with ancestry.

**Unresolved.** Who decides; fees; whether refused genesis genomes are wild.

**Requirements to advance.** A ratified decision on fees and curation, written before the first fossil.

### ERA 10 — AUTONOMY

**Purpose.** Progressively remove infrastructure from the reproductive loop inside bounded worlds.

**Scientific question.** How much of the lifecycle can move from the programmer and the infrastructure into the organism?

**Participant experience.** Autonomy worlds shown with the infrastructure's remaining role stated explicitly: execution opportunities and resources only; no copying.

**Collector experience.** None specific.

**Organism experience.** Executed when the scheduler gives an opportunity; persists only if its own execution produces descendants.

**System behaviour.** A world whose scheduler executes instances but never copies them. New members enter only through R3 events or through births (continuous abiogenesis into the autonomy world, if that world is chosen to receive them). Populations that stop reproducing go extinct and the extinction is recorded.

**Mild technical requirements.** A scheduler mode with copying disabled; extinction detection; long-run snapshots.

**Data model.** As Eras 3, 4, 8, plus `AutonomyRun { worldId, startGeneration, infrastructureRole: 'execution+resources', copying: false, outcome }`.

**Experimental controls.** The same seed population in a copying world and in an autonomy world; autonomy worlds seeded with random genomes as the null.

**Success criteria.** A population persists for N generations with no infrastructure copying, replicated.

**Failure conditions.** Every autonomy population goes extinct. A strong, publishable negative result.

**Contamination risks.** Any residual copying hidden in world rules; seeding autonomy worlds with hand-picked genomes.

**Safety, absolute.** Autonomy worlds are private EVMs with no connection to public infrastructure. Any proposal to instantiate an autonomous population on a public chain is a separate, audited, explicitly authorised decision, never a consequence of an experiment's success.

**Economic effect.** None.

**Website changes.** Autonomy worlds with the infrastructure's role stated; extinction records.

**Unresolved.** N; whether births should flow into autonomy worlds.

**Requirements to advance.** There is no next era. Beyond this is the question mark.

---

## Part VII — Scorecards (PROPOSED)

### VII.1 Status vocabulary

Every criterion and every level carries one status:

| status | meaning |
|---|---|
| **NOT OBSERVED** | no candidate instance in the record |
| **CANDIDATE** | observed once or in one run; not yet replicated |
| **REPLICATED** | reproduced under controlled conditions by the lab from the record |
| **STRONG** | independently replicated outside the project, with methodology reviewed |
| **DISPUTED** | a replication failed or a confounder is unresolved; the dispute is linked |

A status changes only when evidence changes, and every change is an entry in the experiment log with the evidence linked. Nothing on the public scorecard is edited by hand.

Each criterion publishes: definition; what would count; what would not count; known confounders; methodology; evidence; counterarguments; replication status; raw data.

### VII.2 Artificial-life criteria

| criterion | counts | does not count | today |
|---|---|---|---|
| pattern in space-time | a genotype persisting across instances and time | one deployed contract existing | REPLICATED, trivially: genotypes are patterns; this criterion is weak and is listed to be honest about it |
| self-reproduction | see R-scale ≥ R3 | infrastructure copying; CREATE without inherited bytes | NOT OBSERVED |
| self-representation | see S-scale ≥ S2 | having bytecode | NOT OBSERVED |
| metabolism | see M-scale ≥ M3 | gas paid by a caller | NOT OBSERVED |
| functional environmental interaction | see E-scale ≥ E4 | reading `TIMESTAMP` then dying | NOT OBSERVED (E1 CANDIDATE: 107 input-dependent programs in the study; sensing without benefit) |
| interdependence of parts | ablation shows parts whose removal destroys a function other parts depend on | one-instruction programs | NOT OBSERVED |
| stability under perturbation | phenotype persists across environment perturbations better than random controls | identical behaviour because the program ignores the environment | NOT OBSERVED |
| evolution | heritable phenotype change across generations under selection, beyond drift | mutation alone | NOT OBSERVED |
| growth | population or lineage expansion caused by organisms' own activity | humans pressing install | NOT OBSERVED |

### VII.3 Reproduction, R0–R5

| level | definition | what distinguishes it from the level below |
|---|---|---|
| R0 | a human causes a genotype to exist (birth) | — |
| R1 | infrastructure reads a parent and writes a varied child (assisted heredity) | there is a parent |
| R2 | the environment, by its rules, copies an instance when some condition the instance produced is met | infrastructure acts only through published world rules, not per-genome |
| R3 | the parent's own execution constructs a descendant instance containing inherited information | no infrastructure copying at all |
| R4 | the descendant retains the construction mechanism | the process can repeat |
| R5 | R4 with heritable variation arising in the process | lineages can diverge without infrastructure mutation |

The Xerox line is between R2 and R3 and is drawn on the scorecard in those words.

### VII.4 Self-representation, S0–S4

| level | definition |
|---|---|
| S0 | no instruction reads the instance's own code or address |
| S1 | self-inspection executed (`CODESIZE`, `CODECOPY`, `ADDRESS`, `EXTCODEHASH(self)`) |
| S2 | self-copied information used as input to `CREATE`/`CREATE2` |
| S3 | the resulting child's code contains inherited bytes from the template |
| S4 | the child's template use recurs |

Having bytecode is S0. Mainnet has S1 candidates (programs that executed `CODESIZE` before dying).

### VII.5 Metabolism, M0–M5

| level | definition |
|---|---|
| M0 | execution paid for by the environment or a caller |
| M1 | an instance holds a resource (balance, storage) |
| M2 | an instance's behaviour depends on a resource it holds |
| M3 | an instance's execution acquires a resource from the environment |
| M4 | acquired resources support the instance's persistence or reproduction |
| M5 | the acquisition-and-use cycle is heritable |

### VII.6 Environmental interaction, E0–E5

| level | definition |
|---|---|
| E0 | no instruction reads the environment |
| E1 | environment sensed (any environmental opcode executed) |
| E2 | phenotype depends on the environment (differs across inputs or states) |
| E3 | environment modified (state, balance, logs, creation that persists) |
| E4 | modification measurably improves persistence or reproduction |
| E5 | the adaptation is heritable |

### VII.7 Robustness and interdependence

Measured, not levelled: for each genotype, the fraction of single-byte ablations that leave the phenotype unchanged (neutrality), that destroy it (lethality), and that alter it (plasticity); and the pairwise interaction between ablations. Reported as distributions for random vs evolved populations.

### VII.8 Evolution

Measured as the difference, with intervals, between a regime's phenotype trajectory and the drift control's, attributed to heritable genotype change. Status assigned per regime per world.

---

## Part VIII — Is the ordering right?

Mostly no, and it is worth saying plainly.

1. **Ablation (Era 5) should start now, on the genesis population.** It requires only the lab and the existing 800 genomes, it establishes the robustness baseline that every later comparison needs, and it is the natural first experiment of Era 1 (a single-byte substitution *is* an ablation).

2. **Environment (Era 4) cannot wait until after selection (Era 3).** Selection is defined relative to an environment. World v0 (the five probes) is already an environment with implicit pressures: a 1,000,000-gas ceiling, fresh state, one caller address. Era 3 needs the world vocabulary from day one, even if only one world exists.

3. **Swarm (Era 2) is not an era.** It is capacity, justified only by a measured need. Placing it before selection risks building infrastructure for an experiment that may fit on one machine.

4. **Self-representation (7) and reproduction (8) are not eras.** They are scorecard criteria with detectors that should run from Era 1 onward over every trace. Making them "late" eras implies we expect to arrive; the honest posture is to watch for them from the beginning.

5. **Wild vs collected (9) is a decision, not an era**, and it is needed before Era 1 produces its first descendant (Part X).

A truer sequence:

```
0  abiogenesis (current)
1  descent + neighbourhoods + ablation baseline + detectors (S, R, E, M) over every trace
2  worlds defined; selection regimes incl. drift; populations
3  ecology (shared worlds, transplants, perturbations); metabolism worlds as a subset
4  autonomy worlds (no infrastructure copying), only if R3 has ever been observed
∞  swarm, when compute-bound; fossilisation, when and if Part IX resolves
```

---

## Part IX — The collector, ownership and descendants (PROPOSED)

Today a receipt means: this release, its bytes, its program, who installed it, who holds it.

**Proposed rules.**

- A receipt never confers control over participation. Any public genome may be studied by anyone; experiments are systematic, not opt-in or opt-out. (Counter-argument: a collector who dislikes their program being mutated has no recourse. Response: the program is public bytes on a public chain and always was; the receipt was never a licence.)
- Descendants are **wild** by default: no receipt, no owner. The lineage record says "descended from release 166," which is a fact about provenance, not a property right.
- A collector may not claim autonomously produced descendants. Feudal ownership of evolution would make the artist's and collectors' incentives bear on which lineages are reported, which contaminates everything after.
- Whether a collector may *request* assisted descent of their release ahead of the systematic run: open. It costs nothing, but it is a selection pressure (collectors with time and interest shape the record). If allowed, it must be labelled as collector-initiated.
- Fossilisation receipts, if they exist, refer to a fossil release in a separate contract and say "fossil" on the card.

---

## Part X-A — Decisions ratified (constitution version 1, 2026-10-08)

Ratified by the artist at release 802, before any heredity experiment, before any code.

1. **Genotype identity is `keccak256(runtime bytes)`.** It is the on-chain checksum and what the invariant verifies. Identical bytes born twice are one genotype with two genesis events.
2. **Descendant length is fixed at 64 bytes for the neighbourhoods experiment only.** This expires when the first population experiment is designed; that experiment must publish its length rule as a world parameter. Permanent fixed length would deny organisms duplication and insertion, which is designing the organism by omission.
3. **The genesis population is every installer release requested before block *G*, the block in which the first mutation event is recorded.** *G* will be written here when it happens. Later births are generation 0 with an era tag and are not biologically distinguished in any way.
4. **Receipts refer to releases only. Descendants have no owner.** No future contract mints receipts for descendants by default. Collectors, the artist, and the keeper hold no property interest in any lineage. This protects the credibility of everything reported afterward.
5. **Refused genomes are in the population** as genesis genotypes with `instantiable: false`. They may have descendants.
6. **Vocabulary is layered and labelled.** Wherever facts are stated (the installer, the catalogue, the record, datasets) the words are install, release, program, refused, abandoned. The readings and the essays may use birth, organism, abiogenesis, and the rest, labelled as interpretation. The install button is never renamed.
7. **A stopping rule will be written before the first population experiment runs**, stating what result ends the experiment with a published negative conclusion. It is a required part of that experiment's pre-registration, not an afterthought.

Amendments to these are recorded here with dates. Experiments cite the version they ran under.

## Part X-B — Constitution amendment 1 (2026-10-08): research editions

Ratified by the artist at release 806, with E1 running and its results unknown.

**Rule 13 is amended.** The installer remains the only place a fee is taken from a participant, and everything after abiogenesis remains free. In addition, the artist may make and sell **research editions**: one artwork per pre-registered experiment, under these conditions, all of which are binding:

1. The edition is defined in the experiment's pre-registration, before results exist, and is generated deterministically from the sealed record. It exists whatever the hypotheses say.
2. Its metadata carries the record's root hash and the anchor transaction, so the image can be checked against the data that produced it.
3. It is offered only after the experiment's results are published.
4. It confers no rights over any program, release, receipt, lineage, or experiment, and no influence on any future one.
5. It is minted on a contract separate from the installer; the installer and its receipts are never touched.
6. Proceeds go to the artist and fund the work. The amount changes nothing about what is run or reported.
7. The catalogue stays plain. An edition is shown on the experiment's results page, never on a release's record or receipt.

**Why this is consistent with the principle.** The principle protects participants from being charged for evolution and protects the experiment from an artist with a stake in which lineages thrive. An edition about a finished experiment, fixed before its outcome, charges no participant and rewards no outcome. It is the artist's artwork about the research, which the roadmap (Part V) already named as the one honest lever.

**E1.** The E1 edition is a 1/1 generated from the sealed E1 record once it is complete, auctioned on the E1 results page after the results are published. Its form is chosen from renders made from the record and is recorded in `IDEAS.md` and the E1 document when fixed.

## Part X — Decisions needed now, as originally posed (expensive or impossible to reverse)

1. **Genotype identity = `keccak256(runtime bytes)`.** Already the on-chain checksum. Adopt. Consequence: identical bytes born twice are one genotype with two genesis events.
2. **Descendant identity.** Content-addressed: `childId = keccak256(parentIds ‖ operator ‖ seed ‖ experimentVersion)`; the genotype id is separate (two different events can yield the same bytes). Adopt before the first mutation event is written.
3. **Genesis designation.** Define the genesis population as all installer releases requested before block *G*, where *G* is the block in which the first Era 1 mutation event is recorded. Write *G* here when it happens. Later births are generation 0 with era tags. Nothing else distinguishes them.
4. **The 64-byte question.** Is genotype length fixed at 64 for descendants? Fixing it keeps the work's identity and makes neighbourhoods comparable; allowing insertion and deletion opens real evolutionary dynamics (duplication is how function grows). Proposal: Era 1 neighbourhoods at fixed length; Era 2 populations allow length change within [1, 24576], recorded as a world rule.
5. **Refused genomes.** They have identity, bytes, and a receipt, but no instance can exist on Ethereum. Proposal: they are in the lineage record as genesis genotypes with `instantiable: false`; they can have descendants (a one-byte mutation of the first byte makes them placeable), which is itself interesting.
6. **NFT / organism separation.** Decide now, in writing, that receipts refer to releases only, and that no future contract mints receipts for descendants by default.
7. **Experiment versioning.** Every record carries `{harnessVersion, worldId+version, mutationEngineVersion, constitutionVersion, gitCommit}`. Adopt the schema before the first record.
8. **Mutation reproducibility.** Seeds from one deterministic stream per experiment; the stream's root seed published; operators pure functions. Adopt before any event.
9. **Provenance storage.** Append-only files in the repository, content-hashed, with periodic root hashes published on-chain (any cheap chain, or as calldata on mainnet) so the record cannot be rewritten later without detection. Decide where the roots go.
10. **Vocabulary.** The catalogue says install/release/program. The roadmap says birth/organism/genotype. Decide whether the public face of the experiment adopts biological terms, and if so, keep the catalogue's facts in the catalogue's words.
11. **World v0 is the lab's current probe set.** Freeze and name it so every later comparison has a fixed reference.
12. **The three epistemic layers** (catalogue / lab / readings) become a rule: datasets contain the lab's layer only.

---

## Part XI — The minimum next release

*Pre-registered as [`experiments/E1-neighbourhoods.md`](experiments/E1-neighbourhoods.md) on 2026-10-08; not yet run.*

The smallest honest step toward heredity that keeps everything that makes the current work what it is:

**Neighbourhoods.** For every genesis genome (installed and refused), generate every single-byte substitution at a sample of positions, or all 64 × 255 = 16,320 one-mutants if compute allows (800 × 16,320 ≈ 13 million placements, about nine hours on the lab at 400/s; a 1-in-16 sample is thirty-five minutes). Place and probe each under world v0. Record mutation events, genotypes and phenotypes in the lineage record with the schema from Part X. Compute, per genesis genome, the neutral / lethal / altering fractions, and the same for a matched set of fresh random genomes.

**Publish** a *descent* view on the readings page: for each release, its neighbourhood summary, written in the readings' voice, with the record's numbers beneath, and a sentence stating that these descendants were made by infrastructure (R1) and live only on the lab's chain.

**Change nothing on mainnet.** No new contract, no new fee, no token for descendants.

**What it establishes.** Heredity (R1) and variation exist in the record; the robustness baseline (Era 5) for the genesis population; the detectors for S, E, M, R run over the first large body of related genomes; and the schema, identifiers, versioning and provenance habits that everything later depends on. If the neighbourhoods turn out to be as dead as random bytes, that is the first result of the experiment and it is published.

---

## Part XII — The evolutionary record (PROPOSED)

An append-only, content-addressed log, readable without the site:

```
genotypes/        id → bytes, length, first-seen event
events/           birth | mutation | recombination | placement | probe | ablation | transplant | perturbation | extinction | fossilisation | status-change
worlds/           id+version → full definition
experiments/      id → constitution version, harness version, regime, seeds, world, hypothesis written before the run
replications/     event → replication attempts and outcomes
log/              human-written entries: hypotheses, decisions, failures, amendments
roots/            periodic content hashes, with where each was published on-chain
```

Every event names its experiment; every experiment names its constitution version; every status on the scorecard names the events that justify it. A genotype discovered years from now is traced: genotype → event that produced it → parents → … → a genesis genotype → a release → a block on Ethereum.

---

## Part XIII — The site through the eras (PROPOSED)

- **Always:** the install button exactly as now, first on the page, with the sentence that it introduces unrelated random bytes into whatever exists. A visitor years from now must understand that in one glance.
- **Era 1:** readings gain descent; the summary gains lineages and descendants; the constitution and scorecard pages appear, with every criterion NOT OBSERVED except where the study already shows candidates.
- **Era 2/3:** populations, worlds, generation counters, extinctions, regime statements; an experiment log.
- **Later:** a lineage explorer; genome and phenotype views; a wild population counter; swarm status if it exists; fossils if they exist, labelled.
- **Never:** rarity, rankings, "alive" meters, or a percentage.

The catalogue page keeps saying `unknown`.

---

## Part XIV — Scientific credibility (PROPOSED practice)

For every criterion: what counts, what does not, confounders, methodology, the role of human selection, the environment's pressures, the infrastructure's contribution, replication, raw data. Hypotheses are written before runs. Negative results are published with equal prominence. Datasets and the harness are open so that external artificial-life researchers can reproduce any observation. A paper is a possible output; a status change for marketing is not.

---

## Part XV — Safety (binding)

- Organisms live in private EVMs. No host access, no filesystem, no network, no persistence beyond the record.
- Swarm nodes, if built, run only EVM bytecode in an interpreter and cannot be asked to do anything else.
- No self-propagating software is ever released onto public infrastructure as a consequence of an experiment. Fossilisation installs a chosen genotype as an ordinary contract through an audited contract; autonomy experiments never touch a public chain.
- No evasion of real security systems, no scanning, no exploitation. The questions here do not require any of it.
- The installer remains the only mainnet write path of the work, and it installs only what the chain chose.

---

## Part XVI — Open questions (deliberately unanswered)

1. Does the experiment adopt biological vocabulary in public, or keep the installer's plain words and reserve biology for the readings?
2. Is genotype length fixed at 64 for descendants?
3. Are refused genomes in the population?
4. May collectors initiate assisted descent of their own releases?
5. Who, if anyone, may fossilise, and is there ever a fee?
6. Where do the record's root hashes live?
7. Which selection regimes run first, and at what population size and mutation rate?
8. How is the `STOP` attractor handled without designing against it?
9. What is "the same world" across versions of the harness and the EVM?
10. When mainnet's gas rules change, does the price follow, and who decides?
11. Is a swarm ever justified, and would compute donation become a hidden selection pressure?
12. What would make us stop? A written stopping rule for the experiment is itself an open question.

---

## Part XVII — The statements, evaluated

- *"SLOPWARE began with random programs and asked what happens when the programmer leaves."* Accurate about the past and the question. Adopt as the project's one-line description.
- *"We may design the universe. We must not design the organism."* Accurate as a rule; slightly grand as copy. Adopt as the constitution's epigraph, not as marketing.
- *"SLOPWARE charges for creation. Evolution is free."* Accurate today and binding later. Adopt, with the fossilisation question noted beside it.
- *"Can meaningless computation become alive?"* Do not adopt. It presumes the direction. The question the work can honestly ask is whether anything on the scorecard ever changes status, and the answer may be no.

---

*Written 2026-10-08 at release 802, before any heredity experiment. Nothing above has been built.*
