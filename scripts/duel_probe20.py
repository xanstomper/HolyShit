#!/usr/bin/env python3
"""probe20: mine event vocabulary from fairness + gameplay + originals + bets chunks (no sockets)"""
import re
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

CHUNKS = ["fairness-BrSEdCht.js", "gameplay.store-DflfLauD.js",
          "mines-JMeX4n0d.js", "plinko-1j9_14l-.js", "originals-D9ydTVTC.js",
          "mybets-DzG7NxC9.js", "useGameSessionMode-DVOGFHE_.js"]
for path in CHUNKS:
    try:
        r = requests.get(BASE + "/assets/" + path, headers={
            "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
            "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
        }, timeout=20)
    except Exception as e:
        print("===", path, "ERR", str(e)[:100])
        continue
    t = r.text
    print("===", path, r.status_code, len(t))
    if r.status_code != 200:
        time.sleep(7)
        continue
    evs = sorted(set(re.findall(r"(?:emit|on)\(`([a-zA-Z_:-]+)`", t)))
    print("-- events:", evs[:24])
    for pat, cap in ((r"clientSeed|serverSeed|nonce", 4), (r"`join`|join\(", 3),
                     (r"sha256|hashChain|hexEncode", 2)):
        ms = list(re.finditer(pat, t))
        if ms:
            print("--", pat, "hits:", len(ms))
            for m in ms[:cap]:
                s = max(0, m.start() - 120)
                print("   >>>", t[s:m.end() + 220].replace("\n", " ")[:360])
    time.sleep(7)
