#!/usr/bin/env python3
"""probe5: (a) all 416 chunk names from index (b) /auth/web3 validation-probe empty/minimal bodies"""
import json
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


r = g(BASE + "/assets/index-CW30_Dqt.js")
idx = r.text
print("=== index", r.status_code, len(idx))
refs = sorted(set(re.findall(r'["\'](?:\./)?assets/([A-Za-z0-9_.-]+\.js)["\']', idx)))
print("-- ALL chunk names (%d):" % len(refs))
print(", ".join(refs))
time.sleep(10)

for body in ({}, {"address": "0xabc"}):
    rr = requests.post(BASE + "/auth/web3", headers={
        "User-Agent": UA, "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "Origin": BASE, "Referer": BASE + "/",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin",
    }, data=json.dumps(body), timeout=20)
    print("=== POST /auth/web3", json.dumps(body), rr.status_code, rr.text[:400])
    time.sleep(10)
