---
name: pd-render-scheduling
description: "Budget and schedule creative workers across local devices while preserving interactive and audio workloads."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Render Scheduling

Budget the actual installed host, not planned hardware upgrades or the maximum number of agent chats. Inventory CPU threads, GPU memory, RAM, disk bandwidth, application session limits and licensing. Begin with one render/native host slot and separately bounded lightweight validation workers.

Give every job explicit workspace, lease, timeout, process ownership, cancellation and cleanup. Keep interactive high-quality previews separate from bulk export queues. Use low-resolution previews, incremental rebuilds and source/configuration hashes to reduce iteration time. Cache only artifacts whose source, dependencies, tool version and relevant environment match.

Benchmark completed trustworthy outcomes per wall-clock time, including queueing, launch, render, validation and retries. More workers can reduce useful throughput through GPU contention or native focus collisions. Keep foreground reservations for gaming and Ableton and degrade/pause bulk work before audio underruns or UI stalls.

Test two conflicting jobs before scaling; prove one job cannot delete another's public staging files or close its document. Persist failures and release only owned resources. Do not add another scheduler to phenoDesign when asset-engine or an existing broker already owns execution; provide a coherent design-facing interface over that owner.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
