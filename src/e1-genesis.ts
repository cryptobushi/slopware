/**
 * E1 — snapshot the genesis set, generate the control set, and freeze world v0.
 *
 *   npx tsx src/e1-genesis.ts --rpc https://ethereum-rpc.publicnode.com --contract 0x… --out slopware/experiments/E1
 *
 * Read-only against the public chain. Writes:
 *   genesis.json   every installer release requested at or before the snapshot block, with its 64 bytes
 *   controls.json  one fresh 64-byte genome per genesis genome, from the seeded stream "E1-control"
 *   world-v0.json  the frozen environment: probe payloads from "E1-world-v0", gas, hardfork; worldId = keccak of it
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { createPublicClient, http, keccak256, parseAbi, toBytes, type Hex } from 'viem';
import { seededRng } from './rng.js';
import { PROBE_GAS } from './probe.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const RPC = args.rpc ?? 'https://ethereum-rpc.publicnode.com';
const CONTRACT = args.contract as Hex;
const OUT = args.out ?? 'slopware/experiments/E1';
if (!/^0x[0-9a-fA-F]{40}$/.test(CONTRACT ?? '')) { console.error('--contract required'); process.exit(2); }

const abi = parseAbi([
  'function releases() view returns (uint256)',
  'function software(uint256) view returns ((address installer,uint64 requestedAt,uint64 installedAt,uint8 status,uint96 paid,address program,bytes32 checksum))',
  'function bytecodeOf(uint256) view returns (bytes)',
]);
const MULTICALL3 = '0xcA11bde05977b3631167028862bE2a173976CA11' as Hex;
const hex = (b: Uint8Array) => `0x${Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')}` as Hex;

const pub = createPublicClient({ transport: http(RPC) });
const snapshotBlock = await pub.getBlockNumber();
const releases = Number(await pub.readContract({ address: CONTRACT, abi, functionName: 'releases', blockNumber: snapshotBlock }));
console.log(`snapshot block ${snapshotBlock} · ${releases} releases`);

const ids = Array.from({ length: releases }, (_, i) => BigInt(i + 1));
const chunk = <T,>(a: T[], n: number) => Array.from({ length: Math.ceil(a.length / n) }, (_, i) => a.slice(i * n, (i + 1) * n));
const genomes: any[] = [];
for (const part of chunk(ids, 200)) {
  const sw = await pub.multicall({ contracts: part.map((id) => ({ address: CONTRACT, abi, functionName: 'software', args: [id] })), multicallAddress: MULTICALL3, blockNumber: snapshotBlock });
  const bc = await pub.multicall({ contracts: part.map((id) => ({ address: CONTRACT, abi, functionName: 'bytecodeOf', args: [id] })), multicallAddress: MULTICALL3, blockNumber: snapshotBlock });
  part.forEach((id, i) => {
    const s: any = sw[i].status === 'success' ? sw[i].result : null;
    const bytes = bc[i].status === "success" ? (bc[i].result as unknown as Hex) : ("0x" as Hex);
    if (!s) return;
    const status = ['none', 'installing', 'installed', 'rejected', 'abandoned'][s.status];
    if (status !== 'installed' && status !== 'rejected') { console.log(`  release ${id} is ${status} at the snapshot; excluded`); return; }
    genomes.push({ release: Number(id), status, installer: s.installer, program: status === 'installed' ? s.program : null, requestedAt: Number(s.requestedAt), bytes, genotypeId: keccak256(bytes), instantiable: status === 'installed' });
  });
}
mkdirSync(OUT, { recursive: true });
writeFileSync(`${OUT}/genesis.json`, JSON.stringify({ experiment: 'E1', snapshotBlock: Number(snapshotBlock), contract: CONTRACT, count: genomes.length, genomes }, null, 1));
console.log(`genesis.json: ${genomes.length} genomes (${genomes.filter((g) => !g.instantiable).length} refused)`);

const rng = seededRng('E1-control');
const controls = genomes.map((_, i) => { const b = rng.bytes(64); const h = hex(b); return { index: i, bytes: h, genotypeId: keccak256(h), instantiable: b[0] !== 0xef }; });
writeFileSync(`${OUT}/controls.json`, JSON.stringify({ experiment: 'E1', seed: 'E1-control', count: controls.length, genomes: controls }, null, 1));
console.log(`controls.json: ${controls.length} genomes (${controls.filter((g) => !g.instantiable).length} begin with 0xef)`);

const w = seededRng('E1-world-v0');
const world = {
  name: 'world v0', chain: 'anvil', hardfork: 'osaka', chainId: 31337, state: 'fresh per batch', loader: '0x604080600b6000396000f3',
  gasPerCall: PROBE_GAS, callerKeyIndex: 9, tracer: 'debug_traceCall structLogs, stack disabled',
  probes: { random32: hex(w.bytes(32)), selector: hex(w.bytes(4)), arg32: hex(w.bytes(32)), payloadSeed: 'E1-world-v0' },
};
const worldId = keccak256(toBytes(JSON.stringify(world)));
writeFileSync(`${OUT}/world-v0.json`, JSON.stringify({ worldId, ...world }, null, 1));
console.log(`world-v0.json: ${worldId}`);
process.exit(0);
