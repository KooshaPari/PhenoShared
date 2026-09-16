# Local operations source

Canonical private preservation repository for small, machine-local operational
scripts that do not belong to an existing product repository.

[![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/local-ops/total)](https://github.com/KooshaPari/local-ops/releases)

The initial capture includes browser-profile helpers, a fork watcher, shell
cache refresh, SSH desktop helper, suspended-process recovery, and local
GitHub/shell safety guards. It contains source only: no credentials, logs,
runtime state, or installed package artifacts.

This capture does not change active command paths. Each future active-link
promotion requires an entry-point-specific runtime check and a reversible
backup.
