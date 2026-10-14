/**
 * Rolling-map pilot (slopware/pilots/rolling-map/PROTOCOL.md). EXPLORATORY: not E5, not pre-registered, not anchored.
 * World: the PILOT world (world-pilot.json), block context frozen, program placed with anvil_setCode, probe A only.
 *
 * One run = (pair q, founder f, replicate r, arm). Every arm of a run gets the same logical evaluation budget
 *   E = G × POP + A,  A = the mapping cost of the most mapping-hungry arm in --arms (rolling8: ceil(G/8) × K × S),
 * and spends it on generations of POP one-byte proposals (search evaluations) and, for the mapping arms, on measuring
 * local upward accessibility (mapping evaluations): at a refresh generation the up-to-S distinct genomes of the top
 * fitness class are each measured on K seeded one-byte mutants, accessibility = (# finite mutants outliving the genome) / K.
 * Mapped mutants are measurement only: they never enter the population (they are cached, so a later identical proposal is a
 * cache hit, which is counted and reported). Budget is counted in logical evaluations, cache hits included, as E4 counted.
 * A run stops when the remaining budget cannot pay for a full generation, so baseline runs more generations than rolling8.
 *
 * Map use (fixed before the run): selection sorts candidates by fitness descending (F2, probe A, loop class never continues),
 * then, among EXACT fitness ties only, by accessibility descending where known (a candidate's own measurement if it was
 * mapped, else the value inherited from its parent; known before unknown), then by the seeded tie key as in E4 §5.6.
 * baseline never knows an accessibility; static maps at generation 1 only; rollingI maps at generations 1, 1+I, 1+2I, …
 *
 * Seeds: domain-separated keccak streams as E4 §5.7, with the pilot seed string; the arm is NOT part of the seed, so all
 * arms of a run see the same proposal stream for as long as their populations agree (common random numbers).
 *
 *   npx tsx src/pilot_rolling.ts --pairs 0-11 --founders P,N --replicates 0-7 --arms baseline,static,rolling8,rolling16,rolling32,rolling64
 *                                --generations 128 --k 256 --s 1 --port 8900 --out /root/pilot/run --shard 0/32
 */
import { spawn, type ChildProcess } from 'node:child_process';
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { keccak256, toBytes, type Hex } from 'viem';
import { connect, type Chain } from './chain.js';
import { fromHex } from './opcodes.js';
import { probe, standardProbes, type ProbeResult } from './probe.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const world = JSON.parse(readFileSync(args.world ?? 'slopware/pilots/rolling-map/world-pilot.json', 'utf8'));
const FOUNDERS = JSON.parse(readFileSync(args['founders-file'] ?? 'slopware/experiments/E4/founders.json', 'utf8')).pairs as any[];
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const PROBE_A = specs[0];
const PORT = Number(args.port ?? 8900); const OUT = args.out ?? 'pilot-out'; const SEED = args.seed ?? 'PILOT-rolling-map-2026-10-14';
const G = Number(args.generations ?? 128), POP = Number(args.pop ?? 64), L = 64, K = Number(args.k ?? 256), S = Number(args.s ?? 1);
const ARMS = (args.arms ?? 'baseline,static,rolling8,rolling16,rolling32,rolling64').split(',');
const RETRIES = 3; const ADDR = world.programAddress as Hex;
const range = (s: string) => s.split(',').flatMap((part) => { const [a, b] = part.split('-').map(Number); return b === undefined ? [a] : Array.from({ length: b - a + 1 }, (_, i) => a + i); });
const PAIRS = range(args.pairs ?? '0-11'); const FKEYS = (args.founders ?? 'P,N').split(','); const REPS = range(args.replicates ?? '0-7');
const [SHARD, NSHARDS] = (args.shard ?? '0/1').split('/').map(Number);
const hex = (b: Uint8Array) => ('0x' + Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')) as Hex;
const mapsAt = (arm: string, n: number) => arm === 'baseline' ? false : arm === 'static' ? n === 1 : (n - 1) % Number(arm.replace('rolling', '')) === 0;
const mappingCost = (arm: string) => arm === 'baseline' ? 0 : arm === 'static' ? K * S : Math.ceil(G / Number(arm.replace('rolling', ''))) * K * S;
// the budget is a property of the pilot, not of the arms a worker happens to run: pass --budget (PROTOCOL.md: 16384) when a
// worker runs a subset of the arms; without it, the allowance is the mapping cost of the most mapping-hungry arm given.
const BUDGET = args.budget ? Number(args.budget) : G * POP + Math.max(...ARMS.map(mappingCost)); const A = BUDGET - G * POP;
const HEADER = { pilot: 'rolling-map', worldId: world.worldId, seed: SEED, generations: G, pop: POP, K, S, arms: ARMS, budget: BUDGET, mappingAllowance: A, fitness: 'F2 probe A', harness: 'pilot_rolling.ts' };

// ---------------------------------------------------------------- anvil: pilot world, never mined
let anvil: ChildProcess | null = null; let chain: Chain;
async function freshChain() {
  if (anvil) { anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  for (let attempt = 0; attempt < 3; attempt++) {
    anvil = spawn('anvil', ['--port', String(PORT), '--hardfork', world.hardfork, '--chain-id', String(world.chainId), '--silent', '--gas-limit', String(world.blockGasLimit), '--timestamp', String(world.genesisTimestamp), '--no-mining', '--base-fee', String(world.baseFee), '--gas-price', String(world.gasPrice)], { stdio: 'ignore' });
    for (let i = 0; i < 300; i++) {
      try { const r = await fetch(`http://127.0.0.1:${PORT}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' }); if (r.ok) { chain = await connect(`http://127.0.0.1:${PORT}`, world.callerKeyIndex); return; } } catch {}
      await new Promise((r) => setTimeout(r, 200));
    }
    anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error('anvil did not start');
}
process.on('exit', () => anvil?.kill('SIGKILL'));

// ---------------------------------------------------------------- one evaluation: probe A only, with E4's retry policy
interface Ev { life: number; loop: boolean; sigH: string; hf: string | null }
const sigA = (p: ProbeResult) => { const rd = p.returnData && p.returnData !== '0x' ? keccak256(p.returnData as Hex).slice(0, 18) : ''; return [p.outcome, p.instructionCount, p.lastOp ?? '', p.returnDataLength, rd].join('|'); };
async function evaluateOnce(bytes: Uint8Array): Promise<Ev> {
  await chain.request('anvil_setCode', [ADDR, hex(bytes)]);
  const p = await probe(chain, ADDR, PROBE_A);
  const loop = p.outcome === 'out_of_gas' && p.instructionCount > 32;
  return { life: p.instructionCount, loop, sigH: keccak256(toBytes(sigA(p))).slice(0, 18), hf: null };
}
interface Counts { logical: number; physical: number; hits: number; map: number; search: number; hf: number; retries: number }
let cache = new Map<string, Ev>(); let C: Counts;
async function evaluate(bytes: Uint8Array, kind: 'map' | 'search'): Promise<Ev> {
  C.logical++; C[kind]++;
  const key = hex(bytes); const c = cache.get(key); if (c) { C.hits++; return c; }
  let lastErr = '';
  for (let t = 0; t <= RETRIES; t++) {
    try { const e = await evaluateOnce(bytes); C.retries += t; C.physical++; cache.set(key, e); return e; }
    catch (err: any) { lastErr = String(err.message ?? err).slice(0, 120); if (t < RETRIES) { try { await freshChain(); } catch {} } }
  }
  C.hf++; C.physical++; return { life: 0, loop: true, sigH: '', hf: lastErr };
}
const fitness = (e: Ev): number | null => (e.hf || e.loop) ? null : e.life;

// ---------------------------------------------------------------- seeds (E4 §5.7 form, pilot seed string)
function stream(domain: string, q: number, f: number, r: number, n: number, s: number): Uint8Array {
  const tag = toBytes(`${SEED}-${domain}`); const b = new Uint8Array(tag.length + 17); b.set(tag, 0);
  const dv = new DataView(b.buffer); let o = tag.length;
  dv.setUint32(o, q); o += 4; dv.setUint8(o, f); o += 1; dv.setUint32(o, r); o += 4; dv.setUint32(o, n); o += 4; dv.setUint32(o, s);
  return toBytes(keccak256(b));
}
const u64mod = (h: Uint8Array, m: number) => Number(new DataView(h.buffer, h.byteOffset, 8).getBigUint64(0) % BigInt(m));
const cmpBytes = (a: Uint8Array, b: Uint8Array) => { for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i]; return 0; };
const hamming = (a: Uint8Array, b: Uint8Array) => { let d = 0; for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) d++; return d; };

// ---------------------------------------------------------------- one run
interface Slot { bytes: Uint8Array; fit: number; acc: number | null; accG: number | null }
async function runOne(q: number, fkey: string, r: number, arm: string) {
  const f = fkey === 'P' ? 0 : 1; const founder = FOUNDERS[q][fkey]; const fb = fromHex(founder.bytes as Hex);
  const file = `${OUT}/runs/${q}-${f}-${r}-${arm}.jsonl`;
  if (existsSync(file) && readFileSync(file, 'utf8').includes('"final":true')) return null;
  writeFileSync(file, '');
  cache = new Map(); C = { logical: 0, physical: 0, hits: 0, map: 0, search: 0, hf: 0, retries: 0 };
  await freshChain();
  const t0 = Date.now();
  const f0 = await evaluate(fb, 'search'); const fit0 = fitness(f0);
  if (fit0 === null) throw new Error(`founder ${founder.genomeId} not finite under the pilot world`);
  appendFileSync(file, JSON.stringify({ header: true, ...HEADER, pair: q, founder: fkey, f, replicate: r, arm, genomeId: founder.genomeId, founderBytes: founder.bytes, founderLife: fit0, founderLifeE4: FOUNDERS[q].founderLife, startedAt: new Date().toISOString() }) + '\n');
  let slots: Slot[] = Array.from({ length: POP }, () => ({ bytes: fb, fit: fit0, acc: null, accG: null }));
  let prevMapped: Uint8Array[] = []; let n = 0; let budget = BUDGET - 1;   // the founder evaluation is paid by every arm alike
  while (budget >= POP) {
    n++;
    // ---- mapping, if this arm maps at this generation and can pay for at least one genome
    if (mapsAt(arm, n) && budget >= K) {
      const best = Math.max(...slots.map((s) => s.fit));
      const seen = new Set<string>(); const targets: Slot[] = [];
      for (const s of slots) { if (s.fit !== best) continue; const h = hex(s.bytes); if (seen.has(h)) continue; seen.add(h); targets.push(s); if (targets.length === S) break; }
      const events: any[] = [];
      for (let ti = 0; ti < targets.length && budget >= K; ti++) {
        const g = targets[ti]; let up = 0, loops = 0, unins = 0; const c0 = { ...C };
        for (let k = 0; k < K; k++) {
          const idx = ti * K + k;
          const pos = u64mod(stream('mappos', q, f, r, n, idx), L); const w = u64mod(stream('mapval', q, f, r, n, idx), 255); const val = w < g.bytes[pos] ? w : w + 1;
          const child = new Uint8Array(g.bytes); child[pos] = val;
          if (child[0] === 0xef) { unins++; continue; }                       // counted in K, never evaluated, costs nothing (as A1's denominator)
          const ev = await evaluate(child, 'map'); budget--;
          if (ev.loop) loops++; const fk = fitness(ev); if (fk !== null && fk > g.fit) up++;
        }
        const acc = up / K; const gh = hex(g.bytes);
        for (const s of slots) if (hex(s.bytes) === gh) { s.acc = acc; s.accG = n; }
        events.push({ genome: gh, fit: g.fit, acc, up, loops, unins, K, distFounder: hamming(g.bytes, fb), distPrev: prevMapped.length ? Math.min(...prevMapped.map((p) => hamming(g.bytes, p))) : null, cost: { logical: C.logical - c0.logical, physical: C.physical - c0.physical, hits: C.hits - c0.hits } });
      }
      prevMapped = targets.map((t) => t.bytes);
      appendFileSync(file, JSON.stringify({ map: true, g: n, events, budgetLeft: budget }) + '\n');
    }
    if (budget < POP) break;
    // ---- proposals
    type Cand = { slot: Slot; key: Uint8Array; survivor: boolean; idx: number };
    const cands: Cand[] = slots.map((s, i) => ({ slot: s, key: stream('tie-survivor', q, f, r, n, i), survivor: true, idx: i }));
    let loops = 0, unins = 0, hf = 0;
    for (let s = 0; s < POP; s++) {
      const pi = u64mod(stream('parent', q, f, r, n, s), POP); const parent = slots[pi];
      const pos = u64mod(stream('position', q, f, r, n, s), L); const w = u64mod(stream('value', q, f, r, n, s), 255); const val = w < parent.bytes[pos] ? w : w + 1;
      const child = new Uint8Array(parent.bytes); child[pos] = val;
      if (child[0] === 0xef) { unins++; continue; }
      const ev = await evaluate(child, 'search'); budget--;
      if (ev.hf) { hf++; continue; }
      if (ev.loop) { loops++; continue; }
      const fit = fitness(ev)!;
      cands.push({ slot: { bytes: child, fit, acc: parent.acc, accG: parent.accG }, key: stream('tie', q, f, r, n, s), survivor: false, idx: s });
    }
    // ---- selection: fitness desc; among exact ties accessibility desc (known before unknown); then tie key asc; then survivor, slot
    cands.sort((a, b) => b.slot.fit - a.slot.fit
      || ((b.slot.acc ?? 0) - (a.slot.acc ?? 0))                      // unknown accessibility counts as 0: only positive information discriminates
      || cmpBytes(a.key, b.key) || (a.survivor === b.survivor ? a.idx - b.idx : a.survivor ? -1 : 1));
    const chosen = cands.slice(0, POP);
    const best = Math.max(...chosen.map((c) => c.slot.fit));
    // tie statistics for the pre-run benchmark and the report: size of the top class among candidates, distinct genomes in it,
    // whether the cut fell inside a fitness tie, how many of the chosen were ordered by a known accessibility
    const topSize = cands.filter((c) => c.slot.fit === best).length; const distinctTop = new Set(cands.filter((c) => c.slot.fit === best).map((c) => hex(c.slot.bytes))).size;
    const cutTie = cands.length > POP && cands[POP - 1].slot.fit === cands[POP].slot.fit;
    const knownAcc = chosen.filter((c) => c.slot.acc !== null).length;
    slots = chosen.map((c) => c.slot);
    appendFileSync(file, JSON.stringify({ g: n, B: Math.log2(best), best, median: chosen.map((c) => c.slot.fit).sort((a, b) => a - b)[POP >> 1], loops, unins, hf, topSize, distinctTop, cutTie, knownAcc, budgetLeft: budget, c: { ...C } }) + '\n');
  }
  const secs = (Date.now() - t0) / 1000;
  appendFileSync(file, JSON.stringify({ final: true, generations: n, survivors: slots.map((s) => [hex(s.bytes), s.fit, s.acc]), counts: C, budget: BUDGET, budgetLeft: budget, seconds: secs, finishedAt: new Date().toISOString() }) + '\n');
  return { n, secs, C };
}

// ---------------------------------------------------------------- the shard
mkdirSync(`${OUT}/runs`, { recursive: true });
const runs: [number, string, number][] = [];
for (const q of PAIRS) for (const fk of FKEYS) for (const r of REPS) runs.push([q, fk, r]);
const mine = runs.filter((_, i) => i % NSHARDS === SHARD);
console.log(`pilot rolling-map · shard ${SHARD}/${NSHARDS} · ${mine.length} founder×replicate runs × ${ARMS.length} arms · G ${G} POP ${POP} K ${K} S ${S} · budget ${BUDGET} (allowance ${A}) · world ${world.worldId.slice(0, 18)}`);
const T0 = Date.now(); let evals = 0, phys = 0;
for (const [q, fk, r] of mine) for (const arm of ARMS) {
  const res = await runOne(q, fk, r, arm);
  if (!res) { console.log(`  ${q}-${fk}-${r} ${arm}: already final`); continue; }
  evals += res.C.logical; phys += res.C.physical;
  console.log(`  ${q}-${fk}-${r} ${arm}: ${res.n} generations · logical ${res.C.logical} (map ${res.C.map}, search ${res.C.search}) · physical ${res.C.physical} · hits ${res.C.hits} · hf ${res.C.hf} · ${res.secs.toFixed(0)} s · ${(res.C.physical / res.secs).toFixed(1)} exec/s`);
}
console.log(`done · shard ${SHARD}/${NSHARDS} · logical ${evals} · physical ${phys} · ${((Date.now() - T0) / 1000).toFixed(0)} s · ${(phys / ((Date.now() - T0) / 1000)).toFixed(1)} exec/s`);
anvil?.kill('SIGKILL');
