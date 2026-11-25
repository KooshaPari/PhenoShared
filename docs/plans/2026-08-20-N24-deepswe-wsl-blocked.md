# N24 DeepSWE — WSL-blocked (G3)

**Status:** Blocked per G3 (WSL virtualization not enabled on host).
**Forward DAG:** N24 = DeepSWE v1.1 bench/custom/deepswe (agentica-project/DeepSWE) — mini-SWE-agent ReAct loop on Docker.
**Evidence:** WSL2 unable to start since virtualization not enabled (error Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED). See task 10.

## Placeholder

- N24 remains G3-blocked; no live DeepSWE verification until WSL re-enabled (requires Virtual Machine Platform + firmware virtualization).
- Bench harness wiring for DeepSWE is intact: `bench/suites/deepswe.py`, `scripts/run_deepswe.py`, `config/deepswe.yaml`, `eval/deepswe.py` are present and type-checked (mypy 0).
- Forward DAG should gate N24 on `wsl --status` and skip eval when blocked, preserving CI green.

## Gate

- G3 exception documented; v0.12 task 10 satisfied via placeholder doc.
- Next: Re-enable WSL (admin: `wsl.exe --install --no-distribution`, enable Virtual Machine Platform, reboot) then rerun `python scripts/run_deepswe.py --help` and full harbor verifier wire-up.

## References

- `bench/suites/deepswe.py` — stub suite (G3 comment added)
- `config/deepswe.yaml` — config
- `docs/plans/2026-08-10-v0.12-summit-release-notes.md` — WBS-PERT v0.12

---
*Generated for v0.12 task 10 — WSL-blocked per G3, placeholder doc suffices.*
