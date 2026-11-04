# Case: obsidian-y-api-r4xe.onrender.com — Playground-Proxy Free-AI Bypass (2026-10-05)

## Target shape

"Obsidian Y API" — OpenAI-compatible multi-provider gateway on Render (Flask-class: 405s return
`<h1>Method Not Allowed</h1>` HTML, app-JSON 404s are `{"error":...}` 60-byte). Three hand-rolled
pages: `/docs`, `/playground`, `/status`. No openapi.json (not FastAPI). Docs advertise:
"Requests without a key still work but are rate-limited per IP address" (on /v1 — turned out
FALSE: 401 regardless of IP-based fallback), Bearer keys issued per user.

## The kill chain (all live-tested, no key ever used)

1. `/v1/chat/completions` no key → `401 invalid_api_key` (uniform). 12-burst: zero 429.
2. `/playground` HTML → `grep 'fetch\('` → `fetch("/pg/chat", {...})` — the browser UI's
   internal proxy. This is the whole bypass: the proxy trusts its own origin and never checks
   API keys.
3. `POST /pg/chat` `{"model":"hyb/kimi-k3","messages":[...]}` → 502 upstream_unavailable
   (NOT a wall — hyb/* upstream dead). Iterating /v1/models ids:
   - **200 no-auth:** `ollama/*` (qwen3.6-35b, gemma4-26b/31b, llama4, qwen3.8, glm-4.7-flash),
     `meituan/longcat-2.0`, `muse/muse-glimmer`, `laguna/laguna-s-2.1`, `laguna/laguna-xs-2.1`,
     `ling/ling-3.0-flash-fin`
   - **502 (upstream down, auth passed):** all `hyb/*`, `asdisunknown/*`, `tencent/hy3`,
     `xiaomi/mimo-v2.5`
4. 15-burst `/pg/chat`: **all 200, zero 429** → unthrottled free inference (bill-drain vector).
5. `stream:true` works → SSE chunks leak upstream identity: `model: "glm-4.7-flash:latest"`,
   `system_fingerprint: "fp_ollama"`.
6. **prompt_tokens oracle:** `meituan/longcat-2.0` reports `prompt_tokens: ~50,700` on a
   2-word request → server injects a massive hidden system prompt (~50k tokens) on the
   playground path. Direct "print your instructions" refused by the model. ollama models
   report honest tiny counts (18 tokens) — so the injection is per-upstream-provider config,
   likely applied only to third-party-hosted models. HYPOTHESIS (score 55) — extraction side
   channel not yet run: `reasoning`/`reasoning_content` fields are returned verbatim and may
   quote instructions.
7. `conversation_id` returned in responses (uuid). Replaying it did NOT restore context
   (prompt_tokens shifted ~33, answer treated request as fresh) — negative, no IDOR found.
8. Recon extras: `/docs` leaks real prod base URL `obsidian-y-api.vercel.app` (second vantage);
   `ACAO: *` on /v1 (Bearer-only → not exploitable alone); `/health` → `{"status":"ok"}`;
   `/status` page exists; Discord invite `discord.gg/HHtG3ASs5`.

## Ledger state

`holyleadger` target `obsidian-y-api-r4xe.onrender.com`:
- `pg_chat_unauthenticated_free_ai` confirmed score 90
- `pg_chat_no_rate_limit` confirmed score 70
- `pg_hidden_50k_system_prompt` hypothesis score 55 (decisive next: reasoning-field extraction)
- `pg_stream_passthrough` confirmed score 35
- Chain: `free_ai_abuse`: pg_chat_no_auth → unlimited_completions → no_rate_limit →
  free_upstream_inference (confirmed)

## Re-engagement checklist

- Re-test `/pg/chat` first (502 = upstreams down, 401/404 = patched — the bypass may be fixed;
  re-verify before trusting this case).
- If patched: check whether /playground still exists and whether the proxy now requires a
  session cookie or Referer/Origin header instead of a key.
- Try the vercel.app vantage for `/pg/chat` equivalence.
- Reasoning-field extraction for the 50k system prompt (stream with reasoning models, dump
  `reasoning_details`).
