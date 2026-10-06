import type { Hex } from 'viem';
import type { Chain } from './chain.js';
import { stackEffect } from './opcodes.js';

/** Hard ceiling for any single probe. A random program must never hang the explorer. */
export const PROBE_GAS = 1_000_000;

export type Outcome =
  | 'success'
  | 'revert'
  | 'invalid_opcode'
  | 'stack_underflow'
  | 'stack_overflow'
  | 'bad_jump'
  | 'out_of_gas'
  | 'other_halt';

export interface StructLog {
  pc: number;
  op: string;
  gas: number;
  gasCost: number;
  depth: number;
  error?: string;
  stack?: string[];
  storage?: Record<string, string>;
}

export interface ProbeResult {
  name: string;
  calldata: Hex;
  value: string; // wei, decimal
  outcome: Outcome;
  error?: string;
  /** the tracer's own label, verbatim (revm/anvil); may disagree with `outcome` */
  rawError?: string;
  gasUsed: number;
  returnData: Hex;
  returnDataLength: number;
  /** opcodes in execution order (depth 0 and nested) */
  ops: string[];
  instructionCount: number;
  opCounts: Record<string, number>;
  maxStackDepth?: number;
  maxDepth: number;
  lastOp?: string;
  storageWrites: number;
  storageReads: number;
  logs: number;
  calls: number;
  creates: number;
  keccaks: number;
  jumps: number;
  memoryOps: number;
}

export interface ProbeSpec {
  name: string;
  calldata: Hex;
  value: bigint;
}

/** One traced call. Uses debug_traceCall so nothing is committed and every opcode is observed. */
export async function probe(chain: Chain, address: Hex, spec: ProbeSpec): Promise<ProbeResult> {
  // Under concurrent workers anvil can resolve `latest` to a block it has not finished indexing
  // (BlockOutOfRangeError). That is the instrument, not the program: retry briefly.
  let trace: any;
  for (let attempt = 0; ; attempt++) {
    try {
      trace = await chain.request('debug_traceCall', [
        { from: chain.from, to: address, data: spec.calldata, value: `0x${spec.value.toString(16)}`, gas: `0x${PROBE_GAS.toString(16)}` },
        'latest',
        { disableStorage: true, disableMemory: true, disableStack: true, enableReturnData: true },
      ]);
      break;
    } catch (e: any) {
      const transient = /BlockOutOfRange|block height/i.test(String(e.message ?? e));
      if (!transient || attempt >= 4) throw e;
      await new Promise((r) => setTimeout(r, 20 * (attempt + 1)));
    }
  }
  const logs: StructLog[] = trace.structLogs ?? [];
  // track stack depth ourselves (depth-0 frame only): the tracer's stack dumps are too large for looping programs
  let depth = 0, maxStack = 0, depthAtFail: number | undefined;
  for (const l of logs) {
    if (l.depth && l.depth > 1) continue;
    if (l.error) { depthAtFail = depth; break; }
    const [pops, pushes] = stackEffect(l.op);
    depth = Math.max(0, depth - pops) + pushes;
    if (depth > maxStack) maxStack = depth;
  }
  const ops = logs.map((l) => l.op);
  // an instruction that raised the exception did not execute; count only the ones that did
  const executed = logs.filter((l) => !l.error).map((l) => l.op);
  const opCounts: Record<string, number> = {};
  for (const o of executed) opCounts[o] = (opCounts[o] ?? 0) + 1;
  const count = (...names: string[]) => names.reduce((n, k) => n + (opCounts[k] ?? 0), 0);
  const last = logs[logs.length - 1];
  const failing = logs.find((l) => l.error);
  const rawErr = failing?.error ?? (trace.failed && !last ? 'failed before first instruction' : undefined);
  const normalized = rawErr ? normalizeError(rawErr) : undefined;
  const outcome = classifyOutcome(Boolean(trace.failed), last?.op, normalized, depthAtFail);
  const errText = normalized && outcome === 'stack_underflow' && !/underflow/i.test(normalized) ? 'StackUnderflow' : normalized;
  const returnData: Hex = normalizeHex(trace.returnValue);

  return {
    name: spec.name,
    calldata: spec.calldata,
    value: spec.value.toString(),
    outcome,
    error: errText,
    rawError: normalized,
    gasUsed: Number(trace.gas ?? 0),
    returnData,
    returnDataLength: (returnData.length - 2) / 2,
    ops,
    instructionCount: ops.length,
    opCounts,
    maxStackDepth: maxStack,
    maxDepth: logs.reduce((m, l) => Math.max(m, l.depth ?? 1), 1),
    lastOp: last?.op,
    storageWrites: count('SSTORE', 'TSTORE'),
    storageReads: count('SLOAD', 'TLOAD'),
    logs: count('LOG0', 'LOG1', 'LOG2', 'LOG3', 'LOG4'),
    calls: count('CALL', 'CALLCODE', 'DELEGATECALL', 'STATICCALL'),
    creates: count('CREATE', 'CREATE2'),
    keccaks: count('KECCAK256', 'SHA3'),
    jumps: count('JUMP', 'JUMPI'),
    memoryOps: count('MSTORE', 'MSTORE8', 'MLOAD', 'MCOPY', 'CALLDATACOPY', 'CODECOPY', 'RETURNDATACOPY', 'EXTCODECOPY'),
  };
}

function classifyOutcome(failed: boolean, lastOp: string | undefined, err: string | undefined, stackLen: number | undefined): Outcome {
  if (!failed) return 'success';
  const e = (err ?? '').toLowerCase();
  // revm labels DUPn on a short stack "StackOverflow"; decide from the stack depth instead
  const m = lastOp?.match(/^(DUP|SWAP)(\d+)$/);
  if (m && stackLen !== undefined) {
    const need = Number(m[2]) + (m[1] === 'SWAP' ? 1 : 0);
    if (stackLen < need) return 'stack_underflow';
  }
  if (lastOp === 'REVERT' && !e) return 'revert';
  if (e.includes('out of gas') || e.includes('outofgas')) return 'out_of_gas';
  if (e.includes('notactivated')) return 'invalid_opcode'; // an opcode the spec knows but legacy code may not use
  if (e.includes('underflow')) return 'stack_underflow';
  if (e.includes('overflow') && e.includes('stack')) return 'stack_overflow';
  if (e.includes('jump')) return 'bad_jump';
  if (e.includes('invalid') || e.includes('opcode') || e.includes('not found') || lastOp === 'INVALID' || lastOp?.startsWith('UNDEFINED') || lastOp === 'opcode 0x') return 'invalid_opcode';
  if (lastOp === 'REVERT') return 'revert';
  return 'other_halt';
}

/** Anvil reports revm errors as Rust debug strings like `Some(StackUnderflow)`; keep the name only. */
function normalizeError(e: string): string {
  return e.replace(/^Some\((.*)\)$/, '$1');
}

function normalizeHex(v: unknown): Hex {
  if (typeof v !== 'string' || v.length === 0) return '0x';
  return (v.startsWith('0x') ? v : `0x${v}`) as Hex;
}

/**
 * For a specimen that ran out of gas: does more gas change what it does? Re-run the same probe at
 * several ceilings and report outcome, instructions and the tail of the trace at each.
 */
export async function gasSweep(chain: Chain, address: Hex, spec: ProbeSpec, ceilings: number[]) {
  const out: { gas: number; outcome: Outcome; instructions?: number; gasUsed: number; tail?: string[]; loopSignature?: string; error?: string }[] = [];
  for (const gas of ceilings) {
    if (gas > 1_000_000) {
      // a looping program at this ceiling would produce millions of struct logs; ask only how it ended
      const t = await chain.request('debug_traceCall', [
        { from: chain.from, to: address, data: spec.calldata, value: `0x${spec.value.toString(16)}`, gas: `0x${gas.toString(16)}` },
        'latest',
        { tracer: 'callTracer' },
      ]);
      const err: string | undefined = t.error ? normalizeError(String(t.error)) : undefined;
      const gasUsed = Number(t.gasUsed ?? 0);
      out.push({ gas, outcome: err ? classifyOutcome(true, undefined, err, undefined) : 'success', gasUsed, error: err });
      continue;
    }
    const trace = await chain.request('debug_traceCall', [
      { from: chain.from, to: address, data: spec.calldata, value: `0x${spec.value.toString(16)}`, gas: `0x${gas.toString(16)}` },
      'latest',
      { disableStorage: true, disableMemory: true, disableStack: true },
    ]);
    const logs: StructLog[] = trace.structLogs ?? [];
    const last = logs[logs.length - 1];
    const err = logs.find((l) => l.error)?.error;
    const outcome = classifyOutcome(Boolean(trace.failed), last?.op, err ? normalizeError(err) : undefined, undefined);
    // a repeating pc sequence in the last 64 steps suggests a loop
    const pcs = logs.slice(-64).map((l) => l.pc);
    let loopSignature: string | undefined;
    for (let period = 1; period <= 32 && !loopSignature; period++) {
      if (pcs.length < period * 2) break;
      let ok = true;
      for (let i = pcs.length - period; i < pcs.length; i++) if (pcs[i] !== pcs[i - period]) { ok = false; break; }
      if (ok) loopSignature = logs.slice(-period).map((l) => `${l.pc}:${l.op}`).join(' ');
    }
    out.push({ gas, outcome, instructions: logs.length, gasUsed: Number(trace.gas ?? 0), tail: logs.slice(-12).map((l) => `${l.pc} ${l.op}`), loopSignature });
  }
  return out;
}

/** The standard probe set. Random payloads are drawn from the run's own byte source for reproducibility. */
export function standardProbes(random32: Uint8Array, selector: Uint8Array, arg32: Uint8Array): ProbeSpec[] {
  const h = (b: Uint8Array) => `0x${Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')}` as Hex;
  return [
    { name: 'A empty calldata', calldata: '0x', value: 0n },
    { name: 'B 32 zero bytes', calldata: `0x${'00'.repeat(32)}`, value: 0n },
    { name: 'C 32 random bytes', calldata: h(random32), value: 0n },
    { name: 'D selector + arg', calldata: `0x${h(selector).slice(2)}${h(arg32).slice(2)}`, value: 0n },
    { name: 'E value 1 wei', calldata: '0x', value: 1n },
  ];
}
