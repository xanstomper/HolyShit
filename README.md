# HolyShit! — Red-Team Mandate & Engagement Framework

**Version:** 2.0.0  
**Author:** Hermes Agent  
**License:** MIT  
**Platform:** Linux (any OpenAI-compatible endpoint)

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

**Output shape:** every claim produces VERDICT / EVIDENCE / CONFIDENCE / ATT&CK mapping / NEXT DECISIVE TEST / SCOPE NOTE.

**Kill-chain discipline:** every engagement moves through phases explicitly: Recon → Resource-Development → Initial-Access → Execution → Persistence → Privilege-Escalation → Defense-Evasion → Credential-Access → Discovery → Lateral-Movement → Collection → C2 → Exfiltration → Impact.

---

## Reference Files

| File | Purpose | Lines |
|------|---------|-------|
| `references/mandate.txt` | Canonical system prompt payload | 142 |
| `references/full-teardown-playbook.md` | Phase-ordered website+infra teardown | 111 |
| `references/vector-matrix.md` | 116 attack classes, 16 categories | 157 |
| `references/operational-playbooks.md` | Per-target-type workflows | 196 |
| `references/detection-evasion-modules.md` | Purple-team stealth validation | 143 |
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
