# SLOPWARE — Baseline

*Uniform random EVM runtime bytecode, 10,000 specimens at each of four lengths, five probes each, full tracing. 2026-10-06. Seeds `slopware-baseline-16/32/64/128`; every number below is reproducible to the byte with `npm run explore -- --count 10000 --bytes <L> --seed slopware-baseline-<L>`.*

The generator was not tuned. Nothing was discarded. This is what the space contains.

## The distribution

| | 16 bytes | 32 bytes | 64 bytes | 128 bytes |
|---|---:|---:|---:|---:|
| installed | 99.62% | 99.57% | 99.68% | 99.72% |
| refused (leading `0xEF`, EIP-3541) | 38 | 40 | 32 | 26 |
| lost to the instrument (placement timed out) | 0 | 3 | 0 | 2 |
| probes run | 49,810 | 49,785 | 49,840 | 49,860 |
| **execution success** | **8.99%** | **2.57%** | **1.05%** | **0.46%** |
| instructions: mean / median | 1.26 / 1 | 1.28 / 1 | 1.31 / 1 | 1.28 / 1 |
| instructions: p90 / max | 2 / 7 | 2 / 10 | 2 / 10 | 2 / 11 |
| died at first instruction | 78.9% | 78.7% | 77.7% | 79.4% |
| invalid opcode | 48.3% | 53.3% | 53.8% | 53.7% |
| stack underflow | 42.6% | 44.0% | 44.9% | 45.6% |
| bad jump | 0.03% | 0.11% | 0.13% | 0.12% |
| revert | 0.01% | 0.01% | 0.04% | 0 |
| **out of gas** | **0.02%** | **0.02%** | **0.05%** | **0.01%** |
| other halt (memory) | 0.05% | 0.02% | 0.05% | 0.04% |
| state read (SLOAD/TLOAD executed) | 0.18% | 0.17% | 0.27% | 0.21% |
| state write (SSTORE/TSTORE executed) | 0.06% | 0.05% | 0.06% | 0.06% |
| hashing | 0.01% | 0 | 0.02% | 0.01% |
| branching (JUMP/JUMPI executed) | 0 | 0 | 0.01% | 0 |
| emits log | 0 | 0.01% | 0.01% | 0.01% |
| returns data | 0 | 0 | 0 | 0 |
| external call executed | 0 | 0 | 0 | 0 |
| contract creation executed | 0 | 0 | 0.02% | 0 |
| calldata-dependent | 0 | 0 | 0 | 0 |
| value-dependent | 0 | 0 | 0.02% | 0.01% |

Lifespan (instructions before halt, empty calldata, installed specimens):

| instructions | 16 b | 32 b | 64 b | 128 b |
|---:|---:|---:|---:|---:|
| 1 | 7,888 | 7,873 | 7,802 | 7,952 |
| 2 | 1,697 | 1,579 | 1,570 | 1,494 |
| 3 | 288 | 358 | 385 | 328 |
| 4 | 68 | 98 | 138 | 134 |
| 5 | 16 | 35 | 48 | 49 |
| 6 | 4 | 9 | 17 | 11 |
| 7+ | 1 | 5 | 8 | 4 |

Interestingness: at least 90.8% of every run scores under 10. The highest score in 39,995 specimens is 48.

## What the numbers mean

**Lifespan is geometric and does not depend on length.** About 21% of random programs survive their first instruction; of those, a similar share survive the second; and so on. The mean sits between 1.26 and 1.31 at every length. The reason is arithmetic: of 256 byte values, only 55 are defined opcodes that need no operands (STOP, PUSH0–PUSH32, the environment reads, PC, MSIZE, GAS, JUMPDEST). A random first byte is one of them with probability 0.215. Each later instruction faces similar odds, slightly improved by whatever the pushes left on the stack. Length is nearly irrelevant to how long a program lives; it only changes how it ends.

**Short programs "succeed" by running off the end.** Execution success is 8.99% at 16 bytes and 0.46% at 128. The difference is not ability; it is the edge of the code. `PUSHn` consumes the next *n* bytes as data, so a 16-byte program whose first instructions are pushes often has its program counter walk past the last byte — and executing past the end of code is an implicit `STOP`. Longer programs keep going and die. The commonest clean halt is a handful of pushes followed by nothing.

**Roughly half of all bytes are not instructions at all.** 51% of byte values are undefined, and within defined programs PUSH immediates swallow 20–50% of the code. Of the 128 bytes in a long specimen, perhaps 40 are ever candidates to execute.

**Out of gas exists, but not the way we imagined.** 10 out-of-gas programs in 39,859. None of them loops. Every one is a single instruction with an appetite larger than any budget — a `LOG`, `CALLDATACOPY`, `KECCAK256`, `MLOAD` or `RETURN` whose offset or length is a pushed constant of several bytes. The memory-expansion formula is quadratic; these ask for more memory than 1M, 10M or any gas can buy. The gas sweep confirms it: 100k → OOG, 1M → OOG, 10M → OOG, same instruction count each time. This is **OOG by appetite, not by persistence**. A program that *runs* until stopped — a loop that lands a backward jump on a real `JUMPDEST` with a satisfiable stack — did not appear in 39,859.

A related class the tracer labels separately — `MemoryOOG`, `MemoryLimitOOG`, 86 probes across the runs — is the same phenomenon caught by a different guard (revm's memory-size limit rather than the gas meter). We record all of these as the EVM reports them.

**State is touched, rarely, and almost never kept.** 23 programs executed an `SSTORE` or `TSTORE`; nearly all then died, and an exceptional halt reverts the write. A trait here records that the instruction *executed*, not that its effect survived. 1 wrote transient storage and halted cleanly — gone at the end of the transaction. 1 program persisted a storage write in 39,859 attempts.

**Almost nothing responds to input.** 3 calldata- or value-dependent specimens. The probes differ in calldata and value; almost no program's behavior changed. Random programs at these lengths are deaf.

**The space contains instructions from the future.** About 7% of byte values are EOF opcodes the specification names but legacy code cannot execute (`RJUMP`, `CALLF`, `SWAPN`, `EOFCREATE`, `EXTCALL`…). The tracer halts them with `NotActivated` rather than "unknown". 1.98% of installed programs died on one. If EOF activates, those programs die differently.

## Specimens worth looking at

**Nothing returned data** in 39,859 programs. The 100k and 1M studies found the first ones.

**`slopware-baseline-10k-64b` #001238 — wrote state and lived.** `PUSH31 · CHAINID · TSTORE · PUSH20 · PUSH21 · STOP`. One transient storage write, then a clean halt. Score 43.

**`slopware-baseline-10k-16b` #008338 — wrote state and lived.** `CODESIZE · GASLIMIT · EXTCODEHASH · PUSH11 · SSTORE · STOP`. One persistent storage write, then a clean halt. Score 43.

**`slopware-baseline-10k-64b` #004009 — the one that branched.** `PUSH0 · ORIGIN · PUSH0 · POP · JUMPI · ISZERO`. A `JUMP` or `JUMPI` executed; where it would have gone depended on what was on the stack. Our probes all called from the same address and chain, so the branch looked input-independent. It may not be.

**`slopware-baseline-10k-64b` #007868 — responds to money.** `SELFBALANCE · PUSH21 · RETURN`. Called with nothing: success after 3 instructions. Called with one wei: invalid opcode after 3. The value it was sent is on its stack, and the program does something different with it.

**`slopware-baseline-10k-64b` #009694 — responds to money.** `MSIZE · PUSH27 · BLOBBASEFEE · CREATE · STOP · DUP8`. Called with nothing: stack underflow after 5 instructions. Called with one wei: stack underflow after 6. The value it was sent is on its stack, and the program does something different with it.

**`slopware-baseline-10k-64b` #008904 — executed CREATE.** `SELFBALANCE · PUSH21 · PUSH7 · NUMBER · MSIZE · ISZERO · DUP5 · CREATE2 · STOP · Unknown`. A creation ran, with whatever happened to be on the stack as value, offset and length; the program then died (invalid opcode), and the exceptional halt undid the child. No child program exists on the chain.

**`slopware-baseline-10k-64b` #009694 — executed CREATE.** `MSIZE · PUSH27 · BLOBBASEFEE · CREATE · STOP · DUP8`. A creation ran, with whatever happened to be on the stack as value, offset and length; the program then died (stack underflow), and the exceptional halt undid the child. No child program exists on the chain.

**`slopware-baseline-10k-128b` #000665 — the longest life.** 11 instructions: `DIFFICULTY · PUSH24 · SGT · PUSH31 · PUSH3 · EXTCODEHASH · BLOCKHASH · SUB · MUL · NOT · DUP3`. It touched more of the machine than anything else in 39,859.

**The out-of-gas programs.** `PUSH4 · PUSH3 · LOG3` (16 b #000553); `TIMESTAMP · ADDRESS · PUSH0 · BYTE · LOG0` (16 b #009672); `PUSH8 · COINBASE · NOT · PUSH15 · CALLDATACOPY` (32 b #002373); `PUSH8 · PUSH1 · LOG0` (32 b #005283); `PC · BALANCE · TIMESTAMP · LOG1` (64 b #000119); `GASLIMIT · CODESIZE · LOG2` (64 b #001829). Each wants memory it cannot have.

## Instrument notes

- Tracer: `debug_traceCall` struct logs, stack dumps off (depth tracked from the instruction stream — revm labels DUPn on a short stack `StackOverflow`; we classify from depth and keep the label), 1,000,000 gas per probe. Exceptional halts consume all gas by EVM rule; for them the gas figure is the ceiling, not work done.
- Gas sweep for OOG at 100k / 1M via struct logs and 10M via `callTracer` (a looping program at 10M would emit millions of log entries).
- Receipt polling at 25 ms; viem's 4 s default made each placement wait a full poll.
- Everything local: Anvil on 127.0.0.1, chain 31337, Anvil's published test keys only.
- These four runs shared the machine with a 1,000,000-specimen study. 5 placements timed out at 30 s and are recorded as instrument failures, not as refusals; the bytecode of every specimen is reproducible from the seed, the timeouts are not.

## What the baseline says

Random EVM program space at 16–128 bytes is overwhelmingly death within two instructions, by two causes in roughly equal measure: bytes that are not instructions, and instructions that reach for operands that do not exist. Among the few that live longer, almost all are pushes that fall off the end of the code. Real behavior — a storage read, a hash, a branch, a return, a write that survives — occurs at rates of 1 in 500 to 1 in 39,859, and loops and external calls did not occur at all.

That is the honest shape of the space. If slopware is interesting, it is because of how little is there, and how specific the few exceptions are.

## Not done, by design

No weighted generation, mutation, reproduction, selection, or AI. The 100k and 1M studies at 64 bytes (`deep-100k-64b`, `deep-1m-64b`) went looking for more of what is rare here — persistent writes, executed calls and creations, programs that listen; their numbers are on the site.
