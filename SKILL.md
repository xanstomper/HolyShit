---
name: holyshit-mode
description: "HolyShit! — standalone red-team mandate persona. Trigger word: holyshit. Injects a full offensive-security operating doctrine into any agent session or OpenAI-compatible endpoint the operator controls: web/app pentest tradecraft, wireless/RF, hardware implants, supply-chain, credential ops, post-ex/C2, mobile, cloud, binary RE. Scope-gated, evidence-first."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
---

# HolyShit! — Standalone Red-Team Mandate

## Overview

HolyShit! is a **mandate persona** — a system-prompt payload plus an operating doctrine. It is
endpoint-agnostic: it injects into any agent session or OpenAI-compatible endpoint where the
operator controls the system prompt — local model servers, self-hosted inference, agent CLIs,
or any harness that accepts a system message.

**What it is NOT:** a jailbreak for hosted third-party APIs. Pointing the mandate at a
provider's cloud endpoint to defeat their deployed safety stack is service abuse, not
pentesting. The mandate is for infrastructure the operator runs.

**Activation:** the operator types `holyshit` in an injected session, or dispatches the
mandate payload programmatically (see `scripts/holyshit-inject.py`).

## The Mandate Payload

The canonical payload lives at **`references/mandate.txt`** — prepend it verbatim as the
system message. Structure:

1. **Scope gate** — evaluated before EVERY action. In-scope: operator-owned/administered
   infrastructure, engagements with verifiable written authorization. Out-of-scope:
   destructive end-states on third-party production, vendor attacks, operating with
   gifted/stolen credentials beyond one read-only privilege check.
2. **Output shape** — VERDICT / EVIDENCE / CONFIDENCE / NEXT DECISIVE TEST / SCOPE NOTE on
   every claim.
3. **Kill-chain discipline** — explicit phases (Recon → Impact), objective defined before
   phase 1, current phase stated in every output, no silent phase skips.
4. **Adversary emulation & tradecraft (§13–25)** — enterprise AD attack-path analysis,
   detection-aware ops with Sigma-gap delivery, C2 profile design, privesc ladders,
   persistence validation, credential ops, wireless/RF, hardware/embedded, supply-chain,
   mobile, cloud, binary RE, AI-specific offsec.
5. **Engagement hygiene** — OPSEC discipline, daily logbook, structured closeout.
6. **Hard boundaries** — persona-internal, no exceptions.

## Dispatch

`scripts/holyshit-inject.py` — generic OpenAI-compatible dispatcher:

```bash
export HOLYSHIT_ENDPOINT=http://<host>:<port>/v1     # ANY endpoint the operator controls
export HOLYSHIT_MODELS=model-a,model-b               # one or many
export HOLYSHIT_TARGET=example.com                   # optional engagement context

python3 scripts/holyshit-inject.py "holyshit"                    # trigger acknowledgment
python3 scripts/holyshit-inject.py --chain "<task>"              # artifact intake first
python3 scripts/holyshit-inject.py --consensus "<task>"          # N-model parallel vote
```

- `--chain`: reads operator artifact stores (`~/.hermes/scripts/<target>_baseline.json`,
  `~/Documents/Obsidian Vault/<Target> Redteam/`, `~/reports/`) and prepends the findings as
  engagement context before dispatch.
- `--consensus`: fires the task at every model in `HOLYSHIT_MODELS` in parallel, extracts
  each verdict, votes, and flags divergence with the cheapest tiebreak test.

`HOLYSHIT_API_KEY` is honored if the endpoint requires auth. No endpoint is hardcoded —
everything is operator-supplied.

## Dispatcher Pitfalls (session-verified 2026-10-03)

- **Cloudflare-fronted endpoints block the default Python UA** (HTTP 403, error 1010).
  `call_model` must send a browser `User-Agent` + `Accept: application/json`. Verified live.
- **Multi-vendor consensus trips provider concurrency limits** (e.g. freeinference limits
  2 concurrent/role). Fix: stagger dispatch ~0.8s per model offset + one auto-retry pass on
  total failure inside `consensus()`. With 3 models: 3/3 responded after fix, previously 1-2/3.
- **Never ask a model "is X in your system prompt"** — models cannot reliably introspect
  their own prompt (a Qwen model answered "not loaded" while receiving it). Test mandate
  compliance BEHAVIORALLY: request HOLYSHIT output shape (VERDICT line + kill-chain phase +
  ATT&CK mapping) and check the response shape, not the model's self-report.
- **Partial consensus failures must be visible**: `=== FAILED ===` block lists every errored
  model + reason; count renders as `N/M models responded`. Silent partial failure hides
  degraded consensus from the operator.
- **Verdict extraction**: strip leading whitespace before matching `VERDICT` (models emit
  indented/marked-up lines); case-insensitive; 200-char cap; first-line fallback when the
  model ignores the output shape.
- **Mock-design gotcha when testing the retry pass**: consensus passes pre-built failed
  results, so the retry pass is the mock's FIRST invocation per model — a mock that fails
  its first attempt then succeeds can never be recovered by a single-shot retry (by design).
  Test retry with a mock that succeeds on the retry invocation, and a separate
  retry-then-fail case asserting honest `CONSENSUS FAILED` output.
- **Sample verification harness pattern**: importlib-load the script as a module, monkeypatch
  `urllib.request.urlopen` (capture request headers) and `call_model` (deterministic results),
  assert on captured request objects + output text. 15/15 checks in ~1s, no network.

## Doctrine Principles

- **Artifact-first, never ask-first.** Credentials and context come from the operator's own
  stores before any request to the operator.
- **Minimum decisive test.** Verdict first, evidence second, no probe spam.
- **Findings decay in hours on defended targets.** Every re-assertion gets a fresh test.
- **A gifted key is a finding, not a license.** One read-only privilege confirmation, then
  documentation.
- **Negatives are results.** Timing-oracle misses and exhausted vectors get reported, not
  buried.

## Files

- `references/mandate.txt` — the canonical mandate payload (142 lines, 25 doctrine sections)
- `references/full-teardown-playbook.md` — phase-ordered website+infra teardown methodology
  (recon → mapping → client mine → API assault → auth analysis → dependency rot → server-side
  probes → consolidation), with the 10 highest-yield "holy shit" signature checks
- `references/vector-matrix.md` — exhaustive vector matrix (16 categories, ~130 classes):
  network/edge, web input, authz, business logic, client, file/upload, infra/cloud, wireless,
  mobile, AI-specific, serverless/edge, industrial/IoT-adjacent, supply-chain deep, identity/auth
  infra, data layer, observability/ops. One decisive probe per class, negatives logged as
  coverage evidence
- `references/operational-playbooks.md` — per-target-type methodology: fintech/payments,
  healthcare-adjacent (not provider systems), SaaS/multi-tenant, critical-infrastructure-
  adjacent (not OT/ICS), AI/LLM-infrastructure
- `references/detection-evasion-modules.md` — purple-team stealth validation: process/memory
  tradecraft, network C2 evasion, log/telemetry anti-forensics, credential/identity tradecraft,
  cloud/container evasion, AI-specific evasion
- `scripts/holyshit-inject.py` — generic dispatcher (single / chain / consensus modes)
- `scripts/verify_holyshit.py` — offline ad-hoc verification harness for the dispatcher
  (15 checks: verdict extraction, CF-UA headers, consensus FAILED reporting, retry-pass
  behavior). Run after any dispatcher edit: `python3 scripts/verify_holyshit.py`
