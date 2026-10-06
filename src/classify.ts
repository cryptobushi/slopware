import type { ProbeResult } from './probe.js';

/**
 * Behavioral traits. A specimen may carry many. None of these is a judgement of correctness;
 * a program that dies at its first instruction has a behavior too.
 */
export type Trait =
  | 'BIRTH_FAILED'
  | 'STOPS'
  | 'RETURNS_DATA'
  | 'SUCCESS_NO_RETURN'
  | 'REVERTS'
  | 'INVALID_OPCODE'
  | 'STACK_UNDERFLOW'
  | 'STACK_OVERFLOW'
  | 'BAD_JUMP'
  | 'OUT_OF_GAS'
  | 'STATE_READ'
  | 'STATE_WRITE'
  | 'EMITS_LOG'
  | 'EXTERNAL_CALL'
  | 'CONTRACT_CREATION_ATTEMPT'
  | 'HASHING'
  | 'BRANCHING'
  | 'MEMORY'
  | 'CALLDATA_DEPENDENT'
  | 'VALUE_DEPENDENT'
  | 'DIES_AT_FIRST_INSTRUCTION'
  | 'FUTURE_OPCODE'
  | 'UNKNOWN';

export interface Classification {
  /** the single label a human reads first */
  primary: string;
  traits: Trait[];
  /** instructions executed before the first halt, by probe */
  lifespan: Record<string, number>;
  notes: string[];
}

export function classify(probes: ProbeResult[], born: boolean): Classification {
  const traits = new Set<Trait>();
  const notes: string[] = [];
  const lifespan: Record<string, number> = {};
  if (!born) return { primary: 'BIRTH_FAILED', traits: ['BIRTH_FAILED'], lifespan, notes };

  for (const p of probes) {
    lifespan[p.name[0]] = p.instructionCount;
    switch (p.outcome) {
      case 'success':
        traits.add(p.returnDataLength > 0 ? 'RETURNS_DATA' : p.lastOp === 'STOP' || p.instructionCount === 0 ? 'STOPS' : 'SUCCESS_NO_RETURN');
        break;
      case 'revert': traits.add('REVERTS'); break;
      case 'invalid_opcode': traits.add('INVALID_OPCODE'); break;
      case 'stack_underflow': traits.add('STACK_UNDERFLOW'); break;
      case 'stack_overflow': traits.add('STACK_OVERFLOW'); break;
      case 'bad_jump': traits.add('BAD_JUMP'); break;
      case 'out_of_gas': traits.add('OUT_OF_GAS'); break;
      default: traits.add('UNKNOWN');
    }
    if (p.storageReads) traits.add('STATE_READ');
    if (p.storageWrites) traits.add('STATE_WRITE');
    if (p.logs) traits.add('EMITS_LOG');
    if (p.calls) traits.add('EXTERNAL_CALL');
    if (p.creates) traits.add('CONTRACT_CREATION_ATTEMPT');
    if (p.keccaks) traits.add('HASHING');
    if (p.jumps) traits.add('BRANCHING');
    if (p.memoryOps) traits.add('MEMORY');
    if (p.instructionCount <= 1 && p.outcome !== 'success') traits.add('DIES_AT_FIRST_INSTRUCTION');
    if (p.rawError && /notactivated/i.test(p.rawError)) { traits.add('FUTURE_OPCODE'); notes.push(`${p.name}: halted on ${p.lastOp} — an EOF opcode the specification names but legacy code cannot execute`); }
    if (p.rawError && p.error && p.rawError !== p.error) notes.push(`${p.name}: tracer said ${p.rawError}; classified as ${p.outcome} from stack depth`);
  }

  // behaviour that differs across inputs — judged only on probes the instrument actually ran
  const ran = probes.filter((p) => !(p.error ?? '').startsWith('instrument:'));
  const sig = (p: ProbeResult) => `${p.outcome}|${p.instructionCount}|${p.returnData}`;
  const calldataProbes = ran.filter((p) => 'ABCD'.includes(p.name[0]));
  if (calldataProbes.length > 1 && new Set(calldataProbes.map(sig)).size > 1) traits.add('CALLDATA_DEPENDENT');
  const a = ran.find((p) => p.name[0] === 'A'), e = ran.find((p) => p.name[0] === 'E');
  if (a && e && sig(a) !== sig(e)) traits.add('VALUE_DEPENDENT');
  if (ran.length < probes.length) notes.push(`${probes.length - ran.length} probe(s) failed in the instrument, not the program`);

  // a primary label: the halt reason of the empty-calldata probe, or what it did if it lived
  const first = a ?? probes[0];
  let primary = 'UNKNOWN';
  if (first) {
    primary = first.outcome === 'success'
      ? (first.returnDataLength ? 'RETURNS_DATA' : first.instructionCount <= 1 ? 'STOPS' : 'SUCCESS_NO_RETURN')
      : first.outcome.toUpperCase();
  }
  if (traits.size === 0) traits.add('UNKNOWN');
  return { primary, traits: [...traits], lifespan, notes };
}
