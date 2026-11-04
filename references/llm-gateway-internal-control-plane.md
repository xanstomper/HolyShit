# LLM-Gateway Internal-Fleet Control-Plane Exploitation

Class-level playbook for a recurring finding shape: an OpenAI-compatible LLM gateway's
**public inference surface is keyed (401), but its internal serving fleet exposes an
UNAUTHENTICATED control plane** — free inference via a vLLM `/invocations` route, an
elastic-scaling write, and monitoring/metrics ACLs keyed on spoofable Host headers.

Session-verified 2026-10-14 against `experientiallabs.ai` / `xplabs.ai` (operator-owned).

## Surface-discovery pattern (recon to impact in ~6 moves)

1. **Grab `/llms.txt` + `/.well-known/api-catalog` first.** These are linked from the HTTP
   `Link:` headers and often carry the full API contract: base URL, the management-API split
   (`/v1` inference vs `/api` management), key format (`xpl_` + 40 hex), and the fact that
   "one key reaches both surfaces but CANNOT mint keys / reach admin." This map precedes ANY
   targeted probe.
2. **`/api/models` (the management catalog) is often keyless** even when `/v1/models`
   (the OpenAI-compatible list) requires a key — the docs spell this split out. `GET /api/models`
   keyless leaks the **entire catalog**: every model, its provider rows, billing fields, AND the
   **internal `base_url` of each routing lane** (e.g. `wm.xplabs.ai/v1`, `gateway.xplabs.ai/qwen/v1`,
   `...us-east.modal.direct/v1`). Grep every provider row's `base_url` — that's the internal fleet.
3. **Enumerate `*.internal-tld` subdomains** (crt.sh + `socket.getaddrinfo` on a wordlist).
   The catalog base_urls reveal the fleet; confirm each host answers from the internet.
4. **Pull `/openapi.json` on every internal host.** The PUBLIC gateway often has none (or a
   relay stub), but internal serving gateways frequently ship the full spec — revealing
   control-plane routes (`/invocations`, `/scale_elastic_ep`, `/is_scaling_elastic_ep`,
   `/generative_scoring`, `/kv_event_sources`, `/load`, `/detokenize`, `/tokenize`) that the
   public surface never exposes.
5. **Probe auth-ASYMMETRY, not just presence.** Fire `/v1/chat/completions` (expect 401) THEN
   the control-plane routes with an empty/minimal body. The discriminator:
   - `401` = auth-gated (like inference).
   - `400` with a "field required" / **field name in the error** = NO AUTH — only body
     validation blocks execution. Supply the field and it executes. `{"new_data_parallel_size" is
     required"}` → send it → `200 "Scaled to N data parallel engines"`.
   - `404`/`000` = not on this host / model-not-on-lane.
6. **Verify the control-plane primitive ONCE with a bounded, non-destructive value**, then stop.
   For free-AI: one minimal `{"prompt":"Say OK","model":"<slug>"}` proves reachability; a
   `stream:true` probe proves OpenAI-SDK drop-in usability. For scaling: use the safe floor (1),
   NOT 0 (DoS) and NOT a huge number (cost burn). The `500 "Scale failed"` on a huge value is
   itself proof the endpoint really attempts the op (not a stub).

## The two crown compound findings

- **Free AI / payment-gate bypass.** A vLLM `/invocations` (or `/generate`, `/completions`)
  control-plane route that serves LLM completions keylessly while `/v1/chat/completions` is 401.
  It accepts ANY catalog slug routed to that lane (`claude-opus-5`, `deepseek-r1`, glm/qwen/...)
  — incl. models that advertise `requires_payment:true` on the paid surface → **payment-gate
  bypass**. `stream:true` → SSE = drop-in for any OpenAI SDK. This is COMPROMISE (upstream
  bill-drain + free premium inference), not an observation. The served_by model can differ from
  the requested one (model substitution), and an **abliterated** model may be served by default.
- **Unauthenticated infra write.** `/scale_elastic_ep`-style control plane lets an attacker
  resize the serving fleet's data-parallel engines: cost-destruction (scale up) or DoS (scale to
  0, if `0` isn't validation-blocked). Even when `0` → 400 "must be positive", unbounded positive
  scaling still executes.

## Caddy Host-header ACL bypass on monitoring/metrics

Internal gateways serve via Caddy. Monitoring paths (`/metrics`, `/debug/pprof*`, `/debug/vars`,
`/internal`, `/admin`) that return **403 for the public hostname** often flip to **200 with
`Host: 127.0.0.1`** (or `localhost`) — the loopback-only ACL is keyed on Host/SNI, not the
client IP, so it's spoofable remotely:

```
curl -k --resolve 127.0.0.1:443:<ip> -H 'Host: 127.0.0.1' https://127.0.0.1/metrics   # 403→200
```

`server: Caddy` in the response header confirms the stack. Note the 200 may be an empty shell
(0 bytes) if the real data binds to a different internal vhost — the status flip is still the
finding (defeats the loopback-only intent).

## Hardened-auth negatives (don't waste time — these are the STRONG parts)

When the platform's auth is well-built, the following are dead ends CONFIRMED live:
- **Supabase/GoTrue server-side PKCE**: OAuth forwards to `https://<proj>.supabase.co/auth/v1/
  authorize` **from the server**, and the **anon key NEVER ships to the browser** (zero refs in
  every JS chunk). You CANNOT reach `/auth/v1/settings`/signup/verify keyless. Don't hunt the
  anon key in the bundle — it isn't there.
- **`redirect_to` hardcoded server-side**: 4 override attempts (https://evil, //evil, javascript:,
  a legit URI) are all ignored; the authorize URL always carries the fixed
  `redirect_to=https://<app>/auth/callback?next=%2F`. NOT the GoTrue `redirect_uri`-forward flaw.
- **Turnstile on every bootstrap** (`/auth/otp`, `/auth/create-account`, `/auth/password/signin`
  → `captcha_failed`) and **opaque DB session cookies** (`session_id`, not a forgeable JWT).
  Staging may be even tighter (`?error=staff_only`).

## Staging / parallel-environment discovery

- Brute `*.domain` subdomains; a **staging host** is often AWS-direct (no Cloudflare; IP ranges
  like `16.x/54.x/3.x` = AWS) with its OWN `llms.txt`, `/.well-known/api-catalog`,
  keyless `openapi.json` + `/api/models` catalog, and a `api.staging.<domain>` gateway.
- Staging catalogs can expose MORE hidden internal infra than prod (Modal `*.modal.direct` GPU
  URLs, `stealth/<model>` hidden-tier names, `-private`/`-latest` slugs).
- Modal endpoints may be scale-to-zero (`503 no upstreams available`) — a waking function with
  open auth = free GPU, but usually Modal web-auth applies.

## Ledger grammar (from this run)
- `holyleadger chain` splits steps on the **unicode `→`**; keep the impact text free of arrows or
  you get 1 empty step. (Duplicated-chain files surfaced this run.)