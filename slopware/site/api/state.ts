// Cached read of the installer for the catalogue page. Every visitor used to ask the public RPC
// directly, forty calls per page load; this asks once, via Multicall3, and lets Vercel's edge
// cache serve everyone for ten seconds. Pure reads; nothing here signs anything.
//   GET /api/state            → summary + the newest 40 releases
//   GET /api/state?from=A&to=B → releases A..B (at most 60), for paging back
import { createPublicClient, http, parseAbi, type Hex } from 'viem';

const abi = parseAbi([
  'function price() view returns (uint256)',
  'function releases() view returns (uint256)',
  'function installed() view returns (uint256)',
  'function rejected() view returns (uint256)',
  'function software(uint256) view returns ((address installer,uint64 requestedAt,uint64 installedAt,uint8 status,uint96 paid,address program,bytes32 checksum))',
]);
const MULTICALL3 = '0xcA11bde05977b3631167028862bE2a173976CA11' as Hex;
const STATUS = ['none', 'installing', 'installed', 'rejected', 'abandoned'];

export default async function handler(req: any, res: any) {
  const rpc = process.env.RPC_URL; const address = process.env.SLOPWARE as Hex | undefined;
  if (!rpc || !address) { res.status(503).json({ error: 'installer not configured' }); return; }
  const pub = createPublicClient({ transport: http(rpc) });
  try {
    const [block, price, releases, installed, rejected] = await Promise.all([
      pub.getBlockNumber(),
      pub.readContract({ address, abi, functionName: 'price' }),
      pub.readContract({ address, abi, functionName: 'releases' }),
      pub.readContract({ address, abi, functionName: 'installed' }),
      pub.readContract({ address, abi, functionName: 'rejected' }),
    ]);
    const total = Number(releases);
    let to = Number(req.query?.to ?? total), from = Number(req.query?.from ?? Math.max(1, to - 39));
    to = Math.min(Math.max(1, to), total); from = Math.max(1, Math.min(from, to)); if (to - from > 59) from = to - 59;
    const ids = total ? Array.from({ length: to - from + 1 }, (_, i) => BigInt(to - i)) : [];
    const results = ids.length ? await pub.multicall({ contracts: ids.map((id) => ({ address, abi, functionName: 'software', args: [id] })), multicallAddress: MULTICALL3, allowFailure: true }) : [];
    const rows = results.map((r: any, i) => {
      const s = r.status === 'success' ? r.result : null;
      return s ? { id: Number(ids[i]), status: STATUS[s.status] ?? String(s.status), program: s.status === 2 ? s.program : null, installer: s.installer, requestedAt: Number(s.requestedAt), installedAt: Number(s.installedAt) } : { id: Number(ids[i]), status: 'unknown' };
    });
    const settledOnly = rows.every((r) => r.status === 'installed' || r.status === 'rejected');
    // the newest window changes every block; a window of old, settled releases does not
    res.setHeader('Cache-Control', req.query?.to && settledOnly ? 'public, s-maxage=3600, stale-while-revalidate=86400' : 'public, s-maxage=10, stale-while-revalidate=30');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.status(200).json({ block: Number(block), price: price.toString(), releases: total, installed: Number(installed), rejected: Number(rejected), from, to, rows });
  } catch (e: any) {
    res.setHeader('Cache-Control', 'no-store');
    res.status(502).json({ error: String(e.shortMessage ?? e.message ?? e).slice(0, 200) });
  }
}
