#!/usr/bin/env python3
"""probe13: socket layer decode - token mint, namespaces, anon join paths (ws + gs)"""
import re
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

CHUNKS = ["socket-CvRziMuy.js", "useSocket-CpZUhESH.js", "getSocketNamespace-BUVBK2du.js",
          "balance.store-CcrjJ3vQ.js"]
PATS = [
    ("ws-urls", r"domain\.websocket|/ws|wss?:", 150, 240, 8),
    ("token", r"token", 120, 180, 8),
    ("namespace", r"namespace|nsp", 100, 160, 6),
    ("auth-opts", r"auth:|query:\{", 160, 260, 6),
    ("rooms", r"subscribe|room|join|emit\(`", 100, 180, 10),
]
for path in CHUNKS:
    r = requests.get(BASE + "/assets/" + path, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1", "Referer": BASE + "/",
        "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }, timeout=20)
    print("===", path, r.status_code, len(r.text))
    t = r.text
    if r.status_code == 200:
        for label, pat, b, a, cap in PATS:
            ms = list(re.finditer(pat, t))
            print("--", label, "hits:", len(ms))
            for m in ms[:cap]:
                s = max(0, m.start() - b)
                print("   >>>", t[s:m.end() + a].replace("\n", " ")[:460])
    time.sleep(8)
