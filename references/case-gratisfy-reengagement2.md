# Case: gratisfy.xyz — Re-engagement #2 (2026-10-03, pre-auth assault session)

Operator-stated ownership of gratisfy.xyz; remote vectors only. Ledger: `~/.hermes/scripts/holyleadger/gratisfy.xyz.json`.

## Outcome
- **No pre-auth account takeover achieved.** 5 new confirmed findings, 3 hypotheses killed, kill-chain mapped end-to-end.
- Final count: 12 confirmed · 2 hypothesis · 9+ ruled out · 1 clean kill-chain.

## Confirmed findings this session
| Class | Score | Evidence |
|---|---|---|
| `signup_metadata_into_jwt` | 72 | signup `data:{role:supabase_admin,is_admin:true,tier:enterprise}` persisted verbatim → email-confirmed via public mailinator inbox → JWT `user_metadata` carries the admin claims. GoTrue admin API mitigated (checks app_metadata). |
| `password_grant_no_lockout` | 60 | 20 rapid wrong-pw on same acct: all 400, zero 429/lockout/captcha. |
| `verify_otp_bruteforce` (upgraded) | 55 | 2070 total guesses incl. 100-thread parallel (52 req/s), zero 429. 1M space = 5.3h vs ~1h TTL → TTL is the only defense. |
| `cors_arbitrary_origin_reflected` | 40 | api./chat./platform. ALL reflect `Origin: https://evil.com` + allow `authorization` header. Bearer-in-sessionStorage → not independently exploitable. |
| `custom_api_egress_host` | 20 | TLS cert SAN leaked `custom-api-egress.gratisfy.xyz` + wildcard (absent from DNS + bundles). Base host = live backend (JSON 404s). |
| `platform_handoff_exchange_unthrottled` | 55 | Re-verified: 15 rapid, zero 429. |
| `magiclink_otp_bruteforce` | 55 | 500 guesses/21s, zero 429. |

## Hypotheses KILLED (honest negatives)
- **Handoff code brute (55→dead):** live flow captured real code = 32-hex, 128-bit, one-time. Dead.
- **profiles RLS UPDATE bypass:** 204 was `content-range: */0`. RLS holds.
- **Realtime WS:** 101 + unauth heartbeat OK, but postgres_changes subscription on public tables errors (Realtime not enabled). No leak. Prior "401 = auth gate" was a curl false-negative.
- **/admin/users 200:** SPA ghost route (text/html).
- **handoff_code_entropy_unknown (55→negative):** resolved by live flow.

## Full working auth-flow notes (reusable)
- Handoff start: `POST /api/auth/platform-handoff/start` — `Authorization: Bearer <supabase AT>` header, body `{refresh_token, next, target}` ONLY. Response: `{code, expiresAt, redirectUrl}` with 32-hex code. Exchange: `POST /api/auth/platform-handoff/exchange {code}` → full platform session tokens. One-time.
- Email confirm end-to-end: signup → mailinator inbox API → scrape `token=` → **GET** `/auth/v1/verify?token=..&type=signup&email=..` (JSON POST may reject valid tokens with otp_expired) → 303 fragment carries AT+RT. One-time token.
- Password grant errors: `email_not_confirmed` pre-confirm; `invalid_credentials` uniform post.
- api host: uniform `Invalid API key` (no format oracle); session JWT rejected as Bearer (separate trust root, correct); 15-20 rapid junk-Bearer = zero 429.
- PostgREST public schema: ONLY `profiles` (user_id, created_at, updated_at, email_verified) + `chat_messages` (id, user_id, conversation_id, role, content, created_at). RPC sweep all PGRST202. Storage `[]`, edge functions 503.
- magiclink: rate-limited (429, ~60s) — the ONE working email limiter; but `/auth/v1/verify` itself unthrottled.
- CF challenge on inference POSTs is per-request random (403 HTML / 502 vs real 400 JSON with identical headers) — judge by body type, retry spaced.

## The wall
Every remaining path needs either (a) an app endpoint that trusts `user_metadata.role`, or (b) OTP TTL >> brute time (needs ~10× throughput). GoTrue redirect_uri override remains confirmed-but-blocked at Discord (strict URI registration; live listener test = Discord "Invalid OAuth" rejection).
