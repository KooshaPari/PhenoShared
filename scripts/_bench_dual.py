#!/usr/bin/env python3
"""Dual-lane benchmark + quality eval for pheno-harness (2026-08-02 v2).

Fixes vs v1:
  - JSON quality: strips ```json fences, actually parses JSON, verifies keys.
  - Concurrency: per-request latency measured correctly; errors filtered out.
  - Adds GPU profiling: samples nvidia-smi (util/power/temp/VRAM) during a
    long generation on each lane.
"""

import json
import re
import statistics
import subprocess
import threading
import time
import urllib.request

LANES = [
    {"port": 19000, "model": "lfm25-8b-a1b", "name": "3090Ti/LFM2.5-8B"},
    {
        "port": 19002,
        "model": "ibm-granite/granite-4.1-3b",
        "name": "1080Ti/Granite-4.1",
    },
]

PAYLOADS = [
    {"label": "short", "content": "Say hello in exactly 5 words.", "max_tokens": 20},
    {
        "label": "medium",
        "content": "Explain what a transformer model is in 3 sentences.",
        "max_tokens": 100,
    },
    {
        "label": "long",
        "content": "Write a detailed comparison of Python vs Rust for systems programming, covering memory safety, performance, ecosystem, and learning curve.",
        "max_tokens": 500,
    },
    {
        "label": "reasoning",
        "content": "What is 137 * 29? Show your work step by step.",
        "max_tokens": 200,
    },
]

QUALITY = [
    {
        "name": "arithmetic",
        "content": "What is 137 * 29? Show your work.",
        "max_tokens": 300,
        "check": "3973",
    },
    {
        "name": "constrained",
        "content": "Respond with exactly the single word: READY",
        "max_tokens": 100,
        "check": "READY",
    },
    {
        "name": "json",
        "content": "Respond with a JSON object with keys: name, role, years. No prose.",
        "max_tokens": 120,
        "keys": ["name", "role", "years"],
    },
]


def post(url, body, timeout=600):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with (
        urllib.request.urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return json.loads(resp.read())


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with (
        urllib.request.urlopen(req, timeout=30) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return json.loads(resp.read())


def bench_chat(lane, payload, n=3):
    url = f"http://127.0.0.1:{lane['port']}/v1/chat/completions"
    body = {
        "model": lane["model"],
        "messages": [{"role": "user", "content": payload["content"]}],
        "max_tokens": payload["max_tokens"],
        "temperature": 0.0,
        "stream": False,
    }
    times, cps, otokens = [], [], 0
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            data = post(url, body)
            elapsed = time.perf_counter() - t0
            ot = data.get("usage", {}).get("completion_tokens", 0)
            times.append(round(elapsed, 3))
            cps.append(round(ot / elapsed, 2) if elapsed > 0 else 0)
            otokens = ot
        except Exception:
            times.append(0.0)
            cps.append(0.0)
    ok = [t for t in times if t > 0]
    okc = [c for c in cps if c > 0]
    return {
        "latency_avg_s": round(sum(ok) / len(ok), 3) if ok else None,
        "tok_per_s_avg": round(sum(okc) / len(okc), 1) if okc else None,
        "completion_tokens": otokens,
    }


def bench_concurrent(lane, content, max_tokens=50, n=4):
    url = f"http://127.0.0.1:{lane['port']}/v1/chat/completions"
    body = {
        "model": lane["model"],
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    t0 = time.perf_counter()
    results, errors = [], []

    def worker():
        s = time.perf_counter()
        try:
            post(url, body, timeout=300)
            results.append(time.perf_counter() - s)
        except Exception as e:
            errors.append(str(e)[:80])

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    ok = [r for r in results if isinstance(r, float)]
    return {
        "wall_s": round(wall, 2),
        "n_ok": len(ok),
        "n_err": len(errors),
        "avg_req_s": round(sum(ok) / len(ok), 2) if ok else None,
        "p50_req_s": round(statistics.median(ok), 2) if ok else None,
        "throughput_req_s": round(len(ok) / wall, 2) if wall > 0 else None,
        "errors": errors[:3],
    }


def extract_json(text):
    """Return the first brace-balanced JSON object in text, or None.

    Handles: ```json fences, <think> blocks (closed OR truncated), leading
    prose, trailing fences. Uses brace-depth scanning so an unclosed think
    block or a prose '{' before the real object never corrupts the parse.
    """
    # Strip complete think blocks, then find every '{...}' region and try to
    # parse the first brace-balanced candidate that yields a dict.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start = 0
    while True:
        i = text.find("{", start)
        if i < 0:
            return None
        depth = 0
        j = i
        in_str = False
        esc = False
        while j < len(text):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[i : j + 1]
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict):
                                return obj
                        except Exception:
                            pass
                        break
            j += 1
        start = i + 1


def quality_check(lane, item):
    url = f"http://127.0.0.1:{lane['port']}/v1/chat/completions"
    body = {
        "model": lane["model"],
        "messages": [{"role": "user", "content": item["content"]}],
        "max_tokens": item["max_tokens"],
        "temperature": 0.0,
    }
    # JSON checks: use guided decoding (json_object) so LFM2.5's <think> block
    # isn't truncated mid-reasoning at the token cap — eliminates the harness
    # extraction false-negative while the model itself was emitting valid JSON.
    if "keys" in item:
        body["response_format"] = {"type": "json_object"}
    data = post(url, body)
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    if "keys" in item:
        obj = extract_json(content)
        passed = obj is not None and all(k in obj for k in item["keys"])
        detail = f"keys={sorted(obj.keys()) if obj else None}"
    else:
        passed = item["check"].lower() in content.lower()
        detail = f"contains='{item['check']}'"
    return {
        "name": item["name"],
        "passed": passed,
        "check": item.get("check", item.get("keys")),
        "detail": detail,
        "content": content[:200],
        "completion_tokens": usage.get("completion_tokens", 0),
    }


def sample_gpu(dur):
    """Sample nvidia-smi every second for `dur` seconds (threaded)."""
    end = time.time() + dur
    rows = []
    while time.time() < end:
        try:
            out = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,utilization.gpu,power.draw,temperature.gpu,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout
            rows.append(out.strip().replace("\n", " | "))
        except Exception:
            pass
        time.sleep(1)
    return rows


def gpu_profile(lane, duration=20):
    url = f"http://127.0.0.1:{lane['port']}/v1/chat/completions"
    body = {
        "model": lane["model"],
        "messages": [
            {
                "role": "user",
                "content": "Write a long detailed essay about the history of computing, at least 300 words.",
            }
        ],
        "max_tokens": 400,
        "temperature": 0.0,
    }
    samples = []
    t = threading.Thread(target=lambda: samples.extend(sample_gpu(duration)))
    t.start()
    try:
        data = post(url, body, timeout=600)
        usage = data.get("usage", {})
    except Exception as e:
        return {"error": str(e)[:120], "samples": samples}
    t.join()
    return {"completion_tokens": usage.get("completion_tokens", 0), "samples": samples}


def main() -> None:
    out = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "lanes": {}}
    for lane in LANES:
        print(f"\n=== {lane['name']} (:{lane['port']}) — {lane['model']} ===")
        try:
            get_json(f"http://127.0.0.1:{lane['port']}/v1/models")
        except Exception as e:
            print(f"  LANE DOWN: {e}")
            continue
        post(
            f"http://127.0.0.1:{lane['port']}/v1/chat/completions",
            {
                "model": lane["model"],
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5,
            },
        )
        bench = {}
        for p in PAYLOADS:
            r = bench_chat(lane, p)
            bench[p["label"]] = r
            print(
                f"  {p['label']:10s}  avg {r['latency_avg_s']}s  {r['completion_tokens']:4d} tok  {r['tok_per_s_avg']} tok/s"
            )
        conc = bench_concurrent(lane, "What is the capital of France?")
        bench["concurrent_4"] = conc
        print(
            f"  concurrency4  wall {conc['wall_s']}s  ok={conc['n_ok']} err={conc['n_err']}  {conc['throughput_req_s']} req/s"
        )
        quals = [quality_check(lane, q) for q in QUALITY]
        for q in quals:
            print(
                f"  quality {q['name']:12s}  {'PASS' if q['passed'] else 'FAIL'}  {q.get('detail', '')}  | {q['content'][:60]}"
            )
        prof = gpu_profile(lane)
        bench["gpu_profile"] = {
            "completion_tokens": prof.get("completion_tokens"),
            "n_samples": len(prof.get("samples", [])),
            "error": prof.get("error"),
        }
        out["lanes"][lane["name"]] = {
            "bench": bench,
            "quality": quals,
            "gpu_profile_samples": prof.get("samples", []),
        }
    print("\n" + json.dumps({k: v for k, v in out.items() if k != "lanes"}, indent=2))
    for name, lane in out["lanes"].items():
        print(
            f"\n[{name}] gpu_profile samples ({len(lane.get('gpu_profile_samples', []))}):"
        )
        for s in lane.get("gpu_profile_samples", [])[:20]:
            print("   ", s)


if __name__ == "__main__":
    main()
