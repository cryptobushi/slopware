// Cached read of one release for the record page. A settled release never changes, so once it is
// installed or refused the edge may keep it for a day; one still installing is kept ten seconds.
//   GET /api/release?id=N
import { createPublicClient, http, parseAbi, type Hex } from 'viem';

const abi = parseAbi([
  'function software(uint256) view returns ((address installer,uint64 requestedAt,uint64 installedAt,uint8 status,uint96 paid,address program,bytes32 checksum))',
  'function bytecodeOf(uint256) view returns (bytes)',
  'function ownerOf(uint256) view returns (address)',
  'error NoSuchRelease()',
]);
const STATUS = ['none', 'installing', 'installed', 'rejected', 'abandoned'];

export default async function handler(req: any, res: any) {
  const rpc = process.env.RPC_URL; const address = process.env.SLOPWARE as Hex | undefined;
  const id = Number(req.query?.id);
  if (!rpc || !address) { res.status(503).json({ error: 'installer not configured' }); return; }
  if (!Number.isInteger(id) || id < 1) { res.status(400).json({ error: 'id' }); return; }
  const pub = createPublicClient({ transport: http(rpc) });
  try {
    const s = await pub.readContract({ address, abi, functionName: 'software', args: [BigInt(id)] });
    const [bytecode, owner] = await Promise.all([
      s.status === 2 || s.status === 3 ? pub.readContract({ address, abi, functionName: 'bytecodeOf', args: [BigInt(id)] }) : Promise.resolve('0x' as Hex),
      pub.readContract({ address, abi, functionName: 'ownerOf', args: [BigInt(id)] }).catch(() => null),
    ]);
    const settled = s.status === 2 || s.status === 3;
    res.setHeader('Cache-Control', settled ? 'public, s-maxage=86400, stale-while-revalidate=604800' : 'public, s-maxage=10, stale-while-revalidate=30');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.status(200).json({ id, status: STATUS[s.status] ?? String(s.status), installer: s.installer, owner, program: s.status === 2 ? s.program : null, requestedAt: Number(s.requestedAt), installedAt: Number(s.installedAt), checksum: s.checksum, bytecode });
  } catch (e: any) {
    const m = String(e.shortMessage ?? e.message ?? e);
    if (/NoSuchRelease|0xbdf01e81/.test(m)) { res.setHeader('Cache-Control', 'public, s-maxage=10'); res.status(404).json({ error: 'no such release' }); return; }
    res.setHeader('Cache-Control', 'no-store');
    res.status(502).json({ error: m.slice(0, 200) });
  }
}
