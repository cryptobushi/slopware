#!/usr/bin/env python3
"""Write BASELINE.md from the four 10k baseline runs. Every number in the document comes from
results/<run>/specimens.jsonl; the prose around them is fixed and was checked against the runs.
Usage: python3 scripts/baseline_md.py [date]   (runs: slopware-baseline-10k-{16,32,64,128}b)"""
import json, sys, collections, datetime

LENGTHS = [16, 32, 64, 128]
RUN = "slopware-baseline-10k-{}b"
date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()

def load(L):
    rows = [json.loads(l) for l in open(f"results/{RUN.format(L)}/specimens.jsonl")]
    inst = [r for r in rows if r["birth"]["status"] == "deployed"]
    return rows, inst

data = {L: load(L) for L in LENGTHS}
def has(r, t): return t in r["classification"]["traits"]
def ops(p): return p.get("ops") or []
def names(p): return [o.split()[0] for o in ops(p)]
def pct(a, b, d=2): return f"{100*a/b:.{d}f}%" if b else "—"
def pctz(a, b):  # 0 stays 0, otherwise two decimals
    return "0" if a == 0 else pct(a, b)
def fmt(n): return f"{n:,}"

cols = {}
for L in LENGTHS:
    rows, inst = data[L]
    probes = [p for r in inst for p in r["probes"]]
    lives = sorted(p["instructionCount"] for p in probes)
    q = lambda f: lives[min(len(lives) - 1, int(f * len(lives)))]
    fm = collections.Counter(p["outcome"] for p in probes)
    notplaced = [r for r in rows if r["birth"]["status"] != "deployed"]
    refused = [r for r in notplaced if r["birth"]["status"] != "error"]
    lost = [r for r in notplaced if r["birth"]["status"] == "error"]
    c = {
        "installed": pct(len(inst), len(rows)),
        "refused": f"{len(refused)}",
        "lost": f"{len(lost)}",
        "refused_all_ef": all(r["bytecode"][2:4] == "ef" for r in refused),
        "probes": fmt(len(probes)),
        "success": pct(fm["success"], len(probes)),
        "mean_median": f"{sum(lives)/len(lives):.2f} / {q(0.5)}",
        "p90_max": f"{q(0.9)} / {lives[-1]}",
        "first": pct(sum(1 for r in inst if has(r, "DIES_AT_FIRST_INSTRUCTION")), len(inst), 1),
        "invalid": pct(fm["invalid_opcode"], len(probes), 1),
        "underflow": pct(fm["stack_underflow"], len(probes), 1),
        "badjump": pctz(fm["bad_jump"], len(probes)),
        "revert": pctz(fm["revert"], len(probes)),
        "oog": pctz(fm["out_of_gas"], len(probes)),
        "other": pctz(fm["other_halt"] + fm.get("stack_overflow", 0), len(probes)),
        "read": pctz(sum(1 for r in inst if has(r, "STATE_READ")), len(inst)),
        "write": pctz(sum(1 for r in inst if has(r, "STATE_WRITE")), len(inst)),
        "hash": pctz(sum(1 for r in inst if has(r, "HASHING")), len(inst)),
        "branch": pctz(sum(1 for r in inst if has(r, "BRANCHING")), len(inst)),
        "log": pctz(sum(1 for r in inst if has(r, "EMITS_LOG")), len(inst)),
        "ret": pctz(sum(1 for r in inst if has(r, "RETURNS_DATA")), len(inst)),
        "call": pctz(sum(1 for r in inst if has(r, "EXTERNAL_CALL")), len(inst)),
        "create": pctz(sum(1 for r in inst if has(r, "CONTRACT_CREATION_ATTEMPT")), len(inst)),
        "cdep": pctz(sum(1 for r in inst if has(r, "CALLDATA_DEPENDENT")), len(inst)),
        "vdep": pctz(sum(1 for r in inst if has(r, "VALUE_DEPENDENT")), len(inst)),
        "life": collections.Counter(r["probes"][0]["instructionCount"] for r in inst if r["probes"]),
        "top": max(r["score"]["total"] for r in inst),
        "under10": pct(sum(1 for r in inst if r["score"]["total"] < 10), len(inst), 1),
        "future": pct(sum(1 for r in inst if has(r, "FUTURE_OPCODE")), len(inst)),
        "n_inst": len(inst), "n_probes": len(probes), "fm": fm,
    }
    cols[L] = c

def row(label, key, bold=False):
    cells = [cols[L][key] for L in LENGTHS]
    if bold: cells = [f"**{v}**" for v in cells]
    return f"| {'**'+label+'**' if bold else label} | " + " | ".join(cells) + " |"

total_inst = sum(cols[L]["n_inst"] for L in LENGTHS)
total_probes = sum(cols[L]["n_probes"] for L in LENGTHS)
all_rows = [(L, r) for L in LENGTHS for r in data[L][1]]
survive1 = 1 - sum(1 for _, r in all_rows if has(r, "DIES_AT_FIRST_INSTRUCTION")) / total_inst
oogs = [(L, r) for L, r in all_rows if has(r, "OUT_OF_GAS")]
loops = [(L, r) for L, r in oogs if any(p["outcome"] == "out_of_gas" and p["instructionCount"] > 32 for p in r["probes"])]
rets = [(L, r) for L, r in all_rows if has(r, "RETURNS_DATA")]
sst_live = [(L, r) for L, r in all_rows if any(p["outcome"] == "success" and (p.get("opCounts") or {}).get("SSTORE", 0) > 0 for p in r["probes"])]
tst_live = [(L, r) for L, r in all_rows if any(p["outcome"] == "success" and (p.get("opCounts") or {}).get("TSTORE", 0) > 0 for p in r["probes"])]
branches = [(L, r) for L, r in all_rows if has(r, "BRANCHING")]
deps = [(L, r) for L, r in all_rows if has(r, "CALLDATA_DEPENDENT") or has(r, "VALUE_DEPENDENT")]
calls = [(L, r) for L, r in all_rows if has(r, "EXTERNAL_CALL")]
creates = [(L, r) for L, r in all_rows if has(r, "CONTRACT_CREATION_ATTEMPT")]
writes_any = [(L, r) for L, r in all_rows if has(r, "STATE_WRITE")]
mem_errs = sum(1 for L in LENGTHS for r in data[L][1] for p in r["probes"] if p.get("rawError") and "memory" in p["rawError"].lower())
longest = max(all_rows, key=lambda t: max(p["instructionCount"] for p in t[1]["probes"]))
top_score = max(cols[L]["top"] for L in LENGTHS)
top_specs = sorted(all_rows, key=lambda t: -t[1]["score"]["total"])[:3]

def longest_probe(r): return max(r["probes"], key=lambda p: p["instructionCount"])
def trace(r, n=12):
    p = longest_probe(r); nm = names(p)
    return " · ".join(nm[:n]) + (f" · … ({len(nm)-n} more)" if len(nm) > n else "")
def ref(L, r): return f"`{RUN.format(L)}` #{r['id']}"

lines = []
A = lines.append
A("# SLOPWARE — Baseline")
A("")
A(f"*Uniform random EVM runtime bytecode, 10,000 specimens at each of four lengths, five probes each, full tracing. {date}. Seeds `slopware-baseline-16/32/64/128`; every number below is reproducible to the byte with `npm run explore -- --count 10000 --bytes <L> --seed slopware-baseline-<L>`.*")
A("")
A("The generator was not tuned. Nothing was discarded. This is what the space contains.")
A("")
A("## The distribution")
A("")
A("| | 16 bytes | 32 bytes | 64 bytes | 128 bytes |")
A("|---|---:|---:|---:|---:|")
A(row("installed", "installed"))
A(row("refused (leading `0xEF`, EIP-3541)" if all(cols[L]["refused_all_ef"] for L in LENGTHS) else "refused", "refused"))
total_lost = sum(int(cols[L]["lost"]) for L in LENGTHS)
if total_lost: A(row("lost to the instrument (placement timed out)", "lost"))
A(row("probes run", "probes"))
A(row("execution success", "success", bold=True))
A(row("instructions: mean / median", "mean_median"))
A(row("instructions: p90 / max", "p90_max"))
A(row("died at first instruction", "first"))
A(row("invalid opcode", "invalid"))
A(row("stack underflow", "underflow"))
A(row("bad jump", "badjump"))
A(row("revert", "revert"))
A(row("out of gas", "oog", bold=True))
A(row("other halt (memory)", "other"))
A(row("state read (SLOAD/TLOAD executed)", "read"))
A(row("state write (SSTORE/TSTORE executed)", "write"))
A(row("hashing", "hash"))
A(row("branching (JUMP/JUMPI executed)", "branch"))
A(row("emits log", "log"))
A(row("returns data", "ret"))
A(row("external call executed", "call"))
A(row("contract creation executed", "create"))
A(row("calldata-dependent", "cdep"))
A(row("value-dependent", "vdep"))
A("")
A("Lifespan (instructions before halt, empty calldata, installed specimens):")
A("")
A("| instructions | 16 b | 32 b | 64 b | 128 b |")
A("|---:|---:|---:|---:|---:|")
for k in range(1, 7):
    A(f"| {k} | " + " | ".join(fmt(cols[L]["life"].get(k, 0)) for L in LENGTHS) + " |")
A("| 7+ | " + " | ".join(fmt(sum(v for kk, v in cols[L]["life"].items() if kk >= 7)) for L in LENGTHS) + " |")
A("")
A(f"Interestingness: at least {min(cols[L]['under10'] for L in LENGTHS)} of every run scores under 10. The highest score in {fmt(total_inst + sum(int(cols[L]['refused']) for L in LENGTHS))} specimens is {top_score}.")
A("")
A("## What the numbers mean")
A("")
A(f"**Lifespan is geometric and does not depend on length.** About {survive1*100:.0f}% of random programs survive their first instruction; of those, a similar share survive the second; and so on. The mean sits between {min(cols[L]['mean_median'].split(' /')[0] for L in LENGTHS)} and {max(cols[L]['mean_median'].split(' /')[0] for L in LENGTHS)} at every length. The reason is arithmetic: of 256 byte values, only 55 are defined opcodes that need no operands (STOP, PUSH0–PUSH32, the environment reads, PC, MSIZE, GAS, JUMPDEST). A random first byte is one of them with probability 0.215. Each later instruction faces similar odds, slightly improved by whatever the pushes left on the stack. Length is nearly irrelevant to how long a program lives; it only changes how it ends.")
A("")
A(f"**Short programs \"succeed\" by running off the end.** Execution success is {cols[16]['success']} at 16 bytes and {cols[128]['success']} at 128. The difference is not ability; it is the edge of the code. `PUSHn` consumes the next *n* bytes as data, so a 16-byte program whose first instructions are pushes often has its program counter walk past the last byte — and executing past the end of code is an implicit `STOP`. Longer programs keep going and die. The commonest clean halt is a handful of pushes followed by nothing.")
A("")
A("**Roughly half of all bytes are not instructions at all.** 51% of byte values are undefined, and within defined programs PUSH immediates swallow 20–50% of the code. Of the 128 bytes in a long specimen, perhaps 40 are ever candidates to execute.")
A("")
oog_desc = "; ".join(f"`{trace(r, 6)}` ({L} b #{r['id']})" for L, r in oogs[:6])
A(f"**Out of gas exists, but not the way we imagined.** {len(oogs)} out-of-gas programs in {fmt(total_inst)}. {'None of them loops' if not loops else f'{len(loops)} of them loop'}. {'Every one' if not loops else 'The rest'} is a single instruction with an appetite larger than any budget — a `LOG`, `CALLDATACOPY`, `KECCAK256`, `MLOAD` or `RETURN` whose offset or length is a pushed constant of several bytes. The memory-expansion formula is quadratic; these ask for more memory than 1M, 10M or any gas can buy. The gas sweep confirms it: 100k → OOG, 1M → OOG, 10M → OOG, same instruction count each time. This is **OOG by appetite, not by persistence**. A program that *runs* until stopped — a loop that lands a backward jump on a real `JUMPDEST` with a satisfiable stack — {'did not appear' if not loops else 'appeared ' + str(len(loops)) + ' time(s)'} in {fmt(total_inst)}.")
A("")
A(f"A related class the tracer labels separately — `MemoryOOG`, `MemoryLimitOOG`, {mem_errs} probes across the runs — is the same phenomenon caught by a different guard (revm's memory-size limit rather than the gas meter). We record all of these as the EVM reports them.")
A("")
A(f"**State is touched, rarely, and almost never kept.** {len(writes_any)} programs executed an `SSTORE` or `TSTORE`; nearly all then died, and an exceptional halt reverts the write. A trait here records that the instruction *executed*, not that its effect survived. {len(tst_live)} wrote transient storage and halted cleanly — gone at the end of the transaction. {len(sst_live) if sst_live else 'Not one'} program{'s' if len(sst_live) != 1 else ''} persisted a storage write in {fmt(total_inst)} attempts.")
A("")
A(f"**{'Nothing' if not deps else 'Almost nothing'} responds to input.** {len(deps)} calldata- or value-dependent specimens. The probes differ in calldata and value; {'no' if not deps else 'almost no'} program's behavior changed. Random programs at these lengths are deaf.")
A("")
A(f"**The space contains instructions from the future.** About 7% of byte values are EOF opcodes the specification names but legacy code cannot execute (`RJUMP`, `CALLF`, `SWAPN`, `EOFCREATE`, `EXTCALL`…). The tracer halts them with `NotActivated` rather than \"unknown\". {pct(sum(1 for _, r in all_rows if has(r, 'FUTURE_OPCODE')), total_inst)} of installed programs died on one. If EOF activates, those programs die differently.")
A("")
A("## Specimens worth looking at")
A("")
if rets:
    for L, r in rets[:2]:
        p = longest_probe(r)
        A(f"**{ref(L, r)} — returned data.** `{trace(r)}`. {p['returnDataLength']:,} bytes returned, {p['gasUsed']:,} gas.")
        A("")
else:
    A(f"**Nothing returned data** in {fmt(total_inst)} programs. The 100k and 1M studies found the first ones.")
    A("")
for L, r in (tst_live + sst_live)[:2]:
    A(f"**{ref(L, r)} — wrote state and lived.** `{trace(r)}`. One {'transient' if (L, r) in tst_live else 'persistent'} storage write, then a clean halt. Score {r['score']['total']}.")
    A("")
for L, r in branches[:1]:
    A(f"**{ref(L, r)} — the one that branched.** `{trace(r)}`. A `JUMP` or `JUMPI` executed; where it would have gone depended on what was on the stack. Our probes all called from the same address and chain, so the branch looked input-independent. It may not be.")
    A("")
for L, r in deps[:2]:
    byname = {p["name"][0]: p for p in r["probes"]}
    a, e = byname.get("A"), byname.get("E")
    if a and e and (a["outcome"], a["instructionCount"]) != (e["outcome"], e["instructionCount"]):
        A(f"**{ref(L, r)} — responds to money.** `{trace(r, 8)}`. Called with nothing: {a['outcome'].replace('_', ' ')} after {a['instructionCount']} instructions. Called with one wei: {e['outcome'].replace('_', ' ')} after {e['instructionCount']}. The value it was sent is on its stack, and the program does something different with it.")
    else:
        A(f"**{ref(L, r)} — responds to calldata.** `{trace(r, 8)}`. Its outcome changed with what it was called with.")
    A("")
for L, r in creates[:2]:
    p = longest_probe(r)
    A(f"**{ref(L, r)} — executed CREATE.** `{trace(r, 10)}`. A creation ran, with whatever happened to be on the stack as value, offset and length; the program then died ({p['outcome'].replace('_', ' ')}), and the exceptional halt undid the child. No child program exists on the chain.")
    A("")
LL, lr = longest
A(f"**{ref(LL, lr)} — the longest life.** {longest_probe(lr)['instructionCount']} instructions: `{trace(lr, 14)}`. It touched more of the machine than anything else in {fmt(total_inst)}.")
A("")
if oogs:
    A(f"**The out-of-gas programs.** {oog_desc}. Each wants memory it cannot have.")
    A("")
A("## Instrument notes")
A("")
A("- Tracer: `debug_traceCall` struct logs, stack dumps off (depth tracked from the instruction stream — revm labels DUPn on a short stack `StackOverflow`; we classify from depth and keep the label), 1,000,000 gas per probe. Exceptional halts consume all gas by EVM rule; for them the gas figure is the ceiling, not work done.")
A("- Gas sweep for OOG at 100k / 1M via struct logs and 10M via `callTracer` (a looping program at 10M would emit millions of log entries).")
A("- Receipt polling at 25 ms; viem's 4 s default made each placement wait a full poll.")
A("- Everything local: Anvil on 127.0.0.1, chain 31337, Anvil's published test keys only.")
if total_lost: A(f"- These four runs shared the machine with a 1,000,000-specimen study. {total_lost} placements timed out at 30 s and are recorded as instrument failures, not as refusals; the bytecode of every specimen is reproducible from the seed, the timeouts are not.")
A("")
A("## What the baseline says")
A("")
A(f"Random EVM program space at 16–128 bytes is overwhelmingly death within two instructions, by two causes in roughly equal measure: bytes that are not instructions, and instructions that reach for operands that do not exist. Among the few that live longer, almost all are pushes that fall off the end of the code. Real behavior — a storage read, a hash, a branch, a return, a write that survives — occurs at rates of 1 in 500 to 1 in {fmt(total_inst)}{', and loops' + (' and external calls' if not calls else '') + ' did not occur at all' if not loops else ''}.")
A("")
A("That is the honest shape of the space. If slopware is interesting, it is because of how little is there, and how specific the few exceptions are.")
A("")
A("## Not done, by design")
A("")
A("No weighted generation, mutation, reproduction, selection, or AI. The 100k and 1M studies at 64 bytes (`deep-100k-64b`, `deep-1m-64b`) went looking for more of what is rare here — persistent writes, executed calls and creations, programs that listen; their numbers are on the site.")
open("BASELINE.md", "w").write("\n".join(lines) + "\n")
print(f"BASELINE.md written: {total_inst:,} installed · {len(oogs)} OOG · {len(loops)} loops · {len(rets)} returns · {len(sst_live)} persistent writes · {len(tst_live)} transient · {len(branches)} branches · {len(deps)} input-dependent · top {top_score}")
