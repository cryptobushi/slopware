/**
 * E1 §7.6: replicate an H5 candidate on fresh chains before it is reported as anything but a candidate.
 *
 *   npx tsx src/e1-replicate.ts --bytes 0x<64 bytes> [--times 3] [--port 8590] [--persist]
 *
 * Each replicate starts its own anvil under world v0, places the child, runs the five probes exactly as the run did,
 * and prints the signature, the behaviours reached, and the traced ops of any probe that executed CREATE.
 * With --persist, one real transaction is also sent (exploratory, outside the protocol) so a CREATE actually
 * commits, and the code at the would-be grandchild's address is read back.
 */
import { spawn, type ChildProcess } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { getContractAddress, keccak256, type Hex } from 'viem';
import { connect } from './chain.js';
import { deployRuntime } from './deploy.js';
import { fromHex } from './opcodes.js';
import { probe, standardProbes, type ProbeResult } from './probe.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i++) { const a = process.argv[i]; if (a.startsWith('--')) { const v = process.argv[i + 1]; if (v && !v.startsWith('--')) { args[a.slice(2)] = v; i++; } else args[a.slice(2)] = 'true'; } }
const BYTES = fromHex(args.bytes as Hex);
if (BYTES.length !== 64) throw new Error('--bytes must be 64 bytes');
const TIMES = Number(args.times ?? 3); const PORT = Number(args.port ?? 8590);
const world = JSON.parse(readFileSync('slopware/experiments/E1/world-v0.json', 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));

function sig(p: ProbeResult) {
  const rd = p.returnData && p.returnData !== '0x' ? keccak256(p.returnData as Hex).slice(0, 18) : '';
  return [p.outcome, p.instructionCount, p.lastOp ?? '', p.returnDataLength, rd, (p.opCounts ?? {})['SSTORE'] ?? 0, (p.opCounts ?? {})['TSTORE'] ?? 0, p.logs, p.creates, p.calls].join('|');
}
function reaches(ps: ProbeResult[]) {
  const r = new Set<string>();
  for (const p of ps) {
    if (p.outcome === 'success') r.add('clean_halt');
    if (p.outcome === 'success' && ((p.opCounts ?? {})['SSTORE'] ?? 0) > 0) r.add('write_survives');
    if (p.returnDataLength > 0) r.add('returns_data');
    if (p.creates > 0) r.add('create_executed');
    if (p.creates > 0 && p.outcome === 'success') r.add('child_may_exist');
    if (p.calls > 0) r.add('external_call');
    if (p.outcome === 'out_of_gas') r.add('out_of_gas');
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
  } finally { anvil.kill('SIGKILL'); }
}

console.log(`replicating ${args.bytes} · ${TIMES} fresh chains · world ${world.worldId.slice(0, 10)}…`);
const sigs: string[] = [];
for (let t = 0; t < TIMES; t++) {
  const out = await withAnvil(PORT + t, async (rpc) => {
    const chain = await connect(rpc, world.callerKeyIndex);
    const d = await deployRuntime(chain, BYTES);
    if (d.status !== 'deployed' || !d.address) return { failure: d.reason ?? d.status };
    const ps: ProbeResult[] = [];
    for (const spec of specs) ps.push(await probe(chain, d.address, spec));
    const result: any = { address: d.address, signature: ps.map(sig).join('||'), reaches: reaches(ps), probes: ps.map((p) => ({ name: p.name, outcome: p.outcome, instructions: p.instructionCount, creates: p.creates, calls: p.calls, gasUsed: p.gasUsed, ops: p.ops })) };
    if (args.persist) {
      // exploratory: commit the CREATE for real and look for the grandchild. A contract's nonce starts at 1 (EIP-161) and a
      // CREATE that proceeds increments it, so childNonceAfter === 1 means the creation failed before it began.
      const creating = ps.find((p) => p.creates > 0 && p.outcome === 'success') ?? ps[0];
      const spec = specs.find((s) => s.name === creating.name)!;
      const hash = await chain.wallet.sendTransaction({ account: chain.wallet.account!, chain: null, to: d.address as Hex, data: spec.calldata, value: spec.value, gas: BigInt(world.gasPerCall) } as any);
      const rc = await chain.pub.waitForTransactionReceipt({ hash });
      const grandchild = getContractAddress({ from: d.address as Hex, nonce: 1n });
      const code = (await chain.pub.getCode({ address: grandchild })) ?? '0x';
      const nonce = await chain.pub.getTransactionCount({ address: d.address as Hex });
      result.persist = { probe: creating.name, txStatus: rc.status, gasUsed: Number(rc.gasUsed), childNonceAfter: nonce, grandchild, grandchildCode: code, grandchildCodeBytes: (code.length - 2) / 2 };
    }
    return result;
  });
  if ('failure' in out) { console.log(`#${t + 1} placement failed: ${out.failure}`); continue; }
  sigs.push(out.signature);
  console.log(`#${t + 1} ${out.address} · reaches ${out.reaches.join(', ')}`);
  for (const p of out.probes) if (p.creates > 0 || t === 0) console.log(`   ${p.name.padEnd(18)} ${p.outcome.padEnd(16)} ${String(p.instructions).padStart(3)} instr · creates ${p.creates} · calls ${p.calls} · gas ${p.gasUsed}${p.creates > 0 ? `\n      ops: ${p.ops.join(' · ')}` : ''}`);
  if (out.persist) console.log(`   persist: ${JSON.stringify(out.persist)}`);
}
console.log(`signatures identical across replicates: ${new Set(sigs).size === 1 && sigs.length === TIMES}`);
