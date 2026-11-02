#!/usr/bin/env python3
"""probe29: keno/moonshot/hilo/duelpoker seeds+state+history + fairness snippet dump"""
import json
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


for game in ("keno", "moonshot", "hilo", "duelpoker"):
    for sub in ("seeds", "state", "history"):
        try:
            r = requests.get(f"{BASE}/ws/games/{game}/{sub}", headers=hdrs(), timeout=15)
            body = r.text[:220]
            print(f"--- /ws/games/{game}/{sub}: {r.status_code} {body}")
            if r.status_code == 200 and sub in ("seeds", "history"):
                open(f"/dev/shm/.dkv/{game}_{sub}.json", "w").write(r.text)
        except Exception as e:
            print(f"--- {game}/{sub}: ERR {str(e)[:80]}")
        time.sleep(7)

r = requests.get(BASE + "/assets/fairness-BrSEdCht.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Site": "same-origin",
}, timeout=20)
t = r.text
open("/dev/shm/.dkv/fairness.js", "w").write(t)
print("=== fairness snippet strings:")
for m in re.finditer(r"`const [^`]{60,900}`", t):
    s = m.group(0).strip("`")
    print("----")
    print(s[:700])
