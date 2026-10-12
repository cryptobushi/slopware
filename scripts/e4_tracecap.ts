// E4 Amendment 2 verification: through the real probe path (chain.ts transport + probe.ts tracer), a tight loop that burns the
// full 1,000,000 probe gas (~245k executed instructions, ~21 MB step trace) must be measured and classified, not rejected.
// Usage: anvil --port 8898 &  then  npx tsx scripts/e4_tracecap.ts
import { connect } from '../src/chain.js';
import { probe, standardProbes } from '../src/probe.js';
import { fromHex } from '../src/opcodes.js';
import { readFileSync } from 'node:fs';
const world = JSON.parse(readFileSync(new URL('../slopware/experiments/E4/world-v0.json', import.meta.url), 'utf8'));
const specs = standardProbes(fromHex(world.probes.random32), fromHex(world.probes.selector), fromHex(world.probes.arg32));
const chain = await connect('http://127.0.0.1:8898');
const A = '0x00000000000000000000000000000000000000aa';
// tight loop: JUMPDEST PUSH1 0 JUMP — burns the whole probe gas, ~245k executed instructions, ~21 MB step trace
await chain.request('anvil_setCode', [A, '0x5b600056']);
const t0 = Date.now();
const r = await probe(chain, A as any, specs[0]);
console.log(JSON.stringify({ probe: r.name, outcome: r.outcome, instructionCount: r.instructionCount, lastOp: r.lastOp, error: r.error, ms: Date.now() - t0 }));
// short finite program for contrast: PUSH1 0 STOP
await chain.request('anvil_setCode', [A, '0x600000']);
const r2 = await probe(chain, A as any, specs[0]);
console.log(JSON.stringify({ probe: r2.name, outcome: r2.outcome, instructionCount: r2.instructionCount, lastOp: r2.lastOp }));
process.exit(0);
