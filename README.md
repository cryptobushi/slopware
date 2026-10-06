# SLOPWARE

*software nobody wrote*

Software is written: someone decides what it should do and writes it, and it does that, more or less. Slopware is installed before it exists. You press install. In the next block, Ethereum fixes sixty-four bytes nobody chose, and those bytes become the whole of a program at an address of its own. Nothing reads them first. Nothing repairs them. Nothing tries again.

```
randomness → bytecode → EVM → ?
```

Conventional generative art is code → randomness → image. This runs the other way. The program is the sculpture, placed on the world computer. The token is the receipt. The installer is the only program here anyone wrote.

## This repository

| | |
|---|---|
| [`slopware/`](slopware/README.md) | the work: one immutable ERC-721 installer (`contracts/`), a keeper that completes installations (`keeper/`), the site (`site/`), and the documents — [randomness](slopware/RANDOMNESS.md), [security](slopware/SECURITY.md), [what was left out](slopware/FUTURE.md), [launch](slopware/LAUNCH.md) |
| `src/`, `scripts/` | the lab: an instrument that samples random EVM program space on a local chain and records what is there |
| [`BASELINE.md`](BASELINE.md) | what the lab found, with every number reproducible from a seed |

The lab came first. Before building an installer that would put unknown programs on Ethereum for money, we wanted to know, empirically and without flattering the result, what random bytecode does. The answer shaped the work: no filtering, no retries, no "observed behavior" on the token, and a site that says `UNKNOWN` and means it.

## The invariant

For every installed release:

```
eth_getCode(program) == bytecode        // sixty-four bytes, nothing before, nothing after
```

Random bytes are placed by `CREATE` behind an eleven-byte loader whose only job is to copy them into memory and return them, so the bytes become the program's *runtime* code unchanged. The installer never calls the program. The lab verifies the same equality for every specimen it places, byte for byte, before probing it.

## The lab

The lab deploys arbitrary programs on purpose, so it runs only against a local chain. It refuses any RPC whose host is not `localhost` / `127.0.0.1` or whose chain id is not `31337`, and the only keys it holds are Anvil's published test keys.

Requires Node 20+ and Foundry.

```sh
npm install
npm run chain                                                   # anvil on 127.0.0.1:8546
npm run explore -- --count 100 --bytes 64                       # cryptographically random
npm run explore -- --count 10000 --bytes 64 --seed slopware-baseline-64   # deterministic
npm run inspect -- --run <run-id> --id 000042                   # one specimen, disassembled, every probe
npm run replay  -- --run <run-id> --id 000042                   # place it again and compare behavior
```

Options: `--count`, `--bytes`, `--seed`, `--probes` (letters from `ABCDE`), `--workers` (≤10), `--top` (how many high-scoring records to copy aside), `--compact` (drop opcode lists for programs that die within two instructions), `--run` (run id), `--rpc` (local only).

**Seeds.** With `--seed`, every byte a run consumes — specimen bytecode *and* probe payloads — comes from one stream of `keccak256(seed ‖ counter)` blocks. The same seed, count and length reproduce every specimen and every probe exactly, on any machine.

**Probes.** Each placed specimen is called five ways under a 1,000,000-gas ceiling with every executed opcode traced:

| | calldata | value |
|---|---|---|
| A | empty | 0 |
| B | 32 zero bytes | 0 |
| C | 32 random bytes | 0 |
| D | 4-byte selector + 32-byte argument, random | 0 |
| E | empty | 1 wei |

A specimen that runs out of gas is swept again at 100k, 1M and 10M gas to tell a loop from a single instruction with an appetite for memory.

**Records.** Every run writes `results/<run-id>/run.json`, `specimens.jsonl` (one record per specimen: bytecode, keccak, placement, every probe with its trace, traits, classification, score, and the probe payloads, so any specimen can be replayed) and `summary.json`. `scripts/rare.py <run-id>` pulls out the rare behaviors; `scripts/lab_json.py <run-id>` writes the numbers the site's lab section reads.

**How random programs fail.** Roughly half of all byte values are not instructions; executing one halts. Most instructions pop operands, and a random program almost always reaches one before it has pushed enough. `PUSHn` swallows the next *n* bytes as data, so long pushes eat large stretches of the bytecode, and a push that runs past the end of the code is an implicit `STOP`. Exceptional halts consume all gas supplied, so the gas figure for them is the ceiling, not work done. One tracer quirk is handled explicitly: Anvil labels a `DUPn` on a short stack `StackOverflow`; the classifier decides underflow versus overflow from the recorded stack depth and keeps the tracer's label alongside. About 7% of byte values are EOF opcodes the specification names but legacy code cannot execute; these are recorded as `FUTURE_OPCODE`, not as unknown.

Traits are observations, not judgements. `UNKNOWN` is a legitimate classification: the machine can list the instructions without our understanding the program.

## Running the work locally

```sh
./slopware/sim.sh     # anvil (osaka, 2 s blocks) + installer + keeper + site at http://127.0.0.1:8001
cd slopware/contracts && forge test
```

Nothing in this repository deploys to mainnet by itself. See [`slopware/LAUNCH.md`](slopware/LAUNCH.md).

## Principle

Simple over clever. Preserve the bytecode over convenience. Never improve a random program. The artwork is not that slopware is good software. The artwork is that nobody knows what it is.
