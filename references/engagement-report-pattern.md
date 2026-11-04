# Engagement Report Pattern — Remediate-Ranked Findings Deliverable

The final stage of the HolyShit! engagement loop is `score → probe → chain → converge →
persist → report`. `holyleadger.py report` turns the persistent ledger JSON into a
human-readable, remediate-ranked markdown report that a client or operator can act on.
This is the reference for the report's structure and the reasoning behind each section.

## Command

```bash
export HOLYSHIT_TARGET=example.com
python3 scripts/holyleadger.py report                 # stdout
python3 scripts/holyleadger.py report --out engagement-report.md   # write to file
```

Reads the ledger at `~/.hermes/scripts/holyleadger/<target>.json` (override home via
`HOLYSHIT_SCRIPT_DIR`).

## Automated life: the report is the output of `scan`

With `HOLYSHIT_TARGET` exported, `holyshit.py scan <task>`:
1. **dispatches** to the models (`holyshit-inject`)
2. **converges** to CONFIRMED/BLOCKED/HYPOTHESIS (`holyconverge`)
3. **auto-persists** the outcome — confirmed → `holyleadger add confirmed` + `chain` (rc 0);
   blocked/exhausted → `holyleadger add hypothesis` (rc 1/3). No `HOLYSHIT_TARGET` → no-op
   (safety + makes offline harnesses deterministic).

So a confirmed finding is guaranteed to land in state (and appear in the next `report`)
with zero manual `add`. The report is thus always current after any `scan`.

## Structure (each section's purpose)

- **Header** — target, generation timestamp, counts (classes tracked / confirmed /
  hypothesis / negative / chains). Compliance + scope-evidence at a glance.
- **`## Confirmed Holy Shits`** — the money section. Each confirmed class, ranked by score
  desc (then status tier), with score / technique / probe-count / last-probed. **Severity
  high first.** This is what clients read first.
- **`## Hypotheses (need proof)`** — unproven-but-higher-probability classes with score +
  probe-count. Not Holy Shits (mandate §29 strictness: a finding needs provable req+resp,
  kill-chain phase + ATT&CK id, one-sentence impact, non-destructive validation) — flagged
  as the highest-priority NEXT decisive tests.
- **`## Ruled Out (negative)`** — classes tested and cleared. Evidence of test coverage
  (valuable for scope/compliance), excluded from remediation.
- **`## Attack Paths`** — each recorded chain (crown jewel, steps joined with `→`, impact).
  Chains the isolated findings into exploit narratives.
- **`## Remediation Priority`** — the standing ordering: (1) confirmed holyshits first
  (RCE/admin-bypass/cross-tenant/cloud-cred), (2) confirmed chains (fix the base primitive
  step first), (3) hypotheses (prove or dismiss), (4) re-verify confirmed on every deploy
  (findings decay).

## Ranking rule

`confirmed(3) > inconclusive(2) > hypothesis(1) > negative(0)`, then score desc within a
tier. Implemented as `sorted(classes.items(), key=lambda kv: (-rank(status), -score))`.
Confirmed classes always outrank hypotheses even if the hypothesis has a higher raw score —
a proven finding is worth more than an unproven high-scoring guess.

## Verification

`report` is verified (a) in-module with an isolated temp ledger seeded with mixed
confirmed/hypothesis/negative + one chain, asserting: rc 0, all six sections present,
score-desc ordering, accurate counts line, chain steps + impact rendered, `--out` writes
a file; and (b) as a subprocess CLI (`holyleadger.py report --target --out`) writing to an
isolated dir. The CI workflow's ledger smoke step ALSO runs `report` and greps for the
"Confirmed Holy Shits" section + a known class name, so a broken report fails the build.

## Pairs with `next`

`holyleadger.py next --top N` is the inverse view: it lists the highest-value ACTIONS
(re-verify decayed confirmed, prove hypotheses, re-probe crown paths) and excludes
negatives. `report` shows "here's what we found"; `next` shows "here's what to do next."
Operators run `next`, execute the top `holyshit scan <task>` commands, then `report` to see the ledger consolidate.

## The sendable disclosure variant (Obsidian/client-ready)

When the operator wants findings documented **to send to the target** (bounty, responsible
disclosure, or leverage), write a SECOND document distinct from the internal report — same
facts, different framing:

- **Professional disclosure tone, no tooling or vantage reveals** beyond what reproduces the
  bug: PoC links/requests a defender can run, code citations from THEIR OWN bundle, fixes per
  finding. No operator infrastructure names, no burner identities, no attack-tooling names.
- **Severity-ranked with honest credit**: state mitigations that work (a respected opt-out, a
  held gate) inside the finding — credibility with the target's security team is leverage,
  padding is not.
- **Claim-channel check BEFORE promising a bounty** (and before burning hours): fetch
  `/.well-known/security.txt`, grep the ToS for disclosure/bounty language, and search the
  platforms (Bugcrowd/HackerOne/Intigriti/Immunefi/YesWeHack/Cantina) for the target or its
  family. No program + no security.txt + silent ToS = **no payout channel exists** — say so
  early and frame the work as a disclosure package or portfolio, never as income. Never
  promise a bounty for a target with no claim channel.
- Deliverable placement: the operator's Obsidian vault (`~/Documents/Obsidian Vault/<Target>
  Redteam/`) as one markdown note per engagement, named for sending. Link the internal case
  file by name, not by content — the internal report keeps tooling/vantage detail; the sendable
  doc keeps only what the target may see.
- If raw evidence exists (socket captures, header dumps), say where it is preserved and offer
  the walkthrough — an offer to reproduce on demand is what converts a report into a bounty
  conversation.