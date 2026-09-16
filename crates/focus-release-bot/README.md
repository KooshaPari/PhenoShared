# focus-release-bot

Discord webhook poster for FocalPoint release notes. Posts release notes to a Discord webhook as formatted embeds with fields for version, changelog, breaking changes, and installation instructions. Webhook URL is passed at runtime, never stored in code.

## Purpose

Automates release notifications to Discord channels for team coordination. Formats release metadata (version, changelog, breaking changes) as rich embeds with color-coded fields. Used by CI/CD pipelines to announce new releases and gather feedback.

## Key Types

- `BotError` — variants for HTTP, JSON, missing webhook URL
- `EmbedField` — name, value, inline flag
- `ReleaseEmbed` — title, description, fields (version, changelog, breaking, install), color
- `DiscordWebhookClient` — POST to webhook endpoint

## Entry Points

- `post_release()` — accept `ReleaseEmbed`, POST to webhook URL
- `EmbedField::new()` — construct field with metadata
- Error handling for network/JSON failures

## Functional Requirements

- Discord webhook API compliance
- Formatted embeds with color and field validation
- No hardcoded credentials (URL passed at runtime)

## Consumers

- CI/CD release pipelines (fastlane, GitHub Actions)
- `focus-ci-watcher` (failure notifications, planned)
