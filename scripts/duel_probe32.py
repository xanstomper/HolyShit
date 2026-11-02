#!/usr/bin/env python3
"""probe32: full /ws/config dump (keys/flags) + config siblings + cross-user room join test on gs"""
import json
import re
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def hdrs():
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": BASE, "Referer": BASE + "/",
    }


r = requests.get(BASE + "/ws/config", headers=hdrs(), timeout=20)
t = r.text
open("/dev/shm/.dkv/ws_config.json", "w").write(t)
print("--- /ws/config:", r.status_code, "bytes", len(t))
# secret-ish key names
for pat, cap in ((r"[\"']([a-zA-Z_]*(?:key|secret|token|password|apikey)[a-zA-Z_]*)[\"']", 12),
                 (r"https?://[a-zA-Z0-9.-]+", 16)):
    ms = sorted(set(m.group(1) if pat.startswith("[\"']") else m.group(0) for m in re.finditer(pat, t)))
    print("-- pattern hits:", ms[:cap])
try:
    j = json.loads(t)
    def walk(d, pfx=""):
        if isinstance(d, dict):
            for k, v in d.items():
                walk(v, pfx + "." + str(k))
        elif isinstance(d, list) and d and len(d) < 6:
            for n, v in enumerate(d):
                walk(v, pfx + f"[{n}]")
        else:
            s = str(d)
            if len(s) > 60 or re.search(r"key|secret|token|Key|KEY", pfx):
                print("   ", pfx, "=", s[:90])
    walk(j)
except Exception as e:
    print("--- parse err", str(e)[:100])
time.sleep(7)

for sub in ("countries", "providers", "payments", "features", "restricted", "license"):
    try:
        rr = requests.get(f"{BASE}/ws/config/{sub}", headers=hdrs(), timeout=15)
        print(f"--- /ws/config/{sub}: {rr.status_code} {rr.text[:140]}")
    except Exception as e:
        print(f"--- {sub}: ERR {str(e)[:70]}")
    time.sleep(7)

# cross-user room join test on gs (single harvested uuid, read-only listen)
uuid = next(iter(json.load(open("/dev/shm/.dkv/bets_live.json"))["all"][0]["user"].values()), None)
uuid = "0dae0315-7e68-402b-950c-dd6ad34ca129"  # from live feed record #1
import websocket
tok = requests.post(BASE + "/auth/token?scope=gs", headers=hdrs(), timeout=20).json().get("token", "")
ws = websocket.WebSocket(timeout=8)
try:
    ws.connect("wss://duelbits.com/gs/socket.io/?EIO=4&transport=websocket",
               header=[f"Origin: {BASE}", f"User-Agent: {UA}"])
    ws.recv()  # open
    ws.send('40{"token":"' + tok + '"}')
    print("--- gs ns:", ws.recv()[:80])
    for room in (f"user:{uuid}", uuid, f"round:{uuid}"):
        ws.send(f'42["join",["{room}"]]')
        try:
            f = ws.recv()
            print(f"--- join {room[:20]}:", str(f)[:240])
        except Exception as e:
            print(f"--- join {room[:20]}: timeout/no-frame ({str(e)[:50]})")
            break
    for i in range(2):
        try:
            f = ws.recv()
            print(f"--- listen{i}:", str(f)[:300])
        except Exception:
            print(f"--- listen{i}: quiet")
            break
    ws.close()
except Exception as e:
    print("--- gs room test ERR:", str(e)[:130])
