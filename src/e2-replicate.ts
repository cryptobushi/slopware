/**
 * E2 §7.5: replicate W4 events three times on fresh chains before they are reported as anything but candidates.
 *
 *   npx tsx src/e2-replicate.ts --candidates <w4-candidates.json> --out <replications.jsonl> [--times 3] [--port 8650]
 *
 * For each candidate genome: three separate anvil processes under world v0; place, run probes A–E, record the signature,
 * the behaviours reached, and for external_call whether any probe entered a callee frame (maxDepth >= 2), which is the
 * harness's only witness that the call reached code. A candidate replicates if all three runs reach the same event.
 */
import { spawn, type ChildProcess } from 'node:child_process';
import { appendFileSync, readFileSync } from 'node:fs';
import { keccak256, type Hex } from 'viem';
import { connect } from './chain.js';
import { deployRuntime } from './deploy.js';
import { fromHex } from './opcodes.js';
import { probe, standardProbes, type ProbeResult } from './probe.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const cands: any[] = JSON.parse(readFileSync(args.candidates, 'utf8'));
const OUT = args.out; const TIMES = Number(args.times ?? 3); const PORT = Number(args.port ?? 8650);
const world = JSON.parse(readFileSync('slopware/experiments/E2/world-v0.json', 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));

function sig(p: ProbeResult) {
  const rd = p.returnData && p.returnData !== '0x' ? keccak256(p.returnData as Hex).slice(0, 18) : '';
  return [p.outcome, p.instructionCount, p.lastOp ?? '', p.returnDataLength, rd, (p.opCounts ?? {})['SSTORE'] ?? 0, (p.opCounts ?? {})['TSTORE'] ?? 0, p.logs, p.creates, p.calls].join('|');
}
function reaches(ps: ProbeResult[]) {
  const r = new Set<string>();
  for (const p of ps) {
    if (p.outcome === 'success') r.add('clean_halt');
    if (p.returnDataLength > 0) r.add('returns_data');
    if (p.creates > 0) r.add('create_executed');
    if (p.calls > 0) r.add('external_call');
    if (p.calls > 0 && (p.maxDepth ?? 1) >= 2) r.add('external_call_entered_code');
    if (p.outcome === 'out_of_gas' && p.instructionCount > 32) r.add('loop');
  }
  return [...r].sort();
}
async function withAnvil<T>(port: number, f: (rpc: string) => Promise<T>): Promise<T> {
  const anvil: ChildProcess = spawn('anvil', ['--port', String(port), '--hardfork', world.hardfork, '--chain-id', String(world.chainId), '--silent', '--gas-limit', '30000000'], { stdio: 'ignore' });
  try {
    for (let i = 0; i < 300; i++) {
      try { const r = await fetch(`http://127.0.0.1:${port}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' }); if (r.ok) break; } catch {}
      await new Promise((r) => setTimeout(r, 200));
    }
    return await f(`http://127.0.0.1:${port}`);
  } finally { anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 200)); }
}

let n = 0, replicated = 0;
for (const c of cands) {
  const runs: any[] = [];
  for (let t = 0; t < TIMES; t++) {
    runs.push(await withAnvil(PORT + (t % 4), async (rpc) => {
      const chain = await connect(rpc, world.callerKeyIndex);
      const d = await deployRuntime(chain, fromHex(c.bytes));
      if (d.status !== 'deployed' || !d.address) return { failure: d.reason ?? d.status };
      const ps: ProbeResult[] = []; for (const spec of specs) ps.push(await probe(chain, d.address, spec));
      return { signature: ps.map(sig).join('||'), reaches: reaches(ps), maxDepth: Math.max(...ps.map((p) => p.maxDepth ?? 1)), calls: ps.map((p) => p.calls) };
    }));
  }
  const ok = runs.every((r) => !r.failure && r.reaches.includes(c.event));
  const same = new Set(runs.map((r) => r.signature ?? 'fail')).size === 1;
  if (ok) replicated++;
  appendFileSync(OUT, JSON.stringify({ ...c, replicated: ok, signaturesIdentical: same, enteredCode: runs.every((r) => r.reaches?.includes('external_call_entered_code')), runs }) + '\n');
  n++; if (n % 20 === 0) console.log(`${n}/${cands.length} · replicated ${replicated}`);
}
console.log(`done · ${n} candidates · ${replicated} replicated 3/3 → ${OUT}`);
process.exit(0);
