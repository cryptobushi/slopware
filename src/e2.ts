/**
 * E2 — walks on the living. One shard: a range of parents, one arm, every walk sequential, its own anvil.
 * Protocol: slopware/experiments/E2-walks.md (§4 walk, §5 clean state per genotype, §7.1 per-walk record).
 *
 *   npx tsx src/e2.ts --arm A|B --from 0 --to 87 [--walks 5] [--attempts 10000] [--port 8600] [--out record]
 *                     [--seed E2-walks] [--parents slopware/experiments/E2/parents.json]
 *
 * Every attempt: revert the chain to the post-genesis snapshot, place the proposed child at the same address every
 * genotype gets, run probes A–E, record. Arm A accepts a step iff the full signature is unchanged; arm B iff the child
 * is instantiable and its probe-A lifespan is not shorter. For every accepted lengthening step in arm B the same
 * substitution is applied to the plateau-start genome and to the original parent (W5). Unfinished walks found in the
 * output are re-run from attempt 0 with the same stream; the analysis keeps one line per attempt.
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
const ARM = (args.arm ?? 'A') as 'A' | 'B';
if (ARM !== 'A' && ARM !== 'B') throw new Error('--arm A|B');
const DIR = 'slopware/experiments/E2';
const parentsFile = JSON.parse(readFileSync(args.parents ?? `${DIR}/parents.json`, 'utf8'));
const PARENTS: any[] = parentsFile.parents;
const FROM = Number(args.from ?? 0), TO = Math.min(Number(args.to ?? PARENTS.length - 1), PARENTS.length - 1);
const WALKS = Number(args.walks ?? 5), ATTEMPTS = Number(args.attempts ?? 10000), PORT = Number(args.port ?? 8600);
const OUT = args.out ?? 'record', SEED = args.seed ?? 'E2-walks';
const world = JSON.parse(readFileSync(`${DIR}/world-v0.json`, 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const HARNESS = { harnessVersion: 'e2-1', worldId: world.worldId, protocol: 'E2-walks.md' };
const NOVEL = new Set(['external_call', 'create_succeeds', 'child_has_code', 'loop']);

mkdirSync(`${OUT}/${ARM}`, { recursive: true });
const walksFile = `${OUT}/${ARM}/walks-${FROM}-${TO}.jsonl`;
const summariesFile = `${OUT}/${ARM}/summaries-${FROM}-${TO}.jsonl`;
const lengtheningFile = `${OUT}/${ARM}/lengthening-${FROM}-${TO}.jsonl`;
const hex = (b: Uint8Array) => ('0x' + Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')) as Hex;

// ---------------------------------------------------------------- the frozen signature (E1 §6) and behaviours
function sig(p: ProbeResult) {
  const rd = p.returnData && p.returnData !== '0x' ? keccak256(p.returnData as Hex).slice(0, 18) : '';
  return [p.outcome, p.instructionCount, p.lastOp ?? '', p.returnDataLength, rd, (p.opCounts ?? {})['SSTORE'] ?? 0, (p.opCounts ?? {})['TSTORE'] ?? 0, p.logs, p.creates, p.calls].join('|');
}
const signature = (ps: ProbeResult[]) => ps.map(sig).join('||');
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
  return r;
}
function consumedBytes(bytes: Uint8Array, probeA: ProbeResult) {
  const dis = disassemble(bytes); const n = probeA.instructionCount;
  if (n <= 0) return 1;
  if (n > dis.length) return 64;
  const last = dis[n - 1]; const len = 1 + (last.imm ? last.imm.length / 2 : 0);
  return Math.min(64, last.pc + len);
}
// which bytes of the consumed prefix are executed opcodes and which are PUSH immediates (the two prefix models, W1/W3)
function executedOpcodePositions(bytes: Uint8Array, probeA: ProbeResult): Set<number> {
  const dis = disassemble(bytes); const n = Math.min(probeA.instructionCount, dis.length); const ops = new Set<number>();
  for (let i = 0; i < n; i++) ops.add(dis[i].pc);
  return ops;
}
const kindOf = (pos: number, consumed: number, ops: Set<number>) => pos >= consumed ? 'tail' : ops.has(pos) ? 'op' : 'imm';

// ---------------------------------------------------------------- the stream (§4): keccak256(seed ‖ parent ‖ arm ‖ walk ‖ attempt)
function proposal(parentIndex: number, walk: number, attempt: number, current: Uint8Array): { pos: number; val: number } {
  const h = toBytes(keccak256(toBytes(`${SEED}|${parentIndex}|${ARM}|${walk}|${attempt}`)));
  const pos = h[0] % 64;
  const k = 1 + (((h[1] << 8) | h[2]) % 255);           // 1..255: never the current byte
  return { pos, val: (current[pos] + k) % 256 };
}

// ---------------------------------------------------------------- anvil, snapshot, revert
let anvil: ChildProcess | null = null;
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

let chain: Chain; let snap: string;
async function freshChain() { await startAnvil(); chain = await connect(`http://127.0.0.1:${PORT}`, world.callerKeyIndex); snap = await chain.request('evm_snapshot', []); }
async function clean() { const ok = await chain.request('evm_revert', [snap]); if (!ok) throw new Error('revert failed'); snap = await chain.request('evm_snapshot', []); }

// ---------------------------------------------------------------- one evaluation from the clean state (§5)
interface Evaluation { instantiable: boolean; failure: string | null; address: string | null; sig: string; life: number; consumed: number; ops: Set<number>; reach: string[]; probes: ProbeResult[] }
async function evaluate(bytes: Uint8Array): Promise<Evaluation> {
  if (bytes[0] === 0xef) return { instantiable: false, failure: 'refused: first byte 0xEF', address: null, sig: 'REFUSED', life: 0, consumed: 0, ops: new Set(), reach: [], probes: [] };
  await clean();
  const d = await deployRuntime(chain, bytes);
  if (d.status !== 'deployed' || !d.address) return { instantiable: false, failure: d.reason ?? d.status, address: null, sig: `FAILED|${d.status}`, life: 0, consumed: 0, ops: new Set(), reach: [], probes: [] };
  const ps: ProbeResult[] = [];
  for (const spec of specs) {
    try { ps.push(await probe(chain, d.address, spec)); }
    catch (e: any) { ps.push({ name: spec.name, calldata: spec.calldata, value: spec.value.toString(), outcome: 'other_halt', error: `instrument: ${String(e.message ?? e)}`, gasUsed: 0, returnData: '0x', returnDataLength: 0, ops: [], instructionCount: 0, opCounts: {}, maxDepth: 1, storageWrites: 0, storageReads: 0, logs: 0, calls: 0, creates: 0, keccaks: 0, jumps: 0, memoryOps: 0 } as any); }
  }
  const r = reaches(ps);
  // the W4 detectors: a CREATE inside a clean halt is re-sent for real; nonce and created code are read; the next clean() undoes it
  const creating = ps.find((p) => p.creates > 0 && p.outcome === 'success');
  if (creating) {
    try {
      const spec = specs.find((s) => s.name === creating.name)!;
      const hash = await chain.wallet.sendTransaction({ account: chain.wallet.account!, chain: null, to: d.address as Hex, data: spec.calldata, value: spec.value, gas: BigInt(world.gasPerCall) } as any);
      await chain.pub.waitForTransactionReceipt({ hash, timeout: 30_000 });
      const nonce = await chain.pub.getTransactionCount({ address: d.address as Hex });
      if (nonce >= 2) {
        r.add('create_succeeds');
        const code = (await chain.pub.getCode({ address: getContractAddress({ from: d.address as Hex, nonce: 1n }) })) ?? '0x';
        if (code !== '0x') r.add('child_has_code');
      }
    } catch (e: any) { r.add(`detector_error:${String(e.message ?? e).slice(0, 40)}`); }
  }
  return { instantiable: true, failure: null, address: d.address, sig: signature(ps), life: ps[0].instructionCount, consumed: consumedBytes(bytes, ps[0]), ops: executedOpcodePositions(bytes, ps[0]), reach: [...r].sort(), probes: ps };
}

// ---------------------------------------------------------------- the walk (§4)
const hamming = (a: Uint8Array, b: Uint8Array) => { let d = 0; for (let i = 0; i < 64; i++) if (a[i] !== b[i]) d++; return d; };
const done = new Set<string>();
if (existsSync(summariesFile)) for (const l of readFileSync(summariesFile, 'utf8').split('\n')) if (l.trim()) { const s = JSON.parse(l); done.add(`${s.parentIndex}|${s.walk}`); }

const t0 = Date.now(); let attemptsRun = 0;
for (let pi = FROM; pi <= TO; pi++) {
  const parent = PARENTS[pi]; const parentBytes = fromHex(parent.bytes as Hex);
  for (let w = 0; w < WALKS; w++) {
    if (done.has(`${pi}|${w}`)) continue;
    await freshChain();
    const base = await evaluate(parentBytes);
    if (!base.instantiable) throw new Error(`parent ${pi} not instantiable`);
    let cur = new Uint8Array(parentBytes), curSig = base.sig, curLife = base.life, curConsumed = base.consumed, curOps = base.ops;
    let plateau = new Uint8Array(parentBytes), plateauLife = base.life, plateauAttempt = 0, neutralSince = 0;
    const steps: [number, number][] = []; const firstReach: Record<string, number> = {}; let firstNovel: number | null = null;
    let accepted = 0, acceptedBelowPrefix = 0, acceptedOnOpcode = 0, acceptedOnImmediate = 0, predRight = 0, predRight2 = 0, maxLife = base.life; const hammingSeries: [number, number][] = [];
    const decile = new Array(10).fill(0).map(() => ({ right: 0, right2: 0, n: 0 }));
    for (let t = 1; t <= ATTEMPTS; t++) {
      const { pos, val } = proposal(pi, w, t, cur);
      const child = new Uint8Array(cur); child[pos] = val;
      const ev = await evaluate(child);
      const cls = !ev.instantiable ? 'lethal' : ev.sig === curSig ? 'neutral' : ev.life > curLife ? 'lengthened' : ev.life < curLife ? 'shortened' : 'altered';
      const kind = kindOf(pos, curConsumed, curOps);
      const predictedNeutral = pos >= curConsumed; const predictedNeutral2 = kind !== 'op'; const isNeutral = cls === 'neutral';
      if (predictedNeutral === isNeutral) predRight++; if (predictedNeutral2 === isNeutral) predRight2++;
      const dec = Math.min(9, Math.floor((t - 1) * 10 / ATTEMPTS)); decile[dec].n++; if (predictedNeutral === isNeutral) decile[dec].right++; if (predictedNeutral2 === isNeutral) decile[dec].right2++;
      const accept = ARM === 'A' ? ev.instantiable && ev.sig === curSig : ev.instantiable && ev.life >= curLife;
      for (const b of ev.reach) if (!(b in firstReach)) { firstReach[b] = t; if (NOVEL.has(b) && firstNovel === null) firstNovel = t; }
      const line: any = { p: pi, arm: ARM, w, t, pos, val, acc: accept, cls, sigH: keccak256(toBytes(ev.sig)).slice(0, 18), life: ev.life, reach: ev.reach, kind, pred: predictedNeutral, pred2: predictedNeutral2, cons: curConsumed };
      if (!ev.instantiable) line.failure = ev.failure;
      if (accept) {
        line.bytes = hex(child);
        if (pos < curConsumed) acceptedBelowPrefix++;
        if (kind === 'op') acceptedOnOpcode++; else if (kind === 'imm') acceptedOnImmediate++;
        if (ev.life > curLife) {
          // W5: the same substitution on the plateau-start genome (defines the class) and on the original parent (descriptive)
          const onPlateau = new Uint8Array(plateau); onPlateau[pos] = val; const evP = await evaluate(onPlateau);
          const onParent = new Uint8Array(parentBytes); onParent[pos] = val; const evO = await evaluate(onParent);
          const lengthensPlateau = evP.instantiable && evP.life > plateauLife;
          const rec = { p: pi, w, t, pos, val, from: curLife, to: ev.life, neutralSince, plateauAttempt, hammingFromPlateau: hamming(cur, plateau), hammingFromParent: hamming(cur, parentBytes),
            plateauLife, plateauResultLife: evP.instantiable ? evP.life : null, lengthensPlateau, cls: lengthensPlateau ? 'A' : 'B',
            parentResultLife: evO.instantiable ? evO.life : null, lengthensParent: evO.instantiable && evO.life > base.life, bytesBefore: hex(cur), bytesAfter: hex(child) };
          appendFileSync(lengtheningFile, JSON.stringify(rec) + '\n');
          steps.push([t, ev.life]); plateau = new Uint8Array(child); plateauLife = ev.life; plateauAttempt = t; neutralSince = 0;
        } else neutralSince++;
        cur = child; curSig = ev.sig; curLife = ev.life; curConsumed = ev.consumed; curOps = ev.ops; accepted++; if (ev.life > maxLife) maxLife = ev.life;
      }
      appendFileSync(walksFile, JSON.stringify(line) + '\n');
      if (t % 1000 === 0) hammingSeries.push([t, hamming(cur, parentBytes)]);
      attemptsRun++;
      if (t % 1000 === 0) { await freshChain(); }
    }
    const summary = {
      parentIndex: pi, set: parent.set, label: parent.label, arm: ARM, walk: w, parentLifespan: base.life, parentConsumed: base.consumed, budget: ATTEMPTS,
      accepted, acceptedBelowPrefix, acceptedOnOpcode, acceptedOnImmediate, finalBytes: hex(cur), finalLifespan: curLife, maxLifespan: maxLife, finalConsumed: curConsumed,
      localNeutralSteps: ARM === 'A' ? accepted : undefined, ancestralNeutral: curSig === base.sig, prefixUnchanged: hex(cur.slice(0, base.consumed)) === hex(parentBytes.slice(0, base.consumed)),
      opcodesUnchanged: [...base.ops].every((pc) => cur[pc] === parentBytes[pc]),
      hammingFromParent: hamming(cur, parentBytes), hammingSeries, steps, firstReach, firstNovel, prefixPredictorRight: predRight, opcodePredictorRight: predRight2, prefixPredictorByDecile: decile, ...HARNESS, finishedAt: new Date().toISOString(),
    };
    appendFileSync(summariesFile, JSON.stringify(summary) + '\n');
    const rate = attemptsRun / ((Date.now() - t0) / 1000);
    console.log(`  ${parent.label.padEnd(14)} ${ARM} walk ${w} · accepted ${String(accepted).padStart(5)} · life ${base.life} → ${curLife} (max ${maxLife}) · hamming ${hamming(cur, parentBytes)} · ${rate.toFixed(1)}/s`);
  }
}
console.log(`done · ${attemptsRun} attempts · ${((Date.now() - t0) / 60000).toFixed(1)} min`);
process.exit(0);
