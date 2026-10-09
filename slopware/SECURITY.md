# Security

SLOPWARE places arbitrary, untrusted programs on purpose. The model is: **the installer never executes a program; a program never touches the installer.**

## Boundaries

- **Program.** Sixty-four random bytes. May contain `CALL`, `DELEGATECALL`, `SELFDESTRUCT`, `CREATE`, `CREATE2`, `SSTORE`, `REVERT`, `INVALID`, pathological memory operations — anything. Placed by `CREATE`, never called by the installer. Its only tie to the installer is that the installer's nonce determined its address.
- **Loader.** Eleven fixed bytes: copy the bytecode to memory, return it. The only code that runs during an installation. The bytecode is data to it.
- **Installer (`Slopware`).** Immutable; no proxy; no admin over bytecode, programs, numbering or records. The artist can change only `price`, which has no effect on generation.

## Specific concerns

**Refused bytecode never reaches CREATE.** An EIP-3541 refusal is an exceptional halt in the creation frame: it consumes *all* gas forwarded to CREATE — by EIP-150, 63/64 of the caller's. The first design bounded CREATE in a self-call with a fixed 120,000-gas stipend. Sepolia, under Amsterdam pricing, showed the flaw: a placement there costs ~311k, so every completion reverted and the deployment was dead. A fixed stipend is a bet on gas prices the contract cannot revise. Now the refusal rule (first byte `0xEF`) is applied by the contract itself and recorded as `Rejected` without running CREATE, and CREATE receives every unit of gas the completer sent. A rejection costs under 100k gas.

**A gas-starved placement must never be recorded as a rejection.** For bytecode Ethereum does not refuse, CREATE returning nothing can only mean too little gas. `_place` reverts (`PlacementFailed`, or the EVM's own out-of-gas), the whole completion unwinds, the release stays `Installing` and can be completed with more gas. Only bytecode beginning with `0xEF` is recorded `Rejected`. Tested.

**Reentrancy.** `install` makes no external calls; `_mint` (not `_safeMint`), so no receiver callback runs during an installation. `complete` makes no external call except `CREATE` of the loader, which runs eleven fixed bytes and returns. Refunds and the artist's withdrawal are pull-based and run after state updates. A contract installer that re-enters from `receive()` or `onERC721Received` is tested and cannot.

**Callbacks.** None. No oracle callback, no receiver hook.

**Completing twice.** `complete` requires `status == Installing` and sets a terminal status before any external effect. Tested.

**Entropy reuse.** `blockhash(R+1)` is mixed with the release number; two installs in one block yield different bytecode. Tested.

**Numbering.** `releases` advances once per release, whether installed singly or in a batch; numbers are sequential and never skipped, including rejections and abandonments.

**Batches.** `installMany` is bounded at 100 (about 7.7M gas; the per-transaction cap is 2^24). `completeMany` passes over releases that are not ready or already settled instead of reverting, so a keeper's batch cannot be made to fail by a collector completing one of its releases first. Each release in a batch has its own bytecode because the release number is mixed into the hash.

**Rejection accounting.** `installed + rejected + abandoned + installing == releases` always; rejected bytecode is stored because no program exists to read it from.

**Money.** `withdraw` sends `balance − totalRefundable` to the immutable artist; refunds owed cannot be withdrawn by the artist. `claimRefund` zeroes before sending. Price is exact (`WrongPrice`).

**Malicious completers.** `complete` is permissionless by design. A completer cannot influence the bytecode or the outcome; they can only pay to make it happen.

**Gas griefing.** The worst a caller can do is fail to supply enough gas; the result is a revert, not a corrupted record.

**Abandonment.** After 256 blocks the entropy is gone; `complete` records `Abandoned` and credits a refund. There is no path to substitute entropy.

**Metadata.** `tokenURI` is a view over recorded facts; it reads the program's code via `EXTCODECOPY`, which executes nothing, and never calls the program.

## Not protected against, and why

- Proposer influence over `blockhash(R+1)`: see RANDOMNESS.md. Priced as acceptable; disclosed.
- Programs doing harmful things *to themselves or to third parties who call them*. An installed program is an arbitrary program at a public address. Calling it is at the caller's risk; the site never calls it.

## Audit status

Unaudited, and live on mainnet since 2026-10-06 by the artist's decision. The test suite (`contracts/test/Slopware.t.sol`, 21 tests including fuzzing and a 3,000-bytecode corpus) encodes the properties above, and a three-deployment Sepolia rehearsal found and fixed two defects that tests could not (a gas allowance that failed under Amsterdam pricing; a metadata encoding that broke in wallets), both recorded in `LAUNCH.md`. An independent review of `Slopware.sol` is still recommended.

## Operational surface

- **Keeper key.** Held as a Vercel environment variable, readable by the team; the wallet holds gas money and can affect no outcome of the installer. The cron endpoint requires a bearer secret; completing is permissionless anyway, so the secret only prevents strangers from spending the keeper's gas.
- **Keeper as creator of record (from 2026-10-08).** Research editions (roadmap Part X-B) are minted from the keeper's wallet on a creator contract separate from the installer. That contract names the artist's wallet as a second admin, so a compromised or lost keeper key cannot take the series, and auction proceeds are swept from the keeper to the artist promptly, so the wallet never holds more than gas and a pending sweep. A compromised keeper key could still mint an unauthorised token on that contract; the artist admin can revoke the keeper if that ever happens, and the edition list in each experiment's document is the authority on which tokens are real.
- **Read API.** `site/api/state.ts` and `site/api/release.ts` are read-only, hold no keys, and cache at the edge.
- **Deploy page.** `deploy/index.html` embeds the compiled creation bytecode and signs with the artist's own wallet in the browser; no key leaves the wallet.
- **The lab and experiments** run only on private chains with Anvil's published test keys and refuse any other RPC; see `ROADMAP.md` Part XV for the binding safety rules of the experiment.
