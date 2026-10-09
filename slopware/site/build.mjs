// The site is one document. The build copies it to dist/ with the installer's address filled in
// from the SLOPWARE environment variable (left as the placeholder when unset, so ?contract= still works).
import { mkdirSync, readFileSync, writeFileSync, copyFileSync, existsSync, cpSync } from 'node:fs';
const addr = process.env.SLOPWARE ?? '';
mkdirSync('dist', { recursive: true });
let html = readFileSync('index.html', 'utf8');
if (/^0x[0-9a-fA-F]{40}$/.test(addr)) html = html.replaceAll('__SLOPWARE__', addr);
const rpc = process.env.RPC_URL ?? '';
if (/^https?:\/\//.test(rpc)) html = html.replaceAll('__RPC__', rpc);
// Bake the catalogue's numbers in at build time so a visitor, crawler or agent without JavaScript sees them (the page
// refreshes them live). Three eth_calls; any failure leaves the placeholders, which the page fills on load.
async function state() {
  if (!/^0x[0-9a-fA-F]{40}$/.test(addr) || !/^https?:\/\//.test(rpc)) return null;
  const call = async (sel) => { const r = await fetch(rpc, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_call', params: [{ to: addr, data: sel }, 'latest'] }) }); const j = await r.json(); return BigInt(j.result); };
  try { const [price, releases, rejected] = await Promise.all([call('0xa035b1fe'), call('0x913e10e9'), call('0xd13b0e64')]); return { price, releases, rejected }; } catch { return null; }
}
const st = await state();
if (st) {
  const eth = (Number(st.price) / 1e18).toString();
  html = html.replace('<span id="price">—</span>', `<span id="price">${eth}</span>`).replace('<span id="count">—</span>', `<span id="count">${(st.releases - st.rejected).toLocaleString('en-US')}</span>`);
  html = html.replace('</head>', `<meta name="slopware:state" content="price ${eth} ETH · ${st.releases} releases · ${st.rejected} refused · as built">\n</head>`);
}
writeFileSync('dist/index.html', html);
copyFileSync('lab.json', 'dist/lab.json');
for (const f of ['readings.html', 'readings.json', 'og-site.png', 'og-readings.png']) if (existsSync(f)) copyFileSync(f, `dist/${f}`);
if (existsSync('r')) cpSync('r', 'dist/r', { recursive: true });
for (const f of ['e1.html', 'e1.md', 'og-e1.png', 'llms.txt', 'readings.md']) if (existsSync(f)) copyFileSync(f, `dist/${f}`);
if (existsSync('e1-data')) cpSync('e1-data', 'dist/e1-data', { recursive: true });
console.log(`built dist/ · installer ${addr || '(placeholder; pass ?contract=)'}`);
