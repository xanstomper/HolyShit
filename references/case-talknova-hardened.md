# Case: talknova.site — hardened-target recon (2026-10-03 + 2026-10-04 re-engagement)

A young (Wayback first capture ~2026-09-18) Cloudflare-fronted Next.js SPA, Google-OAuth-only,
manual crypto plan activation via Discord tickets. Full phase-1/2 sweep produced ZERO confirmed
vulns — a worked example of a hardened target and the probe recipes that produced high-quality
negatives fast (~20 curl/grep rounds).

## 2026-10-04 re-engagement — new surface found, still zero confirmed vulns

Bundle hash `DwftPOeS` (same architecture, new code-split chunks). Key discovery: **always
fetch code-split chunks** — the main bundle only lazy-loads page components; the real API
surface lives in the chunks.

New endpoints NOT in 2026-10-03 case:
- `/api/apikey`, `/api/apikey/regenerate`, `/api/apikey/rotate` — personal OpenAI-compatible key CRUD
- `/v1/models`, `/v1/chat/completions` — key-authenticated API
- `/api/admin/{session,login,logout,stats,logs,users,grants,apikeys,custom-keys}` — full admin portal
- `/api-access` — SPA route for key management (not an API endpoint)

Admin portal map (from `AdminPage-Cgkb504W.js`):
- Login: `POST /api/admin/login` with `{username, password}` (not email)
- User management: `GET /api/admin/users?q=&page=&filter=`, `PATCH /api/admin/users/:id`, `DELETE /api/admin/users/:id`
- Plan grants: `POST /api/admin/grants` `{email, plan, days}`, `DELETE /api/admin/grants/:id`
- Custom API keys: `POST /api/admin/custom-keys` `{label, balanceDollars, allowedModels}`, `PATCH /api/admin/custom-keys/:id` (top-up, model restrict), `DELETE /api/admin/custom-keys/:id`
- Audit: `GET /api/admin/logs`, `GET /api/admin/stats`

All admin endpoints return 401 without server-side admin session. Rate limiter on
`/api/admin/login` is aggressive: 4 failed attempts → 429 with 30-minute decay.

## Re-engagement probe recipe (reusable for any baselined hardened target)

1. **Diff the live bundle hash** against the prior case file. Same hash = same code; new hash = redeploy, re-run full probe ladder.
2. **Fetch ALL code-split chunks.** The main bundle only holds the route table; page components are lazy-loaded. Find chunks via `grep -oE '"\./[A-Za-z0-9_-]+\.js"' app.js`, then fetch each and mine for `fetch("..."` calls.
3. **Ghost-route sweep on every discovered path.** Only `application/json` responses are real; `text/html` = SPA fallback ghost. This instantly kills false positives.
4. **Authz matrix on new surface.** For every new endpoint, test: GET unauth, POST unauth, PATCH/DELETE unauth, IDOR by numeric ID, mass assignment with extra fields.
5. **Rate-limit probe EARLY on login endpoints.** If the limiter is aggressive, you'll lock yourself out before injection tests — do SQLi/NoSQLi probes first, or accept the lockout as a negative finding.
6. **Where the wall is, say it.** Pre-auth surface exhausted → state the exact next test and the credential required. Do not probe spam past the wall.

## Architecture snapshot (2026-10-04)
- Static SPA bundle at `/v2/index-DwftPOeS.js` (1.4MB) holds route table; page chunks:
  - `ApiAccessPage-R65e4e7N.js` — key CRUD UI
  - `AdminPage-Cgkb504W.js` — full admin portal UI
  - `PayPage-8GPU0X34.js` — manual crypto checkout (no wallet addresses client-side)
  - `DocsPage-B3El2gVm.js` — documentation
- Origin lock on all cookie-auth POSTs: wrong/missing/`null` Origin →
  `403 {"error":"Cross-origin request rejected."}`.
- OAuth: 10-min HttpOnly SameSite=Lax state cookie (`koda_oauth_state`) bound 1:1 to the state
  param, PKCE S256 with server-held verifier, hardcoded redirect_uri, `returnTo` sanitized.
- CSP: hash-based `script-src 'self'` + strict `connect-src` allowlist, `frame-ancestors 'none'`, COOP/CORP, HSTS.
- API keys: personal keys shared with web chat usage; admin can issue standalone keys with dollar balance + model allowlist.

## Probe recipes that paid off (reusable)

### SPA endpoint + body-shape mining (minified bundle)
1. `grep -oE '"/[a-zA-Z0-9_/.-]{2,60}"' app.js | sort -u` → route + endpoint list.
2. All fetch calls: `grep -oE 'fetch\("[a-z0-9/_-]+"' app.js | sort -u`.
3. Body shapes live at CALL SITES of the wrapper fn, not the fetch itself — find the wrapper
   (e.g. `async function Y8(e,t){fetch("/api/chat"...}`), then grep its callers:
   `grep -oE 'Y8\(\{[^}]{0,150}' app.js` → reveals real body keys (`{modelId, message}` not
   the guessed `{model, messages}`). Server error strings are the oracle.
4. **Code-split chunk discovery**: `grep -oE '"\./[A-Za-z0-9_-]+\.js"' app.js` → fetch each chunk, mine for endpoints.

### OAuth state-binding test (5 curls, decisive)
1. GET `/api/auth/google/start?attempt=x1` → capture state cookie A.
2. GET start again → cookie B. Then `callback?state=A&code=fake` with cookie B → hardened if `Invalid OAuth state`.
3. Matched cookie + fake code → expect token-exchange failure.
4. `returnTo=https://evil.com` on /start → hardened if Location still goes only to Google.
5. Callback with no cookie / no state → expect 400.

### Origin-lock matrix (cookie-auth endpoints)
For each POST endpoint, fire: attacker Origin, `Origin: null`, and NO Origin — all should 403.

### Ghost-route discrimination
404s returning `application/json` = real routing layer (not SPA fallback). Only `text/html`
404/200s are ghosts. Check `/openapi.json`, `/docs`, `/api/docs` — but expect them genuinely absent on hardened non-FastAPI targets.

### Admin authz matrix (when admin endpoints are discovered)
- GET unauth → expect 401
- POST unauth → expect 401
- PATCH/DELETE unauth → expect 401
- IDOR by numeric ID (`/users/1`, `/grants/1`, `/custom-keys/1`) → expect 401
- Mass assignment probe (`{"plan":"max","is_admin":true}`) → expect 401 or validation error
- Rate-limit probe on login → note decay time (talknova: 30 min)

## Results (negatives are results — log them)
- CORS arbitrary origin+credentials: NEGATIVE (hard origin lock on all cookie endpoints).
- OAuth state/PKCE/open-redirect/replay: NEGATIVE (textbook hardening).
- Rate limiting on /api/admin/login: CONFIRMED WORKING (4 fails → 429, 30-min decay).
- Authz on admin surface: NEGATIVE (all endpoints 401 without session).
- IDOR on admin user/grant/custom-key endpoints: NEGATIVE (401 on all unauth attempts).
- SQLi/NoSQLi on admin login: NOT TESTED (rate limiter locked us out first).
- Ghost routes: all /api 404s are `application/json` — real routing.
- Backdoors: no client-side ID hardcodes or role gates in the bundle.
- CSP: hash/nonce lockdown; no obvious XSS delivery channel.
- API key auth: NEGATIVE (/v1/models 401 without Bearer).

## Where the wall is
Everything interesting sits behind:
1. **Google session** — /api/chat plan-tier tampering, /api/usage IDOR, /api/apikey authz (can user A read user B's key?)
2. **Admin session** — admin API depth, session fixation, CSRF on state-changing admin POSTs, privilege escalation via mass assignment on /api/admin/users/:id

Pre-auth surface exhausted. The next decisive test REQUIRES credentials.

## Operational note
Ledger state saved to `~/.hermes/scripts/holyleadger/talknova.site.json` with full endpoint map, findings, and attack-surface notes.
