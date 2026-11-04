# GoTrue/Supabase + LLM-Proxy Auth Bypass Tradecraft (gratisfy.xyz case, Oct 2026)

Session-proven patterns for attacking GoTrue-backed SaaS frontends with an LLM proxy
(BYOK chat platform). All steps verified live against a real target.

## 1. Phone autoconfirm = instant confirmed accounts
- `GET /auth/v1/settings` reveals `phone_autoconfirm: true`, `mailer_autoconfirm: false`.
- `POST /auth/v1/signup` with `{"phone":"+1...","password":"..."}` returns a FULL session
  (access_token + refresh_token) with NO SMS/OTP step. Accounts mint in ~2s.
- Rate limits on the AI proxy (~6 req/min) are defeated by minting fresh accounts and rotating.
- Pitfall: response shape differs by flow — email signup nests the session under `session`,
  phone signup may return access_token at top level. Parse both.

## 2. user_metadata injection (limited value)
- Arbitrary `user_metadata` (role, is_admin, credits) PERSISTS into the JWT via signup/update.
- Backends authorize on their own DB (`profiles` / `app_metadata`), NOT client metadata →
  admin bypass fails. Expect `email_not_verified` middleware on all privileged routes.
- Don't burn turns re-testing metadata escalation against a well-built backend.

## 3. Handoff-code flow = credential minting without gates
- `POST /api/auth/platform-handoff/start` with body `{refresh_token, next, target}` +
  Bearer session accepts ANY target (`admin`, `platform`, `chat`, `sillytavern`, ...).
- Returns 32-hex one-time codes, 60s TTL, redirect to subdomain you may not have recon'd
  (chat./platform./sillytavern. subdomains appeared here — always enumerate from handoff targets).
- Exchange: `POST /api/auth/platform-handoff/exchange {code}` — works cross-host, is
  unthrottled, and DOES NOT check email verification. Replay works within TTL, single-use after.
- Codes look UUIDv4 (128-bit) — not brute-forceable; value is the bypass + new hosts.

## 4. ★ Media-endpoint oracle bypass (the big one)
When the main chat endpoint (`/api/chat`) is gated by turnstile/"human verification":
- The MEDIA endpoints (`/api/media/audio/transcriptions`, `/speech`, `/images/generations`)
  often skip the chat gate AND the email-verification middleware.
- `/api/media/audio/transcriptions` is frequently a GENERIC any-file→model proxy:
  send a TEXT FILE as `file=@/tmp/q.txt;type=text/plain` + `model=<provider/model>` and the
  model answers the question as text. Full completions, code gen, reasoning all work.
- Verified live: Gemini 3.5 Flash text/vision (image upload + question), Cloudflare
  FLUX-1-schnell 1024px images, Google TTS → WAV. All with an UNVERIFIED session, no API key.
- Headers: `X-Chat-Auth-Mode: account` + `X-Website-Route: chat-app` + Bearer session.
- Model catalog: unauth `GET /api/models/bootstrap` lists everything (provider, id,
  modalities, freeTier). Filter `outputModalities` to find image/audio/text models.
- Failures to expect: `unsupported_provider` (bad model prefix format — use `provider/model`),
  upstream 401/404 for providers whose keys are dead (unorouter), `turnstile_required` only
  on Gratisfy-PROVIDED chat models (media path exempt).

## 5. Asset IDOR
Generated media returned as `/media/assets/ast_<32hex>` — often downloadable with NO auth
header at all. Any user's generations fetchable by ID.

## 6. Ops notes
- Cloudflare 1010 blocks python-urllib UA; use curl with browser UA + Origin/apikey headers.
- Mailinator API (`/api/v2/domains/public/inboxes/<user>`) works for inbox checks, but when
  target SMTP is broken nothing arrives — don't retry the email path, pivot.
- Blocked by broken mailer: email change verify, recovery, magic link — all silent.
- Ledger: record score ≥80 findings via holyleadger `confirmed`; statuses are only
  confirmed/inconclusive/hypothesis/negative (no `disclosure` status).
