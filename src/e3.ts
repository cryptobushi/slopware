/**
 * E3 — somewhere else. Protocol: slopware/experiments/E3-somewhere-else.md.
 *
 * Two modes, both from the same clean world state for every genotype (§6), with the retry policy of §6:
 * a probe timeout, receipt timeout, RPC error or instrumentation exception is retried up to three times from a fresh
 * revert; a placement that still fails is a HARNESS FAILURE with no signature, counted and listed, never a phenotype.
 *
 *   walks           npx tsx src/e3.ts --mode walks --from 0 --to 87 [--walks 3] [--attempts 2000] [--targets 8,16,32,48,60] --port 8700 --out record
 *                   neutral walks (E2 arm A rule); endpoints frozen at the first accepted step reaching each Hamming target
 *                   → record/walks/attempts-<from>-<to>.jsonl, record/walks/endpoints-<from>-<to>.jsonl
 *   neighbourhoods  npx tsx src/e3.ts --mode neighbourhoods --genomes <genomes.jsonl> --from i --to j --tag main|rep --port 8700 --out record [--sample N]
 *                   exhaustive one-mutant neighbourhoods of the listed genomes (16,319 placeable children each)
 *                   → record/neighbourhoods/<tag>/placements-<i>-<j>.jsonl, record/neighbourhoods/<tag>/summaries-<i>-<j>.jsonl
 *                   --sample N (smoke tests only) evaluates a seeded sample of N children instead of all; the run uses no sample.
 */
import { spawn, type ChildProcess } from 'node:child_process';
import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { getContractAddress, keccak256, toBytes, type Hex } from 'viem';
import { connect, type Chain } from './chain.js';
import { deployRuntime } from './deploy.js';
import { disassemble, fromHex } from './opcodes.js';
import { probe, standardProbes, type ProbeResult } from './probe.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const MODE = args.mode ?? 'walks';
const DIR = 'slopware/experiments/E3';
const PARENTS: any[] = JSON.parse(readFileSync(args.parents ?? 'slopware/experiments/E2/parents.json', 'utf8')).parents;
const world = JSON.parse(readFileSync(args.world ?? `${DIR}/world-v0.json`, 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const PORT = Number(args.port ?? 8700); const OUT = args.out ?? 'record'; const SEED = args.seed ?? 'E3-walks-2026-10-10';   // fixed by the pre-registration; the smoke test used 'E3-walks' (disclosed there)
const RETRIES = 3;
const HARNESS = { harnessVersion: 'e3-1', worldId: world.worldId, protocol: 'E3-somewhere-else.md' };
const hex = (b: Uint8Array) => ('0x' + Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')) as Hex;
const hamming = (a: Uint8Array, b: Uint8Array) => { let d = 0; for (let i = 0; i < 64; i++) if (a[i] !== b[i]) d++; return d; };

// ---------------------------------------------------------------- the frozen signature (E1 §6) and behaviours (E2 §3 W4 + S1)
function sig(p: ProbeResult) {
  const rd = p.returnData && p.returnData !== '0x' ? keccak256(p.returnData as Hex).slice(0, 18) : '';
  return [p.outcome, p.instructionCount, p.lastOp ?? '', p.returnDataLength, rd, (p.opCounts ?? {})['SSTORE'] ?? 0, (p.opCounts ?? {})['TSTORE'] ?? 0, p.logs, p.creates, p.calls].join('|');
}
const signature = (ps: ProbeResult[]) => ps.map(sig).join('||');
const SELF_INSPECT = ['CODESIZE', 'CODECOPY', 'ADDRESS', 'EXTCODEHASH', 'EXTCODESIZE', 'EXTCODECOPY'];
function reaches(ps: ProbeResult[]) {
  const r = new Set<string>();
  for (const p of ps) {
    if (p.outcome === 'success') r.add('clean_halt');
    if (p.outcome === 'success' && ((p.opCounts ?? {})['SSTORE'] ?? 0) > 0) r.add('write_survives');
    if (p.returnDataLength > 0) r.add('returns_data');
    if (p.creates > 0) r.add('create_executed');
    if (p.calls > 0) r.add('external_call');
    if (p.calls > 0 && (p.maxDepth ?? 1) >= 2) r.add('external_call_entered_code');
    if (p.outcome === 'out_of_gas' && p.instructionCount > 32) r.add('loop');
    if (SELF_INSPECT.some((op) => ((p.opCounts ?? {})[op] ?? 0) > 0)) r.add('self_inspection');
  }
  return r;
}

// ---------------------------------------------------------------- anvil, snapshot, revert
let anvil: ChildProcess | null = null; let chain: Chain; let snap: string;
async function startAnvil(): Promise<void> {
  if (anvil) { anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  for (let attempt = 0; attempt < 3; attempt++) {
    anvil = spawn('anvil', ['--port', String(PORT), '--hardfork', world.hardfork, '--chain-id', String(world.chainId), '--silent', '--gas-limit', '30000000'], { stdio: 'ignore' });
    for (let i = 0; i < 300; i++) {
      try { const r = await fetch(`http://127.0.0.1:${PORT}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' }); if (r.ok) return; } catch {}
      await new Promise((r) => setTimeout(r, 200));
    }
    anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error('anvil did not start');
}
process.on('exit', () => anvil?.kill('SIGKILL'));
async function freshChain() { await startAnvil(); chain = await connect(`http://127.0.0.1:${PORT}`, world.callerKeyIndex); snap = await chain.request('evm_snapshot', []); }
async function clean() { const ok = await chain.request('evm_revert', [snap]); if (!ok) throw new Error('revert failed'); snap = await chain.request('evm_snapshot', []); }

// ---------------------------------------------------------------- one evaluation from the clean state, with the retry policy (§6)
interface Evaluation { instantiable: boolean; harnessFailure: string | null; sig: string; life: number; consumed: number; ops: Set<number>; reach: string[]; detector: 'ok' | 'none' | 'unavailable'; retries: number }
const REFUSED: Evaluation = { instantiable: false, harnessFailure: null, sig: 'REFUSED', life: 0, consumed: 0, ops: new Set(), reach: [], detector: 'none', retries: 0 };
function consumedBytes(bytes: Uint8Array, probeA: ProbeResult) {
  const dis = disassemble(bytes); const n = probeA.instructionCount;
  if (n <= 0) return 1; if (n > dis.length) return 64;
  const last = dis[n - 1]; const len = 1 + (last.imm ? last.imm.length / 2 : 0); return Math.min(64, last.pc + len);
}
function executedOpcodePositions(bytes: Uint8Array, probeA: ProbeResult): Set<number> {
  const dis = disassemble(bytes); const n = Math.min(probeA.instructionCount, dis.length); const ops = new Set<number>();
  for (let i = 0; i < n; i++) ops.add(dis[i].pc); return ops;
}
async function evaluateOnce(bytes: Uint8Array): Promise<Evaluation> {
  await clean();
  const d = await deployRuntime(chain, bytes);
  if (d.status === 'error') throw new Error(`deploy: ${d.reason}`);                      // instrument error → retry
  if (d.status !== 'deployed' || !d.address) return { ...REFUSED, sig: `FAILED|${d.status}`, reach: [] }; // a program-level failure to place, not an instrument error
  const ps: ProbeResult[] = [];
  for (const spec of specs) ps.push(await probe(chain, d.address, spec));              // a throwing probe propagates → retry
  const r = reaches(ps); let detector: Evaluation['detector'] = 'none';
  const creating = ps.find((p) => p.creates > 0 && p.outcome === 'success');
  if (creating) {
    detector = 'unavailable';
    for (let t = 0; t <= RETRIES; t++) {
      try {
        const spec = specs.find((s) => s.name === creating.name)!;
        const hash = await chain.wallet.sendTransaction({ account: chain.wallet.account!, chain: null, to: d.address as Hex, data: spec.calldata, value: spec.value, gas: BigInt(world.gasPerCall) } as any);
        await chain.pub.waitForTransactionReceipt({ hash, timeout: 90_000 });
        const nonce = await chain.pub.getTransactionCount({ address: d.address as Hex });
        if (nonce >= 2) { r.add('create_succeeds'); const code = (await chain.pub.getCode({ address: getContractAddress({ from: d.address as Hex, nonce: 1n }) })) ?? '0x'; if (code !== '0x') r.add('child_has_code'); }
        detector = 'ok'; break;
      } catch { /* retry the detector only; the phenotype is already measured */ }
    }
  }
  return { instantiable: true, harnessFailure: null, sig: signature(ps), life: ps[0].instructionCount, consumed: consumedBytes(bytes, ps[0]), ops: executedOpcodePositions(bytes, ps[0]), reach: [...r].sort(), detector, retries: 0 };
}
let harnessFailures = 0, retriesTotal = 0;
async function evaluate(bytes: Uint8Array): Promise<Evaluation> {
  if (bytes[0] === 0xef) return REFUSED;
  let lastErr = '';
  for (let t = 0; t <= RETRIES; t++) {
    try { const e = await evaluateOnce(bytes); e.retries = t; retriesTotal += t; return e; }
    catch (err: any) { lastErr = String(err.message ?? err).slice(0, 120); if (t < RETRIES) { try { await freshChain(); } catch {} } }
  }
  harnessFailures++;
  return { instantiable: false, harnessFailure: lastErr, sig: 'HARNESS_FAILURE', life: 0, consumed: 0, ops: new Set(), reach: [], detector: 'none', retries: RETRIES };
}
const classify = (ev: Evaluation, curSig: string, curLife: number) => !ev.instantiable ? (ev.harnessFailure ? 'harness_failure' : 'lethal') : ev.sig === curSig ? 'neutral' : ev.life > curLife ? 'lengthened' : ev.life < curLife ? 'shortened' : 'altered';

// ---------------------------------------------------------------- mode: walks (§4)
async function runWalks() {
  const FROM = Number(args.from ?? 0), TO = Math.min(Number(args.to ?? PARENTS.length - 1), PARENTS.length - 1);
  const WALKS = Number(args.walks ?? 3), ATTEMPTS = Number(args.attempts ?? 2000);
  const TARGETS = (args.targets ?? '8,16,32,48,60').split(',').map(Number);
  mkdirSync(`${OUT}/walks`, { recursive: true });
  const attemptsFile = `${OUT}/walks/attempts-${FROM}-${TO}.jsonl`, endpointsFile = `${OUT}/walks/endpoints-${FROM}-${TO}.jsonl`;
  const done = new Set<string>();
  if (existsSync(endpointsFile)) for (const l of readFileSync(endpointsFile, 'utf8').split('\n')) if (l.trim()) { const e = JSON.parse(l); if (e.target === 'end') done.add(`${e.parentIndex}|${e.walk}`); }
  const t0 = Date.now(); let n = 0;
  for (let pi = FROM; pi <= TO; pi++) {
    const parent = PARENTS[pi]; const pb = fromHex(parent.bytes as Hex);
    for (let w = 0; w < WALKS; w++) {
      if (done.has(`${pi}|${w}`)) continue;
      await freshChain();
      const base = await evaluate(pb); if (!base.instantiable) throw new Error(`parent ${pi} not instantiable or harness failure: ${base.harnessFailure}`);
      let cur = new Uint8Array(pb), accepted = 0; const reached = new Set<number>();
      for (let t = 1; t <= ATTEMPTS && reached.size < TARGETS.length; t++) {
        const h = toBytes(keccak256(toBytes(`${SEED}|${pi}|${w}|${t}`)));
        const pos = h[0] % 64, val = (cur[pos] + 1 + (((h[1] << 8) | h[2]) % 255)) % 256;
        const child = new Uint8Array(cur); child[pos] = val;
        const ev = await evaluate(child); n++;
        const cls = classify(ev, base.sig, base.life); const acc = ev.instantiable && ev.sig === base.sig;   // arm A: full signature equals the PARENT's (ancestral) signature, which equals the current one by induction
        appendFileSync(attemptsFile, JSON.stringify({ p: pi, w, t, pos, val, acc, cls, sigH: keccak256(toBytes(ev.sig)).slice(0, 18), life: ev.life, retries: ev.retries, ...(ev.harnessFailure ? { harnessFailure: ev.harnessFailure } : {}), ...(acc ? { bytes: hex(child) } : {}) }) + '\n');
        if (acc) {
          cur = child; accepted++;
          const d = hamming(cur, pb);
          for (const target of TARGETS) if (!reached.has(target) && d >= target) {
            reached.add(target);
            appendFileSync(endpointsFile, JSON.stringify({ parentIndex: pi, set: parent.set, label: parent.label, walk: w, target, attempt: t, acceptedSteps: accepted, hamming: d, bytes: hex(cur), signature: ev.sig, ancestralNeutral: ev.sig === base.sig, ...HARNESS }) + '\n');
          }
        }
      }
      appendFileSync(endpointsFile, JSON.stringify({ parentIndex: pi, walk: w, target: 'end', attempts: Math.min(ATTEMPTS, n), accepted, targetsReached: [...reached].sort((a, b) => a - b), finalBytes: hex(cur), finalHamming: hamming(cur, pb), harnessFailures, retriesTotal }) + '\n');
      console.log(`  ${parent.label.padEnd(14)} walk ${w} · accepted ${accepted} · targets ${[...reached].sort((a, b) => a - b).join(',')} · ${(n / ((Date.now() - t0) / 1000)).toFixed(1)}/s · harness failures ${harnessFailures} · retries ${retriesTotal}`);
    }
  }
  console.log(`walks done · ${n} attempts · harness failures ${harnessFailures} · retries ${retriesTotal}`);
}

// ---------------------------------------------------------------- mode: neighbourhoods (§2, §5.2)
async function runNeighbourhoods() {
  const genomes = readFileSync(args.genomes, 'utf8').split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
  const FROM = Number(args.from ?? 0), TO = Math.min(Number(args.to ?? genomes.length - 1), genomes.length - 1), TAG = args.tag ?? 'main';
  const SAMPLE = args.sample ? Number(args.sample) : 0;
  mkdirSync(`${OUT}/neighbourhoods/${TAG}`, { recursive: true });
  const placementsFile = `${OUT}/neighbourhoods/${TAG}/placements-${FROM}-${TO}.jsonl`, summariesFile = `${OUT}/neighbourhoods/${TAG}/summaries-${FROM}-${TO}.jsonl`;
  const done = new Set<string>();
  if (existsSync(summariesFile)) for (const l of readFileSync(summariesFile, 'utf8').split('\n')) if (l.trim()) done.add(JSON.parse(l).genomeId);
  const t0 = Date.now(); let n = 0;
  for (let gi = FROM; gi <= TO; gi++) {
    const g = genomes[gi]; if (done.has(g.genomeId)) continue;
    const gb = fromHex(g.bytes as Hex);
    await freshChain();
    const self = await evaluate(gb); if (!self.instantiable) { appendFileSync(summariesFile, JSON.stringify({ genomeId: g.genomeId, ...g, selfFailure: self.harnessFailure ?? self.sig }) + '\n'); continue; }
    const counts: Record<string, number> = { neutral: 0, altered: 0, lengthened: 0, shortened: 0, lethal: 0, harness_failure: 0 };
    const sigs = new Map<string, number>(); let upward = 0; const reachCounts: Record<string, number> = {}; let detectorUnavailable = 0;
    // children: every position, every other value; or (smoke only) a seeded sample
    const children: [number, number][] = [];
    for (let pos = 0; pos < 64; pos++) for (let val = 0; val < 256; val++) if (val !== gb[pos]) children.push([pos, val]);
    let list = children;
    if (SAMPLE) { const h = (i: number) => parseInt(keccak256(toBytes(`${g.genomeId}|${i}`)).slice(2, 10), 16); list = children.map((c, i) => [c, h(i)] as const).sort((a, b) => a[1] - b[1]).slice(0, SAMPLE).map((x) => x[0]); }
    for (const [pos, val] of list) {
      const child = new Uint8Array(gb); child[pos] = val;
      const ev = await evaluate(child); n++;
      const cls = classify(ev, self.sig, self.life); counts[cls]++;
      if (ev.instantiable) { sigs.set(ev.sig, (sigs.get(ev.sig) ?? 0) + 1); if (ev.life > self.life) upward++; for (const b of ev.reach) reachCounts[b] = (reachCounts[b] ?? 0) + 1; if (ev.detector === 'unavailable') detectorUnavailable++; }
      appendFileSync(placementsFile, JSON.stringify({ g: g.genomeId, pos, val, cls, sigH: ev.instantiable ? keccak256(toBytes(ev.sig)).slice(0, 18) : null, life: ev.life, reach: ev.reach.length ? ev.reach : undefined, det: ev.detector === 'unavailable' ? 'u' : undefined, r: ev.retries || undefined, hf: ev.harnessFailure ?? undefined }) + '\n');
    }
    const placeable = list.length - (list.some(([p, v]) => p === 0 && v === 0xef) ? 1 : 0);
    appendFileSync(summariesFile, JSON.stringify({ genomeId: g.genomeId, ...g, selfSignature: self.sig, selfLifespan: self.life, selfConsumed: self.consumed, selfOps: [...self.ops].sort((a, b) => a - b), children: list.length, placeable, counts, distinctSignatures: sigs.size, upward, reachCounts, detectorUnavailable, sampled: SAMPLE || undefined, signatureHistogram: [...sigs.entries()].map(([s, c]) => [keccak256(toBytes(s)).slice(0, 18), c]), ...HARNESS, finishedAt: new Date().toISOString() }) + '\n');
    console.log(`  ${String(g.genomeId).padEnd(36)} ${TAG} · neutral ${(100 * counts.neutral / placeable).toFixed(1)}% · distinct sigs ${sigs.size} · upward ${upward} · hf ${counts.harness_failure} · ${(n / ((Date.now() - t0) / 1000)).toFixed(1)}/s`);
  }
  console.log(`neighbourhoods done · ${n} placements · harness failures ${harnessFailures} · retries ${retriesTotal}`);
}

if (MODE === 'walks') await runWalks(); else if (MODE === 'neighbourhoods') await runNeighbourhoods(); else throw new Error('--mode walks|neighbourhoods');
process.exit(0);
