---
name: fd3d-device-budgets
description: "Budget local rendering and frontend GPU work alongside foreground use; use before running Blender, image-to-3D models or parallel browser/GPU agents."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Resource admission before worker fan-out

Start with one worker. The number of agent chats is not the number of safe GPU jobs. Preserve the operator's interactive applications, input focus, audio devices and current work.

## Probe and constrain
Record executable versions, actual GPU model/free VRAM, RAM, renderer backend and platform. Treat planned upgrades and another machine's hardware as unavailable until probed. Start CPU preview threads conservatively, use bounded resolution/samples, retain logs and stop at a timeout.

Separate a cheap geometry/logic lane from a scarce GPU-render lane. Queue scene renders; do not run image-to-3D texture generation, browser GPU benchmarks and foreground gaming simultaneously and call the results representative. Cache by source/input/tool/color-policy hash, not just filename.

For the browser, measure cold transfer/startup, frame-time distribution during movement, offscreen idle and memory after lifecycle cleanup. Proposed numbers in `contracts/quality-budget.json` are project starting targets, not universal limits or measurements. Adapt to foreground-reserved mode and the actual device.

## Escalation
If a job does not fit, first lower preview resolution/samples, serialize shape/texture stages, reuse geometry, or use a poster. Do not silently upload private reference assets to cloud APIs or rent compute. Request authorization for external cost/data transfer explicitly.

## Gate
No focus stealing or full-home/profile mounts. No "GPU available" claim based only on an installed driver. Timeout must terminate the owned worker; test this in the local process model before relying on it for subprocess-spawning tools.

Sources: R05, R23, R24. See `scripts/doctor.py`, `scripts/run_blender.py` and `resources/LOCAL-GENERATION.md`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
