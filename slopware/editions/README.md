# Research editions

One artwork per pre-registered experiment, under constitution amendment 1 (`../ROADMAP.md`, Part X-B). Deployed, minted and listed **from the keeper wallet** (`0xB847754313D6320f43396F885d168b0B433b913f`), which is the creator of record; the artist's wallet is a second admin on the contract and the sole receiver of auction proceeds. Nothing here touches the installer.

## What this is

- `src/ResearchEditions.sol`: Manifold's `ERC721Creator` (package `@manifoldxyz/creator-core-solidity` 3.0.0), unchanged, under the series name. It is the same contract Manifold Studio deploys, so Manifold's marketplace, widgets and media API treat it as native.
- `irys-upload.mjs`: pins a file to Arweave through Irys, paid in ETH from the keeper (devnet when not `mainnet`). Prints the Arweave id.
- `widgets.html`: the auction section for an experiment's results page, built from Manifold's listing widgets in the site's register. Placeholders `__ID__` (listing id), `__NET__` (chain id), `__MKT__` (marketplace address).

Manifold's marketplace: mainnet `0x3a3548e060be10c2614d0a4cb0c03cc9093fd799` (V1), Sepolia `0x5246807fB65d87b0d0a234e0F3D42374DE83b421` (V2). Both proxy the same implementation. Fee 0 bps; a 6.9% referrer cut applies only if a listing enables referrers, which ours do not.

## The sequence (all signed by the keeper)

```sh
export PATH="$HOME/.foundry/bin:$PATH"; export KEEPER_WALLET_FILE=<protected file>
RPC=...; PK=$(python3 -c "import json;print(json.load(open('$KEEPER_WALLET_FILE'))['private_key'])")
K=0xB847754313D6320f43396F885d168b0B433b913f; ARTIST=0x29104975057C20062596FB755047c1C9fb59daaE; MKT=<marketplace>

# 1. contract (once per series)
forge build
ARGS=$(cast abi-encode "constructor(string,string)" "SLOPWARE research editions" "SLOPRE")
BIN=$(python3 -c "import json;print(json.load(open('out/ResearchEditions.sol/ResearchEditions.json'))['bytecode']['object'])")
cast send --rpc-url $RPC --private-key $PK --create "${BIN}${ARGS#0x}"          # → contract C
cast send --rpc-url $RPC --private-key $PK $C 'approveAdmin(address)' $ARTIST

# 2. pin (image first, then metadata that points at it)
IMG=$(node irys-upload.mjs threads.png image/png mainnet)
META=$(node irys-upload.mjs metadata.json application/json mainnet)

# 3. mint
cast send --rpc-url $RPC --private-key $PK $C 'mintBase(address,string)' $K "https://gateway.irys.xyz/$META"   # → tokenId T (Transfer log)

# 4. list: individual auction, reserve R wei, starts on first bid, runs D seconds, 10% increments, 5-minute extension, proceeds 100% to the artist
cast send --rpc-url $RPC --private-key $PK $C 'approve(address,uint256)' $MKT $T
SIG='createListing((uint256,uint8,uint24,uint24,uint16,uint16,address,address,uint48,uint48),(uint256,address,uint8,bool),(uint16,uint240),(address,uint16)[],bool,bool,bytes)'
cast send --rpc-url $RPC --private-key $PK $MKT "$SIG" "($R,1,1,1,300,1000,0x0000000000000000000000000000000000000000,0x0000000000000000000000000000000000000000,0,$D)" "($T,$C,1,false)" "(0,0)" "[($ARTIST,10000)]" false false 0x
# listing id = return value (simulate with cast call first) — the token is escrowed in the marketplace

# 5. page: fill widgets.html with the listing id, chain id, marketplace; add to the experiment's results page

# 6. after endTime (startTime is set by the first bid; endTime = first bid + D, extended by late bids)
cast send --rpc-url $RPC --private-key $PK $MKT 'finalize(uint40)' $LISTING   # token → winner, ETH → artist; with no bid the token returns to the keeper
```

Metadata carries: name, description (what the lines are), image, `external_url` (the experiment's results page), and attributes for experiment, record root hash, anchor transaction, script hash, program count, date, "minted by: the keeper". Fixed before the auction; `setTokenURI` exists but is not used after listing.

## Rehearsal — Sepolia, 2026-10-08

Everything above was run once on Sepolia with a placeholder image, by the keeper, with no human step.

| step | result |
|---|---|
| contract | `0xf001e6b9277c2c63945917be9063ccfceafeb407` (tx `0xf460f4b35f24f4a4d3373bac07af8b28aebf37d9bdacbeec6fcb4cf1fa7940dc`), owner keeper, admin artist |
| pin | image `4kjdVrCc8N4KjLL6sS6nRoNp8zLbhD1X43e4XVMDcN5b`, metadata `5MoFbPjrq9xEQ14rKL2gvz2Df1vntzzgMvbkokNhpAjn` (Irys devnet, expires) |
| mint | token 1, 796,865 gas |
| listing | id 1554 on marketplace V2 (tx `0xa7b67a9b0722c614458e8870e10b707e4c38e89fc557d0b6ebc732d20947f3dc`), reserve 0.01, 15 minutes, receiver artist 100% |
| bid | 0.01 ETH from a throwaway wallet; widgets showed image, current bid, countdown, minimum next bid 0.011, history |
| finalize | queued for the auction's end; result appended below when it lands |

Notes: the connect widget must not be given `data-app-name` without a `data-client-id`; with neither, it runs on the fallback provider. The widgets read the listing from the chain directly and fetched the token's media through Manifold's own API, so no indexing by Manifold was needed. Deploy cost 33.5M gas on Sepolia under the Amsterdam repricing; the mainnet estimate for the same bytecode is 4.79M gas, about 0.001 ETH at a 0.1 gwei base fee.
