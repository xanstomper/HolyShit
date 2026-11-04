# Operational Playbooks — Per-Target-Type Methodology

Companion to the mandate and vector matrix. Select by target class; each playbook is a
phase-ordered workflow tuned to that environment's attack surface. Run under written
authorization; all techniques are discovery/documentation oriented with revert maps.

---

## PLAYBOOK A — FINTECH / PAYMENTS

**Objective**: validate PCI-DSS boundary integrity, transaction logic, and fraud controls.

**Phase 1 — Recon**
- CT logs + Wayback on `%.target.tld` — separate payment gateway domains from marketing.
- ASN map: payment processors, fraud vendors, banking partners (third-party = out of scope).
- GitHub/org sweep for processor API keys, webhook secrets, test-card configs.

**Phase 2 — Payment Flow Analysis**
- **Transaction state machine**: map every state transition (auth → capture → refund → void).
  Test race conditions on duplicate capture (single-packet attack).
- **Amount manipulation**: negative/zero/decimal overflow, currency confusion (USD vs JPY
  decimal places), coupon stacking, post-hoc price edits in cart APIs.
- **Webhook integrity**: signature validation, timestamp/nonce enforcement, replay window.
  Send signed-but-stale events to test replay acceptance.
- **3DS / SCA validation**: bypass via fallback APIs, merchant-initiated transaction abuse,
  exemption thresholds (low-value exemption farming).

**Phase 3 — Auth & Session**
- Session fixation via `?token=` params (referrer leakage to third-party analytics = HOLY SHIT).
- JWT validation: alg=none, kid injection, weak HMAC secret (hashcat), no audience check.
- OAuth state/redirect validation on payment-provider handoffs.

**Phase 4 — API Surface**
- IDOR on transaction IDs (cross-account access with second test account only).
- Mass assignment: `is_refunded`, `is_authorized`, `amount_final` injection on PUT.
- GraphQL introspection on payment APIs; field-level auth on `card_token`, `bank_account`.

**Phase 5 — Infrastructure**
- PCI boundary: is card data touching your servers or processor-hosted fields? Look for
  PAN in logs, PAN in URLs, PAN in analytics events.
- Public buckets: S3/GCS with transaction exports, settlement files, chargeback evidence.

**Deliverable**: transaction-flow map, race-condition findings, webhook-replay validation,
PCI-boundary assessment, IDOR/authorization gaps.

---

## PLAYBOOK B — HEALTHCARE-ADJACENT (NOT PROVIDER SYSTEMS)

**Scope note**: Hospital EHRs, clinical devices, and patient-care systems are RESTRICTED
TARGETS. This playbook covers adjacent business systems: patient portals, billing platforms,
telehealth scheduling, wellness apps, medical-device companion apps.

**Phase 1 — Recon**
- Subdomain enumeration: separate clinical systems from business systems.
- Wayback for old patient-portal versions; ghost-route diffing.

**Phase 2 — PHI Boundary Validation**
- Test whether PHI appears in URLs, logs, analytics, or third-party trackers.
- Validate de-identification: can you re-identify "anonymized" records via
  quasi-identifiers (ZIP + DOB + gender)?
- API responses: does `GET /appointment/123` leak `diagnosis_code`, `notes`, `ssn`?

**Phase 3 — Auth & Access**
- Role-based access: patient vs provider vs admin — BFLA on every privileged endpoint.
- Break-glass access: is emergency-access logged and auditable? Test with scoped break-glass
  account.
- Family/caregiver proxy access: can Patient A view Patient B's records via shared links?

**Phase 4 — Business Logic**
- Appointment race conditions: double-booking, overbooking provider slots.
- Prescription-refill logic: early-refill detection bypass, quantity manipulation.
- Telehealth session tokens: predictable? Replayable? TTL enforcement?

**Phase 5 — Mobile Companion Apps**
- Hardcoded API keys, debug flags, exported components (Android), keychain analysis (iOS).
- Deeplink handling: unvalidated parameter → WebView JS injection → session theft.

**Deliverable**: PHI-boundary map, role-authorization matrix, proxy-access findings,
mobile-trust findings, de-identification validation.

---

## PLAYBOOK C — SAAS / MULTI-TENANT

**Objective**: validate tenant isolation, subscription enforcement, and admin boundaries.

**Phase 1 — Recon**
- Tenant enumeration: subdomain (`tenant.target.com`) vs path (`target.com/tenant`) vs
  header (`X-Tenant-ID`). Map isolation model.
- CT logs + DNS for forgotten tenant subdomains (dangling CNAME takeover).

**Phase 2 — Tenant Isolation**
- **IDOR across tenants**: `GET /api/tenant-a/resource/123` with tenant-b token.
- **Shared infrastructure**: Redis, DB, queue — can you leak across via cache keys,
  pub/sub channels, job queues?
- **Feature flags**: can tenant-a enable enterprise features by guessing flag names?
- **Subdomain takeover**: tenant churn leaves orphaned DNS → cloud service takeover.

**Phase 3 — Subscription & Billing**
- Downgrade-with-features: cancel subscription, verify enterprise features revoke immediately.
- Trial re-spam: email tricks (`+tag`, dots, unicode) to farm infinite trials.
- Usage metering: can you reset/rollback usage counters via API or race conditions?
- Webhook integrity: unsigned subscription events → free upgrades (replay test).

**Phase 4 — Admin & Superuser**
- Admin panel discovery: `/admin`, `/internal`, `/ops` — 405-matrix verify.
- Impersonation endpoints: `POST /admin/impersonate` with tenant-admin token — BFLA test.
- Audit logs: are admin actions logged? Can admins wipe their own logs?

**Phase 5 — API & Integration**
- OAuth app validation: third-party integrations with over-scoped permissions.
- API key scoping: read-only keys that can write? Write keys that can delete?
- Webhook payload validation: SSRF in webhook URLs, blind payload injection.

**Deliverable**: tenant-isolation map, subscription-bypass findings, admin-boundary
violations, integration-trust model, dangling-takeover candidates.

---

## PLAYBOOK D — CRITICAL-INFRASTRUCTURE-ADJACENT (NOT OT/ICS)

**Scope note**: OT/ICS (SCADA, PLCs, grid systems) are RESTRICTED TARGETS. This playbook
covers adjacent IT: building management systems, logistics platforms, supply-chain portals,
fleet management, smart-city dashboards (non-safety-critical).

**Phase 1 — Recon**
- Separate safety-critical OT networks from business IT via passive DNS + ASN analysis.
- Shodan/Censys for exposed industrial protocols (Modbus, BACnet, DNP3) — flag as
  RESTRICTED, do not touch, report to owner.

**Phase 2 — Access Control**
- Role separation: operator vs supervisor vs auditor — BFLA on privileged actions.
- Shared-account detection: can multiple users share credentials without detection?
- Physical-access integration: badge systems, door controllers — API exposure?

**Phase 3 — Data Integrity**
- Sensor-data validation: can you inject falsified telemetry via API (test with scoped
  simulator, never production sensors)?
- Audit-log integrity: are logs tamper-evident? Can you delete your own entries?
- Time-series manipulation: backdate/forward-date records in historian databases.

**Phase 4 — Supply-Chain Portal**
- Vendor onboarding: document upload → malware scanning → sandbox escape (test with EICAR).
- Purchase-order race conditions: duplicate approvals, split orders to bypass thresholds.
- Invoice tampering: can vendors alter bank details post-approval?

**Deliverable**: IT/OT boundary map, role-authorization findings, data-integrity validation,
supply-chain workflow gaps, exposed-OT report (no touch, disclosure only).

---

## PLAYBOOK E — AI / LLM-INFRASTRUCTURE

**Objective**: red-team the operator's own AI stack: model endpoints, agent frameworks,
RAG pipelines, fine-tunes, guardrails.

**Phase 1 — Endpoint Discovery**
- Model API enumeration: `/v1/models`, `/v1/completions`, `/v1/chat/completions` — 405 matrix.
- Version disclosure: model names, provider leaks, quantization format (GGUF = self-hosted).
- Cost/tokens endpoint: rate limits, billing validation, quota enforcement.

**Phase 2 — Prompt-Injection Surface**
- **Direct**: jailbreak attempts on the operator's own models (roleplay, encoding, DAN-class,
  language-switch) — validate guardrail regression as CI gate.
- **Indirect**: inject payloads into documents the model retrieves (RAG poisoning), test
  whether the model executes embedded instructions.
- **Tool injection**: manipulate tool descriptions mid-conversation; test if the model
  follows modified tool specs.

**Phase 3 — Agent Framework**
- Tool permission scoping: can a read-only tool be coerced into writes via prompt?
- Multi-agent trust: Agent A receives untrusted input, passes to Agent B — does B validate?
- System-prompt exfiltration: can you extract the system prompt via token-by-token probing?

**Phase 4 — Data & Model Security**
- Training-data extraction: membership inference, verbatim recall of fine-tuning data.
- Model theft: can you distill the model via API queries? Rate-limit vs. extraction budget.
- Embedding inversion: text from embeddings via nearest-neighbor reconstruction.

**Phase 5 — Infrastructure**
- GPU/cluster exposure: Jupyter notebooks, TensorBoard, MLflow — unauthenticated?
- Model artifact storage: public buckets with `.safetensors`, `.gguf`, `adapter_model.bin`?
- CI/CD for models: can you poison the training pipeline via dependency confusion?

**Deliverable**: injection-surface map, guardrail regression suite, agent-trust findings,
data-exposure validation, infrastructure gaps.

---

## PLAYBOOK F — BETTING / CASINO / GAMBLING

**Objective**: game-integrity (provably fair), money-RPC authorization, and the
forgotten regional/mirror infrastructure these operators always accumulate.

**Phase 1 — Surface & Mirror Recon**
- CT logs on `%.<brand>.tld` AND partner/white-label brands (shared backends leak
  into each other's bundles — `providers/<partner>-originals` in the JS is the tell).
- Regional entrance/mirror domains (e.g. Turkish `giris`/`tr.` hosts) sit on separate
  legacy hosting — fingerprint SEPARATELY; they never inherit main-site hardening.
- PTR-reverse every infrastructure IP, then whois every name in the funnel (links,
  PTRs, robots): unregistered-but-linked = registration takeover, executable same-day.
- Parked-domain landers (`ap:"parking"` script) on mirror domains = dead funnel links.

**Phase 2 — Provably-Fair Structural Test (the integrity crown)**
- Capture a FULL game round from the UNAUTH socket: `game_starting` → `game_started`
  → `player_bet`/`game_tick` → `game_crash`.
- Verify commitment PLACEMENT: a fairness commitment must precede the outcome on a
  publicly-checkable channel. Hash delivered in the SAME event as the result = no
  verifiable pre-commitment = the marketing claim is unfalsifiable (integrity finding
  that supports extortion narratives — capture it before the attackers publish theirs).
- Check for staff-control flags in public event schemas (`forced`, manual-settle) —
  outcome-control capability confirmed in the wire schema is a regulator-grade question.
- Mixed-game asymmetry matters: client-seed PF on dice-class games vs no visible
  commitment on crash-class games is the common real pattern.

**Phase 3 — Money-RPC Authorization**
- Extract the client's shared schema library (io-ts/zod chunk) for every money RPC's
  exact shape — then fire valid-shaped unauth probes and read the GATE ORDER
  (validation → auth → balance is the secure order; explicit "Not logged in" beats
  silent session-fail for reporting).
- **Wallet-claim trust model**: if the RPC carries a client-supplied wallet object,
  reason from its structure — no cross-user identifier (walletId/ownerId) in the shape
  = cross-wallet theft structurally impossible, worst case is self-inflation. Then
  weigh: `*_requested` field naming (server treats client figure as advisory),
  optional fee fields (server computes), attached anti-fraud session tokens, and
  economic self-detection (minting bugs scream in ledger reconciliation). Deliver a
  reasoned confidence % + the residual edges (unit conversion, wallet_type override,
  float-vs-integer refinement asymmetries) when a live session isn't available.

**Phase 4 — The Forgotten Edges (where these breaches actually come from)**
- Aged machine/service accounts, never-rotated credentials, staging hosts, dead-name
  identities — the attacker group narrative + the founder's incident statement usually
  corroborate the access method even while disputing scale. Cross-check them.
- Vendor paths in mail (SPF includes, PTR-named mail servers), support-tool data
  channels (identity-verification HMAC fields on user objects), custody integrations.
- Default-credential decisive test on ANY internet-exposed database the engagement
  owns (3-4 read-only attempts, stop at denial — the posture finding stands either way).

**Deliverable**: integrity-commitment map, money-RPC gate-order matrix, mirror/edge
infrastructure assessment, dead-name takeover list, prioritized firewall/patch list.

---

## USAGE

Select playbook by target class. If target spans multiple classes (fintech + SaaS), run
both playbooks in sequence, deduplicating findings. Every playbook ends with the standard
closeout: executive summary, technique-mapped findings, detection gaps, remediations,
evidence appendix.
