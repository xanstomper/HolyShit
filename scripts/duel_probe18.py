#!/usr/bin/env python3
"""probe18: full bets-live structure + gs socket connect/listen + find socket provider chunk"""
import json
import re
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


r = requests.get(BASE + "/ws/user/bets/live", headers=hdrs(), timeout=20)
print("--- bets/live:", r.status_code, "bytes", len(r.text))
try:
    j = r.json()
    open("/dev/shm/.dkv/bets_live.json", "w").write(json.dumps(j))
    recs = j.get("all", [])
    print("--- record count:", len(recs))
    if recs:
        fields = sorted({k for rec in recs for k in rec.keys()})
        ufields = sorted({k for rec in recs for k in (rec.get("user") or {}).keys()})
        games = sorted({rec.get("game") for rec in recs})
        print("--- fields:", fields)
        print("--- user fields:", ufields)
        print("--- games:", games[:20])
        import datetime
        ts = [rec.get("timestamp", 0) for rec in recs]
        print("--- timestamp span (s):", (max(ts) - min(ts)) / 1000 if ts else 0)
        u0 = recs[0].get("user") or {}
        print("--- sample user (redacted):", {k: (str(v)[:6] + "..." if isinstance(v, str) and len(str(v)) > 12 else v)
                                              for k, v in u0.items()})
except Exception as e:
    print("--- parse err:", str(e)[:120], r.text[:200])
time.sleep(8)

# gs socket: connect namespace + listen
sid_r = requests.get(BASE + "/gs/socket.io/?EIO=4&transport=polling", headers=hdrs(), timeout=20)
sid = json.loads(sid_r.text[1:]).get("sid")
print("--- gs sid:", sid)
pr = requests.post(f"{BASE}/gs/socket.io/?EIO=4&transport=polling&sid={sid}",
                   headers=hdrs({"Content-Type": "text/plain;charset=UTF-8"}),
                   data="40", timeout=20)
print("--- gs connect(40):", pr.status_code, pr.text[:120])
for i in range(3):
    time.sleep(1.5)
    gr = requests.get(f"{BASE}/gs/socket.io/?EIO=4&transport=polling&sid={sid}",
                      headers=hdrs(), timeout=20)
    print(f"--- gs poll{i}:", gr.status_code, gr.text[:400])

# find the socket provider chunk (token attachment)
idx = requests.get(BASE + "/assets/index-CW30_Dqt.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Site": "same-origin",
}, timeout=25).text
ms = [m for m in re.finditer(r"getSocketNamespace|getSocket", idx)]
print("--- index getSocket hits:", len(ms))
for m in ms[:4]:
    s = max(0, m.start() - 260)
    print("   >>>", idx[s:m.end() + 300].replace("\n", " ")[:600])
