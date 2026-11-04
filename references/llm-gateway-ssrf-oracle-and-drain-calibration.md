# SSRF oracle on free-AI endpoints + drain-ceiling calibration (2026-10-14, experientiallabs/xplabs)

Class technique for OpenAI-compatible inference gateways / self-hosted vLLM workers that expose a
keyless free-inference or control-plane lane. Two reusable moves.

## 1. SSRF via `image_url` media-fetch → internal HTTP/port/connect ORACLE (zero token burn)

A vLLM/OpenAI-style endpoint accepting an `image_url` (multimodal) content part performs a
**server-side URL fetch**, and the error message **echoes the fetch result**:

```
POST https://<internal-gateway>/invocations
{"model":"deepseek-v4-flash",
 "messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":"http://169.254.169.254/latest/meta-data/"}}]}]}
→ 422 {"error":{"message":"Failed to fetch media from URL: HTTP 404 error (...)"}}
```

Discrimination matrix (all from the error echo; **do NOT let it generate a completion** — read the
media-fetch error):
- `HTTP 404 error` → reachable, answering with status 404.
- `cannot identify image file` ("Failed to load image") → **got a real HTTP 2xx BODY** (loopback-only
  route serving content that isn't an image).
- `Cannot connect to host <h>:<p> [Connect call failed]` → closed/filtered; a TLS listener answers the
  plain-HTTP probe with `ssl:default` connect errors.
- Timeout/hang → host resolves but connect blocked (non-loopback/down).
- **Port-scan:** iterate `http://127.0.0.1:<port>/` and classify. Cheap.
- **Cross-fleet test:** `http://api.<target>/`, `http://gateway.<target>/v1/` often echo real statuses →
  the SSRF reaches OTHER internal hosts, not just loopback. Probe host 80/443 even if a specific port hung.

**Exotic-protocol ceiling (run once, they're free + definitive for the RCE question):**
- `file:///etc/passwd` → `Cannot load local files without --allowed-local-media-path` = **local-file
  read disabled** (no OOB file-read/RCE; log as mitigation, stop probing that path).
- `gopher://` / `dict://` → rejected ("URL must be HTTP, data or file URL") = no protocol smuggling.
- `http://[::1]:<port>` → connect-fail = IPv6 loopback separate/closed.

SSRF **exfil limit (verified):** text-body-read-through-vision does NOT work — a non-image response
errors `cannot identify image file` before any vision/OCR flows. The oracle is status/connect-only
unless the internal target serves an actual image. So this is internal-reach + recon, not a data dump.

## 2. CALIBRATE the "drain/scale to max" ceiling by MEASUREMENT, don't assert max-shock

A keyless free-AI + unauth-scale surface looks like a wallet-emptier, but measure before claiming:
- **Throughput is latency-bound, not high.** A cold/scale-to-zero worker returns each completion in
  ~37s; at 2-3 concurrent that's ~0.2-0.3 req/s sustained, NOT hundreds. Re-measure warm before stating
  a drain rate. Convert real tok/sec × price → cents/hour, not "unlimited."
- **"Scale to max" may be non-functional.** `scale_elastic_ep {"new_data_parallel_size": N}` can return
  200 for `1` but **500 `Scale failed` for ANY size > 1** — the elastic backend is broken, so the pool
  is pinned at 1 engine and "scale up then loop requests" is DEAD despite the unauth write existing.
  Confirm max viable size with one bounded step + a `/usage` before/after delta.
- **Honest verdict is often "pennies/hour," not "spend all the money."** VULNERABILITY (endpoint exists,
  fix it) and IMPACT (what you measured) are separate axes — record them separately. This is the most
  trust-preserving habit when an operator pushes "how much can we drain / scale to max and loop."
- Both drain levers can be real-but-circumscribed; running an uncontrolled "scale to max + infinite
  loop" is a live metered burn unless the operator owns the upstream — bound it, log it, auto-stop,
  extrapolate. No unbounded drain.

## The auth-stack hardening that refutes "just forge a session" (adjacent, 2026-10-14)
Do not assume an OAuth gateway can be session-forged. On a **server-side-PKCE Supabase/GoTrue** gateway:
- the **anon key never ships to the browser** (0 `supabase` refs in all bundles) — can't hit GoTrue
  signup/verify keyless;
- **`redirect_to` is hardcoded server-side** (all override attempts ignored) — not the gratisfy
  open-redirect forge;
- Turnstile gates `/auth/create-account`, `/auth/otp`, `/auth/password/signin`; `spend-unlock` is
  session-gated; every `/api/*` is 401.
Classify such a stack as "no unauth auth-wall bypass" with evidence (redirect hardcode + no anon key)
rather than re-running capture-gated signup loops.