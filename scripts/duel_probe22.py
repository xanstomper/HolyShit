#!/usr/bin/env python3
"""probe22: roulette seeds endpoint + game history across bases (unauth)"""
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


for base in ("https://duelbits.com/ws", "https://duelbits.com/auth", "https://duelbits.com/gs"):
    for path in ("/games/roulette/seeds", "/original-game-history"):
        try:
            r = requests.get(base + path, headers=hdrs(), timeout=20)
            print(f"--- GET {base.split('//')[1]}{path}: {r.status_code} {r.text[:400]}")
        except Exception as e:
            print(f"--- GET {base}{path}: ERR {str(e)[:100]}")
        time.sleep(8)
