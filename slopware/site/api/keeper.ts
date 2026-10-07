// Vercel cron target. Vercel calls GET /api/keeper every minute with `Authorization: Bearer <CRON_SECRET>`.
// Completing is permissionless, so a stranger calling this would only spend the keeper's gas;
// the secret keeps that from being a lever.
import { runKeeper } from './_keeper.js';

export default async function handler(req: any, res: any) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers?.authorization !== `Bearer ${secret}`) {
    res.status(401).json({ error: 'unauthorized' });
    return;
  }
  try {
    const report = await runKeeper(process.env);
    console.log(JSON.stringify({ keeper: report.keeper, balanceEth: report.balanceEth, block: report.block, baseFeeGwei: report.baseFeeGwei, completed: report.completed.length, waiting: report.waiting.length, deferred: report.deferred.length, errors: report.errors }));
    res.status(report.ok ? 200 : 500).json(report);
  } catch (e: any) {
    console.error(String(e.message ?? e));
    res.status(500).json({ ok: false, error: String(e.message ?? e).slice(0, 200) });
  }
}
