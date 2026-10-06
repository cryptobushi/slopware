import { keccak256, type Hex } from 'viem';
import { withTimeout, type Chain } from './chain.js';
import { deploymentRuleCheck, hex, wrapInitCode } from './opcodes.js';

export interface Deployment {
  status: 'deployed' | 'rejected_by_rule' | 'reverted' | 'mismatch' | 'error';
  reason?: string;
  address?: Hex;
  txHash?: Hex;
  gasUsed?: number;
  deployedCode?: string;
  codeMatches?: boolean;
}

const DEPLOY_GAS = 2_000_000n;

/** Deploy `runtime` verbatim via the init wrapper, then read the code back and compare byte for byte. */
export async function deployRuntime(chain: Chain, runtime: Uint8Array): Promise<Deployment> {
  const rule = deploymentRuleCheck(runtime);
  const init = wrapInitCode(runtime);
  try {
    const txHash = await chain.wallet.sendTransaction({
      account: chain.wallet.account!,
      chain: null,
      data: `0x${hex(init)}`,
      gas: DEPLOY_GAS,
    } as any);
    const rc = await withTimeout(chain.pub.waitForTransactionReceipt({ hash: txHash, pollingInterval: 25, timeout: 30_000 }), 35_000, 'birth receipt');
    if (rc.status !== 'success') {
      return { status: 'reverted', reason: rule ?? 'creation reverted', txHash, gasUsed: Number(rc.gasUsed) };
    }
    const address = rc.contractAddress!;
    const code = (await chain.pub.getCode({ address })) ?? '0x';
    const deployedCode = code.slice(2);
    const matches = deployedCode === hex(runtime);
    if (!matches) {
      return { status: 'mismatch', reason: rule ?? 'deployed code differs from the generated runtime', address, txHash, gasUsed: Number(rc.gasUsed), deployedCode, codeMatches: false };
    }
    return { status: 'deployed', address, txHash, gasUsed: Number(rc.gasUsed), deployedCode, codeMatches: true, ...(rule ? { reason: `rule predicted failure but deployment succeeded: ${rule}` } : {}) };
  } catch (e: any) {
    return { status: rule ? 'rejected_by_rule' : 'error', reason: rule ?? String(e.shortMessage ?? e.message ?? e) };
  }
}

export function codeHash(runtime: Uint8Array): Hex {
  return keccak256(`0x${hex(runtime)}`);
}
