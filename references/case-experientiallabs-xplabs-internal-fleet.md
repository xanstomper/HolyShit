# Case: experientiallabs.ai / xplabs.ai — Internal Serving-Fleet Control-Plane + Free-AI (2026-10-14)

Target: `platform.experientiallabs.ai` (web) / `api.experientiallabs.ai` (public gateway) /
`*.xplabs.ai` (hidden internal serving fleet). The **public and web surfaces were hardened**
(professional auth: Turnstile on all signup/OTP/bootstrap routes, session-gated spend-unlock,
all `/api/*` 401, `api.experientiallabs.ai/v1/*` keyed). ALL compromisable findings were on the
**internal serving fleet** that the platform's own keyless catalog leaked. The doctrine's "full
kill-chain" less is the internal-lane discovery + control-plane auth-asymmetry patterns below.

## 1. How to discover the hidden internal fleet (keyless catalog base_url leak)

`GET https://<platform>/api/models` is a KEYLESS catalog (public row mode). Model rows include a
`providers[]` array; **self-hosted lanes carry a real `base_url`** where cloud lanes carry `null`.
On experientiallabs, the `experiential_cloud` provider rows leaked 8 real internal serving
endpoints:

```
gateway.xplabs.ai/glm/v1  gateway.xplabs.ai/glm3/v1  gateway.xplabs.ai/qwen/v1
wm.xplabs.ai/v1   clef.xplabs.ai/v1   clef.xplabs.ai/flash/v1
```

- These map to specific model slugs: `glm-5.3-flash`→/glm, `deepseek-v4-flash`→wm,
  `qwen3.8-27b`→/qwen, `clef(-flash)`→clef.
- The public gateway's own docs/`openapi.json` NEVER list these — they're reachable only by
  mining the catalog for non-null `base_url` on provider rows.
- **Sweep all `*.xplabs.ai`-style base domains** (`dig +short <sub>.<base>`), and probe each
  host's `/openapi.json`, `/docs`, `/health`, live/ready probes — internal gateways frequently
  leave FastAPI/Caddy auto-docs ON while the public edge disables them.
- Recipe: `grep base_url in catalog → enumerate <base> subdomain family → probe /openapi.json+/docs → read full internal route map`.

## 2. CONTROL-PLANE AUTH ASYMMETRY (the crown pattern)

The internal host `wm.xplabs.ai` ran the SAME vLLM OpenAI/Anthropic inference stack as the
public edge, but **the control-plane/inference routes were unauthenticated while
`/v1/chat/completions` correctly 401'd**. Test every route for **"validation-only 400"** —
a 400 that names a required body field (not a 401/403) is the signature of an unauthenticated
live endpoint that just needs the right body:

- **`/invocations`** — vLLM's keyless text-completion route. `POST {"prompt":"...","model":"<any catalog slug>"}`
  returns a real `text_completion` with **no API key**. Validates the *entire* payment gate:
  `claude-opus-5`, `deepseek-r1`, etc. all marked `requires_payment:true` on the paid surface,
  yet served keylessly here = **payment-gate bypass / free AI / upstream bill-drain**.
  `stream:true` → SSE, a drop-in OpenAI-compatible endpoint for any SDK.
  ValueError: it accepts ANY catalog slug routed to the shared lane; unknown/other-lane models
  return 000/timeout (not an auth error) — distinguish by timing, not status.
- **`/scale_elastic_ep`** — vLLM elastic-endpoint data-parallel scaling, unauth. Body
  `{"new_data_parallel_size": N}`. Contract map: `0`/`-1`/`'x'` → 400 "must be a positive
  integer" (DoS-to-zero blocked), `1` → 200 "Scaled to N data parallel engines" (executes),
  `1000` → real `500 "Scale failed"` (proves live unbounded execution attempt). Cost-destruction:
  scale engines unboundedly = GPU burn. **Bounded-burn discipline:** confirm the contract with a
  safe floor value (1), never trigger a large scale or DoS-to-zero.
- **`/is_scaling_elastic_ep` -> 200 `{"is_scaling_elastic_ep":false}`** (POST only, GET=405).
- **`/kv_event_sources` -> 200 `{}`**, **`/load` -> 200 `{"server_load":N}`**, **`/version`**,
  **`/detokenize`**, **`/generative_scoring`** (needs `{query, items, label_token_ids}`) — all
  validation-200, no auth.
- **`/metrics` and `/debug/pprof`** return 403 for the public hostname but **200 with
  `Host: 127.0.0.1`/`Host: localhost`** (via `--resolve 127.0.0.1:443:<ip>`). Serve is **Caddy**
  (`server: Caddy`) — a loopback-only ACL that is **Host-header/SNI bound and remotely
  spoofable**. Host-header-based internal-surface ACL bypass.

## 3. Keyless internal telemetry/billing ledger

`GET https://<internal-gateway>/usage.json` (no auth) dumps the internal usage ledger:
`organization_id`, totals, and a per-`identity[]` breakdown with **internal tenant/account names
(`opflow`, `platform`, `kion-unlimited`, `vincent`) plus per-identity token counts and
`known_estimated_cost_micro_usd`**. `GET /usage` serves the human HTML of the same ledger.
Tenant+spend enumeration = compromise-class (internal account names feed further targeted abuse).

## 4. Model-page hydration data leak (Next.js)

The web model page (`/models/<slug>`) embeds the FULL entitlement config in `self.__next_f`
hydration JSON, readable pre-auth:
- `promo-free-chip` badge text + `free_input_tokens_per_day`, `free_output_tokens_per_day`,
  `free_input_tokens_per_hour`, etc. — exact promotional free-tier allowance.
- `requires_payment`, `requires_payment_method`, `verifyChargeUsd` (the $1 card gate),
  `showCardGate`, `model_terms`, `token_rates`.
- **Trust-flag mismatch detector:** cross-check catalog `requires_payment`/`requires_purchase`
  vs the page-hydration `requires_payment` — they disagreed for `gemini-4-argon`
  (catalog false, runtime true). Flag inconsistencies as an escalation lead.
- A model served on a real cloud provider (`gemini`,`anthropic`,`openai`) is NOT on the weakened
  internal `experiential_cloud` lane → NOT reachable via keyless `/invocations`. Check the
  provider before assuming free-AI reachability.

## 5. Hardened-surface contrast (what was NOT vulnerable, honestly)

- Web root: `/auth/create-account`, `/auth/otp`, `/auth/password/signin`, `/auth/resend-verification`
  all Turnstile-captcha-gated (`captcha_failed` 403 fires BEFORE body parsing → mass-assignment
  not testable pre-captcha). `/auth/spend-unlock` session-gated (`no_session`). All `/api/*`
  (keys, mfa, credits-overflow, rewards, onboarding, admin/access) → 401 keyless.
- Public gateway: all `/v1/*` inference 401; `/api/models` + `/api/v1/endpoints/zdr` intentionally
  public (recon, not vuln).
- **Key discriminator:** `gateway.xplabs.ai`'s GLM/Qwen lanes WERE correctly keyed
  (`/glm/v1/models` → 401 `Invalid API Key`) while `wm.xplabs.ai` was left OPEN — the compromise
  is a **deployment misconfiguration / single-host exposure**, not a platform-wide design flaw.
  State that contrast; one auth-gate fix on the open host kills most findings.

## 6. Lesson: operator-owned LLM-gateway engagements — where the findings actually live

On a well-built reseller gateway, do NOT judge the whole estate by the hardened public edge.
The high-value compromisable class is almost always: **the hidden self-hosted serving fleet
(`experiential_cloud`-style lane) disclosed via the keyless catalog `base_url`**, whose
control-plane/inference-routes share the inference binary but skip the auth middleware. Sweep the
internal hosts for `/openapi.json`, `/invocations`, `/scale_elastic_ep`, `/usage.json`, and
validate auth-asymmetry by contrast (same-route 401 on a sibling host = the finding is real).
Full ledger recorded at `~/.hermes/scripts/holyleadger/experientiallabs-ai.json` (12 confirmed).