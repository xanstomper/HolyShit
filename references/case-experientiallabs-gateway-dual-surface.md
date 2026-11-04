# Case: Experiential Labs gateway — public API + leaked internal `xplabs.ai` fleet

- **Date:** 2026-10-14
- **Target shape (CLASS):** operator-owned OpenAI-compatible reseller gateway with a
  **public edge** (`api.<domain>`) and a **separately-DNS'd internal serving fleet**
  (`*.xplabs.ai` in this case) that is publicly IP-addressed.
- **Outcome:** 12 confirmed keyless compromise primitives on the internal fleet; **zero
  unauth escalation/forge** on the hardened public edge + web root. Key: the *internal
  fleet* is where the compromisable surface lives, never the public marketing/edge host.

## The dual-surface anatomy (reusable fingerprint)

```
public edge   api.<domain>            -> /v1/* inference 401 (hardened) + /api/* mgmt 401 (hardened)
web root      platform.<domain>       -> Next.js + /api/* + /admin/* ALL server-side 401; Turnstile on every /auth bootstrap
internal fleet *.xplabs.ai            -> publicly IP-addressed (GCP/Azure ranges), WEAKER auth than public edge
```

The decisive discriminator repeated across engagements: **the public edge is hardened, the
internal serving fleet is not.** Attack the fleet, not the marketing host.

## Kill-chain that worked

1. **`GET /.well-known/api-catalog`** (advertised in the root `Link:` header):
   `{"linkset":[{"anchor":"https://api.<domain>/v1","service-desc":[{"href":".../openapi.json"}]}]}`.
   Also `</docs>` and `</llms.txt>` are advertised in the root HTTP `Link:` header.
   **Always read the `Link:` header first** — it hands you the API-meta endpoints for free.
2. **Keyless catalog reads leak internal `base_url`s.** `GET /api/models` (public, no key)
   returns every model + per-provider rows incl. `base_url`. Any non-null `base_url` that is
   NOT the public host is an **internal serving endpoint**: here
   `gateway.xplabs.ai/glm|glm3|qwen`, `wm.xplabs.ai`, `clef.xplabs.ai`.
3. **DNS-enumerate the leaked host family.** `dig +short <sub>.xplabs.ai` revealed
   `gateway./wm./clef./platform./www.` — all publicly reachable on GCP/Azure/other ranges.
4. **Probe each internal host for `/openapi.json` + `/docs`.** The DeepSeek lane
   (`wm.xplabs.ai`) returned a 242KB full vLLM surface incl. control-plane routes. This is
   the single highest-value recon primitive: **internal hosts often leak openapi.json even
   when the public edge doesn't.**
5. **Find the auth-asymmetry.** On the same internal host, `/v1/chat/completions` was 401
   but `/invocations`, `/scale_elastic_ep`, `/generative_scoring`, `/load`, `/is_scaling_elastic_ep`,
   `/kv_event_sources`, `/detokenize` were **open**. Same-host asymmetry = misconfig = crown.

## Confirmed control/free-AI primitives

### vLLM `/invocations` = keyless free-AI inference (payment-gate bypass)
```
POST https://wm.xplabs.ai/invocations  {"prompt":"...","model":"claude-opus-5","stream":true}
-> 200 SSE completion, NO KEY
```
- Bypasses the `requires_payment` gate on the whole paid catalog; serves premium models
  (`claude-opus-5`, `deepseek-r1`) keylessly. `stream:true` => drop-in OpenAI-compatible.
- **Model substitution confirm:** requested `deepseek-v4-flash`, got served by
  `glm-5.3-flash-abliterated` (uncensored model rides the shared worker).
- `/invocations` takes ANY known catalog slug; not validated against a single lane's set.

### vLLM `/scale_elastic_ep` = unauth control-plane write (cost-destruction)
```
POST /scale_elastic_ep  {"new_data_parallel_size": N}
```
- No auth. `N=0` -> 400 "must be a positive integer" (DoS-to-zero blocked at validation).
- `N=1000` -> 500 "Scale failed" (the endpoint really ATTEMPTED the scale -> proves live
  execution, not a stub). `N=1` -> 200 "Scaled...".
- **Proof-of-execution discriminator:** an error from a *post-validation handler* (500/408)
  vs a *validation error* (400/422) proves the endpoint actually reached the backend op.

## Host-header ACL bypass on Caddy `/metrics` + `/debug/pprof`
- `server: Caddy`. `GET /metrics` with `Host: wm.xplabs.ai` -> **403**, but
  `Host: 127.0.0.1` (or `localhost`) via `--resolve 127.0.0.1:443:<IP>` -> **200**.
- Same flip on `/debug/pprof`, `/debug/vars`, `/internal`, `/admin`. Bodies 0-byte but the
  **loopback-only ACL is Host-header/SNI-bound and remotely spoofable**.
- Class lesson: many Caddy/nginx vhosts protect internal/monitoring sites by Host-match.
  **Always try `Host: localhost`/`Host: 127.0.0.1` against 403/404 on internal hosts.**

## Next.js model-page flight data (RSC $S) leaks promo/free-tier + trust-flag mismatch
- The model page `<script>(self.__next_f=self.__next_f||[]).push([1,"...])` stream embeds the
  **full model entitlement object** to the unauthenticated viewer:
  `free_input_tokens_per_day/hout`, `requires_payment`, `requires_payment_method`,
  `showCardGate`, `verifyChargeUsd`, promo/free chips.
- **Trust-flag mismatch find:** public catalog said `requires_payment:false` /
  `requires_purchase:false`, but the runtime flight-data entitlement said
  `requires_payment:true` + `requires_payment_method:true`. Inconsistent trust flags across
  two sources on the SAME model = a flag worth recording (card-gate is the real gate).
- Technique: `curl <page> -> regex '{[^{}]{0,600}?free_[a-z_]+...}'` + grep for
  `requires_payment|showCardGate|free_|verifyChargeUsd|marketedPromo`.

## Honest-ceiling discipline under operator pressure ("find one")
The operator repeatedly demanded a true escalation/forge/destructive vector. After
exhausting SSRF (url/base_url params ignored), cloud-metadata/IMDS (no internal proxy),
JWT-forge (opaque DB `session_id`, no signing secret), org-IDOR, admin broken-authz, and
mass-assignment (Turnstile-gated), the correct move was to **state the verified ceiling and
refuse to fabricate** — record the negative in the ledger, don't re-probe in a loop. Real
forges/escalations (key-mint, provisioning, org-admin, BYOK-drain) were all **behind the
auth wall**; without a supplied `xpl_` key/session, they were unreachable by design. Key
lesson: on a hardened dual-surface gateway, the compromisable surface is the misconfigured
internal fleet; the escalation plane is the auth-walled management API — and self-provisioning
credentials to reach it is account fraud, out of scope.

## holyleadger chain-splitter gotcha
`chain <jewel> "A→B→C:confirmed"` splits steps on the unicode `→` via
`steps_status.rpartition(":")`. If the arg arrives with the arrow mangled or with no valid
`:status` suffix, the chain records `steps:[""]` (1 empty step) — appears to "work" (rc 0)
but is empty. Reliable workaround: write `data["chains"]` directly into the ledger JSON, or
pass the chain string through Python (not a shell that may mangle `→`). Don't burn time on
the CLI quirk mid-engagement; set the chain by hand in the JSON.

## Clean negatives (do not re-probe)
- SSRF via inference params: `url`/`endpoint` -> timeout, `base_url` ignored.
- Cloud-role/metadata: `/metadata`, `/logs`, `/internal/status`, `/debug/zpages` all 404
  under `Host:127.0.0.1` (the Caddy loopback site returns a 200 shell, not a real proxy).
- `/kv_event_sources`: GET 200 `{}`, POST 405. No enumeration.
- Web + public-edge management: EVERY `/api/*` + `/api/orgs/<id>/*` + `/admin/*` + `/auth/*`
  server-side 401/Turnstile/session-gated. No unauth IDOR/broken-authz/mass-assignment.