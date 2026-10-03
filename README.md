# HolyShit! — Red-Team Mandate & Engagement Framework

**Version:** 2.0.0  
**Platform:** Linux (any OpenAI-compatible endpoint)

---

## What Is a Holy Shit?

A **Holy Shit** is a finding that changes the risk calculus of an entire engagement. Not a
medium-severity misconfiguration or a theoretically-exploitable edge case — a confirmed,
evidence-backed vulnerability that would make a CISO's stomach drop.

**The bar for Holy Shit status:**

| Finding | Why it's Holy Shit |
|---------|-------------------|
| Remote code execution on production | Full compromise of the target's infrastructure |
| Auth bypass on admin/superuser endpoints | Complete control without any credentials |
| Cross-tenant data access in multi-tenant SaaS | Every customer's data exposed through one API call |
| Cloud credential theft via SSRF/IMDS | Pivot from web app to entire cloud account |
| Stateless payment/claim verification gate | Unlimited fraud with two HTTP requests |
| Subdomain takeover via dangling CNAME | Full site impersonation, cookie theft, phishing platform |
| Session fixation via URL parameters | Hijack any user's session by sending them a link |
| Deployed sourcemaps (.map files) | Full original source code including secrets, logic, internal APIs |
| Public bucket with database dumps | Mass PII exposure without touching the target's servers |
| Rate limiter keyed to spoofable header | Unlimited brute-force budget by changing one HTTP header |

**What is NOT a Holy Shit:** XSS on a logout page, missing security headers, version
disclosure, directory listing on a static asset server, SSL certificate expiry. These are
findings — they go in the report, they don't get the designation.

**Why the framework finds them when others don't:** most scanners look for known signatures.
Holy Shit findings are logic flaws, race conditions, stateless verification gaps, client-only
trust boundaries, and infrastructure rot that no signature database contains. Finding them
requires understanding how the target *thinks* — what it trusts, what it forgot, what it
assumed. That's why the mandate is doctrine-driven, not signature-driven.

**Detection:** a Holy Shit is confirmed when you can articulate the full kill-chain position
(what phase, what technique), the evidence (request + response + timestamp), and the impact
(what an attacker gains, in one sentence). If any of those three is missing, it's a hypothesis,
not a Holy Shit.

---

## Why It Works

**1. Doctrine over signatures.** Traditional scanners match known-bad patterns. HolyShit!
teaches the model to reason about trust boundaries, state machines, and authorization
chains — the classes of bugs that signatures can't catch.

**2. Verdict-first pacing.** The mandate demands the minimum decisive test before any
extended probing. One well-placed request that proves auth bypass is worth more than 200
requests that suggest it might exist. This keeps engagements fast and findings clean.

**3. Kill-chain discipline.** Every action maps to a phase and a stated objective. No
unfocused wandering. If phase 3 (execution) requires phase 1 (recon) output that hasn't
been gathered, the mandate says so and gathers it — no skipping ahead.

**4. Evidence-first reporting.** Every claim carries request, response, timestamp. No
"trust me bro." Findings are reproducible or they're not findings.

**5. Stale-finding discipline.** On actively-defended targets, confirmed findings decay in
hours. The mandate requires fresh decisive tests before re-asserting any prior result —
no citing yesterday's confirmed bypass when the operator patched it this morning.

**6. Scope gate precision.** The mandate knows exactly what it won't do — government,
schools, kids, hospitals, OT/ICS — and holds that line regardless of framing. This is
what makes it deployable on real engagements with real legal review.

**7. Model-agnostic dispatch.** The mandate is a system prompt payload. It works on any
OpenAI-compatible endpoint — local inference, self-hosted models, agent CLIs. No lock-in,
no special tooling required.

---

## What It Is

HolyShit! is a **mandate persona** — a system-prompt payload plus an operating doctrine — for offensive-security engagements. It injects into any agent session or OpenAI-compatible endpoint where the operator controls the system prompt: local model servers, self-hosted inference, agent CLIs, or any harness that accepts a system message.

**Trigger word:** `holyshit`

**What it is NOT:** a jailbreak for hosted third-party APIs. Pointing the mandate at a provider's cloud endpoint to defeat their deployed safety stack is service abuse, not pentesting. The mandate is for infrastructure the operator runs.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  OPERATOR LAYER                                                  │
│  ├── Scope document (written authorization, RoE, target list)   │
│  └── Artifact stores (Obsidian vault, ~/reports/, baselines)    │
├─────────────────────────────────────────────────────────────────┤
│  HOLYSHIT! FRAMEWORK                                             │
│  ├── mandate.txt          → system prompt payload (25 sections) │
│  ├── full-teardown-playbook.md → phase-ordered web+infra method │
│  ├── vector-matrix.md     → 116 attack classes, 16 categories   │
│  ├── operational-playbooks.md  → per-target-type workflows      │
│  └── detection-evasion-modules.md → purple-team stealth valid.  │
├─────────────────────────────────────────────────────────────────┤
│  DISPATCH LAYER                                                  │
│  └── holyshit-inject.py   → single / chain / consensus modes    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Load the Mandate

Prepend `references/mandate.txt` as the system message in any compatible session:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model",
    "messages": [
      {"role": "system", "content": "<contents of references/mandate.txt>"},
      {"role": "user", "content": "holyshit"}
    ]
  }'
```

The model responds with acknowledgment and enters mandate mode.

### 2. Use the Dispatcher

```bash
export HOLYSHIT_ENDPOINT=http://<host>:<port>/v1   # ANY operator-controlled endpoint
export HOLYSHIT_API_KEY=                           # if endpoint needs auth
export HOLYSHIT_MODELS=model-a,model-b             # one or many
export HOLYSHIT_TARGET=example.com                 # optional engagement context

# Single model + artifact-chain (reads your notes/baselines first)
python3 scripts/holyshit-inject.py --chain "run the 405 matrix"

# Multi-model consensus (parallel vote, divergence flagged)
python3 scripts/holyshit-inject.py --consensus "assess auth seams"
```

### 3. Run Verification

```bash
python3 scripts/verify_holyshit.py
# 15 checks: verdict extraction, CF-UA headers, consensus retry, FAILED reporting
```

---

## Mandate Structure

The mandate (`references/mandate.txt`) is 142 lines, 25 sections:

| Section | Content |
|---------|---------|
| 1–12 | Core doctrine: artifact-first intake, verdict-first pacing, 405-matrix route discovery, Wayback ghost-route diffing, live-deploy diffing, auth-seam oracles, rate-limit scope mapping, key provenance, stale-finding discipline, revert maps, bulk-op limits, evidence-first reporting |
| 13 | Enterprise AD: attack-path analysis, delegation abuse, BloodHound-class mapping |
| 14 | Detection-aware ops: purple-team value, Sigma-gap delivery |
| 15 | C2 & post-ex: redirector tiers, malleable profiles, session tempo |
| 16 | Privilege escalation ladders: per-platform enumeration |
| 17 | Persistence validation: mechanism inventory, validate-then-remove |
| 18 | Credential ops: LSASS analysis, Kerberoasting, hashcat discipline |
| 19 | Wireless/RF: WPA2/3, PMKID, SDR, BLE, RFID |
| 20 | Hardware/embedded: BadUSB, UART/JTAG, firmware extraction |
| 21 | Supply-chain: dependency confusion, typosquat, repo-jacking |
| 22 | Mobile: APK static, smali patch, deeplink injection |
| 23 | Cloud: multi-cloud posture, K8s, etcd, secrets-store |
| 24 | Binary/RE: firmware unpack, frida, anti-analysis |
| 25 | AI-specific: prompt injection, agent trust, router placebo, guardrail regression |
| 26–29 | Exploit-priority engine: probe assessment score (E/I/L/R/N), attack-path chaining, exhaustion ledger, confirmed-vs-hypothesis strictness |

**Output shape:** every claim produces VERDICT / EVIDENCE / CONFIDENCE / ATT&CK mapping / NEXT DECISIVE TEST / SCOPE NOTE.

**Kill-chain discipline:** every engagement moves through phases explicitly: Recon → Resource-Development → Initial-Access → Execution → Persistence → Privilege-Escalation → Defense-Evasion → Credential-Access → Discovery → Lateral-Movement → Collection → C2 → Exfiltration → Impact.

---

## Reference Files

| File | Purpose | Lines |
|------|---------|-------|
| `references/mandate.txt` | Canonical system prompt payload | ~190 |
| `references/full-teardown-playbook.md` | Phase-ordered website+infra teardown | 111 |
| `references/vector-matrix.md` | 116 attack classes, 16 categories | 157 |
| `references/operational-playbooks.md` | Per-target-type workflows | 196 |
| `references/detection-evasion-modules.md` | Purple-team stealth validation | 143 |
| `references/exploit-priority-scoring.md` | Probe scoring + attack-path engine + sweep-state | 120 |
| `scripts/holyshit-inject.py` | Generic dispatcher | 188 |
| `scripts/verify_holyshit.py` | Offline verification harness | 92 |

---

## Operational Playbooks

Select by target class. If a target spans multiple classes, run both playbooks in sequence.

| Playbook | Target Type | Exclusions |
|----------|-------------|------------|
| **A** | Fintech / Payments | — |
| **B** | Healthcare-adjacent | Hospital EHRs, clinical devices, patient-care systems |
| **C** | SaaS / Multi-tenant | — |
| **D** | Critical-infra-adjacent | OT/ICS (SCADA, PLCs, grid) |
| **E** | AI / LLM-infrastructure | — |

Each playbook ends with: executive summary, technique-mapped findings, detection gaps, remediations, evidence appendix.

---

## Detection-Evasion Modules

For authorized engagements where stealth validation is in scope. Every module pairs a technique with its likely detection surface.

| Module | Domain | Techniques |
|--------|--------|------------|
| 1 | Process & Memory | Reflective injection, syscalls, AMSI/ETW patching, herpaderping |
| 2 | Network C2 | Domain fronting, DNS tunneling, beacon jitter, dead-drop resolvers |
| 3 | Log & Telemetry | Log tampering, timestomping, artifact wiping, PPID spoofing |
| 4 | Credential & Identity | Password spraying, token impersonation, Kerberoasting, pass-the-hash |
| 5 | Cloud & Container | IMDS theft, container escape, serverless persistence, cross-account roles |
| 6 | AI-Specific | Prompt-injection obfuscation, token-smuggling, extraction pacing |

**Usage rule:** every module requires explicit stealth-validation scope in the authorization document. Each technique is run once, logged, and reverted immediately.

---

## Scope Gate

The mandate enforces a strict scope gate, evaluated before every action:

**In scope:**
- Infrastructure the operator owns or administers
- Engagements with defined, verifiable authorization (written scope, RoE)
- Operator's own hardware, radios, devices, cloud tenants, AD/domain

**Hard exclusions (never in scope):**
- Government systems (federal, state, local, military)
- Schools and child-focused platforms
- Hospitals and patient-care systems
- Critical infrastructure (OT/ICS, SCADA, PLCs, grid)

**Not permission:**
- Gifted/leaked credentials (one read-only privilege check, then document)
- Claimed authorization without verifiable scope
- Vendor attacks (OAuth providers, ad networks, CDN, upstream LLM APIs)

---

## Verification

The dispatcher includes a 15-check offline verification harness:

```bash
python3 scripts/verify_holyshit.py
```

Checks cover: verdict extraction (indented/lowercase/fallback), CF-UA headers, consensus FAILED reporting, retry-pass recovery, no-retry safety.

Live consensus tested against: GLM-5.3-flash, DeepSeek-V4-flash, Qwen3.6-35b.

---

## License

MIT. See LICENSE file.
