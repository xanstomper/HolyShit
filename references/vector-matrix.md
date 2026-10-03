# Exhaustive Vector Matrix — Every Holy Shit Class

Completeness layer for the teardown playbook. When phases 1–7 signal nothing, sweep this
matrix top-to-bottom on scoped targets: one decisive probe per cell, log negative results as
coverage evidence. Cell format: CLASS — probe — holy-shit indicator.

## A. NETWORK / EDGE
- TLS: weak ciphers/certs, SAN leaks, hostname mismatch, cert pinning gaps — sslscan output
- HSTS/CSP/XFO/Referrer-Policy/CORS misconfig — `Origin: evil.test` reflection on authed endpoints = cred theft
- Request smuggling (CL.TE / TE.CL / TE.TE) — differential timing on front/back servers
- HTTP/2 & HTTP/3 quirks — rapid reset, header-name case desync, QPACK smuggling
- Host-header injection — password-reset poisoning, cache poisoning, SSRF pivot
- Web cache poisoning/deception — unkeyed input reflection (params, headers), X-Forwarded-* trust
- IP honoring — X-Forwarded-For / X-Real-IP / CF-Connecting-IP acceptance = limiter bypass + log poisoning
- Origin exposure — direct IP hit on discovered origin bypassing CDN protections entirely

## B. WEB APP — INPUT
- SQLi: error/boolean/time/stacked/OOB (DNS exfil) on every parameter class
- NoSQLi: `{"$ne":null}`, `$regex`/`$where` injection on JSON APIs
- Command injection: `;`/`|`/backtick/`$()`/newline variants, blind via DNS
- SSTI: `{{7*7}}` `${7*7}` `<%= 7*7 %>` in mailers/report generators/rendered fields
- Path traversal: `../` encoded/double/nested/null-byte; in filenames, ZIP entries, range headers
- XXE: file://, http:// SSRF pivot, OOB exfil, billion-laughs
- Open redirect: //evil, /\evil, %2F%2Fevil, @evil in redirect targets
- SSRF: URL-import/webhook features → 169.254.169.254, localhost, internal CIDRs, DNS rebinding
- Deserialization: Java (ysoserial classes), PHP (phar/unserialize gadgets), Python (pickle)
- Format-string/prototype pollution: `__proto__`, `constructor.prototype` in JSON merges

## C. WEB APP — AUTHZ
- IDOR/BOLA: every GET/PUT/DELETE with enumerateable IDs, cross-account only
- BFLA: privileged API actions replayed as low-priv test user
- Mass assignment: is_admin/role/verified/credits/price/owner_id injected on writes
- Hidden endpoints: ghost routes (playbook §3), debug endpoints (/debug, /actuator, /swagger, /api-docs, /.env)
- Client-only gates: frontend-hidden routes still callable (verify server-side 405/401)
- JWT: alg=none, kid injection, weak HMAC secret (hashcat), no audience check, key-confusion RS256→HS256
- Session: fixation via URL params, no rotation on privilege change, non-HttpOnly, missing SameSite
- OAuth: missing/predictable state, redirect_uri bypass (open-redirect chains), token-in-fragment, PKCE downgrade
- Password reset: host-header poisoning, token-in-URL leakage (referrer), predictability, no single-use
- 2FA: response-status trust, brute-forceable codes, bypass via backup-code enumeration, remember-token reuse

## D. BUSINESS LOGIC
- Race conditions: parallel withdraw/redeem/transfer (single-packet attack — N requests, one connection)
- Payment flows: negative/zero/decimal prices, currency confusion, coupon stacking, post-hoc price edits
- Stateless verification: claim gates with no server-to-server callback (playbook §5)
- Subscription/lifetime bypass: downgrade-with-features, trial re-spam via email tricks
- Export/import: CSV injection (=cmd), formula injection in generated files
- Referrer/CSRF: state-changing actions without CSRF tokens (SameSite=None paths)
- Webhooks: unsigned payloads, signature-confusion, replay without timestamp/nonce
- Introspection leaks: GraphQL, Swagger UI live, Spring Boot actuators, .git/.svn deployment

## E. CLIENT
- XSS: stored/reflected/DOM, every sink (innerHTML, eval, document.write, postMessage targets)
- postMessage: wildcard targetOrigin, unvalidated origin on receive
- DOM clobbering / CSS injection / clickjacking (missing XFO/frame-ancestors)
- Sourcemaps deployed (.map) — full source recovery
- Service worker / cache poisoning of asset URLs
- Client-side secrets: API keys, feature flags, internal hostnames in bundles
- Dependency rot: dead third-party scripts/invites/widgets (hijackable references)

## F. FILE / UPLOAD
- Content-type confusion, double extensions, polyglots (GIF+JS, ZIP+JS)
- Image parsers: ImageMagick-class (CVE-tracked), SVG with embedded JS
- Archive extraction: zip-slip traversal, symlink entries, decompression bombs
- Resume/range parsing: header injection via filename, path traversal in multipart names

## G. INFRA / CLOUD
- Public buckets: S3/GCS/Azure listing+read+write, backup dirs, credential files
- Metadata endpoints via SSRF: 169.254.169.254 (AWS/GCP/Azure IMDS, IMDSv1 vs v2)
- K8s: API server anonymous, kubelet 10250 auth, etcd 2379 exposure, dashboard public
- Container registries: anonymous pull, :latest overwrite
- CI/CD: public workflow logs with secrets, self-hosted runner exposure, artifact signing gaps
- Mail: SPF/DKIM/DMARC gaps → spoofing; subdomain takeover via orphaned MX/CNAME
- Cloudflare/CDN: Workers KV/D1 exposure via misrouted routes, origin-shield bypass

## H. PROTOCOL / WIRELESS (operator hardware)
- WiFi: PMKID, handshake capture+crack, rogue AP, WPS
- BLE: GATT enumeration, no-pairing writes
- SDR: replay, rolling-code
- RFID/NFC: MIFARE nested, UID clone

## I. MOBILE (operator apps)
- APK/IPA static: hardcoded keys, debuggable flags, exported components, backup=true
- Deeplink handling: unvalidated parameter → WebView JS injection
- Cert pinning gaps; runtime hooking (frida) on own builds
- IPC exposure: broadcast receivers, content providers, exported services (Android)
- Keychain/keystore analysis: key accessibility classes, jailbreak-detection bypass
- WebView bridge: JS-native bridge functions callable from loaded content
- App extension abuse: share extensions, keyboard extensions leaking input
- OTA update mechanism: signing validation, rollback protection

## J. AI-SPECIFIC (operator apps)
- Prompt injection: indirect via retrieved content, tool-description injection, system-prompt exfil
- Agent over-scope: tool permissions wider than claimed (read→write drift)
- Router placebo: tokenizer/cost fingerprint divergence on "premium" models
- Guardrail bypass: encoding/roleplay/language-switch regression suites as CI gates
- Training-data extraction probes on own fine-tunes
- Model extraction: query pacing, semantic-similarity evasion, distillation via API
- Embedding inversion: nearest-neighbor reconstruction from embedding queries
- Multi-agent trust: Agent A passes untrusted input to Agent B without validation
- Token-smuggling: homoglyphs, zero-width chars, split tokens evading keyword filters
- RAG poisoning: malicious documents injected into retrieval corpus

## K. SERVERLESS / EDGE
- Cloudflare Workers: KV/D1/R2 exposure via misrouted routes, secret env-var leakage
- Lambda/Cloud Functions: env-var secrets, IAM over-permission, cold-start side-channels
- Edge functions: geo-IP bypass, header-based routing confusion, A/B test poisoning
- CDN cache poisoning: unkeyed input in cache keys, X-Forwarded-* trust
- Serverless persistence: event rules, cron triggers, queue poison-pill messages
- WASM sandbox escapes: memory-corruption in edge runtimes (operator's own deployments)
- Durable objects / stateful edge: cross-tenant state leakage via ID prediction

## L. INDUSTRIAL / IOT-ADJACENT (NOT OT/ICS)
- MQTT brokers: anonymous auth, topic wildcard abuse, retained-message poisoning
- CoAP devices: unauthenticated resource discovery, firmware extraction via /firmware
- Zigbee/Z-Wave: pairing-mode weaknesses, network-key extraction from operator devices
- Building management: BACnet/IP exposure on IT networks (flag, don't touch OT)
- Fleet management: GPS spoofing validation, OTA update signing on operator vehicles
- Smart-city dashboards: non-safety-critical API exposure, data poisoning validation

## M. SUPPLY-CHAIN DEEP
- Package registry: dependency confusion on operator's namespace, typosquat detection
- CI/CD runners: self-hosted runner isolation, workflow secret exposure, artifact signing
- Container registries: anonymous pull, :latest overwrite, image-signing verification gaps
- SBOM completeness: phantom dependencies, license-compliance gaps as attack surface
- Git ops: branch-protection bypass, signed-commit enforcement, deploy-key scoping
- Binary provenance: reproducible-build validation, compiler-flag analysis for backdoors

## N. IDENTITY / AUTH INFRA
- SAML: XML signature wrapping, assertion replay, audience restriction bypass
- OIDC: nonce/state validation, token exchange abuse, consent phishing surface
- LDAP: anonymous bind, injection in search filters, credential caching on clients
- Kerberos: delegation abuse (unconstrained/constrained/RBCD), ticket lifetime policy
- SCIM: over-scoped provisioning tokens, bulk-user enumeration via SCIM endpoints
- FIDO/WebAuthn: origin validation, attestation bypass, resident-key extraction

## O. DATA LAYER
- Graph databases: Cypher injection, traversal-based authz bypass
- Time-series: InfluxDB/Prometheus unauthenticated writes, metric poisoning
- Vector DBs: embedding-space manipulation, nearest-neighbor authz leaks
- Message queues: Kafka/RabbitMQ anonymous produce/consume, poison-pill injection
- Caches: Redis unauthenticated access, cache-key prediction, cache-side-channel leaks
- Search engines: Elasticsearch anonymous access, index-level authz gaps

## P. OBSERVABILITY / OPS
- Monitoring: Grafana/Prometheus anonymous access, alert-rule poisoning
- Logging: log-injection via crafted input, log-volume DoS on operator's own stack
- Tracing: Jaeger/Zipkin exposure, trace-context spoofing
- Alert fatigue: repetitive low-severity alerts masking real events (validate dedup logic)
- Status pages: information leakage in incident post-mortems, timeline metadata

## SWEEP DISCIPLINE
- One decisive probe per cell. A negative result IS a result — log it as coverage evidence.
- Escalate only on signal. No blind CVE spam, no spray-and-pray.
- HOLY SHIT = confirmed cell with impact narrative + kill-chain position. Everything else
  is documented coverage.
- All probes respect the mandate scope gate: scoped targets only, non-destructive, revert
  map before any state change, disclosure path for anything outside own infrastructure.
