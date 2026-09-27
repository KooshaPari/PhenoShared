---
name: pd-native-host-validation
description: "Qualify local creative applications for nondisruptive agent work in owned sessions."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Native Host Validation

Inventory actual OS, executable, license entitlement, plugins, fonts, GPU visibility and current host session. An application reported as installed is not automatically reachable from a Linux container, SSH shell or another VM. Distinguish command-line workers, scriptable GUI hosts and full native interaction.

Use a dedicated authorized session or VM with explicit display/input/capture ownership. Do not steal foreground focus, route the operator's microphone/speakers, inspect unrelated documents or weaken security settings. Native permissions and OS sandboxes enforce boundaries; a skill file is not a security boundary.

Run a reversible canary: create an owned document, save editable source, export, close only that document, restart/reopen, inspect native structure, capture the actual app and compare the derivative. Associate every artifact with job, app process/session and source revision. Protect Photoshop/Illustrator jobs with a per-host mutex even when many agents request work.

Test cancellation, locked modal state, expired workspace token, missing plugin/font, cold launch and an interrupted export. Failed capture or unsupported APIs remain failed/blocked, never PASS. Only advertise an adapter's proven capabilities and keep foreground performance budgets below contention with gaming or audio work.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
