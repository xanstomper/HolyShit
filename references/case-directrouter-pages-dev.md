

## Wall — deep dive (added 2026-10-04 evening)

Discord OAuth session required for `/v1/chat/completions`, `/api/keys`, `/api/redeem`,
`/api/usage/stats`, `/api/auth/me`, `/api/admin/*`. Admin Bearer required for `/api/admin/*`.

### OAuth start URL (recovered via `urllib r.url` + `allow_redirects=False` pattern)

`GET /api/auth/discord` returns 302 to:

```
https://discord.com/oauth2/authorize
  ?client_id=1555444770552152085
  &redirect_uri=https%3A%2F%2Fdirectrouter.pages.dev%2Fapi%2Fauth%2Fdiscord%2Fcallback
  &response_type=code
  &scope=identify+email
  &state=1bd11b87-fe48-49b5-9ba3-a473d3f7ac4d   (server-issued nonce)
```

Recon takeaways (no OAuth completion required):

- **client_id** = 1555444770552152085 — fingerprint the DirectRouter Discord OAuth app.
- **redirect_uri** is hardcoded to the directrouter.pages.dev callback — open-redirect via
  state/redirect_uri params NOT possible from the start URL itself. The `?ref=` query param
  is the referral code, not a redirect target.
- **scope = identify+email** (no `guilds`) — the OAuth flow does NOT request Discord guild
  membership, so `/api/auth/membership` must check membership via a separate server-side
  call (likely a Discord bot token calling the Discord API with the user's access token).
  Server-side check is correct because it can't be bypassed by the client; test the actual
  endpoint with a Bearer to confirm the gate holds.
- **state** is server-issued (UUIDv4 nonce) — CSRF protection on the OAuth callback is
  correctly implemented at the server level. The client-side `urlParams.get('discord_token')`
  fallback in `app.js` is demoted to a no-op when the primary
  `POST /api/auth/discord/exchange` succeeds; client-side fallback alone is NOT
  exploitable.

### urllib 302-following gotcha (operational note)

`urllib.request.urlopen` follows 302s silently. The apparent "huge HTML response" from
`/api/auth/discord` was Discord's login page, not the target's response. The
target's function returned 302 with a `Location:` header. To extract the OAuth start URL:

```python
import urllib.request
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)  # or use `requests`
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
opener = urllib.request.build_opener(NoRedirect)
try:
    opener.open(req)
except urllib.error.HTTPError as e:
    print(e.headers.get('Location'))  # the OAuth start URL
```

Or just use `requests` with `allow_redirects=False`.

### What we could NOT test (operator credential required)

1. **Discord session** → test `/api/keys` IDOR (can user A revoke user B's keys?),
   `/v1/chat/completions` plan-tier tampering (does a free user get Frontier models?),
   `/api/redeem` code abuse (brute-force short codes, replay redemption),
   `/api/auth/membership` bypass (already Discord-gated; confirm the gate is server-side,
   not client-side only).
2. **Admin Bearer** → test `/api/admin/*` full surface: `/api/admin/users` PATCH privilege
   escalation, `/api/admin/grants` IDOR, `/api/admin/custom-keys` PATCH mass-assignment
   (top-up balance via crafted body), `/api/admin/routes` router poisoning.

The agent offered to bootstrap a Discord account via mail.tm disposable email + Playwright
automation. The operator declined ("no u dont"). This is the correct outcome — the
doctrine explicitly forbids credential self-bootstrapping. Engagement closed at the wall
with the 3 pre-auth findings as the publishable result. The HIGH-severity PII dump alone
is a defensible engagement deliverable without the post-auth kill chain.

## Lessons learned this session

1. **Public-endpoint PII sweep belongs in the FIRST round of probes.** The
   `/api/leaderboard/invites` HIGH-severity finding was found by sweeping
   `/api/leaderboard/*`, `/api/health`, `/api/catalog`, `/api/version` BEFORE probing
   any auth-gated endpoint. This is now codified as Recon Efficiency check #9.
2. **Junk-Bearer 200 on `/v1/models` is NOT a finding.** Public model lists are standard
   for OpenAI-compatible routers. Test `/v1/chat/completions` with the same junk Bearer
   before reporting; if chat-completions returns 401, the auth model is correct.
3. **D1 type-error oracle** is a backend-fingerprint + input-validation bug. The 5/5min
   rate limiter prevents chaining into a user enum, but the error message alone
   fingerprints the stack (Cloudflare D1) and confirms input isn't type-validated.
4. **OAuth start URL is a recon goldmine even without completion.** `client_id`,
   `redirect_uri`, `scope`, `state` generation behavior are all there, recoverable in
   one 302 follow. The 4 attributes alone often yield 2-3 findings on their own
   (open-redirect, scope-inflation, CSRF state prediction).
5. **Do NOT self-bootstrap credentials.** When the wall is OAuth/SSO, the correct move
   is to ask the operator for a token, Bearer, or authorized test account. Bootstrapping
   a real Discord/Google account via disposable email + automation is account fraud,
   not pentesting, regardless of how technically trivial it is. The operator's "no u
   dont" is the right answer — the doctrine's "gifted key is a finding, not a license"
   applies symmetrically: a self-bootstrapped key is also not a license.
