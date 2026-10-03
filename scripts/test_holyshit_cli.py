#!/usr/bin/env python3
"""Offline wiring test for holyshit.py unified CLI (CI + local). Traps subprocess.run
so orchestration is proven without any real endpoint/network."""
import sys, os, importlib.util

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holyshit.py")
spec = importlib.util.spec_from_file_location("h", SRC)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)

os.environ.update({"HOLYSHIT_ENDPOINT": "http://x/v1", "HOLYSHIT_MODELS": "m1,m2",
                   "HOLYSHIT_API_KEY": "k", "HOLYSHIT_TARGET": "t"})

calls = []
h.subprocess.run = lambda cmd, env=None: (calls.append(cmd) or type("P", (), {"returncode": 0})())

_orig = sys.argv
fails = []
def check_sub(name, argv, want):
    calls.clear()
    sys.argv = argv
    rc = h.main()
    ok = rc == 0 and any(want in c[1] for c in calls) if want else rc == 0
    print(("PASS " if ok else "FAIL ") + name + f" (rc={rc})")
    if not ok: fails.append(name)
    sys.argv = _orig

check_sub("run -> dispatch", ["h", "run", "hello"], "holyshit-inject")
check_sub("converge -> holyconverge", ["h", "converge", "chain"], "holyconverge")
check_sub("dispatch --chain", ["h", "dispatch", "--chain", "t"], "holyshit-inject")
check_sub("scan -> both", ["h", "scan", "candidate"], None)  # composite, check len below

# scan should have made 2 calls (inject + converge)
calls.clear()
sys.argv = ["h", "scan", "candidate"]; rc = h.main(); sys.argv = _orig
scan_ok = rc == 0 and len(calls) == 2 and "holyshit-inject" in calls[0][1] and "holyconverge" in calls[1][1]
print(("PASS " if scan_ok else "FAIL ") + f"scan makes both calls (calls={len(calls)})")
if not scan_ok: fails.append("scan both")

print()
print("ALL PASS" if not fails else f"FAILURES: {fails}")
sys.exit(1 if fails else 0)