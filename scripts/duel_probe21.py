#!/usr/bin/env python3
"""probe21: full API path-literal map from api layer + fairness verifier URL + mines strings"""
import re
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def g(path):
    return requests.get(BASE + "/assets/" + path, headers={
        "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
        "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }, timeout=20)


r = g("api-3bWgqh5p.js")
t = r.text
print("=== api", r.status_code, len(t))
paths = sorted(set(re.findall(r"`(/[a-zA-Z][a-zA-Z0-9/_.$${}\[\]-]{0,70})`", t)))
print("--- api path literals (%d):" % len(paths))
for p in paths:
    print("   ", p)
user_paths = [p for p in paths if "user" in p.lower() or "profile" in p.lower()
              or "bet" in p.lower() or "balance" in p.lower()]
print("--- user/bet/balance-related:", user_paths)
time.sleep(7)

r = g("fairness-BrSEdCht.js")
t = r.text
print("=== fairness", r.status_code, len(t))
fps = sorted(set(re.findall(r"`(/[a-zA-Z][a-zA-Z0-9/_.$${}\[\]-]{0,70})`", t)))
print("--- fairness paths:", fps[:20])
for m in list(re.finditer(r"fairness", t))[:6]:
    s = max(0, m.start() - 100)
    print("   >>>", t[s:m.end() + 160].replace("\n", " ")[:280])
time.sleep(7)

r = g("mines-JMeX4n0d.js")
t = r.text
print("=== mines strings:", sorted(set(re.findall(r"`([a-z][a-zA-Z_/-]{2,40})`", t)))[:40])
