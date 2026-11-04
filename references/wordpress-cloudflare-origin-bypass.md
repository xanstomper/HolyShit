# WordPress / WooCommerce — Cloudflare Origin Bypass & WP Recon (session-verified 2026-10-06, 

A hardened WordPress/WooCommerce storefront sitting behind Cloudflare. Complete playbook for
reaching the raw origin, fingerprinting the stack, and triaging the real control surface.

## 1. Find the origin IP (bypass the CF WAF entirely)

The single highest-leverage move on any Cloudflare-fronted target. Once you have the true
origin IP, the entire WAF/challenge stack is moot — you talk straight to the backend.

**Origin-leak sources (key-free):**
- **SPF record first.** `dig +short <target> TXT @1.1.1.1`. A `v=spf1 ip4:<ip>` entry leaks the
  real sending/origin host. On .163.60 ~all` → origin at that IP,
  **not** behind CF (CF anycast IPs are 104.21.x / 172.67.x). This was the instant win.
- MX records can leak the mail host (which may share origin infra).
- crt.sh (`https://crt.sh/?q=%25.domain&output=json`) for subdomain discovery — flaky (502),
  retry with backoff.
- Memory/env intel (known hosting netblocks, e.g. `bacloud.info 88.119.163.0/24`).

**Verify the origin serves the target:** connect with SNI set to the Host AND send the
`Host:` header, using a TLS context that skips hostname verification (origin cert may not cover
every vhost):

```python
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
conn = http.client.HTTPSConnection("88.119.163.60", 443, context=ctx, timeout=15)
conn.request("GET", "/", headers={"Host":""Mozilla/5.0 Chrome/124.0"})
```

If this returns WP/app content while `curl https://domain` yields a CF "One moment, please…"
challenge, **the WAF is bypassed**.

## 2. Use `http.client` over a raw socket, not curl/urllib, for origin work

When you must set an arbitrary `Host` + SNI and control TLS verification, `http.client` with
an unverified `SSLContext` is far cleaner than curl flag soup or raw `socket+ssl` string builds.
It also **handles chunked transfer-encoding automatically** — a raw TCP reader does not.

**Raw-socket chunking pitfall (hit this session):** a bare `socket+ssl` read returns the
chunked body *with* `10000\r\n` size-prefix lines interleaved. JSON.parse fails with
`Extra data: line 2 column 1 (char 7)`. Either (a) use `http.client` (auto-deframes), or (b)
manually decode: read hex size lines, consume that many bytes, repeat until `0`. Also note:
`re.search(bytes_pattern, str)` raises `TypeError: cannot use a string pattern on a bytes-like
object` — keep pattern/input types matched.

## 3. WordPress fingerprint — the open thing leaks everything

The homepage body (even under a 503/maintenance shell) carries the whole stack:
- `<meta name="generator" content="WordPress 6.7.3" />`, `WooCommerce 9.5.1`, `Elementor 3.26.4`.
- Asset paths in the HTML enumerate installed plugins:
  `re.findall(r'wp-content/(?:themes|plugins|uploads)/[\w\.\-]+', html)` →
  `elementor, pro-elements, ht-mega-for-elementor, qi-addons-for-elementor, funnel-builder, …`.
- Exact plugin versions from readme.txt: `GET /wp-content/plugins/<slug>/readme.txt` → regex
  `Stable tag[:：]\s*([0-9][\w\.\-]+)`. Some plugin readmes return 503/maintenance-shell; those
  are the ones to note as "version unknown, version file blocked".
- Server header inconsistency = multi-instance backend (flipped `LW_speed` ↔ `openresty/1.31.1.1`
  across requests) — a signal the app is load-balanced / partially in maintenance.

## 4. WP REST `_embed` user-enum bypass (beat stop-user-enumeration)

`/wp-json/wp/v2/users`, `/?author=N`, `?rest_route=/wp/v2/users` are all blocked by the
stop-user-enumeration plugin. BUT REST-embedded author objects still leak the admin:
```
GET /wp-json/wp/v2/posts?per_page=20&_embed
→ _embedded.author[] = {"id":1,"name":"":".../author/geo/"}
```
The `slug` is the **WordPress username** (here: sole admin `geo`). Scan posts/pages/any public
content type with `_embed` and collect every distinct `slug`. Always check the WP REST route
index first: `GET /wp-json/` returns every namespace + route + method (huge recon goldmine —
844 routes on 

## 5. Admin-ajax unauth action sweep

Many plugins register `wp_ajax_nopriv_*` handlers that are genuinely public. Sweep:
`POST /wp-admin/admin-ajax.php` with `action=<name>` for each plugin's likely handler names.
- `200` + meaningful JSON = LIVE unauth handler (hit the jackpot).
- `200` body `0` or `-1` = handler ran but dismissed/empty (still registered → tune params).
- `400` = no such handler.
On d 400 — origin is uniformly gated.

## 6. Coming-soon / maintenance-mode discriminator (login brute NOT viable)

A site in LiteSpeed/coming-soon maintenance serves bulk `503 Retry-After: 600` on `/` and store
pages while still serving REST + assets. **The decisive test for "is the login backend actually
processing auth":** POST a bogus credential to `wp-login.php` and `/my-account/`:
- Real login → `302` redirect, or `200` with `#login_error` div / `woocommerce-error`, a
  `set-cookie` test cookie, and the `name="log"`/`name="user_login"` field.
- **Maintenance-shell auth** → `200` with the generic "DOCTYPE html / charset=utf8 / viewport"
  page, **no login form, no error oracle, no set-cookie**. The login backend is NOT reachable
  even at the origin → **credential brute is a dead end right now**, regardless of username or
  origin access. Document it as a negative blocker and route the control chain to the
  maintenance-bypass or plugin-CVE instead.

## 7. Sensitive-file soft-404 discriminator (don't false-positive)

On this origin, every missing path under `.env.bak`, `/.htpasswd`, `/backup.zip`, `/dump.sql`,
`/.git/config`, `/wp-config.php` returned **`200 text/html`** with the same generic
"DOCTYPE html / charset=utf8 / viewport" page. That identical template is a **custom soft-404**,
NOT file content. Discriminate by body: real secrets would differ / be smaller; an identical
shell = file does not exist. A plain `st==200` is a false-positive trap.

## 8. Loud-but-hardened: `wp-admin/install.php` and xmlrpc

- `wp-admin/install.php` returning 200 with "WordPress Already Installed" = DB configured, no
  installer takeover (a 200 with the actual install form = critical).
- `xmlrpc.php` returning `405` = blocked (no XML-RPC brute/pingback). `401/403` on
  `wp-login.php?action=lostpassword` etc. = username-oracle closed.

## Ledger pitfalls
- `holyleadger chain` splits the chain value on `-->`. If you embed `->` in the `--impact` text,
  the chain parser fragment and you get "1 step". Keep `--impact` free of arrow sequences.
- Statuses are lowercase (`confirmed|negative|hypothesis`). Set `HOLYSHIT_TARGET=<domain>` or pass
  `--target` or every `add` fails.

## Worked case numbers (
- origin_ip_exposed = confirmed 90, wp_admin_username_enum = confirmed 70 (slug **geo**, ID 1,
  sole admin), wordpress_stack_inventory = confirmed 55.
- auth_surface_hardened = negative 85, site_in_coming_soon = negative 70 (blocks the login chain).
- Control chain recorded: origin_ip_exposed → CF WAF bypass → direct-origin wp-admin → admin
  "geo" credential access → wp-admin → plugin/theme RCE → full control. Presently blocked by
  maintenance mode.