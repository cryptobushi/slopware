/**
 * The readings' sentences, generated once here so the page downloads text instead of traces.
 * A life, told from the trace: what it did, how it fell, and what it would have done.
 * Moved verbatim from slopware/site/readings.html on 2026-10-08 so the page could get lighter.
 */

export interface ReadingLike {
  status: string;
  disassembly: { pc: number; name: string; imm: string; truncated: boolean }[];
  probes: { name: string; outcome: string; rawError?: string; instructions: number; ops: string[]; returnDataLength: number }[];
  inputDependent: boolean;
  notable: string[]; future: string[]; undefinedBytes: number;
}

const SPEAK: Record<string, string> = {
  SELFDESTRUCT: 'ended itself', CREATE: 'had a child', CREATE2: 'had a child at a chosen address',
  CALL: 'called someone', CALLCODE: 'called someone', DELEGATECALL: 'let someone else act in its name', STATICCALL: 'asked someone a question',
  SSTORE: 'remembered something for good', TSTORE: 'remembered something for a moment', SLOAD: 'checked its memory', TLOAD: 'checked its short-term memory',
  LOG0: 'shouted into the log', LOG1: 'shouted into the log', LOG2: 'shouted into the log', LOG3: 'shouted into the log', LOG4: 'shouted into the log',
  JUMP: 'gone somewhere else', JUMPI: 'made a decision', JUMPDEST: 'marked a place to come back to',
  RETURN: 'given an answer', REVERT: 'taken it all back', STOP: 'rested', INVALID: 'stopped on purpose',
  KECCAK256: 'hashed something', ORIGIN: 'looked at who started this', CALLER: 'looked at who was calling',
  SELFBALANCE: 'checked its wallet', BALANCE: "checked someone's wallet", ADDRESS: 'checked its own address',
  TIMESTAMP: 'looked at the clock', NUMBER: 'looked at the clock', BLOCKHASH: 'looked at the past', PREVRANDAO: 'rolled the dice', BLOBHASH: 'looked at the blobs',
  CHAINID: 'asked which world it was in', CODESIZE: 'measured itself', CODECOPY: 'read itself', EXTCODESIZE: 'measured someone else', EXTCODECOPY: 'read someone else', EXTCODEHASH: 'fingerprinted someone else',
  CALLDATASIZE: 'listened for input', CALLDATALOAD: 'listened for input', CALLDATACOPY: 'listened for input', CALLVALUE: 'counted the money it was sent',
  RETURNDATASIZE: 'checked for an answer', RETURNDATACOPY: 'read an answer', GAS: 'checked how much time was left', GASLIMIT: 'checked the size of the day', GASPRICE: 'checked the price of things', BASEFEE: 'checked the price of things', BLOBBASEFEE: 'checked the price of things', COINBASE: 'looked at who built the block',
  MSIZE: 'measured its desk', MLOAD: 'rummaged in memory', MSTORE: 'put something down', MSTORE8: 'put something down', MCOPY: 'moved something around', PC: 'checked where it was',
};
const say = (name: string): string => {
  if (SPEAK[name]) return SPEAK[name];
  if (/^PUSH/.test(name)) { const k = Number(name.slice(4)); return `picked up ${k === 0 ? 'nothing' : k === 1 ? 'a byte' : k + ' bytes'}`; }
  if (/^(DUP|SWAP)/.test(name)) return 'shuffled what it was holding';
  if (/^(ADD|SUB|MUL|DIV|SDIV|MOD|SMOD|ADDMOD|MULMOD|EXP|SIGNEXTEND)$/.test(name)) return 'done some arithmetic';
  if (/^(LT|GT|SLT|SGT|EQ|ISZERO)$/.test(name)) return 'compared two things';
  if (/^(AND|OR|XOR|NOT|BYTE|SHL|SHR|SAR|CLZ)$/.test(name)) return 'fiddled with some bits';
  if (/^(POP)$/.test(name)) return 'dropped something';
  return name.toLowerCase();
};
// base forms, for what a program reached for and could not have
const REACH: Record<string, string> = {
  SELFDESTRUCT: 'end itself', CREATE: 'have a child', CREATE2: 'have a child', CALL: 'call someone', CALLCODE: 'call someone', DELEGATECALL: 'let someone act in its name', STATICCALL: 'ask someone a question',
  SSTORE: 'remember something for good', TSTORE: 'remember something for a moment', SLOAD: 'check its memory', TLOAD: 'check its short-term memory',
  LOG0: 'shout into the log', LOG1: 'shout into the log', LOG2: 'shout into the log', LOG3: 'shout into the log', LOG4: 'shout into the log',
  JUMP: 'go somewhere else', JUMPI: 'make a decision', RETURN: 'give an answer', REVERT: 'take it all back', KECCAK256: 'hash something',
  BALANCE: "check someone's wallet", BLOCKHASH: 'look at the past', BLOBHASH: 'look at the blobs', EXTCODESIZE: 'measure someone else', EXTCODECOPY: 'read someone else', EXTCODEHASH: 'fingerprint someone else',
  CALLDATALOAD: 'listen for input', CALLDATACOPY: 'listen for input', CODECOPY: 'read itself', RETURNDATACOPY: 'read an answer',
  MLOAD: 'rummage in memory', MSTORE: 'put something down', MSTORE8: 'put something down', MCOPY: 'move something around', POP: 'drop something',
};
const reach = (name: string): string => REACH[name] || (/^(DUP|SWAP)/.test(name) ? 'shuffle what it was holding' : /^(ADD|SUB|MUL|DIV|SDIV|MOD|SMOD|ADDMOD|MULMOD|EXP|SIGNEXTEND)$/.test(name) ? 'do some arithmetic' : /^(LT|GT|SLT|SGT|EQ|ISZERO)$/.test(name) ? 'compare two things' : /^(AND|OR|XOR|NOT|BYTE|SHL|SHR|SAR|CLZ)$/.test(name) ? 'fiddle with some bits' : `do ${name}`);
const list = (xs: string[]): string => xs.length <= 1 ? xs.join('') : xs.length === 2 ? `${xs[0]} and ${xs[1]}` : `${xs.slice(0, -1).join(', ')}, and ${xs[xs.length - 1]}`;
const cap = (t: string): string => t.charAt(0).toUpperCase() + t.slice(1);

export function verdict(r: ReadingLike): string {
  if (r.status === 'rejected') return 'Ethereum would not let this one exist: its first byte is 0xEF, the one byte the protocol refuses. The bytes are kept. Nothing was born.';
  const a = r.probes[0]; if (!a) return '';
  const d = r.disassembly;
  const n = a.instructions;
  const at = d[Math.min(Math.max(0, n - 1), d.length - 1)] || d[0];
  const executed = d.slice(0, Math.max(0, n - 1)).map((i) => i.name.replace(' (not activated)', ''));
  const did = executed.length ? cap(list([...new Set(executed.map(say))])) + '. ' : '';
  const dep = r.inputDependent ? ' It answers differently depending on what you say to it.' : '';
  const bare = at.name.replace(' (not activated)', '');
  if (a.outcome === 'success') {
    if (n <= 1) return `Born, breathed once, and rested. It does nothing, successfully.${dep}`;
    return `${did}Then it ${a.returnDataLength ? `gave an answer, ${a.returnDataLength} bytes long` : 'rested'}. Alive.${dep}`;
  }
  let fall: string;
  if (/^UNDEFINED/.test(at.name)) fall = `${n <= 1 ? 'Its first word' : 'Its next word'} was not a word: ${bare.replace('UNDEFINED(', '').replace(')', '')} is not an instruction. It died ${n <= 1 ? 'before its first breath' : 'there'}.`;
  else if (/not activated/.test(at.name)) fall = `${n <= 1 ? 'Its first word' : 'Its next word'}, ${bare}, is from a language Ethereum does not speak yet. It died ${n <= 1 ? 'before its first breath' : 'mid-sentence'}.`;
  else if (a.outcome === 'stack_underflow') fall = `${n <= 1 ? 'It reached' : 'Then it reached'} to ${reach(bare)} with ${n <= 1 ? 'empty hands' : 'less in its hands than that takes'}, and fell.`;
  else if (a.outcome === 'bad_jump') fall = 'Then it tried to go somewhere that is not a place, and fell.';
  else if (a.outcome === 'out_of_gas' || /memory(limit)?oog/i.test(a.rawError || '')) fall = `${n <= 1 ? 'It asked' : 'Then it asked'} for more room than the world could give (${bare}) and starved.`;
  else if (a.outcome === 'revert') fall = 'Then it took everything back and went quiet.';
  else fall = `Then it fell (${a.outcome.replace('_', ' ')}).`;
  return `${did}${fall}${dep}`;
}

export function wouldHaveBeen(r: ReadingLike): string {
  if (r.status !== 'installed') return '';
  const a = r.probes[0]; const reached = a ? a.instructions : 0;
  const later = r.disassembly.slice(reached).map((i) => i.name.replace(' (not activated)', ''));
  const wishes = [...new Set(later.filter((n) => r.notable.includes(n)).map((n) => SPEAK[n]).filter(Boolean))];
  const bits: string[] = [];
  if (wishes.length) bits.push(a && a.outcome === 'success' ? `Past where it stopped, unread, it would have ${list(wishes)}.` : `Had it lived, it would have ${list(wishes)}.`);
  if (r.future.length) bits.push(`It carries ${r.future.length === 1 ? 'one word' : r.future.length + ' words'} from a language Ethereum will speak later: ${r.future.join(', ')}.`);
  const pushes = r.disassembly.filter((i) => i.imm).reduce((s, i) => s + i.imm.length / 2, 0);
  if (pushes >= 32) bits.push(`${pushes} of its 64 bytes are luggage.`);
  if (r.undefinedBytes >= 24) bits.push(`${r.undefinedBytes} of its bytes are not words at all.`);
  return bits.join(' ');
}

/** The trace line: the instructions probe A executed, by name, capped so a looping program cannot bloat the index. */
export function traceLine(r: ReadingLike, max = 40): string {
  const a = r.probes[0];
  if (!a || !a.ops.length) return r.status === 'installed' ? '(halted before the first instruction)' : '';
  const names = a.ops.map((o) => o.split(' ')[0]);
  return names.length > max ? `${names.slice(0, max).join(' · ')} · … (${names.length} in all)` : names.join(' · ');
}
