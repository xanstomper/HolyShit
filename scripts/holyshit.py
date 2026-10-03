#!/usr/bin/env python3
"""
holyshit.py — unified entrypoint for the HolyShit! red-team framework.

Wraps the three tools into one command so an engagement runs as a single loop:
  dispatch -> converge -> persist.

Subcommands (thin, faithful passes to the underlying scripts):

  run     <task>                 dispatch (holyshit-inject) then persist result
  scan    <task>                 dispatch + converge a candidate to confirmation
  converge <task>                multi-model confirmation loop (holyconverge)
  dispatch <task>                single/chain/consensus dispatch (holyshit-inject)

Env (same as the individual tools):
  HOLYSHIT_ENDPOINT  HOLYSHIT_API_KEY  HOLYSHIT_MODELS  HOLYSHIT_TARGET
  HOLYSHIT_SCRIPT_DIR (ledger home override)

Exit codes: 0 ok, 1 blocked/harness-fail, 2 bad usage/env, 3 budget-exhausted(converge).
"""
import os, sys, pathlib, subprocess, argparse

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = {
    "inject": HERE / "holyshit-inject.py",
    "converge": HERE / "holyconverge.py",
    "leadger": HERE / "holyleadger.py",
}

def _env_requires(msg):
    print(f"holyshit: {msg}", file=sys.stderr)
    return 2

def _run(script_path, args, env=None):
    cmd = [sys.executable, str(script_path)] + args
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(cmd, env=e)

def cmd_dispatch(args):
    if not os.environ.get("HOLYSHIT_ENDPOINT") or not os.environ.get("HOLYSHIT_MODELS"):
        return _env_requires("HOLYSHIT_ENDPOINT + HOLYSHIT_MODELS required for dispatch")
    cli = []
    if getattr(args, "consensus", False): cli.append("--consensus")
    if getattr(args, "chain", False): cli.append("--chain")
    cli.append(args.task)
    p = _run(SCRIPTS["inject"], cli)
    return p.returncode

def cmd_converge(args):
    if not os.environ.get("HOLYSHIT_ENDPOINT") or len(
            [m for m in os.environ.get("HOLYSHIT_MODELS","").split(",") if m]) < 2:
        return _env_requires("HOLYSHIT_ENDPOINT + >=2 models in HOLYSHIT_MODELS for converge")
    cli = ["--budget", str(getattr(args, "budget", 12)), "--minproof",
           str(getattr(args, "minproof", 2)), args.task]
    p = _run(SCRIPTS["converge"], cli)
    rc = p.returncode
    _persist_converge_outcome(args, rc)
    return rc

def _persist_converge_outcome(args, rc):
    """Auto-persist a converge result to the ledger (closes the dispatch->persist loop).
    Only when a target is set; derives a stable class ID from the task string."""
    target = os.environ.get("HOLYSHIT_TARGET", "")
    if not target:
        return
    class_id = _slug(args.task)
    if rc == 0:   # CONFIRMED
        _run(SCRIPTS["leadger"], ["add", class_id, "confirmed", "--target", target])
        _run(SCRIPTS["leadger"], ["chain", class_id, f"DISPATCHED→{class_id}:confirmed",
                                  "--target", target, "--impact", args.task[:200]])
    elif rc in (1, 3):  # BLOCKED or budget-exhausted -> hypothesis (gap not auto-known)
        _run(SCRIPTS["leadger"], ["add", class_id, "hypothesis", "--target", target])

def _slug(s: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9._-]", "_", s).strip("_")[:64] or "task"

def cmd_scan(args):
    """dispatch then converge: the full confirm loop on one task."""
    rc = cmd_dispatch(args)
    if rc != 0:
        return rc
    print("\n[holyshit] dispatch ok — converging confirmation...", file=sys.stderr)
    # reuse the dispatch task + same env for converge
    return cmd_converge(args)

def cmd_leadger(args):
    cli = [args.lead_cmd] + [a for a in [args.argextra] if a]
    p = _run(SCRIPTS["leadger"], cli)
    return p.returncode

def main() -> int:
    ap = argparse.ArgumentParser(prog="holyshit",
        description="unified HolyShit! red-team framework CLI (dispatch/converge/persist)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("dispatch"); d.add_argument("--consensus", action="store_true")
    d.add_argument("--chain", action="store_true"); d.add_argument("task")
    c = sub.add_parser("converge"); c.add_argument("--budget", type=int, default=12)
    c.add_argument("--minproof", type=int, default=2); c.add_argument("task")
    s = sub.add_parser("scan"); s.add_argument("--consensus", action="store_true")
    s.add_argument("--chain", action="store_true"); s.add_argument("--budget", type=int, default=12)
    s.add_argument("--minproof", type=int, default=2); s.add_argument("task")
    l = sub.add_parser("run")  # alias: dispatch only, simplest
    l.add_argument("task")

    args = ap.parse_args()
    if args.cmd == "dispatch":
        return cmd_dispatch(args)
    if args.cmd == "converge":
        return cmd_converge(args)
    if args.cmd == "scan":
        return cmd_scan(args)
    if args.cmd == "run":
        return cmd_dispatch(args)
    return 0

if __name__ == "__main__":
    sys.exit(main())