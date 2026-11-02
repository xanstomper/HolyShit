#!/usr/bin/env python3
"""probe6: api layer + routes + recaptcha chunks -> exact /auth/web3 call site, body, headers"""
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


def show(t, tag, pats):
    for label, pat, b, a, cap in pats:
        for m in list(re.finditer(pat, t))[:cap]:
            s = max(0, m.start() - b)
            print("--", tag, label, ":", t[s:m.end() + a].replace("\n", " ")[:760])


API_PATS = [
    ("authweb3", r"auth/web3", 320, 460, 6),
    ("web3", r"web3", 160, 260, 8),
    ("signing", r"personal_sign|signMessage|utf8ToHex", 150, 180, 4),
    ("recaptcha", r"recaptcha|captcha", 120, 200, 4),
    ("headers", r"x-api|x-brand|x-client|headers:\{", 120, 220, 6),
]
ROUTE_PATS = [
    ("signin-routes", r"sign|login|auth|web3|wallet", 80, 160, 12),
]
for path, pats in [
    ("api-3bWgqh5p.js", API_PATS),
    ("routes-BIIJS3eO.js", ROUTE_PATS),
    ("route-DIkdoSms.js", ROUTE_PATS),
    ("route-DIvnAHzC.js", ROUTE_PATS),
    ("route-w48XLRpG.js", ROUTE_PATS),
    ("useRecaptcha-CQZPQ9TW.js", API_PATS[3:4]),
]:
    r = g(BASE + "/assets/" + path)
    time.sleep(9)
    print("===", path, r.status_code, len(r.text))
    if r.status_code == 200:
        show(r.text, path[:20], pats)
        refs = sorted(set(re.findall(r'["\'](?:\./)?assets/([A-Za-z0-9_.-]+\.js)["\']', r.text)))
        hits = [n for n in refs if re.search(r"login|sign|web3|wallet|auth", n, re.I)]
        if hits:
            print("--", path[:20], "refs:", hits[:16])
