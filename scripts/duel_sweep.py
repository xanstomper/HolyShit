#!/usr/bin/env python3
"""
duelbits full-spectrum sweep - runs on Vermes. Artifacts in /dev/shm/.dkv only.
Phases: secrets | fleet | endpoints | cors | tls | burst
Usage: python3 sweep.py [phase ...]   (no args = all in order)
Log: /dev/shm/.dkv/sweep.jsonl ; secrets report: /dev/shm/.dkv/secrets_report.txt
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
WORK = "/dev/shm/.dkv"
CHUNKS = os.path.join(WORK, "chunks")
LOG = os.path.join(WORK, "sweep.jsonl")

STATE = {"sleep": 1.2, "blocks": 0}


def log(d):
    d["t"] = time.strftime("%H:%M:%S")
    with open(LOG, "a") as f:
        f.write(json.dumps(d) + "\n")


def pace():
    time.sleep(STATE["sleep"])


def heat():
    STATE["blocks"] += 1
    STATE["sleep"] = min(STATE["sleep"] * 2, 20)
    if STATE["blocks"] >= 4:
        print(json.dumps({"verdict": "VANTAGE_BURNED"}))
        sys.exit(2)


def cool():
    STATE["blocks"] = 0


def hdrs(base=BASE, extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": base, "Referer": base + "/",
    }
    if extra:
        h.update(extra)
    return h


def chunk_names():
    r = requests.get(BASE + "/assets/index-CW30_Dqt.js", headers={
        "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
        "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }, timeout=25)
    names = sorted(set(re.findall(r'["\'](?:\./)?assets/([A-Za-z0-9_.-]+\.js)["\']', r.text)))
    return names


def phase_secrets():
    os.makedirs(CHUNKS, exist_ok=True)
    names = chunk_names()
    log({"phase": "secrets", "chunk_count": len(names)})
    print(f"--- chunks: {len(names)}")
    report = []
    PATS = [
        ("aws-key", r"AKIA[0-9A-Z]{16}"),
        ("sk-key", r"sk-[a-zA-Z0-9_\-]{20,}"),
        ("gh-token", r"gh[pousr]_[A-Za-z0-9]{30,}"),
        ("slack", r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
        ("google", r"AIza[0-9A-Za-z_\-]{30,}"),
        ("jwt-literal", r"eyJhbGci[A-Za-z0-9_\-.]{40,}"),
        ("private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY"),
        ("bearer", r"Bearer [A-Za-z0-9_\-.]{25,}"),
        ("bearer-assign", r"(?:api[_-]?key|apikey|secret|password|token|passwd)\s*[:=]\s*[`\"'][A-Za-z0-9_\-\.]{16,}[`\"']"),
        ("supabase", r"(https://[a-z0-9]{18,}\.supabase\.co)"),
        ("internal-ip", r"(?<![0-9.])(?:10|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.[0-9]+\.[0-9]+(?![0-9.])"),
        ("internal-host", r"[a-z0-9\-]+\.(?:internal|local|corp|intra|staging\.|dev\.)[a-z0-9.-]*"),
        ("sentry", r"@sentry\.io/[0-9]+|https://[a-f0-9]{32}@sentry"),
        ("sumsub", r"sumsub|SUMSUB"),
        ("paymentiq", r"paymentiq|PaymentIQ"),
        ("base64-blob", r"[\"'`]([A-Za-z0-9+/]{60,}={0,2})[\"'`]"),
    ]
    seen_urls = set()
    fetched = 0
    for i, n in enumerate(names):
        p = os.path.join(CHUNKS, n)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            try:
                r = requests.get(BASE + "/assets/" + n, headers={
                    "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
                    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors",
                    "Sec-Fetch-Site": "same-origin",
                }, timeout=20)
                if r.status_code == 200 and not r.text.startswith("<!DOCTYPE"):
                    open(p, "w").write(r.text)
                    fetched += 1
                elif r.status_code in (403, 429) or "Just a moment" in r.text[:200]:
                    heat()
                else:
                    cool()
            except Exception as e:
                log({"phase": "secrets", "err": str(e)[:80], "chunk": n})
        else:
            fetched += 1
        try:
            t = open(p).read()
        except Exception:
            continue
        for label, pat in PATS:
            for m in re.finditer(pat, t):
                v = m.group(0)[:90]
                if label == "base64-blob":
                    # only flag blobs that decode to ascii w/ key-ish content
                    try:
                        import base64
                        d = base64.b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4))
                        if not re.match(rb"^[\x20-\x7e]+$", d[:40]):
                            continue
                        v = d[:80].decode("ascii", "replace")
                    except Exception:
                        continue
                entry = {"chunk": n, "type": label, "value": v}
                if label in ("internal-ip", "internal-host", "supabase"):
                    entry["value"] = v
                report.append(entry)
        hosts = set(re.findall(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+\.(?:com|io|net|bet|dev|app|xyz|org)", t))
        for hname in hosts:
            if hname not in seen_urls and ("duelbits" in hname or "sportsbits" in hname
                                           or "switchflips" in hname):
                seen_urls.add(hname)
        if i % 40 == 0:
            pace()
        pace()
    hosts = sorted(seen_urls)
    with open(os.path.join(WORK, "secrets_report.txt"), "w") as f:
        f.write(json.dumps({"report": report, "hosts": hosts}, indent=1))
    # summarize: top types
    from collections import Counter
    c = Counter(e["type"] for e in report)
    print(f"--- fetched {fetched}/{len(names)} chunks; hosts: {len(hosts)}")
    print("--- host inventory:", hosts[:60])
    print("--- secret-type counts:", dict(c))
    for e in report:
        if e["type"] not in ("base64-blob",):
            print("--- HIT", e["type"], e["chunk"][:28], e["value"][:70])


def phase_fleet():
    out = {}
    # CT logs
    try:
        r = requests.get("https://crt.sh/?q=%25.duelbits.com&output=json", timeout=30,
                         headers={"User-Agent": UA})
        names = sorted({x["name_value"].replace("\n", " ").split(" ")[0]
                        for x in r.json()})
        out["ct_duelbits"] = names[:80]
        print(f"--- ct hosts: {len(names)}")
    except Exception as e:
        out["ct_err"] = str(e)[:100]
    try:
        r = requests.get("https://crt.sh/?q=%25.duelbits.io&output=json", timeout=30,
                         headers={"User-Agent": UA})
        names = sorted({x["name_value"].replace("\n", " ").split(" ")[0] for x in r.json()})
        out["ct_duelbits_io"] = names[:40]
    except Exception:
        pass
    # DNS: SPF/TXT origin leak
    for cmd in ("dig +short TXT duelbits.com", "dig +short TXT _dmarc.duelbits.com",
                "dig +short A dev.duelbits.com", "dig +short A staging.duelbits.com"):
        try:
            o = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=15).stdout
            out[cmd] = o.strip()[:300]
        except Exception as e:
            out[cmd] = str(e)[:80]
        print("---", cmd, "->", out[cmd][:160])
    # fleet probe: hosts from CT + bundle, dedupe, HEAD /
    hosts = set(out.get("ct_duelbits", [])) | set(out.get("ct_duelbits_io", []))
    try:
        hosts |= set(json.load(open(os.path.join(WORK, "secrets_report.txt")))["hosts"])
    except Exception:
        pass
    open(os.path.join(WORK, "fleet_hosts.json"), "w").write(json.dumps(sorted(hosts)))
    STATE["sleep"] = 4.0
    res = {}
    for h in sorted(hosts)[:40]:
        if "*" in h or " " in h:
            continue
        try:
            r = requests.head(f"https://{h}/", headers={"User-Agent": UA}, timeout=10,
                              allow_redirects=False)
            res[h] = r.status_code
        except Exception as e:
            res[h] = "ERR:" + str(e)[:40]
        print(f"--- {h}: {res[h]}")
        pace()
    out["fleet_probe"] = res
    open(os.path.join(WORK, "fleet_probe.json"), "w").write(json.dumps(res, indent=1))


def phase_endpoints():
    paths = set()
    for fn in os.listdir(CHUNKS):
        try:
            t = open(os.path.join(CHUNKS, fn)).read()
        except Exception:
            continue
        for m in re.finditer(r"[`\"'](/[a-zA-Z][a-zA-Z0-9/_$.\{\}\[\]-]{1,70})[`\"']", t):
            v = m.group(1)
            if re.search(r"\.(css|svg|png|jpg|woff|ico)|://", v):
                continue
            paths.add(v)
    paths = sorted(paths)
    open(os.path.join(WORK, "api_paths.json"), "w").write(json.dumps(paths, indent=1))
    print(f"--- distinct path literals: {len(paths)}")
    STATE["sleep"] = 5.0
    results = {}
    interesting = [p for p in paths if not re.search(
        r"^(/assets|/_next|/favicon)|\.(js|css|map|json|txt|xml|webmanifest)$", p)]
    for p in interesting[:60]:
        for base in (BASE + "/ws", BASE + "/auth"):
            try:
                r = requests.get(base + p, headers=hdrs(), timeout=12)
                k = "GET " + base.split("//")[1] + p
                results[k] = r.status_code
                cls = "json" if r.text[:1] in ("{", "[") else "html"
                if r.status_code == 200 and cls == "json":
                    print(f"--- OPEN {k}: {r.text[:140]}")
                elif r.status_code == 200:
                    print(f"--- 200-html {k}")
            except Exception as e:
                results[k] = "ERR"
        pace()
    open(os.path.join(WORK, "endpoint_probe.json"), "w").write(json.dumps(results, indent=1))


def phase_cors():
    STATE["sleep"] = 5.0
    res = {}
    for base in (BASE + "/ws", BASE + "/auth", BASE + "/gs"):
        for path in ("/config", "/user/bets/live", "/token?scope=ws"):
            try:
                r = requests.get(base + path, headers=hdrs(extra={
                    "Origin": "https://evil.example"}, ), timeout=12)
                acao = r.headers.get("access-control-allow-origin")
                acac = r.headers.get("access-control-allow-credentials")
                k = f"GET {base.split('//')[1]}{path}"
                res[k] = {"status": r.status_code, "acao": acao, "acac": acac}
                if acao:
                    print(f"--- CORS {k}: {acao} cred={acac}")
            except Exception as e:
                res[k] = str(e)[:60]
            pace()
    open(os.path.join(WORK, "cors_probe.json"), "w").write(json.dumps(res, indent=1))


def phase_tls():
    out = {}
    for host in ("duelbits.com", "duelbits.io", "api.duelbits.com"):
        try:
            o = subprocess.run(
                f"echo | openssl s_client -connect {host}:443 -servername {host} 2>/dev/null "
                f"| openssl x509 -noout -ext subjectAltName",
                shell=True, capture_output=True, text=True, timeout=15).stdout
            out[host] = o.strip()[:400]
            print(f"--- SAN {host}:", o.strip()[:260])
        except Exception as e:
            out[host] = str(e)[:60]
    try:
        r = requests.get(BASE + "/", headers={
            "User-Agent": UA, "Accept": "text/html,*/*", "Referer": BASE + "/",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none", "Upgrade-Insecure-Requests": "1",
            "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        }, timeout=15)
        sec = {k: v[:120] for k, v in r.headers.items()
               if k.lower() in ("strict-transport-security", "content-security-policy",
                                "x-frame-options", "x-content-type-options",
                                "referrer-policy", "permissions-policy", "server",
                                "set-cookie", "cf-ray")}
        out["headers"] = sec
        print("--- headers:", json.dumps(sec, indent=1)[:700])
    except Exception as e:
        out["headers"] = str(e)[:80]
    open(os.path.join(WORK, "tls_headers.json"), "w").write(json.dumps(out, indent=1))


def phase_burst():
    STATE["sleep"] = 0.25
    res = {"token_mint": [], "bets_live": []}
    for i in range(15):
        try:
            r = requests.post(BASE + "/auth/token?scope=ws", headers=hdrs(), timeout=10)
            res["token_mint"].append(r.status_code)
        except Exception:
            res["token_mint"].append("ERR")
    cool()
    time.sleep(3)
    for i in range(15):
        try:
            r = requests.get(BASE + "/ws/user/bets/live", headers=hdrs(), timeout=10)
            res["bets_live"].append(r.status_code)
        except Exception:
            res["bets_live"].append("ERR")
    cool()
    from collections import Counter
    res["token_mint_c"] = dict(Counter(res["token_mint"]))
    res["bets_live_c"] = dict(Counter(res["bets_live"]))
    print("--- burst results:", json.dumps(res["token_mint_c"]), json.dumps(res["bets_live_c"]))
    open(os.path.join(WORK, "burst.json"), "w").write(json.dumps(res))
    STATE["sleep"] = 5.0


PHASES = {"secrets": phase_secrets, "fleet": phase_fleet, "endpoints": phase_endpoints,
          "cors": phase_cors, "tls": phase_tls, "burst": phase_burst}

if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    wanted = sys.argv[1:] or list(PHASES)
    for name in wanted:
        print(f"===== PHASE {name}")
        try:
            PHASES[name]()
        except SystemExit:
            raise
        except Exception as e:
            print(f"--- phase {name} ERR: {repr(e)[:160]}")
