// Run one keeper pass from the shell, against any chain the env points at.
//   RPC_URL=http://127.0.0.1:8545 SLOPWARE=0x… KEEPER_KEY=0x… npx tsx api/_local.ts
import { runKeeper } from './_keeper.js';

const report = await runKeeper(process.env);
console.log(JSON.stringify(report, null, 2));
process.exit(report.ok ? 0 : 1);
