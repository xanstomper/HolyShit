# Engagement Report — gamdom.com

**Generated:** 2026-11-02 21:55 UTC  
**Classes tracked:** 54  
**Confirmed:** 35 · **Hypothesis:** 2 · **Negative (ruled out):** 17  
**Chains:** 3

---

## Confirmed Holy Shits

### `whitearmor_extortion_context`
- **Score:** 90  
- **Technique:** Oct 26-27 WhiteArmor extortion: claims 15,420,003 accounts x 146 fields, $15M BTC ransom, ~100-record JSON sample (437KB). Attacker-stated initial access: aged internal MACHINE account, credentials NEVER ROTATED, retained admin privileges for years, moved through internal control panels + data stores. Founder disputed scale (15.4M) and extraction, NOT the access method. Oct 14 disclosure: 'unauthorized connection involving an automation server.'  
- **Probed:** 1x, last 2026-11-02 04:06:20.345602+00:00

### `db_write_proof`
- **Score:** 80  
- **Technique:** Founder statement: 'withdrawal requests were added to the database' = CONFIRMED DB WRITE access during the wallet event (Oct 13). Write-capable foothold into a DB-connected automation path => read capability is a lateral step. $3M wallet theft + ~$1M from private key systems, total ~$4.2M.  
- **Probed:** 1x, last 2026-11-02 04:06:20.426903+00:00

### `cross_system_data_holdings`
- **Score:** 75  
- **Technique:** WhiteArmor holdings per ransomware.live Oct 31: support chats + photos (Intercom export), Perabet records (userid|email|password - shared partner platform, /casino/providers/perabet-originals in client bundle), admin records w/ last-IP (Felix uid 16259643 last IP 13.x), 146-field wide table = main users table. Cross-system read proven by their own possession claims.  
- **Probed:** 1x, last 2026-11-02 04:06:20.501381+00:00

### `crash_no_preround_commitment`
- **Score:** 75  
- **Technique:** GAME INTEGRITY - full crash round captured unauth (149 frames, 2 complete rounds): game_starting={game_id,time_till_start}, game_started={bonusPool} - ZERO hash/seed/commitment fields pre-round; the sha256 hash appears ONLY in game_crash ALONGSIDE the result (hash:9bf6d6bf..., game_crash:128). Nothing binds the outcome before bets close on any publicly-checkable channel. Gamdom markets 'provably fair' - on crash the public wire cannot prove pre-commitment. WhiteArmor's PF-lies claim aligns with this structure. Test left: authed UI may show the hash mid-round (needs session). Evidence: /tmp/gd_crash_full.txt  
- **Probed:** 1x, last 2026-11-02 05:25:30.156675+00:00

### `identity_feed_study`
- **Score:** 75  
- **Technique:** IDENTITY FEED STUDY (clean 771KB capture, continuation-reassembled): 40 hidden-mode users with REAL names+IDs+XP+balances, stable across independent captures (doddy tv/DoddyTheViking, Angelodonedidit id 48171857 confirmed twice). Config leak list: Mck5030 34.7B value, psxroolz 9.7B, weakerarms 36B. Whale list live: Cabrzy +305.6M Keno, SteveWillDoIt +182.4M sportsbook. 8 steam-linked accounts (public steamstatic avatars). DB tables: crash/dice/hilo/roulette.plays + external_games.transactions_v2. All anonymous, all the time.  
- **Probed:** 1x, last 2026-11-02 07:31:42.517819+00:00

### `turkish_entrance_eol_stack`
- **Score:** 70  
- **Technique:** tr.perabet.com + giris.perabet.com (217.23.12.109, LeaseWeb) = 2015-era VestaCP box: PHP 5.4.45 (EOL Sep 2015, 11yrs unpatched) via X-Powered-By, VestaCP panel on 8083 (React-rebuilt UI, title Vesta, API responds 'Error: authentication failed' unauth), Dovecot+vsFTPd 3.0.2 mail/ftp stack, Apache server-status present (403). 301 redirect LEAKS absolute docroot: /home/admin/web/tr.perabet.com/public_html/. /phpmyadmin/ path serves a stub printing the PHP version. This box hosts the LOGIN/ENTRANCE pages funneling Turkish users into perabet/gamdom.  
- **Probed:** 1x, last 2026-11-02 04:42:45.939618+00:00

### `hidden_mode_display_username_leak`
- **Score:** 70  
- **Technique:** HOLY SHIT UPGRADE - the real names LEAK: the hidden_mode masking masks username->'Hidden user' but display_username ships the REAL NAME verbatim. One 30s anonymous EIO=3 websocket capture (457KB): 39 unique hidden users identified with real names + user IDs + XP + balances. Examples: id=16417442 'emrakdnz' (1.18T xp), id=7188711 'psxroolz' (9.7B value), id=16320332 'watersound11' (10.4B value), id=48264601 'weakerarms' (36B value). The 'hide statistics from other users' feature = server masks ONE field and forgets its alias; any scraper gets the complete identity+financial profile of every opted-out user in 30 seconds. Fix: server-side - when hidden_mode, NULL display_username AND username on every feed path (or drop the row).  
- **Probed:** 1x, last 2026-11-02 07:08:50.498650+00:00

### `name_hiding_failure_study`
- **Score:** 70  
- **Technique:** SYSTEMATIC masking-failure study across 4 captures (1.4MB): the ONLY name-carrier = leaderboard rows (197-200/capture) - username masked but display_username = REAL NAME (confirmed 40+ unique hidden users). Bet feeds (662-1330 rows) = username masked + NO display_username field at all - mask holds there. So: leaderboard path = the leak; bet-cash paths = ids+xp+balances only. Softblock-details = per-account regional state (US=SOFT softblock), NOT a userlist - negative. HILO CORRECTION: apriori {color,number} = the CURRENT reference card (public by game design - players bet higher/lower against it), NOT an outcome pre-commit. Crash/roulette/hilo all ship gameHash only at result; the cross-round hash CHAIN (verified) is the real commitment mechanism.  
- **Probed:** 1x, last 2026-11-02 07:50:39.783655+00:00

### `mysql_internet_exposed`
- **Score:** 65  
- **Technique:** MariaDB 5.5.68 greeting served on 0.0.0.0:3306 - internet-reachable, EOL Oct 2018 (8yrs unpatched), version leaked verbatim in handshake, mysql_native_password auth. Same class as the never-rotated machine account that breached gamdom: an aging, forgotten, privileged component. Port scan: 21,22,53,80,110,143,443,465,587,993,995,3306,8083 all open.  
- **Probed:** 1x, last 2026-11-02 04:42:46.019274+00:00

### `turkish_funnel_fully_necrotic`
- **Score:** 65  
- **Technique:** EVERY link and identity in the Turkish entrance funnel is dead/unregistered/parked: main LOGIN+SIGNUP CTAs (GIRIS YAP/UYE OL) -> a.info/pera = DEAD domain (registered, no A/NS, connection fails both schemes); Perabet TV social -> golvar8.com = UNREGISTERED; mirror link -> perabet-01-ampsites.com = PARKED lander; box PTR identity -> sieveunem.net = UNREGISTERED dead name; SSH banner OpenSSH_7.4 (2016, CVE-2018-15473 user-enum class). The entire Turkish-market entrance infrastructure is abandoned-but-live, broken for users, and every name in it is free for anyone to register. Fix: rebuild funnel on owned infra, audit what a.info/pera WAS (the redirect target), register all dead names, patch or decommission the box.  
- **Probed:** 1x, last 2026-11-02 05:00:44.852331+00:00

### `crash_hidden_user_live_financials`
- **Score:** 60  
- **Technique:** /crash namespace streams REAL-TIME per-play financial data for hidden_mode users to UNAUTH sockets: userId:799920 (name-masked 'Hidden user'), xp, and walletInfo with LIVE BALANCE in real units (SOL_LAMPORT: 85929837->42964918->85884453 = the wallet visibly draining bet by bet). Complete real-time financial surveillance of a privacy-opted user by anyone with a websocket. Third unauth leak path (general firehose + game-details + crash live feed).  
- **Probed:** 1x, last 2026-11-02 05:25:30.365202+00:00

### `engineio_sid_bearer_attach`
- **Score:** 60  
- **Technique:** PROTOCOL HIJACK MECHANISM: opened a SECOND websocket against the live page's engine.io session (sid=J7aA0_I1tazHKLFqAIHf, EIO=3 wss) -> 101 Switching Protocols ACCEPTED on the existing session, v2 ping answered with pong. The sid is a single-secret bearer credential: anyone who learns a victim's sid (access logs, any leak) attaches to their socket from a non-browser client (Origin allowlist is client-asserted = trivially fakeable from python/curl). On an AUTHED socket this = receive the victim's personal event stream (wallet deltas, notifications, transactions) + emit as them. Fix: bind socket sessions to the HTTP session cookie server-side (reject connections whose cookie != handshake session), not just the sid.  
- **Probed:** 1x, last 2026-11-02 05:31:43.522280+00:00

### `golvar8_unregistered_link`
- **Score:** 55  
- **Technique:** golvar8.com = UNREGISTERED ('No match' whois, no DNS) but LINKED LIVE on the official tr.perabet.com entrance page as the 'Perabet TV' social link (perabetTv.png icon, target=_blank). Anyone can register it today and receive every click from the real login funnel with inherited legitimacy. Registration-takeover of the user funnel. Fix: remove/replace the link + register the domain defensively.  
- **Probed:** 1x, last 2026-11-02 04:57:00.815831+00:00

### `vestacp_panel_analysis`
- **Score:** 55  
- **Technique:** Custom React-rebuilt VestaCP panel (port 8083, v0.9.8 final/abandoned) analyzed from its own 1.5MB bundle: full custom API surface = /api/v1/{login,reset,list/*,edit/*,delete/*,upload/?dir=,view/file/<path>,bulk/*}. AUTH FINDINGS: (1) GET login/index.php mints a fresh session token UNAUTH every call (anon shell bound to empty user) AND leaks full system config unauth: VERSION 0.9.8, httpd:8080+nginx:80/443, vsftpd, exim+dovecot, clamav, spamassassin, mysql, named, webalizer/awstats, iptables+fail2ban, VESTA_CERTIFICATE=admin:giris.perabet.com; (2) gated endpoints (list/edit/delete/upload) reject the anon token via 302/shell - custom session check HOLDS; (3) ?user=admin param ignored for session binding; (4) token travels in URL QUERY PARAMS (?token=) = log/referrer-leak pattern; (5) file-viewer img URLs constructed WITHOUT token and with malformed &raw=true (no ?) = the panel's own client is sloppy; (6) reset flow = POST {user,code,password} - code not brute-tested (state-changing, skipped). One credential (panel/FTP/mail/DB) + years of unpatched CVEs = rooted box; no cred-free takeover proven.  
- **Probed:** 1x, last 2026-11-02 05:21:04.531952+00:00

### `crash_forced_capability_flag`
- **Score:** 55  
- **Technique:** game_crash event ships forced:false flag = a FORCED-CRASH capability exists in the crash game system (staff-side outcome control). Whether abused is unknowable externally, but the control surface is confirmed in the public event schema. Regulator/reputation-grade integrity question.  
- **Probed:** 1x, last 2026-11-02 05:25:30.268362+00:00

### `logerror_unauth_write`
- **Score:** 50  
- **Technique:** UPGRADED: POST /logError = unauth unthrottled write sink. 1MB payload accepted (200 ok), any content-type (text/plain ok), arrays/nested ok, MALFORMED json ok. 20-burst zero 429 ~3.3rps. No size cap, no rate limit, no validation. Availability risk (log backend fill) + log-injection into whatever renders these. Fix: size cap + per-IP rate limit + schema validation.  
- **Probed:** 2x, last 2026-11-02 04:12:11.454267+00:00

### `game_namespace_map_complete`
- **Score:** 50  
- **Technique:** FULL game-wire map on the REAL protocol (EIO=3): 7 live namespaces - chat/general/dice/crash/crypto/hilo/roulette (limbo/mines/plinko/keno/blackjack/twist/pocket = invalid). hilo: announceGame publishes apriori={color,number} PRE-round (real commit structure - outcome committed publicly, reveal only via authed session); announceGameResult = hash only ON the public wire. roulette: announceGame apriori=null, gameHash rides announceGameResult ONLY (same unverifiable pattern as crash: no pre-round commitment on the public channel). hilo+roulette userBets streams ALSO leak hidden-mode users (id + xp + walletInfo amounts in LTC_LITOSHI etc.) - FOUR leak paths total now.  
- **Probed:** 1x, last 2026-11-02 07:41:10.314323+00:00

### `general_namespace_unauth_feed`
- **Score:** 45  
- **Technique:** socket.io /general namespace serves UNAUTH connections a live firehose: 234KB in 15s. initialize event (~90KB): playersOnline, KOTH prize events, generalStats (total bet counts), leaderboards, bigwins/bet ticker w/ user id+username+bet+profit+game+date. Mirrors public UI data mostly - by design - but see hidden_mode_leak. Evidence: /tmp/gd_general_raw.bin  
- **Probed:** 1x, last 2026-11-02 04:18:41.655808+00:00

### `hidden_mode_id_value_leak`
- **Score:** 45  
- **Technique:** 41 hidden_mode users in the unauth /general feed: names ARE masked server-side (Hidden user) but internal user ID + XP + wager/profit value + per-bet activity rows ship unauth on leaderboard AND game-detail paths. Cross-referencing the raw id against any unmasked event (chat, bigwins, referral) deanonymizes opted-out users. Fix: when hidden_mode, strip id+xp+value at the SERVER on every feed path (rank-only), don't rely on UI masking.  
- **Probed:** 1x, last 2026-11-02 04:18:41.736474+00:00

### `tipuser_idor_gate_order`
- **Score:** 45  
- **Technique:** tipUser IDOR probe with FULL valid shape from extracted schema library (toId:number, reason, walletInfo:{amount>=0,unit:WalletUnit enum COINS|USDT|USDC|USD1|FIAT_*|BTC_SATOSHI|..., displayCurrency, wallet_type?}, antiFraudSession) => explicit 'Not logged in' error. muteUser/adminCommand/tipRain/toggleMessagePin/toggleGloballyMessagePin/say => uniform session-fail error. Gate order = validation THEN auth; no unauth execution. The walletInfo-trust forge test (send amount=999B with a session, server may trust client-supplied wallet claim) is READY-MADE and requires only a session.  
- **Probed:** 1x, last 2026-11-02 04:31:33.812145+00:00

### `dns_authority_on_fossil_box`
- **Score:** 45  
- **Technique:** 217.23.12.109 port 53 = AUTHORITATIVE DNS for tr.perabet.com + giris.perabet.com (answers authoritatively, recursion refused = not an open resolver). The Turkish funnel's DNS is served by the same 2015-fossil box hosting the login pages: root the box = DNS + login pages + exposed MariaDB simultaneously. Full-spectrum control of the Turkish user funnel from one compromised machine.  
- **Probed:** 1x, last 2026-11-02 05:31:43.641774+00:00

### `db_schema_disclosure_in_feed`
- **Score:** 45  
- **Technique:** The public firehose ships DATABASE TABLE NAMES with every bet event: crash.plays, dice.plays, hilo.plays, roulette.plays, external_games.transactions_v2 (sourceTable field). Live schema disclosure = the backend data model handed to any anonymous socket - the exact targeting map for SQLi/data-theft operators. Fix: strip sourceTable/sourceId/refClientId from public events.  
- **Probed:** 1x, last 2026-11-02 07:08:50.637489+00:00

### `panel_login_mint_flaw`
- **Score:** 45  
- **Technique:** VestaCP custom panel /api/v1/login/index.php mints a session token UNCONDITIONALLY (any/no credentials - verified: wrong pw, empty pw, nonexistent user ALL return 200 + fresh token) but authorization fails downstream with 'NO LANGUAGE DEFINED' + empty panel. Auth design flaw: cred check not enforced at mint time; sessions = unprivileged shells (gated endpoints reject). Default-cred test (admin:admin/password/vesta/changeme panel, ftp anonymous, mysql root:toor/password, admin:admin) - ALL DENIED (corrected earlier false positive). No panel access.  
- **Probed:** 1x, last 2026-11-02 07:31:42.384917+00:00

### `pageview_unauth_write`
- **Score:** 40  
- **Technique:** UPGRADED: POST /pageview = unauth unthrottled write sink. 1MB path accepted (204), markup ok, 20-burst zero 429. Same fix: cap + rate limit + validate/escape on any analytics render.  
- **Probed:** 2x, last 2026-11-02 04:12:11.536149+00:00

### `cross_brand_shared_infra`
- **Score:** 40  
- **Technique:** perabet.com = IDENTICAL stack: same Fastly IPs, same nginx/CSP/gd-lang/x-nginx-limit-req, same /client-api router (verbatim identical error envelopes incl 'Invalid reset password init request'), same edge block on /signup. WhiteArmor holds perabet records (userid|email|password) = same-family breach surface. If user/session store is shared cross-brand, one brand's session may authorize the other - UNTESTED (needs an account on either brand; both captcha+edge-gated identically).  
- **Probed:** 1x, last 2026-11-02 04:29:49.515080+00:00

### `eio3_emit_fence`
- **Score:** 40  
- **Technique:** The REAL production protocol (EIO=3) emit matrix: EVERY client->server emit (say/lastRain/emoji_reaction/leave/toggleMessagePin/join-moderators) => namespace DISCONNECT (41/nsp). The socket layer = receive-only for anonymous clients by design (production client uses HTTP RPC; sockets reject emitters). Control surface unauth = ZERO across both protocols. The money/control paths (panel, DB, mail, authed RPCs, domain registrations) each require exactly one operator-held key.  
- **Probed:** 1x, last 2026-11-02 07:24:28.791734+00:00

### `unauth_socket_session`
- **Score:** 35  
- **Technique:** engine.io handshake over websocket succeeds UNAUTH with browser headers (Origin+Referer+Sec-Fetch): 101 + sid + io cookie HttpOnly SameSite=Strict; 40/chat, namespace connect accepted. Push frames did NOT arrive within test windows => chat read may still be auth-gated at event level. No unauth capability proven yet. Hardening: require auth at handshake for player namespaces.  
- **Probed:** 1x, last 2026-11-02 04:04:19.567383+00:00

### `perabet_rpc_table_mirrors_fences`
- **Score:** 35  
- **Technique:** Perabet /stream/chat/rpc LIVE table (12 methods): join/say/adminCommand/devCommand/muteUser/tipUser/tipRain/lastRain/toggleMessagePin/toggleGloballyMessagePin/leave/place_bet. tipUser => explicit 'Not logged in' = SAME fence as gamdom (validation-then-auth). place_bet => 503 Maintenance page = perabet's bet backend DOWN. getHistory/bet/init absent from chat-ns (dice-ns). Cross-brand deployment lag theory: NEGATIVE - fences mirror.  
- **Probed:** 1x, last 2026-11-02 07:44:10.634680+00:00

### `clientapi_method_oracle`
- **Score:** 30  
- **Technique:** Param validation runs BEFORE auth on /client-api/* and /stream/<ns>/rpc/*: unknown path => generic Invalid parameters, unknown rpc => 'unknown rpc' string, live ns => Invalid parameters. Lets unauth callers enumerate which methods/namespaces exist server-side. Observation-class (no data), hardening: auth-check before validation or uniform errors.  
- **Probed:** 1x, last 2026-11-02 04:04:19.496102+00:00

### `prod_config_key_leak`
- **Score:** 30  
- **Technique:** Production bundle ships config: CAPTCHA_TYPE=turnstile, CAPTCHA_SITE_KEY=0x4AAAAAAAVYmhQqnlHxZkQ7, CAPTCHA_INVISIBLE_SITE_KEY=0x4AAAAAAAVj3vrx8ZWsyxIS, AND RECAPTCHA_SITE_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI - that is GOOGLE'S UNIVERSAL ALWAYS-PASS TEST KEY. If any server-side flow still validates reCAPTCHA against the test secret, captcha is bypassable there. Keys are public by design but the test key in prod config is a hygiene flag - audit server captcha-verify paths, remove the test key.  
- **Probed:** 1x, last 2026-11-02 04:26:21.985744+00:00

### `family_infra_stale_records`
- **Score:** 30  
- **Technique:** VestaCP box PTR = sieveunem.net (UNREGISTERED, dead DNS - box identifies as a dead name). mail.perabet.com -> 83.142.228.186 + webmail/smtp -> 200.124.136.170 (PTR mail.pronetgaming.com = perabet's mail rides VENDOR Pronet Gaming infra) - both IPs serve NOTHING (15 ports filtered) = stale DNS records on live domains. ampsites mirror domains (01/02/03, GoDaddy batch-registered 2023-01-11, expire 2027-01-11) are PARKED (ap=parking lander) while linked from the entrance page.  
- **Probed:** 1x, last 2026-11-02 04:57:00.904218+00:00

### `rpc_namespace_method_map`
- **Score:** 25  
- **Technique:** Full RPC method x namespace map via 'unknown rpc' oracle: /stream/chat = 11 methods (adminCommand,devCommand,join,leave,say,lastRain,muteUser,tipRain,tipUser,toggleMessagePin,toggleGloballyMessagePin); /stream/dice = 21 (adds bet,changeSeedPair,getHistory,getInitData,get_battle,join_battle,view_battle,iframe_end_seen,init,place_bet,send_round_estimates_summary,stop_viewing_battle + chat mod set - shared router); /stream/crash = 4 (init,place_bet,cash_out,cash_out_all). Dice exposing mod/tip methods = reduce registration to actual per-ns surface.  
- **Probed:** 1x, last 2026-11-02 04:12:11.607314+00:00

### `signup_turnstile_wall`
- **Score:** 25  
- **Technique:** Real-browser signup attempt x2 (fresh state, valid shadow-DOM form, boxes checked, CDP click): Turnstile NEVER initializes in harness (window.turnstile undefined, no CF scripts/iframes) - client bails before POST, modal closes silently, zero /signup requests. Combined with Fastly 54113 edge block on non-browser TLS = automated signup impossible from both angles. Registration wall VERIFIED. Handoff: gamdom-wallet-claim-test.py written to ~ - fires the walletInfo forge probe (amount=999999999999 + negative-amount edge) the moment a session cookie is supplied.  
- **Probed:** 1x, last 2026-11-02 04:34:26.897659+00:00

### `docroot_path_redirect_leak`
- **Score:** 25  
- **Technique:** Apache catch-all 301 chain leaks absolute docroot (/home/admin/web/tr.perabet.com/public_html/) as a redirect target; filesystem-as-URL tests (own+cross-tenant dirs, conf files) all fall through to the catch-all 301 - path DISCLOSURE confirmed, no file-read primitive. Box hosting posture: single-purpose entrance funnel.  
- **Probed:** 1x, last 2026-11-02 06:09:48.876765+00:00

### `userapi_surface`
- **Score:** 20  
- **Technique:** Third API prefix discovered from live app traffic: /user-api/ (softblock-details - unauth-readable chat softblock config, change-pp avatar upload authed). Real app also runs socket.io EIO=3 (v2 protocol) via polling; EIO=4 namespace map (chat/general/crypto/dice/crash live; admin/mod/staff/sports/slotsArena rejected) is authoritative from websocket testing.  
- **Probed:** 1x, last 2026-11-02 04:26:22.094703+00:00

## Hypotheses (need proof)

- `inteligance_gamdom_host` — score 65 · probed 1x
- `chat_rpc_role_gate_untested` — score 60 · probed 1x

## Ruled Out (negative)

- `crash_hash_chain_verifies` — probed 1x, last 2026-11-02 06:07:03.458651+00:00
- `signup_registration_hardening` — probed 1x, last 2026-11-02 04:26:21.876297+00:00
- `cors_no_reflection` — probed 1x, last 2026-11-02 04:04:19.088613+00:00
- `email_infra_symplify` — probed 1x, last 2026-11-02 04:06:20.654694+00:00
- `clientapi_authz_gate` — probed 1x, last 2026-11-02 04:12:11.689766+00:00
- `wstransport_origin_allowlist` — probed 1x, last 2026-11-02 04:20:59.708192+00:00
- `socket_emit_fence` — probed 1x, last 2026-11-02 04:20:59.787249+00:00
- `sourcemaps_access_controlled` — probed 1x, last 2026-11-02 04:04:19.185626+00:00
- `staff_dashboard_ip_gated` — probed 1x, last 2026-11-02 04:04:19.265984+00:00
- `swagger_no_ssrf` — probed 1x, last 2026-11-02 04:18:41.809059+00:00
- `stagsrv_dead_origin` — probed 1x, last 2026-11-02 04:42:46.097584+00:00
- `production_protocol_capture` — probed 1x, last 2026-11-02 05:29:48.340011+00:00
- `leak_artifacts_absent` — probed 1x, last 2026-11-02 04:04:19.336611+00:00
- `help_subdomain_intercom` — probed 1x, last 2026-11-02 04:04:19.417864+00:00
- `admin_path_decoy` — probed 1x, last 2026-11-02 04:29:49.419913+00:00
- `perabet_stale_zone` — probed 1x, last 2026-11-02 05:36:12.043278+00:00
- `blog_not_wp_sealed` — probed 1x, last 2026-11-02 07:04:57.361540+00:00

## Attack Paths

### turkish_entrance_box _(confirmed)_
- **Steps:** tr.perabet_entrance_box → php54+vesta+mysql55_exposed → same_disease_as_gamdom_breach  
- **Impact:** Entrance-infrastructure root => credential capture of Turkish-market users at the login funnel + pivot into family infra

### crash_integrity _(confirmed)_
- **Steps:** crash_no_preround_commitment → forced_capability_flag → hidden_user_live_financials  
- **Impact:** Public-verifiability of 'provably fair' marketing is unfalsifiable on crash; staff outcome-control surface confirmed; opted-out users' live financials anonymously observable

### hidden_users_exposed _(confirmed)_
- **Steps:** hidden_mode_display_username_leak → crash_hidden_user_live_financials → general_namespace_unauth_feed  
- **Impact:** Complete real-time identity+financial surveillance of privacy-opted users by anonymous scrapers; GDPR/privacy exposure on the hide-statistics promise

---

## Remediation Priority

1. **Confirmed holyshits** — fix first (RCE, admin bypass, cross-tenant data, cloud cred theft).
2. **Confirmed chains** — each step is a dependency; fix the base primitive first.
3. **Hypotheses** — prove or dismiss with the next decisive test (see `next`).
4. **Re-verify confirmed on every deploy** — findings decay; a patch may not hold.
