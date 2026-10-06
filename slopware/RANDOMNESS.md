# Randomness

The invariant: **the collector commits before the bytecode exists, and nobody — collector, artist or keeper — can select, preview or retry it.** Every option was judged against that, and against launching quickly at a ~$1 price.

## Options

### A. Chainlink VRF (or equivalent)
Verifiable, unmanipulable, two transactions. Rejected for v1: mainnet fulfillment costs several dollars per request — more than the price — and makes a $1 piece depend on a third-party coordinator, a subscription and a callback into the installer. Viable later if price or chain change; the two-step shape already matches VRF's request/fulfill.

### B. Commit / reveal
Collector commits `hash(secret)`; bytecode = `f(secret, later blockhash)`. Fatal: once the later block exists the collector can compute the bytecode off-chain and simply decline to reveal — paying the price to discard what they saw. That is a retry. Rejected.

### D. One transaction, `keccak(prevrandao, msg.sender, …)`
The collector can simulate the transaction and abort if they dislike the result; `prevrandao` for the current block is known before sending. They know the bytecode before committing. Rejected.

### C. Two steps, next-block entropy, anyone completes — **chosen**
1. `install()` — pay; the release is numbered and minted; the request block *R* recorded. No bytecode exists.
2. `complete(release)` — anyone, from block *R+2*: bytecode = `keccak(blockhash(R+1), release, 0) ‖ keccak(…, 1)`. CREATE. Done.

Why it holds:
- At commit time the deciding block does not exist. No preview, no simulation.
- Once it exists, the collector cannot stop the installation: anyone may complete it, and the artist runs a keeper that does so within a block or two. Declining to complete does not produce a different result.
- The entropy is consumed exactly once; a second `complete` reverts.
- The artist has no input at any step.

## Residual risks, plainly

- **Proposer influence.** The proposer of block *R+1* can affect its hash by choosing what to include and in what order, and could grind toward a preferred bytecode. Real in principle. At a ~$1 release there is nothing to gain, and it is the chain's randomness, not the artist's or the collector's. We do not claim VRF-grade unpredictability.
- **Abandonment.** `blockhash` is available for 256 blocks (~51 minutes). If nobody completes within that window, the entropy is gone from the EVM. The release is recorded `Abandoned`, the price refundable to the installer, and **no bytecode is substituted**. With a running keeper this does not happen; the design is honest if it does.
- **The collector as completer.** The site has the collector's own wallet complete the installation to spare the keeper gas; if they refuse, the keeper does it. The keeper is a liveness service, not a trust assumption about outcomes — it cannot alter the bytecode.
- **Same-block installs** share a deciding block but not a bytecode: the release number is mixed in.

## Why not fix the proposer risk
VRF is the honest fix and it is priced out at this scale. We prefer a clearly stated weak point to a mechanism that makes the piece cost more than it charges.
