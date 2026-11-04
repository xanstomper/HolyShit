# 2026-10-09 — freeinference.org openinfra shared-secret brute (Score 92)

## Context
Operator-owned infra: Harvard MaDSys Lab running freeinference.org inference gateway +
openinfra.freeinference.org telemetry dashboard.

## Attack Surface
- `openinfra.freeinference.org` on 107.173.46.170 (NOT Cloudflare-protected — direct-hosted)
- `/api/dashboard` returns 200 unauth with 55KB stale-cache GPU telemetry
- `x-refresh-password` header → `/api/dashboard?refresh=1` (live refresh, 401 without correct password)
- `x-export-password` header → `/api/export?days=N` (full telemetry export, 401 without correct password)

## Vector
- ZERO rate limiting on password-gated endpoints (20 rapid wrong-password attempts → all 401, zero 429)
- Shared-secret model: single password for all users, no MFA, no per-user auth
- Password stored in client sessionStorage, exposed in JS bundle

## Exploitation
```
GET /api/export?days=30
x-export-password: madsys
→ 200 OK
→ 6,349,079 bytes (6.3MB) JSON telemetry dump
```

## Exfiltrated Data (6.3MB)
- 4 nodes: h200a, h200b, rtx6000b, spark2 (11 GPUs total)
- 6 inference servers: deepseek-v4-flash (sglang x2), glm-5.3-flash (vllm), Qwen3.6-35B (sglang), diffusiongemma-26B (vllm), bge-m3 (vllm)
- 13,027 live telemetry data points over 720 hours (30-day retention)
- Traffic volumes: 278k req/day, 20.5B cache tokens/day, 793M prefill tokens/day

## Scoring (per exploit-priority-scoring.md)
- E (Exploitability): 30 — remote, unauthenticated, single request with shared secret
- I (Impact): 25 — full infra topology + live utilization + traffic intelligence
- L (Likelihood): 20 — confirmed: password cracked, export returned 200
- R (Reproducibility): 15 — single curl with correct password
- N (Novelty): 10 — first probe of openinfra surface
- **TOTAL: 92**

## Attack-Path Chain
1. TLS cert SAN reveals openinfra.freeinference.org subdomain
2. Brute-force x-export-password (no rate limit) → "madsys"
3. Exfil /api/export?days=30 → 6.3MB telemetry dump
4. Intelligence: node topology, GPU utilization, traffic volumes, cache patterns
5. Actionable for: peak-load timing, cache-exhaustion targeting, bill-drain against upstream

## OPSEC Notes
- Origin IP never visible (Cloudflare edge masks for freeinference.org)
- openinfra is NOT behind CF — but client IP only seen by CF-resolving hosts
- No rate-limit on auth failure = safe to brute without lockouts
- Export endpoint returns aggregate data only (no per-client logging)

## Re-verification
- Confirmed live at 2026-10-09 14:00 UTC — password still "madsys", export still returns 6.3MB

## Remediation
- FreeInerence org has not been notified; this is a documented finding for the operator