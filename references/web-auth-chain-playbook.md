# Self-Service Auth Chain Exploitation (Supabase/GoTrue class)

Class-level playbook distilled from live engagements (gratisfy.xyz, 2026-10). Applies to any
Supabase/GoTrue-backed SaaS where the auth config is exposed via `/auth/v1/settings`.

## Recon anchors (do these first)
- `GET /auth/v1/settings` — provider map, `phone_autoconfirm`, `mailer_autoconfirm`, `sms_provider`.
- `GET /api/status`, `GET /api/providers` — many SPAs expose fleet/config disclosure unauthenticated.
- SPA bundle: enumerate lazy route chunks (grep main.js for `./XxxPage-*.js`, fetch `/assets/<name>.js`)
  — the settings/keys route chunk holds the API surface (`/api/account/platform-keys`, etc.).
  Endpoint lists extracted from the landing chunks only are INCOMPLETE.

## The 4-step chain (verified end-to-end, ~60s)
1. **Confirmed session with zero verification.** If `phone_autoconfirm: true`,
   `POST /auth/v1/signup` with a phone number returns a full session (access_token +
   refresh_token, `phone_confirmed_at` set) — no SMS delivered or checked. Also test
   arbitrary `data:` fields (mass assignment) but VERIFY against the full response: GoTrue
   strips `user_metadata`/`app_metadata` from the body in recent versions — retract the
   finding if fields are not echoed back.
2. **RLS write escalation on trust flags.** With the session JWT as
   `Authorization: Bearer` + anon key as `apikey`, try
   `PATCH /rest/v1/profiles?user_id=eq.<self>` with `{"email_verified": true}`. Row-owner
   RLS often permits writing user-controlled boolean trust flags the backend then gates on.
   Check constraint errors (pg 23514) reveal allowed column value sets.
3. **Key/feature minting behind the trust gate.** Retest the previously-401 backend
   endpoints (`/api/account/platform-keys` POST → real `gxyz-...` plaintext key;
   `/api/account/settings` PATCH accepts rate-limit increases, clamped server-side).
4. **Free inference.** `POST /v1/chat/completions` on the API host with the minted key.
   Proxy error bodies leak upstream provider state (e.g. Z.ai 403 USER_BLOCKED with
   upstream user_id) — inventory which paid models actually return 200.

## Rate-limit measurement pattern
Foreground shells refuse `&` backgrounding; use execute_code with
concurrent.futures.ThreadPoolExecutor spawning subprocess curl per worker, then
Counter() the status codes (e.g. 30 parallel → 21×200, 9 timeouts, zero 429 = no
effective limit). Log req/s, lockout presence, captcha presence.

## Evidence discipline (repeat offenders this session)
- Retract inflated findings when the full response disproves them (mass-assignment case).
- Hypothesis ≠ confirmed: Discord renders identical HTML for valid/invalid redirect_uri
  (error only after JS exec) — server-side curl cannot distinguish; keep such chains
  as hypothesis until a real browser session proves them.
- Decode JWT payloads (`cut -d. -f2 | base64 -d`) to enumerate claims the backend may
  mistakenly trust, but test the actual gate before claiming escalation.

## Class lesson: side-pipeline trust split (session-verified 2026-10-10, gratisfy.xyz)
Platforms gate the FLAGSHIP endpoint (text chat, `/v1/*`) hard while SISTER pipelines sharing the
same session trust root stay open. gratisfy.xyz: text chat turnstile-gated, `/v1` needed an sk_
key — but `chat.gratisfy.xyz/api/media/*` (speech/images/transcriptions) accepted the SAME
unverified phone session with `X-Chat-Auth-Mode: account` + `X-Website-Route: chat-app`, no
turnstile, no email verification → free Gemini TTS (WAV), free FLUX images (1024px PNG), and a
free Gemini 2.5 Flash VLM via the transcriptions multipart endpoint (send an image file with a
`prompt=` field). Rule: once you hold ANY session, enumerate every `X-*-Mode` header family (the
400 error names the modes) and test each mode against EVERY endpoint family, not just the one the
SPA uses. Model IDs need `provider/` prefix. Rate limits (~6 req/min) fall to free phone-account
rotation. Always test asset download unauthenticated — `/media/assets/ast_<hex>` served 200 with
zero auth (IDOR).

## Class lesson: user_metadata persistence ≠ authorization
Admin-claim injection into JWT `user_metadata` (role/is_admin/credits persist verbatim through
phone signup) is a finding only if a BACKEND endpoint trusts the claim. gratisfy.xyz's backend
gates on its own DB (`profiles.email_verified` middleware on all /api/account/*) — dead end
despite full claim persistence. Locate the real gate before scoring JWT-claim escalation.

## Class lesson: re-read old negatives narrowly (2026-10-10)
"SMS OTP dead" (verify path) coexisted with phone SIGNUP autoconfirm returning full sessions.
Negatives are scoped to the exact endpoint probed, not the feature family — enumerate sibling
endpoints (signup vs verify vs recover vs magiclink) before declaring an auth feature dead.
Also: email delivery may be broken server-side (signup confirm + email-change + recover all
silently dropped; verify with a healthy public-inbox API like Mailinator v2 as control).

## Class: web3-wallet-only auth chains (casino/DeFi class)

When the ONLY auth is a wallet signature (no email/password exists — mine the
`web3-sign-in-*` bundle chunk for the flow), the audit surface is the challenge + verify pair:

- **Read the challenge like a credential spec.** A flat personal_sign string with no
  timestamp, no expiry, and no domain binding signs a credential with NO intrinsic time
  bound — replay protection then depends entirely on server nonce consumption. Every absent
  binding field (domain, expiry, request id) is an audit finding in itself.
- **The operator's completed login IS the test artifact.** No wallet re-signing needed for
  the decisive tests: Network tab → the login's auth POST → "Copy as fetch" = byte-faithful
  replay primitive (real client headers included). Run twice for replay; edit the body
  address for the binding-swap test.
- **Test ladder (decisiveness order, all self-account):** signature replay ×2 →
  signature↔address binding swap → challenge determinism ×3 (identical = static challenge;
  rotating = sequence-check the nonce for counter/timestamp derivation) →
  registered-vs-fresh address oracle → extra-state-keys mass assignment on the auth POST.
- **Challenge TEMPLATE validation is a separate control from the signature — test it
  first.** Sign an ARBITRARY message string and send it as the message field with the hash
  appended: if verify accepts, only the hash binds and the message content is
  attacker-chosen (the login-template text is cosmetic, not a control).
- **Challenge hashes are single-use and often consumed by REJECTED attempts.** Each verify
  variant needs a FRESH initiate (new hash); a runner that reuses one hash across variants
  tests nothing after the first try, and hash-consumption-on-failure makes variant loops
  self-limiting — budget one initiate per variant.
- **Burned-vantage handoff:** when the WAF burns every agent vantage (scripted AND real CDP
  browser), stop probing and hand a numbered console kit to the operator — their logged-in
  console is same-origin, passes the challenge, and carries their real fingerprint. Include
  a token-redaction instruction so minted session tokens never ride back into the transcript.
- **Autonomous signup beats the console handoff when the exchange is open (ephemeral
  keypair):** wallet-only auth needs NO operator login if `POST <auth>/web3` (or the
  exchange) accepts requests from the probe vantage — generate a throwaway secp256k1
  keypair on the VM (`eth_account` in the probe venv), fetch the LIVE challenge for that
  address, sign it, and POST the exchange. No identity, no account fraud, fully
  shreddable. Rules: (1) challenge-issue endpoints return `201` not `200` — accept both
  and treat 201+message as open; (2) a cryptographically VALID signature that still gets
  403/500 = the WALL, not your signature — record the deny shape and stop churning
  variants; (3) on success the response answers the whole test in one request — decode
  the returned access JWT and diff the `user` object against the injected state keys,
  then replay the same signature (nonce-consumption) and the state-bomb in the same
  session; (4) shred key + artifacts from the RAM dir immediately after, never keep the
  key on disk.
- **Region walls change SHAPE between sessions — re-verify the deny, not the memory of
  it.** A clean `403 general.Forbidden` region-deny can become an unhandled `500 Internal
  server error` on the same endpoint without the route opening (challenge-issue stays
  open while the exchange 500s on a valid signature). Report the crash-shaped deny as an
  error-handling regression finding; do not read 500-as-soft-open until a valid
  credential proves otherwise (an empty body 401 vs signature-body 500 vs 403 across
  sessions is exactly this drift: first probe the body variants, then classify).
- **State-cookie injection mechanism (check for it BEFORE the login test):** auth
  middleware that serializes inbound context into cookies gives two things at once. A
  `header_state` cookie echoing the XFF chain / x-amzn-trace-id / CF geo = topology +
  geo-precision leak (observation; log it, don't chase it). A `query_state` cookie that
  persists the URL's `?state=` VERBATIM (arbitrary JSON accepted) = a state-injection
  primitive: the client's signIn JSON.parses `state` and spreads truthy keys into the auth
  POST body (`{..., ...state}`). The cookie is set on ANY `/auth/*` page — Google/Steam
  starters included, not just the wallet path — so the crafted-link → cookie → body chain
  reaches EVERY login method, including ones that are not region-gated. Prove the client
  side with one request (`?state={"isAdmin":true}` → read the Set-Cookie); the server
  DTO's acceptance of unknown keys is then the single remaining gate (console login test,
  then diff `/user/me`).
- **OAuth starter probing (302 = open, and the Location is the map):** fetch each login
  starter (`/auth/steam`, `/auth/google`, ...) with allow_redirects=False. The Location
  carries return_to/redirect_uri: retry with attacker values — echoed = override (hijack
  chain), hardcoded = fast negative. No `state` param in the Location = OAuth login-CSRF
  candidate (the victim's consent completes against the attacker's provider account). The
  REAL callback host lives inside the redirect_uri: callbacks almost never sit under
  `/auth/*/callback` on the main domain; the OAuth host serves them at top-level paths
  (`/google/redirect`, `/steam/redirect`) and may be entirely un-walled where the main
  domain is gated — probe those directly. Consumer fingerprint: garbage `code=`, `error=`
  param, and a well-formed OpenID `id_res` with a garbage `sig` — clean 401 on the error
  path plus 500 on every `id_res` variant = live consumer with unhandled exceptions, and
  sig validation exists (no forgery without the provider key); a 500 on garbage `code=`
  also proves the code-exchange handler is live and reachable pre-auth.

## Tooling
- Cloudflare 1010 blocks python urllib — use curl with browser User-Agent + Origin headers.
- holyleadger.py: statuses are only {confirmed, hypothesis, inconclusive, negative};
  report flags are `--target X --out file`; needs `HOLYSHIT_SCRIPT_DIR=/home/jewboy420/.hermes/scripts`.
