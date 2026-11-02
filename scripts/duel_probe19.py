#!/usr/bin/env python3
"""probe19: socket.io CONNECT with anon token on gs + ws; listen for pushes; mine event vocabulary"""
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


def mint(scope):
    r = requests.post(BASE + f"/auth/token?scope={scope}", headers=hdrs(), timeout=20)
    return r.json().get("token", "")


def socket_session(nsp, scope):
    tok = mint(scope)
    print(f"--- [{nsp}] token minted len={len(tok)} tail={tok[-4:]}")
    sid = json.loads(requests.get(
        f"{BASE}/{nsp}/socket.io/?EIO=4&transport=polling",
        headers=hdrs(), timeout=20).text[1:])["sid"]
    print(f"--- [{nsp}] sid={sid}")
    pr = requests.post(f"{BASE}/{nsp}/socket.io/?EIO=4&transport=polling&sid={sid}",
                       headers=hdrs({"Content-Type": "text/plain;charset=UTF-8"}),
                       data='40{"token":"' + tok + '"}', timeout=20)
    print(f"--- [{nsp}] connect+token:", pr.status_code, pr.text[:160])
    packets = []
    for i in range(4):
        time.sleep(1.2)
        gr = requests.get(f"{BASE}/{nsp}/socket.io/?EIO=4&transport=polling&sid={sid}",
                          headers=hdrs(), timeout=20)
        body = gr.text[:500]
        packets.append(body)
        print(f"--- [{nsp}] poll{i}:", gr.status_code, body)
        if gr.status_code != 200:
            break
    return packets


socket_session("gs", "gs")
time.sleep(6)
socket_session("ws", "ws")

# event vocabulary from gameplay/fairness chunks
for path in ("fairness-BrSEdCht.js", "gameplay.store-DflfLauD.js",
             "sessionConfirmation.store-CiyWEZbi.js"):
    r = requests.get(BASE + "/assets/" + path, headers={
        "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
        "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }, timeout=20)
    t = r.text
    print("===", path, r.status_code, len(t))
    if r.status_code == 200:
        for pat, cap in ((r"emit\(`[a-zA-Z_]+`", 10), (r"\.on\(`[a-zA-Z_]+`", 10),
                         (r"clientSeed|serverSeed|nonce|hash", 6)):
            ms = list(re.finditer(pat, t))
            vals = sorted({m.group(0) for m in ms})
            print("--", pat, "unique:", vals[:14])
            for m in ms[:2]:
                s = max(0, m.start() - 140)
                print("   >>>", t[s:m.end() + 200].replace("\n", " ")[:360])
    time.sleep(7)
