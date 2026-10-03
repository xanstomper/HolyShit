#!/usr/bin/env python3
"""
holyshit.py — unified entrypoint for the HolyShit! red-team framework.

Wraps the three tools into one command so an engagement runs as a single loop:
  dispatch -> converge -> persist.

Subcommands (thin, faithful passes to the underlying scripts):

  plan    [--top N] [--target T]  emit ordered probe queue from ledger state
  run     <task>                  dispatch (holyshit-inject) then persist result
  scan    <task>                  dispatch + converge a candidate to confirmation
  converge <task>                 multi-model confirmation loop (holyconverge)
  dispatch <task>                 single/chain/consensus dispatch (holyshit-inject)

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

def _slug(s: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9._-]", "_", s).strip("_")[:64] or "task"

# ---------------------------------------------------------------------------
# Crown-jewel autoplanner: read ledger next-state, emit ordered scan commands.
# The operator doesn't decide what to probe — the framework does.
# ---------------------------------------------------------------------------

# High-yield probe templates keyed by class-ID substring (first hit wins).
# Each value is a task string passed to `holyshit scan`. {class} is substituted.
_PROBE_TEMPLATES = [
    ("ssrf",      "verify SSRF to internal metadata (IMDS 169.254.169.254) via {class}"),
    ("idor",      "test IDOR / object-level authz on {class} across tenants"),
    ("jwt",       "probe JWT alg=none / weak-secret / kid-injection on {class}"),
    ("auth",      "map auth seam on {class}: token refresh, session fixation, OAuth state"),
    ("admin",     "attempt privilege escalation to admin via {class} role confusion"),
    ("sqli",      "test SQLi on {class} with error/union/time-based vectors"),
    ("xss",       "test stored/reflected XSS on {class} with CSP bypass variants"),
    ("ssti",      "test SSTI on {class} template rendering endpoint"),
    ("xxe",       "test XXE on {class} XML parser for file read / SSRF pivot"),
    ("deser",     "test insecure deserialization on {class} for RCE gadget"),
    ("upload",    "test file-upload on {class}: path traversal, polyglot, MIME bypass"),
    ("redirect",  "test open-redirect on {class} for OAuth token leakage"),
    ("csrf",      "test CSRF on {class} state-changing endpoint"),
    ("cors",      "test CORS misconfig on {class} for cross-origin data theft"),
    ("bucket",    "check public/signed S3 or GCS bucket exposure on {class}"),
    ("subdomain", "check subdomain takeover on {class} dangling CNAME"),
    ("secrets",   "hunt hardcoded secrets / sourcemaps in {class} client bundles"),
    ("rate",      "test rate-limiter bypass on {class} via type-coercion / dual-stack"),
    ("webhook",   "test webhook replay / signature bypass on {class}"),
    ("graphql",   "introspect + batch/alias abuse on {class} GraphQL endpoint"),
    ("grpc",      "probe gRPC reflection + unauthenticated methods on {class}"),
    ("cache",     "test web-cache poisoning on {class} via unkeyed headers"),
    ("sso",       "test SAML/OAuth SSO bypass on {class} assertion tampering"),
    ("api",       "fuzz {class} API for undocumented methods / 405-matrix"),
    ("cloud",     "check cloud metadata / IAM escalation via {class} SSRF chain"),
    ("path",      "test path-traversal / LFI on {class} file endpoints"),
    ("cmd",       "test command injection on {class} system/exec parameters"),
    ("ldap",      "test LDAP injection on {class} directory search"),
    ("xpath",     "test XPath injection on {class} XML query"),
    ("header",    "test HTTP header injection / request smuggling on {class}"),
    ("race",      "test race condition on {class} balance/limit transfer"),
    ("logic",     "test business-logic flaw on {class} state machine bypass"),
    ("payment",   "test stateless payment / amount-tamper on {class} checkout"),
    ("password",  "test password-reset poisoning / token leak on {class} flow"),
    ("mfa",       "test MFA bypass on {class} via downgraded factor / replay"),
    ("oauth",     "test OAuth redirect_uri / token-exchange abuse on {class}"),
    ("websocket", "test WebSocket authz / CSWSH on {class} socket endpoint"),
]

_GENERIC_TEMPLATE = "run the highest-priority probe for {class} per vector-matrix"

def _probe_for_class(class_id):
    cid = class_id.lower()
    for key, tmpl in _PROBE_TEMPLATES:
        if key in cid:
            return tmpl.format(**{"class": class_id})
    return _GENERIC_TEMPLATE.format(**{"class": class_id})

def cmd_dispatch(args):
    if not os.environ.get("HOLYSHIT_ENDPOINT") or not os.environ.get("HOLYSHIT_MODELS"):
        return _env_requires("HOLYSHIT_ENDPOINT + HOLYSHIT_MODELS required for dispatch")
    cli = []
    if getattr(args, "consensus", False): cli.append("--consensus")
    if getattr(args, "chain", False): cli.append("--chain")
    cli.append(args.task)
    p = _run(SCRIPTS["inject"], cli)
    return p.returncode

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

def cmd_plan(args):
    """Read the ledger's next-state and emit ordered, ready-to-run scan commands."""
    target = getattr(args, "target", None) or os.environ.get("HOLYSHIT_TARGET", "")
    if not target:
        return _env_requires("HOLYSHIT_TARGET required for plan (or pass --target)")
    import io, contextlib, re
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("ledger", str(SCRIPTS["leadger"]))
    ledger = _ilu.module_from_spec(spec); spec.loader.exec_module(ledger)
    ledger.DEFAULT_DIR = pathlib.Path(os.environ.get(
        "HOLYSHIT_SCRIPT_DIR", pathlib.Path.home()/".hermes/scripts"))/"holyleadger"
    top = getattr(args, "top", 10)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ledger.cmd_next(target, top)
    raw = buf.getvalue()
    actionable = []
    for line in raw.splitlines():
        m = re.match(r"\s*(\d+|-)\s+(\S.*?)\s{2,}(\S+)$", line)
        if m:
            score, kind, cid = m.group(1), m.group(2), m.group(3)
            actionable.append((cid, kind, score))
    if not actionable:
        print(f"plan: no actionable classes in ledger for target '{target}'. Ledger clean.")
        return 0
    print(f"=== HOLYSHIT PLAN — {target} (top {top}) ===")
    print(f"# {'='*60}")
    print(f"# Auto-generated probe queue. Execute in order; each persists to the ledger.")
    print(f"# Re-run `plan` after each scan to re-rank.")
    print(f"# {'='*60}\n")
    me = pathlib.Path(__file__).resolve()
    for i, (cid, kind, score) in enumerate(actionable, 1):
        probe = _probe_for_class(cid)
        print(f'python3 {me} scan "{probe}"   # [{i}] {kind} score={score}')
    print(f"\n# Next: run `python3 {me} ledger report` for the full findings report.")
    return 0

def cmd_scan(args):
    """dispatch then converge: the full confirm loop on one task."""
    rc = cmd_dispatch(args)
    if rc != 0:
        return rc
    print("\n[holyshit] dispatch ok — converging confirmation...", file=sys.stderr)
    return cmd_converge(args)

def cmd_leadger(args):
    cli = [args.lead_cmd] + [a for a in [args.argextra] if a]
    p = _run(SCRIPTS["leadger"], cli)
    return p.returncode

def main() -> int:
    ap = argparse.ArgumentParser(prog="holyshit",
        description="unified HolyShit! red-team framework CLI (dispatch/converge/persist/plan)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("plan"); pl.add_argument("--top", type=int, default=10)
    pl.add_argument("--target", default=os.environ.get("HOLYSHIT_TARGET", ""))
    d = sub.add_parser("dispatch"); d.add_argument("--consensus", action="store_true")
    d.add_argument("--chain", action="store_true"); d.add_argument("task")
    c = sub.add_parser("converge"); c.add_argument("--budget", type=int, default=12)
    c.add_argument("--minproof", type=int, default=2); c.add_argument("task")
    s = sub.add_parser("scan"); s.add_argument("--consensus", action="store_true")
    s.add_argument("--chain", action="store_true"); s.add_argument("--budget", type=int, default=12)
    s.add_argument("--minproof", type=int, default=2); s.add_argument("task")
    l = sub.add_parser("run"); l.add_argument("task")
    le = sub.add_parser("ledger"); le.add_argument("lead_cmd")
    le.add_argument("argextra", nargs="?", default="")

    args = ap.parse_args()
    if args.cmd == "plan":
        return cmd_plan(args)
    if args.cmd == "dispatch":
        return cmd_dispatch(args)
    if args.cmd == "converge":
        return cmd_converge(args)
    if args.cmd == "scan":
        return cmd_scan(args)
    if args.cmd == "run":
        return cmd_dispatch(args)
    if args.cmd == "ledger":
        return cmd_leadger(args)
    return 0

if __name__ == "__main__":
    sys.exit(main())