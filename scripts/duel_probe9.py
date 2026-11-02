#!/usr/bin/env python3
"""probe9: full signIn() body + Xb state transform + final /auth/web3 POST construction"""
import re

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

r = requests.get(BASE + "/assets/web3-sign-in-B-om7o8t.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-origin",
}, timeout=25)
t = r.text
print("=== web3-sign-in", r.status_code, len(t))
for m in list(re.finditer(r"async signIn", t))[:2]:
    print("---- signIn() full ----")
    print(t[m.start():m.start() + 1700].replace("\n", " "))
for pat in (r"Xb=", r"function Xb", r"Xb\s*=\s*\("):
    m = re.search(pat, t)
    if m:
        print("---- Xb def ----")
        print(t[max(0, m.start() - 100):m.start() + 900].replace("\n", " "))
        break
for m in list(re.finditer(r"domain\.auth", t))[:4]:
    print("---- domain.auth ctx ----")
    print(t[max(0, m.start() - 350):m.end() + 350].replace("\n", " "))
