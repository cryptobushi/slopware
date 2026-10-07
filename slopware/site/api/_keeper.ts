/**
 * SLOPWARE keeper, as one scheduled run.
 *
 * A release is requested in block R and decided by the hash of block R+1. Someone must then call
 * complete(release); the collector's browser usually does, within a block or two. This run finds any
 * release still installing whose deciding block is final and completes it, so a collector who closed
 * the tab is not left waiting, and a release nobody came back for is recorded as abandoned (and
 * refundable) rather than left in limbo.
 *
 * It has no power over the outcome. It cannot choose, skip or alter bytecode; it only pays gas so the
 * inevitable happens sooner. Anyone may run one. Vercel's cron runs this one every minute.
 *
 * Gas discipline: when the base fee is above MAX_BASE_FEE_GWEI the run waits for a cheaper block,
 * except for releases within SOON blocks of losing their entropy (256 blocks after the request),
 * which are completed regardless so the record is settled before the hash is gone.
 */
import { createPublicClient, createWalletClient, formatEther, http, parseAbi, parseAbiItem, type Hex } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

export interface KeeperEnv {
  RPC_URL?: string;
  SLOPWARE?: string;
  KEEPER_KEY?: string;
  MAX_BASE_FEE_GWEI?: string;
}

export interface KeeperReport {
  ok: boolean;
  skipped?: string;
  keeper?: string;
  balanceEth?: string;
  block?: string;
  baseFeeGwei?: string;
  releases?: string;
  candidates?: number;
  completed: { release: string; status: string; gasUsed: string; hash: string }[];
  waiting: string[];
  deferred: string[];
  errors: string[];
}

const abi = parseAbi([
  'function releases() view returns (uint256)',
  'function statusOf(uint256) view returns (uint8)',
  'function software(uint256) view returns ((address installer,uint64 requestedAt,uint64 installedAt,uint8 status,uint96 paid,address program,bytes32 checksum))',
  'function complete(uint256)',
  'function completeMany(uint256[]) returns (uint256)',
]);
const BATCH = 40; // releases per completeMany; 40 × ~175k gas stays far under the 2^24 per-transaction cap
const installing = parseAbiItem('event Installing(uint256 indexed release, address indexed installer, uint256 requestedAt, uint256 paid)');
const STATUS = ['none', 'installing', 'installed', 'rejected', 'abandoned'];

const ENTROPY_WINDOW = 256n; // blockhash is available for this many blocks
const SOON = 20n; // complete regardless of gas price when this close to the window's end
const LOOKBACK = 320n; // blocks of Installing events to consider
const RECENT = 40n; // newest releases checked by number as well, in case the keeper was down

export async function runKeeper(env: KeeperEnv): Promise<KeeperReport> {
  const report: KeeperReport = { ok: true, completed: [], waiting: [], deferred: [], errors: [] };
  const rpc = env.RPC_URL;
  const address = env.SLOPWARE as Hex | undefined;
  const key = env.KEEPER_KEY as Hex | undefined;
  if (!rpc || !address || !/^0x[0-9a-fA-F]{40}$/.test(address) || !key) {
    return { ...report, skipped: 'RPC_URL, SLOPWARE and KEEPER_KEY must all be set' };
  }
  const maxBaseFeeWei = BigInt(Math.round(Number(env.MAX_BASE_FEE_GWEI ?? '3') * 1e9));

  const pub = createPublicClient({ transport: http(rpc), pollingInterval: 500 });
  const account = privateKeyToAccount(key);
  const wallet = createWalletClient({ account, transport: http(rpc) });
  report.keeper = account.address;

  const [releases, latest, balance] = await Promise.all([
    pub.readContract({ address, abi, functionName: 'releases' }),
    pub.getBlock({ blockTag: 'latest' }),
    pub.getBalance({ address: account.address }),
  ]);
  const block = latest.number;
  const baseFee = latest.baseFeePerGas ?? 0n;
  report.block = block.toString();
  report.baseFeeGwei = (Number(baseFee) / 1e9).toFixed(3);
  report.balanceEth = formatEther(balance);
  report.releases = releases.toString();

  // candidates: releases requested in the recent past, plus the newest few by number
  const ids = new Set<bigint>();
  try {
    const logs = await pub.getLogs({ address, event: installing, fromBlock: block > LOOKBACK ? block - LOOKBACK : 0n, toBlock: block });
    for (const l of logs) if (l.args.release !== undefined) ids.add(l.args.release);
  } catch (e: any) {
    report.errors.push(`getLogs: ${String(e.shortMessage ?? e.message ?? e).slice(0, 120)}`);
  }
  for (let id = releases; id >= 1n && id > releases - RECENT; id--) ids.add(id);
  report.candidates = ids.size;

  // decide what is ready; then settle it in batches so a hundred releases cost one transaction's base fee, not a hundred
  const ready: bigint[] = [];
  for (const id of [...ids].sort((a, b) => (a < b ? -1 : 1))) {
    let s;
    try { s = await pub.readContract({ address, abi, functionName: 'software', args: [id] }); }
    catch (e: any) { report.errors.push(`software(${id}): ${String(e.shortMessage ?? e.message ?? e).slice(0, 120)}`); continue; }
    if (s.status !== 1) continue;
    const deciding = BigInt(s.requestedAt) + 1n;
    if (block <= deciding) { report.waiting.push(id.toString()); continue; } // deciding block not final yet
    const expiresAt = deciding + ENTROPY_WINDOW;
    const soon = block + SOON >= expiresAt;
    if (baseFee > maxBaseFeeWei && !soon) { report.deferred.push(id.toString()); continue; }
    ready.push(id);
  }
  for (let i = 0; i < ready.length; i += BATCH) {
    const chunk = ready.slice(i, i + BATCH);
    try {
      const hash = chunk.length === 1
        ? await wallet.writeContract({ address, abi, functionName: 'complete', args: [chunk[0]], chain: null, gas: 320_000n })
        : await wallet.writeContract({ address, abi, functionName: 'completeMany', args: [chunk], chain: null, gas: 300_000n * BigInt(chunk.length) + 100_000n });
      const rc = await pub.waitForTransactionReceipt({ hash, pollingInterval: 500, timeout: 45_000 });
      for (const id of chunk) {
        const after = await pub.readContract({ address, abi, functionName: 'statusOf', args: [id] });
        report.completed.push({ release: id.toString(), status: STATUS[after] ?? String(after), gasUsed: chunk.length === 1 ? rc.gasUsed.toString() : `${rc.gasUsed} shared by ${chunk.length}`, hash });
      }
    } catch (e: any) {
      const m = String(e.shortMessage ?? e.message ?? e);
      if (!/NotInstalling/.test(m)) { report.errors.push(`complete ${chunk.length === 1 ? chunk[0] : `${chunk[0]}…${chunk[chunk.length - 1]}`}: ${m.slice(0, 160)}`); report.ok = false; }
    }
  }
  return report;
}
