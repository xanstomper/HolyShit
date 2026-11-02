#!/usr/bin/env python3
"""probe3: dump auth.store + APIConfig whole; mine index for route chunks + /auth strings"""
import re
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def g(url):
    return requests.get(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1", "Referer": BASE + "/",
        "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }, timeout=20)


def whole(label, path):
    r = g(BASE + path)
    print("===", label, r.status_code, len(r.text))
    print(r.text)
    time.sleep(9)
    return r.text


store = whole("auth.store", "/assets/auth.store-Bx48JkQE.js")
time.sleep(4)
apicfg = whole("APIConfig", "/assets/APIConfig-D3zTv-cI.js")
time.sleep(4)

r = g(BASE + "/assets/index-CW30_Dqt.js")
idx = r.text
print("=== index", r.status_code, len(idx))
print("-- auth refs (ci):")
for m in re.finditer(r'.{60}/auth.{120}', idx)  :
    print("   ", m.group(0).replace("\n", " ")[:200])
    if m.start() > len(idx):
        break
refs = sorted(set(re.findall(r'["\'](?:\./)?assets/([A-Za-z0-9_.-]+\.js)["\']', idx)))
print("-- index chunk-name count:", len(refs))
hits = [n for n in refs if re.search(r'auth|sign|web3|login|register|wallet', n, re.I)]
print("-- interesting names:", hits[:40])
# lazy import manifest style
print("-- mapDeps-style:", re.findall(r'__vite__mapDeps|mapDeps|imports:\[', idx)[:3])
