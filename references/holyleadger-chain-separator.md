# holyleadger chain command — exact separator semantics (corrected 2026-10-14)

The `chain` splitter in `scripts/holyleadger.py` line 89 is:

```python
steps_s, _, status = steps_status.rpartition(":")
steps = [s.strip() for s in steps_s.split("→")]   # UNICODE arrow, not "->"
```

Consequences (verified live 2026-10-14; the prior `->` doc note was misleading):

1. **A `:status` suffix is REQUIRED.** The chain arg must look like `"A→B→C:confirmed"`.
   Without the trailing `:status`, `rpartition(":")` finds no colon, the WHOLE string becomes
   `steps_s`, and if the arrows then split it the status falls back to `hypothesis`; worse, a
   chain value that never reaches the script cleanly records as `steps:[""]` (1 step, empty).
2. **Use the UNICODE `→` (U+2192), not ASCII `->`.** The splitter splits only on `→`.
   An ASCII `->` chain will NOT split → records as a single opaque step → 1 step.
3. **Keep `--impact` free of arrow sequences** (both `->` and `→`) — split happens on the whole
   `steps_status` arg only, but an arrow in impact text is confusing when reading the report.
4. **Pass the literal `→` via Python `subprocess` argv, NOT a shell heredoc/echo.** Shells and
   the terminal tool mangle the unicode arrow when it rides through a string literal. Safest:
   build `chain_val = "A→B→C:confirmed"` in Python and invoke
   `subprocess.run(['python3','scripts/holyleadger.py','chain',jewel,chain_val,'--target',t,'--impact',...])`.
5. If you still get `1 step` + `[""]` after following all of the above, just write the chain
   dict straight into the ledger JSON (`data['chains'].append({...})`) — the ledger is just JSON;
   the CLI is a convenience, not the only writer.