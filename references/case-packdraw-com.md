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