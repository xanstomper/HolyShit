# Full-Target Teardown Playbook — "Holy Shit" Hunting

Companion to the HolyShit! mandate. Phase-ordered methodology for taking a website +
infrastructure apart end-to-end and surfacing critical-severity findings. Run under written
authorization; every technique here is discovery/documentation oriented.

## PHASE 0 — AUTHORIZATION PIN
- Pin scope doc, target list (domains/ASNs/IP ranges), RoE before touching anything.
- Anything outside the doc = OUT, log it and route to disclosure instead.

## PHASE 1 — PASSIVE RECON (no target contact)
- **Certificate transparency**: crt.sh / censys on `%.target.tld` — subdomains the operator forgot.
- **ASN/whois**: netblocks, hosting provider, named orgs, corporate acronyms.
- **Wayback CDX**: `/cdx/search/cdx?url=<host>*&output=json&collapse=urlkey` — full asset
  history. Old bundles, .well-known/, old ?v= query strings, deleted pages.
- **Search-engine dorking**: site:, filetype:, inurl: — exposed configs, dumps, admin panels.
- **GitHub/org leak hunting**: API keys, internal hostnames, CI configs, .env patterns in
  operator-visible repos and gists referencing the target.
- **Artifact-first**: operator's own vault/notes/baselines before anything else.
- Deliverable: target map + forgotten-asset list. Forgotten assets = highest-yield entry.

## PHASE 2 — INFRASTRUCTURE MAPPING
- **DNS dump**: A/AAAA/CNAME/MX/TXT/NS/SRV + zone-attempt. CNAME chains → dangling subdomain
  takeover (CNAME → deprovisioned cloud service = HOLY SHIT: takeover).
- **Port/service surface**: only within scope. Map CDN/WAF (headers, ASN, TLS fingerprint).
  Origin discovery via: historical DNS (SecurityTrails-class), old cert SANs, old Wayback
  references, direct IP scans of known netblocks, mail-header leaks.
- **WAF fingerprinting**: response header quirks, block-page signatures, challenge behavior.
  Record what evasion class is even necessary.
- **Cloud posture**: public buckets (S3/GCS/Azure blob naming patterns), exposed object
  listings, metadata endpoints, Cloudflare-only vs origin-direct behavior.
- Deliverable: asset graph, origin map, WAF/CDN posture, dangling-takeover candidates.

## PHASE 3 — CLIENT-SIDE DEEP MINE
- **Bundle inventory**: every script tag (app.js AND giveaway.js/providers.js/membership.js
  etc.), size baseline saved (`~/.hermes/scripts/<target>_baseline.json`).
- **Endpoint extraction**: regex /api/ from ALL bundles; diff against Wayback old versions —
  ghost routes (removed-from-frontend, still-live-backend).
- **Secrets sweep**: hardcoded keys, tokens, internal URLs, debug flags, sourcemaps (map files
  often still deployed — HOLY SHIT: full original source).
- **Client-only trust checks**: window.* globals, client-side gates (console-call bypass),
  client-side validation of payments/rates/limits.
- Deliverable: endpoint list (live vs ghost), secret findings, client-trust violations.

## PHASE 4 — API SURFACE ASSAULT (read-only oracles)
- **405-matrix route verification**: wrong-method everything; real routes answer 405,
  ghosts answer 200 text/html. Build the true endpoint map.
- **Auth-seam taxonomy**: classify 401/403 error strings per endpoint — diverging strings =
  separate auth layers = prime bypass candidates.
- **IDOR/BOLA sweep**: on any owned test account, enumerate object IDs on every GET.
  Cross-tenant probes only with a second test account, never production users' data.
- **Type-coercion probes**: object-where-string (`{"param":{"a":1}}`), array smuggling,
  null/absent-field variation. Watch for 500s (disclose class) AND rate-limit dodges.
- **Rate-limit scope mapping**: which endpoints limited, per-IP keying basis, IPv4 vs IPv6
  pools, malformed-payload counting.
- **Mass assignment**: send extra fields (is_admin, role, credits, price) on POST/PUT to
  owned accounts — watch for acceptance.
- **GraphQL**: introspection enabled? depth/alias abuse, field-level auth gaps.
- Deliverable: true route map, seam-classified auth, coercion/500 classes, IDOR/assignment findings.

## PHASE 5 — AUTH & FLOW ANALYSIS
- **Session model**: where tokens live (cookie vs localStorage), flags (HttpOnly/Secure/
  SameSite), rotation on privilege change, fixation vectors, ?token= URL params (HOLY SHIT:
  session fixation via referrer/history).
- **OAuth flows**: state validation, redirect_uri validation, token-in-fragment leakage,
  PKCE enforcement.
- **Password/account flows**: enumeration via response/timing divergence, reset-token
  entropy and single-use enforcement.
- **Verification gates**: server-side verification or stateless claim gate? (hash-verify →
  empty-body claim + no server-to-server callback = farm hypothesis; CVSS ~7.5 documented).
- Deliverable: session/OAuth/reset findings, stateless-verification hypotheses.

## PHASE 6 — INFRA & DEPENDENCY ROT
- **External dependency health**: Discord invites (dead + undismissable gate = pre-loaded
  lockout), CDN scripts, widget endpoints, third-party SaaS the target depends on.
- **Software supply chain**: version-disclosed frameworks → known-CVE mapping (with
  exploited-or-not verification, not blind CVE spam).
- **Hot-deploy watch**: asset-size baseline diffs; half-shipped scaffolding (zero-call-site
  gates, {"enabled":false} widgets) cataloged as next-regression surface.
- **Mail/DNS records**: SPF/DMARC/DKIM gaps (spoofing), subdomain takeover via TXT/CNAME.
- Deliverable: rot findings, CVE map, regression-watch list.

## PHASE 7 — SERVER-SIDE CLASS PROBES (scoped, minimal)
- SQLi class: error-based + boolean oracle on clearly-input-reflected params first.
- SSRF: webhook/URL-import features → internal addresses (169.254.169.254 metadata =
  HOLY SHIT: cloud creds).
- XXE/SSRF in document processors; deserialization in session/upload paths.
- Upload handling: content-type/type-confusion, path traversal in filenames.
- Template injection in mail/report generators.
- Discipline: one probe per class on the most-likely param, escalate only on signal.

## PHASE 8 — CONSOLIDATE & REPORT
- **Severity ranking**: HOLY SHIT tier = RCE, auth bypass on admin, full PII access, cloud
  cred theft, takeover chains, stateless payment/claim gates. Then high → med → low.
- **Attack-path chains**: combine findings into kill-chain narratives (recon→impact).
- **Detection gaps** (if purple-team scope): per-finding, propose analytic coverage.
- **Disclosure**: host abuse contact, upstream provider ToS, regulator — for anything
  outside own-infrastructure boundary.
- Deliverable: executive summary, technique-mapped findings, chains, remediations, evidence appendix.

## HOLY SHIT SIGNATURES — highest-yield quick checks (one probe each)
1. Dangling CNAME → takeover
2. Deployed .map sourcemap → full source
3. Ghost route with no auth (content-type verified)
4. ?token= / ?discord_token= URL param session fixation
5. Metadata endpoint SSRF (169.254.169.254)
6. Stateless claim/verification gate (no server callback anywhere)
7. Client-only payment/credits/permission gate
8. Zero-call-site auth scaffolding (unwired gate = lockout or bypass depending on direction)
9. Public bucket with creds/backups
10. Rate limiter keyed to a header you control (X-Forwarded-For honored = unlimited budget)
