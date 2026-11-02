#!/usr/bin/env python3
"""probe15: decode anon token claims + dump useSocket (token attachment) + engine.io handshake test"""
import base64
import json
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


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


def b64d(s):
    s += "=" * (-len(s) % 4)
    return json.loads(base64.urlsafe_b64decode(s))


r = requests.post(BASE + "/auth/token?scope=ws", headers=hdrs(), timeout=20)
tok = r.json().get("token", "")
print("--- mint scope=ws:", r.status_code, "token len", len(tok), "tail", tok[-4:])
print("--- header:", b64d(tok.split(".")[0]))
claims = b64d(tok.split(".")[1])
print("--- claims:", json.dumps(claims))
print("--- exp-iat:", claims.get("exp", 0) - claims.get("iat", 0), "s")
time.sleep(8)
# does scope land in the token?
r2 = requests.post(BASE + "/auth/token?scope=chat", headers=hdrs(), timeout=20)
tok2 = r2.json().get("token", "")
print("--- mint scope=chat claims:", json.dumps(b64d(tok2.split(".")[1])))
time.sleep(8)
r3 = requests.post(BASE + "/auth/token", headers=hdrs(), timeout=20)
tok3 = r3.json().get("token", "")
print("--- mint no-scope claims:", json.dumps(b64d(tok3.split(".")[1])))

r = requests.get(BASE + "/assets/useSocket-CpZUhESH.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Site": "same-origin",
}, timeout=20)
print("=== useSocket", r.status_code)
print(r.text)
