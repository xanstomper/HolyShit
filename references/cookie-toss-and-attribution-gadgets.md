# Cookie-Toss & Attribution Gadgets (tracker/attrib subdomains)

Any SPA with a tracker/attribution page (`media.`, `clever.`, `track.`, ad-landing hosts) that
writes URL params as cookies on the MAIN registrable domain is a cookie-toss platform. The
class: attacker-crafted links plant attacker-chosen cookies on the target's origin — device
identity, attribution, and sometimes session state.

## Recognition recipe

1. **Find the tracker pages** in the subdomain inventory (passive DNS/CT logs) and fetch each
   with a working browser fingerprint — they are small static pages (1–6 KB) whose only script
   reads `URLSearchParams` and writes `document.cookie`.
2. **Read the write logic**: the domain attribute (main registrable domain = the toss target),
   Max-Age (90d is typical), SameSite/Secure flags, the per-visit param cap, and the
   RESERVED-NAME blocklist.
3. **Blocklists are exact-match Set lookups** — the miss is the finding: prefixed session
   families (`stel_token` vs reserved `token`), identity cookies (`client-context`), and
   attribution cookies (`referralCode`) fall through while the literal names are blocked.
4. **Inventory the SPA's cookie STORES** (React store pattern: `(0,X.N)("name", default)`
   call sites; also `cookie.get(...)` helpers) to map what the app READS from tossable cookies
   — preference stores are noise; identity/attribution/session-adjacent stores are impact.

## Impact gates (test in order)

- **Fingerprint hijack**: identity cookie = a device-fingerprint visitorId (e.g. FingerprintJS
  Pro). The SPA typically SKIPS fingerprint generation when the cookie exists (early-return
  before the `import('https://fpjscdn.net/...')`). Verify end-to-end in a real browser:
  toss the cookie via the tracker page → navigate the main site → the value must SURVIVE the
  SPA load (not overwritten) AND the fingerprint library must NEVER be fetched (check the
  network log for the fp CDN) → the attacker value is the adopted device identity. Impact:
  device-ban evasion + risk-model poisoning. Verify the control too: without the toss the lib
  may load LAZILY (not at page load) — absence of the CDN fetch on page load alone is NOT the
  discriminator; the toss-survival is.
- **Attribution/affiliate hijack**: attribution cookies (`stag`, referral) read at signup —
  an attacker link claims commission on the victim's deposits forever. Watch for a
  force-set FIXED default tag (their own ad pipeline) proving the cookie drives attribution.
- **Session fixation surface**: session cookie names missing from the reserved list = plantable.
  The verdict needs the server's Set-Cookie attributes from a real login (host-only vs domain,
  path scope) — before a session exists, rate as a surface, not a chain.

## Fleet spread

Inventory EVERY mirror/sibling domain's tracker hosts — the gadget is copy-pasted per brand.
One confirmed gadget on the primary + one on any mirror = fleet-wide claim.

## Fixes to recommend

Allowlist (not blocklist) writable params; refuse writes matching session-family prefixes;
signed/short-lived attribution tokens validated server-side at signup; treat identity cookies
as untrusted client input and re-verify server-side before risk decisions.
