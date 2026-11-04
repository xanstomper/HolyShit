# Case: rainbet.com — crypto casino (RBGAMING N.V. / Rain Group Ltd, Anjouan license)

Recon-led engagement from the Vermes VM vantage (Oracle DC, 92.5.99.31). No ownership claim,
no credentialed attempts against real accounts, no destructive action. Ephemeral burner wallet
generated in VM RAM only (`/dev/shm/.dkv/mm_key.json`).

## Stack fingerprint

- **Apex = Next.js (Turbopack)**, buildId `xtOWrPweZNz3HzPBUgdez`, 257 JS chunks (6.4 MB).
- **API = Express on DigitalOcean App Platform** (`x-powered-by: Express`, `x-do-app-origin`
  app GUIDs on responses). Two planes:
  - `api.rainbet.com` — direct API host, **CF bot-block (hard 403) for the DC vantage**, even
    real chromium navigation gets "Sorry, you have been blocked" (IP-reputation rule).
  - `services.rainbet.com` — **erpc gateway, same backend, OPEN with chrome-TLS impersonation**.
- **WAF = Cloudflare, TLS-fingerprint-keyed on the apex**: default curl/python JA3 → 403
  "Attention Required"; `curl-impersonate-chrome110` full header stack → 200. The block is NOT
  path-based on the apex (API paths 403 only with weak fingerprints).
- **Socket = `socket.rainbet.com`, engine.io EIO=4, websocket-only** (polling returns
  `{"code":0,"message":"Transport unknown"}`), **socket.io-msgpack-parser** (frames are
  msgpack `{type,data,nsp}` — text `40` frames are silently dropped).
- Locale SSR: `/en/*` pages carry `__NEXT_DATA__` pageProps (races, categories, feature flags).

## Findings (confirmed)

1. **Arbitrary cookie-toss gadget on the main domain — media.rainbet.com (score 80).**
   The page writes EVERY `?param` as a cookie `Domain=rainbet.com; Path=/; Max-Age=90d;
   SameSite=None; Secure` (≤25 params/visit). Reserved list = exact-match
   {session, sid, token, jwt, auth, csrf, xsrf, PHPSESSID, stag} — **misses the real session
   family `stel_token`/`stel_ssid`/`stel_acid`, the FingerprintJS `client-context`, and
   `referralCode`**. Verified live in chromium: `?testparam=hello123&client-context=1111...`
   both land in `document.cookie`. Any link to `media.rainbet.com/?<name>=<value>` = attacker
   cookie on the casino's origin for 90 days.
2. **Fingerprint hijack via the same gadget (score 70).** `client-context` =
   FingerprintJS Pro v4 visitorId (fpjscdn.net, region us). SPA: `if (cookie.get("client-context")) return;`
   — cookie present ⇒ fingerprint generation SKIPPED, attacker value adopted. Ban-evasion +
   risk-model poisoning primitive (`er_risk_level` exists server-side).
3. **Affiliate-attribution hijack (score 65).** `stag` cookie = the affiliate tag
   (`getAffiliateTag: () => cookie.get("stag")`), consumed at sign-up attribution.
   `clever.rainbet.com?stag=<tag>` tosses it for 7d (SameSite=None). media.rainbet.com
   FORCE-sets `stag=58916_6a29c69394efb819d8945edf` on every visitor (affiliate 58916 = their
   own ad pipeline default).
4. **Metamask auth open pre-auth (score 60).** `POST /v1/auth/metamask/initiate
   {address, stage:1}` → 201 `{success, hash:8-char}` with NO captcha/Turnstile. Verify =
   `POST /v1/auth/metamask/verify {address, localized_message, signature, stage:2}` (personal_sign
   over `localized_message + " " + hash`). Solana wallet auth shares the error family
   (`er_sol_signature_verification_failed`). Rate limit on the auth plane is IP-keyed and LONG
   (er_rate_limit 429 persisted >30 min after a probe burst — see runner).
5. **Unauth cross-user bet feeds (score 45).** socket namespaces `/recent-bets`,
   `/recent-wins`, `/recent-high-bets` stream to GUESTS: per-bet UUID, user UUID, masked
   username (4 chars + "…"), rank (e.g. platinum-ii), amounts/currency/multiplier, 32-char
   per-bet token (server-seed-family), game/provider slug. Anonymization is inconsistent —
   some items omit `u.i`/`u.n` entirely. `/player-bets` guest connect → CONNECT_ERROR
   `er_spectator_not_allowed`; `/chat` guest joins silently dropped. Connection gate:
   replica sockets (identical frames, same cookies) are closed ~1.2s after the first packet;
   frames injected onto the SPA's own trusted connection are processed normally.
6. **TLS-impersonation apex bypass (score 75, tradecraft).** The JA3-keyed block falls to
   curl-impersonate; the whole `/_next` asset tree + SSR + services plane become reachable.
7. **`/v1/public/active-races` 500 er_database_error** on services for all `type` params while
   SSR fetches the same data internally — routing/regression inconsistency.
8. **Public profile ID oracle (score 55).** `/v1/public/profile?id=<str>` — short strings/ints
   → `404 er_no_user_found`; arrays → `400 er_field_validation_id`; UUIDs rejected
   (`er_field_validation_id`). IDs ride `?user=` on the bets page. Real publicId format still
   unknown (feed UUIDs are NOT it).
9. **Internet-exposed AMQP: rbtmq-stg.rainbet.com (159.203.53.157) :5672** — protocol-header
   exchange leaks broker capabilities (publisher_confirms, exchange routing). Banner-level
   only per doctrine. Siblings rbtmq-preprod(-us) = port 22 only.
10. **Official mirror fleet: rainbet.com/.live/rainbet1.com/rainbet.us** ("the same account,
    balance, and history"). .live/.rainbet1 = managed challenge wall for the DC vantage;
    rainbet.us = geo-403 JS-redirect wall EXCEPT `/api/analytics/account-id` (401 leaks through).

## Walls (verified, not assumed)

- `staging`/`dashboard`/`ds`/`aiostaging` = Cloudflare Access walls.
- `slot-integrations.rainbet.com` = NestJS, `/docs` → CF Access; all guessed paths 404
  (real routing, "Cannot GET").
- `api.rainbet.com` + `staging-api` = IP-reputation hard block (even real chromium).
- Sign-up = Turnstile `secure_token` + edge managed challenge on the auth plane.
- `staging-mono`/`dev-mono` = AWS ELB (`awselb/2.0`) 504 — orphaned backends.
- Game verifier = fully client-side (no bet-lookup oracle).

## Ceiling verdict (2026-11-03 closeout of the autonomous phase)

- **Region block = absolute for the DE vantage.** 8 runner cycles: the wallet-verify returns
  `451 er_sign_up_region_block` for plain AND restricted variants; the `ssr-client-ip` /
  `country` / `region` SSR headers are IGNORED (region = CF-IPCountry-derived). Email signup =
  Turnstile + edge challenge. No session without a non-blocked egress or an operator session.
- **Socket auth = server-bound.** `/player-bets` connects with a client-asserted
  `x-public-id` (a victim's real 32-char id) are silently dropped from guest connections —
  the claim is derived from the session server-side. Opt-out (stats:0) is respected on both
  the profile and the history endpoints — the financial-dump finding was re-rated 70→55.
- Demo mode = preview-only for guests; no unauth game flow.
- DMARC `p=quarantine`, SPF `~all`, 25/50 historical subdomains clean-NXDOMAIN (no dangling
  CNAMEs, no takeovers); rbtmq droplets mid-decommission (DNS deleted, droplet alive by IP);
  `staging-mono` ELB orphaned.

**The "they'd feel it" finding = the toss+fingerprint combo**: FingerprintJS Pro (a paid
service) is defeated by a 40-byte URL param on their own media host — device-ban evasion +
attribution/affiliate hijack via any link. That is the headline of the disclosure package.

## Pending (the runner)

**CLOSED** — superseded by the ceiling verdict above. The session-dependent tests
(stel_token fixation verdict, wallet/vault/seeds surface, x-public-id socket join) remain
documented as the unlock list for a non-blocked vantage or an operator session.
