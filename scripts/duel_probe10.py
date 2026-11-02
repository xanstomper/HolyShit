#!/usr/bin/env python3
"""probe10: fleet discriminators - .net liveness, switchflips auth surface, geo-override state param"""
import json
import re
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def hdrs(base, extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": base, "Referer": base + "/",
    }
    if extra:
        h.update(extra)
    return h


def fresh():
    import secrets
    return "0x" + secrets.token_hex(20)


def p(label, method, url, base, body=None, extra=None):
    try:
        r = requests.request(method, url, headers=hdrs(base, extra), data=body, timeout=20)
        print(f"--- {label}: {r.status_code} {r.text[:200]}")
        return r
    except Exception as e:
        print(f"--- {label}: ERR {str(e)[:120]}")
        return None


p("duelbits.net root", "GET", "https://duelbits.net/", "https://duelbits.net",
  extra={"Accept": "text/html,*/*", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
         "Sec-Fetch-Site": "none"})
time.sleep(9)
p("switchflips root", "GET", "https://switchflips.com/", "https://switchflips.com",
  extra={"Accept": "text/html,*/*", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
         "Sec-Fetch-Site": "none"})
time.sleep(9)
p("switchflips web3 message", "POST",
  "https://switchflips.com/auth/web3/message/?publicAddress=" + fresh(),
  "https://switchflips.com")
time.sleep(9)

# geo-override attempt on duelbits.com: their SPA reads ?ip=XX from the URL (api chunk Nr())
from eth_account import Account
from eth_account.messages import encode_defunct
b = Account.create()
addr = b.address.lower()
r = requests.post("https://duelbits.com/auth/web3/message/?publicAddress=" + addr,
                  headers=hdrs("https://duelbits.com"), timeout=20)
msg = r.json().get("message", "")
print("--- geo-probe challenge:", r.status_code, msg[:120])
time.sleep(9)
sig = Account.sign_message(encode_defunct(hexstr=msg.encode("utf-8").hex()), b.key).signature.hex()
if not sig.startswith("0x"):
    sig = "0x" + sig
body = json.dumps({"address": addr, "signature": sig, "ip": "DE", "country": "DE"})
p("geo-override auth", "POST",
  "https://duelbits.com/auth/web3?ip=DE&country=DE",
  "https://duelbits.com", body=body,
  extra={"Content-Type": "application/json"})
