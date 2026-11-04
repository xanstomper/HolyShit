# Breach-Context Adjacent-Infrastructure Pivot

Worked recipe for re-engaging a target whose main host is hardened — or whose
engagement IS a breach follow-up. The compromisable surface lives in the family
orbit: partner brands, market mirrors, dead-certed internal hosts, bare origins.
Session-verified end-to-end: main-site probes found walls; the pivot ladder found
an EOL VestaCP box with an internet-exposed EOL database hosting the user login funnel.

## 1. Build the brief from breach-OSINT

- Search: `<target> breach leak <year>` — hit Breachsense, ransomware.live, and 2-3 news writeups.
- Record from the attacker's leak-site statement: claimed initial access, claimed data
  holdings, escalation promises. This is the engagement brief — the attacker documents
  their own kill-chain.
- Corroborate against the victim's public statements. The mechanism is confirmed when the
  victim's own PR admits it ("unauthorized withdrawal requests were added to the database"
  = proven DB-level WRITE). Disputed scale ≠ disputed method.
- The two datasets (attacker holdings vs victim confirmations) define what remains open.

## 2. The pivot ladder (run in order; stop at first live surface)

1. **CT logs:** `curl "https://crt.sh/?q=%25.<domain>&output=json"` — collect every host
   ever certified. Dedupe, ignore wildcards. Misspelled internal names ("inteligance")
   and infra names ("td", "stagsrv", "incoming-callbacks") are the high-value subset.
2. **Partner brands from the client bundle:** grep the pooled JS for
   `/casino/providers/<brand>-originals` style routes — sister brands ship inside the app.
   Run the SAME ladder against each sister domain's CT logs.
3. **Mirror/entrance sites:** regional gambling pattern — `<tr|giris|m>.<brand>.com`
   on DIFFERENT hosting (different IP range, different server stack, often PHP).
   These host the login funnel for that market. Fingerprint hard.
4. **Passive DNS for dead-certed hosts:** `curl "https://api.hackertarget.com/hostsearch/?q=<domain>"`
   returns historical host→IP pairs. Cross-reference CT hosts with no current DNS.
   A live cert with stripped DNS = decommissioned "internal control panel" — the exact
   artifact the attacker's statement points at. Wayback (`archive.org/wayback/available`)
   and urlscan.io history may hold what it hosted.
5. **Bare origins:** any host resolving to raw cloud IPs (AWS EC2, LeaseWeb) instead of the
   CDN = infrastructure outside the edge rules. Probe its paths directly.

## 3. Era-stack fingerprint recipe (the Holy Shit shape)

On a live mirror/entrance box:

- `curl -sI https://<host>/` — `X-Powered-By: PHP/5.4.45` = EOL Sep 2015, 11 years unpatched.
- Follow any 301s with `-w "%{redirect_url}"` — a redirect leaking
  `/home/<user>/web/<domain>/public_html/...` = stock VestaCP/HestiaCP layout; also a
  standalone absolute-path disclosure finding.
- Read-only TCP connect scan of common ports: 21,22,25,53,80,110,143,443,465,587,993,995,
  2222,3306,5432,6379,8080,8083,8443,8888,10000.
- Banner-grab the answers:
  - `:8083` — title `Vesta`/`Hestia` = exposed EOL hosting panel. POST `/api/` with
    `cmd=v-list-sys-info&user=admin&password=wrong` → uniform `Error: authentication failed`
    = API live, auth-gated, no user enumeration. Map known-CVE surface; do NOT brute creds.
  - `:3306` — raw connect + recv leaks the MariaDB/MySQL version in the greeting
    (`5.5.x-MariaDB` = EOL Oct 2018). Internet-reachable EOL DB = the finding itself.
  - `:110/:143` Dovecot, `:21` vsFTPd — normal panel stack, note exposure.
- Probe the web layer: `/phpmyadmin/`, `/server-status`, `/phpinfo.php` — 301/403 = exists.

## 4. Schema-library extraction — proving the auth gate WITHOUT a session

The SPA client ships the complete zod/io-ts request-shape library, derived from the
backend's shared types. Exploit it:

1. Pool all code-split chunks, grep for the schema-definition chunk (look for
   `intersection([type({...}), partial({...})])`, `refinement(Integer,`, `union([...])`).
2. Extract the target RPC's full arg schema + every referenced enum (WalletUnit:
   COINS|USDT|USDC|USD1|FIAT_*|BTC_SATOSHI|...).
3. Build a COMPLETE valid shape and fire it unauth: the uniform `Invalid parameters` wall
   becomes an explicit error (`Not logged in`) = validation→auth order proven, pre-auth
   question closed.
4. Read the trust model from the schemas:
   - `*_requested` field naming and OPTIONAL client-supplied fields (`userExpectedFeeCoins`)
     = the server recomputes; client amounts are requests, not truths.
   - A money-transfer shape with NO cross-user identifier (no walletId/ownerId) means
     IDOR is structurally impossible on that surface — only self-inflation (trusted
     amount) could be a vuln, and that gets caught by ledger reconciliation.
   - Asymmetry worth flagging: a tip endpoint using generic `number` where withdrawals
     use `refinement(Integer, e=>e>0)` — the loose side is where unit-conversion edges live.
5. Deliver the verdict with a confidence number (~92%) + the named residual edges.

## 5. Registration walls — verify both layers before documenting

- **Edge layer:** Fastly VCL returns `400 ... Error 54113` on non-browser TLS for sensitive
  POSTs (`/signup`) while the same client passes on other endpoints. Python/curl replicas
  die here regardless of headers.
- **Browser layer:** replicate the flow in a real-browser harness (shadow-DOM forms need
  recursive shadow-root piercing; native value-setter + input/change events for React
  inputs; real `.click()` on controlled checkboxes — a failed checkbox blocks submit
  SILENTLY with no error text). If invisible Turnstile never initializes
  (`window.turnstile` undefined, no challenges.cloudflare.com scripts/iframes, no request
  fires on submit), the wall is verified.
- Document the wall, write a ready-made cookie-driven test script for the operator, and
  stop. Never forge captcha tokens.

## 6. Post-breach user-protection checks (do these even when the core is clean)

- `dig TXT _dmarc.<domain>` — `p=reject; pct=100` = spoofing dead. `p=none` or missing =
  post-breach phishing is trivially easy and becomes a critical finding.
- Full SPF (`-all` vs `~all`) + DKIM selector sweep (`default|google|s1|s2|selector1...`).
- The breach data itself drives phishing lures; the email-auth posture decides whether
  attackers can send AS the domain. This is the live risk while the extortion clock runs.

## 7. Cross-brand blast radius

- Identical CDN IPs + verbatim-identical error envelopes across sister brands = shared
  backend user/session store hypothesis.
- Ledger a cross-brand session-replay hypothesis (one account on either brand tests it)
  and the credential-reuse angle: attacker leaks of ONE brand's `userid|email|password`
  records degrade the whole family.
- Sister-brand CT logs surface what the main brand's logs hide: staging servers (dead
  503 origin behind a live route) and dangling CDN routes ("unknown domain" errors).
