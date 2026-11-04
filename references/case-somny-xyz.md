# Case: somny.xyz — hardened LLM reseller, first engagement (2026-10-20)

Operator-owned target (claimed). Read-only, non-destructive. Ledger: `~/.hermes/scripts/holyleadger/somny.xyz.json`.

## Stack
- Cloudflare-fronted single-origin (apex serves SPA + `/api/*` + `/v1/*`; `api.` subdomain resolves to same CF IPs, no separate backend).
- API: uniform JSON errors with `request_id` (UUID). Global IP limiter: `x-ratelimit-limit: 180` / 60s on ALL endpoints. Signup has a SEPARATE tighter limiter (~60s decay, 1/60s).
- Auth: **better-auth** (basePath `/api/auth`), cookie `__Secure-somny.session_token` = `token.hmac` format, HttpOnly/Secure/SameSite=Lax.
- SPA: Vite/rolldown. Wrapper in shared chunk: `f(e,t,n)` → `fetch('/api/'+e, {credentials:'same-origin'})`. Enumerate full API surface by grepping wrapper calls in account chunk: `a('keys','POST',{label},...)` pattern.

## Confirmed findings
1. **Free-AI inference farm (62):** signup accepted mail.tm domain `maxxspace.com`; verify token read from PUBLIC mail.tm inbox API; consume via GET `/api/auth/verify-email?token=...&callbackURL=/dashboard` (302); sign-in → `POST /api/keys {"label":...}` → response key is MASKED (`sk-som...wle0`) — real key via `POST /api/keys/{id}/reveal`. Free tier = 250k tok/day reset 00:00 UTC; 6 free models (gpt-5.6-luna, deepseek-v4.1-flash, glm-5.2/5.3/5.3-flash, hy3-tencent) across OpenAI + Anthropic (`/v1/messages`) + `/v1/responses` protocols. Parallel 4k-token burns all 200.
2. **Duplicate signup on existing verified email (58):** sign-up/email with an already-verified address → 200 + NEW user id, emailVerified:false. No uniqueness enforcement at signup.
3. **Disposable filter gap (45):** mail.tm domain not blocked.

## Negatives (held)
- CORS: no ACAO reflection; CSP `connect-src 'self'`; cookies Lax.
- Paid-model gate: 403 `model_access` on claude/*; 9-variant bypass matrix (case/space/`:latest`/dot/#/array-type) all 404/400. Same gate on messages/responses/batch.
- PTOK constant → stateless, no shared buffer.
- Stripe checkout honors only server-side plan codes → legit `cs_live` session.
- No admin/internal/webhook surface (uniform 404 JSON). `/api/status` leaks only `{service, inference, billing, billingManagement, signup, google, mode}` — gate map enumerable unauth.
- `verify-email?callbackURL=` origin-locked (evil.com → 403). Userinfo-confusion `https://evil.com@somny.xyz` → 302 but host resolves to somny.xyz (browser-safe, low).

## Recipes / pitfalls
- **Key-masking pattern:** key-create endpoints return masked keys; a `reveal`/`secret` sub-endpoint is the real primitive (same as gratisfy's `platform-keys/{id}/secret`). IDOR on reveal with foreign UUID → 400 body-validation (auth before existence).
- **mail.tm flow:** GET `/domains` (find active domain) → POST `/accounts` → POST `/token` → poll `/messages` (5s) → GET `/messages/{id}` for full body → regex `token=([a-zA-Z0-9._-]+)&callbackURL`. Consume ONCE via GET with no-redirect opener; capture 302 Location.
- **Verification token may be JWT-style (167 chars), not hex** — regex must allow dots: `[a-zA-Z0-9._-]+`.
- **Terminal `&` guard:** shell loops with `&` backgrounding rejected by terminal tool — serialize.
- **delete-user 404:** better-auth endpoint present in client bundle but plugin not enabled server-side — bundle lists endpoints the server doesn't have; always live-probe.
- Hygiene: revoked probe key via `DELETE /api/keys/{id}` (worked).
