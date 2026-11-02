#!/usr/bin/env python3
"""probe26: crash full history fields (hash chain?) + fairness crash docs + roulette re-poll"""
import re
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


r = requests.get(BASE + "/ws/games/crash/history", headers=hdrs(), timeout=20)
print("--- crash/history:", r.status_code, "bytes", len(r.text))
try:
    j = r.json()
    recs = j.get("history", [])
    print("--- count:", len(recs), "keys:", sorted({k for x in recs for k in x.keys()}))
    for x in recs[:3]:
        print("--- rec:", json.dumps(x))
except Exception as e:
    print("--- err", str(e)[:120], r.text[:200])
time.sleep(8)

r = requests.get(BASE + "/ws/games/crash/state", headers=hdrs(), timeout=20)
print("--- crash/state:", r.status_code)
try:
    print(json.dumps(r.json())[:800])
except Exception:
    print(r.text[:400])
time.sleep(8)

r = requests.get(BASE + "/assets/fairness-BrSEdCht.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Site": "same-origin",
}, timeout=20)
t = r.text
print("=== fairness crash refs:")
for m in list(re.finditer(r"[Cc]rash", t))[:6]:
    s = max(0, m.start() - 160)
    print("   >>>", t[s:m.end() + 240].replace("\n", " ")[:420])
ms = list(re.finditer(r"hashChain|chain|previous", t))
print("--- chain refs:", len(ms))
for m in ms[:3]:
    s = max(0, m.start() - 140)
    print("   >>>", t[s:m.end() + 240].replace("\n", " ")[:420])
time.sleep(8)

for i in range(2):
    r = requests.get(BASE + "/ws/games/roulette/history?limit=100", headers=hdrs(), timeout=20)
    recs = r.json()
    played = [h for h in recs if h.get("participants", 0) > 0]
    print(f"--- roulette poll{i}: played={len(played)}", 
          json.dumps(played[:3]))
    if played:
        break
    time.sleep(60)
