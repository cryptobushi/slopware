/** E4 §6 investigation: re-evaluate the 23 first-divergent genomes through the real harness path (e4.ts evaluateOnce),
 *  several times on one anvil (revert between) and again on a restarted anvil; report signature stability and executed env opcodes. */
import { spawn, type ChildProcess } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { keccak256, toBytes, type Hex } from 'viem';
import { connect, type Chain } from '../src/chain.js';
import { deployRuntime } from '../src/deploy.js';
import { fromHex } from '../src/opcodes.js';
import { probe, standardProbes, type ProbeResult } from '../src/probe.js';
const world = JSON.parse(readFileSync('slopware/experiments/E4/world-v0.json', 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const PORT = Number(process.env.PORT ?? 8900); const N = Number(process.env.N ?? 3);
const items = JSON.parse(readFileSync(process.argv[2], 'utf8')) as any[];
function sig(p: ProbeResult) { const rd = p.returnData && p.returnData !== '0x' ? keccak256(p.returnData as Hex).slice(0, 18) : ''; return [p.outcome, p.instructionCount, p.lastOp ?? '', p.returnDataLength, rd, (p.opCounts ?? {})['SSTORE'] ?? 0, (p.opCounts ?? {})['TSTORE'] ?? 0, p.logs, p.creates, p.calls].join('|'); }
const ENV = new Set(['TIMESTAMP','PREVRANDAO','DIFFICULTY','BLOCKHASH','NUMBER','GASPRICE','BASEFEE','COINBASE','BLOBBASEFEE','BLOBHASH','GASLIMIT','CHAINID','SELFBALANCE','BALANCE','ORIGIN','GAS','CALLER','ADDRESS','CALLVALUE','EXTCODEHASH','EXTCODESIZE']);
let anvil: ChildProcess | null = null; let chain: Chain; let snap: string;
async function startAnvil() {
  if (anvil) { anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  anvil = spawn('anvil', ['--port', String(PORT), '--hardfork', world.hardfork, '--chain-id', String(world.chainId), '--silent', '--gas-limit', '30000000'], { stdio: 'ignore' });
  for (let i = 0; i < 300; i++) { try { const r = await fetch(`http://127.0.0.1:${PORT}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' }); if (r.ok) break; } catch {} await new Promise((r) => setTimeout(r, 200)); }
  chain = await connect(`http://127.0.0.1:${PORT}`, world.callerKeyIndex); snap = await chain.request('evm_snapshot', []);
}
async function clean() { const ok = await chain.request('evm_revert', [snap]); if (!ok) throw new Error('revert failed'); snap = await chain.request('evm_snapshot', []); }
async function evalOnce(bytes: Uint8Array) {
  await clean(); const d = await deployRuntime(chain, bytes); if (d.status !== 'deployed' || !d.address) return { s: `FAILED|${d.status}`, ps: [] as ProbeResult[] };
  const ps: ProbeResult[] = []; for (const spec of specs) ps.push(await probe(chain, d.address, spec)); return { s: ps.map(sig).join('||'), ps };
}
process.on('exit', () => anvil?.kill('SIGKILL'));
await startAnvil();
const blk = await chain.request('eth_getBlockByNumber', ['latest', false]);
console.log(`anvil latest block ${Number(blk.number)} timestamp ${Number(blk.timestamp)} mixHash ${blk.mixHash} baseFee ${blk.baseFeePerGas}`);
for (const it of items) {
  const bytes = fromHex(it.genome as Hex); const seen = new Map<string, number>(); const envOps = new Set<string>(); const variants: string[][] = [];
  for (let round = 0; round < 2; round++) {
    if (round === 1) await startAnvil();
    for (let i = 0; i < N; i++) {
      const { s, ps } = await evalOnce(bytes); const h = keccak256(toBytes(s)).slice(0, 18);
      seen.set(h, (seen.get(h) ?? 0) + 1);
      for (const p of ps) for (const k of Object.keys(p.opCounts ?? {})) if (ENV.has(k)) envOps.add(k);
      if (!variants.some((v) => v[0] === h)) variants.push([h, s]);
    }
  }
  const match = (h: string) => h === it.run.h ? 'RUN' : h === it.second.h ? 'SECOND' : 'NEW';
  console.log(`${it.pop} g${it.g} s${it.slot} val ${it.mut.val}: hashes ${[...seen].map(([h, c]) => `${h}×${c}(${match(h)})`).join(' ')} · env ops ${[...envOps].join(',') || '-'}`);
  if (variants.length > 1) {
    const a = variants[0][1].split('||'), b = variants[1][1].split('||');
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) console.log(`    probe ${i}: ${a[i]}\n           vs ${b[i]}`);
  }
}
anvil?.kill('SIGKILL');
