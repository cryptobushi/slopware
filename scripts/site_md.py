#!/usr/bin/env python3
"""Agent-facing text for slopware.fun: llms.txt and readings.md, generated from the same data the pages use.

  python3 scripts/site_md.py

readings.md is one line per release from slopware/site/r/index.json (the readings' own sentences); llms.txt is the
site's summary for language models with links to the Markdown mirrors. e1.md is written by scripts/e1_page.py."""
import json, datetime

SITE = "slopware/site"
idx = json.load(open(f"{SITE}/r/index.json"))
rs = sorted(idx["readings"], key=lambda r: r["id"])
s = idx["summary"]
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

lines = ["# SLOPWARE — readings", "", f"The lab's observations of every program SLOPWARE has installed, as of {now}: {s['releasesRead']:,} releases read, {s['installed']:,} installed, {s['refused']} refused by Ethereum. Each installed program's sixty-four bytes were placed on a private copy of Ethereum and called five ways with every instruction traced. Observation, not record: the installer itself records nothing about behaviour. The siblings line comes from experiment E1 (https://slopware.fun/e1.md).", "",
         f"- {100*s['diedAtFirst']/max(1,s['installed']):.1f}% died on their first instruction (the million-program study found {s['labPrediction']['diedAtFirstPct']}%)", f"- longest run: {s['longest']} instructions", f"- {s['cleanHalts']} halted cleanly", f"- {s['inputDependent']} answered differently to different input", f"- {s['returnedData']} returned data", f"- {s['withFutureOpcodes']} carry an instruction Ethereum does not activate yet", "", "## Every release", ""]
for r in rs:
    bits = [f"**SLOPWARE {r['id']:06d}** · {r['status']}" + (f" · program {r['program']}" if r.get("program") else "") + f" · installed by {r['by']}", r["verdict"]]
    if r.get("would"): bits.append(r["would"])
    if r.get("trace"): bits.append(f"Trace: {r['trace']}")
    if r.get("sib"): bits.append(r["sib"])
    lines.append(" ".join(bits)); lines.append("")
open(f"{SITE}/readings.md", "w").write("\n".join(lines))

llms = f"""# SLOPWARE

> Software nobody wrote. An immutable Ethereum contract (the installer, 0x44a64905069963b8321ee2b755a0b8b56d69cbc6, mainnet) places sixty-four random bytes, decided by the hash of the block after the request, as a new program's entire runtime code. Nothing chooses the bytes: not the collector, not the artist, not the keeper. Each release has an ERC-721 receipt stating facts only. The lab then observes what each program does, separately, and says so.

Site: https://slopware.fun · Repository: https://github.com/cryptobushi/slopware · Artist: Bushi (https://x.com/bushibuilds)

## What is where

- Catalogue (the installer, every release, install from a wallet): https://slopware.fun/ — live numbers come from https://slopware.fun/api/state (JSON: block, price in wei, releases, installed, rejected).
- Readings (the lab's observations, one life per release): https://slopware.fun/readings — Markdown mirror https://slopware.fun/readings.md — data https://slopware.fun/r/index.json (index with sentences) and https://slopware.fun/r/d-N.json (bytes, disassembly and five calls per 100 releases) — full record https://slopware.fun/readings.json.
- E1, the first pre-registered experiment (one-byte neighbourhoods of every genesis program, 26 million placements, results, data, research edition auction): https://slopware.fun/e1 — Markdown mirror https://slopware.fun/e1.md — data https://slopware.fun/e1-data/e1.json — picture https://slopware.fun/e1-data/threads.png.
- Protocol, constitution, roadmap, security notes, launch record: the repository, in particular slopware/experiments/E1-neighbourhoods.md, slopware/ROADMAP.md, slopware/SECURITY.md, slopware/LAUNCH.md.

## Facts an agent is often asked for

- Installer contract: 0x44a64905069963b8321ee2b755a0b8b56d69cbc6 (Ethereum mainnet; Sourcify exact match). Price is set by the artist with setPrice and is the only mutable thing; there is no pause, cap, allowlist or owner mint. Current price and counts: /api/state.
- Install flow: install() or installMany(n ≤ 100) pays the price per release and records the request block R; after block R+1 exists anyone calls complete(release) (the keeper does it within a minute or two for anyone who walks away); the bytes are keccak256(blockhash(R+1), release, 0) ‖ keccak256(…, 1); if the first byte is 0xEF Ethereum refuses the program (EIP-3541) and the release is recorded as refused with its bytes kept; otherwise the 64 bytes become a contract's entire runtime code and the receipt records the program's address and checksum.
- Keeper: 0xB847754313D6320f43396F885d168b0B433b913f, a scheduled function that completes installations; it has no power over any outcome. It also signs the research editions.
- Research editions contract: 0x55540e5bcd1b0a1e2c00de4ae55ef007bde35664 ("SLOPWARE research editions"), one artwork per pre-registered experiment, minted by the keeper, proceeds to the artist, no rights conferred. Token 1 is THREADS (E1), Manifold marketplace listing 20909, reserve 0.05 ETH.
- E1 results in one line each: H1 held (collected programs behave under mutation exactly like fresh random ones); H2 held (a byte a program never reaches can be anything, median error 0.0062); H3 not held as written because the pre-registration miscounted (54 living first bytes, not 55, over 254 placeable replacements; observed 21.26% = 54/254); H4 held (0.37% of one-mutants live longer than the parent, bound 3%); H5 not held narrowly (one replicated one-mutant executes a CREATE that fails for lack of balance and then halts cleanly; nothing is created).
- Vocabulary: the catalogue states facts (install, release, program, refused); the lab records what executed; the readings interpret in a figurative voice (lives, deaths, siblings). Receipts never carry behaviour, traits or rarity.

## For quoting

The three sentences of E1: One byte changed at random in a random program is, with 98.4% certainty, the same program; the rest is almost entirely a different way to die. The programs people bought behave under mutation exactly like programs nobody bought, so there is nothing in the catalogue that the lab's distribution does not already contain. The single new thing in twenty-six million tries was a program that tries to create another, is refused for offering money it does not have, and then rests instead of dying, which is not reproduction, and is still more than anything in the million-program study did.
"""
open(f"{SITE}/llms.txt", "w").write(llms)
print(f"readings.md: {len(rs)} releases · llms.txt written")
