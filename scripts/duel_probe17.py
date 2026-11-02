#!/usr/bin/env python3
"""probe17: app chunk SocketProvider + EIO=3 on /ws + bets feed under /ws base"""
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


r = g("app-DkAHa4SK.js")
t = r.text
print("=== app", r.status_code, len(t))
if r.status_code == 200:
    for pat, cap in ((r"getSocketNamespace", 4), (r"io\(", 6), (r"socket", 6)):
        ms = list(re.finditer(pat, t))
        print("--", pat, "hits:", len(ms))
        for m in ms[:cap]:
            s = max(0, m.start() - 200)
            print("   >>>", t[s:m.end() + 280].replace("\n", " ")[:540])
    refs = sorted(set(re.findall(r'["\'](?:\./)?assets/([A-Za-z0-9_.-]*[Ss]ocket[A-Za-z0-9_.-]*\.js)["\']', t)))
    print("-- socket-ish refs:", refs[:12])
time.sleep(8)


def hdrs(extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": BASE, "Referer": BASE + "/",
    }
    if extra:
        h.update(extra)
    return h


for q in ("EIO=3&transport=polling", "EIO=4&transport=polling&sid=x"):
    rr = requests.get(f"{BASE}/ws/socket.io/?{q}", headers=hdrs(), timeout=20)
    print(f"--- /ws handshake {q[:26]}: {rr.status_code} {rr.text[:200]}")
    time.sleep(8)

for ep in ("/ws/user/bets/live", "/ws/user/bets/my", "/ws/bets/live", "/ws/config"):
    rr = requests.get(BASE + ep, headers=hdrs({"Accept": "application/json, text/plain, */*"}),
                      timeout=20)
    print(f"--- GET {ep}: {rr.status_code} {rr.text[:240]}")
    time.sleep(8)
