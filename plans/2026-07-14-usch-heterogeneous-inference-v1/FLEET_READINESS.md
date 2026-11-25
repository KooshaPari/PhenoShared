# Offline fleet-readiness slice

`config/fleet_readiness.yaml`, `pheno/fleet_readiness.py`, and
`scripts/fleet_readiness.py` establish the first executable device gate without
contacting a device. The policy is closed and keeps every mutation, remote
probe, SSH, install, download, server, Mac, phone, and GTX 1080 Ti gate false.

The `pheno.fleet.device-capability.v1` manifest hash-binds the exact device and
OS build, runtime binary, backend capabilities, collector/app build, telemetry
capabilities, measured available-memory headroom, thermal stop state,
lifecycle/cancellation/recovery state, owner handoff, and non-authorization
fields. Remote templates are deterministic but explicitly unmeasured, pending
handoff, and incapable of authorizing a benchmark or mutation.

The content hash proves integrity after capture, not device or owner
authenticity. Until a separately authorized collector binds a bundle to an
authenticated device identity and owner handoff, an observed JSON bundle is
self-reported capability evidence only and cannot authorize execution.

## Telemetry handoff contract

`pheno/evidence/telemetry.py` adds the offline
`pheno.eval.telemetry-bundle.v1` handoff that a later authorized collector must
populate. It hash-binds a capability manifest to the exact run, model,
runtime/config, device/topology, process set, collector/config, and monotonic
clock. The profile-specific requirements are deliberately different:

- RTX 3090 Ti uses a WSL host+guest identity, Linux/NVML process-tree
  attribution, monotonic POSIX time, and required GPU power, energy,
  process-scoped VRAM, process RAM, system headroom, temperature, throttle,
  lifecycle, and GPU utilization series;
- M1 Pro uses native Metal/macOS identity, `mach_continuous_time`, Darwin
  process-tree attribution, and aligns process/unified-memory streams using
  their maximum so shared physical bytes are counted once, never summed;
- Galaxy S21 Ultra and iPhone 17 Pro Max use app/UID attribution, mobile
  monotonic clocks, battery power/energy, process memory, OS memory headroom,
  thermal state, throttle, and foreground lifecycle. Direct temperature is
  required on Android but remains an explicit optional/missing series on iOS,
  where OS thermal state remains required; and
- GTX 1080 Ti is accepted only as a helper-role CUDA record with its own
  process-scoped RAM/VRAM, device-capability, and topology hashes. A telemetry
  pass does not justify or authorize installing it.

Every metric has measured/missing/not-applicable semantics fixed by profile.
The validator recomputes time-grid coverage, power and energy, thermal and
lifecycle excursions, and a three-pair instrumentation-overhead calibration.
The physical-memory peak follows the existing
`time_aligned_peak_attributable_physical_bytes` scope and remains null unless
all profile components align with at least 95% coverage. Missing required
telemetry, unknown state, or unleased whole-device power is `not_evaluable`;
throttling, prohibited thermal/lifecycle transitions, or more than 5%
collection overhead fails telemetry quality.

This is still an offline data contract. It contains no NVML, WSL, SSH, Metal,
Android, iOS, process, subprocess, network, model-loader, or server call. A
bundle is self-reported until an authorized collector and owner-handoff flow
provide external authenticity; its content hash alone grants no authority.

The optional-GPU simulation is also offline. Its input supplies intervals for
baseline AVS, primary power, helper candidate rate, coordination rate, helper
and IPC latency, acceptance, and helper power, plus explicit PSU, slot,
connector, case, and thermal gates. The conservative result uses the worst
blocked-time, goodput, and power endpoints. It returns `not_justified` unless
both the lower-bound net AVS gain and lower-bound energy-efficiency gain are
positive and every physical gate passes. Even a positive result is only
`candidate_for_user_review`; install and execution remain unauthorized.

Read-only examples:

```powershell
python scripts/fleet_readiness.py validate-policy
python scripts/fleet_readiness.py template-remote --device m1_pro_16gb
python scripts/fleet_readiness.py validate-capability owner-capability.json
python scripts/fleet_readiness.py simulate-1080 explicit-interval-input.json
python scripts/eval_contract.py validate-telemetry captured-telemetry.json
```

The CLI has no output-file, network, subprocess, package-manager, model-loader,
SSH, probe, install, or launch operation. A later authorized device-owner task
may implement native collectors that populate these manifests; that work is
not part of this slice.
