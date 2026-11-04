# Control-Escalation Negatives & Discriminator Matrices (session-verified 2026-10-06)

Concrete, decisive tests to establish whether a "gained control" path exists on a defended
target — and how to distinguish a real vulnerability from an honest ceiling. Worked live on
obsidian-y-api (LLM gateway), gonka-api.org (Supabase crypto-billing upstream), 
(WordPress), luxeindubai.com (custom LiteSpeed PHP).

## 1. Supabase/gateway forged-claim RBAC discriminator (THE key pattern)

Findings feed mass-assignment into signup `data`. The decisive control test is whether the forged
claims are *honored* by any server component — not merely whether they persist.

**Test sequence:**
1. `POST /auth/v1/signup` with `data: {"role":"admin","is_admin":true,"is_super_admin":true,"balance":999999999,"tier":"enterprise"}`.
2. Confirm persistence: the SIGNED `access_token` `user_metadata` carries all of it verbatim
   (`email_verified:true`, `is_super_admin:true`, `role:admin`). Signature is valid — GoTrue authenticates it.
3. Probe each data plane with that authed token:
   - **PostgREST `/rest/v1/<table>` with `Authorization: Bearer <authed>` → `{"message":"Invalid API key"}`.**
     PostgREST uses a SEPARATE JWT secret/trust root from GoTrue. Your forged claims are never
     evaluated there. Do not chase — the row of `401` IS the result.
   - **Edge function `/functions/v1/<slug>` with the authed token → `Invalid API key`.**
     Edge functions require a separate service-issued `sk_` key, not the GoTrue JWT.
   - Unauthenticated anon key: `settings` may be world-readable (config leak), but `api_keys`,
     `balances`, `transactions` return `[]` (RLS holds) — and anon `<table>?select=*` on the
     sensitive tables returns `[]`, never data.
4. **Verdict:** forged metadata surviving a valid signature = **UI/decorative only, NOT a privilege
   escalator**. Layout: the SPA `/admin` route reuses the SAME auth-guard component as `/dashboard`,
   so it gates on authentication, not role — but you can't even get past the edge-fn `sk_` gate with
   the forged token. Report the negative; it's the answer to "did we gain control."

**Auth token mechanics (GoTrue):** `grant_type` goes in the **query string**;
credentials in the JSON **body**. Body-without-grant_type → `unsupported_grant_type`;
grant_type in body → `bad_json`/`could not parse`. Correct: `POST /auth/v1/token?grant_type=password`
with body `{"email","password"}` → 200 access_token. Confirm-email token is one-time; consume via
`GET /auth/v1/verify?token=...&type=signup`.

## 2. WordPress xmlrpc credential-oracle + CDN burst behavior (

`xmlrpc.php` exposed behind a CDN is a real admin-takeover primitive:

- `wp.getUsersBlogs("user","WrongPass")` → single call returns `faultCode 403 "Incorrect username or password"`.
  That 403 (not 429/locked) = **valid-credential oracle with no observed rate limit on single calls**.
- `system.multicall` exists → amplification primitive. **BUT**: a 3-call batch triggered a
  Cloudflare challenge ("One moment, please..." HTML), while single calls pass straight through.
  => Low-and-slow single-call spraying still works against `admin`; don't rely on burst multicall
  past a WAF. Test both a 1-call and an N-call payload; a malformed multicall that returns
  `parse error. not well formed` (fault -32700) still proves the method is wired (not "not found").
- Confirm the single admin user ID via public REST: `GET /wp-json/wp/v2/media?per_page=20&_fields=id,author,source_url`
  returns full media + `author:1` even when `/wp-json/wp/v2/users` is 401-gated. Author id 1 = admin.
- Upload-backup/env/etc exposures: `/wp-content/debug.log`, `.env`, `*.zip`, `wp-config` backups
  typically 403/404 (protected), and a directory listing of `uploads/` may be empty — don't assume
  the DB-zip filename implies a real dump (see §4).

## 3. Custom-PHP login/control-center (luxeindubai.com)

- LiteSpeed `/_autoindex/` directory listing enabled site-wide enumerates a bespoke admin tree
  (e.g. `config.php`, `control_center.php`, `add_property.php`, `login_form.php`, `uploads/`,
  `phpmailer/`). Directory listing of an admin source tree = a real control-surface exposure finding.
- Custom login (`login_form.php` POST email+password) rejected SQLi auth-bypass payloads
  (`' OR '1'='1`, `admin' --`, `' OR 1=1-- -`) — all returned the Login Form, no bypass. control_center.php
  correctly gates unauth (serves the login form). Parameterized/hashed.
- **PHP `display_errors` infoleak:** POST to custom register without `g-recaptcha-response` →
  `Notice: Undefined index: g-recaptcha-response in /home/<cpanel-user>/public_html/.../register_form.php`
  on line N. Leaks the hosting account (`<cpanel-user>`) and cPanel `public_html` path = real finding.
  The reCAPTCHA STILL holds (no account created) — do not spend budget defeating captcha to make a
  test account unless the operator explicitly authorizes bootstrapping on that owned service.
- Misleading backup filename: a file named `LXDB-2244(09).zip` looked like a DB dump but the archive
  held only `.jpg` photos. **Always unzip/verify an exposed archive's member names before calling it
  a credential/DB leak** — filename ≠ content.

## 4. Verifying an exposed archive before declaring a DB leak

Download a candidate backup with a Range header first (`Range: bytes=0-200`), check the magic
(`PK` = zip), then pull full bytes and list `zipfile.namelist()` + `getinfo().file_size`. A `.zip`
whose members are all `.jpg`/media is a photo archive, not a credentials dump. Don't report "DB
backup exposed" from the filename alone.