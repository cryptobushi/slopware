import { createPublicClient, createWalletClient, http, type Hex, type PublicClient, type WalletClient } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

/** The explorer only ever talks to a local, ephemeral chain. */
export const EXPECTED_CHAIN_ID = 31337;
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]', '::1', '0.0.0.0']);

/** Anvil's ten default accounts (mnemonic "test test … junk"). Well-known test keys with no value anywhere real. */
export const ANVIL_KEYS: Hex[] = [
  '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
  '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d',
  '0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a',
  '0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6',
  '0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a',
  '0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba',
  '0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e',
  '0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356',
  '0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97',
  '0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6',
];
const ANVIL_KEY: Hex = ANVIL_KEYS[0];

export interface Chain {
  rpc: string;
  pub: PublicClient;
  wallet: WalletClient;
  from: Hex;
  request: (method: string, params: unknown[]) => Promise<any>;
}

export async function connect(rpc: string, keyIndex = 0): Promise<Chain> {
  const url = new URL(rpc);
  if (!LOCAL_HOSTS.has(url.hostname)) {
    throw new Error(`refusing non-local RPC ${rpc}: this explorer deploys arbitrary programs and only runs against localhost`);
  }
  // a local chain mines instantly; poll receipts fast and never wait forever
  const pub = createPublicClient({ transport: http(rpc, { timeout: 60_000 }), pollingInterval: 25 });
  const chainId = await pub.getChainId();
  if (chainId !== EXPECTED_CHAIN_ID) {
    throw new Error(`refusing chain id ${chainId}: expected the local development chain ${EXPECTED_CHAIN_ID}`);
  }
  const account = privateKeyToAccount(ANVIL_KEYS[keyIndex % ANVIL_KEYS.length] ?? ANVIL_KEY);
  const wallet = createWalletClient({ account, transport: http(rpc, { timeout: 60_000 }), pollingInterval: 25 });
  return {
    rpc,
    pub,
    wallet,
    from: account.address,
    request: (method, params) => withTimeout((pub as any).request({ method, params }), 60_000, method),
  };
}

/** No call against a random program may hang the explorer. */
export function withTimeout<T>(p: Promise<T>, ms: number, what: string): Promise<T> {
  return Promise.race([
    p,
    new Promise<T>((_, reject) => setTimeout(() => reject(new Error(`${what} timed out after ${ms} ms`)), ms)),
  ]);
}
