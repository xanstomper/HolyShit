# Case: logfare.ai re-engagement (2026-10-06) — anon playground inference farm

## Architecture change since 2026-10-03 baseline
Main host is now server-rendered (no SPA bundle); auth moved to cookie sessions; signup gained a
**Discord-membership gate** ("Verify that you are in the Logfare Discord server") — the old
no-email signup is gone. `/migrate` flow for existing accounts.

## Re-verified
- **CORS arbitrary-origin + credentials reflection** (score 72) on every endpoint including
  state-changers (`/v1/auth/regenerate-key`, `/v1/me/delete`). BUT: auth is now cookie-based and
  observed cookies ship `SameSite=Lax; HttpOnly; Secure` + path scoping → cross-site POSTs don't
  carry the session. **Exploitability downgraded 9.1 → ~7.1.** Lesson: the SAME finding changes
  severity when the auth model changes — re-rate exploitability, not just presence, on re-engage.
- `/openapi.json` full exposure (60+ routes, no security schemes).

## HOLY SHIT (75): chat.logfare.ai anon inference farm
Chain: `Origin: https://chat.logfare.ai` header (plain spoof) → `POST /api/chat {"message":...,
"model":"logfare/auto"}` → server mints `lfc_session` (90-day HttpOnly) with zero auth → real
SSE completions. ~30 reqs, zero 429s; 3 parallel long completions (1.7k/1k/2.7k tokens) served.

Key discriminators learned:
- **Origin gate is a header string-match, enforced only at SESSION MINT.** evil/null/absent →
  403 during mint; once a session cookie exists, the same POST works with **no Origin at all**.
  Test the gate separately for mint vs. use — one 403 does not mean the endpoint is gated.
- **Playground hosts hide the real API.** Ghost discrimination on chat host: `404 text/html` =
  ghost, `403 application/json` = real route. Found `/api/health`, `/api/models`,
  `/api/chat`, `/api/auth`, `/api/conversations`, `/api/settings`, `/api/consent`.
- **Error channel gives body shape:** bare POST → 400 "message required" (field is `message`,
  not OpenAI `messages`).
- **SSE is base64-wrapped JSON per `data:` line** (`eyJ...`) — decode with `+ '='*(-len%4)`;
  `logfare_complete:true` final chunk carries usage. First-chunk `usage.prompt_tokens` is the
  PTOK-drift oracle (constant ~7-36/fresh session here = isolated sessions, no shared buffer).
- **Anon `/api/settings` PUT accepts `system_prompt`/`default_model` (persisted) but mass-assigned
  `tier/role/premium/consent` fields are silently dropped** — server re-checks tier on every call
  (`consent_required` 403 on tier-2 models). `/api/consent` GET leaks `{"tier":"anonymous",
  "can_use_premium":false,"logged_in":false}`.
- **Conversation IDOR held** (cross-session read → 404). PATCH/DELETE own conversation 200.

## Negatives (hardened)
Discord OAuth: forged state → 400; state cookie HttpOnly/Secure/Lax/path-scoped JWT;
`redirect_uri` on `/v1/auth/discord/start` NOT client-controllable. Login rate limit works
(5×401 → 429). OAuth/device/SSO client probes give no enumeration oracle. `/api/conversations`
and `/api/settings` 200 on anon sessions are per-session state, not leaks.

## Wall
All `/v1/*` account surface 401; the real authed matrix needs a Discord-verified login →
operator-supplied session per scope gate (do not bootstrap).
