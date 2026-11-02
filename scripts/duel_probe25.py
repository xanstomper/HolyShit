#!/usr/bin/env python3
"""probe25: THE derivation test - predicted roulette tickets vs observed, control (prev period) vs current (anomaly)"""
import hashlib
import json
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def hdrs():
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": BASE, "Referer": BASE + "/",
    }


seeds = json.load(open("/dev/shm/.dkv/roulette_seeds.json"))
seeds.sort(key=lambda x: x["startRound"])
cur = seeds[-1]
prev = seeds[-2]
print("--- prev period:", prev["startRound"], "seed", prev["serverSeed"][:12],
      "pub", prev["publicSeed"])
print("--- cur period:", cur["startRound"], "seed(field)", cur["serverSeed"][:12],
      "hash", cur["serverSeedHash"][:12], "pub", cur["publicSeed"])

hist = None
for q in ("?limit=500", "?limit=200", ""):
    r = requests.get(BASE + "/ws/games/roulette/history" + q, headers=hdrs(), timeout=20)
    if r.status_code == 200:
        hist = r.json()
        print(f"--- history {q}: {len(hist)} rounds; sample:",
              json.dumps(hist[0])[:160] if hist else None)
        if len(hist) >= 50:
            break
    time.sleep(7)

if not hist:
    raise SystemExit("no history")

played = [h for h in hist if h.get("participants", 0) > 0]
print("--- rounds with participants:", len(played), "/", len(hist))
tickets = sorted({h.get("ticket") for h in played})
print("--- ticket value range:", tickets[:20])

def predict(seed, pub, rnd):
    h = hashlib.sha256(f"{seed}:{pub}:{rnd}".encode()).hexdigest()
    return int(h[:8], 16) % 15

# CONTROL: previous period (revealed seed) - validates the formula
ctl = [h for h in played if prev["startRound"] <= h["id"] < cur["startRound"]]
print("--- control rounds in prev period:", len(ctl))
ok = sum(1 for h in ctl if predict(prev["serverSeed"], prev["publicSeed"], h["id"]) == h["ticket"])
print(f"--- CONTROL match: {ok}/{len(ctl)}")

# CURRENT period (anomalous hash-as-seed record)
cut = [h for h in played if h["id"] >= cur["startRound"]]
print("--- current-period rounds:", len(cut))
ok2 = sum(1 for h in cut if predict(cur["serverSeed"], cur["publicSeed"], h["id"]) == h["ticket"])
print(f"--- CURRENT match (published-as-seed): {ok2}/{len(cut)}")
if cut:
    for h in cut[:8]:
        print("   round", h["id"], "actual", h["ticket"],
              "pred", predict(cur["serverSeed"], cur["publicSeed"], h["id"]))
