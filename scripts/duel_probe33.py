#!/usr/bin/env python3
"""probe33: gs room-join test via polling frames - public crash room (sanity) then cross-user room (decisive)"""
import json
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


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


tok = requests.post(BASE + "/auth/token?scope=gs", headers=hdrs(), timeout=20).json().get("token", "")
sid = json.loads(requests.get(f"{BASE}/gs/socket.io/?EIO=4&transport=polling",
                              headers=hdrs(), timeout=15).text[1:])["sid"]
pr = requests.post(f"{BASE}/gs/socket.io/?EIO=4&transport=polling&sid={sid}",
                   headers=hdrs({"Content-Type": "text/plain;charset=UTF-8"}),
                   data='40{"token":"' + tok + '"}', timeout=15)
print("--- ns connect:", pr.status_code, pr.text[:80])
time.sleep(1)

# public crash round (sanity check that joins work at all)
cs = requests.get(BASE + "/ws/games/crash/state", headers=hdrs(), timeout=15).json()
round_id = cs.get("id")
print("--- crash round:", round_id)


def emit_join(room):
    p = requests.post(f"{BASE}/gs/socket.io/?EIO=4&transport=polling&sid={sid}",
                      headers=hdrs({"Content-Type": "text/plain;charset=UTF-8"}),
                      data='42["join",["' + room + '"]]', timeout=15)
    print(f"--- join {room[:28]}: POST {p.status_code} {p.text[:60]}")
    for i in range(2):
        time.sleep(1.5)
        try:
            g = requests.get(f"{BASE}/gs/socket.io/?EIO=4&transport=polling&sid={sid}",
                             headers=hdrs(), timeout=6)
            print(f"    poll{i}: {g.status_code} {g.text[:260]}")
            if g.status_code != 200:
                break
        except requests.exceptions.ReadTimeout:
            print(f"    poll{i}: quiet")
            if i:
                break


emit_join("crash:" + round_id)
time.sleep(3)
uuid = "0dae0315-7e68-402b-950c-dd6ad34ca129"
emit_join("user:" + uuid)
time.sleep(3)
emit_join(uuid)
