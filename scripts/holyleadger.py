#!/usr/bin/env python3
"""
holyleadger.py — persistent per-target engagement state for HolyShit!.

Implements mandate doctrine §28 (exhaustion ledger + sweep-state) as durable JSON so
state survives across sessions. The lever that compounds reliability: never re-probe a
definite negative, re-verify confirmed positives on every deploy, and prioritize the
highest-scoring unprobed crown-jewel classes — regardless of which session ran last.

Ledger file: ~/.hermes/scripts/holyleadger/<target>.json
(auto-snapped to the <slug>_baseline.json convention used elsewhere in this stack)

Data per target:
  classes:  {class_id: {status: confirmed|negative|inconclusive|hypothesis,
                         technique, score, evidence, probe_count, last_probed}}
  chains:   [{crown_jewel, steps, status: confirmed|blocked|hypothesis, impact}]
  meta:     {created, updated, last_scope, total_probes, confirmed_count}

Commands:
  add    CLASS ID STATUS [--technique T] [--score N]   record a probe result
  chain  JEWEL STEPS-STATUS [--impact ...]             record a finalized chain
  status [--target T] [--class CLASS]                  show table (confirmed/hypothesis/negative)
  next   [--top N]                                     list highest-value unprobed/actionable classes
  reset                                                clear a target's ledger (destructive)

Env: HOLYSHIT_SCRIPT_DIR overrides the ledger home; HOLYSHIT_TARGET sets default target.
"""
import os, sys, json, pathlib, argparse, datetime, re

DEFAULT_DIR = pathlib.Path(os.environ.get("HOLYSHIT_SCRIPT_DIR",
    pathlib.Path.home() / ".hermes" / "scripts")) / "holyleadger"

def _slug(target: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", target.replace("https://", "").replace("http://", "").rstrip("/")).strip("_")

def _path(target: str) -> pathlib.Path:
    return DEFAULT_DIR / f"{_slug(target)}.json"

def load(target: str) -> dict:
    p = _path(target)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return {"classes": {}, "chains": [], "meta": {}}

def save(target: str, data: dict) -> pathlib.Path:
    p = _path(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    data["meta"].setdefault("created", str(datetime.datetime.now(datetime.timezone.utc)))
    data["meta"]["updated"] = str(datetime.datetime.now(datetime.timezone.utc))
    data["meta"]["total_probes"] = sum(1 for c in data["classes"].values())
    data["meta"]["confirmed_count"] = sum(1 for c in data["classes"].values()
                                          if c["status"] == "confirmed")
    p.write_text(json.dumps(data, indent=2))
    return p

_STATUS = {"confirmed", "negative", "inconclusive", "hypothesis"}

def cmd_add(target, class_id, status, technique=None, score=None):
    data = load(target)
    rec = data["classes"].setdefault(class_id, {"status": status, "probe_count": 0})
    rec["status"] = status
    rec["probe_count"] = rec.get("probe_count", 0) + 1
    if technique: rec["technique"] = technique
    if score is not None: rec["score"] = int(score)
    rec["last_probed"] = str(datetime.datetime.now(datetime.timezone.utc))
    p = save(target, data)
    print(f"recorded {class_id}={status} (probe #{rec['probe_count']}) -> {p}")
    return 0

def cmd_chain(target, jewel, steps_status, impact=None):
    data = load(target)
    # steps_status like "SSRF-PRIMITIVE→IMDS→CLOUD-CREDS:confirmed"
    steps_s, _, status = steps_status.rpartition(":")
    steps = [s.strip() for s in steps_s.split("→")]
    chain = {"crown_jewel": jewel, "steps": steps,
             "status": status if status in _STATUS else "hypothesis",
             "impact": impact or "",
             "recorded": str(datetime.datetime.now(datetime.timezone.utc))}
    data["chains"].append(chain)
    p = save(target, data)
    print(f"chain recorded ({chain['status']}, {len(steps)} steps) -> {p}")
    return 0

def cmd_status(target, class_filter=None):
    data = load(target)
    print(f"\n=== LEDGER: {target} ===")
    print(f"total probes: {data['meta'].get('total_probes',0)}  "
          f"confirmed: {data['meta'].get('confirmed_count',0)}  "
          f"chains: {len(data['chains'])}")
    rows = sorted(data["classes"].items(),
                  key=lambda kv: (-(kv[1].get("score",0)), kv[1].get("last_probed","")))
    shown = 0
    for cid, rec in rows:
        if class_filter and class_filter not in cid:
            continue
        print(f"  [{rec['status']:<12}] {cid:<40} score={rec.get('score','-'):<5} "
              f"probes={rec.get('probe_count',0)}")
        shown += 1
    if not shown:
        print("  (no classes recorded yet)")
    if data["chains"]:
        print("  -- chains --")
        for c in data["chains"]:
            print(f"  [{c['status']:<12}] {c['crown_jewel']}: {' → '.join(c['steps'])}")
    return 0

def cmd_next(target, top=5):
    """Pairs with doctrine §28: re-verify confirmed, never re-probe negative, surface highest."""
    data = load(target)
    actionable = []
    for cid, rec in data["classes"].items():
        s = rec["status"]
        if s == "confirmed":
            actionable.append(("RE-VERIFY (decays)", rec.get("score", 0), cid))
        elif s == "inconclusive" and rec.get("score", 0) >= 50:
            actionable.append(("RE-PROBE crown path", rec.get("score", 0), cid))
        elif s == "hypothesis":
            actionable.append(("PROVE hypothesis", rec.get("score", 0), cid))
        # negative -> explicitly NOT actionable (doctrine: never re-probe w/o code change)
    actionable.sort(key=lambda x: -x[1])
    print(f"\n=== NEXT ACTIONS: {target} (top {top}) ===")
    if not actionable:
        print("  nothing actionable — ledger clean or empty")
        return 0
    for kind, score, cid in actionable[:top]:
        print(f"  {score:>3}  {kind:<20} {cid}")
    print("\n  (negatives excluded — re-probe only after a code/stack change)")
    return 0

def cmd_reset(target):
    p = _path(target)
    if p.exists():
        p.unlink()
        print(f"reset {p}")
        return 0
    print("no ledger for target")
    return 0

def main() -> int:
    ap = argparse.ArgumentParser(prog="holyleadger", description="persistent HolyShit! engagement state")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add");            a.add_argument("class_id"); a.add_argument("status", choices=_STATUS)
    a.add_argument("--technique");        a.add_argument("--score", type=int)
    a.add_argument("--target", default=os.environ.get("HOLYSHIT_TARGET", ""))
    c = sub.add_parser("chain");          c.add_argument("jewel"); c.add_argument("steps_status")
    c.add_argument("--impact");           c.add_argument("--target", default=os.environ.get("HOLYSHIT_TARGET",""))
    s = sub.add_parser("status");         s.add_argument("--target", default=os.environ.get("HOLYSHIT_TARGET",""))
    s.add_argument("--class")
    n = sub.add_parser("next");           n.add_argument("--target", default=os.environ.get("HOLYSHIT_TARGET",""))
    n.add_argument("--top", type=int, default=5)
    r = sub.add_parser("reset");          r.add_argument("--target", default=os.environ.get("HOLYSHIT_TARGET",""))
    args = ap.parse_args()

    if not args.target:
        print("holyleadger: no target. Pass --target or export HOLYSHIT_TARGET", file=sys.stderr)
        return 2
    if args.cmd == "add":
        return cmd_add(args.target, args.class_id, args.status, args.technique, args.score)
    if args.cmd == "chain":
        return cmd_chain(args.target, args.jewel, args.steps_status, args.impact)
    if args.cmd == "status":
        return cmd_status(args.target, getattr(args, "class", None))
    if args.cmd == "next":
        return cmd_next(args.target, args.top)
    if args.cmd == "reset":
        return cmd_reset(args.target)
    return 0

if __name__ == "__main__":
    sys.exit(main())