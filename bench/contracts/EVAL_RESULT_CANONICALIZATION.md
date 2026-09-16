# JSON Canonicalization Rules for EvaluationReport v0.1

> Author: feynman (Chat 3)
> Status: v0.1 ratified — matches EVAL_RESULT_CONTRACT.md
> Purpose: define exactly how producer and consumer compute `schema_hash` and
> `top_level_sha256` so both sides agree byte-for-byte.

## Canonicalization

Both `schema_hash` and `top_level_sha256` use the same procedure:

1. Start with the JSON document (the schema body for `schema_hash`; the artifact
   body minus the `hash_chain` field for `top_level_sha256`).
2. Parse with `json.loads`. Reject any duplicate keys (Python's `json` raises).
3. Recursively sort dict keys lexicographically (UTF-8 codepoint order). Lists preserve
   order — they are NOT sorted. The exception is `task_results`, which the producer
   MUST sort by `task_id` lex before canonicalization (acceptance case P5).
4. Serialize with `json.dumps(d, sort_keys=False, separators=(",", ":"), ensure_ascii=False)`.
   The previous step already sorted keys, so `sort_keys=False` is correct here.
5. Encode to UTF-8 bytes (no BOM).
6. SHA-256 those bytes. Output as lowercase hex, 64 chars, no `0x` prefix.

## Why this set of rules

- **Sorted keys**: gives a deterministic byte sequence regardless of producer
  implementation language or dict ordering.
- **Compact separators**: removes whitespace noise.
- **UTF-8 (not ensure_ascii=True)**: preserves non-ASCII identifiers and prompts verbatim.
- **Lists preserve order**: task_results order is meaningful and is fixed by P5; other
  lists are not arbitrary permutations, so reordering them would change semantics.
- **No re-serialization of floats**: `pass_at_1` must already be rounded to 4 decimal
  places by the producer (acceptance case P7). The canonicalizer does NOT round.

## Hash boundaries

```
schema_hash            = sha256(canonicalize(SCHEMA_BODY))
top_level_sha256       = sha256(canonicalize(ARTIFACT_MINUS_HASH_CHAIN))
task_ids_sorted_sha256 = sha256("\n".join(sorted(task_ids)).encode("utf-8"))
```

The schema body is the literal JSON object in the frozen block below. The producer
MUST copy it verbatim; the consumer MUST refuse an artifact whose embedded schema
hashes to a different value.

## Frozen schema body

This is the canonical v0.1 schema. Producer and consumer both hash this exact text.

SCHEMA_HASH = 533dd0fa0d9b36145ef2e23a5c32aed39a67bc09bd36822b58289b61d5640a2e

```json
{"$id":"https://pheno-omlx/contracts/EvaluationReport/v0.1","title":"EvaluationReport","type":"object","required":["contract_version","artifact_kind","schema_hash","producer","run","matrix","suites","totals","hash_chain"],"properties":{"contract_version":{"type":"string","pattern":"^0\\.[0-9]+$"},"artifact_kind":{"const":"EvaluationReport"},"schema_hash":{"type":"string","pattern":"^[a-f0-9]{64}$"},"producer":{"type":"object","required":["repo","head","branch","dirty_paths"],"properties":{"repo":{"const":"pheno-harness"},"head":{"type":"string","minLength":7},"branch":{"type":"string"},"dirty_paths":{"type":"array","items":{"type":"string"}},"host":{"type":"object","properties":{"os":{"type":"string"},"chip":{"type":"string"},"mlx_server_url":{"type":"string"}},"additionalProperties":true}},"additionalProperties":true},"run":{"type":"object","required":["run_id","started_at","stopped_at","variant","model","judge_mode","energy_source","executed_by","command","evidence_label"],"properties":{"run_id":{"type":"string","format":"uuid"},"started_at":{"type":"string","format":"date-time"},"stopped_at":{"type":"string","format":"date-time"},"variant":{"enum":["stock","ours"]},"model":{"type":"string"},"model_revision":{"type":["string","null"]},"judge_mode":{"enum":["deterministic","llm"]},"energy_source":{"enum":["none","m1_pmu","nvidia_smi"]},"executed_by":{"type":"string"},"command":{"type":"string"},"evidence_label":{"enum":["live verified","historical","reported","inferred","unknown"]}},"additionalProperties":false},"matrix":{"type":"object","required":["suites","tasks_per_suite","variants","total_cells"],"properties":{"suites":{"type":"array","minItems":1,"items":{"enum":["mmlu-pro","gpqa-diamond","aime","arc-agi-2","livecodebench","aider-polyglot","swe-bench","swe-bench-pro","bfcl","terminal-bench"]}},"tasks_per_suite":{"type":"integer","minimum":1},"variants":{"type":"array","items":{"enum":["stock","ours"]}},"total_cells":{"type":"integer","minimum":1}}},"suites":{"type":"array","items":{"type":"object","required":["suite","n","passed","wrong","errored","pass_at_1","wall_clock_s","tokens_in","tokens_out","evidence_label","provenance","task_results"],"properties":{"suite":{"enum":["mmlu-pro","gpqa-diamond","aime","arc-agi-2","livecodebench","aider-polyglot","swe-bench","swe-bench-pro","bfcl","terminal-bench"]},"n":{"type":"integer","minimum":1},"passed":{"type":"integer","minimum":0},"wrong":{"type":"integer","minimum":0},"errored":{"type":"integer","minimum":0},"partial_credit_mean":{"type":["number","null"],"minimum":0,"maximum":1},"pass_at_1":{"type":"number","minimum":0,"maximum":1},"wall_clock_s":{"type":"number","minimum":0},"tokens_in":{"type":"integer","minimum":0},"tokens_out":{"type":"integer","minimum":0},"evidence_label":{"enum":["live verified","historical","reported","inferred","unknown"]},"provenance":{"type":"object","required":["synthetic","substitute"],"properties":{"dataset_revision":{"type":["string","null"]},"synthetic":{"type":"boolean"},"substitute":{"type":["string","null"],"enum":[null,"qwen2.5-substitute","cached-only","syntax-only","synthetic"]}},"additionalProperties":false},"task_results":{"type":"array","minItems":1,"items":{"type":"object","required":["task_id","status","wall_clock_s","tokens_in","tokens_out","judge","evidence_label"],"properties":{"task_id":{"type":"string","minLength":1},"status":{"enum":["ok","wrong","error","skipped"]},"prompt_hash":{"type":"string","pattern":"^[a-f0-9]{64}$"},"completion_hash":{"type":"string","pattern":"^[a-f0-9]{64}$"},"expected_hash":{"type":"string","pattern":"^[a-f0-9]{64}$"},"wall_clock_s":{"type":"number","minimum":0},"tokens_in":{"type":"integer","minimum":0},"tokens_out":{"type":"integer","minimum":0},"first_token_latency_s":{"type":["number","null"],"minimum":0},"judge":{"enum":["ok","wrong","error","skipped","regex"]},"tool_calls":{"type":"array","items":{"type":"object"}},"cached":{"type":"boolean"},"error":{"type":["string","null"]},"raw_score":{"type":"number","minimum":0,"maximum":1},"evidence_label":{"enum":["live verified","historical","reported","inferred","unknown"]}},"additionalProperties":false}}},"additionalProperties":false}},"totals":{"type":"object","required":["cells","passed","wrong","errored","pass_at_1","wall_clock_s","tokens_in","tokens_out","evidence_label"],"properties":{"cells":{"type":"integer","minimum":1},"passed":{"type":"integer","minimum":0},"wrong":{"type":"integer","minimum":0},"errored":{"type":"integer","minimum":0},"pass_at_1":{"type":"number","minimum":0,"maximum":1},"wall_clock_s":{"type":"number","minimum":0},"tokens_in":{"type":"integer","minimum":0},"tokens_out":{"type":"integer","minimum":0},"energy_total":{"type":["number","null"],"minimum":0},"evidence_label":{"enum":["live verified","historical","reported","inferred","unknown"]}}},"comparator":{"type":"object","required":["delta_pass_at_1","winner"],"properties":{"delta_pass_at_1":{"type":"number"},"winner":{"enum":["stock","ours","tie"]},"p_value":{"type":["number","null"],"minimum":0,"maximum":1}},"additionalProperties":false},"hash_chain":{"type":"object","required":["top_level_sha256","task_ids_sorted_sha256"],"properties":{"top_level_sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"},"task_ids_sorted_sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"}},"additionalProperties":false}},"additionalProperties":false}
```

## Reference canonicalizer (Python, 30 lines, illustrative only)

This is reference pseudocode Chat 6 may translate to any language. It is **not**
shipped as production code — the contract document is normative.

```python
import hashlib, json

def canonicalize(obj):
    return json.dumps(
        _sort(obj),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

def _sort(obj):
    if isinstance(obj, dict):
        return {k: _sort(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        # Lists preserve order; producer is responsible for pre-sorting task_results.
        return [_sort(x) for x in obj]
    return obj

def sha256_hex(obj):
    return hashlib.sha256(canonicalize(obj)).hexdigest()
```

## Reference producer flow (pseudocode)

```python
import uuid, hashlib, datetime as dt

def emit_artifact(suite_results_by_suite, head, branch, dirty_paths, variant, model,
                  model_revision, command, executed_by, judge_mode, energy_source,
                  host_info, run_id, started_at, stopped_at, comparator=None):
    artifact = {
        "contract_version": "0.1",
        "artifact_kind": "EvaluationReport",
        "schema_hash": SCHEMA_HASH,        # computed once from canonicalize(FROZEN_SCHEMA_BODY)
        "producer": {
            "repo": "pheno-harness",
            "head": head,
            "branch": branch,
            "dirty_paths": dirty_paths,
            "host": host_info,
        },
        "run": {
            "run_id": run_id,
            "started_at": started_at,
            "stopped_at": stopped_at,
            "variant": variant,
            "model": model,
            "model_revision": model_revision,
            "judge_mode": judge_mode,
            "energy_source": energy_source,
            "executed_by": executed_by,
            "command": command,
            "evidence_label": "live verified",
        },
        "matrix": suites_to_matrix(suite_results_by_suite),
        "suites": [s.to_contract_dict() for s in suite_results_by_suite.values()],
        "totals": totals_from_suites(suite_results_by_suite),
        "comparator": comparator,
        "hash_chain": {},
    }
    # task_results sorted by task_id within each suite (P5)
    for s in artifact["suites"]:
        s["task_results"].sort(key=lambda t: t["task_id"])

    # fill hash_chain last so it can hash everything else
    body_minus_hash_chain = {k: v for k, v in artifact.items() if k != "hash_chain"}
    all_ids = sorted(t["task_id"] for s in artifact["suites"] for t in s["task_results"])
    artifact["hash_chain"] = {
        "top_level_sha256": sha256_hex(body_minus_hash_chain),
        "task_ids_sorted_sha256": hashlib.sha256("\n".join(all_ids).encode("utf-8")).hexdigest(),
    }
    return artifact
```

## Reference consumer flow (pseudocode)

```python
def accept(artifact):
    assert artifact["contract_version"] == "0.1"                            # C1
    assert artifact["schema_hash"] == SCHEMA_HASH                            # C2
    body = {k: v for k, v in artifact.items() if k != "hash_chain"}
    assert sha256_hex(body) == artifact["hash_chain"]["top_level_sha256"]    # C3
    for suite in artifact["suites"]:
        ids = [t["task_id"] for t in suite["task_results"]]
        assert len(set(ids)) == len(ids)                                    # C4 uniqueness
        assert round(suite["passed"] / suite["n"], 4) == suite["pass_at_1"] # C5
    if artifact["run"]["evidence_label"] != "live verified":                  # C6
        return record_only(artifact)
    if artifact["run"]["variant"] not in ("stock", "ours"):                   # C7
        return reject(artifact)
    if artifact["suites"][0]["provenance"]["synthetic"]:                     # C8
        return record_only(artifact)
    if artifact["suites"][0]["provenance"]["substitute"] is not None:        # C9
        return record_only(artifact)
    return advance_promotion(artifact)
```

## Drift detection

If a future producer wants to add a field to the contract, it MUST:

1. Bump `contract_version` to `0.2` (or higher).
2. Append the new field to the frozen schema body, recompute `SCHEMA_HASH`, and
   re-publish `bench/contracts/EVAL_RESULT_CONTRACT.md` and this canonicalization file.
3. Wait for Chat 6 and Argis to re-acknowledge before any v0.2 artifact is emitted.
4. Never silently add fields under `additionalProperties: true` without bumping version.

The `producer.*` object is the only one with `additionalProperties: true` in v0.1,
to allow host-level metadata without bumping the contract for every hardware change.
All other objects are closed.
