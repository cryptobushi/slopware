/**
 * SLOPWARE keeper: completes installations so no collector can abandon bytecode they have seen.
 *
 * Once the block after a request exists, calls complete(release). Anyone may run
 * this; the artist runs one. Idempotent — an installation already completed by someone else reverts
 * cheaply (NotInstalling) and is skipped.
 *
 *   RPC=http://127.0.0.1:8545 SLOPWARE=0x… KEEPER_KEY=0x… npx tsx slopware/keeper/keeper.ts
 */
import { createPublicClient, createWalletClient, http, parseAbi, type Hex } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

const RPC = process.env.RPC ?? 'http://127.0.0.1:8545';
const SLOPWARE = (process.env.SLOPWARE ?? '') as Hex;
const KEY = (process.env.KEEPER_KEY ?? '') as Hex;
if (!SLOPWARE || !KEY) { console.error('SLOPWARE and KEEPER_KEY are required'); process.exit(2); }

const abi = parseAbi([
  'function releases() view returns (uint256)',
  'function statusOf(uint256) view returns (uint8)',
  'function software(uint256) view returns ((address installer,uint64 requestedAt,uint64 installedAt,uint8 status,uint96 paid,address program,bytes32 checksum))',
  'function complete(uint256)',
]);

const pub = createPublicClient({ transport: http(RPC), pollingInterval: 500 });
const account = privateKeyToAccount(KEY);
const wallet = createWalletClient({ account, transport: http(RPC) });

async function tick() {
  const [releases, block] = await Promise.all([pub.readContract({ address: SLOPWARE, abi, functionName: 'releases' }), pub.getBlockNumber()]);
  // scan back from the newest specimen; stop at the first stretch of settled ones
  let settledRun = 0;
  for (let id = releases; id >= 1n && settledRun < 64; id--) {
    const s = await pub.readContract({ address: SLOPWARE, abi, functionName: 'software', args: [id] });
    if (s.status !== 1) { settledRun++; continue; }
    settledRun = 0;
    if (block <= BigInt(s.requestedAt) + 1n) continue; // entropy block not final yet
    try {
      const hash = await wallet.writeContract({ address: SLOPWARE, abi, functionName: 'complete', args: [id], chain: null, gas: 300_000n });
      const rc = await pub.waitForTransactionReceipt({ hash, pollingInterval: 500, timeout: 60_000 });
      const after = await pub.readContract({ address: SLOPWARE, abi, functionName: 'statusOf', args: [id] });
      console.log(`${new Date().toISOString()} complete(${id}) ${rc.status} → ${['none', 'installing', 'INSTALLED', 'REJECTED', 'ABANDONED'][after]} gas ${rc.gasUsed}`);
    } catch (e: any) {
      const m = String(e.shortMessage ?? e.message ?? e);
      if (!/NotInstalling/.test(m)) console.error(`complete(${id}) failed: ${m.slice(0, 160)}`);
    }
  }
}

console.log(`keeper for ${SLOPWARE} on ${RPC} as ${account.address}`);
for (;;) {
  try { await tick(); } catch (e: any) { console.error(String(e.message ?? e).slice(0, 160)); }
  await new Promise((r) => setTimeout(r, 2_000));
}
