#!/usr/bin/env python3
"""Ad-hoc verification harness for holyshit-inject.py (no network required).

Run:  python3 ~/.hermes/skills/security/holyshit-mode/scripts/verify_holyshit.py
Exit: 0 = all pass, 1 = failures listed.

Covers: verdict extraction (indented/lowercase/fallback/truncation), browser-UA +
Accept + Bearer headers on outbound requests (Cloudflare 403/1010 fix), consensus
partial-failure reporting, single-shot retry pass behavior (recovery, retry-then-fail
honesty, no-retry guard when messages=None).

Pattern: importlib-load the script as a module, monkeypatch urllib.request.urlopen
(capture request headers) and call_model (deterministic results).
"""
import sys, importlib.util, pathlib

SRC = pathlib.Path(__file__).resolve().parent / "holyshit-inject.py"
spec = importlib.util.spec_from_file_location("hsi", SRC)
hsi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hsi)

fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        fails.append(name)

# --- 1. Verdict extraction ---
check("verdict indented", hsi.extract_verdict("  VERDICT: auth bypass confirmed") == "auth bypass confirmed")
check("verdict lowercase", hsi.extract_verdict("verdict: SQLi present") == "SQLi present")
check("verdict fallback first line", hsi.extract_verdict("no marker here\nsecond") == "no marker here")
check("verdict truncation 200", len(hsi.extract_verdict("VERDICT: " + "x" * 500)) == 200)

# --- 2. Headers on outbound request (mock urlopen) ---
captured = {}
class FakeResp:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def read(self): return b'{"choices":[{"message":{"content":"hi"}}],"usage":{}}'
def fake_urlopen(req, timeout=0):
    captured["ua"] = req.headers.get("User-agent") or req.headers.get("User-Agent")
    captured["accept"] = req.headers.get("Accept")
    captured["auth"] = req.headers.get("Authorization")
    return FakeResp()
_orig_urlopen = hsi.urllib.request.urlopen
hsi.urllib.request.urlopen = fake_urlopen
r = hsi.call_model("http://x/v1", "k123", "m1", [{"role": "user", "content": "t"}])
hsi.urllib.request.urlopen = _orig_urlopen
check("UA header set (CF 403 fix)", "Mozilla/5.0" in (captured.get("ua") or ""), repr(captured.get("ua")))
check("Accept header set", captured.get("accept") == "application/json")
check("auth bearer passthrough", captured.get("auth") == "Bearer k123")
check("call ok + text", r["ok"] and r["text"] == "hi")

# --- 3. Consensus partial-failure reporting ---
results = [{"model": "a", "ok": True, "latency_s": 1, "text": "VERDICT: yes"},
           {"model": "b", "ok": False, "error": "HTTP 429: limit"}]
out = hsi.consensus(results)
check("consensus count 1/2", "1/2" in out)
check("FAILED block visible", "=== FAILED ===" in out and "HTTP 429" in out)

# --- 4. Retry pass ---
# Consensus receives pre-built FAILED results -> the retry pass is the mock's FIRST
# invocation per model. Mock succeeds there = retry recovers.
retry_calls = []
def fake_call(ep, key, model, messages, timeout=180):
    retry_calls.append(model)
    return {"model": model, "ok": True, "latency_s": 1, "text": "VERDICT: recovered"}
hsi.call_model = fake_call
out = hsi.consensus(
    [{"model": "a", "ok": False, "error": "429"}, {"model": "b", "ok": False, "error": "429"}],
    "http://x/v1", "k", [{"role": "user", "content": "x"}])
check("retry fired per model", sorted(retry_calls) == ["a", "b"], str(retry_calls))
check("retry recovers", "recovered" in out, out[:100])
check("retry count 2/2", "2/2" in out)

def always_fail(ep, key, model, messages, timeout=180):
    return {"model": model, "ok": False, "error": "429", "latency_s": 0}
hsi.call_model = always_fail
out = hsi.consensus([{"model": "a", "ok": False, "error": "429"}],
                    "http://x/v1", "k", [{"role": "user", "content": "x"}])
check("retry-then-fail reports honestly", "CONSENSUS FAILED" in out and "429" in out)

# --- 5. messages=None -> no retry, no crash ---
def must_not_fire(*a, **k):
    raise AssertionError("retry must not fire when messages is None")
hsi.call_model = must_not_fire
out = hsi.consensus([{"model": "a", "ok": False, "error": "429"}])
check("no-retry path safe", "CONSENSUS FAILED" in out)

print()
print("ALL PASS" if not fails else f"FAILURES: {fails}")
sys.exit(1 if fails else 0)
