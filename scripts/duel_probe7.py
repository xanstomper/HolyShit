#!/usr/bin/env python3
"""probe7: web3-sign-in chunk -> the EXACT message fetch, signing mode, POST body, state forwarding"""
import re
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

r = requests.get(BASE + "/assets/web3-sign-in-B-om7o8t.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-origin",
}, timeout=20)
t = r.text
print("=== web3-sign-in", r.status_code, len(t))
print("---- FULL DUMP (first 12000 chars) ----")
print(t[:12000])
print("---- auth/web3 contexts ----")
for m in list(re.finditer(r"auth/web3", t))[:8]:
    s = max(0, m.start() - 350)
    print(">>>", t[s:m.end() + 500].replace("\n", " ")[:900])
    print()
