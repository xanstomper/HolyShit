#!/usr/bin/env python3
"""
holyconverge.py — HolyShit confirmation loop for the dispatcher.

Turns the mandate's scoring engine into a convergence loop: given a Holy Shit candidate
chain, probe it across multiple models in rounds until either (a) a minimum-proof consensus
confirms it, (b) the chain is blocked, or (c) the round budget is spent. Only chains that
survive become confirmed Holy Shits; everything else stays a labeled HYPOTHESIS.

Use AFTER holyshit-inject.py surfaces candidate chains. This is the "second pass" that
converts diverging hypotheses into a confirmed finding — the compound that moves single-
sweep reliability toward the stated 9/10 goal on chained-vector engagements.

Modes:
  default    single consensus round across models, then convergence
  --budget N max total model calls (default 12); --minproof K models to agree (default 2)

Usage:
  export HOLYSHIT_ENDPOINT=http://<host>:<port>/v1
  export HOLYSHIT_API_KEY=sk-...           # if auth
  export HOLYSHIT_MODELS=m1,m2,m3           # at least 2 required for convergence
  python3 holyconverge.py --budget 15 --minproof 2 \
    "Chain candidate: [SSRF primitive] -> [IMDS 169.254.169.254] -> cloud creds. Prove or block each edge."
"""
import os, sys, json, time, pathlib, urllib.request, urllib.error, concurrent.futures

HERE = pathlib.Path(__file__).resolve().parent
MANDATE_PATH = HERE / "references" / "mandate.txt"

def load_mandate() -> str:
    return MANDATE_PATH.read_text() if MANDATE_PATH.exists() else "### HOLYSHIT! MANDATE — ACTIVE"

def build_system(target: str) -> str:
    mandate = load_mandate()
    if target:
        mandate += f"\n\nENGAGEMENT TARGET: {target}"
    return mandate

def call_model(ep, key, model, messages, timeout=180):
    headers = {"Content-Type": "application/json",
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
               "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {"model": model, "messages": messages, "temperature": 0.1}
    req = urllib.request.Request(ep.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(), headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        return {"model": model, "ok": True, "latency_s": round(time.time()-t0, 2),
                "text": data["choices"][0]["message"]["content"]}
    except urllib.error.HTTPError as e:
        return {"model": model, "ok": False, "latency_s": round(time.time()-t0, 2),
                "error": f"HTTP {e.code}: {e.read()[:200]}"}
    except Exception as e:
        return {"model": model, "ok": False, "latency_s": round(time.time()-t0, 2),
                "error": str(e)}

def verdict_of(text: str) -> str:
    for line in text.splitlines():
        up = line.upper().lstrip()
        for tag in ("CONFIRMED", "BLOCKED", "HYPOTHESIS", "PROVEN", "VERDICT"):
            if up.startswith(tag):
                return tag
    return "INCONCLUSIVE"

def classify(results):
    counts = {}
    for r in results:
        if r["ok"]:
            counts[verdict_of(r["text"])] = counts.get(verdict_of(r["text"]), 0) + 1
        else:
            counts["ERROR"] = counts.get("ERROR", 0) + 1
    return counts

def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    budget  = 12
    minproof = 2
    for a in sys.argv[1:]:
        if a.startswith("--budget "):
            budget = int(a.split()[1])
        if a.startswith("--minproof "):
            minproof = int(a.split()[1])
    task = args[0] if args else "holyshit"
    ep = os.environ.get("HOLYSHIT_ENDPOINT", "")
    key = os.environ.get("HOLYSHIT_API_KEY", "")
    target = os.environ.get("HOLYSHIT_TARGET", "")
    models = [m.strip() for m in os.environ.get("HOLYSHIT_MODELS", "").split(",") if m.strip()]
    if not ep or len(models) < 2:
        print("holyconverge requires HOLYSHIT_ENDPOINT + at least 2 models in HOLYSHIT_MODELS",
              file=sys.stderr)
        return 2

    sys_prompt = build_system(target)
    # prompt: instruct strict confirmation discipline from mandate section 29
    task_enhanced = task + ("\n\nReply with a single leading keyword: CONFIRMED (proof exists, "
        "non-destructive, cite req+resp), BLOCKED (a step is disproven or destructive), or "
        "HYPOTHESIS (gapped — say exactly what's missing). Prefix exactly one keyword.")
    messages = [{"role": "system", "content": sys_prompt},
                {"role": "user", "content": task_enhanced}]

    transcript = []
    spent = 0
    round_no = 1
    while spent < budget:
        n = min(len(models), budget - spent)
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
            results = list(ex.map(
                lambda i_m: call_model(ep, key, i_m[1], messages) if i_m[0] == 0
                else (time.sleep(0.8*i_m[0]), call_model(ep, key, i_m[1], messages))[1],
                enumerate(models[:n])))
        spent += n
        counts = classify(results)
        transcript.append({"round": round_no, "results": results})
        confirmed = counts.get("CONFIRMED", 0) + counts.get("PROVEN", 0)
        blocked = counts.get("BLOCKED", 0)
        echoed = "Transient (got N responses, not spending budget on echo)" if spent >= budget else ""

        print(f"--- round {round_no} (calls used {spent}/{budget}) ---")
        for r in results:
            st = r.get("ok") and verdict_of(r["text"]) or "ERROR"
            print(f"  [{r['model']}] {st} :: {r['text'][:120]}")
        print(f"  aggregate -> confirmed={confirmed} blocked={blocked} {echoed}")

        if confirmed >= minproof:
            print(f"\nCONVERGED: {confirmed} models confirm the chain — marking CONFIRMED Holy Shit.")
            return 0
        if blocked >= max(minproof, len(models) - minproof + 1):
            print(f"\nBLOCKED: {blocked} models block the chain — recording as blocked, "
                  f"not a Holy Shit.")
            return 1
        # inconclusive/hypothesis but budget left -> ask repair question next round
        if spent >= budget:
            break
        # build a sharper prompt from the disagreements for the next round
        gaps = [r["text"] for r in results if r["ok"] and verdict_of(r["text"]) in
                ("HYPOTHESIS", "INCONCLUSIVE")]
        prompt_2 = task + "\n\nA prior round did not fully confirm. Address this reviewer gap only: "
        if gaps:
            prompt_2 += gaps[0][:300]
        else:
            prompt_2 += "Provide the single decisive confirmation or a precise blocker."
        prompt_2 += ("\nReply with one leading keyword: CONFIRMED | BLOCKED | HYPOTHESIS.")
        messages = [{"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt_2}]
        round_no += 1
        time.sleep(1.5)

    print("\nBUDGET EXHAUSTED without hard convergence. Rule per mandate §29: do NOT mark "
          "CONFIRMED. Record as HYPOTHESIS with the exact gap, or raise --budget.")
    return 3

if __name__ == "__main__":
    sys.exit(main())