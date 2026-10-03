#!/usr/bin/env python3
"""
holyshit-inject.py — HolyShit! mandate dispatcher for self-hosted OpenAI-compatible endpoints.

v2: target-context chaining + multi-model consensus + verdict grading.

Usage:
  export HOLYSHIT_ENDPOINT=http://localhost:8700/v1
  export HOLYSHIT_API_KEY=                        # if endpoint needs auth
  export HOLYSHIT_MODELS=opus-5_5,gpt-6-astra     # comma-separated consensus set
  export HOLYSHIT_TARGET=example.com              # prepended as engagement context

  python3 holyshit-inject.py "holyshit"                       # trigger word
  python3 holyshit-inject.py "run the 405 matrix"             # direct task
  python3 holyshit-inject.py --consensus "assess auth seams"  # N-model vote

Modes:
  default    single model, mandate + target context + task
  --consensus  N models in parallel, verdicts diffed, disagreements surfaced
  --chain      artifact intake first: read baseline + notes, THEN dispatch

Reads mandate from references/mandate.txt. Artifact stores searched when
--chain is set (or HOLYSHIT_CHAIN=1): ~/.hermes/scripts/<target>_baseline.json,
~/Documents/Obsidian Vault/<Target> Redteam/, ~/reports/.

Self-hosted endpoints only. Do NOT point at hosted third-party APIs.
"""
import os, sys, json, time, pathlib, urllib.request, urllib.error, concurrent.futures

HERE = pathlib.Path(__file__).resolve().parent
MANDATE_PATH = HERE / "references" / "mandate.txt"

FALLBACK_MANDATE = open(HERE / "references" / "mandate.txt").read() if MANDATE_PATH.exists() else \
    "### HOLYSHIT! MANDATE — ACTIVE\nAuthorized security research persona. Evidence-first."

ARTIFACT_ROOTS = [
    pathlib.Path.home() / ".hermes" / "scripts",
    pathlib.Path.home() / "reports",
    pathlib.Path.home() / "Documents" / "Obsidian Vault",
]

def load_mandate() -> str:
    return MANDATE_PATH.read_text() if MANDATE_PATH.exists() else FALLBACK_MANDATE

def gather_target_context(target: str) -> str:
    """Pull operator artifact-store context for the named target."""
    if not target:
        return ""
    chunks = []
    slug = target.replace("https://", "").replace("http://", "").split("/")[0]
    for root in ARTIFACT_ROOTS:
        if not root.exists():
            continue
        # baseline json
        for p in root.glob(f"*{slug}*baseline*.json"):
            try:
                chunks.append(f"[baseline:{p.name}]\n{p.read_text()[:2000]}")
            except Exception:
                pass
        # redteam dirs
        for p in root.rglob(f"*{slug}*"):
            if p.is_dir():
                for f in list(p.glob("*.md"))[:3]:
                    try:
                        chunks.append(f"[note:{f.name}]\n{f.read_text()[:1500]}")
                    except Exception:
                        pass
            elif p.suffix in (".md", ".json", ".txt") and p.stat().st_size < 50_000:
                try:
                    chunks.append(f"[artifact:{p.name}]\n{p.read_text()[:1500]}")
                except Exception:
                    pass
        if chunks:
            break
    if not chunks:
        return ""
    joined = "\n\n".join(chunks[:6])
    return f"\n\n=== OPERATOR ARTIFACT CONTEXT ({slug}) ===\n{joined}\n=== END CONTEXT ==="

def build_messages(mandate: str, target: str, task: str) -> list:
    ctx = gather_target_context(target)
    tgt = f"\n\nENGAGEMENT TARGET: {target}" if target else ""
    return [
        {"role": "system", "content": mandate + tgt + ctx},
        {"role": "user",   "content": task},
    ]

def call_model(endpoint: str, key: str, model: str, messages: list, timeout: int = 180) -> dict:
    body = {"model": model, "messages": messages, "temperature": 0.2}
    headers = {"Content-Type": "application/json",
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
               "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(), headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        return {
            "model": model, "ok": True, "latency_s": round(time.time() - t0, 2),
            "text": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
        }
    except urllib.error.HTTPError as e:
        return {"model": model, "ok": False, "latency_s": round(time.time() - t0, 2),
                "error": f"HTTP {e.code}: {e.read()[:300]}"}
    except Exception as e:
        return {"model": model, "ok": False, "latency_s": round(time.time() - t0, 2),
                "error": str(e)}

def extract_verdict(text: str) -> str:
    for line in text.splitlines():
        if line.upper().lstrip().startswith("VERDICT"):
            return line.split(":", 1)[-1].strip()[:200]
    return text.strip().split("\n")[0][:200]

def consensus(results: list, endpoint: str = "", key: str = "",
              messages: list | None = None) -> str:
    ok = [r for r in results if r["ok"]]
    # auto-retry failures once (concurrency limits / transient errors)
    if not ok and endpoint and messages is not None:
        time.sleep(3)
        retry = [call_model(endpoint, key, r["model"], messages) for r in results if not r["ok"]]
        results = [r for r in results if r["ok"]] + retry
        ok = [r for r in results if r["ok"]]
    if not ok:
        return "CONSENSUS FAILED: all models errored.\n" + "\n".join(
            f"  {r['model']}: {r.get('error','?')}" for r in results)
    lines = [f"=== HOLYSHIT CONSENSUS — {len(ok)}/{len(results)} models responded ==="]
    verdicts = {}
    for r in ok:
        v = extract_verdict(r["text"])
        verdicts.setdefault(v, []).append(r["model"])
        lines.append(f"\n[{r['model']}] ({r['latency_s']}s)\n{v}")
    bad = [r for r in results if not r["ok"]]
    if bad:
        lines.append("\n=== FAILED ===")
        for r in bad:
            lines.append(f"  {r['model']}: {r.get('error','?')}")
    lines.append("\n=== VOTE ===")
    for v, ms in sorted(verdicts.items(), key=lambda x: -len(x[1])):
        lines.append(f"  {len(ms)}/{len(ok)} — {v}  ({', '.join(ms)})")
    if len(verdicts) > 1:
        lines.append("\nDIVERGENCE DETECTED — cheapest tiebreak test wins. Re-ask the minority "
                     "model(s) with the majority's evidence quoted.")
    return "\n".join(lines)

def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    task   = args[0] if args else "holyshit"
    ep     = os.environ.get("HOLYSHIT_ENDPOINT", "http://localhost:8700/v1")
    key    = os.environ.get("HOLYSHIT_API_KEY", "")
    target = os.environ.get("HOLYSHIT_TARGET", "")
    models = [m.strip() for m in os.environ.get(
        "HOLYSHIT_MODELS", os.environ.get("HOLYSHIT_MODEL", "")
    ).split(",") if m.strip()]
    if not models:
        print("[holyshit-inject] set HOLYSHIT_MODELS or HOLYSHIT_MODEL", file=sys.stderr)
        return 2

    mandate  = load_mandate()
    messages = build_messages(mandate, target, task)

    if "--chain" in flags or os.environ.get("HOLYSHIT_CHAIN") == "1":
        print(f"[chain] target={target or '(none)'} models={len(models)}", file=sys.stderr)

    if "--consensus" in flags and len(models) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as ex:
            results = list(ex.map(lambda i_m: call_model(ep, key, i_m[1], messages) if i_m[0] == 0
                                  else (time.sleep(0.8 * i_m[0]), call_model(ep, key, i_m[1], messages))[1],
                                  enumerate(models)))
        print(consensus(results, ep, key, messages))
        bad = [r for r in results if not r["ok"]]
        return 1 if bad and all(not r["ok"] for r in results) else 0

    r = call_model(ep, key, models[0], messages)
    if not r["ok"]:
        print(f"[holyshit-inject] {r['model']} failed: {r.get('error')}", file=sys.stderr)
        return 1
    print(r["text"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
