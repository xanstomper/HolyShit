#!/usr/bin/env python3
"""probe30: local feed analysis (staff accounts?) + roulette history walk-back for played rounds + derivation test"""
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


# 1) local analysis of the saved feed
j = json.load(open("/dev/shm/.dkv/bets_live.json"))
seen_users = {}
staff = []
for key in ("all", "large", "lucky", "wins"):
    for rec in j.get(key, []):
        u = rec.get("user") or {}
        if u.get("id"):
            seen_users[u["id"]] = u
            if u.get("authRole", 0) not in (0, None):
                staff.append((key, u.get("displayName"), u.get("authRole")))
print("--- unique users in feed:", len(seen_users))
print("--- staff (authRole>0):", staff[:6])
print("--- levels:", sorted({u.get("level") for u in seen_users.values()}))
print("--- verified flags:", sorted({u.get("verified") for u in seen_users.values()}))

# 2) roulette history walk-back
seeds = json.load(open("/dev/shm/.dkv/roulette_seeds.json"))
seeds.sort(key=lambda x: x["startRound"])
cur = seeds[-1]
mid = cur["startRound"] + 2000
played = []
for before in ("", f"?before={mid}&limit=100", f"?before={cur['startRound'] + 4000}&limit=100",
               f"?offset=2000&limit=100"):
    try:
        r = requests.get(BASE + "/ws/games/roulette/history" + before, headers=hdrs(), timeout=15)
        recs = r.json() if r.status_code == 200 else []
        pl = [h for h in recs if h.get("participants", 0) > 0]
        ids = [h["id"] for h in recs]
        print(f"--- history {before[:34] or '(newest)'}: {len(recs)} recs, played={len(pl)}, "
              f"id-range {min(ids) if ids else '-'}..{max(ids) if ids else '-'}")
        played += pl
        if len(played) >= 10:
            break
    except Exception as e:
        print(f"--- {before}: ERR {str(e)[:80]}")
    time.sleep(7)

# 3) derivation test if we have played rounds
if played:
    for h in played[:12]:
        pred = int(hashlib.sha256(
            f"{cur['serverSeed']}:{cur['publicSeed']}:{h['id']}".encode()
        ).hexdigest()[:8], 16) % 15
        print("--- round", h["id"], "actual", h.get("ticket"), "pred-from-published", pred,
              "MATCH" if pred == h.get("ticket") else "no")
else:
    print("--- no played rounds found in walk-back window")
