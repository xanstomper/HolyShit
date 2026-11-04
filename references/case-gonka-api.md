# Case: gonka-api.org — LLM-reseller Supabase stack (2026-10-06)

Operator-claimed upstream of the obsidian-y-api gateway (crypto-billing LLM
reseller "Easy GonkaAI API"). Full compromise-chain attempt: key-minting works
end-to-end; privilege escalation gated by correct RLS. Crown chain (75):
automated signup → free 20¢ `sk_` keys → resell/drain gonka inference.

## Stack fingerprint
- Frontend: Lovable.app SPA at `gonka-api.org` (mirror `cheap-ai-hub.lovable.app`,
  leaked by the GoTrue confirmation email's `redirect_to` param).
- Backend: Supabase project `hskyauefqcgbvgvxkluj`, GoTrue v2.197.0,
  PostgREST + Edge Functions.
- Anon key: HS256 JWT mined from `/assets/supabase-CXOtveJb.js`
  (`role:anon`, public-by-design, enables the whole recon ladder).

## Ghost-route trap → real API discovery
- `gonka-api.org/v1/*` returns the SPA HTML shell for every path (200
  text/html) — classic SPA fallback. Don't judge API existence by status.
- Real LLM API is a Supabase Edge Function, found via FAQ JSON-LD embedded in
  the main JS bundle: `https://<project>.supabase.co/functions/v1/gonka`
  ("Point any OpenAI-compatible client at ... and use your Easy GonkaAI key").
- Auth: `Authorization: Bearer sk_...`. Endpoints: `/v1/models` (3 models),
  `/v1/chat/completions` (real completions, `reasoning` field present),
  `/v1/credits` → leaks `{label, usage, limit, limit_remaining, balance}` per key.

## PostgREST recon (RLS-solid)
- `/rest/v1/` root → 401 service_role only; per-table anon reads still work.
- Existing tables: `api_keys`, `balances`, `transactions` — all `[]` to anon.
- 42703 column oracle: `api_keys(id,user_id,key,created_at)`,
  `balances(id,user_id,credits_cents)`, `transactions(id,user_id,type,created_at,description)`.
- RLS holds vs tautology `or=(key.neq.null)` / neq filters / `Prefer: count=exact`.
  IDOR by `id=` / `user_id=neq.` negative — scoping is on `auth.jwt()->>'sub'`.

## Mass-assignment: confirmed, NOT exploitable (gate re-confirmed)
- `/auth/v1/signup` `data:{role:"admin",is_admin:true,balance:999999,tier:"enterprise"}`
  persists VERBATIM into `user_metadata`, survives email confirmation into the
  verified JWT. `app_metadata` stays clean (GoTrue protects it).
- Gate: PostgREST RLS ignores `user_metadata`; edge-function billing reads real
  `balances.credits_cents` — a 2000-token completion deducted −0.002 from the
  20¢ balance. No backend authorizes on `user_metadata.role`. Score ~55
  hardening note, not a holy shit.

## Disposable-email filter bypass (discovery recipe)
- Signup enforces a 23514 CHECK constraint on email domain.
- Blocked: tempmail, guerrillamail, yopmail, 10minutemail, maildrop, getnada,
  dispostable, fakeinbox, trashmail, sharklasers, grr.la.
- MISSED (200): harakirimail.com, pokemail.net, spam4.me, bccto.me, chammy.info.
- Discovery: batch-signup one probe account per candidate domain, read
  200 vs 23514. A filter-list gap = automate account creation at scale.

## harakirimail public-inbox chain (mailinator blocked here)
- List: `GET https://harakirimail.com/api/v1/inbox/<name>` (metadata only).
- Full body: `GET https://harakirimail.com/api/v1/email/<_id>` (`bodyhtmltext`).
- Extract `token=([a-f0-9]{40,})` from the confirm link; consume ONCE.
- Confirm: `GET /auth/v1/verify?token=...&type=signup&email=...` → 303 with
  `#access_token` fragment. Take a stable session via password grant afterward.
- Bonus leak: the confirm email's `redirect_to` exposed the Lovable mirror host.

## Crown chain (confirmed live, score 75)
`disposable_signup → harakirimail_public_inbox_confirm → mint_sk_key →
20¢_free_credit → /functions/v1/gonka inference`. Operator's gateway routes to
gonka → scaled signups bleed the operator's upstream supply chain.

## Negatives logged
19 admin/secret path probes on the edge function → all 404 (no admin panel, no
key-management endpoint). `/v1/credits` is the only metadata leak.

## Cross-ref: same reseller class, different stack (apimart.ai, 2026-10-06)
apimart.ai = the OneAPI/new-api variant of the sketchy-reseller class (SEO-spam
botnet on GitHub, `x-oneapi-request-id` fingerprint, 309 models). Full recipe +
route-mining method: `references/case-apimart-newapi-fork.md`. Use both files
together when engaging this class — Supabase/Lovable stack vs Go/OneAPI fork
have different recon ladders (chunk-mining + upstream-source reading vs
PostgREST oracles).
