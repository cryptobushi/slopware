# Security

SLOPWARE places arbitrary, untrusted programs on purpose. The model is: **the installer never executes a program; a program never touches the installer.**

## Boundaries

- **Program.** Sixty-four random bytes. May contain `CALL`, `DELEGATECALL`, `SELFDESTRUCT`, `CREATE`, `CREATE2`, `SSTORE`, `REVERT`, `INVALID`, pathological memory operations — anything. Placed by `CREATE`, never called by the installer. Its only tie to the installer is that the installer's nonce determined its address.
- **Loader.** Eleven fixed bytes: copy the bytecode to memory, return it. The only code that runs during an installation. The bytecode is data to it.
- **Installer (`Slopware`).** Immutable; no proxy; no admin over bytecode, programs, numbering or records. The artist can change only `price`, which has no effect on generation.

## Specific concerns

**Refused bytecode burns gas.** An EIP-3541 refusal is an exceptional halt in the creation frame: it consumes *all* gas forwarded to CREATE — by EIP-150, 63/64 of the caller's. Unbounded, a rejection would burn nearly the completer's entire gas limit. CREATE therefore runs inside `placeProgram`, a self-call with a fixed `DEPLOY_GAS` stipend (120,000; a successful placement needs ~50,000). A rejection costs ~270k gas total.

**A gas-starved placement must never be recorded as a rejection.** If `placeProgram` returns `address(0)` and the bytecode does *not* begin with `0xEF`, the only cause is insufficient gas in the frame. `complete` reverts with `OutOfGasNotRejection()`; the release stays `Installing` and can be completed with more gas. Only a genuine protocol refusal (`0xEF`) is recorded `Rejected`. Tested.

**Reentrancy.** `install` makes no external calls; `_mint` (not `_safeMint`), so no receiver callback runs during an installation. `complete` makes one external call — to itself, bounded — whose only effect is `CREATE` of the loader. Refunds and the artist's withdrawal are pull-based and run after state updates. A contract installer that re-enters from `receive()` or `onERC721Received` is tested and cannot.

**Callbacks.** None. No oracle callback, no receiver hook.

**Completing twice.** `complete` requires `status == Installing` and sets a terminal status before any external effect. Tested.

**Entropy reuse.** `blockhash(R+1)` is mixed with the release number; two installs in one block yield different bytecode. Tested.

**Numbering.** `releases` increments once per `install`; numbers are sequential and never skipped, including rejections and abandonments.

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

Unaudited. The test suite (`contracts/test/Slopware.t.sol`, 18 tests including fuzzing and a 3,000-bytecode corpus) encodes the properties above. An independent review of `Slopware.sol` is recommended before mainnet.
