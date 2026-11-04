# Client-Bundle Source Study (Deep-Dive Playbook)

Mining a SPA's shipped chunks is the highest-yield recon step when the API surface is
socket-driven and the env map is compiled into the client. Works on rolldown-vite,
webpack, and Vite SPAs.

## Order of operations

1. **Inventory.** Fetch index.html → asset list; fetch the entry chunk + every listed
   chunk. Every fetch needs the full spoof stack (UA, Accept, Accept-Language, sec-ch-ua,
   Sec-Fetch-*, Referer, --compressed) AND `-w "%{http_code} %{size_download}\n"` — a
   silent empty download is the #1 false-negative source. Pace 3-5s on WAF'd targets;
   a CF managed-challenge body is binary/turnstile — bail before re-probing.
2. **APIConfig / env chunks FIRST.** Grep for `APIConfig-*.js` and `env-*.js`: the whole
   environment map ships there — per-hostname blocks of `{token, auth, oAuth, websocket,
   gamesocket}` including dev/staging/canary hosts and preview-host regexes. Every
   hardcoded internal host is a probe target: DNS check, then gate classification
   (CF Access login page has title "Sign in · Cloudflare Access"; Netlify 401 = password
   gate; Netlify "Not Found - Request ID" + Server:Netlify = deleted deploy). The env
   chunk also inventories every VITE_* key — score each by what it authenticates
   (Contentful delivery token = semi-public; provider widget keys = semi-public by
   design; a minted API key = finding).
3. **Endpoint call sites.** Regexes that work, in order:
   - quoted absolute paths: `["'\`](/[a-zA-Z0-9_\-/?.=&${}.:]{1,160})["'\`]`
   - relative template-literal paths WITHOUT leading slash (common wrapper pattern):
     `[\x27\x60]([a-zA-Z][a-zA-Z0-9_/.-]{1,90})[\x27\x60]` filtered by route vocabulary
     (`user/`, `games/`, `auth/`, `betradar/`, `config/`, `tickets/`, ...). Most quoted
     strings are i18n keys — filter HARD or the list is 1000+ noise entries.
   - fetch/axios call sites: `fetch\(\s*["'\`]([^"'\`]{1,200})["'\`]` plus absolute-URL
     in-call-site regexes (they leak admin/dev hosts the DNS enum misses).
4. **Lazy chunks.** Grep the routes/entry chunk for `assets/<name>.js` references
   (webpack `__vite__mapDeps`, import maps) and fetch every referenced chunk missing from
   your set. The login/auth chunk is usually lazy and holds the signIn logic; a secret
   sweep is incomplete without it AND the entry chunk itself.
5. **Socket vocabulary.** emit/on/join event names — filter CSS-in-JS noise (reject
   strings with spaces; keep known prefixes, `user:`, `game:`, `internal:`, custom
   subscription events).
6. **Privilege branches.** `user.id === N` hardcodes; numeric user-class enums (VIP
   ladder) and loginTypes enums = internal vocabulary for mass-assignment payloads;
   `isInternal`-style flags may be domain vocabulary (sportsbook internal MARKETS), not
   privilege — check the field's type before rating.
7. **Import resolution (critical step).** For every call of interest, resolve the
   imported helper to its defining chunk, its export-map alias (`export{T as A, C as P}`),
   and the function body. Cookie readers, URLSearchParams readers, and localStorage
   readers are indistinguishable at the call site; the carrier determines the exploit.

## Pitfalls

- **Route sweeps MUST pass `allow_redirects=False`.** A followed 302 records the PROVIDER
  page (accounts.google.com) as the route status — 200-OPEN verdicts on OAuth starters are
  artifacts. Classify status + content-type from the no-redirect response; a 302 with a
  provider Location is itself the REAL route (read its return_to/redirect_uri params).
- **CF Access gates return 200 HTML "Sign in · Cloudflare Access" for every path** —
  detect by title/body string, not status; determinism tests run against Access pages
  produce garbage "rotating/identical" verdicts. Parse `Server:` + `content-type` before
  scoring any response.
- **Region gates are selective:** sweep the whole auth plane (200-JSON = OPEN,
  403-JSON = exists-gated, 404-JSON = absent). OAuth STARTERS often escape the gate their
  exchange sits behind — the starter side is testable from datacenter vantage even when
  the exchange is not.
- **Region-deny shapes drift:** a clean 403 on a route can become an unhandled 500 crash
  between sessions. Re-probe the wall each engagement session; never assume the old
  status class still holds.
- **Socket transport walls:** polling `400 Transport unknown` / `400 Bad handshake
  method` = websocket-only namespace; CF 403 on python WS upgrades = vantage limitation.
  Log both as coverage and move on.
- **CMS/deep-content regex sweeps false-positive massively** on Contentful-style link IDs
  (`SKLyX0GT...`, `pkY...`) matching sk-/pk-prefixed secret patterns — thousands of hits,
  zero secrets. Whack-list linkType/sys contexts before reporting counts.
- **Mint endpoints ignore bodies:** a scope-mint that returns a token for EVERY body
  (grant_type=password with credentials, empty {}, garbage) proves the mint has no
  credential oracle — the response SHAPE across bodies is the finding, not the tokens.

## Autonomous ephemeral-wallet signup test

For web3-wallet login targets where the exchange is region-walled from every vantage you
control, complete the register + mass-assignment probe without the operator console:

1. Generate keypair on the probe box: `eth_account.Account.create()` (venv on disk —
   /dev/shm is often noexec).
2. Challenge: `POST <auth>/web3/message/?publicAddress=<addr>` — accept 200 AND 201
   (non-200 success statuses are common); response `.message`.
3. Sign: `Account.sign_message(encode_defunct(text=msg), key)` — `hex_signature` is
   65-byte r||s||v, directly recoverable by web3.js `personal.ecRecover`.
4. `POST <auth>/web3` body `{address, signature, ...injected-keys}` — 200/201 returns the
   session + user object; diff the user object for stuck keys (role/VIP class/verified).
5. Hygiene: key stays in RAM; shred the artifacts dir immediately; the account is
   throwaway and non-destructive.
6. Scope note: a vanity keypair is an operator-directed self-account test, NOT identity
   fraud — no real identity, no funds, no third-party accounts touched.

## Dangling-preview cookie-toss chain

1. Resolve preview wildcards (`deploy-preview-N.*`, `main.*`); fetch root: Netlify
   "Not Found - Request ID: <ulid>" + `Server: Netlify` = deleted deploy on live DNS =
   dangle.
2. Find cookie-TRUST primitives in the main-site client: grep chunks for cookie readers
   (e.g. `function C(e){let t=e+\`=\`;...document.cookie...}`) and trace every call site.
3. Chain: a claimed wildcard host serves a page that `Set-Cookie: <trusted-name>=<json>;
   Domain=.parent.com; Path=/` (domain-suffix rule makes the main origin honor it) →
   victim click → victim's next login ships the attacker's cookie keys in the auth body.
4. Gates: wildcard claimability (infrastructure takeover — operator's explicit call),
   server-side key acceptance (operator console: `document.cookie='<name>=<json>;path=/'`
   then login and diff the profile/me endpoint).

## Tracker-page cookie-toss gadget (no dangle needed)

The target's OWN tracker/attrib pages (`media.*`, `clever.*`, `out.*`) are a cookie-toss
primitive WITHOUT any dangling host: they write URL params as cookies on the MAIN
registrable domain (`Domain=<main>; Path=/; Max-Age=90d; SameSite=None; Secure`, often
≤25 params/visit). Test with a REAL browser (the CF burn pattern blocks scripted fetches
mid-round on these hosts — drive the harness browser instead).

1. Fetch the tracker page source and read its blocklist: reserved names are an EXACT-match
   Set (`session, sid, token, jwt, auth, csrf, xsrf`) — PREFIXED session cookies
   (`stel_token`-family), identity cookies, and `referralCode` fall through. Whatever name
   scheme the site prefixes, the blocklist misses it.
2. Map what the SPA READS from cookies: the React persistent-store pattern
   (`(0,X.N)("name", default)` builders) = cookie-backed stores; identity stores beat
   preference stores. `client-context` = the FingerprintJS Pro visitorId — the SPA SKIPS
   fingerprint generation when the cookie exists, so a tossed value IS the device
   identity (ban evasion + risk-model poison). `stag`-class cookies = affiliate tags read
   at signup (`getAffiliateTag`) = attribution hijack; a fixed-default stag on the tracker
   page = the operator's own ad-pipeline affiliate id.
3. Impact chain: attacker link → tracker page with params → cookies on the main origin →
   identity/attribution/fixation effects. Session-fixation verdict needs the real
   Set-Cookie attributes (HttpOnly guards JS overwrites of an EXISTING cookie; a tossed
   name still pre-plants before first login) — rate honestly, don't assume takeover.
4. Fleet multiplier: inventory media/clever/out hosts on EVERY mirror domain — the gadget
   ships per-brand (`clever.rainbet1.com` carried it when the main domain did).

## Error-code vocabulary = the API feature map

Grep all chunks for the platform's error-code prefix (e.g. `er_[a-z0-9_]+`) and sort: every
`er_<feature>_<failure>` names an endpoint family that may not appear in any fetch site
(kick, telegram, sol, kyc/persona, vault+2fa, raffles, seeds, party). 150+ codes = a full
hidden-surface inventory; score only after probing, but USE the map to pick probe targets
(and to spot auth methods the current UI hides, e.g. sol-wallet sign-in codes without a UI
button).
