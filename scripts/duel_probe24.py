#!/usr/bin/env python3
"""probe24: find observed-round source - /ws/games/* path sweep + full roulette/crash records from bets/live"""
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


for game in ("roulette", "crash"):
    for sub in ("rounds", "history", "results", "live", "current", "state"):
        try:
            r = requests.get(f"{BASE}/ws/games/{game}/{sub}", headers=hdrs(), timeout=15)
            tag = "JSON" if r.text[:1] in ("{", "[") else "other"
            print(f"--- /ws/games/{game}/{sub}: {r.status_code} [{tag}] {r.text[:150]}")
        except Exception as e:
            print(f"--- /ws/games/{game}/{sub}: ERR {str(e)[:80]}")
        time.sleep(7)

r = requests.get(BASE + "/ws/user/bets/live", headers=hdrs(), timeout=20)
try:
    recs = r.json().get("all", [])
    rou = [x for x in recs if "roulette" in str(x.get("game", ""))]
    cra = [x for x in recs if str(x.get("game", "")) == "crash"]
    print("--- roulette records in live feed:", len(rou))
    for x in rou[:3]:
        print("--- ROU:", json.dumps(x))
    print("--- crash records:", len(cra))
    for x in cra[:2]:
        print("--- CRA:", json.dumps(x))
except Exception as e:
    print("--- err", str(e)[:120])
