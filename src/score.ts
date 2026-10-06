import type { Classification } from './classify.js';
import type { ProbeResult } from './probe.js';

/**
 * Interestingness: a transparent heuristic to help a human find specimens worth looking at.
 * It is not a judgement of worth — the dead and the boring are part of the work. Change freely.
 *
 *   life          +0.5 per instruction of the longest life, capped at +60
 *   clean halt    +15 if any probe halted by STOP/RETURN; +10 more if any returned data
 *   dependence    +20 CALLDATA_DEPENDENT · +15 VALUE_DEPENDENT
 *   state         +15 STATE_READ · +25 STATE_WRITE
 *   effects       +20 EMITS_LOG · +25 EXTERNAL_CALL · +30 CONTRACT_CREATION_ATTEMPT
 *   computation   +15 HASHING · +15 BRANCHING · +5 MEMORY
 *   out of gas    +30 (it kept going until we stopped it)
 *   revert data   +10 if a REVERT carried data
 *   dead on arrival −20 if every probe died at its first instruction
 *
 * Trait credits count only instructions that actually executed (the one that raised the
 * exception did not).
 */
export function score(probes: ProbeResult[], cls: Classification): { total: number; parts: Record<string, number> } {
  const parts: Record<string, number> = {};
  const add = (k: string, v: number) => { if (v) parts[k] = (parts[k] ?? 0) + v; };
  const t = new Set(cls.traits);
  const longest = Math.max(0, ...probes.map((p) => p.instructionCount));
  add('life', Math.min(60, Math.round(longest * 0.5 * 10) / 10));
  if (probes.some((p) => p.outcome === 'success')) add('clean halt', 15);
  if (probes.some((p) => p.outcome === 'success' && p.returnDataLength > 0)) add('returns data', 10);
  if (t.has('CALLDATA_DEPENDENT')) add('calldata dependent', 20);
  if (t.has('VALUE_DEPENDENT')) add('value dependent', 15);
  if (t.has('STATE_READ')) add('state read', 15);
  if (t.has('STATE_WRITE')) add('state write', 25);
  if (t.has('EMITS_LOG')) add('logs', 20);
  if (t.has('EXTERNAL_CALL')) add('external call', 25);
  if (t.has('CONTRACT_CREATION_ATTEMPT')) add('create', 30);
  if (t.has('HASHING')) add('hashing', 15);
  if (t.has('BRANCHING')) add('branching', 15);
  if (t.has('MEMORY')) add('memory', 5);
  if (t.has('OUT_OF_GAS')) add('out of gas', 30);
  if (probes.some((p) => p.outcome === 'revert' && p.returnDataLength > 0)) add('revert data', 10);
  if (probes.length && probes.every((p) => p.instructionCount <= 1 && p.outcome !== 'success')) add('dead on arrival', -20);
  const total = Object.values(parts).reduce((a, b) => a + b, 0);
  return { total: Math.round(total * 10) / 10, parts };
}
