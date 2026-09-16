# PhenoCompose delegated evaluation dogfood

This lane exercises PhenoCompose's persisted `run-action` boundary with
NanoVMS as the bounded host-action execution plane and Podman as the resolved
provider. It does not add a second scheduler and does not use a raw runtime,
GPU-discovery, WSL, or process-launch recovery path.

The manifest is `config/phenocompose_dogfood_v0.yaml`. Its single action runs
Portage on the host through `nvms action --request -`. The executable is the
provider-resolved `portage` command; no workstation executable root or Podman
pipe is committed. The argument vector reproduces the successful
`headless-terminal` invocation, including:

- model `openai/local/qwen35-08b`;
- one concurrent trial and exactly one `headless-terminal` task;
- quote-free `base64json:` values for `model_info` and `llm_call_kwargs`;
- the RTX 3090 Ti UUID
  `GPU-8d337a84-43de-158d-7526-7175288a6064` with CUDA 13.0 and its derived CDI
  binding;
- the action-level, host-workspace-relative `output_root: jobs/harbor`, matching
  `config/harbor.yaml`.

The `--env docker` value is only Portage's historical environment-schema
token. The effective engine and resolved provider must both be `podman`.

## Delegated boundary

The allowed sequence is:

```text
pheno-compose plan <manifest>
pheno-compose apply <manifest> --dry-run
pheno-compose run-action <persisted-run> harbor-headless-terminal --job-id <id>
pheno-compose export-provenance <persisted-run>
pheno-compose down <persisted-run>
```

The automated fake test materializes an empty-container persisted-run fixture
from the deterministic plan and dry-run result. This tests the action boundary
without starting or stopping a runtime service. `run-action` may launch only
the configured `NVMS_BIN`; NanoVMS owns provider inspection, pipe resolution,
GPU reservation, bounded host execution, and cleanup.

PhenoCompose resolves the action output root against the host workspace before
delegation. Harbor output therefore resolves to `<workspace>/jobs/harbor`;
PhenoCompose run and job provenance remains separately under the configured
`.phenocompose` state directory.

The harness helper allow-list contains only the five operations above. It has
no raw fallback. In particular, it does not invoke a container CLI, WSL,
GPU-discovery utility, or Portage directly.

## Prerequisites

- PhenoCompose commit `533fd62b649b233c110e130a2969d71a1e2e462d`
  or a descendant containing typed `run-action`, persisted jobs, and the
  action-level output-root contract.
- NanoVMS commits `a61ca46` and `745d6c2` or descendants containing
  `nvms action --request -` and self-contained provider provenance.
- Python test dependencies from `requirements.txt`.
- For live mode only: validated explicit `PHENOCOMPOSE_BIN` and `NVMS_BIN`
  files, Portage on the provider-resolved host path, the benchmark dataset,
  the local OpenAI-compatible endpoint, and the declared GPU/toolkit/CDI
  binding.

No local executable root and no provider pipe belongs in the manifest.

## Fake test

Point at a validated PhenoCompose artifact and run:

```powershell
$env:PHENO_COMPOSE_BIN = "C:\tools\pheno-compose.exe"
python -m pytest tests\test_phenocompose_dogfood.py -q
```

The test creates an `NVMS_BIN` fixture that accepts exactly
`action --request -`, validates the request through PhenoCompose, emits the
NanoVMS JSON result contract, and exercises both success and failure
persistence. It also proves that the request receives the exact resolved
`<workspace>/jobs/harbor` path, that provenance remains in state storage, and
that traversal or ambiguous Windows roots fail before NanoVMS is invoked. It
performs no live provider operation.

## Opt-in live test

Live mode is skipped by default and requires both binaries explicitly:

```powershell
$env:PHENO_DOGFOOD_LIVE = "1"
$env:PHENOCOMPOSE_BIN = "C:\validated\pheno-compose.exe"
$env:NVMS_BIN = "C:\validated\nvms.exe"
python -m pytest tests\test_phenocompose_dogfood.py -q -k live
```

The live test fails closed if the job is absent, unsuccessful, ambiguous, or
missing exact route, digest, GPU binding, lifecycle, hash, or cleanup evidence.
It does not attempt recovery through a raw control path.

## Provenance contract

Every persisted job must contain:

- the normalized manifest SHA-256;
- `effective_engine: podman`, `resolved_provider: podman`, and
  `execution_plane: nanovms`;
- the exact UUID, CUDA 13.0, and CDI binding;
- bounded duration, output, timeout/truncation flags, exit code, and matching
  output hashes;
- an explicit success value and a machine-readable failure code on failure.

`export-provenance` must reproduce both successful and failed job records.
Missing or conflicting evidence is a test failure, never an invitation to
probe or repair through direct commands.

## Rollback

For the fixture lane, `down` transitions only the empty persisted fixture to
`down`; it has no service IDs to stop. Live action cleanup remains NanoVMS's
bounded reservation-release responsibility. If an action fails, retain the
persisted job evidence and stop. Do not perform raw runtime recovery from this
lane.

## Current status

The fake delegated boundary is the acceptance target. No live Podman success
is claimed. PhenoCompose now delegates the manifest action's
host-workspace-relative `jobs/harbor` output root, so the prior output-path
contract blocker is resolved. The opt-in live lane remains skipped by default
until its explicit hardware and provider prerequisites are supplied.
