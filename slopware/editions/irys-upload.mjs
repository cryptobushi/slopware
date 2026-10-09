import { Uploader } from "@irys/upload";
import { EthereumToken } from "@irys/upload-ethereum";
import fs from "node:fs";
const [,, file, ctype, net] = process.argv;
const pk = JSON.parse(fs.readFileSync(process.env.KEEPER_WALLET_FILE,"utf8")).private_key;
let b = Uploader(EthereumToken).withWallet(pk);
const irys = net === "mainnet" ? await b.withRpc("https://ethereum-rpc.publicnode.com") : await b.withRpc("https://ethereum-sepolia-rpc.publicnode.com").devnet();
const size = fs.statSync(file).size;
const price = BigInt((await irys.getPrice(size)).toString());
const bal = BigInt((await irys.getBalance()).toString());
if (bal < price) { const f = await irys.fund((price * 2n).toString()); console.error("funded", f.id); }
const r = await irys.uploadFile(file, { tags: [{ name: "Content-Type", value: ctype }, { name: "App", value: "SLOPWARE research editions" }] });
console.log(r.id);
