#!/usr/bin/env python3
"""probe31: chain-direction test - is seed[N+1] = sha256(seed[N])? (roulette local + crash remote) + crash formula fit"""
import hashlib
import json
import time

import requests

BASE = "https://duelbits.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


# 1) roulette daily seeds: forward chain?
seeds = json.load(open("/dev/shm/.dkv/roulette_seeds.json"))
seeds.sort(key=lambda x: x["startRound"])
fwd = sum(1 for a, b in zip(seeds, seeds[1:]) if sha(a["serverSeed"]) == b["serverSeed"])
rev = sum(1 for a, b in zip(seeds, seeds[1:]) if sha(b["serverSeed"]) == a["serverSeed"])
pub_in = sum(1 for a, b in zip(seeds, seeds[1:])
             if b["serverSeed"] == sha(a["serverSeed"] + a["publicSeed"]))
print(f"--- roulette chain: forward={fwd} reverse={rev} seed+pubseed={pub_in} of {len(seeds)-1} links")

# 2) crash history chain + ticket formula fit
def hdrs():
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin", "Origin": BASE, "Referer": BASE + "/",
    }


r = requests.get(BASE + "/ws/games/crash/history", headers=hdrs(), timeout=20)
recs = r.json().get("history", [])
recs.sort(key=lambda x: x["startedAt"])
print("--- crash rounds:", len(recs))
open("/dev/shm/.dkv/crash_history.json", "w").write(json.dumps(recs))

fwd = sum(1 for a, b in zip(recs, recs[1:]) if sha(a["serverSeed"]) == b["serverSeed"])
rev = sum(1 for a, b in zip(recs, recs[1:]) if sha(b["serverSeed"]) == a["serverSeed"])
print(f"--- crash chain: forward={fwd} reverse={rev} of {len(recs)-1} links")

# 3) ticket formula hunt (post-hoc): ticket vs f(serverSeed, id)
def fits(fn, name):
    ok = 0
    for x in recs:
        try:
            if fn(x["serverSeed"], x["id"], x["startedAt"]) == x["ticket"]:
                ok += 1
        except Exception:
            pass
    print(f"--- formula {name}: {ok}/{len(recs)}")
    return ok


fits(lambda s, i, t: int(sha(f"{s}:{i}").hexdigest()[:8], 16) % 10000, "sha(seed:id)[:8]%10000")
fits(lambda s, i, t: int(sha(f"{s}:{i}").hexdigest()[:8], 16) % 1000, "sha(seed:id)[:8]%1000")
fits(lambda s, i, t: int(sha(f"{i}:{s}").hexdigest()[:8], 16) % 10000, "sha(id:seed)[:8]%10000")
fits(lambda s, i, t: (int(sha(s + str(i)).hexdigest()[:13], 16) % 10000), "sha(seed+id)[:13]%10000")

# crash game chunk for the real verifier code
r = requests.get(BASE + "/assets/fairness-BrSEdCht.js", headers={
    "User-Agent": UA, "Accept": "*/*", "Referer": BASE + "/",
    "Sec-Fetch-Dest": "script", "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Site": "same-origin",
}, timeout=20)
t = r.text
m = re.search = None
import re
i = t.find("crash")
while i != -1:
    seg = t[max(0, i - 300):i + 400]
    if "ticket" in seg or "multiplier" in seg or "hash" in seg.lower():
        print("--- fairness crash ctx:", seg.replace("\n", " ")[:520])
        break
    i = t.find("crash", i + 1)
