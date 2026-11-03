# Case: packdraw.com — Vercel/Next.js pack-opening platform (day-1 recon)

2026-11-03. Real-browser vantage required: **Vercel Security Checkpoint 429s ALL
non-browser traffic** (HTML, assets, `/api/*` — JSON `{"error":{"code":"challenge"}}`).
Datacenter vantage (Vermes) fully blocked; the real-browser harness passes and was the
only working vantage. All engagement data in `/dev/shm/.dkv/packdraw/`.

## Stack map (verified)
- **Vercel + Next.js App Router (Turbopack**, immutable chunk hashing), SSR-heavy.
- **Pusher 8.0.2** realtime: public channel `pack-result` (live packs counter),
  `private-encrypted-user-*` channels behind `/api/pusher/auth` (403 without session —
  REAL route; `/pusher/auth` + `/pusher/user-auth` = SPA-fallback ghosts, not routes).
- **TokenEx** card tokenization iframe (`/api/tokenize/iframe/config` — 404 GET; POST
  untested), **ImageKit** CDN (account `hr727kunx`, path `community_packs/...`),
  **reCAPTCHA Enterprise** on auth (sitekey `6LcfH48qAAAAAOnZqFXlOGJmJHGYJtNBFbfpbAsg`),
  Axiom telemetry, Vercel observability beacon `/monitoring?o=...&p=...`.
- **Auth: email/password + Google + Apple** (no phone). Register = modal, not a route
  (`/en-us/register` = 404). Login fields: email/password/checkbox (+ reCAPTCHA).
- Money: crypto deposit/cashout ("withdraw value in crypto", "no daily withdrawal
  limit"), card deposits via TokenEx iframe. Deposit promo code PACKDRAW +5%.
- Legal: Packdraw Limited (Cyprus HE 445177) + PackDraw US LLC (Delaware 7571319).
- DNS: Vercel NS, MX Google (smtp.google.com), SPF google+sendgrid+mailgun, fb+google
  verification TXT. Wildcard cert `*.packdraw.com`.
- Subdomains (CT): status.packdraw.com (Vercel status-page SPA, all paths 200, one
  monitored service slug `command`), howitworks/battles (DNS only, Vercel 404s),
  UUID subdomain = deleted Vercel deployment (503), www (checkpoint).
- Business surface: packs (Pokemon TCG heavy + MTG), battles (NORMAL/SHARE/JACKPOT,
  up to $1.2K entries, live "unboxed" values via Pusher), deals, rewards, events,
  user-created packs ("Create Pack": packName + item catalog incl. $700K cars).

## Provably-fair scheme (from their fairness page — the key attack surface)
- Packs/deals: `ticket = normalize(hash(clientSeed + serverSeed + nonce))` in 1..1M;
  item by ticket range (ranges visible in pack details). Server seed committed as hash
  pre-open, revealed unhashed AFTER the game.
- Battles: entropy = `sha256(future EOS block hash)` (mined after entries close);
  jackpot = `sha256(eosBlockHash)` modular raffle over ticket ranges; card-flip:
  `nonce = roundIndex*lineCount + lineIndex`, win if ticket <= survivalProb*1M.
- **THE OPEN QUESTION (WhiteArmor-grade if wrong): server-seed rotation policy.**
  Per-open rotation = standard safe. Per-account FIXED seed revealed after every open =
  after ONE open the user knows the seed and can compute future tickets BEFORE paying
  (controls clientSeed + nonce) → open only when the ticket lands on value > pack price
  → guaranteed-profit drain. Demo mode exists without account but the modal flow did not
  complete in testing (needs the mode-confirm step click-timing). Decisive test: 2 opens
  (one account, ~$11) or a working demo run — compare revealed seeds + pre-open hashes.

## Unauthed-surface verdict
- Thin by design: SSR-only product data (full odds tables public = fine), checkpoint +
  reCAPTCHA on all interactive planes, realtime gated. No unauth data plane leak found.
- Negatives: /api/pusher/auth 403; tokenize config 404 GET; /pusher/* ghosts; VM fully
  checkpoint-walled; wayback has HTML shells only (NO JS chunks archived — bundle mining
  there is a dead end; 2026 shell = current-ish build references only); Elavon/Tokex
  vendor config untested.

## Queued operator tests (self-account, non-destructive)
1. **Seed-rotation test** (the top finding): register → open 2 cheap packs → record
   pre-open hashed seed + post-open revealed seed for each; check (a) hash(revealed) ==
   pre-open hash (commitment discipline), (b) seeds differ between opens (rotation), or
   (c) same seed persists (PREDICTIVE → guaranteed-win exploit).
2. **Battle verification**: join/observe one battle → after EOS block, verify
   `sha256(blockHash) → ticket → winner` against the recorded winner.
3. **Cross-user Pusher**: with an account, request `/api/pusher/auth` for
   `private-encrypted-user-<OTHER>` channel → 403 = good; 200 = cross-user realtime.
4. **Create-pack validation**: user-created packs — can the user set odds/weights/price
   such that EV > price (self-dealing), or is validation server-side?
5. **Tokenize iframe config** POST shape (may leak tokenExId/timestamp config).
## 2026-11-03 sweep round (VM + browser)

- **Checkpoint bypass verified:** Security Checkpoint binds ONLY to apex/www. All
  78 fuzzed `*.packdraw.com` names resolve (wildcard DNS) and answer WITHOUT 429 from
  the datacenter (404s = catch-all Vercel). `packdraw.vercel.app` serves the app shell
  (old build era, SPA-fallback 200 ghosts for EVERY path incl /.git/HEAD, /.env,
  swagger, graphql — ghost discrimination, none are real); `/api/pusher/auth` on the
  alias = 405 (route exists). `staging.packdraw.com` = Vercel Authentication 401
  (password off — v1 curl/MCP-gated). WAF coverage = branded host only; tool-based
  attackers re-point to the alias/subdomain plane.
- **Prod API surface (definitive):** ~140-path dict via in-page fetch: only
  `/api/pusher/auth` is a real route (GET 405, POST 403 for every channel class incl.
  public names — realtime authz holds). `tokenize/iframe/config` = 200-HTML ghost on
  GET AND POST. No demo/open/seed/user/admin routes. No $ACTION_ID_ public actions.
  App architecture = SSR/RSC + auth-gated server actions; unauth data rides RSC.
- **Full path fuzz of the alias:** 134/134 paths = 200 SPA shell (ghosts); verified the
  shell is byte-identical to prove ghost status before discounting.

## 2026-11-03 vector sweep round (customer info / control panels / wallet)

- **Customer info:** NOT reachable unauth. Public `pack-result`/`created` stream verified =
  product+price only (live DOM + RSC checked); private channels 403; SSR anonymized.
- **Control panels:** absent on every plane (prod 404/ghost, alias host-level-405, staging
  Vercel-auth 401; admin staff dashboard internal names all 404).
- **Wallet/drain plane:** money APIs = server actions behind auth; deposit/cashout
  mechanics invisible unauth. The only drain-class chain remains PF seed-prediction
  (operator 2-open test). Alias = static shell, POST blocked host-level (405 everywhere =
  Vercel frozen deployment, NOT routes - discriminator: 405-on-all-paths means host-level
  block, not route existence).

## 2026-11-03 3AM-shinjitsu sweep (P3 prepared-exploit + P5 closeout)

- **CVE-2025-29927 (Next middleware bypass): BLOCKED** — identical statuses with/without
  `x-middleware-subrequest` on /en-us/account + 7 route guesses; Vercel platform fix.
- **_next/image optimizer SSRF: BLOCKED** — 400 on any non-allow-listed host (allow-list =
  imagekit etc.; Vercel metadata-IP block upstream).
- **postMessage surface: none** in loaded client chunks.
- **Breach-context brief (cartel class):** no hack/leak of PackDraw; but no gambling
  license; federal litigation (MN 25-cv-4128, Sept-2026 order) alleges PackDraw built
  with misappropriated Partnership code (The House/WowDAO/Packs.com/Packs Protocol
  brands) delivered into Roobet orbit; PDCC Services Ltd entity; minor-recruitment
  suits MN+NY; $500K-impersonation laundering suit defendant; ~$259M deposits by
  Apr-2025; Trustpilot 3.9/5 with unauthorized-charge + odds-tightening complaints.
- **§8 coverage verdict:** all 10 classes probed or N/A for the unauth plane; every
  finding ledgered; remaining account-plane tests = operator ask (seed-rotation 2-open
  test, cross-user pusher with session, create-pack EV, battle hash verify).

## 2026-11-03 3AM final: demo inert, PF hypothesis upgraded, T2 stands

- Demo mode: verified INERT for guests (4 click sequences incl post-Continue, DOM dumps,
  zero network) — no unauth seed-observation path exists.
- PF algorithm verbatim (from their fairness page): `ticket = (BigInt('0x'+sha512(
  clientSeed+':'+serverSeed+':'+nonce)) % 1_000_000) + 1`; jackpot = `sha256(eosBlockHash)
  % totalTickets + 1` with contiguous ticket ranges. Their text: nonce is needed "when
  server seeds and client seeds remain unchanged, as is the case when opening multiple
  packs in a single purchase"; the hashed server seed is shown in the account PROFILE
  before purchase and the unhashed seed exposed after. Account-level seed commitment +
  nonce-machinery = fixed-seed architecture hypothesis (58-70 if 2-open test confirms
  non-rotation across purchases). Full verify recipe documented in the ledger class.

## 2026-11-03 3AM keep-going round: routes complete + drift oracle armed

- Drift baseline: chunk 0lvv874ns6o2c.js sha1 = 0d48fa724bf3 (re-arm before any future
  re-probe); checkpoint shell byte-stable (17385B 429 from VM).
- /draw, /deals (10,905 products to $350K), /events (Daily Raffle $2,500 pool; winners
  list PUBLIC with masked handles first3+last3, exact ticket counts, payouts; raffle RNG
  not covered by the PF doc), /rewards (login-gated ladder: daily/weekly/monthly + free
  packs L2-L100).
- Google/Apple OAuth = server-action start (no client-side client_id/redirect_uri);
  CORS clean (403 no reflection). OAuth/raffle-RNG items = operator-plane/inconclusive.
