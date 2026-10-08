/**
 * E1 — Neighbourhoods. The runner.
 *
 * For each parent genome in a set (genesis or control), place the parent three times, then place every
 * single-byte substitution (or a seeded sample of values per position), probe each under world v0, and
 * record placements and per-parent fractions. The protocol is slopware/experiments/E1-neighbourhoods.md;
 * nothing here may deviate from it without a dated amendment there.
 *
 *   npx tsx src/e1.ts --set genesis --from 0 --to 9 --port 8560 --workers 10 --out slopware/experiments/E1/record
 *   options: --sample 255 (all values) | 16 (seeded sample per position) · --restart-every 10 (parents per anvil)
 *
 * Spawns its own anvil on --port, local only. Writes record/<set>/placements-<from>-<to>.jsonl and parents-<from>-<to>.jsonl.
 */
import { spawn, type ChildProcess } from 'node:child_process';
import { appendFileSync, mkdirSync, readFileSync } from 'node:fs';
import { keccak256, toBytes, type Hex } from 'viem';
import { connect, type Chain } from './chain.js';
import { deployRuntime } from './deploy.js';
import { disassemble, fromHex, hex } from './opcodes.js';
import { probe, standardProbes, type ProbeResult } from './probe.js';
import { seededRng } from './rng.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const SET = (args.set ?? 'genesis') as 'genesis' | 'control';
const DIR = args.dir ?? 'slopware/experiments/E1';
const OUT = args.out ?? `${DIR}/record`;
const PORT = Number(args.port ?? 8560);
const WORKERS = Math.max(1, Math.min(10, Number(args.workers ?? 10)));
const SAMPLE = Number(args.sample ?? 255);
const RESTART_EVERY = Number(args['restart-every'] ?? 10);
const FROM = Number(args.from ?? 0);

const world = JSON.parse(readFileSync(`${DIR}/world-v0.json`, 'utf8'));
const setFile = JSON.parse(readFileSync(`${DIR}/${SET === 'genesis' ? 'genesis' : 'controls'}.json`, 'utf8'));
const parents: any[] = setFile.genomes;
const TO = Math.min(Number(args.to ?? parents.length - 1), parents.length - 1);
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const HARNESS = { harnessVersion: 'e1-1', worldId: world.worldId, protocol: 'E1-neighbourhoods.md' };

mkdirSync(`${OUT}/${SET}`, { recursive: true });
const placementsFile = `${OUT}/${SET}/placements-${FROM}-${TO}.jsonl`;
const parentsFile = `${OUT}/${SET}/parents-${FROM}-${TO}.jsonl`;

// ---------------------------------------------------------------- anvil, owned by this process
let anvil: ChildProcess | null = null;
async function startAnvil(): Promise<void> {
  if (anvil) { anvil.kill('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  anvil = spawn('anvil', ['--port', String(PORT), '--hardfork', world.hardfork, '--chain-id', String(world.chainId), '--silent', '--gas-limit', '30000000'], { stdio: 'ignore' });
  for (let i = 0; i < 100; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' }); if (r.ok) return; } catch {}
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error('anvil did not start');
}
process.on('exit', () => anvil?.kill('SIGKILL'));

// ---------------------------------------------------------------- the frozen signature (protocol §6)
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
  const s = (p: ProbeResult) => `${p.outcome}|${p.instructionCount}|${p.returnData}`;
  const abcd = ps.filter((p) => 'ABCD'.includes(p.name[0]));
  if (new Set(abcd.map(s)).size > 1) r.add('calldata_dependent');
  const a = ps.find((p) => p.name[0] === 'A'), e = ps.find((p) => p.name[0] === 'E');
  if (a && e && s(a) !== s(e)) r.add('value_dependent');
  return [...r].sort();
}
// behaviours the million-program study never showed (protocol H5)
const NEVER_SEEN = new Set(['external_call', 'child_may_exist', 'loop']);

function consumedBytes(bytes: Uint8Array, probeA: ProbeResult) {
  const dis = disassemble(bytes); const n = probeA.instructionCount;
  if (n <= 0) return 1;
  if (n > dis.length) return 64;
  const last = dis[n - 1]; const len = 1 + (last.imm ? last.imm.length / 2 : 0);
  return Math.min(64, last.pc + len);
}

// ---------------------------------------------------------------- one placement
async function place(chain: Chain, bytes: Uint8Array) {
  const d = await deployRuntime(chain, bytes);
  if (d.status !== 'deployed' || !d.address) return { address: null as string | null, probes: [] as ProbeResult[], failure: d.reason ?? d.status };
  const ps: ProbeResult[] = [];
  for (const spec of specs) {
    try { ps.push(await probe(chain, d.address, spec)); }
    catch (e: any) { ps.push({ name: spec.name, calldata: spec.calldata, value: spec.value.toString(), outcome: 'other_halt', error: `instrument: ${String(e.message ?? e)}`, gasUsed: 0, returnData: '0x', returnDataLength: 0, ops: [], instructionCount: 0, opCounts: {}, maxDepth: 1, storageWrites: 0, storageReads: 0, logs: 0, calls: 0, creates: 0, keccaks: 0, jumps: 0, memoryOps: 0 } as any); }
  }
  return { address: d.address as string, probes: ps, failure: null };
}
const compact = (ps: ProbeResult[], keepOps: boolean) => ps.map((p) => ({ n: p.name[0], o: p.outcome, i: p.instructionCount, last: p.lastOp, rl: p.returnDataLength, rd: p.returnDataLength ? p.returnData : undefined, err: p.rawError, ss: (p.opCounts ?? {})['SSTORE'] ?? 0, ts: (p.opCounts ?? {})['TSTORE'] ?? 0, lg: p.logs, cr: p.creates, cl: p.calls, ops: keepOps ? p.ops : undefined }));

// ---------------------------------------------------------------- the run
const t0 = Date.now(); let placed = 0;
await startAnvil();
let chains = await Promise.all(Array.from({ length: WORKERS }, (_, i) => connect(`http://127.0.0.1:${PORT}`, i)));
console.log(`E1 ${SET} parents ${FROM}..${TO} · sample ${SAMPLE}/255 · ${WORKERS} workers · world ${world.worldId.slice(0, 10)}…`);

for (let idx = FROM; idx <= TO; idx++) {
  if (idx > FROM && (idx - FROM) % RESTART_EVERY === 0) { await startAnvil(); chains = await Promise.all(Array.from({ length: WORKERS }, (_, i) => connect(`http://127.0.0.1:${PORT}`, i))); }
  const parent = parents[idx];
  const pbytes = fromHex(parent.bytes);
  const parentId = parent.genotypeId as string;
  const label = SET === 'genesis' ? `release ${parent.release}` : `control ${parent.index}`;

  // children: every value at every position, or a seeded sample of values per position
  const children: { pos: number; val: number }[] = [];
  const srng = SAMPLE < 255 ? seededRng(`E1-sample-${parentId}`) : null;
  for (let pos = 0; pos < 64; pos++) {
    const vals = srng ? Array.from(new Set(Array.from({ length: SAMPLE * 3 }, () => srng.bytes(1)[0]).filter((v) => v !== pbytes[pos]))).slice(0, SAMPLE) : Array.from({ length: 256 }, (_, v) => v).filter((v) => v !== pbytes[pos]);
    for (const val of vals) children.push({ pos, val });
  }

  // the parent, three times
  const parentPlacements: any[] = [];
  if (parent.instantiable) {
    for (let rep = 0; rep < 3; rep++) {
      const r = await place(chains[rep % WORKERS], pbytes); placed++;
      parentPlacements.push({ rep, address: r.address, failure: r.failure, signature: r.probes.length ? signature(r.probes) : null, reaches: reaches(r.probes), probes: compact(r.probes, true) });
    }
  }
  const ref = parentPlacements[0];
  const refSig = ref?.signature ?? null;
  const refProbes: ProbeResult[] | null = null;
  const parentLen = ref?.probes?.find((p: any) => p.n === 'A')?.i ?? null;
  const parentClean = (ref?.reaches ?? []).includes('clean_halt');
  const consumed = parent.instantiable && ref?.probes?.length ? consumedBytes(pbytes, { instructionCount: parentLen } as any) : null;

  // the children, across workers
  const counts = { children: children.length, placed: 0, notInstantiable: 0, neutral: 0, altered: 0, lengthened: 0, shortened: 0, lethal: 0, failures: 0 };
  const reachCounts: Record<string, number> = {}; const h5: any[] = [];
  let next = 0;
  await Promise.all(chains.map(async (chain) => {
    for (;;) {
      const k = next++; if (k >= children.length) return;
      const { pos, val } = children[k];
      const cbytes = new Uint8Array(pbytes); cbytes[pos] = val;
      const childId = keccak256(hex(cbytes) as Hex);
      const eventId = keccak256(toBytes(`${parentId}|substitute|${pos}|${val}|E1`));
      const rec: any = { e: eventId, g: childId, p: parentId, pos, val, set: SET };
      if (cbytes[0] === 0xef) { rec.instantiable = false; counts.notInstantiable++; appendFileSync(placementsFile, JSON.stringify(rec) + '\n'); continue; }
      const r = await place(chain, cbytes); placed++;
      if (r.failure) { rec.failure = r.failure; counts.failures++; appendFileSync(placementsFile, JSON.stringify(rec) + '\n'); continue; }
      const s = signature(r.probes); const rs = reaches(r.probes);
      const a = r.probes.find((p) => p.name[0] === 'A')!;
      let cls = 'altered';
      if (refSig !== null && s === refSig) cls = 'neutral';
      else if (parentLen !== null && a.instructionCount > parentLen) cls = 'lengthened';
      else if (parentLen !== null && a.instructionCount < parentLen) cls = 'shortened';
      if (parentClean && !rs.includes('clean_halt')) counts.lethal++;
      (counts as any)[cls]++; counts.placed++;
      for (const b of rs) reachCounts[b] = (reachCounts[b] ?? 0) + 1;
      const novel = rs.filter((b) => NEVER_SEEN.has(b));
      const keepOps = cls !== 'neutral' || novel.length > 0;
      Object.assign(rec, { addr: r.address, cls, sig: s, reaches: rs, probes: compact(r.probes, keepOps) });
      if (novel.length) h5.push({ childId, eventId, pos, val, novel, address: r.address });
      appendFileSync(placementsFile, JSON.stringify(rec) + '\n');
    }
  }));

  const n = counts.placed || 1;
  const summary = {
    set: SET, index: idx, label, release: parent.release ?? null, controlIndex: parent.index ?? null, genotypeId: parentId, bytes: parent.bytes, instantiable: parent.instantiable,
    parent: { placements: parentPlacements.map((p) => ({ rep: p.rep, address: p.address, signature: p.signature, reaches: p.reaches, failure: p.failure })), noiseIdentical: parentPlacements.length === 3 && new Set(parentPlacements.map((p) => p.signature)).size === 1, lifespanA: parentLen, consumedBytes: consumed, predictedNeutral: consumed === null ? null : (64 - consumed) / 64 },
    children: counts,
    fractions: { neutral: counts.neutral / n, altered: counts.altered / n, lengthened: counts.lengthened / n, shortened: counts.shortened / n, lethal: counts.lethal / n },
    reaches: reachCounts, h5,
    ...HARNESS, finishedAt: new Date().toISOString(),
  };
  appendFileSync(parentsFile, JSON.stringify(summary) + '\n');
  const rate = placed / ((Date.now() - t0) / 1000);
  console.log(`  ${label.padEnd(14)} placed ${String(counts.placed).padStart(6)} · neutral ${(summary.fractions.neutral * 100).toFixed(1).padStart(5)}% · lengthened ${String(counts.lengthened).padStart(4)} · clean ${String(reachCounts['clean_halt'] ?? 0).padStart(4)}${h5.length ? ` · H5 candidates ${h5.length}` : ''} · ${rate.toFixed(0)}/s`);
}
console.log(`done · ${placed} placements · ${((Date.now() - t0) / 60000).toFixed(1)} min`);
process.exit(0);
