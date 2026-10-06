import { randomBytes } from 'node:crypto';
import { keccak256, toBytes } from 'viem';

/** A byte source. Either cryptographically random or a deterministic stream from a seed. */
export interface Rng {
  readonly mode: 'crypto' | 'seeded';
  readonly seed?: string;
  bytes(n: number): Uint8Array;
}

export function cryptoRng(): Rng {
  return { mode: 'crypto', bytes: (n) => new Uint8Array(randomBytes(n)) };
}

/**
 * Deterministic stream: keccak256(seed || counter) blocks, concatenated.
 * Same seed → same bytes, forever, on any machine. Not for cryptographic use.
 */
export function seededRng(seed: string): Rng {
  let counter = 0n;
  let buffer = new Uint8Array(0);
  let offset = 0;
  const refill = () => {
    const block = keccak256(concat(toBytes(seed), be64(counter++)));
    buffer = new Uint8Array(toBytes(block));
    offset = 0;
  };
  return {
    mode: 'seeded',
    seed,
    bytes(n) {
      const out = new Uint8Array(n);
      let i = 0;
      while (i < n) {
        if (offset >= buffer.length) refill();
        const take = Math.min(n - i, buffer.length - offset);
        out.set(buffer.subarray(offset, offset + take), i);
        offset += take;
        i += take;
      }
      return out;
    },
  };
}

function be64(v: bigint): Uint8Array {
  const b = new Uint8Array(8);
  for (let i = 7; i >= 0; i--) {
    b[i] = Number(v & 0xffn);
    v >>= 8n;
  }
  return b;
}

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}
