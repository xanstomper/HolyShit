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
  report [--out FILE]                                  remediate-ranked markdown findings report
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

def cmd_report(target, out=None):
    """Emit a remediate-ranked markdown findings report from the ledger.
    Ranks: confirmed>&inconclusive>hypothesis, then by score desc. Writes to --out
    (default stdout). Returns 0."""
    data = load(target)
    classes = data.get("classes", {})
    chains = data.get("chains", [])
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # rank order: confirmed(3) > inconclusive(2) > hypothesis(1) > negative(0), by score desc
    _rank = {"confirmed": 3, "inconclusive": 2, "hypothesis": 1, "negative": 0}
    ordered = sorted(classes.items(),
                     key=lambda kv: (-_rank.get(kv[1].get("status", ""), 0),
                                     -(kv[1].get("score", 0) or 0)))
    conf = sum(1 for c in classes.values() if c.get("status") == "confirmed")
    hyp = sum(1 for c in classes.values() if c.get("status") == "hypothesis")
    neg = sum(1 for c in classes.values() if c.get("status") == "negative")

    L = []
    L.append(f"# Engagement Report — {target}")
    L.append("")
    L.append(f"**Generated:** {now}  ")
    L.append(f"**Classes tracked:** {len(classes)}  ")
    L.append(f"**Confirmed:** {conf} · **Hypothesis:** {hyp} · **Negative (ruled out):** {neg}  ")
    L.append(f"**Chains:** {len(chains)}")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Confirmed Holy Shits")
    L.append("")
    if conf == 0:
        L.append("_None yet._")
    for cid, rec in ordered:
        if rec.get("status") == "confirmed":
            L.append(f"### `{cid}`")
            L.append(f"- **Score:** {rec.get('score','-')}  ")
            L.append(f"- **Technique:** {rec.get('technique','—')}  ")
            L.append(f"- **Probed:** {rec.get('probe_count',0)}x, last {rec.get('last_probed','?')}")
            L.append("")
    L.append("## Hypotheses (need proof)")
    L.append("")
    if hyp == 0:
        L.append("_None._")
    for cid, rec in ordered:
        if rec.get("status") == "hypothesis":
            L.append(f"- `{cid}` — score {rec.get('score','-')} · probed {rec.get('probe_count',0)}x")
    L.append("")
    L.append("## Ruled Out (negative)")
    L.append("")
    if neg == 0:
        L.append("_None._")
    for cid, rec in ordered:
        if rec.get("status") == "negative":
            L.append(f"- `{cid}` — probed {rec.get('probe_count',0)}x, last {rec.get('last_probed','?')}")
    L.append("")
    L.append("## Attack Paths")
    L.append("")
    if not chains:
        L.append("_No chains recorded._")
    for c in chains:
        st = c.get("status", "hypothesis")
        L.append(f"### {c.get('crown_jewel','?')} _({st})_")
        L.append(f"- **Steps:** {' → '.join(c.get('steps', []))}  ")
        L.append(f"- **Impact:** {c.get('impact','')}")
        L.append("")
    L.append("---")
    L.append("")
    L.append("## Remediation Priority")
    L.append("")
    L.append("1. **Confirmed holyshits** — fix first (RCE, admin bypass, cross-tenant data, cloud cred theft).")
    L.append("2. **Confirmed chains** — each step is a dependency; fix the base primitive first.")
    L.append("3. **Hypotheses** — prove or dismiss with the next decisive test (see `next`).")
    L.append("4. **Re-verify confirmed on every deploy** — findings decay; a patch may not hold.")
    L.append("")
    report = "\n".join(L)
    if out:
        pathlib.Path(out).write_text(report)
        print(f"report written -> {out}")
    else:
        print(report)
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
    rep = sub.add_parser("report");       rep.add_argument("--target", default=os.environ.get("HOLYSHIT_TARGET",""))
    rep.add_argument("--out")
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
    if args.cmd == "report":
        return cmd_report(args.target, getattr(args, "out", None))
    return 0

if __name__ == "__main__":
    sys.exit(main())