# Engagement Vantage Policy (2026-11-02)

**ALL target traffic fires from Vermes (`ssh vermes`), never from the home/residential IP.**

## Why (burned 2026-11-02)
The gamdom.com session ran 54 probes + logError/pageview 1MB floods + socket scraping from the
home Comcast IP (67.163.104.183). Result: app-layer IP ban (302 `/banned?reason=IP+Banned`) —
no account needed, the traffic alone was enough. The residential IP is identity-attached
(ISP account, all personal browsing) — burning it costs real access. A datacenter vantage
costs nothing.

## What lives where
- VM (`ssh vermes`, opc@92.5.99.31): `~/holyshit-mode/` (full repo) + `~/.hermes/scripts/holyleadger/` (all 15 ledger JSONs, chmod 700 dir / 600 files).
- Home: same paths (authoritative copy for git pushes — VM has no GitHub creds).
- Sync out: `rsync -az ~/holyshit-mode/ vermes:~/holyshit-mode/` + ledger dir.
- Sync back: reverse rsync after engagement, then relay to GitHub from home.

## VM tooling (keep list current)
python3.9, curl, dig, openssl, jq, nc/ncat, whois, nmap. OL9 = dnf; sudo -n works.
Recon kit added since: `curl-impersonate-chrome` in `~/dkv-venv/bin` (JA3 bypass, see
TLS-impersonation section), chromium-browser + Xvfb (`DISPLAY=:99`, CDP `127.0.0.1:9222`,
profile `/tmp/chrome-prof`) for real-browser surfaces, user-level pip packages in
`~/dkv-venv` (websocket-client, msgpack, eth-account, python-socketio, requests). Kill
chromium with `pkill -9 chromium` and relaunch fresh with `--no-sandbox` + a new
`--user-data-dir` when it gets stuck in an existing-session loop.

## Recipes that change on the VM
- Probes: `ssh vermes '<curl/python/etc>'` — per-command ~0.33s over the ssh mux.
- Long bursts/captures: nohup on the VM, poll the log. **ssh drop does NOT reliably kill remote foreground children** — a piped foreground run survived a terminal timeout and kept probing, so the next launch ran CONCURRENTLY and doubled request volume into one log. Before re-running a VM job, verify no stale remote process exists (`ps` by script name or a pidfile), and poll completion by the job's OWN DONE marker in its log — never `pgrep`/`pkill -f <script>`: the ssh wrapper's cmdline contains the pattern and
  self-matches (pgrep = false RUNNING; `pkill -f` = kills your own ssh session, exit 255) —
  use the process's bare name (`pkill -9 chromium`) or a bracketed regex.
- Inline Python over ssh heredocs: f-string expressions cannot contain backslash escapes (SyntaxError on the literal, hit 3x in one session). Bind the escaped regex/sub result to a variable before the f-string, or write the script to a file and scp it once it passes a few lines.
- `jq` on a jsonl verdict file needs `-s` (slurp) — without it every line errors `Cannot index string with "phase"` because jq parses each JSON value as its own document.
- The `holyleadger` mode-700 PermissionError rule now READS: run it on the VM as opc over ssh,
  or as the shell user at home — never from the execute_code sandbox.
- Dispatcher endpoints (HOLYSHIT_ENDPOINT) are home-local (FreeForge :8705) — LLM dispatch can
  stay on home or use VM-reachable providers; TARGET traffic is what must never touch home.

## Honest caveats
- Datacenter IPs get challenged harder by some WAFs (Fastly/Turnstile fingerprints ASN) —
  if a wall appears that the same probe never hit from home, diff the vantage before blaming
  the probe.
- Vermes holds keys (reverse-tunnel identity, hermes/mochi auth) — probe scripts stay
  read-only curl/socket work; never drop stored target credentials on the VM.
- Never re-probe gamdom.com from the home IP while the ban stands (and don't from the VM
  either without re-checking the case file first).

## Automation-first + shreddable workspace (operator mandate)

- **Automate every queued test on the VM before asking the operator for anything.**
  "Operator console" tests (auth flows, wallet signatures) get a VM kit first: write a phased
  python kit at home, `scp` it over, run phases paced (3.5–6.5s jitter, adaptive backoff on
  403/429, hard stop at 3 consecutive blocks, JSONL verdict log). Hand the operator a console
  test ONLY when the VM wall for that endpoint class is PROVEN — never assumed.
- **Workspace:** all engagement data (results, captures, burner keys, session tokens) goes in
  `/dev/shm/.dkv/` (RAM tmpfs: gone on reboot) plus a `shred.sh` (`rm -rf` the dir) for the
  one-command wipe. NEVER store engagement data on the home box.
- **/dev/shm is mounted noexec on OL9** — venvs/binaries can't execute from RAM. Venv +
  tooling live on disk (`~/dkv-venv`), artifacts in RAM; the shred script wipes both.
- Step 0 of any VM session: `curl -s https://api.ipify.org` to log the egress IP.

## Region-wall discriminator (auth-plane 403 ≠ IP-quality)

Datacenter vantage + `403 general.Forbidden` on auth endpoints while READ surfaces (feeds,
sockets, configs) answer 200 = a RESTRICTED-MARKET geo block on the vantage, not IP-quality.
Confirm via the target's own signal: the realtime socket pushes `blocked:{reason:"region_page",
location:"de"}` naming the geolocated country. Never churn request variants on ONE route
(signing modes, address casings, claimed country params) — they fail identically and the
churn burns the vantage. DO sweep route BREADTH once per route: the region gate is
PER-ROUTE, not per-host — one host answered `/auth/token` 201, `/auth/blockCheck` 200,
`/auth/web3` 403, and `/auth/steam` + `/auth/google` 302 in the same engagement. The 302
OAuth login starters (steam/google/discord) are the likeliest exemptions, so probe every
login-method starter BEFORE declaring the auth plane walled. Gated routes need a
residential unrestricted vantage; open starters do not — say once which is which.

## TLS-impersonation tooling + wall-shape discriminator

- **curl-impersonate on OL9:** binaries can't run from /dev/shm (noexec) — keep them in
  `~/dkv-venv/bin`. The bundled wrapper scripts hardcode a Debian CA path
  (`/etc/ssl/certs/ca-certificates.crt`) and fail with error 77 — run the binary directly
  with `-k` plus the `--ciphers`/header flags copied out of the wrapper, or export
  `CURL_CA_BUNDLE`. chrome110-impersonation passes JA3-keyed apex blocks that stop default
  curl/python outright.
- **Wall shapes differ PER HOST — fingerprint each, never generalize.** On one fleet: the
  apex = JA3-keyed (impersonation passes), the API host = IP-reputation hard block (403
  "you have been blocked" EVEN for real chromium navigation), staging hosts = CF Access
  walls, mirrors = managed challenge. Same org, four different gates. Classify per host:
  (a) impersonation passes = TLS-fingerprint rule; (b) real-browser navigation still
  blocked = IP-reputation rule — no script-side fix exists, the vantage is the wall;
  (c) Access/managed-challenge pages = a wall for scripts AND often for DC-vantage
  browsers. Record the shape per host in the ledger so a re-engage doesn't re-derive it.
- **`retry-after` on app-level 429s = the authoritative cooldown** — read it before
  choosing a retry cadence (see recon-quick-checks #32 for the self-DoS trap).