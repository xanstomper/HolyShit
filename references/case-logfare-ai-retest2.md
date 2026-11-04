# logfare.ai re-engagement — 2026-10-06 (CORS-severity downgrade via cookie SameSite)

## Context
Second engagement of logfare.ai (baseline 2026-10-03: CORS arbitrary-origin + credentials
CVSS ~9.1, broken rate limiting, FastAPI openapi.json exposure). Target rebuilt since
baseline: SPA → server-rendered FastAPI (inline `<script>` blocks, no hashed JS bundle),
plus a NEW OAuth-provider surface (`/oauth/authorize`, `/v1/me/apps`, device flow).

## Re-verification of prior confirmeds (doctrine: patch-check FIRST)
- **CORS reflection SURVIVED** on every endpoint incl. state-changers:
  `/v1/models`, `/login`, `/register`, `/dashboard`, `/v1/chat/completions` (405 but
  headers present), `POST /v1/auth/regenerate-key`, `/v1/me/delete`, `/v1/me/opt-out` —
  all reflect `access-control-allow-origin: https://evil.com` +
  `access-control-allow-credentials: true` (vary: Origin).
- **BUT auth model changed** to cookie sessions. Observed cookie flags
  (`/v1/auth/discord/start`):
  `logfare_discord_oauth_state=...; HttpOnly; Max-Age=600; Path=/v1/auth/discord; SameSite=lax; Secure`
  SameSite=Lax blocks cross-site POST cookies → prior CVSS ~9.1 downgraded to ~7.1
  (cross-site GET/top-level-nav exposure + misconfig lint, not session hijack).
  Authenticated matrix (real login cookie SameSite, IDOR, regenerate CSRF) needs a session.
- **openapi.json still 200** (24.5KB, 60+ routes, no security schemes declared), /docs public.

## New hardening since baseline (negatives)
- **Signup Discord-membership gate**: `POST /v1/auth/register` → 403 "Verify that you are in
  the Logfare Discord server before creating an account." Homepage marketing ("No email, no
  verification, no bullshit") is FALSE — actual gate is Discord membership. `/migrate`
  flow exists for existing accounts.
- **Discord OAuth state binding**: forged state → 400. State cookie = server-issued HS256
  JWT, HttpOnly/Secure/SameSite=Lax/path-scoped/10-min. Textbook.
- **redirect_uri NOT client-controllable**: `/v1/auth/discord/start?redirect_uri=https://evil.com/cb`
  ignored the param, hardcoded `redirect_uri=https://logfare.ai/v1/auth/discord/callback`
  verbatim in the 302 Location (client_id 1553307977572941916, scope=identify).
- **Login rate limiter works now** (baseline said broken): 12-burst → 5×401 then 429s.
- **OAuth/SSO/device no oracle**: bogus client_id on `GET /oauth/authorize` renders generic
  "Connect an app / Enter the code" page (200, no enumeration); `POST /oauth/authorize` 403;
  `POST /v1/integrations/oauth/device_authorization` + `/v1/sso/token` uniform 401.
- `/connections` → 302 `/login?next=%2Fconnections` (proper login redirect).

## Wall
Decisive next tests (login-cookie SameSite verification, `/v1/me/*` IDOR, regenerate-key
CSRF-with-cookie, consent/opt-out flows) all require a logged-in session, which requires
Discord membership. Scope gate: do NOT self-provision a Discord account — ask operator.

## Ledger
`~/.hermes/scripts/holyleadger/logfare.ai.json` — cors_reflected_arbitrary_origin_credentials
(confirmed, 72), openapi_full_exposure (confirmed, 40), 5 negatives.

## Lessons
1. CORS finding severity is a function of auth model + cookie SameSite, not the reflection
   alone. Read raw Set-Cookie flags before rating; re-derive severity when auth model churns.
2. Targets get rebuilt between sessions (SPA → server-rendered). Diff the openapi route list
   across re-engagements like bundle hashes; don't grep a stale bundle.
3. Marketing copy about signup friction is not evidence — probe the register endpoint.
