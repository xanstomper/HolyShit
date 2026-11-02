#!/usr/bin/env python3
"""probe4: crawl chunk graph from NotAuthenticated -> login chunks -> exact auth/web3 call site"""
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


def show(t, tag):
    pats = [
        ("authweb3", r"auth/web3", 260, 420, 4),
        ("web3word", r"web3", 120, 200, 6),
        ("signing", r"personal_sign|signMessage|utf8ToHex|getRandomValues", 130, 170, 4),
        ("nonce", r"nonce", 100, 140, 3),
    ]
    for label, pat, b, a, cap in pats:
        for m in list(re.finditer(pat, t))[:cap]:
            s = max(0, m.start() - b)
            print("--", tag, label, ":", t[s:m.end() + a].replace("\n", " ")[:700])


def chunk_refs(t):
    return sorted(set(re.findall(r'["\'](?:\./)?assets/([A-Za-z0-9_.-]+\.js)["\']', t)))


def fetch(path):
    r = g(BASE + "/assets/" + path)
    time.sleep(9)
    print("===", path, r.status_code, len(r.text))
    return r.text if r.status_code == 200 else ""


wave1 = ["NotAuthenticated-L2RxvSOx.js"]
code = ""
for p in wave1:
    t = fetch(p)
    code += t
    show(t, p[:24])

# wave2: login-ish chunks referenced by wave1 + index
refs = chunk_refs(code)
loginish = [n for n in refs if re.search(r"login|sign|web3|wallet|auth(?!\.store)|connect", n, re.I)]
print("-- wave2 candidates:", loginish[:20])
code2 = ""
for n in loginish[:4]:
    t = fetch(n)
    code2 += t
    show(t, n[:24])

# wave3: any deeper auth chunk named from wave2
refs2 = chunk_refs(code2)
deep = [n for n in refs2 if re.search(r"login|sign-in|web3|wallet", n, re.I)]
print("-- wave3 candidates:", deep[:20])
for n in deep[:4]:
    t = fetch(n)
    show(t, n[:24])
