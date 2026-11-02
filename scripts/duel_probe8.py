#!/usr/bin/env python3
"""probe8: dump every .post/.get path literal from api + routes + web3-sign-in chunks; find web3/ paths"""
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
    }, timeout=25)


def show(t, tag, pats):
    for label, pat, b, a, cap in pats:
        ms = list(re.finditer(pat, t))
        print("--", tag, label, "hits:", len(ms))
        for m in ms[:cap]:
            s = max(0, m.start() - b)
            print("   >>>", t[s:m.end() + a].replace("\n", " ")[:700])


PATS = [
    ("web3slash", r"web3/", 200, 400, 8),
    ("post-calls", r"\.post\(`[^`]{0,80}`", 120, 260, 20),
    ("get-calls", r"\.get\(`[^`]{0,80}`", 60, 160, 12),
    ("message-ep", r"web3/message|/message\?|\?publicAddress", 200, 300, 6),
]
code = ""
for path in ["api-3bWgqh5p.js", "routes-BIIJS3eO.js", "web3-sign-in-B-om7o8t.js"]:
    r = g(path)
    time.sleep(9)
    print("===", path, r.status_code, len(r.text))
    if r.status_code == 200:
        code += r.text
        show(r.text, path[:16], PATS)
# web3/message anywhere in the combined code
print("--- combined web3/message hits ---")
for m in list(re.finditer(r"web3/message|\?publicAddress", code))[:6]:
    s = max(0, m.start() - 300)
    print(">>>", code[s:m.end() + 400].replace("\n", " ")[:760])
