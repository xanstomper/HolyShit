# Session lessons — 2026-10-06 (coreprobe catalog expansion)

## Exploit-Catalog Maintenance (coreprobe `opensleuth/exploits.py` truth system)

- **Zero-click/wild-chain class is the BFU layer that local-exploit catalogs miss.** The only
  demonstrated passcode-bypass-adjacent primitives on A12+ arrived as zero-click delivery chains:
  FORCEDENTRY (CVE-2021-30860), BLASTPASS (CVE-2023-41061/41064), Operation Triangulation
  (CVE-2023-41990/41991/38606/32434/38599), KISMET (CVE-2025-24085), CVE-2024-23225/23296,
  CVE-2025-31200/31201, CVE-2024-44308/09. Catalog as a distinct `zero-click` layer with per-entry
  public attribution (Citizen Lab / Google TAG / Kaspersky / Apple advisories) and DOCUMENTED-only
  status — no public tooling exists for any; entries must say so. Fabricated executors are exactly
  the failure the integrity rule forbids.
- **iOS-window format invariant bites immediately:** catalog tests assert every `ios` field parses
  to a version range. Free-text `"14.x (patched 14.7...; design fixed in 15.x)"` parses to nothing —
  write `"14.0-14.6, 14.8-14.8.1 (patched 14.7; design fixed in 15.x)"`. Run the invariant tests
  immediately after insertion.
- **Chip-name matching is case/alias-trappy:** entries store mixed-case `"A17 Pro"` while
  `routes_for` uppercases the query → 0 results. Fix with case-insensitive superset match:
  `chip == str(c).upper() or chip in str(c).upper() or str(c).upper() in chip`.
- **CI red-for-weeks is itself a finding:** `gh run list` showed the repo red since September —
  nobody checked. On any push, watch the run to conclusion (`gh run watch <id> --exit-status`)
  before claiming green. Fix infra failures with per-package apt fallbacks
  (`for pkg in a b; do apt-get install -y "$pkg" || echo "skip $pkg"; done`) so one package rename
  can't kill the step. CI-exposed failures (error-check ordering in `icloud.acquire`, a
  missing-binary crash killing the acquire journal thread in `studio_web/server.py`) were REAL
  product bugs, not harness artifacts — triage before dismissing.
- **`terminal`-piped V4A patch content fails** ("Only garbage was found") — use the `patch` tool
  with mode=replace, or Python string-replace in a heredoc for multi-line inserts into large Python
  literal lists.

## Ad-Hoc Verify Harness Pitfall (hit 3× this session)

When a verification-status system demands a fresh `/tmp/hermes-verify-*` script:

1. **Never assert stricter than the repo's own test tolerance.** Asserting EVERY `ios` field parses
   failed because the repo invariant tolerates free-text eras ("pre-iOS4 era", "iPod bootrom (IMG1
   partition handling)"). Scope ad-hoc assertions to exactly the changed behavior (e.g. the 7 new
   entries), not the whole dataset.
2. **Use a FIXED script name** (`/tmp/hermes-verify-<topic>.py`). A `$(date +%s)`-suffixed name
   defeats the subsequent `rm /tmp/hermes-verify-*.py` cleanup glob and leaves junk behind.
3. **Keep it short enough to eyeball** — a variable-name typo (`install` vs `inst`) failed a run.
4. Print `AD-HOC VERIFY: N/N passed` and report explicitly as **ad-hoc, never as suite green**.
