#!/usr/bin/env python3
"""probe23: FULL roulette seeds analysis + seeds matrix for all in-house games + roulette chunk paths"""
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


r = requests.get(BASE + "/ws/games/roulette/seeds", headers=hdrs(), timeout=20)
print("--- roulette seeds:", r.status_code, "bytes", len(r.text))
try:
    recs = r.json()
    open("/dev/shm/.dkv/roulette_seeds.json", "w").write(json.dumps(recs))
    print("--- record count:", len(recs))
    eq = sum(1 for x in recs if x.get("serverSeed") == x.get("serverSeedHash"))
    print("--- records where serverSeed == serverSeedHash:", eq, "/", len(recs))
    print("--- keys:", sorted({k for x in recs for k in x.keys()}))
    for x in recs[-6:]:
        print("--- rec:", {k: (v[:18] + "..." if isinstance(v, str) and len(v) > 24 else v)
                          for k, v in x.items()})
    # verify hash relation on records where seeds differ
    for x in recs:
        s, h = x.get("serverSeed"), x.get("serverSeedHash")
        if s and h and s != h:
            calc = hashlib.sha256(s.encode()).hexdigest()
            print("--- seed!=hash record: sha256(serverSeed)==serverSeedHash?", calc == h,
                  "| startRound", x.get("startRound"), "| ts", x.get("timestamp"))
except Exception as e:
    print("--- parse err:", str(e)[:150])
time.sleep(8)

for game in ("dice", "mines", "plinko", "crash", "cannonball", "blackjack"):
    try:
        rr = requests.get(f"{BASE}/ws/games/{game}/seeds", headers=hdrs(), timeout=20)
        print(f"--- GET /ws/games/{game}/seeds: {rr.status_code} {rr.text[:160]}")
    except Exception as e:
        print(f"--- {game}: ERR {str(e)[:80]}")
    time.sleep(8)

r = requests.get(BASE + "/assets/roulette-BT0NZinn.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Site": "same-origin",
}, timeout=20)
t = r.text
print("=== roulette chunk", r.status_code, len(t))
paths = sorted(set(re.findall(r"`(/[a-zA-Z][a-zA-Z0-9/_.$${}\[\]-]{0,70})`", t)))
print("--- paths:", paths[:24])
strs = sorted(set(re.findall(r"`([a-z][a-zA-Z_/-]{3,40})`", t)))
print("--- strings:", strs[:40])
