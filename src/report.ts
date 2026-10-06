/** Run statistics: the distribution is the work. */
export interface Stats {
  count: number; bytes: number;
  born: number; birthFailed: number; birthFailReasons: Record<string, number>;
  probesRun: number; execSuccess: number;
  instructions: { mean: number; median: number; max: number; p90: number };
  failureModes: Record<string, number>;
  pct: Record<string, number>;
  primary: Record<string, number>;
  scoreHistogram: Record<string, number>;
  topIds: string[];
}

const pct = (n: number, d: number) => (d ? Math.round((n / d) * 10000) / 100 : 0);

export function computeStats(specimens: any[], bytes: number): Stats {
  const born = specimens.filter((s) => s.birth.status === 'deployed');
  const failReasons: Record<string, number> = {};
  for (const s of specimens) if (s.birth.status !== 'deployed') failReasons[s.birth.reason ?? s.birth.status] = (failReasons[s.birth.reason ?? s.birth.status] ?? 0) + 1;
  const probes = born.flatMap((s) => s.probes as any[]);
  const lives = probes.map((p) => p.instructionCount as number).sort((a, b) => a - b);
  const q = (f: number) => (lives.length ? lives[Math.min(lives.length - 1, Math.floor(f * lives.length))] : 0);
  const failureModes: Record<string, number> = {};
  for (const p of probes) failureModes[p.outcome] = (failureModes[p.outcome] ?? 0) + 1;
  const has = (trait: string) => born.filter((s) => s.classification.traits.includes(trait)).length;
  const primary: Record<string, number> = {};
  for (const s of specimens) primary[s.classification.primary] = (primary[s.classification.primary] ?? 0) + 1;
  const hist: Record<string, number> = {};
  for (const s of specimens) { const b = s.score ? Math.floor(Math.max(0, s.score.total) / 10) * 10 : 0; const k = `${b}-${b + 9}`; hist[k] = (hist[k] ?? 0) + 1; }
  const top = [...specimens].sort((a, b) => (b.score?.total ?? 0) - (a.score?.total ?? 0)).slice(0, 10).map((s) => s.id);
  return {
    count: specimens.length, bytes,
    born: born.length, birthFailed: specimens.length - born.length, birthFailReasons: failReasons,
    probesRun: probes.length, execSuccess: probes.filter((p) => p.outcome === 'success').length,
    instructions: { mean: lives.length ? Math.round((lives.reduce((a, b) => a + b, 0) / lives.length) * 100) / 100 : 0, median: q(0.5), p90: q(0.9), max: lives.length ? lives[lives.length - 1] : 0 },
    failureModes,
    pct: {
      birthSuccess: pct(born.length, specimens.length),
      execSuccess: pct(probes.filter((p) => p.outcome === 'success').length, probes.length),
      returnsData: pct(has('RETURNS_DATA'), born.length),
      stateRead: pct(has('STATE_READ'), born.length),
      stateWrite: pct(has('STATE_WRITE'), born.length),
      branching: pct(has('BRANCHING'), born.length),
      externalCall: pct(has('EXTERNAL_CALL'), born.length),
      create: pct(has('CONTRACT_CREATION_ATTEMPT'), born.length),
      outOfGas: pct(has('OUT_OF_GAS'), born.length),
      calldataDependent: pct(has('CALLDATA_DEPENDENT'), born.length),
      valueDependent: pct(has('VALUE_DEPENDENT'), born.length),
      diesAtFirstInstruction: pct(has('DIES_AT_FIRST_INSTRUCTION'), born.length),
      emitsLog: pct(has('EMITS_LOG'), born.length),
      hashing: pct(has('HASHING'), born.length),
    },
    primary, scoreHistogram: hist, topIds: top,
  };
}

const fmt = (n: number) => n.toLocaleString('en-US');

export function printStats(s: Stats) {
  const row = (k: string, v: string | number) => console.log(`  ${k.padEnd(30)} ${String(v).padStart(10)}`);
  console.log(`SLOPWARE — lab · ${fmt(s.count)} specimens · ${s.bytes} bytes each`);
  row('INSTALLED', `${fmt(s.born)} (${s.pct.birthSuccess}%)`);
  row('REFUSED', fmt(s.birthFailed));
  for (const [k, v] of Object.entries(s.birthFailReasons)) row(`  ${k.slice(0, 28)}`, fmt(v));
  row('PROBES RUN', fmt(s.probesRun));
  row('EXECUTION SUCCESS', `${fmt(s.execSuccess)} (${s.pct.execSuccess}%)`);
  row('INSTRUCTIONS mean / median', `${s.instructions.mean} / ${s.instructions.median}`);
  row('INSTRUCTIONS p90 / max', `${s.instructions.p90} / ${s.instructions.max}`);
  console.log(`  FAILURE MODES (per probe)`);
  for (const [k, v] of Object.entries(s.failureModes).sort((a, b) => b[1] - a[1])) row(`    ${k}`, `${fmt(v)} (${pct(v, s.probesRun)}%)`);
  console.log(`  TRAITS (% of installed specimens)`);
  for (const k of ['diesAtFirstInstruction', 'returnsData', 'calldataDependent', 'valueDependent', 'stateRead', 'stateWrite', 'branching', 'hashing', 'emitsLog', 'externalCall', 'create', 'outOfGas']) row(`    ${k}`, `${s.pct[k]}%`);
  console.log(`  PRIMARY CLASSIFICATION`);
  for (const [k, v] of Object.entries(s.primary).sort((a, b) => b[1] - a[1])) row(`    ${k}`, fmt(v));
  console.log(`  INTERESTINGNESS`);
  for (const [k, v] of Object.entries(s.scoreHistogram).sort((a, b) => Number(a[0].split('-')[0]) - Number(b[0].split('-')[0]))) row(`    ${k}`, fmt(v));
  row('MOST INTERESTING', s.topIds.slice(0, 5).map((i) => `#${i}`).join(' '));
}
