# Case: duelbits.com — fleet topology, CMS token leak, and WAF vantage burn

Multi-brand React/Vite casino behind Cloudflare -> CloudFront -> S3. Recon-led engagement (no
ownership claim): map-first, no account creation, no credentialed attempts.

## Findings

1. **APIConfig chunk = the whole fleet topology** (`/assets/APIConfig-<hash>.js`). Per-brand
   domains ship `{token, auth, oAuth, websocket, gamesocket}` URLs: `/auth` + `/ws` + `/gs`
   on the main domain, with the OAUTH pointed at a SISTER BRAND (switchflips.com). Fleet:
   duelbits.com/.io/.net/.bet + sportsbits.com + switchflips.com. Grep every fetched chunk
   for a config-by-name chunk (`APIConfig-*`, `env-*`) before probing blind — the topology
   comes free.
2. **Internal env naming in the config**: `dev.r19.ea.duelbits.(com|io)` and a
   `deploy-preview-N.r19.ea.duelbits.(com|io)` regex = live Netlify preview routes.
   Enumerate `deploy-preview-<N>` as live internal surfaces.
3. **Compiled env chunk leaks** (`env-*.js`): Contentful delivery token + space id +
   `VITE_CONTENTFUL_ENVIRONMENT: release-candidate` — PROD PULLS STAGING CMS CONTENT. The
   delivery token works live: 13k entries, 123 types (rewardConfiguration x1547,
   countryRestrictions with dev leftovers, telegramUser config). Marketing-class only; a
   delivery token is semi-public by design, so rate the RC-on-prod as the finding, not the
   token.
4. **NestJS fingerprint**: errors are `{statusCode, code:'general.NotFound'}` — a JSON 404
   under `/auth/*` = REAL routing with wrong subpaths (vs the SPA shell 200 text/html =
   ghost). Fingerprint the error format before declaring an endpoint dead.
5. **`/ws/config/currencies` = 200 unauth** while `/ws/config` = 403 — per-path WAF rules;
   sweep siblings of any open config endpoint.
6. **Web3-wallet-only auth chain (the whole login surface):** there is NO email/password
   auth — the SPA's `web3-sign-in-*.js` chunk ships the full flow: (1) `POST
   /auth/web3/message/?publicAddress=<addr>` returns the sign-message; (2) the wallet signs
   via `personal_sign`; (3) `POST /auth/web3` body `{address, signature, ...state}` returns
   the session token. Three queued vectors, each one fetch from a page context: **nonce
   replay** (call the message endpoint twice for one address — identical message = one
   captured signature is a permanent login), **address-registration oracle** (verify-endpoint
   error differences for registered vs unregistered wallets), and **state-param forwarding**
   (the client forwards arbitrary URL state params into the auth POST body = mass-assignment
   injection point). All WAF-blocked from the burned vantage — hand the live tests to the
   operator's console (kit below).
   LIVE CHALLENGE FORMAT: the sign-message is a FLAT personal_sign utf8 string — "You are
   authenticating on <brand> using address <addr>. Do not share this message with anyone!
   <nonce>" — NO timestamp, NO expiry, NO domain binding, 6-digit numeric nonce (one sample).
   The signed credential therefore has NO intrinsic time bound; replay protection is purely
   the server's nonce-consumption policy, and every absent binding field is itself an audit
   finding.
   Console handoff kit (ordered by decisiveness, all self-account, non-destructive):
   1. Signature replay — Network tab → the login's `POST /auth/web3` → Copy as fetch → run
      TWICE. Copy-as-fetch preserves the client's real headers = byte-faithful replay. Both
      200 = one captured signature is a reusable login; nonce-error on the 2nd = single-use.
   2. Signature↔address binding swap — same body with a random address. Accepted = no
      binding = total auth bypass; expect rejection (that IS the test).
   3. Challenge determinism — message endpoint ×3 same address: identical = static challenge;
      rotating = sequence-check the trailing nonce for counter/timestamp derivation.
   4. Registration oracle — message endpoint for the operator's address vs a fresh random
      one; different status/shape = wallet-existence enumeration oracle.
   5. State-param forwarding — replay body + extra keys (role/is_admin/balance/vipLevel) and
      `?isAdmin=true`, then reload and diff the user/me endpoint for anything that stuck.
   Handoff hygiene: instruct the operator NOT to paste the minted session token back —
   statuses and error bodies only.
7. **One CMS delivery token read FOUR environments** (master, release-candidate, staging,
   development) — the token is space-scoped, not env-scoped. The development env held MORE
   entries than master, with dev-test leftovers dated the day before recon. Enumerate
   `<env>` in the Contentful URL for every env name you can guess; the staging/development
   layers are where drafts and internal tests live.

## WAF vantage burn and recovery (the reusable recipe)

- Aggressive CF configs flag a scripted vantage MID-ROUND: the same path alternates 200/403,
  then every path turnstile-challenges — including hosts that were open an hour earlier and
  even a real-browser harness (managed challenge, not auto-passing). Budget for it; the burn
  is not a wall on the TARGET, it is a wall on YOUR VANTAGE.
- **The burn persists across days and spreads across the brand family.** Host differentials
  recorded pre-burn DECAY: before trusting any "this sibling was unchallenged" note, spend ONE
  navigation re-verifying it — do not re-probe per host. A challenged nav (title "Just a
  moment…") also poisons every in-page fetch: XHR fails with a NetworkError that masquerades
  as a different bug. Check the page title before running in-page probes, and never use the
  CDP browser as burn recovery — on a burned IP the managed challenge does not auto-pass for
  it either; the only clean vantage left is the operator's own logged-in console.
- Recovery pivots that worked, in order:
  1. **Find one unchallenged path** — SPA fallbacks often exempt utility paths
     (`/.well-known/openid-configuration` served the full 78KB SPA shell unchallenged). The
     shell carries the complete asset list: 200+ chunk names incl. the config chunks.
  2. **Wayback CDX index** (`web.archive.org/cdx/search/cdx?url=<domain>/*&output=json&collapse=urlkey`)
     = the captured-URL inventory without touching the live WAF. Reveals endpoint names the
     live site hides (the OIDC path) and the asset history. The availability API and direct
     page fetches rate-limit (429) fast — the CDX query is the one that pays.
  3. **crt.sh for the subdomain fleet** (64 hosts here) when the live surface is walled —
     CT logs never trip the WAF.
  4. web_extract as a different egress for archive pages.
- Dev-tier subdomains (admin-dev, admin-staging, chadmin-*, chad-api-*, auth/wallet/pay/gs/ws
  dev+staging) were CT-visible but challenge/Access-walled — log the fleet map as coverage
  and say what a clean vantage or session unlocks.

## Negatives
- `ephemeral.duelbits.com` = bare nginx default-404 vhost, nothing routed.
- No unauth data plane found before the burn (unlike duel): bet feeds sit behind auth + WAF.
- CMS content = marketing copy/economics, no PII, read-only delivery API.

## 2026-11-02 re-engage (Vermes VM vantage): sockets, PF verification, region wall

Full client decode from the CURRENT build (`index-CW30_Dqt.js` era, rolldown-vite, 416 chunks):

- **Web3 flow verbatim** (`web3-sign-in-*.js`): `POST {domain.token}/web3/message/?publicAddress=<addr>`
  (no headers/body) → `.json().message`; `personal_sign([utf8ToHex(msg), addr])`; state =
  `JSON.parse(url.state||'{}')` through `Xb` = **pure passthrough, NO whitelist** → truthy keys
  become BOTH the auth URL query AND body spread: `POST {domain.token}/web3?${qs}` body
  `{address, signature, ...state}`; response must be `{access, refresh, user}`. APIConfig:
  prod oAuth = switchflips.com; **duelbits.bet config self-labels `duelbits.net`** (their bug).
- **`POST /auth/token?scope=X` mints RS256 JWTs UNAUTH for ANY scope** — sub=admin/mod/internal/
  system all sign (30s TTL, aud=duelbits.com, `id`=stable per-session hash). ws+gs sockets accept
  any sub. No privilege gate at mint; no admin channel in the public client.
- **`GET /ws/user/bets/live` = 200 UNAUTH cross-user feed** (all/large/lucky/wins): displayName,
  internal UUID, registered(ms), level, verified, authRole, bet/win/game. The /ws socket streams
  the same as `bet`/`win` events live (partial user:null anonymization). Config siblings 404;
  `/ws/config` clean.
- **PF verified CORRECT (high-coverage negative):** roulette daily seeds `sha256(seed)==hash`
  49/49 closed periods; crash seeds are a REVERSE chain (`sha256(seed[N+1])==seed[N]` 99/99 —
  safe direction, future = preimage). Live-period record bug: seed==hash in both fields until
  reveal (cosmetic/verification-flow bug, no prediction gain — derive outcomes from the real
  seed, published only after close).
- **Region wall proven, not assumed:** Oracle VM geolocates DE → `/auth/web3` 403 on every
  signature/casing/state variant (ws pushes `blocked:{reason:region_page,location:de}`); missing
  geo fields → unhandled 500 (geo preflight crashes pre-consumption). Dev/staging/canary auth
  APIs = CF Access. The queued replay/binding/mass-assignment tests REQUIRE a residential
  unrestricted vantage (operator browser). Challenge layer: rotates per fetch, zero validation
  (`zzzz` → 201), no cookies, no oracle at message layer.
- **Ops lessons:** /dev/shm is noexec on OL9 (venv on disk, artifacts in RAM tmpfs);
  WAF pacing 3.5-6.5s held on API paths while HTML paths challenge on partial headers — full
  spoof stack is mandatory; socket.io polling needs strict POST→single-long-GET alternation or
  the sid dies (`Session ID unknown`); kit = `~/holyshit-mode/scripts/duel_kit.py` (phases:
  vantage/bundle/determinism/oracle/auth/replay/binding/state_forward/postauth_oracle).

### 2026-11-02 exploit round: minted-Bearer bypass + room authz + full-spectrum sweep (all negative on compromise)

- **Minted-token bearer bypass: HELD.** `/ws/user/bets/my`, `/ws/games/keno/history`,
  `/ws/games/hilo/history`, `/ws/user/profile`, `/ws/user/transactions` all 403 with
  minted `sub=user/admin/mod/system` JWTs in EVERY delivery variant (Bearer, `?token=`,
  cookie). The /ws guard requires real wallet-login claims — the scope mint is inert on HTTP.
- **Room authz: HOLDS.** Real vocabulary: `user:bet`/`user:bonus`/`user:notification`/
  `user:update` personal channels, `internal:` = sportsbook CONTEST prefix (not admin),
  `game:${id}`, `tournament:*`. Joining `internal:*` + `user:<harvested-uuid>` with elevated
  subs returns only the global feed — silent empty joins = server-side membership check.
- **16 unauth-200 endpoints mapped** (`endpoint_probe.json`): betradar odds/event feeds,
  `config/levels` (full VIP economics), `games/v2/plinko` (full probability tables),
  tap-trading bets/price-history, `leaderboard` (69KB standings w/ internal UUIDs + registered
  ms + amounts — same leak class as bets/live). `/auth/blockCheck` = the region oracle
  (`{reason:region_page,location:de}`; `?ip=` is client-display-only).
- **Zero rate limiting** on `/auth/token` mint + `/ws/user/bets/live` (15-burst at 0.25s: all
  201/200, no 429) — unthrottled anon minting + unthrottled feed scraping.
- **Security headers: absent** (no HSTS/CSP/XFO/XCTO on root); duelbits.com cert = apex-only
  SAN. Bundle secrets CLEAN (416 chunks, all key-pattern hits false positives).
- **Unauth surface EXHAUSTED.** Every compromise-class vector now sits behind (a) the
  restricted-region wall (residential unrestricted IP needed) or (b) a real wallet session.
  The operator's console remains the unlock for the replay/binding/mass-assignment chain.
