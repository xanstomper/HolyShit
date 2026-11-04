#!/usr/bin/env python3
"""
HOLYSHIT — Finder Engine CLI. Makes the case canon queryable and feeds the family.
stdlib-only.

Commands:
  cases                     index: every case file + title + mtime (vintage at a glance)
  recipe  --query "words"   search ALL case files + refs → matching recipes (ranked)
  recon   --domain X        discovery checklist generator (the finder's per-domain plan)
  dossier --target X        assemble everything known about a target → one markdown
  handoff --target X --to undercroft|3am [--findings "a;b;c"]
                            package finder findings into the consumer's native format
  vintage --target X [--days N]   staleness flags: findings/cases older than N days
  verify                    self-check

Exit codes: 0 ok · 2 usage/state error.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REFS = SKILL_DIR / "references"
DOMAINS = {
    "web": ["CT log sweep (crt.sh) for the apex + sister brands", "subdomain enum (passive first, then chunked active)",
            "era-stack fingerprinting on every live host", "ghost-route sweep from bundle conventions",
            "client bundle mining (routes, secrets, scope ids, odds/pricing math)", "OAuth/OIDC discovery on every auth plane"],
    "saas": ["org/workspace/tenant enumeration from public pages", "plan/limit documentation harvest (pricing pages, docs)",
             "app-marketplace/listing recon (integrations reveal internal APIs)", "status-page + changelog mining (new surfaces fast)",
             "CT logs for staging/admin tenant subdomains", "breach OSINT on the vendor stack"],
    "fintech": ["regulator archives (SEC/FINRA/CB list enforcement actions)", "payment-provider footprint (which PSPs, which contracts leak ranges)",
                "API doc archaeology (developer portals, postman workspaces)", "certificate transparency for api./pay./wallet. hosts",
                "breach-context OSINT (what similar targets lost)", "incident/disclosure history (what they patch slowly)"],
    "gaming": ["provably-fair verifier harvesting (client seeds/nonce schemes)", "game-config extraction from bundles (weights, ladders, RTP math)",
               "sister-brand/mirror enumeration (gamdom-class families)", "payment-flow mapping (deposits/withdrawals, PSP chains)",
               "support/helpdesk surface recon (reset/verification trust)", "tournament/promo page mining (bonus flow documentation)"],
    "social": ["public API surface (developer docs, GraphQL introspection history)", "oauth app ecosystem recon (3rd-party grants)",
               "media/CDN enumeration (user-content buckets)", "bot/automation API keys in public repos",
               "moderation/report-flow documentation", "fan-club/premium tier feature mapping"],
    "infra": ["ASN/IP range mapping (who hosts what)", "panel fingerprinting (:8080/:8443/:9000 era-panels)",
              "VPN/remote-access surface (gateways, version banners)", "firmware download portals (vendor support sites)",
              "OTA update channel discovery", "certificate chain analysis (internal CA leakage)"],
}
DOMAIN_ALIASES = {"site": "web", "website": "web", "shop": "web", "ecom": "web",
                  "casino": "gaming", "game": "gaming", "bank": "fintech", "payments": "fintech",
                  "iot": "infra", "hosting": "infra"}


def _case_files():
    return sorted(REFS.glob("case-*.md"))


def _title_of(p):
    try:
        for line in p.read_text(errors="replace").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except Exception:
        pass
    return p.stem


def cmd_cases(args):
    files = _case_files()
    now = datetime.now(timezone.utc)
    print(f"▸ HOLYSHIT case canon: {len(files)} case files")
    for p in files:
        age_days = (now - datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)).days
        flag = "  ⚠ stale" if age_days > args.days else ""
        print(f"  {p.name:52s} {age_days:4d}d{flag}  {_title_of(p)[:60]}")
    return 0


def cmd_recipe(args):
    words = [w.lower() for w in args.query.split() if w]
    if not words:
        print("✗ --query required", file=sys.stderr)
        return 2
    scored = []
    for p in sorted(REFS.glob("*.md")):
        try:
            text = p.read_text(errors="replace")
        except Exception:
            continue
        lines = text.splitlines()
        hits = []
        for i, line in enumerate(lines, 1):
            ll = line.lower()
            if any(w in ll for w in words):
                hits.append((i, line.strip()))
        if hits:
            scored.append((len(hits), p, hits))
    scored.sort(reverse=True)
    if not scored:
        print(f"· no recipe matches for: {args.query}")
        return 0
    print(f"▸ recipe search: '{args.query}' → {len(scored)} file(s), ranked")
    for score, p, hits in scored[:args.limit]:
        print(f"\n  ▸ {p.name} ({score} hits) — {_title_of(p)[:70]}")
        for i, line in hits[:args.lines]:
            print(f"    L{i}: {line[:105]}")
    return 0


def cmd_recon(args):
    d = DOMAIN_ALIASES.get(args.domain.lower(), args.domain.lower())
    if d not in DOMAINS:
        print(f"✗ domain {sorted(DOMAINS)} (aliases: {sorted(set(DOMAIN_ALIASES))})", file=sys.stderr)
        return 2
    print(f"▸ HOLYSHIT RECON PLAN — {d} ({len(DOMAINS[d])} passes)")
    for i, item in enumerate(DOMAINS[d], 1):
        print(f"  {i}. {item}")
    print("  ▸ every pass feeds findings → handoff --to undercroft|3am (the family consumes them)")
    return 0


def _family_states(target):
    camp = Path.home() / ".redteam" / "campaigns" / target
    out = {}
    for name, f in (("undercroft", camp / "undercroft-state.json"),
                    ("3am", camp / "state.json"),
                    ("kairo", camp / "hardware-state.json")):
        if f.exists():
            try:
                out[name] = json.loads(f.read_text())
            except Exception:
                pass
    return out


def cmd_dossier(args):
    target = args.target
    L = [f"# HOLYSHIT DOSSIER — {target}", "",
         f"assembled: {datetime.now(timezone.utc).isoformat()}", ""]
    # canon mentions
    needle = target.lower().replace("-", "")
    mentions = []
    for p in _case_files():
        try:
            text = p.read_text(errors="replace")
        except Exception:
            continue
        if needle in p.name.lower() or needle in text.lower():
            hits = sum(1 for line in text.lower().splitlines() if needle in line)
            mentions.append((hits, p, _title_of(p)))
    mentions.sort(reverse=True)
    L.append("## Case canon")
    if mentions:
        for hits, p, title in mentions[:8]:
            L.append(f"- {p.name} — {title} ({hits} mentions)")
    else:
        L.append("- no case file mentions this target")
    # family states
    states = _family_states(target)
    for name, st in states.items():
        L.append(f"## {name} state")
        for key in ("code", "surface", "logic"):
            for x in st.get(key, [])[:10]:
                label = x.get("seam") or x.get("endpoint") or x.get("asset") or "?"
                L.append(f"- [{key}] {label}: {x.get('status', '')}"
                         + (f" — {x.get('proof', '')[:80]}" if x.get("proof") else ""))
        for p_ in st.get("pocs", [])[:10]:
            L.append(f"- [poc] {p_.get('finding')}: {p_.get('request', '')[:80]}")
    # learned vectors
    lv = Path.home() / ".redteam" / "learned-vectors.jsonl"
    if lv.exists():
        rows = [json.loads(l) for l in lv.read_text().splitlines() if l.strip()]
        rel = [r for r in rows if target.lower() in r.get("probe", "").lower()]
        if rel:
            L.append("## Learned vectors touching target")
            L += [f"- flaw {r['flaw']}/{r['seam']}: {r['probe'][:90]}" for r in rel[:10]]
    out = args.output or f"{target}-dossier.md"
    Path(out).write_text("\n".join(L) + "\n")
    print(f"▸ dossier written: {out} ({len(mentions)} canon mentions, {len(states)} family states)")
    return 0


def cmd_handoff(args):
    now = datetime.now(timezone.utc).isoformat()
    findings = [f.strip() for f in (args.findings or "").split(";") if f.strip()]
    if args.to == "shukaku" and not findings:
        # derive findings from the family's CONFIRMED states (dossier-fed harvest)
        camp = Path.home() / ".redteam" / "campaigns" / args.target
        derived = []
        uc = camp / "undercroft-state.json"
        if uc.exists():
            u = json.loads(uc.read_text())
            for s in u.get("surface", []):
                if s.get("status") == "CONFIRMED":
                    derived.append((f"UC-SURFACE:{s.get('endpoint', '?')}",
                                    s.get("proof") or "CONFIRMED surface"))
            for l in u.get("logic", []):
                if l.get("status") == "CONFIRMED":
                    derived.append((f"UC-LOGIC:{l.get('seam', '?')}",
                                    l.get("proof") or "CONFIRMED logic seam"))
            for p in u.get("pocs", []):
                derived.append((f"UC-POC:{p.get('finding', 'poc')}",
                                p.get("proof") or "crafted PoC"))
        k = camp / "hardware-state.json"
        if k.exists():
            try:
                for v in json.loads(k.read_text()).get("vectors", []):
                    derived.append((f"KAIRO-VEC:{v.get('id', '?')}",
                                    v.get("proof") or "synthesized vector"))
            except Exception:
                pass
        findings = [f"{fid} :: {proof}" for fid, proof in derived]
        if not findings:
            print("· no CONFIRMED family findings yet — nothing to hand to the harvester")
            return 0
    if not findings:
        print("✗ --findings required ('a;b;c' — the finder's results)", file=sys.stderr)
        return 2
    if args.to == "undercroft":
        p = Path.home() / ".redteam" / "campaigns" / args.target / "undercroft-state.json"
        st = json.loads(p.read_text()) if p.exists() else {
            "target": args.target, "code": [], "surface": [], "logic": [], "pocs": [],
            "created": now}
        for f in findings:
            st.setdefault("logic", []).append({"seam": f, "where": "holyshit recon",
                                               "status": "PROBED", "proof": "", "delta": "finder handoff", "at": now})
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st, indent=2) + "\n")
        print(f"▸ handoff → undercroft: {len(findings)} finder finding(s) registered as PROBED in {p}")
    elif args.to == "3am":
        lv = Path.home() / ".redteam" / "learned-vectors.jsonl"
        lv.parent.mkdir(parents=True, exist_ok=True)
        with lv.open("a") as fh:
            for f in findings:
                fh.write(json.dumps({"flaw": 11, "seam": "A",
                                     "probe": f"HOLYSHIT RECON :: {f}",
                                     "confirmed_when": "finder-confirmed surface — sweep to verify"}) + "\n")
        print(f"▸ handoff → 3AM: {len(findings)} target-row(s) in {lv} (flaw 11 = observable-oracle/lead)")
    elif args.to == "shukaku":
        camp = Path.home() / ".redteam" / "campaigns" / args.target
        hs = camp / "harvest-state.json"
        st = json.loads(hs.read_text()) if hs.exists() else {
            "target": args.target, "ingested": [], "crown": [], "excluded": [],
            "disclosures": [], "created": now}
        st.setdefault("ingested", [])
        already = {i.get("finding") for i in st["ingested"]}
        added = 0
        for f in findings:
            fid, _, proof = f.partition(" :: ")
            proof = proof.strip() or "finder handoff"
            if fid in already:
                continue
            st["ingested"].append({"finding": fid, "proof": proof, "at": now})
            already.add(fid)
            added += 1
            cls = _crown_class_guess(f"{fid} {proof}")
            print(f"  → crown-class suggestion: {fid[:50]} → {cls}")
        hs.parent.mkdir(parents=True, exist_ok=True)
        hs.write_text(json.dumps(st, indent=2) + "\n")
        print(f"▸ handoff → shukaku: {added} finding(s) ingested → {hs}")
        print(f"  next: shukaku reason --target {args.target} && shukaku hunt --target {args.target}")
    else:
        print("✗ --to undercroft|3am|shukaku", file=sys.stderr)
        return 2
    return 0


# ── v2.2.0 the finder deepens: surface maps · pivot · crown-class guessing ────

ASSET_CLASSES = {
    "web":      ["CT log sweep (crt.sh)", "subdomain enum (passive → chunked active)",
                 "era-stack fingerprint per live host", "bundle mining (routes/secrets/scope ids)"],
    "api":      ["developer-portal archaeology", "schema mining (OpenAPI/GraphQL history)",
                 "authz matrix planning (org/tenant/plan ids)", "verb misuse + versioned legacy routes"],
    "mail":     ["SPF/DKIM/DMARC record audit", "OAuth mail-grant surface", "relay/spoof canon check"],
    "dns":      ["zone enumeration (AXFR, passive DNS)", "registrar/NS hygiene", "DNSSEC posture"],
    "cloud":    ["bucket/object-store naming sweep", "IAM/OIDC provider footprint",
                 "snapshot/backup exposure checks"],
    "repos":    ["public org/repo inventory", "commit/author identity leakage",
                 "secret-scan classes on owned repos", "CI/workflow surface"],
    "identity": ["IdP discovery (OIDC well-known)", "SSO/token-chain mapping",
                 "breach-context OSINT on the org"],
    "social":   ["official handles + staff mapping", "3rd-party oauth app grants",
                 "support/helpdesk trust flows"],
    "devices":  ["firmware portal mining", "OTA channel discovery", "panel fingerprinting",
                 "certificate chain (internal CA leak)"],
}
CLASS_KEYWORDS = {
    "web": ("web", "http", "route", "bundle", "fingerprint"),
    "api": ("api", "schema", "openapi", "graphql", "idor", "authz"),
    "mail": ("mail", "spf", "dkim", "spoof", "smtp", "relay"),
    "dns": ("dns", "zone", "subdomain", "ct log", "certificate"),
    "cloud": ("bucket", "s3", "iam", "cloud", "tenant", "oidc"),
    "repos": ("repo", "git", "secret", "commit", "source", "ci"),
    "identity": ("oauth", "sso", "token", "jwt", "session", "identity", "idp"),
    "social": ("social", "spam", "account", "handle", "moderation"),
    "devices": ("firmware", "uart", "jtag", "radio", "ble", "ota", "device", "hardware"),
}
NEXT_MANDATE = {"web": "undercroft", "api": "undercroft", "mail": "3am",
                "dns": "holyshit recon", "cloud": "kairo", "repos": "kairo",
                "identity": "3am", "social": "holyshit handoff", "devices": "kairo"}


def _crown_class_guess(text):
    t = text.lower()
    for kw, cls in (("user", "PII"), ("row", "PII"), ("email", "PII"),
                    ("card", "FIN"), ("payment", "FIN"), ("billing", "FIN"),
                    ("key", "CRED"), ("secret", "CRED"), ("token", "CRED"),
                    ("backup", "BACKUP"), ("dump", "BACKUP"), (".sql", "BACKUP"),
                    ("repo", "SRC"), ("source", "SRC"), ("tenant", "SASS"),
                    ("admin", "SASS"), ("export", "SASS")):
        if kw in t:
            return cls
    return "PII"


def _refs_by_class(cls):
    kws = CLASS_KEYWORDS[cls]
    refs = []
    for p in sorted(REFS.glob("*.md")):
        try:
            text = p.read_text(errors="replace").lower()
        except Exception:
            continue
        score = sum(1 for k in kws if k in text)
        if score:
            refs.append((score, p.name))
    refs.sort(reverse=True)
    return [name for _, name in refs[:3]]


def cmd_surface(args):
    d = DOMAIN_ALIASES.get(args.domain.lower(), args.domain.lower())
    classes = [args.cls] if args.cls else list(ASSET_CLASSES)
    if args.cls and args.cls not in ASSET_CLASSES:
        print(f"✗ --class one of {list(ASSET_CLASSES)}", file=sys.stderr)
        return 2
    print(f"═══ HOLYSHIT SURFACE MAP — {args.domain} ({d}) · {len(classes)} asset class(es) ═══")
    for cls in classes:
        refs = _refs_by_class(cls)
        nxt = NEXT_MANDATE[cls]
        print(f"  [ ] {cls:8s} → next: {nxt}")
        for act in ASSET_CLASSES[cls]:
            print(f"        · {act}")
        if refs:
            print(f"        canon: {', '.join(refs)}")
    print("  work the boxes top-down; every confirmed box hands off via `handoff`")
    return 0


def cmd_pivot(args):
    """Confirmed seams → canon case recipes → the suggested next mandate."""
    states = _family_states(args.target)
    confirmed = []
    uc = states.get("undercroft", {})
    for s in uc.get("surface", []):
        if s.get("status") == "CONFIRMED":
            confirmed.append(("undercroft/surface", s.get("endpoint", "?"),
                              s.get("proof", "")))
    for l in uc.get("logic", []):
        if l.get("status") == "CONFIRMED":
            confirmed.append(("undercroft/logic", l.get("seam", "?"),
                              l.get("proof", "")))
    am = states.get("3am", {}).get("exploit_intel", {})
    for c in am.get("chains", []):
        confirmed.append(("3am/chain", c.get("chain", "?"), str(c.get("status", ""))))
    if not confirmed:
        print("· no CONFIRMED findings in the family states yet — nothing to pivot")
        return 0
    print(f"═══ HOLYSHIT PIVOT — {args.target} · {len(confirmed)} confirmed ═══")
    for src, label, proof in confirmed:
        words = [w.lower() for w in re.split(r"[\W_]+", f"{label} {proof}") if len(w) > 3]
        canon = []
        for p in sorted(REFS.glob("*.md")):
            try:
                text = p.read_text(errors="replace").lower()
            except Exception:
                continue
            score = sum(1 for w in words if w in text)
            if score:
                canon.append((score, p.name))
        canon.sort(reverse=True)
        crown = _crown_class_guess(label)
        print(f"  {label[:52]} ({src})")
        if canon:
            print(f"      canon: {', '.join(n for _, n in canon[:2])}")
        print(f"      crown-class: {crown} · next: shukaku ingest (harvest) · kairo (compile)")
    return 0


def cmd_vintage(args):
    now = datetime.now(timezone.utc)
    stale = 0
    print(f"▸ vintage report (threshold: {args.days}d)")
    for p in _case_files():
        age = (now - datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)).days
        if age > args.days:
            stale += 1
            print(f"  ⚠ {p.name}: {age}d old — re-verify before citing (findings decay)")
    camp = Path.home() / ".redteam" / "campaigns" / args.target
    for name, f in (("undercroft", camp / "undercroft-state.json"), ("3am", camp / "state.json"),
                    ("kairo", camp / "hardware-state.json")):
        if not f.exists():
            continue
        try:
            st = json.loads(f.read_text())
        except Exception:
            continue
        for grp in ("code", "surface", "logic"):
            for x in st.get(grp, []):
                at = x.get("at", "")
                if at:
                    try:
                        age = (now - datetime.fromisoformat(at)).days
                        if age > args.days and x.get("status") == "CONFIRMED":
                            stale += 1
                            print(f"  ⚠ {name}/{grp}: {x.get('seam') or x.get('endpoint')} — CONFIRMED {age}d ago, re-verify (drift)")
                    except Exception:
                        pass
    print(f"▸ {stale} stale item(s)" if stale else "▸ all fresh")
    return 0


def cmd_verify(args):
    bad = []
    self = Path(__file__).resolve()
    if subprocess.run([sys.executable, "-m", "py_compile", str(self)],
                      capture_output=True).returncode != 0:
        bad.append("compile")
    help_out = subprocess.run([sys.executable, str(self), "--help"],
                              capture_output=True, text=True).stdout
    for want in ("cases", "recipe", "recon", "dossier", "handoff", "vintage", "verify",
                 "surface", "pivot"):
        if want not in help_out:
            bad.append(f"subcommand {want}")
    n_cases = len(_case_files())
    if n_cases < 10:
        bad.append(f"canon thin ({n_cases} case files)")
    if bad:
        print(f"✗ HOLYSHIT verify FAILED: {bad}")
        return 1
    print(f"✓ HOLYSHIT verify: compile · subcommands · canon ({n_cases} cases) — ALL PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="HOLYSHIT — Finder Engine CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cases", help="case-canon index + vintage flags")
    c.add_argument("--days", type=int, default=30)
    r = sub.add_parser("recipe", help="search the case canon (ranked)")
    r.add_argument("--query", required=True)
    r.add_argument("--limit", type=int, default=3)
    r.add_argument("--lines", type=int, default=4)
    rc = sub.add_parser("recon", help="per-domain discovery checklist")
    rc.add_argument("--domain", required=True)
    d = sub.add_parser("dossier", help="assemble everything known about a target")
    d.add_argument("--target", required=True)
    d.add_argument("--output")
    h = sub.add_parser("handoff", help="package findings for a consumer mandate")
    h.add_argument("--target", required=True)
    h.add_argument("--to", required=True, choices=["undercroft", "3am", "shukaku"])
    h.add_argument("--findings", help="'a;b:c' (optional for --to shukaku: derived from family states)")
    s = sub.add_parser("surface", help="attack-surface checklist per asset class")
    s.add_argument("--domain", required=True)
    s.add_argument("--class", dest="cls",
                   choices=list(ASSET_CLASSES), help="narrow to one asset class")
    pv = sub.add_parser("pivot", help="confirmed seams → canon recipes → next mandate")
    pv.add_argument("--target", required=True)
    v = sub.add_parser("vintage", help="staleness flags (findings decay)")
    v.add_argument("--target", default="_")
    v.add_argument("--days", type=int, default=30)
    vf = sub.add_parser("verify", help="self-check")
    a = ap.parse_args()
    if a.cmd == "cases":
        return cmd_cases(a)
    if a.cmd == "recipe":
        return cmd_recipe(a)
    if a.cmd == "recon":
        return cmd_recon(a)
    if a.cmd == "dossier":
        return cmd_dossier(a)
    if a.cmd == "handoff":
        return cmd_handoff(a)
    if a.cmd == "surface":
        return cmd_surface(a)
    if a.cmd == "pivot":
        return cmd_pivot(a)
    if a.cmd == "vintage":
        return cmd_vintage(a)
    if a.cmd == "verify":
        return cmd_verify(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())