#!/usr/bin/env python3
"""
packdraw PF exploit verification kit (their own published algorithm, fairness page).

ticket = (int(sha512(f"{clientSeed}:{serverSeed}:{nonce}"), 16) % 1_000_000) + 1
jackpot = (int(sha256(eosBlockHash), 16) % totalTickets) + 1

Usage:
  python3 packdraw_verify.py ticket <clientSeed> <serverSeed> <nonce>
  python3 packdraw_verify.py commit-check <revealedSeed> <profileHashedSeed>
  python3 packdraw_verify.py grind <serverSeed> <clientSeed> <nextNonce> <packPrice> <ranges.json>
  python3 packdraw_verify.py jackpot <eosBlockHash> <totalTickets>

2-OPEN TEST PROTOCOL (the decisive test; operator account, self-funded, non-destructive):
  1. Profile -> record the displayed server seed HASH (H0) BEFORE any purchase.
  2. Open pack #1 (client seed C1 as shown in profile/settings): after open, history shows
     C1, revealed server seed S1, nonce N1. Record all three.
  3. CHECK A: sha512(S1) == H0  (commitment discipline — their doc says this must hold).
  4. Check the profile hash again (H1) BEFORE purchase #2. Do NOT change client seed.
  5. Open pack #2: record C2, S2, N2.
  6. CHECK B: S2 == S1 (seed NOT rotated => PREDICTIVE: every future ticket computable
     before paying; with the public per-pack ticket ranges, open only tickets with
     EV > price => guaranteed-profit grind against the house). If S2 != S1 => rotating
     seeds, scheme sound, closeout clean.
  NONCE NOTE (their doc): nonce auto-increments "when server seeds and client seeds
  remain unchanged, as is the case when opening multiple packs in a single purchase" —
  so within multi-pack purchases N increments; between purchases N may reset or continue.
"""
import hashlib
import json
import sys

MAX_TICKET = 1_000_000

def sha512(s: str) -> str:
    return hashlib.sha512(s.encode()).hexdigest()

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def combine_seeds(client_seed: str, server_seed: str, nonce: int) -> str:
    return sha512(f"{client_seed}:{server_seed}:{nonce}")

def get_ticket(client_seed: str, server_seed: str, nonce: int) -> int:
    h = combine_seeds(client_seed, server_seed, nonce)
    return (int(h, 16) % MAX_TICKET) + 1

def commit_check(revealed_seed: str, profile_hash: str) -> bool:
    return sha512(revealed_seed) == profile_hash.lower()

def jackpot_ticket(eos_block_hash: str, total_tickets: int) -> int:
    return (int(sha256(eos_block_hash), 16) % total_tickets) + 1

def pack_ranges_from_odds(odds: list) -> list:
    """odds = [(name, price, pct), ...] -> [(name, price, start, end), ...]"""
    ranges, cum = [], 0.0
    for name, price, pct in odds:
        start = int(cum * MAX_TICKET) + 1
        cum += pct / 100.0
        end = min(int(cum * MAX_TICKET), MAX_TICKET)
        ranges.append((name, price, start, end))
    return ranges

def ticket_item(ticket: int, ranges: list):
    for name, price, start, end in ranges:
        if start <= ticket <= end:
            return name, price
    return None, None

def grind_scan(server_seed: str, client_seed: str, nonce_from: int, nonce_to: int,
               pack_price: float, ranges: list, lucky: int = 20):
    """Simulate the drain: compute each future ticket and find +EV opens."""
    hits = []
    for n in range(nonce_from, nonce_from + min(nonce_to - nonce_from, 50000) if nonce_to else lucky):
        t = get_ticket(client_seed, server_seed, n)
        name, price = ticket_item(t, ranges)
        if price and price > pack_price:
            hits.append((n, t, price, name))
            if len(hits) >= lucky:
                break
    return hits

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "ticket" and len(sys.argv) == 5:
        cs, ss, n = sys.argv[2], sys.argv[3], int(sys.argv[4])
        print("ticket:", get_ticket(cs, ss, n))
    elif cmd == "commit-check" and len(sys.argv) == 4:
        print("commit OK" if commit_check(sys.argv[2], sys.argv[3]) else "COMMIT MISMATCH")
    elif cmd == "jackpot" and len(sys.argv) == 4:
        print("winning ticket:", jackpot_ticket(sys.argv[2], int(sys.argv[3])))
    elif cmd == "grind" and len(sys.argv) == 8:
        ss, cs, nf, nt, price, ranges_file = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6]), sys.argv[7]
        ranges = pack_ranges_from_odds(json.load(open(ranges_file)))
        for nonce, t, p, name in grind_scan(ss, cs, nf, nt, price, ranges):
            print(f"nonce={nonce} ticket={t} value=${p} ITEM={name}")
    else:
        print(__doc__)
        print("RANGES FILE: [['Item name', 123.45, 0.0200], ...]  (name, price, pct per row — from the pack detail page)")