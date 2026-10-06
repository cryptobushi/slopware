#!/usr/bin/env bash
# SLOPWARE local simulation: anvil (mainnet rules), the contract, a keeper, and the site.
#   ./slopware/sim.sh        → http://127.0.0.1:8001
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.foundry/bin:$PATH"
RPC=http://127.0.0.1:8545
DEPLOYER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
DEPLOYER_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
KEEPER_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

cleanup() { kill "${ANVIL_PID:-}" "${HTTP_PID:-}" "${KEEPER_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT

echo "anvil (osaka, EIP-7825, 2 s blocks so installations complete on their own)…"
anvil --hardfork osaka --enable-tx-gas-limit --block-time 2 --silent --chain-id 31337 &
ANVIL_PID=$!
for _ in $(seq 1 50); do cast chain-id --rpc-url $RPC >/dev/null 2>&1 && break; sleep 0.2; done

( cd contracts && PRICE=300000000000000 ARTIST=$DEPLOYER forge script script/Deploy.s.sol --rpc-url $RPC --private-key $DEPLOYER_KEY --broadcast --silent >/dev/null )
ADDR=$(cast compute-address $DEPLOYER --nonce 0 --rpc-url $RPC | awk '{print $NF}')
echo "SLOPWARE  $ADDR  (price $(cast call $ADDR 'price()(uint256)' --rpc-url $RPC) wei)"

( cd .. && RPC=$RPC SLOPWARE=$ADDR KEEPER_KEY=$KEEPER_KEY npx tsx slopware/keeper/keeper.ts > /tmp/slopware-keeper.log 2>&1 ) &
KEEPER_PID=$!
( cd site && python3 -m http.server 8001 --bind 127.0.0.1 >/dev/null 2>&1 ) &
HTTP_PID=$!
echo "site      http://127.0.0.1:8001/?contract=$ADDR&rpc=$RPC"
echo "keeper    log at /tmp/slopware-keeper.log"
echo
echo "install from the shell:"
echo "  cast send $ADDR 'install()' --value 300000000000000 --rpc-url $RPC --private-key $DEPLOYER_KEY"
echo "  (the keeper completes it a couple of blocks later)"
echo "  cast call $ADDR 'software(uint256)((address,uint64,uint64,uint8,uint96,address,bytes32))' 1 --rpc-url $RPC"
echo "  cast call $ADDR 'bytecodeOf(uint256)(bytes)' 1 --rpc-url $RPC"
echo
echo "ctrl-c stops everything."
wait $ANVIL_PID
