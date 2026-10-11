/**
 * E4 — after. Protocol: slopware/experiments/E4-after.md. Design: E4-design.md.
 *
 * One mode: population search from a founder under the frozen rules (§5), every genotype evaluated from the same clean
 * world state with the E3 harness code path (harnessVersion e4-1 = e3-1's placement, probes and signature, unchanged)
 * and the retry policy of §6: a probe timeout, receipt timeout, RPC error or instrumentation exception is retried up to
 * three times after the first attempt, each from a fresh revert; a proposal that still fails is a HARNESS FAILURE,
 * recorded, never a candidate, never a phenotype, never cached.
 *
 *   npx tsx src/e4.ts --pairs 0-87 --founders P,N --replicates 0-15 --port 8700 --out record [--seed E4-2026-10-11]
 *                    [--generations 256] [--pop 64] [--e3tables <dir>] [--founders-file slopware/experiments/E4/founders.json]
 *
 * Per population (pair q, founder f, replicate r) → record/populations/<q>-<f>-<r>.jsonl : a header line, one line per
 * generation, a final line with the 64 survivors' bytes, signature hashes and fitnesses and the worker's counts. Genomes
 * are reconstructible from the founder and the recorded proposals; the selection is recorded as candidate references.
 * Per worker → record/cache/cache-<pairs>.jsonl: genome bytes → signature hash, probe-A count, loop flag, reach flags.
 * The cache is per worker process, keyed on genome bytes (§5.8): the founder is executed and cached before its
 * generation 1; every other genome is executed on first encounter (in generation 1 or later) and looked up thereafter.
 * --e3tables: canonical child tables (<genomeId>.tsv, "pos,val,cls,sigH,life,loop" sorted) for the generation-1
 * deterministic check (§6); each table's sha256 must equal predictors.json's tableHash; any field disagreement halts.
 * Without it (smoke tests only) the check is skipped and the record says so.
 */
import { spawn, type ChildProcess } from 'node:child_process';
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { getContractAddress, keccak256, toBytes, type Hex } from 'viem';
import { connect, type Chain } from './chain.js';
import { deployRuntime } from './deploy.js';
import { fromHex } from './opcodes.js';
import { probe, standardProbes, type ProbeResult } from './probe.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const DIR = 'slopware/experiments/E4';
const FOUNDERS = JSON.parse(readFileSync(args['founders-file'] ?? `${DIR}/founders.json`, 'utf8')).pairs as any[];
const PRED = existsSync(`${DIR}/predictors.json`) ? JSON.parse(readFileSync(`${DIR}/predictors.json`, 'utf8')) : null;
const world = JSON.parse(readFileSync(args.world ?? `${DIR}/world-v0.json`, 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const PORT = Number(args.port ?? 8700); const OUT = args.out ?? 'record';
const SEED = args.seed ?? 'E4-2026-10-11';                 // the run seed string, fixed by the pre-registration (§5.7); smoke tests use 'E4-smoke'
const G = Number(args.generations ?? 256), POP = Number(args.pop ?? 64), L = world.genomeLength ?? 64;
const RETRIES = 3; const HF_RATE = 0.001, HF_MIN = 1000;    // §6: cumulative harness-failure rate above 0.1% after 1,000 executions halts the shard
const HARNESS = { harnessVersion: 'e4-1', worldId: world.worldId, protocol: 'E4-after.md', genomeLength: L, seed: SEED, generations: G, pop: POP };
const range = (s: string) => { const [a, b] = s.split('-').map(Number); return b === undefined ? [a] : Array.from({ length: b - a + 1 }, (_, i) => a + i); };
const PAIRS = range(args.pairs ?? '0-87'); const FOUNDER_KEYS = (args.founders ?? 'P,N').split(','); const REPS = range(args.replicates ?? '0-15');
const hex = (b: Uint8Array) => ('0x' + Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')) as Hex;
const sha256 = (s: string) => createHash('sha256').update(s).digest('hex');

// ---------------------------------------------------------------- the frozen signature (E1 §6) and behaviours (E2 §3 W4 + S1), unchanged from E3
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

// ---------------------------------------------------------------- anvil, snapshot, revert (as E3)
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

// ---------------------------------------------------------------- one evaluation from the clean state, with the retry policy (§6), as E3
interface Evaluation { instantiable: boolean; harnessFailure: string | null; sig: string; sigH: string; life: number; loop: boolean; reach: string[]; detector: 'ok' | 'none' | 'unavailable'; retries: number }
const REFUSED: Evaluation = { instantiable: false, harnessFailure: null, sig: 'REFUSED', sigH: '', life: 0, loop: false, reach: [], detector: 'none', retries: 0 };
async function evaluateOnce(bytes: Uint8Array): Promise<Evaluation> {
  await clean();
  const d = await deployRuntime(chain, bytes);
  if (d.status === 'error') throw new Error(`deploy: ${d.reason}`);                      // instrument error → retry
  if (d.status !== 'deployed' || !d.address) return { ...REFUSED, sig: `FAILED|${d.status}` }; // a program-level failure to place, not an instrument error
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
  const s = signature(ps);
  return { instantiable: true, harnessFailure: null, sig: s, sigH: keccak256(toBytes(s)).slice(0, 18), life: ps[0].instructionCount, loop: r.has('loop'), reach: [...r].sort(), detector, retries: 0 };
}
let harnessFailures = 0, retriesTotal = 0, physical = 0, logical = 0, cacheHits = 0;
const cache = new Map<string, Evaluation>();                                           // §5.8: per worker, keyed on genome bytes; never a harness failure
async function evaluateFresh(bytes: Uint8Array): Promise<Evaluation> {
  if (bytes[0] === 0xef) return REFUSED;
  let lastErr = '';
  for (let t = 0; t <= RETRIES; t++) {
    try { const e = await evaluateOnce(bytes); e.retries = t; retriesTotal += t; physical++; return e; }
    catch (err: any) { lastErr = String(err.message ?? err).slice(0, 120); if (t < RETRIES) { try { await freshChain(); } catch {} } }
  }
  harnessFailures++; physical++;
  if (physical >= HF_MIN && harnessFailures / physical > HF_RATE) throw new Error(`HARNESS FAILURE RATE ${harnessFailures}/${physical} above ${HF_RATE}: shard halted (§6)`);
  return { ...REFUSED, harnessFailure: lastErr, sig: 'HARNESS_FAILURE', retries: RETRIES };
}
async function evaluate(bytes: Uint8Array): Promise<{ ev: Evaluation; hit: boolean }> {
  logical++;
  const key = hex(bytes);
  const c = cache.get(key); if (c) { cacheHits++; return { ev: c, hit: true }; }
  const ev = await evaluateFresh(bytes);
  if (!ev.harnessFailure) cache.set(key, ev);
  return { ev, hit: false };
}
/** fitness F2 (§5.1): probe-A count of a finite run; null for the loop class, uninstantiable and harness failures */
const fitness = (ev: Evaluation): number | null => ev.instantiable && !ev.loop ? ev.life : null;

// ---------------------------------------------------------------- seeds, domain-separated (§5.7)
function stream(domain: string, q: number, f: number, r: number, n: number, s: number): Uint8Array {
  const tag = toBytes(`${SEED}-${domain}`); const b = new Uint8Array(tag.length + 17); b.set(tag, 0);
  const dv = new DataView(b.buffer); let o = tag.length;
  dv.setUint32(o, q); o += 4; dv.setUint8(o, f); o += 1; dv.setUint32(o, r); o += 4; dv.setUint32(o, n); o += 4; dv.setUint32(o, s);
  return toBytes(keccak256(b));
}
const u64mod = (h: Uint8Array, m: number) => Number(new DataView(h.buffer, h.byteOffset, 8).getBigUint64(0) % BigInt(m));
const cmpBytes = (a: Uint8Array, b: Uint8Array) => { for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i]; return 0; };

// ---------------------------------------------------------------- the generation-1 deterministic check (§6)
interface E3Row { cls: string; sigH: string; life: number; loop: number }
function loadE3Table(genomeId: string, expectHash: string): Map<string, E3Row> {
  const path = `${args.e3tables}/${genomeId}.tsv`; const text = readFileSync(path, 'utf8');
  if (sha256(text) !== expectHash) throw new Error(`E3 table ${genomeId}: sha256 ${sha256(text)} ≠ predictors.json ${expectHash}`);
  const m = new Map<string, E3Row>();
  for (const l of text.split('\n')) if (l) { const [pos, val, cls, sigH, life, loop] = l.split(','); m.set(`${pos},${val}`, { cls, sigH, life: Number(life), loop: Number(loop) }); }
  return m;
}

// ---------------------------------------------------------------- one population (§5.4–§5.6)
interface Slot { bytes: Uint8Array; fit: number; sigH: string; life: number }
async function runPopulation(q: number, fkey: 'P' | 'N', r: number) {
  const f = fkey === 'P' ? 0 : 1; const pair = FOUNDERS[q]; const founder = pair[fkey];
  const file = `${OUT}/populations/${q}-${f}-${r}.jsonl`;
  if (existsSync(file) && readFileSync(file, 'utf8').includes('"final":true')) return;
  writeFileSync(file, '');
  await freshChain();
  const fb = fromHex(founder.bytes as Hex);
  const { ev: f0 } = await evaluate(fb);                                                  // cached before generation 1 (§5.8)
  if (!f0.instantiable || f0.loop || f0.life !== pair.founderLife) throw new Error(`founder ${founder.genomeId}: not finite or lifespan ${f0.life} ≠ ${pair.founderLife}`);
  if (founder.signature && f0.sig !== founder.signature) throw new Error(`FOUNDER SIGNATURE MISMATCH ${founder.genomeId}: E4 ${f0.sig} ≠ E3 ${founder.signature}`);
  const e3 = args.e3tables && PRED ? loadE3Table(founder.genomeId, PRED.founders[founder.genomeId].tableHash) : null;
  appendFileSync(file, JSON.stringify({ header: true, pair: q, founder: fkey, f, replicate: r, genomeId: founder.genomeId, founderBytes: founder.bytes, founderLife: f0.life, founderSigH: f0.sigH, founderSignatureChecked: !!founder.signature, gen1Check: e3 ? 'e3-tables' : 'none (smoke)', ...HARNESS, startedAt: new Date().toISOString() }) + '\n');
  let slots: Slot[] = Array.from({ length: POP }, () => ({ bytes: fb, fit: f0.life, sigH: f0.sigH, life: f0.life }));
  let prevBest = f0.life;
  for (let n = 1; n <= G; n++) {
    type Cand = { slot: Slot; key: Uint8Array; survivor: boolean; idx: number; ref: string };
    const cands: Cand[] = slots.map((s, i) => ({ slot: s, key: stream('tie-survivor', q, f, r, n, i), survivor: true, idx: i, ref: `s${i}` }));
    const props: any[] = []; let loops = 0, hf = 0, unins = 0;
    for (let s = 0; s < POP; s++) {
      const pi = u64mod(stream('parent', q, f, r, n, s), POP); const parent = slots[pi].bytes;
      const pos = u64mod(stream('position', q, f, r, n, s), L); const w = u64mod(stream('value', q, f, r, n, s), 255); const val = w < parent[pos] ? w : w + 1;
      const child = new Uint8Array(parent); child[pos] = val;
      const p: any = { p: pi, pos, val };
      if (child[0] === 0xef) {
        unins++; p.u = 1;
        if (n === 1 && e3) { const row = e3.get(`${pos},${val}`); if (!row || row.cls !== 'refused') throw new Error(`GENERATION-1 MISMATCH ${founder.genomeId} pos ${pos} val ${val}: uninstantiable in E4, E3 ${JSON.stringify(row)}`); p.e3 = 1; }
        props.push(p); continue;
      }
      const { ev, hit } = await evaluate(child);
      if (hit) p.c = 1;
      if (ev.harnessFailure) {
        hf++; p.hf = ev.harnessFailure;
        if (n === 1 && e3) throw new Error(`GENERATION-1 MISMATCH ${founder.genomeId} pos ${pos} val ${val}: harness failure in E4 (${ev.harnessFailure}); E3 recorded none`);
        props.push(p); continue;
      }
      if (!ev.instantiable) { p.x = ev.sig; props.push(p); continue; }                    // program-level placement failure: not a candidate
      p.h = ev.sigH; p.l = ev.life; if (ev.loop) { loops++; p.loop = 1; }
      if (n === 1 && e3) {
        const row = e3.get(`${pos},${val}`); const mine = { sigH: ev.sigH, life: ev.life, loop: ev.loop ? 1 : 0 };
        if (!row || row.cls === 'refused' || row.cls === 'harness_failure' || row.sigH !== mine.sigH || row.life !== mine.life || row.loop !== mine.loop)
          throw new Error(`GENERATION-1 MISMATCH ${founder.genomeId} pos ${pos} val ${val}: E3 ${JSON.stringify(row)} E4 ${JSON.stringify(mine)}`);
        p.e3 = 1;
      }
      const fit = fitness(ev);
      if (fit !== null) cands.push({ slot: { bytes: child, fit, sigH: ev.sigH, life: ev.life }, key: stream('tie', q, f, r, n, s), survivor: false, idx: s, ref: `o${s}` });
      props.push(p);
    }
    // §5.6: fitness descending, then tie key ascending (bytewise); on an equal key, survivor before offspring, then lower slot
    cands.sort((a, b) => b.slot.fit - a.slot.fit || cmpBytes(a.key, b.key) || (a.survivor === b.survivor ? a.idx - b.idx : a.survivor ? -1 : 1));
    for (let i = 1; i < cands.length; i++) if (cands[i].slot.fit === cands[i - 1].slot.fit && cmpBytes(cands[i].key, cands[i - 1].key) === 0) appendFileSync(file, JSON.stringify({ note: 'tie-key collision', g: n, a: cands[i - 1].ref, b: cands[i].ref }) + '\n');
    const chosen = cands.slice(0, POP); slots = chosen.map((c) => c.slot);
    const best = Math.max(...slots.map((s) => s.fit));
    if (best < prevBest) throw new Error(`B_g decreased at generation ${n}: ${prevBest} → ${best}`);   // §5.6 invariant
    prevBest = best;
    appendFileSync(file, JSON.stringify({ g: n, props, sel: chosen.map((c) => c.ref), fits: slots.map((s) => s.fit), B: Math.log2(best), loops, hf, unins }) + '\n');
  }
  appendFileSync(file, JSON.stringify({ final: true, survivors: slots.map((s) => [hex(s.bytes), s.sigH, s.fit]), logical, physical, cacheHits, harnessFailures, retriesTotal, finishedAt: new Date().toISOString() }) + '\n');
  return slots;
}

mkdirSync(`${OUT}/populations`, { recursive: true }); mkdirSync(`${OUT}/cache`, { recursive: true });
const t0 = Date.now(); let done = 0;
for (const q of PAIRS) for (const fkey of FOUNDER_KEYS as ('P' | 'N')[]) for (const r of REPS) {
  const slots = await runPopulation(q, fkey, r); done++;
  if (slots) console.log(`  pair ${q} ${fkey} rep ${r} · B_G ${Math.log2(Math.max(...slots.map((s) => s.fit))).toFixed(2)} · logical ${logical} physical ${physical} hits ${cacheHits} · hf ${harnessFailures} · ${(physical / ((Date.now() - t0) / 1000)).toFixed(1)} exec/s`);
}
const cacheFile = `${OUT}/cache/cache-${args.pairs ?? '0-87'}-${(args.replicates ?? '0-15')}.jsonl`;
writeFileSync(cacheFile, [...cache.entries()].map(([g, e]) => JSON.stringify({ g, h: e.sigH, l: e.life, loop: e.loop ? 1 : 0, reach: e.reach })).join('\n') + '\n');
console.log(`done · ${done} populations · logical ${logical} · physical ${physical} · cache hits ${cacheHits} · harness failures ${harnessFailures} · retries ${retriesTotal} · cache ${cache.size} genomes → ${cacheFile}`);
process.exit(0);
