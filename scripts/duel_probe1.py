#!/usr/bin/env python3
"""one-shot probe: dump shell structure of duelbits.io + OIDC path on .com to find real asset paths"""
import re
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def g(url, extra=None):
    h = {
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if extra:
        h.update(extra)
    return requests.get(url, headers=h, timeout=20)


def dump(label, r):
    t = r.text
    print("===", label, r.status_code, len(t))
    print("title:", re.findall(r"<title[^>]*>(.*?)</title>", t, re.S)[:1])
    print("script-tags:", [s[:120] for s in re.findall(r"<script[^>]*>", t)[:8]])
    print("js-refs:", re.findall(r"[\"']([^\"' ]{4,120}?\.js[^\"' ]{0,20})[\"']", t)[:24])
    print("head-400:", re.sub(r"\s+", " ", t[:400]))
    return t


dump("io-root", g("https://duelbits.io/"))
time.sleep(6)
dump("com-oidc", g("https://duelbits.com/.well-known/openid-configuration"))
time.sleep(6)
dump("com-root", g("https://duelbits.com/"))
