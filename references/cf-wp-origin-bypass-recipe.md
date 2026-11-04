# Cloudflare-fronted WordPress: Origin Discovery + Direct-Origin Testing Recipe

Generalizes to ANY WordPress/WooCommerce origin sitting behind Cloudflare. Works even when
the CF JS challenge (`One moment, please...`) blocks the public surface completely. Verified
2026-10-06 on  infra).

## 1. Origin IP discovery — the SPF leak (the #1 CF-origin reveal)

When the HTML surface is a CF JS challenge and you can't reach the origin, the origin IP is
often leaked by **SPF** (it must list the real sending/mail IP, which is usually the origin
host):

```
dig +short 
  "v=spf1 ip4:88.119.163.60 ~all"
```

The `ip4:` in SPF is frequently the origin octet. Confirm with `nmap -Pn -T4 --top-ports 60`
on that IP — an open 80/443 alongside mail ports (465/587/993) = it's a full web+mail origin,
not just a mail gateway. PTR (`saturnus.space`) confirms the host identity.

Other origin-leak sources when SPF is absent: crt.sh certificate transparency (look for
certs bound to the origin IP or non-CF SANs), historical DNS the operator forgot to update,
TLS SAN enumeration (`echo | openssl s_client ... | openssl x509 -noout -ext subjectAltName`),
and vhosts that resolve to non-CF IPs. Subdomain DNS is usually a dead end — everything
returns the CF anycast pair.

## 2. Direct-origin testing = WAF fully bypassed

Once you have the origin IP, you do NOT need to solve the CF JS challenge. Hit the IP
directly over raw TLS with the target's `Host:` header. `http.client.HTTPSConnection`
(paired with `_create_unverified_context`) handles TLS + chunked decoding for you:

```python
import ssl, http.client
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
c = http.client.HTTPSConnection("88.119.163.60", 443, context=ctx, timeout=12)
c.request("GET", "/", headers={"Host":""Mozilla/5.0 Chrome/124.0"})
r = c.getresponse(); body = r.read()
```

Every request then lands on the untouched origin with zero Cloudflare WAF/challenge in the
path — exploit payloads pass, admin/API fully reachable. This is the single highest-value
move on any CF-fronted WP target.

## 3. Maintenance/data-plane asymmetry (a mask, not a wall)

A coming-soon/maintenance mode often hard-503s the HTML storefront (`Retry-After: 600`) at
**vhost level** (not plugin-level — so cookie/XFF/IP "bypasses" do nothing) while the
**data plane serves 200**:

| Surface | Status behind 503 |
|---|---|
| `/`, `/wp-login.php`, `/my-account/`, store pages | 503 (masked) |
| `/wp-json/`, `/wp-json/wp/v2/*`, `/wp-json/wc/store/v1/*` | **200 (live)** |
| `/wp-content/..static assets`, `/wp-includes/version.php` | 200 |
| `/wp-admin/admin-post.php`, `/wp-admin/load-scripts.php` | 200 len=0 (execute, no mask) |
| `/wp-admin/*` rest, `/wp-login.php` POST | redirect to `/404/` or 503 |

So: never judge a masked site as "down/empty" from the HTML alone. Enumerate the full REST
surface (`/wp-json/` route index). The backend (products, orders, checkout, plugin endpoints)
is reachable; only the templates are hidden. This is where open-API findings live.

## 4. WP REST: stop-user-enumeration does NOT block embedded author leak

The `stop-user-enumeration` plugin blocks `/wp-json/wp/v2/users`, `/?author=N` (403/401), and
author pages — but **`/wp-json/wp/v2/posts?_embed` (and pages, any post type) leaks the admin's
username via the `_embedded.author` object**:

```json
"_embedded": {"author": [{"id":1, "name":"nk":"/author/geo/"}]}
```

`slug` IS the WordPress username. One request gets you the target admin account for
credential/CVE work even on a "hardened" install.

## 5. Open WooCommerce store API behind the mask

`/wp-json/wc/store/v1/products` (full catalog), `/cart`, `/products/attributes` serve openly
with no auth/no nonce. Checkout (`/checkout`) is POST-reachable and responds to validation
(400 `Missing parameter(s): billing_address`) but **cart add-item and checkout need a nonce**
(`woocommerce_rest_missing_nonce`) — so no order can be created without an authenticated
session. This is the boundary for "customer info" on a masked WC shop: catalog open, orders
gated.

## Negatives / hardened (log as coverage, don't re-probe)
- WP core auth enforced: `/wp/v2/users|settings|plugins`, `/wc/v3/*`, elementor/funnelkit/htmega
  writes all 401/403 (`woocommerce_rest_cannot_view`, `rest_forbidden`).
- xmlrpc.php 405 (blocked); admin-ajax everything 400 `0` (gated); `admin-post.php?action=*`
  → `wp_die` 400.
- Sensitive files (`.env`, `.env.bak`, `.git/config`, `wp-config.php.bak`, `*.sql`, `*.zip`)
  all return a **generic soft-404 HTML shell** (200 text/html `charset=utf8` + `viewport`),
  NOT real content. An all-200-on-every-path result = custom 404 template, not leaked files.
- `wp-admin/install.php` correctly shows "WordPress Already Installed" (no installer takeover).
- Maintenance 503 is vhost-level: XFF `127.0.0.1`/`localhost`, forged logged-in cookies, and
  wp-preview all fail to bypass.

## Python probing pitfalls (hit this session)
- `http.client` over raw sockets auto-de-chunks; raw `recv()` + manual parse does NOT — a
  `10000\r\n{...}\r\n...` prefix on `wp-json` is chunked-transfer remnants, not a malformed
  response. Use `http.client` for anything TCP/IP-based against a vhost origin.
- `re.finditer(...)[:15]` → `TypeError: 'callable_iterator' object is not subscriptable`.
  Wrap with `list()` or use `findall`.
- Don't mix `b'...' in str` — bytes vs str membership raises `TypeError`. Keep body as str or
  decode once.
- `http.client` with a dict split on `':'` for headers is fragile; pass the dict straight to
  the `headers=` kwarg.

## Stack fingerprint trick
Repeated `Server:` flips (LiteSpeed ↔ openresty/1.31.1.1) across connections = **multi-instance
load-balanced backend**, not a misread. Note both versions; CVE-match against the larger
surface (WordPress 6.7.3 / WooCommerce 9.5.1 / Elementor 3.26.4+Pro / HT Mega 2.7.8 / The Plus
6.2.2 / Qi Addons 1.8.9 / Funnel Builder 3.8.0 / Blocksy 2.0.84 / wp-statistics).

## Control-path chain (what "gaining control" requires here)
`origin_ip_exposed -> cf_waf_bypassed -> direct_origin_wp_admin -> admin_credential_access ->
wp-admin -> plugin/theme RCE -> full control`. The blocker on this target: native auth enforced
on all data endpoints (orders/customers/payment-gateway secrets need a session), maintenance is
vhost-level, so the remaining levers are (a) a known-CVE plugin exploit landing WAF-less against
the exact inventory, or (b) finding the admin password via sibling-domain/backup/source-mining.