#!/usr/bin/env python3
"""focused miner: auth.store + APIConfig + index chunk -> exact /auth/web3 call-site shape"""
import re
import time

import requests

BASES = ["https://duelbits.com", "https://duelbits.io"]
TARGETS = [
    "/assets/index-CW30_Dqt.js",
    "/assets/auth.store-Bx48JkQE.js",
    "/assets/APIConfig-D3zTv-cI.js",
    "/assets/env-C6xo6VPS.js",
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def g(url, base, extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": base + "/",
        "Accept-Encoding": "gzip, deflate, br",
    }
    if extra:
        h.update(extra)
    return requests.get(url, headers=h, timeout=20)


def excerpts(t, pat, before, after, cap=3):
    out = []
    for m in re.finditer(pat, t):
        s = max(0, m.start() - before)
        out.append(t[s:m.end() + after])
        if len(out) >= cap:
            break
    return out


def main():
    base = BASES[0]
    for path in TARGETS:
        r = g(base + path, base)
        if r.status_code != 200 and "Just a moment" in r.text:
            r = g(BASES[1] + path, BASES[1])
        t = r.text
        print("===", path, r.status_code, len(t))
        if r.status_code != 200:
            time.sleep(9)
            continue
        for label, pat, b, a, cap in [
            ("authweb3", r"auth/web3", 260, 420, 4),
            ("signin-chunks", r"[A-Za-z0-9_.-]*sign-in[A-Za-z0-9_.-]*\.js", 40, 60, 6),
            ("web3-chunks", r"[A-Za-z0-9_.-]*web3[A-Za-z0-9_.-]*\.js", 40, 60, 8),
            ("signing", r"utf8ToHex|personal_sign|signMessage", 140, 160, 3),
            ("captcha", r"captcha|turnstile|recaptcha", 80, 120, 2),
        ]:
            ex = excerpts(t, pat, b, a, cap)
            if ex:
                print("--", label)
                for e in ex:
                    print("   ", e.replace("\n", " ")[:640])
        time.sleep(9)


if __name__ == "__main__":
    main()
