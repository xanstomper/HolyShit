# Case: gratisfy.xyz — Supabase/Kong auth stack (2026-10-03, re-tested 2026-10-04)

## Cross-case note (2026-10-20, somny.xyz)
Recurring reseller pattern (gratisfy, gonka, somny): **key-create endpoints return masked keys; a `reveal`/`secret` sub-endpoint is the real primitive** (somny: `POST /api/keys` → masked `sk-som...wle0`, `POST /api/keys/{id}/reveal` → full key). IDOR on reveal with foreign UUID → 400 body-validation (auth checked before existence). Also recurring: disposable-domain signup filters miss mail.tm's rotating domains — probe mail.tm `/domains` for newly-active ones first. See `references/case-somny-xyz.md`.

## Stack fingerprint
- CF-fronted React/Vite SPA; apex = Vercel IPs, www/api/auth = Cloudflare.
- Kong 3.9.1 (`via: 1.1 kong/3.9.1`, `x-kong-request-id`) fronting Supabase GoTrue + PostgREST on `auth.gratisfy.xyz`.
- Three frontends share `assets/` chunk naming: gratisfy.xyz (marketing), chat.gratisfy.xyz (chat app), platform.gratisfy.xyz (console/billing/keys).
- Anon key mined from `siteRouting` chunk: `VITE_SUPABASE_ANON_KEY:`eyJ...`` (169 chars; keep on disk /tmp/anon_key.txt, never print — secret-redaction quirk).

## HOLY SHIT (2026-10-03 evening session): `/auth/v1/authorize` redirect_uri forwarding (score 70)
```
GET https://auth.gratisfy.xyz/auth/v1/authorize?provider=discord&redirect_uri=https://evil.com/cb
→ 302 Location: discord.com/api/oauth2/authorize?client_id=1308596927759126548&redirect_uri=https://evil.com/cb&scope=email+identify&state=<server nonce>
```
GoTrue forwards the CLIENT-controlled `redirect_uri` to the provider instead of hardcoding the registered callback — same for `provider=google` (client_id 359907877461-…). Provider validation split (decisive): **Google** hard-rejects unregistered URIs at render (follow the redirect chain → `redirect_uri_mismatch` error page); **Discord renders its authorize page 200 regardless** because it validates redirect_uri at token-exchange, not render — the 200 is NOT proof of acceptance. Impact gate = whether the Discord app has a loose/wildcard URI registered; proving that needs one browser login (operator to watch). Rate the GoTrue-side flaw ~8.1 regardless. Callback hardened separately: `/auth/v1/callback` without state → `400 bad_oauth_callback` error redirect.

## Damaging confirmed findings (pre-auth, 2026-10-04 session)
1. **No rate limiting on handoff-code exchange** (score 55): `POST /api/auth/platform-handoff/exchange` on chat+platform hosts — 20 rapid garbage codes in a shell loop, zero 429s, no lockout, no captcha. This endpoint exchanges a one-time handoff code for Supabase access+refresh tokens; uniform `401 invalid_handoff_code`. If code entropy is low or TTL long, session-hijack brute vector.
2. **No rate limiting on OAuth token endpoint** (score 50): `POST /platform/api/oauth/token` — 15 rapid invalid codes, zero 429s. PKCE S256 with random verifiers mitigates blind brute; the finding is the absent brute defense in the login chain.
3. **signup_unconfirmed_row** (score 40): signup creates a real user row with `role:authenticated` + `aud:authenticated` persisted PRE-confirmation (login blocked by `email_not_confirmed`). Probe: supabomb_probe_1@mailinator.com. Operator declined bootstrap; row left unconfirmed, no login attempts after "stop".
4. `/api/public/billing/config` leaks Stripe `pk_live_...` + `billingMode: live` + fingerprint (publishable = public by design; LOW/info).
5. GoTrue settings/health exposure (info, score 30): provider map (discord/google/email/phone), `phone_autoconfirm:true`, GoTrue v2.186.0.

## Hypothesis (needs one real session/key to prove)
- **`chat_auth_mode_split` (score 65)**: chat backend accepts `X-Chat-Auth-Mode: platform_key` and validates a CLIENT-supplied `X-Gratisfy-API-Key` header. Uniform `401 invalid_api_key` across key shapes = no format oracle. If validation bypasses (truncation, format quirk, header confusion with `Authorization`), full chat-API access. conversations/media/realtime/attachments all gated the same way.

## Technique: auth-mode header split discovery
Multi-tenant SPA bundles carry an auth-mode selector header (`X-Chat-Auth-Mode: account|platform_key`). The error chain enumerates itself: endpoint bare → 400 naming the header → each value names the next required credential. Each branch validates DIFFERENT credentials against DIFFERENT backends — treat each branch as its own auth surface.

## Technique: rate-limit brute test (reusable)
For any code-exchange/token endpoint: 15–20 rapid POSTs with garbage codes in a shell loop, collect `-w "%{http_code}"`. All 401/400 with zero 429 = brute surface open. Confirm uniform error strings (no oracle), note entropy/TTL as the unknown.

## SupaBomb / JWT forge attempt (2026-10-03, all dead)
- alg:none → `signing method none is invalid`; tampered-payload-same-sig → rejected; **HS256 forge with anon-key-as-secret** (the textbook Supabase confusion — the anon key is itself an HS256 JWT with `role:anon`, signed with the same secret class that signs access tokens) → rejected on GoTrue AND PostgREST (`PGRST301 No suitable key or wrong key type` — PostgREST verifies with a different key, layered trust roots); jwk-header injection (CVE-2016-10555 style) → rejected; offline weak-secret crack of the known anon-key sig vs ~20 common secrets incl. default self-hosted `super-secret-jwt-token-with-at-least-32-characters-long` → no hit. GoTrue checks claims BEFORE signature (`missing sub claim` errors first). Offline crack against a known sig is free (zero requests) — always do it before any online probe.
- Supabase service-path sweep on the auth host: `/pg` 401 / `/pg/meta` 403 Kong-gated ("You cannot consume this service"); `/functions/v1/` 503 name-resolution; `/realtime/v1/websocket` 403 pre-handshake; `/storage/v1/bucket` → `[]` for anon, `POST /bucket/list` route 404; `/storage/v1/status` 200.
- **Stack-topography lesson**: PostgREST + storage + pg-meta + functions + realtime all lived on the AUTH host, NOT the api host. Probe every Supabase service path (`/rest/v1/`, `/storage/v1/`, `/pg`, `/pg/meta`, `/functions/v1/`, `/realtime/v1/`) on EVERY Kong-fronted auth host — topography varies per deployment.

## Negatives (logged, do not re-probe without redeploy)
- PostgREST RLS holds for anon: `profiles`+`chat_messages` return `[]`; column oracle works (42703 wrong column; 22P02 bad uuid = type confirmation) but rows gated. Other tables PGRST205. No public RPC (PGRST202).
- Email-enum oracles dead: password grant 400 uniform, recover always 200 `{}`, alg:none JWT rejected, admin API 403 `not_admin`.
- SMS OTP dead server-side (`500 Unable to get SMS provider`) — no SMS-pump vector. Email signup rate-limited (~60s).
- Realtime WS: handshake returns 401 BEFORE frame exchange (stronger gate than the CDN-passthrough 101 pattern).
- `/api/*` routes exist only on chat+platform hosts; api.gratisfy.xyz only serves `/v1/*` OpenAI-compat (nginx 404 text/html elsewhere — different origin stack; note the split).

## Ledger
`~/.hermes/scripts/holyleadger/gratisfy.xyz.json`: 18 entries — 10 confirmed / 1 hypothesis / 7 negative. Top: gotrue_redirect_uri_full_override(85), chat_auth_mode_split(65,hypothesis), handoff_code_bruteforce(55), oauth_token_code_bruteforce(50), verify_otp_bruteforce(45), signup_unconfirmed_row(40).
**Chain recorded**: `signup_unconfirmed_row → gotrue_redirect_uri_full_override → handoff_code_bruteforce → account takeover` (status hypothesis, 3 steps) — the first full kill-chain entry on this target. `holyleadger chain <jewel> "A→B→C:impact"` syntax; steps split on `→`.

## Wall
Proving the handoff-brute chain or platform_key split needs ONE real authenticated session (capture live handoff code + real API key). Doctrine: ask the operator, never bootstrap.

## Next-session entry points
- Bundle hashes (2026-10-03): main B6Fhk0_W, siteRouting BaxhyiW5, chat DiezdlP6, platform D9-WxdCi, sse C_n6QzEY, api Cyn6IDlf, firstPartyOidc CY_Rj2cE — hash-diff before re-probing.
- If redeployed: re-run authorize redirect_uri probe + all three brute bursts (handoff/oauth-token/verify OTP) + auth-mode split chain.
- Browser leg pending: Discord authorize page acceptance of evil.com redirect (needs operator-supervised Discord login).

## Ops pitfalls hit these sessions
- **holyleadger.py path drift**: SKILL.md cites scripts/holyleadger.py but the active profile's skill dir didn't have it — real file at `~/holyshit-mode/scripts/holyleadger.py`. Verify referenced scripts exist in the ACTIVE skill dir before relying on them (bit twice).
- **holyleadger CLI grammar**: `add <class_id> <status> --target T --score N --technique "..."` — BOTH class_id and status are positional, status SECOND (e.g. `add hypothesis hypothesis --target gratisfy.xyz --score 65 --technique "..."`). Omit positional status → `the following arguments are required: status`, exit 2, entry silently never lands (exit code is the only signal). Statuses lowercase only: confirmed|negative|hypothesis|inconclusive; requires `--target` or `export HOLYSHIT_TARGET`. BLOCKED/RE-VERIFY aren't valid statuses — map BLOCKED→negative. (Bit twice: gratisfy 10-04, iceposeidon 10-20 — check exit code, not stdout.)
- **Asset fetch variant-host trap**: the `www.gratisfy.xyz` variant of an asset URL 404'd silently while apex `gratisfy.xyz` served it — `-o` created an empty file and grep read garbage. Always `-w "%{http_code} %{size_download}"` on every chunk fetch to catch silent 404/empty bodies.
