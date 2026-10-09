# SLOPWARE

*software nobody wrote*

Software is written: someone decides what it should do and writes it, and it does that, more or less. Slopware is installed before it exists. You press install. In the next block, Ethereum fixes sixty-four bytes nobody chose, and those bytes become the whole of a program at an address of its own. Nothing reads them first. Nothing repairs them. Nothing tries again.

```
randomness → bytecode → EVM → ?
```

The program is the sculpture. The token is the receipt. The installer — this contract — is the only program here anyone wrote.

**Live on Ethereum mainnet since 2026-10-06** at [`0x44a64905069963b8321ee2b755a0b8b56d69cbc6`](https://etherscan.io/address/0x44a64905069963b8321ee2b755a0b8b56d69cbc6), source verified on Sourcify. The site is [slopware.fun](https://slopware.fun). The launch and its operations are recorded in [`LAUNCH.md`](LAUNCH.md).

## The invariant

For every installed release:

```
eth_getCode(program) == bytecode        // all sixty-four bytes, nothing before, nothing after
```

The program carries no ownership logic, no interface, no metadata. Ownership lives in the ERC-721 beside it. The installer places the program and never calls it.

## One contract

`contracts/src/Slopware.sol` — Solady ERC-721, about 350 lines, immutable, no proxy. The artist's only power is `setPrice`; there is no pause, cap, or off switch.

| | |
|---|---|
| `install()` payable | pay the price; the release is numbered and minted to you; the request block recorded. No bytecode exists yet. |
| `installMany(count)` payable | up to 100 at once, `count × price`; each release numbered, minted and later decided on its own. They share a transaction and a deciding block, nothing more. |
| `complete(release)` · `completeMany(releases[])` | anyone, once the deciding block (request block + 1) is final: bytecode = `keccak(blockhash, release, 0) ‖ keccak(blockhash, release, 1)`; placed by CREATE behind an 11-byte loader with every unit of gas the completer sent; recorded `Installed`, `Rejected` (bytecode Ethereum refuses, EIP-3541) or `Abandoned` (deciding block older than 256 blocks; refundable). |
| `software(release)` | installer, request/completion block, status, price paid, program address, checksum |
| `bytecodeOf(release)` | installed → the program's own code; rejected → kept here |
| `tokenURI(release)` | on-chain JSON and a plain Courier SVG, both base64: facts only |
| `setPrice` | artist only; the one mutable thing |
| `withdraw` / `claimRefund` | pull payments |

Events `Installing`, `Installed` (with the bytecode), `Rejected` (with the bytecode and reason), `Abandoned` let anyone rebuild every release from logs alone.

**Loader (11 bytes):** `PUSH1 0x40 · DUP1 · PUSH1 0x0b · PUSH1 0 · CODECOPY · PUSH1 0 · RETURN`, followed by the bytecode. Only these eleven bytes execute during an installation.

## Randomness

Two steps, next-block entropy, permissionless completion. The collector commits before the deciding block exists and cannot prevent completion once it does; the artist runs a keeper, a Vercel cron at `site/api/keeper.ts` (with `keeper/keeper.ts` as an always-on alternative), that completes within a minute or two for anyone who walks away. About 60% of collectors complete their own installs from the page first. The keeper has no power over any outcome. Proposer influence over the block hash is disclosed, not eliminated. Full analysis — VRF, commit/reveal, single transaction, next block — in [`RANDOMNESS.md`](RANDOMNESS.md).

## Rejections

About 1 in 256 bytecodes begins with `0xEF`, which Ethereum refuses to install (EIP-3541). The release is recorded — number, installer, bytecode, reason — and the collector keeps it. Nothing is substituted. Building this taught us two things worth writing down. First, a refusal inside CREATE is an exceptional halt that consumes *all* gas forwarded to the frame, 63/64 of the caller's. Second, any fixed gas allowance for CREATE is a bet on the chain's pricing: Sepolia's Amsterdam rules made a 64-byte placement cost 311k where it had cost 61k, and a 120k allowance would have frozen every completion. So the installer does neither. The refusal rule is one byte, and the contract applies it itself and records the rejection without running CREATE; for everything else CREATE gets all remaining gas, and a placement that falls short reverts (`PlacementFailed`) so nothing false is recorded. Rejections are cheap and always genuine.

## Gas (Foundry, optimizer 5000 runs; today's mainnet pricing — Amsterdam roughly quadruples storage costs)

| | gas |
|---|---:|
| `install()` | 160,356 (first ever); ~110k thereafter |
| `complete()` → installed | 174,020 |
| `complete()` → rejected | under 100k (no CREATE runs) |
| `installMany(100)` | ~7.7M (about 77k per release) |

## Tests

`cd contracts && forge test` — 21 tests: code == bytecode (bytes, hash, length); a 3,000-bytecode deterministic corpus with zero silent mutation; fuzz over bytecode and over entropy; rejection recorded, not rerolled; rejection gas bounded; gas-starved placement reverts instead of recording; sequential releases; installer immutable through transfer; completion once and not early; same-block installs differ; abandonment → refund; price accounting and authorization; the installer never calls the program (a program that is `INVALID` at its first byte installs fine); contract installers and re-entrancy attempts; no receiver callback; factual `tokenURI`; gas; batches: numbering, per-release events and payment, exact price and bounds, a hundred under the per-transaction gas cap, batch completion that settles what is ready and passes over the rest.

## Running locally

```sh
./slopware/sim.sh     # anvil (osaka, 2 s blocks) + installer + keeper + site at http://127.0.0.1:8001
```

## Site

`site/index.html` — one document in the manner of a contract show: Courier, black on white, text controls, viewport-height sections. At the top, sixty-four random bytes redrawn continuously — the only moving thing on the page. Then the installer explained, the installed sculptures, a record per release (`#/184`), the lab. The catalogue states facts and says `unknown`.

`site/readings.html` — the lab's observation of every installed program, placed on a private chain and probed; each gets a short life in the readings' voice with the record's numbers beneath. Observation, not record. Generated by `npx tsx src/readings.ts`.

Reads go through two cached functions, `site/api/state.ts` and `site/api/release.ts`, so the public RPC sees one read every ten seconds however many people are looking; installs go straight to the chain. `site/build.mjs` fills the installer address and RPC from the Vercel environment; locally, pass `?contract=` and `?rpc=`. `site/lab.json` is generated from the research runs by `../scripts/lab_json.py`. The readings page loads `site/r/index.json`, a light index with each life's sentences already written (about 50 KB compressed for 839 releases), filters it by lens or search, shows forty at a time, and fetches a release's bytes from `site/r/d-<n>.json` (100 releases per chunk) only when a reader opens them; `site/readings.json` remains the full record. Everything a reader needs is in the HTML itself: `site/e1.html` is generated by `../scripts/e1_page.py` from `site/e1.template.html` and the sealed record, so the hypotheses, verdicts, sentences and data are static text (only the auction widgets need script); the build bakes the installer's price and counts into the catalogue; and `site/llms.txt`, `site/e1.md` and `site/readings.md` (from `../scripts/site_md.py`) are plain-text mirrors for agents and crawlers.

## Documents

[`RANDOMNESS.md`](RANDOMNESS.md) · [`SECURITY.md`](SECURITY.md) · [`FUTURE.md`](FUTURE.md) · [`LAUNCH.md`](LAUNCH.md) · [`ROADMAP.md`](ROADMAP.md) (the proposed experiment, constitution v1) · [`IDEAS.md`](IDEAS.md) · [`experiments/`](experiments/) (pre-registered experiments; E1 is the first). The lab — the harness that sampled random program space before the installer was built — lives one directory up (`../README.md`, `../BASELINE.md`).

`deploy/` — the page that deploys the installer from the artist's own wallet; `make.mjs` regenerates it from the compiled artifact.

## Principle

Simple over clever. Preserve the bytecode over convenience. Never improve a random program. The artwork is not that slopware is good software. The artwork is that nobody knows what it is.
