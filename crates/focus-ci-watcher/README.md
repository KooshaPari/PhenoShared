# focus-ci-watcher

CI integration monitor for FocalPoint. Polls `origin/main` at configurable intervals; when new commits are detected, clones into an isolated sandbox and triggers fastlane CI lanes. Failures post to Discord via release-bot webhook library.

## Purpose

Automates CI monitoring and real-time failure alerts for FocalPoint releases. Integrates with fastlane lanes (`test`, `lint`, `build`) and Discord webhooks for team notifications.

## Key Types

- `PollResult` — (sha_changed, current_sha) tuple
- `WatcherConfig` — poll interval, repo path, fastlane lanes, Discord webhook URL
- `Watcher` — orchestrates polling, sandbox cloning, lane execution, error posting

## Entry Points

- `Watcher::start()` — begin polling loop
- `get_remote_sha()` — fetch current `origin/main` SHA via `git ls-remote`
- `run_fastlane_lane()` — execute lane in sandbox, capture output
- `post_failure()` — post formatted error to Discord

## Functional Requirements

- CI automation and monitoring
- Real-time failure notification
- Isolated build sandbox (prevents state pollution)

## Consumers

- Release pipeline automation
- FocalPoint iOS/Android CI (fastlane lanes)
