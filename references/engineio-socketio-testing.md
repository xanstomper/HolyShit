# Engine.io / Socket.io Testing Playbook (realtime app layers)

For any SPA with chat/game/realtime feeds (casinos, gateways, streaming apps). Raw Python + ssl, no deps.

## 1. Find the production protocol version FIRST
- The page's own socket URL carries it: `EIO=3` (socket.io v2) vs `EIO=4` (v4). A site can run BOTH on the same `/socket.io/` path — they are DIFFERENT server instances with DIFFERENT namespace registrations. Test BOTH. Evidence: gamdom ran EIO=3 in production (full namespace set incl. game namespaces) while EIO=4 was a secondary instance missing namespaces (`slotsArena` existed only on EIO=3). Testing one protocol = an incomplete engagement.
- Harvest namespace names from the client bundle (`socketioNamespaces.chat` literals; per-game `math.config.socketioNamespace`) before connecting.
- Per-store config objects (`socketioRoot`) can point at DIFFERENT hosts per namespace on multi-service stacks — if a namespace rejects on the main host, check the config source for alternate roots.

## 2. Mint a session WITHOUT polling (bypass CDN affinity)
- CDN-node affinity (Fastly/Varnish) kills sequential polling from python: handshake 200 + sid, then every follow-up poll = `{"code":1,"message":"Session ID unknown"}` — requests land on different edge nodes and the in-memory engine session is gone. Cookie-pinning (`io=<sid>`) does NOT reliably fix it.
- Use the WEBSOCKET-FIRST handshake: `GET /socket.io/?EIO=3&transport=websocket` with NO `sid` — many servers mint the session over the websocket itself (first frame `0{"sid":...}`), on both EIO=3 and EIO=4.
- Always send browser headers INCLUDING `Origin: <target origin>` — the handshake origin-check is enforced at the transport.
- Short-TTL anon socket tokens are often mintable from a PUBLIC metadata endpoint (duel-family: `GET /api/v2/metadata?uuid=000000` returns `socket_token` + rooms + feature-flag table in ONE unauth response). Mint INSIDE the connect script — the JWT can expire in 30s. Token placement = read it off the page's real handshake; usually the QUERY (`?uid=guest&token=<jwt>&EIO=4&transport=websocket`), not the connect payload. A connect that 101s then immediately `41`s = wrong placement, not an auth wall.
- Placement VARIES by server: socket.io v4 commonly takes the token in the CONNECT frame payload (`40{"token":"<jwt>"}`) — a bare `40` that 101s then answers `44{"message":"Could not establish connection"}` means namespace auth is MISSING, not an auth wall; re-handshake and resend with the token in the frame. Tokens often mint UNAUTH from a dedicated endpoint (`POST /auth/token?scope=X`) — see the scope-abuse pattern in SKILL.md.
- Definitive handshake capture when the bundle-derived URL 400s: `performance.getEntriesByType('resource')` does NOT list WebSocket URLs. Install a persistent hook via CDP — `Page.addScriptToEvaluateOnNewDocument` wrapping `window.WebSocket` to push URLs into a `window.__wsUrls` array — then navigate the harness browser across game pages and read the array. One SPA connection serves all namespaces (route changes add namespaces, not connections), so collect across pages before concluding the map.
- Reply `3` (pong) to every `2` (ping) DURING captures: pingInterval 25–45s + pingTimeout ~20s means an un-pong'd capture dies silently mid-listen (~60–90s in) and reads as an event lull. Silent capture death = check the pong path first.

## 3. Namespace mapping
- Send `40/nsp,` (v4; v2 accepts with/without trailing comma). The bare `40` = engine ack; the namespace ack FOLLOWS — wait 2-4s and read frames in order. `40/nsp,` = LIVE; `44/nsp,"Invalid namespace"` = rejected.
- Live namespaces push an initialize/state event on connect (leaderboards, players online, prize data) — capture it; it is often the most data-rich unauth feed on the platform.
- Fuzz extra names (`/admin`, `/mod`, `/staff`, `/internal`, `/prediction`, `/sports`) — expect `44` on hardened stacks; log as negative coverage.

## 4. RPC surface: HTTP-proxy pattern vs socket emits
- Some stacks proxy RPC over HTTP POST `/stream<ns>/rpc/<method>` (body `{"type":"rpc","arg":...}`) while the socket stays receive-only. Extract the method table from the bundle's `.rpc.<method>(` call sites; extract ARG SHAPES from the shared io-ts/zod schema library the client imports (validation enums ship inline — grab WalletUnit/currency enum literals to build valid shapes).
- Method-existence oracle: unknown method → `unknown rpc`; known method with wrong args → `Invalid parameters`; dead namespace → Express-style `Cannot POST`. Maps the server's method table with zero auth.
- Gate order: a VALID-shaped arg changes the response to a session error (`Not logged in`, generic, or `You are not connected...`) — the auth check is only reachable with correct shapes. The session check may bind to a server-issued token exchanged at page load: a bare engine sid + `io` cookie is NOT enough — expect the session error until the full bootstrap exists.

## 5. Emits on anonymous sockets
- Try socket events (`42/ns,["event",args]`) benign-first, gates LAST: many servers disconnect the namespace (`41`) on ANY unexpected emit, and the disconnect kills the rest of the probe queue.
- Receive-only anonymous sockets are a deliberate design on modern stacks — record as the fence, do not re-probe.

## 6. sid = bearer credential (attach test)
- A second websocket using an EXISTING sid attaches to that session (101 accepted, ping answered). The origin allowlist is client-asserted — it stops cross-site browser JS, NOT a scripted attacker who fakes the header.
- Mechanism test: obtain a live sid (page-context hook capturing socket OPEN frames, or your own session), attach a second socket from python, send `2` (v2 ping), expect pong. Do NOT emit application frames on an attached session.
- Impact gate: only AUTHED sockets carry personal events — the sid-attach is the mechanism finding; severity lives in what rides authed sessions.

## 7. Frame-capture integrity (evidence hygiene)
- ALWAYS reassemble continuation frames: large events arrive as op=1 + op=0 fragments (~4KB each); naive per-frame saves split JSON mid-object and corrupt evidence files. Read each header, honor the `fin` bit, merge fin=0 payloads; skip pongs (op=10) instead of writing them as text junk.
- Sanitize control bytes (`[\x00-\x08\x0b\x0c\x0e-\x1f]`) before json-parsing saved captures, and parse arrays with `json.JSONDecoder().raw_decode` rather than regexing field ORDER (field order varies between event types).
- Re-run a second capture and confirm stable IDs/values before calling a leaked field real — a finding that does not reproduce across captures is a parse artifact.
- The masking may exist on SOME feed paths and not others (leaderboard masked, game-detail/crash rows unmasked-with-flag) — audit every path independently.

## 8. Cross-brand (sibling-domain) drift
- Sister brands on the same stack (same error envelopes, CSP, cookies, CDN IPs): diff RPC method tables, namespace sets, endpoint literals, and gate behavior across brands. Older deployments expose different (usually smaller) surfaces and reveal which gates are new.
- Read the namespace init packet's `serverHost` — pods named `<brand>-rcc-slave-*` identify the INFRA OWNER and prove the fleet relationship at the socket level (a sister brand serving your sockets = same operator; their CSP cross-brand collectors corroborate).
- When the origin brand is geo-blocked from your vantage, its accessible sister brand usually runs the SAME shared data plane — the sister is the working vantage; probing the geo-walled brand's socket/API directly is wasted calls.

## 9. Websocket origin allowlist
- Handshake origin matrix (none / `null` / evil origin): 400/403 on hardened stacks = CSWSH dead at the transport — a positive control, log it.

## 10. Polling lifecycle + transport/CDN traps
- **Socket.io polling allows exactly ONE in-flight GET.** Every POST must be followed by a
  single long GET (hold up to pingInterval); a fresh POST while a GET is pending, or a burst
  of short-timeout GETs, kills the session with `{"code":1,"message":"Session ID unknown"}`.
  That error AFTER a successful handshake+connect = your own polling rhythm, not CDN
  affinity. A quiet long-poll (read timeout, no data) is NORMAL — reconnect and continue,
  don't score it as a failure.
- **`400 {"code":0,"message":"Transport unknown"}` on `transport=polling` = the server
  restricts transports (websocket-only), NOT a missing endpoint.** Go websocket-first;
  don't EIO-fish the path.
- **CDN blocks non-browser websocket UPGRADES (403 HTML on the upgrade request) while
  polling frames pass the same path.** When the upgrade 403s with an HTML body, run
  connects/joins/emits over polling frames instead of churning upgrade headers — python
  websocket-client fingerprints non-browser TLS no matter the header set.

## 11. msgpack-parser targets (frames look "auth-gated" when the gate is the wire format)

Some stacks run socket.io with the **msgpack parser** — EVERY text frame (`40`, `40{}`,
`42[...]`) is silently dropped: no ack, no error, no data. Naive testing concludes
"namespace auth-gated" when the gate is just the encoding. Discriminate before scoring.

- **Capture the REAL client before hand-rolling anything.** CDP: `Network.enable` BEFORE
  `Page.navigate` on a fresh tab, then collect `webSocketFrameSent/Received` — CDP delivers
  frame bytes base64-encoded; decode with `msgpack.unpackb`. The connect frame is
  `{type:0, data:{}, nsp:"/ns"}` — data is an EMPTY MAP, not nil (a nil data field gets
  dropped). Events = `{type:2, data:[name,args], nsp}`. Server acks carry a `pid` msgpack
  ext. performance.getEntries does not list sockets — Network events are the only source.
- **Best vantage = frame injection onto the SPA's own trusted connection.** Via
  `Page.addScriptToEvaluateOnNewDocument`, wrap `window.WebSocket` to record `send` and
  incoming messages per connection; then send hand-rolled msgpack bytes through the SPA's
  live socket. Replica sockets with byte-identical frames and the same cookies get CLOSED
  ~1-2s after the first packet (a connection-level gate the replica fails — registration or
  transport fingerprint), but frames injected on the trusted connection are processed
  normally. Injection sidesteps the connection gate entirely.
- **Protocol violations kill the connection SILENTLY.** An EVENT on a namespace never
  CONNECTed, or any malformed packet = the socket just stops (no error frame). After any
  violation RELOAD the page and re-inject; never re-probe on a dead socket — it reads as
  "no data" and burns the namespace verdict.
- **Guest-open vs gated namespaces: read the client's namespace config map
  (`authenticated:!1/!0` per namespace), then VERIFY each.** Config says guest-open but the
  server still enforces: expect CONNECT_ERROR (`er_spectator_not_allowed`-style) on gated
  namespaces and silent drops on chat joins. Both shapes = the gate, log which.
- **Hex-capture hygiene: pad every byte** (`x.toString(16).padStart(2,'0')`) — bare
  `toString(16)` drops leading zeros and silently corrupts msgpack bytes (map16 lengths,
  0x00 bytes) so hand-decoding garbles. Decode captured frames with the msgpack library,
  never by eyeballing hex.
