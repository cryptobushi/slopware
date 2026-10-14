/** Rolling-map pilot: prove the PILOT world's determinism before anything runs under it.
 *  The pilot world (slopware/pilots/rolling-map/world-pilot.json) differs from world v0 in exactly the ways needed to freeze the
 *  block context: anvil is started with a fixed genesis timestamp, nothing is ever mined (the program is placed with anvil_setCode
 *  at a fixed address instead of a deployment transaction), and every probe is a debug_traceCall against block 0. So TIMESTAMP,
 *  NUMBER, PREVRANDAO (genesis: zero), BLOCKHASH (genesis hash, a function of the fixed genesis), BASEFEE, GASPRICE, COINBASE,
 *  GASLIMIT, CHAINID and ADDRESS are constants of the world file.
 *  Test: the genomes in <genomes.json> (the 23 E4 genomes that read TIMESTAMP / PREVRANDAO / BLOCKHASH and evaluated differently
 *  on two machines, from E4 Amendment 6) are evaluated R times on each of N fresh anvil instances started seconds apart; identical
 *  signatures everywhere is the pass condition. Also prints the block-context the world exposes.
 *  usage: npx tsx scripts/pilot_world_test.ts <world-pilot.json> <genomes.json> [instances=3] [repeats=3] [port=8950] */
import { spawn, type ChildProcess } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { keccak256, toBytes, type Hex } from 'viem';
import { connect, type Chain } from '../src/chain.js';
import { fromHex } from '../src/opcodes.js';
import { probe, standardProbes, type ProbeResult } from '../src/probe.js';
const [,, worldFile, genomesFile, inst = '3', reps = '3', port = '8950'] = process.argv;
const world = JSON.parse(readFileSync(worldFile, 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const items = JSON.parse(readFileSync(genomesFile, 'utf8')) as any[];
const PORT = Number(port); const ADDR = world.programAddress as Hex;
function sig(p: ProbeResult) { const rd = p.returnData && p.returnData !== '0x' ? keccak256(p.returnData as Hex).slice(0, 18) : ''; return [p.outcome, p.instructionCount, p.lastOp ?? '', p.returnDataLength, rd, (p.opCounts ?? {})['SSTORE'] ?? 0, (p.opCounts ?? {})['TSTORE'] ?? 0, p.logs, p.creates, p.calls].join('|'); }
let anvil: ChildProcess | null = null; let chain: Chain;
async function startAnvil() {
  if (anvil) { anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  anvil = spawn('anvil', ['--port', String(PORT), '--hardfork', world.hardfork, '--chain-id', String(world.chainId), '--silent', '--gas-limit', String(world.blockGasLimit), '--timestamp', String(world.genesisTimestamp), '--no-mining', '--base-fee', String(world.baseFee), '--gas-price', String(world.gasPrice)], { stdio: 'ignore' });
  for (let i = 0; i < 300; i++) { try { const r = await fetch(`http://127.0.0.1:${PORT}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' }); if (r.ok) break; } catch {} await new Promise((r) => setTimeout(r, 200)); }
  chain = await connect(`http://127.0.0.1:${PORT}`, world.callerKeyIndex);
}
async function place(bytes: Uint8Array) { await chain.request('anvil_setCode', [ADDR, '0x' + Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')]); }
async function evaluate(bytes: Uint8Array) { await place(bytes); const ps: ProbeResult[] = []; for (const s of specs) ps.push(await probe(chain, ADDR, s)); return { s: ps.map(sig).join('||'), ps }; }
process.on('exit', () => anvil?.kill('SIGKILL'));
// a tiny context-reading program for the report: returns TIMESTAMP ‖ NUMBER ‖ PREVRANDAO ‖ BLOCKHASH(0) ‖ BASEFEE ‖ GASPRICE ‖ COINBASE ‖ GASLIMIT ‖ CHAINID ‖ ADDRESS ‖ CALLER ‖ SELFBALANCE
const CTX = fromHex(('0x42600052436020524460405260004060605248608052' + '3a60a052' + '4160c052' + '4560e052' + '4661010052' + '3061012052' + '3361014052' + '4761016052' + '6101806000f3') as Hex);
const results = new Map<string, Set<string>>(); const ctxSeen = new Set<string>();
const N = Number(inst), R = Number(reps);
for (let i = 0; i < N; i++) {
  if (i) await new Promise((r) => setTimeout(r, 3000));
  await startAnvil();
  const blk = await chain.request('eth_getBlockByNumber', ['latest', false]);
  const ctx = await evaluate(CTX); ctxSeen.add(ctx.ps[0].returnData);
  console.log(`instance ${i + 1}: block ${Number(blk.number)} timestamp ${Number(blk.timestamp)} hash ${blk.hash.slice(0, 18)} mixHash ${blk.mixHash.slice(0, 18)} · context program returns ${ctx.ps[0].returnData.slice(0, 66)}…`);
  for (const it of items) for (let r = 0; r < R; r++) { const { s } = await evaluate(fromHex(it.genome)); (results.get(it.pop) ?? results.set(it.pop, new Set()).get(it.pop)!).add(keccak256(toBytes(s)).slice(0, 18)); }
}
let bad = 0;
for (const it of items) { const hs = results.get(it.pop)!; const ok = hs.size === 1; if (!ok) bad++; console.log(`${it.pop}: ${ok ? 'identical' : 'DIFFERS'} ${[...hs].join(' ')} (E4 run ${it.run.h}, second ${it.second.h})`); }
console.log(`context program: ${ctxSeen.size === 1 ? 'identical return data across instances' : 'RETURN DATA DIFFERS ACROSS INSTANCES'}`);
console.log(`${items.length - bad} of ${items.length} genomes identical across ${N} instances × ${R} evaluations · ${bad ? 'FAIL' : 'PASS'}`);
anvil?.kill('SIGKILL'); process.exit(bad || ctxSeen.size !== 1 ? 1 : 0);
