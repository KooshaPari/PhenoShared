# Testing strategy

## Local checks

```text
python3 scripts/validate_desktop_evidence.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  tests/test_desktop_evidence.py \
  tests/test_desktop_launcher.py \
  tests/test_desktop_nvidia_lane.py
```

Expected current result: validator valid/blocked, 11 focused tests passed,
PowerShell parser pass.

The transport and lane wrapper regression set currently passes 13 tests. The
broader evidence registry set has three pre-existing failures because its
tests patch adapter symbols that are absent from `scripts.evidence_registry`;
those failures are unrelated to the desktop lane changes.

The Harbor provenance regression set also covers the Qwen3.5 normalizer: a
completed trial without a desktop authorization sidecar is non-scoreable, and
a valid sidecar must bind the authorization window, contract SHA-256, model,
and endpoint before the result can be scoreable. The current combined focused
desktop set passes 32 tests; no model or Harbor workload is launched by it.
The Windows Harbor launcher now resolves the newest completed job and invokes
that normalizer with the exact sidecar automatically; a successful Harbor
process without a result or normalization failure is treated as a launcher
failure rather than promotion evidence.

## Live checks when the desktop is available

There is intentionally **no executable live-run command** while the owner-
issued desktop authorization contract is absent. `WindowId` alone is only run
provenance, not permission to launch or evaluate. The launcher and direct
smoke entrypoint therefore fail closed; `-PreflightOnly` is the only current
desktop operation and produces capability evidence only.

After the authorization contract exists, all of the following must be true
before a run command is documented or enabled:

1. The lane policy is reviewed as active and permits inference and benchmarks.
2. A current, canonical-contract-bound no-launch preflight records both GPU
   roles, headroom, runtime port bindings, and artifact identity.
3. The owner-issued authorization binds the window, contract digest,
   preflight digest, endpoint/runtime, issuance, and expiry.
4. The primary and helper evaluation wrappers consume that authority before
   endpoint probing, then emit `pheno.perf.v1` plus result manifests.
5. A read-only process mapping proves helper isolation before any result is
   considered for promotion.

Until those conditions are implemented and independently reviewed, the
readiness report is the canonical source of the two unmet promotion gates;
neither a preflight nor a dry-run is evaluation evidence.
