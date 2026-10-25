#!/usr/bin/env python3
"""Safe Zone live unauthenticated surveillance tracker.
Usage: python3 sz_tracker.py [seconds]
Streams wss://event-public.iceposeidon.com/public-map-ws (no auth):
- contestant GPS fixes (binary kind 1: 36B hdr, i16 lat/lng deltas @1e5)
- tracked devices (Nate) JSON with accuracy_m + heading
- alive roster + eliminations
Prints live table. ctrl-c to stop."""
import socket, ssl, base64, os, json, struct, time, sys

HOST = "event-public.iceposeidon.com"
PATH = "/public-map-ws"
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 60

key = base64.b64encode(os.urandom(16)).decode()
req = (f"GET {PATH} HTTP/1.1\r\nHost: {HOST}\r\nUpgrade: websocket\r\n"
       f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
       f"Sec-WebSocket-Version: 13\r\nOrigin: https://iceposeidon.com\r\n\r\n")
ss = ssl.create_default_context().wrap_socket(
    socket.create_connection((HOST, 443), timeout=10), server_hostname=HOST)
ss.sendall(req.encode())
resp = b""
while b"\r\n\r\n" not in resp:
    resp += ss.recv(4096)
ss.settimeout(DUR + 10)

def rf():
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

roster, fixes, nate = {}, {}, []
t0 = time.time()
while time.time() - t0 < DUR:
    try:
        f = rf()
    except Exception:
        break
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
            for c in j["data"]["roster"]["contestants"]:
                roster[c["name"]] = not c["eliminated_at"]
        elif t == "tracked_devices":
            for d in j["data"]:
                nate.append((d["lat"], d["lng"], d["accuracy_m"], d["heading_deg"]))
                print(f"[DEV] {d.get('name')}: {d['lat']:.6f},{d['lng']:.6f} "
                      f"acc={d['accuracy_m']:.1f}m hdg={d['heading_deg']}")
    elif op == 2 and data[0] == 1:
        cnt = struct.unpack("<H", data[32:34])[0]
        if cnt and len(data) >= 56:
            latB = struct.unpack("<i", data[48:52])[0]
            lngB = struct.unpack("<i", data[52:56])[0]
            for j in range(cnt):
                dlat = struct.unpack("<h", data[56 + j*2:58 + j*2])[0]
                dlng = struct.unpack("<h", data[56 + 2*cnt + j*2:56 + 2*cnt + j*2 + 2])[0]
                slot = struct.unpack("<H", data[56 + 4*cnt + j*2:56 + 4*cnt + j*2 + 2])[0]
                fixes.setdefault(slot, []).append(
                    ((latB + dlat) / 1e5, (lngB + dlng) / 1e5))

print("\n=== SUMMARY ===")
print("alive:", [n for n, a in roster.items() if a])
for s, v in sorted(fixes.items()):
    print(f"slot {s}: pings={len(v)} last={v[-1][0]:.6f},{v[-1][1]:.6f}")
if nate:
    print(f"nate: last={nate[-1][0]:.6f},{nate[-1][1]:.6f} acc={nate[-1][2]:.1f}m")
ss.close()
