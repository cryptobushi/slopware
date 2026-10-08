# Not in the installer

Things that came up and were deliberately kept out of the installer. The work is one installer, one button, one unknown program. Each of these would make it something else. The installer is immutable, so this list is permanent for it; some items now have a life *beside* it in [`ROADMAP.md`](ROADMAP.md), and that is noted where it applies.

- **Evolution, mutation, breeding, reproduction.** Never in the installer. The roadmap proposes them as a separate, pre-registered experiment that may use installed programs as ancestors but changes nothing about them (constitution v1, decision 1). The first such experiment is [`experiments/E1-neighbourhoods.md`](experiments/E1-neighbourhoods.md).
- **Behaviour on the catalogue or the receipt.** The catalogue says `unknown` and the receipt's behaviour attribute is a constant. The lab's observations live on a separate page, `/readings`, labelled as observation, not record. Three layers, never merged.
- **Other bytecode lengths.** Sixty-four only, forever, for releases. Descendants in experiments are fixed at 64 for E1 and may vary later as a published world rule (constitution v1, decision 2).
- **Weighted opcodes, repair, viability filtering, retries.** Forbidden by the invariant. Listed so nobody "improves" them in later.
- **Collector-chosen bytecode or salts.** The collector contributes nothing to the bytecode. Even a user salt lets them grind.
- **Rarity, traits, scores, rankings, leaderboards.** The lab's interestingness heuristic exists to help a human read; it must never appear on a token or in the registry.
- **ERC-2981 royalties.** Left out to keep the contract to its one job; the roadmap's economic principle now rules them out for anything evolutionary too.
- **Chainlink VRF.** The correct randomness if price or chain ever allow it; only the entropy source would change. Would need a new installer.
- **USD peg, bonding curves, staking, protocol token, DAO, treasury.** No.
- ~~**Batch installs.**~~ Reconsidered before launch: `installMany` installs up to a hundred in one transaction, because the work wants a large population. Each release is still decided on its own; the batch shares nothing but a block.
- **Marketplace.** Standard ERC-721; existing infrastructure handles transfers.
- **AI generating programs.** If AI ever enters, it observes; it does not generate.
- **Naming programs, galleries, "run" buttons that call the program.** Calling an arbitrary program is the caller's business; the catalogue stays a catalogue.
- **A completer bounty.** Completion is cheap and the artist runs a keeper; paying completers from the price adds an incentive surface for nothing.
- **A pause, a cap, an off switch.** There is none. Supply is governed by price alone, in public, through `PriceSet` events.
