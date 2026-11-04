# new-api/OneAPI Fork Recipe (session-verified 2026-10-06, apimart.ai)

Fingerprint: `x-oneapi-request-id` response header = OneAPI/new-api backend (QuantumNous/new-api). Then read the UPSTREAM SOURCE live during the engagement (raw.githubusercontent.com) — it gives exact request shapes, middleware order, and rate-limit defaults without touching the target.

## Route-map mining (the big win)

The fork has dozens of custom routes invisible to endpoint guessing: `/api/user/reset_by_code`,
`/api/user/login/email/code`, `/api/web/runtime-key`, `/api/web/token/batch`, `/api/admin-auth`,
`/api/user/free-trial/usage`, `/api/user/promo-discount/preview`, `/api/user/membership`,
`/api/user/{stripe,paypal,nowpayments,antom}/pay`, `/api/messages/tickets/*`, `/api/region-access`.

Method: fetch every `src="/_next/static/chunks/*.js"` from ALL page variants (homepage, /console,
/pricing — each page loads different chunks), then regex `["\'](/api/[A-Za-z0-9_/.-]{2,80})["\']`.
Endpoint guessing alone found ~8 routes; chunk mining found 40+.

## Key facts (upstream source + live confirmation)

- **TurnstileCheck() reads `c.Query("turnstile")`** — token goes in the QUERY STRING even for POST
  routes: `POST /api/user/register?turnstile=TOKEN`.
- **`GET /api/status`** dumps admin module map (SidebarModulesAdmin: ipPool/channel/models/user/
  setting/errorLogs/dailyStats), OAuth client IDs, Turnstile sitekey, version commit hash, email
  verification flag, invite cashback config — all unauth.
- **`GET /api/setup`** returns `{status, root_init, database_type}`. status:true = setup complete;
  root_init is only populated when status:false. Don't false-positive "root not initialized".
  `POST /api/setup` on a completed target: "System has already been initialized."
- **`GET /api/oauth/state`** mints states unauth but state is session-cookie-bound (hardened).
- **`GET /api/pricing/models/all`** dumps the FULL model catalog with internal margins, discount
  ratios, membership tiers unauth when pricing.requireAuth=false — observation-class competitive
  intel, NOT a compromise (473KB on apimart).
- **Rate limits:** `CriticalRateLimit` = 20 req / 20 min per IP (upstream default,
  common/constants.go), SHARED across all critical routes (register/login/reset/verification —
  a burst on one locks all). Most app errors return HTTP 200 with `success:false` — 429 detection
  MUST read bodies, not status codes.
- **Password reset flow:** `GET /api/reset_password?email=X` (Turnstile-gated) emails a 32-hex UUID
  token; `POST /api/user/reset {email, token}` (NO Turnstile — only CriticalRateLimit) returns the
  NEW PASSWORD verbatim in `data`. Email-verification codes are `GenerateVerificationCode(6)` =
  first 6 UUID-hex chars (~1M space, brute-able ONLY if register's Turnstile is bypassable).
  `GET /api/verification?email=` (6-digit codes) IS Turnstile-gated. Reset tokens are NOT
  brute-able (32 hex). Realistic fork-level chain: free-trial farming via IPv6 rotation +
  disposable email, gated on Turnstile solving.
- **In-memory verification map** (common/verification.go): global map, `removeExpiredPairs()` only
  purges EXPIRED entries — inserts ALWAYS happen, so no eviction primitive (memory growth only).
  Do not chase an eviction DoS there.

## IPv6 /64 rotation

`sudo ip -6 addr add <any-addr-in-block>/64 dev <iface>` then `curl --interface <addr>` = fresh
rate-limit bucket per address. NOTE: the sandbox security guard may block `curl --interface <addr>`
mid-session (approved-command gate) — scope-gate with the operator before IP-rotation testing.

## Turnstile harvesting

Headless Playwright (firefox) often fails to render the widget:
`[Cloudflare Turnstile] Unable to find onload callback 'onloadTurnstileCallback'`. The target's own
integration can be half-broken — if the widget never mints tokens for real users either,
server-side enforcement may be flaky. Test `?turnstile=garbage` once the rate limit allows.

## SEO-spam botnet discovery pattern

Sketchy providers seed GitHub with dozens of random-char accounts pushing identical READMEs,
sometimes literally named `*-bypass-guide` — grep those READMEs for the provider domain
(`go.<provider>/k-xxxxx` affiliate links). Identical descriptions + same-day pushes + 0 stars =
same operator. The "bypass-guide" keyword bait tells you the operator KNOWS its surface is weak.
GitHub search queries that surfaced this: `llm api reseller`, `openai compatible api gateway cheap`,
`ai api relay free claude gpt no key`, `openrouter alternative free api key`.
