# Launch

Nothing here deploys to mainnet by itself. The final command is at the bottom, to be run by the artist, by hand, after every box is ticked.

## Before anything

- [ ] `cd slopware/contracts && forge test` — 21/21 green.
- [ ] `forge test --gas-report` consistent with README (install ~160k first / ~110k after, complete ~174k, rejection under 100k — mainnet pricing; Sepolia runs Amsterdam and costs ~4× on storage).
- [ ] Read `Slopware.sol` once more, top to bottom. Nothing in it should surprise you.
- [ ] Independent review arranged, or consciously waived.
- [x] `python3 scripts/lab_json.py deep-1m-64b` run after the 1M study completed (2026-10-06); `site/lab.json` committed.

## Local rehearsal

- [ ] `./slopware/sim.sh` → open the printed URL → install with a wallet on 127.0.0.1:8545 (chain 31337), or use the `cast send` lines it prints.
- [ ] `/tmp/slopware-keeper.log`: installations complete within two blocks.
- [ ] `bytecodeOf(release)` equals `eth_getCode(program)` for an installed release.
- [ ] Force a rejection on a fork (see test `_forceRejection`) and confirm the site shows it.

## Sepolia

Deployed 2026-10-06 from the artist's wallet: `0x5ae269871454c536ead7aa07052eeee0b0194f13` (artist `0x29104975057C20062596FB755047c1C9fb59daaE`, price 0.0004 ETH). Sourcify: exact match. Earlier deployments: `0xadc3c5cfe9c44d6b77236c3a5c941b83531817d6` (bounded 120k-gas placement; could not complete anything under Sepolia's Amsterdam pricing; its one release refundable) and `0xb8e9ef6e0859bfe4aba6b3e93530636de0c7f225` (utf8 metadata whose `#` broke the image; six releases installed and visible there with a blank card). Keeper `0xB847754313D6320f43396F885d168b0B433b913f`, funded 0.05 Sepolia ETH, running from the Vercel cron. Site: https://slopware.vercel.app

- [ ] Deploy from your own wallet: `node slopware/deploy/make.mjs && (cd slopware/deploy && python3 -m http.server 8002)`, open http://127.0.0.1:8002, connect, set artist and price, confirm the network, deploy. (Or from a keystore: `cast wallet import slopware-sepolia --interactive`, then `ARTIST=<artist> PRICE=300000000000000 forge script script/Deploy.s.sol --rpc-url https://ethereum-sepolia-rpc.publicnode.com --account slopware-sepolia --broadcast -vv` in `slopware/contracts`.)
- [ ] `forge verify-contract <addr> src/Slopware.sol:Slopware --chain sepolia --constructor-args $(cast abi-encode "constructor(address,uint256)" <artist> 300000000000000)`
- [ ] Keeper: on Vercel, set `SLOPWARE=<addr>` in the project's production environment and redeploy; the cron at `/api/keeper` runs every minute. (The always-on `keeper/keeper.ts` remains for running one by hand.)
- [ ] Site: the same `SLOPWARE` variable fills the page at build time on Vercel (https://slopware.vercel.app); install a handful from different wallets; confirm records on Etherscan and that wallets render `tokenURI` (base64 JSON and SVG — the first utf8 version broke on the `#` in a color).
- [ ] Leave it a day with the keeper running. Nothing should be abandoned.

## Mainnet decisions (write the answers here)

- [ ] Artist address `0x…` — receives payments, may set the price, can touch nothing else.
- [ ] Initial price in wei `…` (≈ $1 on the day).
- [ ] Keeper address `0x…`, funded; who runs it, where, with what alerting.
- [ ] Site hosting, with `__SLOPWARE__` replaced by the mainnet address.
- [ ] Rejected releases receive a token — confirmed (default yes).

## Mainnet — by hand

Deployed 2026-10-06 from the artist's wallet via the deploy page: `0x44a64905069963b8321ee2b755a0b8b56d69cbc6` (artist `0x29104975057C20062596FB755047c1C9fb59daaE`, price 0.0004 ETH, batch cap 100). Runtime code matches the build byte for byte apart from the immutable artist. Same code as the third Sepolia deployment.

```sh
cd slopware/contracts
cast wallet import slopware-mainnet --interactive
ARTIST=<artist> PRICE=<wei> \
forge script script/Deploy.s.sol --rpc-url <mainnet rpc> --account slopware-mainnet --broadcast -vv
forge verify-contract <addr> src/Slopware.sol:Slopware --chain mainnet --constructor-args $(cast abi-encode "constructor(address,uint256)" <artist> <wei>)
```

Then start the keeper, replace `__SLOPWARE__`, publish, and install release 000001 yourself.

## Open items

1. **No independent audit yet.**
2. ~~Marketplace rendering of utf8 `tokenURI`~~ — Sepolia showed the problem (a raw `#` truncates the image data URI); metadata is now base64 end to end.
3. **Proposer influence on entropy** — disclosed, not eliminated (RANDOMNESS.md).
4. **Keeper liveness is operational.** Down 51 minutes with no one else completing → abandonment (refundable).
5. **`setPrice` trades away full immutability** for a dollar target in a moving ETH price.
