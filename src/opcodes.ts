/** EVM opcode table (Cancun/Prague). Unlisted bytes are undefined → INVALID on execution. */
export const OPCODES: Record<number, string> = {
  0x00: 'STOP', 0x01: 'ADD', 0x02: 'MUL', 0x03: 'SUB', 0x04: 'DIV', 0x05: 'SDIV', 0x06: 'MOD', 0x07: 'SMOD',
  0x08: 'ADDMOD', 0x09: 'MULMOD', 0x0a: 'EXP', 0x0b: 'SIGNEXTEND',
  0x10: 'LT', 0x11: 'GT', 0x12: 'SLT', 0x13: 'SGT', 0x14: 'EQ', 0x15: 'ISZERO', 0x16: 'AND', 0x17: 'OR',
  0x18: 'XOR', 0x19: 'NOT', 0x1a: 'BYTE', 0x1b: 'SHL', 0x1c: 'SHR', 0x1d: 'SAR',
  0x20: 'KECCAK256',
  0x30: 'ADDRESS', 0x31: 'BALANCE', 0x32: 'ORIGIN', 0x33: 'CALLER', 0x34: 'CALLVALUE', 0x35: 'CALLDATALOAD',
  0x36: 'CALLDATASIZE', 0x37: 'CALLDATACOPY', 0x38: 'CODESIZE', 0x39: 'CODECOPY', 0x3a: 'GASPRICE',
  0x3b: 'EXTCODESIZE', 0x3c: 'EXTCODECOPY', 0x3d: 'RETURNDATASIZE', 0x3e: 'RETURNDATACOPY', 0x3f: 'EXTCODEHASH',
  0x40: 'BLOCKHASH', 0x41: 'COINBASE', 0x42: 'TIMESTAMP', 0x43: 'NUMBER', 0x44: 'PREVRANDAO', 0x45: 'GASLIMIT',
  0x46: 'CHAINID', 0x47: 'SELFBALANCE', 0x48: 'BASEFEE', 0x49: 'BLOBHASH', 0x4a: 'BLOBBASEFEE',
  0x50: 'POP', 0x51: 'MLOAD', 0x52: 'MSTORE', 0x53: 'MSTORE8', 0x54: 'SLOAD', 0x55: 'SSTORE', 0x56: 'JUMP',
  0x57: 'JUMPI', 0x58: 'PC', 0x59: 'MSIZE', 0x5a: 'GAS', 0x5b: 'JUMPDEST', 0x5c: 'TLOAD', 0x5d: 'TSTORE',
  0x5e: 'MCOPY', 0x5f: 'PUSH0',
  0xa0: 'LOG0', 0xa1: 'LOG1', 0xa2: 'LOG2', 0xa3: 'LOG3', 0xa4: 'LOG4',
  0xf0: 'CREATE', 0xf1: 'CALL', 0xf2: 'CALLCODE', 0xf3: 'RETURN', 0xf4: 'DELEGATECALL', 0xf5: 'CREATE2',
  0xfa: 'STATICCALL', 0xfd: 'REVERT', 0xfe: 'INVALID', 0xff: 'SELFDESTRUCT',
};
for (let i = 1; i <= 32; i++) OPCODES[0x5f + i] = `PUSH${i}`;
for (let i = 1; i <= 16; i++) OPCODES[0x7f + i] = `DUP${i}`;
for (let i = 1; i <= 16; i++) OPCODES[0x8f + i] = `SWAP${i}`;

export const DEFINED = new Set(Object.keys(OPCODES).map(Number));

/** [pops, pushes] for each defined opcode, so stack depth can be tracked from the instruction stream. */
export function stackEffect(name: string): [number, number] {
  if (name.startsWith('PUSH')) return [0, 1];
  if (name.startsWith('DUP')) { const n = Number(name.slice(3)); return [n, n + 1]; }
  if (name.startsWith('SWAP')) { const n = Number(name.slice(4)); return [n + 1, n + 1]; }
  if (name.startsWith('LOG')) return [2 + Number(name.slice(3)), 0];
  const t: Record<string, [number, number]> = {
    STOP: [0, 0], ADD: [2, 1], MUL: [2, 1], SUB: [2, 1], DIV: [2, 1], SDIV: [2, 1], MOD: [2, 1], SMOD: [2, 1], ADDMOD: [3, 1], MULMOD: [3, 1], EXP: [2, 1], SIGNEXTEND: [2, 1],
    LT: [2, 1], GT: [2, 1], SLT: [2, 1], SGT: [2, 1], EQ: [2, 1], ISZERO: [1, 1], AND: [2, 1], OR: [2, 1], XOR: [2, 1], NOT: [1, 1], BYTE: [2, 1], SHL: [2, 1], SHR: [2, 1], SAR: [2, 1],
    KECCAK256: [2, 1], ADDRESS: [0, 1], BALANCE: [1, 1], ORIGIN: [0, 1], CALLER: [0, 1], CALLVALUE: [0, 1], CALLDATALOAD: [1, 1], CALLDATASIZE: [0, 1], CALLDATACOPY: [3, 0],
    CODESIZE: [0, 1], CODECOPY: [3, 0], GASPRICE: [0, 1], EXTCODESIZE: [1, 1], EXTCODECOPY: [4, 0], RETURNDATASIZE: [0, 1], RETURNDATACOPY: [3, 0], EXTCODEHASH: [1, 1],
    BLOCKHASH: [1, 1], COINBASE: [0, 1], TIMESTAMP: [0, 1], NUMBER: [0, 1], PREVRANDAO: [0, 1], GASLIMIT: [0, 1], CHAINID: [0, 1], SELFBALANCE: [0, 1], BASEFEE: [0, 1], BLOBHASH: [1, 1], BLOBBASEFEE: [0, 1],
    POP: [1, 0], MLOAD: [1, 1], MSTORE: [2, 0], MSTORE8: [2, 0], SLOAD: [1, 1], SSTORE: [2, 0], JUMP: [1, 0], JUMPI: [2, 0], PC: [0, 1], MSIZE: [0, 1], GAS: [0, 1], JUMPDEST: [0, 0],
    TLOAD: [1, 1], TSTORE: [2, 0], MCOPY: [3, 0],
    CREATE: [3, 1], CALL: [7, 1], CALLCODE: [7, 1], RETURN: [2, 0], DELEGATECALL: [6, 1], CREATE2: [4, 1], STATICCALL: [6, 1], REVERT: [2, 0], INVALID: [0, 0], SELFDESTRUCT: [1, 0],
  };
  return t[name] ?? [0, 0];
}

/**
 * Opcodes that exist in the EVM specification but are not activated for legacy code (EOF:
 * EIP-663, EIP-4200, EIP-4750, EIP-6206, EIP-7069, EIP-7480, EIP-7620). Random bytecode can land
 * on one; revm halts it with NotActivated. Functionally an invalid opcode today — but a named one.
 */
export const NOT_ACTIVATED: Record<number, string> = {
  0xd0: 'DATALOAD', 0xd1: 'DATALOADN', 0xd2: 'DATASIZE', 0xd3: 'DATACOPY',
  0xe0: 'RJUMP', 0xe1: 'RJUMPI', 0xe2: 'RJUMPV', 0xe3: 'CALLF', 0xe4: 'RETF', 0xe5: 'JUMPF',
  0xe6: 'DUPN', 0xe7: 'SWAPN', 0xe8: 'EXCHANGE', 0xec: 'EOFCREATE', 0xee: 'RETURNCONTRACT',
  0xf7: 'RETURNDATALOAD', 0xf8: 'EXTCALL', 0xf9: 'EXTDELEGATECALL', 0xfb: 'EXTSTATICCALL',
};

export function pushSize(op: number): number {
  return op >= 0x60 && op <= 0x7f ? op - 0x5f : 0;
}

export interface Instruction {
  pc: number;
  op: number;
  name: string;
  /** PUSH immediate, hex without 0x; '' for non-PUSH */
  imm: string;
  /** immediate was cut off by the end of the code */
  truncated: boolean;
  defined: boolean;
}

/** Linear disassembly from pc 0, consuming PUSH immediates. Bytes inside immediates are data, not opcodes. */
export function disassemble(code: Uint8Array): Instruction[] {
  const out: Instruction[] = [];
  let pc = 0;
  while (pc < code.length) {
    const op = code[pc];
    const n = pushSize(op);
    const immBytes = code.subarray(pc + 1, pc + 1 + n);
    out.push({
      pc,
      op,
      name: OPCODES[op] ?? (NOT_ACTIVATED[op] ? `${NOT_ACTIVATED[op]} (not activated)` : `UNDEFINED(0x${op.toString(16).padStart(2, '0')})`),
      imm: n ? hex(immBytes) : '',
      truncated: n > 0 && immBytes.length < n,
      defined: DEFINED.has(op),
    });
    pc += 1 + n;
  }
  return out;
}

export function formatDisassembly(code: Uint8Array): string {
  return disassemble(code)
    .map((i) => {
      const pc = i.pc.toString(16).padStart(2, '0');
      const imm = i.imm ? ` 0x${i.imm}${i.truncated ? '  (truncated)' : ''}` : '';
      return `${pc} ${i.name}${imm}`;
    })
    .join('\n');
}

/** JUMPDEST positions that are real (not inside PUSH data) — the only valid jump targets. */
export function validJumpDests(code: Uint8Array): Set<number> {
  const s = new Set<number>();
  for (const i of disassemble(code)) if (i.op === 0x5b) s.add(i.pc);
  return s;
}

export function hex(b: Uint8Array): string {
  return Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
}

export function fromHex(h: string): Uint8Array {
  const s = h.startsWith('0x') ? h.slice(2) : h;
  const out = new Uint8Array(s.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(s.slice(i * 2, i * 2 + 2), 16);
  return out;
}

/**
 * Known-good init code that returns the given runtime bytes verbatim:
 *   PUSH2 len · DUP1 · PUSH1 0x0c · PUSH1 0 · CODECOPY · PUSH1 0 · RETURN · <runtime>
 * 12 bytes of init; the runtime follows at offset 0x0c.
 */
export function wrapInitCode(runtime: Uint8Array): Uint8Array {
  if (runtime.length > 0xffff) throw new Error('runtime too long for PUSH2 length');
  const len = runtime.length;
  const init = new Uint8Array([0x61, (len >> 8) & 0xff, len & 0xff, 0x80, 0x60, 0x0c, 0x60, 0x00, 0x39, 0x60, 0x00, 0xf3]);
  const out = new Uint8Array(init.length + len);
  out.set(init, 0);
  out.set(runtime, init.length);
  return out;
}

/** Deployment rules that reject or alter runtime code before we ever get to execute it. */
export function deploymentRuleCheck(runtime: Uint8Array): string | null {
  if (runtime.length > 0 && runtime[0] === 0xef) return 'EIP-3541: runtime code may not begin with 0xEF';
  if (runtime.length > 24576) return 'EIP-170: runtime code exceeds 24,576 bytes';
  return null;
}
