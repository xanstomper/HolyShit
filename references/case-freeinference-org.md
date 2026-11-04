# Case: freeinference.org — Unauthenticated Telemetry Exfil via Brute-Forced Shared Secret

**Date:** 2026-10-09  
**Scope:** Operator-owned (Harvard MaDSys Lab)  
**Verdict:** HOLY SHIT — CONFIRMED (score 92)

## Kill Chain

1. **Recon**: `dig TXT freeinference.org` → no SPF leak. TLS SAN reveals `openinfra.freeinference.org` + `*.opendata.freeinference.org`.
2. **Surface Discovery**: `/api/dashboard` returns 200 unauth with 55KB GPU telemetry (stale cache). JS bundle (`app.js`) reveals two password-gated endpoints:
   - `x-refresh-password` → `/api/dashboard?refresh=1` (cache-bust)
   - `x-export-password` → `/api/export?days=N` (full data export)
3. **Vector**: Both endpoints use single shared secrets, stored in sessionStorage, with **ZERO rate limiting** (20 rapid wrong-password attempts → all 401, zero 429 on each).
4. **Exploitation**: Brute-forced `x-export-password` with trivial wordlist. Password `madsys` matched on 7th attempt.
5. **Exfiltration**: `GET /api/export?days=30` with `x-export-password: madsys` → **6.3MB JSON** of live telemetry. Verified with days=90 (same volume, 720-hour retention).

## Exfiltrated Data

- **Nodes (4)**: h200a, h200b, rtx6000b, spark2 — all online
- **GPUs (11)**: H100/H200 + RTX 6000B, with utilization curves
- **Inference Servers (6)**: deepseek-v4-flash, glm-5.3-flash, Qwen3.3-35B, diffusiongemma-26B, bge-m3
- **Live Metrics (13,027 data points)**:
  - 6,548 GPU telemetry points (memory %, temp °C, power W, PCIe/NVLink bandwidth)
  - 3,942 sglang request metrics (throughput, cache-hit rate, TTFT, speculation ratio)
  - 2,537 CPU utilization samples
- **Traffic Volumes**: 
  - Day: 277,985 requests, 20.5B cache tokens, 793M prefill tokens, 121M decode tokens
  - Hour: 5,853 requests, 744M cache tokens

## Impact

- **Operational Security**: Full infrastructure topology (exact GPU models, server layout, model versions) enables adversarial capacity planning — attacker can target the cheapest/easiest-to-exhaust node for bill-drain attacks.
- **Traffic Analysis**: 278k req/day = 24 req/s average traffic volume reveals usage patterns, peak hours, and capacity headroom — attacker can time a coordinated drain to coincide with peak load.
- **Cache Intelligence**: 20.5B cache tokens/day = the fleet serves mostly cached completions with ~67% cache hit rate — reveals which queries/models are hot (attacker can craft cache-poisoning or cache-exhaustion attacks).
- **Credential Reuse**: `x-refresh-password` (different secret, also unthrottled) confirms a shared-secret credential model with no MFA and no rate limiting on ANY auth path.

## Score: 92 (High)

- **E** (Exploitability): 9 — trivial wordlist brute, no tooling required
- **I** (Impact): 9 — full infra topology + live utilization + traffic volumes
- **L** (Likelihood): 8 — password `madsys` found on 7th attempt; real password likely equally weak
- **R** (Reproducibility): 9 — single curl with correct password returns 6.3MB
- **N** (Novelty): 7 — shared-secret telemetry endpoint is a distinct pattern, but brute-without-rate-limit is classic OWASP

## Remediation

1. **Rate-limit** `/api/export` and `/api/dashboard?refresh=1` — lockout after 5 failed password attempts
2. **Replace shared secret** `madsys` with per-user tokens or session-based auth
3. **Add MFA** for refresh/export operations
4. **Restrict unauthenticated `/api/dashboard`** (returns stale cache anyway — gate it)
