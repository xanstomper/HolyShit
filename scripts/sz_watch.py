#!/usr/bin/env python3
"""Safe Zone 24/7 watcher: logs GPS fixes, devices, items; alerts on
eliminations / projectiles / nukes / EMP / proximity. Read-only feed."""
import socket, ssl, base64, os, json, struct, time, sys, datetime

HOST, PATH = "event-public.iceposeidon.com", "/public-map-ws"
LOG = os.path.expanduser("~/holyshit-mode/logs/sz_watch.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)

def log(msg, alert=False):
    line = f"{datetime.datetime.now(datetime.UTC).isoformat()} {'[ALERT]' if alert else ''} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def connect():
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f"GET {PATH} HTTP/1.1\r\nHost: {HOST}\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
           f"Sec-WebSocket-Version: 13\r\nOrigin: https://iceposeidon.com\r\n\r\n")
    ss = ssl.create_default_context().wrap_socket(
        socket.create_connection((HOST, 443), timeout=15), server_hostname=HOST)
    ss.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += ss.recv(4096)
    ss.settimeout(90)
    return ss

def rf(ss):
    h = b""
    while len(h) < 2:
        c = ss.recv(1)
        if not c:
            return None
        h += c
    op = h[0] & 0xF
    ln = h[1] & 0x7F
    if ln == 126:
        ln = struct.unpack(">H", ss.recv(2))[0]
    elif ln == 127:
        ln = struct.unpack(">Q", ss.recv(8))[0]
    data = b""
    while len(data) < ln:
        c = ss.recv(min(65536, ln - len(data)))
        if not c:
            return None
        data += c
    return op, data

alive_prev = set()
log("watcher started")
while True:
    try:
        ss = connect()
    except Exception as e:
        log(f"connect failed: {e}; retry in 15s")
        time.sleep(15)
        continue
    try:
        while True:
            f = rf(ss)
            if not f:
                break
            op, data = f
            if op == 1:
                try:
                    j = json.loads(data)
                except Exception:
                    continue
                t = j.get("type")
                if t == "contestants":
                    alive_now = {c["name"] for c in j["data"]["roster"]["contestants"]
                                 if not c["eliminated_at"]}
                    for gone in alive_prev - alive_now:
                        log(f"ELIMINATED: {gone}", alert=True)
                    if alive_prev and alive_now - alive_prev:
                        log(f"revived/joined: {alive_now - alive_prev}", alert=True)
                    alive_prev = alive_now
                elif t == "tracked_devices":
                    for d in j["data"]:
                        log(f"DEV {d.get('name')}: {d['lat']:.6f},{d['lng']:.6f} "
                            f"acc={d['accuracy_m']:.1f}m hdg={d['heading_deg']}")
                elif t in ("game_items", "game_items_patch"):
                    dd = j["data"]
                    lst = dd.get("items") or dd.get("added") or dd.get("upserted") or []
                    for it in lst:
                        kinds = [c.get("item", {}).get("type") for c in (it.get("contents") or [])]
                        if it.get("mine") or any(k in ("c4", "nuke") for k in kinds):
                            log(f"HAZARD {it.get('kind')} @{it.get('lat')},{it.get('lng')} "
                                f"contents={kinds}", alert=True)
            elif op == 2:
                k = data[0]
                if k in (4, 8):  # projectiles / zombie-leech streams
                    cnt = struct.unpack("<H", data[32:34])[0]
                    log(f"BIN kind{k} frame: {cnt} records ({len(data)}B)", alert=(k == 4 and cnt))
    except Exception as e:
        log(f"stream error: {e}; reconnect in 5s")
        time.sleep(5)
