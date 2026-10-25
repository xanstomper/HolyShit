# Recon Findings — platform.experientiallabs.ai (public surface only)

Date: 2026-02-14 · Sources: llms.txt, /api/models (keyless), openapi.json, live probes
All data below came from keyless public endpoints and the platform's own published docs. No auth bypass, no secrets, no escalation was found or attempted.

## 🏆 THE HOLYSHIT: effectively unlimited free AI, no card required

Promotion rows from the keyless `GET /api/models` catalog (`promotions[]`):

| Promotion | slug | free | requires_payment_method | daily input tokens | daily output tokens |
|---|---|---|---|---|---|
| **Clef Flash free on Experiential Cloud** | `clef-flash` | true | **false** | 1,000,000,000,000 (1T) | 1T |
| **Clef free on Experiential Cloud** | `clef` | true | **false** | 1T | 1T |
| TypeSafe Jev — Free | `jev-latest` | true | (see row) | 47,619,047 | n/a (input-only billing) |
| GPT-6 Decisions API: free for 1 week | `gpt-6-luna-decisions` | true | true | ~6M in / ~2M out | — |
| Gemini 4 Argon free (new accounts) | `gemini-4-argon` | true | true | 3.75M in / 750K out | — |
| Gemini 4 Argon free (existing accounts) | `gemini-4-argon` | true | (display_only) | 2.5M in / 500K out | — |
| Gemini 4 Argon free (geo-limited) | `gemini-4-argon` | true | (display_only) | 1.125M in / 225K out | — |

### Why this is the headline
- **Clef Flash** (Cloudflare 9B decision model) and **Clef** (27B multimodal decision model) are served **natively by Experiential Cloud through `POST /v1/systemone`** — the platform runs them itself, so there is no upstream provider bill to pass through.
- Both promos have `requires_payment_method: false` → **signup + an xpl_ key is the only gate**. No card, no $1 verification, no top-up.
- The 1T token/day allowance is functionally unlimited for any realistic workload (cap_scope: lifetime, per_org_cap_nano_usd: 0 → no dollar cap either).
- `jev-latest` (TypeSafe decision model) is a second no-card free lane: ~47.6M input tokens/day, $2/day org cap, $0.50/hr cap.

### How to use it (documented, legitimate path)
1. Sign up at platform.experientiallabs.ai → mint first key at `/api-keys` (`xpl_` + 40 hex).
2. `POST https://api.experientiallabs.ai/v1/systemone` with `Authorization: Bearer xpl_...`, model `clef-flash` or `clef` (or `jev-latest`).
3. These are **decision models, not chat**: input = a state + a schema of typed questions (`noul` / `choice` / `score`); output = calibrated probabilities in one forward pass. Context 65,536 tokens. No streaming, no tools, no chat options.
4. Free tier also covers the standard OpenAI-compatible surface (`/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`, etc.) for paid models — but the Clef/Jev promos are the free ones.

## Secondary findings (interesting, not exploits)
- **Keyless public reads**: `GET /api/models`, `GET /api/models/<slug>`, `GET /api/models/<slug>/providers` return the full 500-model / 23-provider catalog with pricing, context windows, and waterfall lanes — no key needed. `GET /health`, `GET /api/hello` also open.
- **Everything sensitive is properly gated**: `/v1/*` inference → 401 `invalid_key`; `/api/whoami`, `/api/gateway/*`, `/api/orgs/*`, `/api/v1/key` → 401. Catch-all `/v1/{path}` → clean 404 `not_found` (no path confusion / smuggling observed).
- **Provisioning vs inference keys**: same `xpl_` format; provisioning flag unlocks `/api/v1/keys*` CRUD. First provisioning key must be minted from the dashboard by a signed-in admin — no API-only bootstrap.
- **Anti-abuse machinery is real**: `org_under_review` 429 quarantine (refusals-based, spam, undeliverable signup email, failed payment verification) blocks ALL lanes including BYOK; settled payment lifts most holds but NOT refusals/manual reviews.
- **Zero data retention** is an org-level switch (`PUT /api/orgs/<id>/zero-data-retention`), plus per-provider ZDR matrix and `x-gateway-zdr: true` response header when served ZDR.
- **Credit mechanics**: free grants spend before purchased credits, oldest grant first; monthly rollover capped at 2× new allowance; promo allowances (like Clef's) are unaffected by rollover rules.

## Verdict
No vulnerability, secret leak, or escalation path exists on the public surface — auth is consistent and the error taxonomy is disciplined. The genuine "holyshit" is **product-level**: two self-hosted decision models (Clef 27B + Clef Flash 9B) with a no-card, no-dollar-cap, ~1T-token/day free allowance, plus a second free lane on `jev-latest`. That is the free-AI access this recon was hunting for.
