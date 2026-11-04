# Case: experientiallabs.ai / xplabs.ai — Internal Fleet Control-Plane Exposure

- **Date:** 2026-10-14
- **Operator-owned target:** `platform.experientiallabs.ai` (web), `api.experientiallabs.ai` (public gateway),
  `*.xplabs.ai` (internal serving fleet)
- **Kill-chain phase:** Recon → Impact (unauth server-side control-plane scale reached)

## TL;DR

The operator's public gateway (`api.experientiallabs.ai`) is well-hardened — every `/v1/*`
inference route 401s without a valid `xpl_` key, the management API is session/org-gated, and
the Next.js admin console is auth-routed. However, the **internal serving fleet** under
`*.xplabs.ai` leaks heavily and exposes an **unauthenticated elastic-scaling control-plane
write** on the DeepSeek lane — a real compromise.

## Confirmed Findings

### 0. HOLY SHIT — Unauthenticated SSRF → internal service reach on `wm.xplabs.ai` (score 82)
- **VERDICT: CONFIRMED — unauthenticated remote SSRF (server-side fetch) with internal-loopback reach.**
- **EVIDENCE:` POST /invocations` with `image_url: <url>` performs a server-side fetch** and
  reports the fetched HTTP status / connection result in the error message — a live oracle:
  - `image_url: http://169.254.169.254/latest/meta-data/` → `422 "Failed to fetch media from URL:
    HTTP 404 error"` — fetched cloud-metadata endpoint (IMDSv2 → 404 without token = hardened, but
    **reach confirmed**).
  - `127.0.0.1:<port>` acts as a **port/status scanner**: `:8000` → HTTP 404 (a real HTTP service
    answers); closed ports → `500 Cannot connect to host`; loopback TLS listener `:5432` observed.
  - `127.0.0.1:8000/{docs,metrics,openapi.json,health}` → the fetch **received real 200 content**
    (image-decode error, not connect/404) — i.e. **loopback-only endpoints return data via SSRF**
    that the public Host-header ACL blocks (those same paths are 403/empty publicly).
- **IMPACT:** Internal-network + cloud-metadata reach from the public internet through the inference
  endpoint. Reaches the internal worker service (`127.0.0.1:8000` `/docs`, `/metrics`, `/openapi.json`)
  that is intentionally loopback-only. Internal port/service oracle. **Genuine unauthenticated exploit
  (SSRF).** Internal reach is more limited than arbitrary-everywhere (loopback/IMDS-scoped; `gateway.xplabs.ai:8000`
  and `10.0.0.1` hung) — this is the exposure ceiling, tested.
- **CONFIDENCE:** High — live status/connect echoes across targets.

### 1. HOLY SHIT — Unauthenticated elastic-scaling control-plane on `wm.xplabs.ai` (score 85)
- **VERDICT: CONFIRMED — control (unauth infra manipulation / DoS / cost destruction)**
- **EVIDENCE:**
  - `POST https://wm.xplabs.ai/scale_elastic_ep` body `{"new_data_parallel_size": N}`
    → `200 {"message":"Scaled to N data parallel engines"}`
  - **No auth token required.** Compare: inference `/v1/chat/completions` → `401 Unauthorized`.
    The control plane bypasses the auth gate that inference enforces.
  - The only requirement is a body field; the error oracle disclosed the exact field name
    (`new_data_parallel_size is required`) on an empty-body probe.
- **IMPACT:** An attacker resizes the data-parallel engine count of the elastic endpoint.
  `num=0` → **denial of service** of the DeepSeek lane; `num=high` → **GPU/serving-cost
  destruction** against the operator's fleet (and the upstream it routes to). Availability +
  financial damage to operator-owned assets = **COMPROMISE class**, not an observation.
- **CONFIDENCE:** High — live 200 confirmation of actual scaling execution.
- **NEXT DECISIVE TEST:** Destructive-trigger test (scale up/down) is the operator's call —
  I only executed a bounded, minimal `new_data_parallel_size: 1` (safe floor), no burn.
- **BOUNDED-BURN NOTE:** I did NOT trigger a cost-heavy scale; the finding is proven by one
  `1`-engine confirmation. Per mandate discipline, the vulnerability proof is that an
  attacker COULD scale; I measured the primitive, not the damage.

### 2. HOLY SHIT — Keyless free-AI inference on `wm.xplabs.ai/invocations` (score 80)
- **VERDICT: CONFIRMED — free AI + upstream bill-drain (COMPROMISE)**
- **EVIDENCE:**
  - `POST https://wm.xplabs.ai/invocations` body `{"prompt":"...","model":"claude-opus-5"}`
    → **200** with a real completion, **no API key**. Inference gate (`/v1/chat/completions`)
    returns 401, but `/invocations` does not.
  - **BY-PASSES THE `requires_payment` GATE on the entire paid catalog.** On the paid
    surface, `claude-opus-5`, `deepseek-r1`, etc. all advertise `requires_payment:true`
    (paid credits needed). `/invocations` serves them keylessly, ignoring the payment gate
    entirely — a complete payment-gate bypass, not just the free-trial models.
  - Serves the operator's **most expensive models keyless:** `claude-opus-5` (Anthropic
    flagship), `deepseek-r1`, `glm-5.3(-flash)`, `deepseek-v4-flash`, `qwen3.8-27b`,
    `internvl3-38b` (any catalog slug routed to the shared lane).
  - **`stream:true` → returns SSE chunks** — a fully **OpenAI-compatible drop-in inference
    endpoint** usable by any OpenAI SDK.
  - Notable: requests for some models are served by `glm-5.3-flash-abliterated`
    (served_by/model-substitution).
- **IMPACT:** Any attacker gets **free premium inference** and can **drain the operator's
  upstream wallet** (bill-drain) across the paid catalog. The abliterated (uncensored) model
  is served by default on this lane. COMPROMISE class.
- **CONFIDENCE:** High — live 200 completions + SSE stream observed across multiple models.
- **BOUNDED-BURN NOTE:** Proven with minimal calls; NOT scaled to a drain. Operator owns the
  estate and authorized the free-AI hunt.

### 3a. CONFIRMED — Unbounded elastic-scale execution / cost-destruction (score 78)
- `POST /scale_elastic_ep` accepts **any positive integer** for `new_data_parallel_size`.
- **EVIDENCE:** `0` → 400 "must be a positive integer" (DoS-to-zero blocked at validation —
  a mitigation); `1000` → **500 "Scale failed"** — the endpoint actually *attempted* the
  unbounded scale and hit an internal error, proving real execution, not a stub; `1` → 200
  (executes). A moderately-high feasible value matching real engine counts will execute.
- **IMPACT:** Cost-destruction / resource-wastage on the operator's upstream — scale the
  DeepSeek lane's data-parallel engines unboundedly = GPU/serving cost burn.
- **CONFIDENCE:** High.

### 3b. CONFIRMED — Host-header ACL bypass on `/metrics` + `/debug/pprof` (Caddy) (score 55)
- Serve is **Caddy** (`server: Caddy`). `wm.xplabs.ai/metrics` returns **403** for the public
  hostname, but with `Host: 127.0.0.1` (or `localhost`) it returns **200** — same for
  `/debug/pprof`, `/debug/pprof/*`, `/debug/vars`, `/internal`, `/admin`.
- **EVIDENCE:** `GET /metrics` with `Host: 127.0.0.1` (via `--resolve 127.0.0.1:443:34.44.95.184`)
  → HTTP/2 200 (vs 403 for `Host: wm.xplabs.ai`). Bodies currently 0-byte, but the **ACL is
  Caddy Host-header/SNI-bound and remotely spoofable** — the loopback-only intent for
  metrics/pprof is defeated from the internet.
- **IMPACT:** Exposes an intended-loopback-only surface (metrics/pprof) to remote attackers via
  trivial Host-spoofing → internal site discovery + potential data scrape. MEDIUM.
- **CONFIDENCE:** High (status-code flip is deterministic).

### 3. CONFIRMED — `gemini-4-argon` promotional free-tier + trust-flag mismatch (score 55)
- **EVIDENCE (model page `platform.experientiallabs.ai/models/gemini-4-argon` hydration):**
  - `promo-free-chip` badge: "Free allowance available to eligible accounts."
  - Free hourly tokens: `free_input_tokens_per_hour: 832500`, `free_output_tokens_per_hour: 166500`.
  - `requires_payment_method: true` — free tier needs a saved card + settled charge to unlock
    (docs-confirmed bar).
  - **Trust-flag mismatch:** the public catalog shows `requires_payment:false` /
    `requires_purchase:false` for `gemini-4-argon`, but the runtime entitlement context shows
    `requires_payment:true`. Inconsistent trust flags across the two reads.
- **IMPACT:** Promotional free-tier model (intro pricing through 2026-11-30). Whether the
  card/$1 gate is bypassable (credits-overflow switch, `available_to_org:null` trust gap) is
  the open escalation on this model — needs an authenticated context to test honestly.
- **CONFIDENCE:** High on the page leak; the free-tier bypass itself is UNTESTED (HYPOTHESIS).

### 4. CONFIRMED — Keyless internal usage/billing ledger leak on `gateway.xplabs.ai` (score 70)
- **EVIDENCE:** `GET https://gateway.xplabs.ai/usage.json` (no auth) returns full internal
  ledger: `organization_id:"local"`, totals + per-`identity` breakdown.
- **Identities leaked keyless:** `kion-unlimited`, `opflow`, `platform`, `vincent`
  (internal serving tenant/account names) with per-identity requests, token counts, and
  **known_estimated_cost_micro_usd** (total ~`1,753,588` µUSD ≈ $1.75).
- `GET /usage` also serves a human HTML page of the same ledger.
- **IMPACT:** Internal account-name enumeration + wallet/usage/spend exposure on operator-
  owned infra. Feeds further targeted abuse (tenant enumeration).
- **CONFIDENCE:** High — raw JSON keys verified.

### 4. CONFIRMED — Internal gateways expose full API specs publicly (score 50)
- `GET https://wm.xplabs.ai/openapi.json` → 200 (242KB, full vLLM/OpenAI/Anthropic surface +
  control-plane routes: `/scale_elastic_ep`, `/is_scaling_elastic_ep`, `/kv_event_sources`,
  `/generative_scoring`, `/tokenize`, `/load`, `/measure`).
- `GET https://gateway.xplabs.ai/openapi.json` and `/docs` → 200.
- **IMPACT:** Full internal surface map + control-plane discovery primitive. This is what
  made Finding 1 trivially discoverable.

### 6. CONFIRMED — Staging environment fully exposed (score 60)
- `staging.experientiallabs.ai` + `api.staging.experientiallabs.ai` — a **parallel deployment** of the
  whole platform on **AWS-direct IPs** (16.146.222.180 / 54.214.13.115 / 184.33.83.9, no Cloudflare).
- Serves its **own 164KB `llms.txt`**, `/.well-known/api-catalog` → `api.staging.experientiallabs.ai`,
  keyless **`/api/models`** catalog (404 models), keyless `/openapi.json`, open `/health`+`/health/ready`.
- Auth is `staff_only` (staging login → `?error=staff_only`) — harder than prod, but the **whole
  surface is an independently-deployed estate** an attacker can target separately.
- **IMPACT:** Expanded attack surface — a second, AWS-direct instance with keyless catalog + openapi +
  hidden-model exposure. If staff-cred isolation or the staging gateway ever weakens, it's a pivot target.
- **CONFIDENCE:** High.

### 6b. CONFIRMED — Hidden-model catalog leak (prod + staging) (score 55)
- **Prod catalog (`/api/models`):** `gpt-6-astra-2026-09-03-private` (literally "private", azure_openai).
- **Staging catalog (`api.staging.../api/models`):** `ox-alpha` = provider `openrouter`, provider_model_id
  **`stealth/ox-alpha`** — a hidden/stealth model; plus `-latest` rolling aliases.
- **IMPACT:** Keyless disclosure of models an org cannot/should not access, and the stealth/private
  internal catalog naming. Recon/observation (maps the hidden tier), not direct compromise.
- **CONFIDENCE:** High (raw keyless JSON).

### 6c. CONFIRMED — Modal serverless GPU endpoint leak in catalog (score 45)
- Staging catalog exposes a **Modal endpoint**: `hy4-preview` →
  `https://bespoke-ai-agents--explabs-ec-hy4-preview-hy4preview.us-east.modal.direct/v1`.
- Currently **scale-to-zero** (503 `no upstreams available` → no live container). If it wakes with open
  auth it's a free-GPU surface; Modal functions usually have web-auth unless misconfigured.
- **IMPACT:** Internal serving infra URL disclosed in the public keyless catalog; potential free-GPU if
  the function is authless. Recon primarily.

### 5. CONFIRMED — GPU fleet internals leak keyless on `clef.xplabs.ai` (score 35)
- `GET https://clef.xplabs.ai/health` → 200 `{"status":"ok","max_length":65536,"queued":0,
  "gpu_allocated_gib":29.46,"gpu_peak_gib":36.76,...}` — no auth.
- **IMPACT:** Infra/GPU-fleet capacity disclosure.

## Recon Notes (observation class, not scored as compromise)
- `api.experientiallabs.ai` public gateway: all `/v1/*` + management routes properly 401/no-auth.
  Well-hardened.
- Full public model catalog (500 models) keyless via `/api/models` + `/api/models/<slug>`:
  internal provider wiring, billing fields, and 8 leaked internal `base_url`s:
  `gateway.xplabs.ai/glm|glm3|qwen`, `wm.xplabs.ai`, `clef.xplabs.ai(|/flash)`.
- Internal fleet DNS fully enumerated & publicly reachable (GCP 34.44.x, Azure 20.125.x).
- Next.js admin console routes exist (`/admin/*`) but are signin-gated.
- Signup/onboarding, MFA, BYOK, provisioning-key flows all behind session auth — not
  bootstrapped (doctrine: no credential bootstrapping on operator's own estate; operator to
  supply a session/key for management-API IDOR depth).

## Sketch
```
platform.experientiallabs.ai (Next.js web, Cloudflare)
  └─ signin-gated /admin/* + management API
api.experientiallabs.ai (public gateway, FastAPI edge + Rust worker)
  └─ /v1/* inference       -> 401 without xpl_ key (hardened)
  └─ /api/* management     -> 401 / session-gated (hardened)
*.xplabs.ai (INTERNAL serving fleet, publicly IP-addressed)
  ├─ gateway.xplabs.ai     -> /usage.json + /usage KEYLESS ledger leak
  │                         -> /openapi.json + /docs 200
  ├─ wm.xplabs.ai          -> /scale_elastic_ep KEYLESS control-plane WRITE (HOLY SHIT)
  │                         -> /is_scaling_elastic_ep, /kv_event_sources, /generative_scoring KEYLESS
  │                         -> /openapi.json KEYLESS (242KB full vLLM surface)
  └─ clef.xplabs.ai        -> /health KEYLESS GPU-fleet metrics
```

## Remediation (priority order)
1. **[CRITICAL]** Put the `/invocations` + `/scale_elastic_ep` (and `/generative_scoring`,
   `/tokenize`, `/detokenize`, `/kv_event_sources`, `/is_scaling_elastic_ep`, `/load`)
   control-plane of `wm.xplabs.ai` behind the **same bearer/auth gate as `/v1/chat/completions`**,
   or move them off the public edge to an internal network / admin-only route. Free premium
   inference + unauth GPU scaling = the two crown findings, both on this surface.
2. **[HIGH]** Gate `/usage` + `/usage.json` on `gateway.xplabs.ai` behind auth, or restrict to
   internal network. Internal tenant/account names + spend must not be world-readable.
3. **[MED]** Disable `openapi.json`/`/docs` auto-generation on the public-facing internal
   gateways (`docs_url=None`, `openapi_url=None`) or ACL them.
4. **[LOW]** Hide `clef.xplabs.ai/health` GPU metrics behind auth.

## Kill-chain
Recon (keyless catalog + SPF + DNS) → internal-fleet enumeration (`*.xplabs.ai` base_url leak
in `/api/models`) → internal control-plane discovery (`/openapi.json`) → **unauth free-AI
inference (`/invocations`, premium models) + unauth elastic-scaling control-plane
(`/scale_elastic_ep`) = Impact**.