# Case: atessa.top — 2026-10-06 (pre-auth closeout + key-plane pass)

Operator-claimed LLM API gateway (uvicorn + Caddy, DIRECT IP 162.250.191.236 — Cloudflare DNS only, no CDN/WAF). React SPA + FastAPI.

## The dual-route decoy (biggest time sink — learn it)
- Bare paths (`/auth/login`, `/vouchers/redeem`) 422 with `"input":null` on EVERY field despite valid JSON = SPA-fallback router where the body never reaches Pydantic. Looks like "captcha strips the body" — it isn't.
- Real API lives under `/api/*`: `/api/auth/login` → `CAPTCHA verification required`; `/api/auth/signup` 422 echoes `input:{...your body...}` back.
- **Rule:** any 422 with `input:null` on all fields → immediately re-probe the same path under `/api` + `/api/v1` prefixes.

## Confirmed findings
1. **Pre-auth routing-table oracle (45):** unauth `POST /v1/chat/completions` — AUTH-GATED set (401) = live routes: claude-sonnet-4-6, claude-opus-4-6/4-7/4-8, claude-haiku-4-5-20251001, mai-voice-2, whisper-large-v3-turbo; all others → 503 `No providers available` (auth NEVER checked). Dumps live provider config pre-auth; any future non-gated provider addition is reachable unauth until auth-order is fixed. Whitespace suffix (`"claude-sonnet-4-6 "`) dodged the exact-match gate for some IDs.
2. **forgot-password unthrottled (40):** no captcha, no rate limit (36 rapid 200s @7.5ms), uniform response = no email enumeration but a mail-bomb pump on the target's sender reputation. `/api/auth/resend-verification` same (35).
3. **Public captcha-config:** `/api/public/captcha-config` → `{enabled:true, site_key:"0x4AAAAAADYnNDVbXy5fKK0H"}`. Found via lazy chunk `TurnstileWidget-D1hFjgeC.js` (chunks call public endpoints the main bundle never touches).
4. **count_tokens unthrottled CPU DoS (50):** `POST /v1/messages/count_tokens` (key-auth) — no rate limit (15-burst zero 429, 2.1s), no body-size cap (2.5M-token/5MB body → 200 `input_tokens: 2500003` in 3.27s), 10 parallel 1M-token bodies all processed (CPU-bound 7-10s each, returned 200). Tokenization endpoints are free CPU amplifiers: bounded-test big-body → burst → parallel on any gateway. Fix: per-key rate limit + server-side max input tokens.
5. **429-vs-401 key-validity discriminator:** exhausted key returns 429 `Quota and bonus credits exhausted. Resets 2026-10-07 00:00:00` — proves key live, leaks reset timestamp + quota model, costs nothing. Even 0×-weight "free" models quota-gated (hard enforcement, no bypass).

## Key-plane trust-root split (operator supplied live sk-proxy- key mid-session)
- Key opens `/v1/*` fully (30-model catalog incl. grok-4.7 family, kimi-k3, muse-spark, nano-banana-pro; Anthropic + Responses APIs both 429 at quota).
- ALL `/api/*` dashboard endpoints 401 on Bearer/X-Api-Key/X-Atessa-Key/X-Proxy-Key/raw-key variants — session-cookie-only. **No plane bleed** (good architecture). Lesson: when the operator hands an API key, first map WHICH plane it opens before planning the authed chain; say explicitly what still needs the session cookie.

## Negatives (do not re-probe w/o code change)
- Turnstile server-verified: bypass matrix (missing/empty/null/dummy/obj) all rejected; dummy → `Invalid CAPTCHA` ≠ `missing` = server verify confirmed cheaply.
- Google OAuth hardened: redirect_uri hardcoded (override ignored), state cookie-bound (cross-cookie callback → auth_failed). client_id `805021536698-smja1uiljue78kr2k3qfif15ki7iiitv`.
- Stripe webhook signature enforced (uniform 400 `Invalid signature` for empty/no-sig/bad-sig).
- CORS allow-list (`allow-credentials:true` present but no ACAO reflection for evil.com).
- Admin `/admin/login` SQLi negative, server-rendered form, French errors.
- SPA ghost shell (1583B HTML) everywhere outside `/api/*` + `/v1/*`.
- Reset/verify token endpoints: uniform `invalid or has expired` for garbage tokens.
- Public pricing/announcements/tutorials endpoints are data-only (pricing JSON leaks tier config + `slots_remaining` — observation, not compromise).

## Bundle-mining yield (the whole engagement came from here)
- Endpoint list via `grep -oE '"/[a-zA-Z0-9_/.-]{2,80}"'` — full app-plane map incl. wrapper call-sites (`QK(i,o,r)` = login(email,pw,captcha_token)).
- i18n strings → voucher format `GIFT-XXXXX-XXXXX-XXXXX`, feature inventory (affiliates, reseller RS keys, credit transfers, image library).
- Lazy chunks → `TurnstileWidget` → public captcha-config.
- No hardcoded secrets / backdoor IDs found.

## Wall
Signup + login captcha-gated server-side (operator declined account creation pre-auth; later supplied key). Remaining authed follow-ups needing a SESSION COOKIE: voucher brute (`/api/vouchers/redeem` + preview oracle), credit-transfer IDOR (`/user/transfer-credits`), key IDOR (`/user/keys/{id}`), reseller RS escalation, mass-assignment JWT persistence. Quota reset 2026-10-07 00:00 UTC gates completion-plane abuse tests.

## Ledger
`holyleadger/atessa.top.json` — confirmed: routing-oracle 45, count_tokens-DoS 50, forgot 40, resend 35, trust-split 30, quota-429 10; negatives: turnstile 20, oauth 15, stripe 15, cors 10, admin 10, ghosts 5; chain `preauth-routing-oracle` (hypothesis).
