# WebSocket Auth Testing on Cloudflare-Fronted Origins

A class-level technique for testing WebSocket endpoints behind a CDN/WAF. The naive
"does the 101 upgrade require auth?" check gives a false negative — Cloudflare proxies
the protocol upgrade without seeing application frames.

## The Trap

```bash
curl -i -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
     -H "Sec-WebSocket-Version: 13" \
     https://target/api/voice/socket
```

You get `HTTP/1.1 101 Switching Protocols` and think "no auth required!" That conclusion
is wrong. The 101 is the CDN/proxy doing its job. The origin server has not yet seen
ANY application data.

## The Correct Test

Exchange actual WebSocket frames. Use Python `socket+ssl` (NOT `websockets` library —
the library often auto-handshakes and masks the raw protocol behavior you need to see).
After the 101, send a frame and observe the response:

```python
import socket, ssl, base64, os, struct

def make_frame(payload, opcode=0x1):
    b1 = 0x80 | opcode
    length = len(payload)
    header = struct.pack('!BB', b1, length | 0x80)  # client frames MUST be masked
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return header + mask + masked

def ws_connect(host, port, path, extra_headers=None):
    key = base64.b64encode(os.urandom(16)).decode()
    headers = {
        'Host': host, 'Upgrade': 'websocket', 'Connection': 'Upgrade',
        'Sec-WebSocket-Key': key, 'Sec-WebSocket-Version': '13',
        'Origin': 'https://target',
    }
    if extra_headers: headers.update(extra_headers)
    req = f'GET {path} HTTP/1.1\r\n'
    for k, v in headers.items(): req += f'{k}: {v}\r\n'
    req += '\r\n'
    ctx = ssl.create_default_context()
    s = socket.create_connection((host, port), timeout=10)
    s = ctx.wrap_socket(s, server_hostname=host)
    s.sendall(req.encode())
    buf = b''
    while b'\r\n\r\n' not in buf:
        chunk = s.recv(4096)
        if not chunk: break
        buf += chunk
    return s

# After handshake, send frames and read responses
s = ws_connect('target.com', 443, '/api/socket')
s.sendall(make_frame(b'{"type":"hello"}'))  # or any probe message
s.settimeout(2)
data = s.recv(8192)
# Parse first byte: 0x88 = CLOSE frame, 0x81 = TEXT frame
if data and data[0] == 0x88:
    close_code = struct.unpack('!H', data[2:4])[0]
    print(f'Server closed: code={close_code}')
    # 1008 = Policy Violation (auth failed), 1000 = Normal closure
```

## Common WebSocket Auth Patterns to Discover

Mine the JS bundle for the auth flow. Search for the `WebSocket` constructor and the
first `send()` call. Typical patterns:

1. **Token in first frame** (most common):
   ```js
   this.socket = new WebSocket(socketUrl);
   this.socket.onopen = () => {
     this.send({type: "authenticate", token: r.token});
   };
   ```
   → Auth lives in the **token source** (usually `POST /api/.../session`), not the WS itself.

2. **Token as query param**:
   ```js
   new WebSocket(`wss://target/socket?token=${token}`)
   ```
   → Test: does the server validate the token, or accept any string? Does the token expire?

3. **Cookie-based** (invisible in upgrade headers):
   ```js
   new WebSocket(socketUrl);  # cookies auto-sent
   ```
   → Test: does an unauthenticated session get a working socket?

4. **Signed URL with expiry**:
   ```js
   new WebSocket(signedUrl)  # server signs the URL with HMAC + expiry
   ```
   → Test: replay, expiry bypass, HMAC key extraction.

## What to Probe After Discovering the Auth Pattern

| Vector | Test |
|--------|------|
| Token reuse across users | Get token as user A, use on user B's resources |
| Token replay | Use the same token twice |
| Token expiry | Wait 5/30/60 min, retry |
| Token forgery | Guess the structure (UUID? JWT? random?) |
| Session-cookie substitute | Send session cookie in upgrade headers, skip token frame |
| Mass assignment on token source | POST `/api/.../session` with `{"unlimited":true,"isAdmin":true}` |
| Origin bypass | Strip Origin header from upgrade request |
| First-frame type confusion | Send `{"type":"ready"}` instead of `{"type":"authenticate",...}` |

## CDN-Specific Gotchas

- **Cloudflare**: forwards the 101 upgrade transparently. The origin server sees
  the upgrade as a normal WebSocket. Spoofing `X-Forwarded-For`/`CF-Connecting-IP`
  on the upgrade returns `403 error 1000` — Cloudflare strips client-supplied IPs
  before proxying. IP rotation to bypass rate limits is NOT possible.

- **AWS CloudFront**: similar passthrough behavior. Check `via:` header to confirm
  CDN presence.

- **Origin behind multiple proxies**: the upgrade may pass through 2+ hops; auth
  may be enforced at any hop. If frames are rejected with no clear pattern,
  check whether the CDN itself is doing auth (e.g. Cloudflare Access).

## Case Study: talknova.site (2026-10-04)

- WebSocket at `/api/voice/socket` accepts 101 upgrade with NO auth headers.
- First frame without valid token → server sends CLOSE 1008 (Policy Violation).
- Auth flow: `POST /api/voice/session` → returns `{token, usage}` → client opens
  WS → first frame is `{type:"authenticate", token: r.token}` → server replies
  `{type:"ready"}`.
- `/api/voice/session` is properly auth-gated: 401 "Sign in to use Voice Mode"
  with uniform error regardless of body shape.
- **Result**: no auth bypass; WebSocket auth is correctly token-bound.

## Socket.io-Specific Testing (namespaces, transports, session tokens)

socket.io targets need tests the generic WS recipe above doesn't cover:

### 1. Namespace discovery — wait for the rejection frame

Unknown namespaces STILL ack `40` (connected) immediately; the server sends
`44<ns>,"Invalid namespace"` only after ~1-2 seconds. A recv window shorter than
that misreads EVERY namespace as live. Connect, then listen ≥2s per namespace and
classify: `40<ns>,` kept = real, `44` follows = rejected.

Then map the RPC layer — socket.io apps often route RPCs over HTTP as a SEPARATE
surface (`POST /stream<ns>/rpc/<method>` with body `{"type":"rpc","arg":...}`).
Existence oracle: unknown method → literal `unknown rpc`; live method, bad args →
`Invalid parameters`; dead namespace path → Express `Cannot POST`. Cross the two
axes for a full method×namespace map with zero credentials.

### 2. Protocol-version drift — test BOTH EIO versions

Servers frequently expose socket.io v2 (`EIO=3`) AND v4 (`EIO=4`) simultaneously,
and the production client often speaks the OLDER one. Synthetic testing against the
wrong protocol version tests a surface the real app doesn't use. Grab the production
URL from page traffic (`wss://host/socket.io/?EIO=3&transport=websocket&sid=...`)
and mirror its version.

### 3. Synthetic sockets: websocket transport only

Sequential HTTP polling from a script dies on CDN node affinity — each request lands
on a different backend and the in-memory session returns `"Session ID unknown"`.
One long-lived websocket connection is immune. And on EIO=3 the websocket-FIRST
handshake works with NO polling pre-step: `GET /socket.io/?EIO=3&transport=websocket`
(no sid) returns 101 and the server pushes `0{"sid":...}` as the first frame — own
session in one connection, no affinity problem. (Synthetic `io=<sid>` cookies do NOT
fix polling affinity — the cookie is not honored by the routing layer.)

### 4. Sid bearer-attach test

engine.io sessions authenticate by sid alone unless the app binds them server-side:
open a SECOND websocket against a LIVE session's sid (`?...&sid=<victim sid>`).
`101 Switching Protocols` + answered pings = the sid is a single-secret bearer
credential. The websocket Origin allowlist is client-asserted (header VALUE
comparison at handshake) — trivially faked from non-browser clients, so it does not
protect the session. A leaked sid (access logs, any reflection) on an AUTHED socket
= full event-stream takeover. Remediation to state: bind socket sessions to the HTTP
session cookie server-side (reject connections whose cookie doesn't match the
handshake session).

### 5. Unauth emit fencing

Gated namespaces usually kill anonymous emitters: send a `42<ns>,["event",...]`
frame unauth and watch for the server's `41` (namespace disconnect) — that IS the
fence working. Log it; don't retry the emit. Order matters: fire benign probes
(say/lastRain) BEFORE gate probes (join moderators) — the first gated emit kills
the namespace and everything after it reads as "no reply".

### 6. Capture: reassemble continuation frames, sanitize binaries

Large socket.io events fragment across websocket frames (continuations, opcode 0).
A recv loop that treats one frame per message splices JSON at ~4KB boundaries and
"Unterminated string" parse errors. Read one FULL message per recv: loop until the
FIN bit, merging opcode-0 payloads into the opcode-1 message. Pongs and other
binary frames arrive as 2-byte opcodes mid-stream — strip `\x00-\x1f` control
bytes from captured text before any JSON parse. A mis-reassembled capture will make
a 90KB `initialize` event parse as a 4KB stub — size-check messages before
trusting field counts.

### 7. Non-default socket.io parsers: the msgpack silent-drop

Some servers run `socket.io-msgpack-parser` — every TEXT frame (`40`, `42[...]`) is
silently dropped with NO ack and NO error, which reads exactly like an auth gate that
isn't one. Text `40` connects and msgpack connects can both be silently ignored while
the REAL client works. Discriminate by capture, never by frame-guessing:

- **Capture the real client first**: CDP `Network.enable` BEFORE `Page.navigate`, then
  collect `Network.webSocketFrameSent/Received` — CDP delivers bytes base64-encoded;
  decode with `msgpack.unpackb`. Connect = `{type:0, data:{}, nsp:"/ns"}` (data = EMPTY
  MAP, not nil), events = `{type:2, data:[name,args], nsp}`. Server acks carry a `pid`
  msgpack ext.
- **Frame injection onto the trusted socket beats replica sockets**: wrap
  `WebSocket.prototype.send` + a message listener via
  `Page.addScriptToEvaluateOnNewDocument`, then send hand-rolled msgpack bytes through
  the SPA's own live connection. Replica sockets with byte-identical frames and cookies
  can get CLOSED ~1s after the first packet (connection-level gate the replica lacks —
  TLS fingerprint or a registration the SPA did at load); frames injected onto the
  trusted connection are processed normally.
- **Protocol violations kill the connection SILENTLY**: an EVENT on a namespace never
  CONNECTed, or any malformed packet — no error frame, the socket just stops answering.
  After any violation RELOAD the page; never re-probe on a dead socket (it reads as
  "no data" and burns the namespace verdict).
- **Guest-open vs gated namespaces**: the client's namespace config
  (`authenticated:!1` flags) maps the surface — feeds marked guest-open stream to
  anonymous sockets while `/player-*` style namespaces return CONNECT_ERROR
  (`er_spectator_not_allowed`-shaped) or silence. Client-asserted auth objects
  (`{"x-public-id": <id>}`) are ignored on guest connections when the server derives
  identity from the session — a leaked PUBLIC id does not open gated namespaces.

## When to Use This

- Target has any WebSocket endpoint (voice, chat, live updates, gaming, trading).
- Target is behind a CDN that proxies WebSocket (Cloudflare, CloudFront, Fastly).
- You see `socketUrl` or `new WebSocket(` in the JS bundle.
- The endpoint appears to accept unauthenticated upgrades (this is normal and
  does NOT mean it's vulnerable — keep probing).

### 8. Impersonated WS clients in practice (curl_cffi)

`Session(impersonate="chrome110")` is the practical client for CF-fronted WS testing:

- **Warm the jar before the upgrade**: a bare `ws_connect` with browser TLS but no
  cookie history gets CF 403; the SAME Session after one `GET https://target/`
  (which receives `__cf_bm`) passes the upgrade. The clearance is cookie-carried,
  not TLS-carried — an "impersonation failed" verdict without a warmed jar is a
  false negative.
- **One Session per probe**: session jars accumulate CF cookies until requests die
  with 431 "Header Value Too Long" (the error names the culprit header).
- **Cookies iterate as name strings**, not Cookie objects — `dict(s.cookies)` for
  name→value.
- **Capture the handshake without raw CDP**: playwright `page.on('websocket')` →
  `ws.on('framesent')`/`ws.on('framereceived')` on a real page load reveals the
  client's exact opening bytes — replicate those byte-for-byte instead of guessing
  packet shapes.

### ASN-block discriminator (block page ≠ solvable challenge)

A 403 "Attention Required!" that PERSISTS for a real headless chromium while
`cdn-cgi/challenge-platform/...` assets return 200 is an ASN/datacenter block, not
a challenge — the JS runs, the wall stays. No header/TLS/cookie stack clears it; the
plane is reachable only from residential egress, which is a sanctioned-vantage
decision for the operator, never a home-IP technique. Record the class negative
with the discriminator evidence and move on.
