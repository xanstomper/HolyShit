# Hardened-LLM-Gateway → Unauthenticated Internal Serving Fleet — Class Technique

Session-verified 2026-10-14 on experientiallabs.ai (public gateway `api.experientiallabs.ai`, internal
fleet `*.xplabs.ai`). Full case: `case-experientiallabs-ai.md`.

## When to use
A public OpenAI-compatible gateway / LLM platform is **professionally hardened** — every `/v1/*` and
`/api/*` route keyed, Turnstile on all bootstrap, opaque DB sessions, no JWT in bundles, no IDOR on the
pre-auth management API. The compromisable surface then often lives on the operator's **internal
serving fleet**, reachable because (a) it is publicly IP-addressed and (b) a worker-level proto surface
was left unauthenticated while the public edge is keyed.

## Stage 1 — Catalog leak reveals the fleet
- `GET /api/models` and `GET /api/models/<slug>` are commonly **keyless catalog reads**. Each model's
  provider rows carry `base_url`, `route_id`, `provider_connection_id`, `connection_alias`, region,
  `api_version`. **Diff these columns for non-null internal hosts.** On experientiallabs the
  `experiential_cloud` self-hosted lane leaked 8 real internal URLs:
  `gateway.xplabs.ai/glm|glm3|qwen`, `wm.xplabs.ai`, `clef.xplabs.ai(/flash)`.
- Resolve the leaked host family (DNS + crt.sh). These are usually on cloud provider IP ranges
  (GCP 34.44.x, Azure 20.125.x, 136.112.x) — publicly routable.
- Probe each internal host for **distinct auth behavior** vs the public host. The misconfigured one
  will answer unauth where the others 401.
- **Discriminator:** if `gateway.xplabs.ai`'s GLM/Qwen lanes return `401 Invalid API Key` but
  `wm.xplabs.ai` is open, it is a **deployment misconfiguration on one worker**, not platform-wide.

## Stage 2 — The unauth worker-level proto surface (the crown)
On a vLLM + Caddy internal gateway:
- **`/invocations` — keyless inference = free premium AI + payment-gate bypass + bill-drain.**
  `POST /invocations {"prompt":"...","model":"claude-opus-5","stream":true}` → 200 SSE completion, NO
  key, while `/v1/chat/completions` on the same host returns 401. Serves the whole paid catalog
  (`claude-opus-5`, `deepseek-r1`, glm/qwen/internvl) keylessly, **ignoring `requires_payment`** = a
  complete payment-gate bypass (verify by noting the paid surface advertises `requires_payment:true`).
  `stream:true` ⇒ drop-in OpenAI-SDK endpoint → free-AI / unlimited upstream bill-drain.
  Serve-mismatch: one requested model may be answered by another (`glm-5.3-flash-abliterated` for
  deepseek) — the uncensored model bypasses the content gate too.
- **`/scale_elastic_ep` — unauth control-plane write.** `POST {"new_data_parallel_size":N}` → 200
  "Scaled to N data parallel engines", no auth. `0` blocked (400 "positive integer") but **any
  positive int executes** (1000 → real 500 "Scale failed" proves unbounded execution attempt) =
  cost-destruction / GPU-burn. Control plane bypasses the auth gate that inference enforces.
- **`/usage.json` + `/usage` — keyless internal billing/tenant ledger.** Internal `identity` names
  (`platform`, `opflow`, `kion-unlimited`) + per-tenant token/cost (µUSD), world-readable.
- **`/openapi.json` + `/docs`** expose the full control/inference surface (`/generative_scoring`,
  `/tokenize`, `/detokenize`, `/load`, `/is_scaling_elastic_ep`, `/kv_event_sources`). Many answer
  validation-only 400 — **no auth, only a missing body field** (error oracles disclose the field).
- **Caddy `Host`-header ACL bypass on `/metrics`+`/debug/pprof`:** `server: Caddy`; `/metrics` 403 for
  the public hostname, but **200 with `Host: 127.0.0.1`/`localhost`** via `--resolve`. The loopback-only
  ACL is Host/SNI-bound and remotely spoofable.

## Honest ceiling
The worker pods are self-contained: no SSRF (`url`/`base_url`/`endpoint` params ignored or time out),
no IMDS/cloud-metadata reach, no `/v1/keys` mint, no RCE. Escalation to key-mint / org-admin / BYOK-secret
drain requires passing the auth wall (authenticated context). When the operator insists "there's
definitely a way past", re-probe the auth surface fresh; if genuinely hardened, record a **negative**
(`auth_wall_hardened_no_bypass`) and state the ceiling — never fabricate a forge or escalation.

## Hardened Auth-Wall Fingerprint (Supabase/GoTrue server-side PKCE) — does NOT inherit the weak variant
- Anon key is **not client-exposed**: OAuth `authorize` to `*.supabase.co/auth/v1/authorize` happens
  **server-side** (server initiates PKCE); zero `supabase`/`eyJ` anon-key in all fetched bundles. GoTrue
  `/auth/v1/*` keyless → `401 No API key found`.
- **`redirect_to` is hardcoded server-side**; override attempts (`https://evil`, `//evil`,
  `javascript:`, legit) are ignored. The gratisfy GoTrue redirect_uri-override forge does NOT apply.
  Fingerprint: `sb-<ref>-auth-token-code-verifier` PKCE cookie + `code_challenge_method=s256`.
- **Turnstile gates every bootstrap** (`/auth/otp`, `/auth/create-account`, `/auth/password/signin` →
  `captcha_failed` 403). Send an empty body to enumerate required fields before captcha blocks.
- **`/auth/spend-unlock`** (card-gate / $1-verify bypass route) is session-gated → `401 no_session`.
- Management API (`/api/orgs/<id>/usage/*`, `/api/keys`, `/api/admin/access`, `/api/account/mfa`)
  returns 401 server-side for every crafted org UUID/numeric id → no IDOR.

**Rule:** when the target is this well-hardened, the auth wall is NOT the vulnerability. State it
plainly, record the negative, pivot to (a) the internal-fleet proto surface above or (b) an
authenticated context from the operator.

## Contrast vs the vulnerable GoTrue variant (gratisfy/gonka)
The earlier findings (redirect_uri forwarded verbatim, anon key client-exposed, unthrottled code
exchange) come from an **un-hardened GoTrue deployment**. Always fingerprint BEFORE assuming: server-side
PKCE + no client anon key + hardcoded redirect_to ⇒ the gratisfy chain does not apply; pivot.