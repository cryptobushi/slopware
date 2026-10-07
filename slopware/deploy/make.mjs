// Writes deploy/index.html: a one-page tool that deploys the installer from a browser wallet.
// The compiled creation bytecode is embedded from contracts/out so the page is self-contained;
// the artist address and price are entered on the page and ABI-encoded there. No key ever leaves
// the wallet. Run `node deploy/make.mjs` after any change to the contract, then open the page.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const artifact = JSON.parse(readFileSync(new URL('../contracts/out/Slopware.sol/Slopware.json', import.meta.url), 'utf8'));
const bytecode = artifact.bytecode.object;
const meta = typeof artifact.metadata === 'string' ? JSON.parse(artifact.metadata) : artifact.metadata;
const compiler = meta.compiler.version;
const runs = meta.settings.optimizer.runs;
const sha = createHash('sha256').update(bytecode).digest('hex').slice(0, 16);

const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SLOPWARE deploy</title>
<style>
html,body{margin:0;background:#fff;color:#000}
body{font-family:"Courier New",Courier,monospace;font-size:15px;line-height:1.5;max-width:860px;margin:0 auto;padding:3em 16px}
h1{font-size:15px;font-weight:normal;margin:0 0 2em}
pre{white-space:pre-wrap;word-break:break-all;margin:0 0 1.3em}
label{display:block;margin:1.3em 0 0.3em}
input{font:inherit;width:100%;max-width:560px;padding:0.3em 0.5em;border:1px solid #000;background:#fff;color:#000}
button{font:inherit;background:none;border:0;padding:0;cursor:pointer;text-decoration:underline;color:#000}
button:disabled{text-decoration:none;color:#888;cursor:default}
.mute{color:#666}.err{color:#b00}.big{font-size:22px}
.warn{border:1px solid #000;padding:1em;margin:2em 0}
</style></head><body>
<h1>SLOPWARE — deploy the installer from your own wallet</h1>

<pre class="mute">compiled with solc ${compiler}, optimizer ${runs} runs · creation bytecode ${(bytecode.length - 2) / 2} bytes · sha256 ${sha}…
constructor(address artist, uint256 price)</pre>

<p><button id="connect">[ connect wallet ]</button></p>
<pre id="who" class="mute">no wallet connected</pre>

<label for="artist">artist address — receives payments, may set the price, can touch nothing else</label>
<input id="artist" placeholder="0x…" spellcheck="false">
<label for="price">opening price in wei (0.0003 ETH = 300000000000000)</label>
<input id="price" value="300000000000000" spellcheck="false">
<pre id="priceEth" class="mute"></pre>

<div class="warn" id="chainbox">
<pre id="chain" class="big">—</pre>
<label><input type="checkbox" id="confirm" style="width:auto"> I am deploying to the network named above, on purpose.</label>
</div>

<p><button id="deploy" disabled>[ deploy ]</button></p>
<pre id="state"></pre>
<pre id="result"></pre>

<script>
(function () {
'use strict';
const BYTECODE = '${bytecode}';
const CHAINS = { 1: 'ETHEREUM MAINNET', 11155111: 'Sepolia testnet', 31337: 'local Anvil', 17000: 'Holesky testnet', 560048: 'Hoodi testnet' };
const SCAN = { 1: 'https://etherscan.io', 11155111: 'https://sepolia.etherscan.io' };
const $ = (id) => document.getElementById(id);
let account = null, chainId = null;

const pad = (h) => h.replace(/^0x/, '').toLowerCase().padStart(64, '0');
function args() {
  const artist = $('artist').value.trim();
  const price = $('price').value.trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(artist)) throw new Error('artist must be a 20-byte address');
  if (!/^[0-9]+$/.test(price) || BigInt(price) === 0n) throw new Error('price must be a positive integer in wei');
  return { artist, price: BigInt(price), encoded: pad(artist) + pad(BigInt(price).toString(16)) };
}
function refresh() {
  try { const a = args(); $('priceEth').textContent = (Number(a.price) / 1e18).toString() + ' ETH'; } catch (e) { $('priceEth').textContent = e.message; }
  $('chain').textContent = chainId ? (CHAINS[chainId] || ('chain id ' + chainId)) : '—';
  let ok = false; try { args(); ok = Boolean(account && chainId && $('confirm').checked); } catch (e) {}
  $('deploy').disabled = !ok;
}
['artist', 'price'].forEach((id) => $(id).addEventListener('input', refresh));
$('confirm').addEventListener('change', refresh);

$('connect').onclick = async () => {
  if (!window.ethereum) { $('who').innerHTML = '<span class="err">no wallet found in this browser</span>'; return; }
  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
  account = accounts[0];
  chainId = Number(await window.ethereum.request({ method: 'eth_chainId' }));
  $('who').textContent = 'connected ' + account;
  if (!$('artist').value) $('artist').value = account;
  window.ethereum.on && window.ethereum.on('chainChanged', (c) => { chainId = Number(c); $('confirm').checked = false; refresh(); });
  window.ethereum.on && window.ethereum.on('accountsChanged', (a) => { account = a[0] || null; $('who').textContent = account ? 'connected ' + account : 'no wallet connected'; refresh(); });
  refresh();
};

$('deploy').onclick = async () => {
  let a; try { a = args(); } catch (e) { $('state').innerHTML = '<span class="err">' + e.message + '</span>'; return; }
  $('deploy').disabled = true;
  $('state').textContent = 'confirm the transaction in your wallet…';
  try {
    const data = BYTECODE + a.encoded;
    const hash = await window.ethereum.request({ method: 'eth_sendTransaction', params: [{ from: account, data }] });
    $('state').textContent = 'sent ' + hash + '\\nwaiting for the receipt…';
    let rc = null;
    while (!rc) { await new Promise((r) => setTimeout(r, 3000)); rc = await window.ethereum.request({ method: 'eth_getTransactionReceipt', params: [hash] }); }
    if (rc.status !== '0x1') throw new Error('deployment reverted');
    const addr = rc.contractAddress;
    const scan = SCAN[chainId];
    $('state').textContent = 'deployed in block ' + parseInt(rc.blockNumber, 16) + ' · gas used ' + parseInt(rc.gasUsed, 16).toLocaleString('en-US');
    $('result').textContent =
      'installer   ' + addr + (scan ? '\\n            ' + scan + '/address/' + addr : '') +
      '\\nartist      ' + a.artist +
      '\\nprice       ' + a.price.toString() + ' wei' +
      '\\n\\nnext, from slopware/contracts:' +
      '\\n  forge verify-contract ' + addr + ' src/Slopware.sol:Slopware --chain ' + chainId +
      ' --constructor-args $(cast abi-encode "constructor(address,uint256)" ' + a.artist + ' ' + a.price.toString() + ')' +
      '\\n\\nthen set SLOPWARE=' + addr + ' on Vercel and redeploy the site.';
  } catch (e) {
    $('state').innerHTML = '<span class="err">' + String(e.message || e).slice(0, 200) + '</span>';
    $('deploy').disabled = false;
  }
};
refresh();
})();
</script>
</body></html>
`;
writeFileSync(new URL('./index.html', import.meta.url), html);
console.log(`deploy/index.html written · solc ${compiler} · ${(bytecode.length - 2) / 2} bytes · sha256 ${sha}…`);
