#!/usr/bin/env python3
"""probe16: io() token attachment grep + engine.io polling handshake (ws/gs, with/without token) + bets feed unauth"""
import re
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def g(path):
    return requests.get(BASE + "/assets/" + path, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1", "Referer": BASE + "/",
        "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }, timeout=20)


r = g("index-CW30_Dqt.js")
idx = r.text
print("=== index", r.status_code, len(idx))
for pat in (r"token.{0,140}io\(", r"io\(.{0,140}token", r"token=`|token=\$\{|\?token=",
            r"query:\{token|auth:\{token"):
    ms = list(re.finditer(pat, idx))
    print("-- pattern", pat, "hits:", len(ms))
    for m in ms[:4]:
        s = max(0, m.start() - 220)
        print("   >>>", idx[s:m.end() + 240].replace("\n", " ")[:520])
time.sleep(8)


def hdrs(extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": BASE, "Referer": BASE + "/",
    }
    if extra:
        h.update(extra)
    return h


for nsp in ("ws", "gs"):
    for label, q in [("no-token", "EIO=4&transport=polling"),
                     ("with-token", "EIO=4&transport=polling&token=AAAA")]:
        rr = requests.get(f"{BASE}/{nsp}/socket.io/?{q}", headers=hdrs(), timeout=20)
        print(f"--- {nsp} handshake {label}: {rr.status_code} {rr.text[:220]}")
        time.sleep(8)

for ep in ("/auth/user/bets/live", "/auth/user/bets/my", "/auth/user/bets/live?scope=ws"):
    rr = requests.get(BASE + ep, headers=hdrs({"Accept": "application/json, text/plain, */*"}),
                      timeout=20)
    print(f"--- GET {ep}: {rr.status_code} {rr.text[:220]}")
    time.sleep(8)
