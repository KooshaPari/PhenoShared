# focus-cli

FocalPoint command-line interface. Exposes core APIs (rules, rewards, penalties, audit, sync, scheduler) as subcommands. Entry point for local testing, admin operations, and scripting.

## Purpose

Provides a Rust CLI wrapper around FocalPoint core logic. Enables developers and admins to test rules, inspect wallet state, run manual syncs, query audit logs, and generate test schedules without deploying to mobile.

## Key Types

- Command parsers (clap-based) for each subcommand
- Output formatters (JSON, table, human-readable)
- Error handlers with actionable messages

## Entry Points

- `rules` — list, enable, disable, test rules
- `wallet` — inspect balance, mutation history
- `sync` — trigger manual connector sync
- `audit` — query and verify audit chain
- `schedule` — generate task schedule for date

## Functional Requirements

- Admin tooling and testing utilities
- No new domain logic; all business rules in `focus-*` crates

## Consumers

- Local development and testing
- CI/CD integration testing
- Ops runbooks and emergency procedures
