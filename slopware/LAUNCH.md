# Launch

Nothing here deploys to mainnet by itself. The final command is at the bottom, to be run by the artist, by hand, after every box is ticked.

## Before anything

- [ ] `cd slopware/contracts && forge test` — 18/18 green.
- [ ] `forge test --gas-report` consistent with README (install ~160k first / ~110k after, complete ~174k, rejection ~270k).
- [ ] Read `Slopware.sol` once more, top to bottom. Nothing in it should surprise you.
- [ ] Independent review arranged, or consciously waived.
- [ ] `python3 scripts/lab_json.py deep-1m-64b` run after the 1M study completes; `site/lab.json` committed.

## Local rehearsal

- [ ] `./slopware/sim.sh` → open the printed URL → install with a wallet on 127.0.0.1:8545 (chain 31337), or use the `cast send` lines it prints.
- [ ] `/tmp/slopware-keeper.log`: installations complete within two blocks.
- [ ] `bytecodeOf(release)` equals `eth_getCode(program)` for an installed release.
- [ ] Force a rejection on a fork (see test `_forceRejection`) and confirm the site shows it.

## Sepolia

- [ ] `cast wallet import slopware-sepolia --interactive`
- [ ] Deploy:
  ```sh
  cd slopware/contracts
  ARTIST=<artist> PRICE=300000000000000 \
  forge script script/Deploy.s.sol --rpc-url https://ethereum-sepolia-rpc.publicnode.com --account slopware-sepolia --broadcast -vv
  ```
- [ ] `forge verify-contract <addr> src/Slopware.sol:Slopware --chain sepolia --constructor-args $(cast abi-encode "constructor(address,uint256)" <artist> 300000000000000)`
- [ ] Keeper against Sepolia: `RPC=… SLOPWARE=<addr> KEEPER_KEY=<key> npx tsx slopware/keeper/keeper.ts`
- [ ] Site pointed at it (`?contract=<addr>` or `__SLOPWARE__` replaced), hosted statically; install a handful from different wallets; confirm records on Etherscan and that marketplace testnet views render `tokenURI` (utf8 JSON + utf8 SVG — watch for ones that need base64).
- [ ] Leave it a day with the keeper running. Nothing should be abandoned.

## Mainnet decisions (write the answers here)

- [ ] Artist address `0x…` — receives payments, may set the price, can touch nothing else.
- [ ] Initial price in wei `…` (≈ $1 on the day).
- [ ] Keeper address `0x…`, funded; who runs it, where, with what alerting.
- [ ] Site hosting, with `__SLOPWARE__` replaced by the mainnet address.
- [ ] Rejected releases receive a token — confirmed (default yes).

## Mainnet — by hand

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
2. **Marketplace rendering of utf8 `tokenURI` unverified**; switch the image to base64 if Sepolia shows a problem.
3. **Proposer influence on entropy** — disclosed, not eliminated (RANDOMNESS.md).
4. **Keeper liveness is operational.** Down 51 minutes with no one else completing → abandonment (refundable).
5. **`setPrice` trades away full immutability** for a dollar target in a moving ETH price.
6. **The 1M lab run** replaces the 100k numbers on the site when it finishes; `lab.json` must be regenerated and committed.
