import { mkdirSync, appendFileSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

export interface RunMeta {
  id: string;
  startedAt: string;
  count: number;
  bytes: number;
  mode: string;
  seed?: string;
  rpc: string;
  probes: string[];
  gasPerProbe: number;
}

export function openRun(meta: RunMeta): { dir: string; specimen: (s: unknown) => void; finish: (summary: unknown) => void } {
  const dir = join('results', meta.id);
  mkdirSync(join(dir, 'interesting'), { recursive: true });
  writeFileSync(join(dir, 'run.json'), JSON.stringify(meta, null, 2));
  const file = join(dir, 'specimens.jsonl');
  writeFileSync(file, '');
  return {
    dir,
    specimen: (s) => appendFileSync(file, JSON.stringify(s) + '\n'),
    finish: (summary) => writeFileSync(join(dir, 'summary.json'), JSON.stringify(summary, null, 2)),
  };
}

export function saveInteresting(dir: string, id: string, record: unknown) {
  writeFileSync(join(dir, 'interesting', `${id}.json`), JSON.stringify(record, null, 2));
}

export function loadSpecimen(runId: string, id: string): any | undefined {
  const file = join('results', runId, 'specimens.jsonl');
  if (!existsSync(file)) throw new Error(`no such run: ${runId}`);
  const want = id.padStart(6, '0');
  for (const line of readFileSync(file, 'utf8').split('\n')) {
    if (!line) continue;
    const r = JSON.parse(line);
    if (r.id === want) return r;
  }
  return undefined;
}

export function loadRun(runId: string): { meta: RunMeta; specimens: any[] } {
  const dir = join('results', runId);
  const meta = JSON.parse(readFileSync(join(dir, 'run.json'), 'utf8'));
  const specimens = readFileSync(join(dir, 'specimens.jsonl'), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
  return { meta, specimens };
}
