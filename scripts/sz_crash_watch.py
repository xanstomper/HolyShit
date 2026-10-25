#!/usr/bin/env python3
"""Crash pre-crash leak oracle: watches /public/gambling/crash for an active game,
then rapid-polls to test if crash_point_hundredths is exposed before the crash.
Run: python3 sz_crash_watch.py [poll_seconds=3] [max_games=3]"""
import json, time, sys, urllib.request

UA = "Mozilla/5.0"
URL = "https://api.iceposeidon.com/public/gambling/crash"

def get():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

def main():
    poll_s = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    max_games = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    seen = 0
    print(f"watching crash (poll={poll_s}s, max_games={max_games}) ... ctrl-c to stop")
    while seen < max_games:
        try:
            d = get()
        except Exception as e:
            print("ERR", e); time.sleep(poll_s); continue
        g = d.get("game")
        if not g:
            time.sleep(poll_s); continue
        seen += 1
        print(f"\n=== GAME {seen} @ {time.strftime('%H:%M:%S')} ===")
        leak = None
        while True:
            keys = set(g.keys()) if isinstance(g, dict) else set()
            if "hundredths" in str(keys) or any("hundredths" in k for k in keys):
                leak = g
                print("!!!!! HUNDREDTHS LEAK PRE-CRASH !!!!!", g)
                break
            print(time.strftime('%H:%M:%S'), json.dumps(g)[:200])
            if g.get("status") in ("crashed", "ended", "complete") or g.get("crashed"):
                break
            try:
                d2 = get(); g = d2.get("game")
                if not g: break
            except Exception as e:
                print("ERR", e); break
            time.sleep(0.35)
        if leak:
            json.dump(leak, open("/tmp/crash_leak.json", "w"))
            print("LEAK SAVED /tmp/crash_leak.json")
        else:
            print(f"game {seen}: no hundredths leak observed pre-crash")
        time.sleep(2)
    print("done")

if __name__ == "__main__":
    main()
