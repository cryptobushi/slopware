/**
 * Readings: the lab's observations of what the installer has installed.
 *
 * Reads every release from the installer on a public chain (read-only), places the same sixty-four
 * bytes on the local lab chain, calls each program five ways with every opcode traced, and writes
 * slopware/site/readings.json. The installer records nothing about behavior and the site says
 * UNKNOWN; this file is the lab looking, separately, and saying what it saw.
 *
 *   npx tsx src/readings.ts --rpc https://ethereum-rpc.publicnode.com --contract 0x… [--lab http://127.0.0.1:8546] [--out slopware/site/readings.json]
 *
 * Incremental: releases already in the output file are kept; only new ones are read.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { traceLine, verdict, wouldHaveBeen } from './readings-text.js';
import { createPublicClient, http, parseAbi, type Hex } from 'viem';
import { connect } from './chain.js';
import { classify } from './classify.js';
import { deployRuntime } from './deploy.js';
import { disassemble, fromHex, type Instruction } from './opcodes.js';
import { probe, standardProbes, type ProbeResult } from './probe.js';

const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const RPC = args.rpc ?? 'https://ethereum-rpc.publicnode.com';
const CONTRACT = (args.contract ?? '') as Hex;
const LAB = args.lab ?? 'http://127.0.0.1:8546';
const OUT = args.out ?? 'slopware/site/readings.json';
const DESCENT = args.descent ?? 'slopware/experiments/E1/summaries/descent.json';
if (!/^0x[0-9a-fA-F]{40}$/.test(CONTRACT)) { console.error('--contract is required'); process.exit(2); }

const abi = parseAbi([
  'function releases() view returns (uint256)',
  'function software(uint256) view returns ((address installer,uint64 requestedAt,uint64 installedAt,uint8 status,uint96 paid,address program,bytes32 checksum))',
  'function bytecodeOf(uint256) view returns (bytes)',
]);
const STATUS = ['none', 'installing', 'installed', 'rejected', 'abandoned'];

// opcodes worth pointing at in the text a dead program never reaches
const NOTABLE = new Set(['SSTORE', 'TSTORE', 'CREATE', 'CREATE2', 'CALL', 'CALLCODE', 'DELEGATECALL', 'STATICCALL', 'SELFDESTRUCT', 'JUMP', 'JUMPI', 'JUMPDEST', 'LOG0', 'LOG1', 'LOG2', 'LOG3', 'LOG4', 'RETURN', 'REVERT', 'STOP', 'KECCAK256', 'SLOAD', 'TLOAD']);

interface Reading {
  id: number; installer: string; program: string | null; requestedAt: number; installedAt: number; status: string;
  bytecode: string;
  disassembly: { pc: number; name: string; imm: string; truncated: boolean }[];
  probes: { name: string; outcome: string; rawError?: string; instructions: number; ops: string[]; returnData: string; returnDataLength: number; gasUsed: number }[];
  traits: string[]; primary: string;
  lifespan: number; inputDependent: boolean;
  notable: string[]; future: string[]; undefinedBytes: number;
  readAt: string; labCodeMatches: boolean;
}

const existing: Reading[] = existsSync(OUT) ? (JSON.parse(readFileSync(OUT, 'utf8')).readings ?? []) : [];
const have = new Set(existing.map((r) => r.id));

const pub = createPublicClient({ transport: http(RPC) });
const chainId = await pub.getChainId();
const releases = Number(await pub.readContract({ address: CONTRACT, abi, functionName: 'releases' }));
console.log(`installer ${CONTRACT} on chain ${chainId} · ${releases} releases · ${have.size} already read`);

const lab = await connect(LAB, 9);
const rnd = new Uint8Array(32); crypto.getRandomValues(rnd);
const sel = new Uint8Array(4); crypto.getRandomValues(sel);
const arg = new Uint8Array(32); crypto.getRandomValues(arg);

const fresh: Reading[] = [];
for (let id = 1; id <= releases; id++) {
  if (have.has(id)) continue;
  const s = await pub.readContract({ address: CONTRACT, abi, functionName: 'software', args: [BigInt(id)] });
  if (s.status === 1) continue; // still installing: read it next time
  const bytecode = (await pub.readContract({ address: CONTRACT, abi, functionName: 'bytecodeOf', args: [BigInt(id)] })) as Hex;
  const runtime = fromHex(bytecode);
  const dis: Instruction[] = disassemble(runtime);
  const names = dis.map((i) => i.name);
  let probes: ProbeResult[] = [];
  let labCodeMatches = false;
  if (s.status === 2) {
    const birth = await deployRuntime(lab, runtime);
    labCodeMatches = Boolean(birth.codeMatches);
    for (const spec of standardProbes(rnd, sel, arg)) probes.push(await probe(lab, birth.address!, spec));
  }
  const cls = s.status === 2 ? classify(probes, true) : { traits: ['REFUSED'], primary: 'REFUSED', lifespan: {}, notes: [] };
  const a = probes[0];
  const sig = (p: ProbeResult) => `${p.outcome}|${p.instructionCount}|${p.returnData}`;
  const r: Reading = {
    id, installer: s.installer, program: s.status === 2 ? s.program : null, requestedAt: Number(s.requestedAt), installedAt: Number(s.installedAt), status: STATUS[s.status],
    bytecode,
    disassembly: dis.map((i) => ({ pc: i.pc, name: i.name, imm: i.imm, truncated: i.truncated })),
    probes: probes.map((p) => ({ name: p.name, outcome: p.outcome, rawError: p.rawError, instructions: p.instructionCount, ops: p.ops, returnData: p.returnData, returnDataLength: p.returnDataLength, gasUsed: p.gasUsed })),
    traits: cls.traits as string[], primary: cls.primary,
    lifespan: a ? a.instructionCount : 0,
    inputDependent: probes.length > 1 && new Set(probes.map(sig)).size > 1,
    notable: [...new Set(names.filter((n) => NOTABLE.has(n)))],
    future: [...new Set(names.filter((n) => /not activated/.test(n)).map((n) => n.replace(' (not activated)', '')))],
    undefinedBytes: names.filter((n) => /^UNDEFINED/.test(n)).length,
    readAt: new Date().toISOString(), labCodeMatches,
  };
  fresh.push(r);
  console.log(`  ${String(id).padStart(6, '0')}  ${r.status.padEnd(9)} ${String(r.lifespan).padStart(2)} instr  ${a ? a.outcome : ''}${r.inputDependent ? '  INPUT-DEPENDENT' : ''}${a?.returnDataLength ? `  returns ${a.returnDataLength} B` : ''}`);
}

const all = [...existing, ...fresh].sort((x, y) => x.id - y.id);
const installed = all.filter((r) => r.status === 'installed');
const summary = {
  releasesRead: all.length, installed: installed.length, refused: all.filter((r) => r.status === 'rejected').length,
  diedAtFirst: installed.filter((r) => r.lifespan <= 1 && r.probes[0]?.outcome !== 'success').length,
  longest: Math.max(0, ...installed.map((r) => Math.max(...r.probes.map((p) => p.instructions)))),
  cleanHalts: installed.filter((r) => r.probes.some((p) => p.outcome === 'success')).length,
  inputDependent: installed.filter((r) => r.inputDependent).length,
  returnedData: installed.filter((r) => r.probes.some((p) => p.returnDataLength > 0)).length,
  withFutureOpcodes: installed.filter((r) => r.future.length > 0).length,
  labPrediction: { diedAtFirstPct: 78.4, cleanHaltPer: 130, refusedPer: 256, inputDependentPer: 9300 },
};
const generatedAt = new Date().toISOString();
writeFileSync(OUT, JSON.stringify({ installer: CONTRACT, chainId, generatedAt, summary, readings: all }, null, 0));

// The page's files: a light index with the sentences already written, and the bytes in chunks of 100 releases,
// fetched only when a reader opens them. The full record above stays as the lab's data file.
const CHUNK = 100;
const rdir = join(dirname(OUT), 'r');
mkdirSync(rdir, { recursive: true });
// E1's neighbourhood, one sentence per release, from the sealed record (protocol §13): made by infrastructure, lab chain only
const descent: Record<number, any> = {};
if (existsSync(DESCENT)) for (const d of JSON.parse(readFileSync(DESCENT, 'utf8')).releases) descent[d.release] = d;
const fmtN = (n: number) => n.toLocaleString('en-US');
function siblings(r: Reading): string {
  const d = descent[r.id]; if (!d || !d.instantiable) return '';
  const c = d.children; const placed = c.placed; const same = c.neutral;
  const parts: string[] = [];
  if (c.lengthened) parts.push(`${fmtN(c.lengthened)} live${c.lengthened === 1 ? 's' : ''} longer`);
  if (c.shortened) parts.push(`${fmtN(c.shortened)} die${c.shortened === 1 ? 's' : ''} sooner`);
  if (c.altered) parts.push(`${fmtN(c.altered)} die${c.altered === 1 ? 's' : ''} differently`);
  const clean = d.reaches?.clean_halt ?? 0;
  if (clean) parts.push(`${fmtN(clean)} halt${clean === 1 ? 's' : ''} cleanly`);
  const rest = parts.length ? `; ${parts.join(', ')}` : '';
  const noise = d.noiseIdentical === false ? ' Its own re-placements did not all agree, so the lab calls it environment-sensitive.' : '';
  return `In E1 the lab changed one byte at a time, every way: of its ${fmtN(placed)} one-byte siblings, ${fmtN(same)} behave exactly as it does${rest}.${noise} The siblings were made by infrastructure and exist only on the lab's chain.`;
}

const index = all.map((r) => ({
  id: r.id, status: r.status, program: r.program, by: r.installer, life: r.lifespan,
  clean: r.probes.some((p) => p.outcome === 'success'), dep: r.inputDependent, fut: r.future.length > 0, ret: r.probes.some((p) => p.returnDataLength > 0),
  verdict: verdict(r), would: wouldHaveBeen(r), trace: traceLine(r), sib: siblings(r) || undefined,
}));
writeFileSync(join(rdir, 'index.json'), JSON.stringify({ installer: CONTRACT, chainId, generatedAt, summary, chunk: CHUNK, readings: index }, null, 0));
const chunks = new Map<number, object[]>();
for (const r of all) {
  const k = Math.floor((r.id - 1) / CHUNK);
  if (!chunks.has(k)) chunks.set(k, []);
  chunks.get(k)!.push({ id: r.id, bytecode: r.bytecode, disassembly: r.disassembly, probes: r.probes.map((p) => ({ name: p.name, outcome: p.outcome, instructions: p.instructions, returnDataLength: p.returnDataLength })), installer: r.installer, requestedAt: r.requestedAt, installedAt: r.installedAt });
}
for (const [k, rows] of chunks) writeFileSync(join(rdir, `d-${k}.json`), JSON.stringify(rows, null, 0));
console.log(`\n${fresh.length} new · ${all.length} readings → ${OUT} · index + ${chunks.size} chunks → ${rdir}/`);
process.exit(0);
