#!/usr/bin/env python3
"""Offline convergence-check for holyconverge.py (CI + local). Mocked network."""
import sys, os, importlib.util

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holyconverge.py")
spec = importlib.util.spec_from_file_location("hc", SRC)
hc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hc)

orig_argv = sys.argv
orig_getenv = os.environ.get

def run_with(env, argv, fake_call):
    hc.call_model = fake_call
    env_full = dict(os.environ); env_full.update(env)
    os.environ.get = lambda k, d=None: env_full.get(k, orig_getenv(k, d))
    sys.argv = argv
    try:
        return hc.main()
    finally:
        sys.argv = orig_argv
        os.environ.get = orig_getenv

fails = []

def case(name, rc_expected, argv, env, fake_call, probe):
    calls = {"n": 0}
    if fake_call is None:
        def fake_call(*a, **k):
            calls["n"] += 1
            return {"model": "m", "ok": True, "latency_s": 0.1,
                    "text": "CONFIRMED: proof req+resp"}
    rc = run_with(env, argv, fake_call)
    ok = rc == rc_expected and probe(calls["n"])
    cell = ("PASS " if ok else "FAIL ") + name + f" (rc={rc}, calls={calls['n']})"
    print(cell)
    if not ok:
        fails.append(name)

base_env = {"HOLYSHIT_ENDPOINT": "http://x/v1", "HOLYSHIT_MODELS": "m1,m2",
            "HOLYSHIT_API_KEY": "k"}

# 1. converge -> 0
case("confirmed converges", 0,
     ["hc.py", "--budget 10", "--minproof 2", "chain"], base_env, None,
     lambda n: n <= 10)

# 2. budget exhaustion (always inconclusive) -> 3, honest no-fabricate
def inconcl(*a, **k):
    return {"model": "m", "ok": True, "latency_s": 0.1, "text": "INCONCLUSIVE: none"}
case("budget exhausted -> 3", 3,
     ["hc.py", "--budget 2", "--minproof 2", "chain"], base_env, inconcl,
     lambda n: n <= 2)

# 3. missing endpoint -> 2
case("missing env -> 2", 2,
     ["hc.py", "chain"], {}, None, lambda n: n == 0)

# 4. blocked path -> 1 (models block)
def blocking(*a, **k):
    return {"model": "m", "ok": True, "latency_s": 0.1, "text": "BLOCKED: step 2 disproven"}
case("blocked -> 1", 1,
     ["hc.py", "--budget 6", "--minproof 2", "chain"], base_env, blocking,
     lambda n: n <= 6)

print()
print("ALL PASS" if not fails else f"FAILURES: {fails}")
sys.exit(1 if fails else 0)