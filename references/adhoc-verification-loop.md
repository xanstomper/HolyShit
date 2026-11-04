# Ad-hoc verification loop (system-prompt driven) — proven procedure

Trigger: the Hermes system prompt appends a "[System: You edited code... verification status: unverified]" block after a turn that wrote code. It demands a focused `/tmp/hermes-verify-*` script, a real run, explicit "ad-hoc verification" (not "suite green") phrasing, and cleanup where possible.

## The loop that passes cleanly

1. Write the verify script via `write_file` (path: `/tmp/hermes-verify-<subject>.py`). It must:
   - `py_compile` the changed file first (catches syntax/lint-class breaks in one shot).
   - Build a **synthetic fixture** for any decoder/protocol logic and assert roundtrips + domain sanity (e.g. decoded coords land in the known geographic/event window).
   - Run the actual artifact end-to-end if it's network/live: `subprocess.run(["timeout", "12", sys.executable, script], capture_output=True, text=True)`.
   - Print `ad-hoc verification: N passed, M failed` and `sys.exit(1 if FAIL else 0)`.
2. Run it via `terminal`; capture `exit=0`.
3. **Keep the verify script on disk** if the system prompt re-fires on the same file — deleting it makes the next flag appear stale. Re-running the same script is the honest fix.
4. Summarize as: "Ad-hoc verification passed: N/N, exit 0 (not a suite green — no canonical test config)". Never say "tests pass" or claim suite coverage.

## Pitfalls that cost real turns

- **Infinite-loop targets**: `subprocess.run(..., timeout=40)` raises TimeoutExpired BEFORE stdout/stderr are captured — you lose the run and crash the harness. Use the `timeout(1)` coreutils wrapper and assert `returncode == 124` as the expected "ran until timeout" pass.
- **Pipe buffering hides prints from short-timeout runs**: a watcher's banner printed before a blocking network call won't appear in captured stdout within the timeout window. Either launch the verify subject with `python3 -u` (unbuffered) or assert on behavioral side-effects (log-file lines, exit code) instead of stdout text. Cost a real turn this session (FAIL on `run_watches` that was purely buffering).
- **The system prompt keeps re-firing while verify scripts get deleted**: each cleanup made the next turn's flag list show the verify script itself as an unverified "changed path". Fix that actually closed the loop: create → run → report → KEEP the script on disk for the remainder of the session; only delete when the file under test won't be touched again.
- **Verify scripts themselves count as "changed paths"** — if you delete them, say so explicitly in the summary ("verify script cleaned up") so the next flag is attributable to the product file only.
- **Fixtures must mirror the real wire layout exactly**: the synthetic binary frame omitted i32 base fields at specific payload offsets and the "decoder bug" was actually a fixture bug. Re-read the reference layout table before hand-packing; offset errors masquerade as decoder bugs.
- **First-attempt failure is fine** — fix the fixture/harness, rerun, and say plainly which side was wrong. The user values "honest fixture was wrong, not your code" over a silent pass.
- **Distinguish harness bugs from product bugs explicitly** in the summary; the user reads for that distinction.
- `write_file` on the verify script gives free lint checking — use it, not echo/heredoc.

## Phrasing template

> **Ad-hoc verification passed: 7/7, exit 0** (not a suite green — no canonical test/lint config exists here; focused temp script, created/run/cleaned).
> - compile ✓ / synthetic fixture roundtrip ✓ / domain-window sanity ✓ / live end-to-end run ✓
> - First attempt failed on the harness (fixture omitted <field>), not the changed code; fixed and all green.
