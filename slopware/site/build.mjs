// The site is one document. The build copies it to dist/ with the installer's address filled in
// from the SLOPWARE environment variable (left as the placeholder when unset, so ?contract= still works).
import { mkdirSync, readFileSync, writeFileSync, copyFileSync, existsSync, cpSync } from 'node:fs';
const addr = process.env.SLOPWARE ?? '';
mkdirSync('dist', { recursive: true });
let html = readFileSync('index.html', 'utf8');
if (/^0x[0-9a-fA-F]{40}$/.test(addr)) html = html.replaceAll('__SLOPWARE__', addr);
const rpc = process.env.RPC_URL ?? '';
if (/^https?:\/\//.test(rpc)) html = html.replaceAll('__RPC__', rpc);
writeFileSync('dist/index.html', html);
copyFileSync('lab.json', 'dist/lab.json');
for (const f of ['readings.html', 'readings.json', 'og-site.png', 'og-readings.png']) if (existsSync(f)) copyFileSync(f, `dist/${f}`);
if (existsSync('r')) cpSync('r', 'dist/r', { recursive: true });
for (const f of ['e1.html', 'og-e1.png']) if (existsSync(f)) copyFileSync(f, `dist/${f}`);
if (existsSync('e1')) cpSync('e1', 'dist/e1', { recursive: true });
console.log(`built dist/ · installer ${addr || '(placeholder; pass ?contract=)'}`);
