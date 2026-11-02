#!/usr/bin/env python3
"""probe14: dump socket chunks whole + live-probe /auth/token scope mint unauth"""
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


for path in ("getSocketNamespace-BUVBK2du.js", "socket-CvRziMuy.js"):
    r = g(path)
    print("===", path, r.status_code)
    print(r.text)
    time.sleep(8)

r = g("index-CW30_Dqt.js")
idx = r.text
print("=== index scope hits:")
for m in list(re.finditer(r"scope", idx))[:12]:
    s = max(0, m.start() - 130)
    print("   >>>", idx[s:m.end() + 160].replace("\n", " ")[:300])
time.sleep(8)


def hdrs(extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": BASE, "Referer": BASE + "/",
    }
    if extra:
        h.update(extra)
    return h


for scope in ("", "chat", "bets", "ws", "gs", "public", "casino", "feed"):
    url = BASE + "/auth/token" + (f"?scope={scope}" if scope else "")
    rr = requests.post(url, headers=hdrs(), timeout=20)
    body = rr.text[:180]
    print(f"--- POST /auth/token?scope={scope or '(none)'}: {rr.status_code} {body}")
    time.sleep(8)
