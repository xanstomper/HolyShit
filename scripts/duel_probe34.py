#!/usr/bin/env python3
"""probe34: room-name templates from cached chunks + sweep artifacts + mystery hosts"""
import json
import os
import re

import requests

os.chdir("/dev/shm/.dkv")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

rooms = set()
joins = []
for fn in os.listdir("chunks"):
    try:
        t = open("chunks/" + fn).read()
    except Exception:
        continue
    for m in re.finditer(r"""[`"'](?:user|round|game|session|admin|mod|internal|chat|bets|feed|table|race|tournament)[:#][a-zA-Z$_{}`"'.-]{0,30}""", t):
        rooms.add(m.group(0)[:44])
    for m in re.finditer(r"\[`?join`?,", t):
        s = max(0, m.start() - 80)
        joins.append((fn, t[s:m.end() + 140].replace("\n", " ")[:220]))
print("room templates:", sorted(rooms)[:30])
print("join payloads:", len(joins))
for fn, j in joins[:10]:
    print("--", fn[:24], "|", j)

for f in ("endpoint_probe.json", "burst.json"):
    if os.path.exists(f):
        d = json.load(open(f))
        print("==", f, "entries:", len(d))
        if f == "burst.json":
            print("   bursts:", d.get("token_mint_c"), d.get("bets_live_c"))
        else:
            opens = {k: v for k, v in d.items() if v == 200}
            print("   200s:", list(opens.items())[:20])
            g403 = [k for k, v in d.items() if v == 403]
            print("   403 (exists,gated):", g403[:24])
    else:
        print("==", f, "PENDING")

for h in ("c.duelbits.com", "31212980.duelbits.com"):
    try:
        r = requests.get("https://" + h + "/", headers={"User-Agent": UA}, timeout=12)
        print("==", h, r.status_code, len(r.text), r.text[:120].replace("\n", " "))
    except Exception as e:
        print("==", h, "ERR", str(e)[:80])
