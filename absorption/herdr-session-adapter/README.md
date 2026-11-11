# herdr_session Paperclip adapter (jcode profile first)

External adapter package (no Paperclip fork). Type `herdr_session`, harness profiles jcode/codex/forgecode.
Built from the desk lane's build spec (herdr-adapter-spec, Oct 18). Typechecks and passes smoke.mjs locally. NOT run against a live herdr, Paperclip or SSH host.

Uses only: `herdr pane run`, `herdr pane read --source recent --lines N`, `herdr agent wait --until done` (documented at herdr.dev/docs/socket-api).
Guards: allowedPanes enforced before send; pane id regex; fixed subcommand allowlist; JSONL audit with prompt sha256 only; panes never killed; pane-missing returns clearSession.

## Install (host side, B)
1. On the desk Paperclip host: `npm i && npm run build` in this dir; register by local path (per Paperclip external adapter docs): POST /api/adapters {"localPath": "<dir>"} or ~/.paperclip/adapter-plugins.json entry. Needs the API token via Infisical, not in config.
2. Adapter config for a role: host, pane (e.g. w1:p2), harness, allowedPanes, hosts {mac: "<ssh alias>"}; first target Mac herdr LOCAL-space pane over tailnet SSH.
3. Verify with the spec's test plan section 13 (testEnvironment, round trip, resume, pane killed, audit, scope violation).
Known limits: POSIX remote shell only (mac); desk Windows shell quoting unsupported; result is a heuristic scrape; `agent wait --until done` observes semantic state, may not match every harness; usage tokens not reported (zeros); no WoR wake-back (v1.1).

## Upstream issue text (C), draft only, do not file without his go
Title: External adapters: document how an adapter can map an agent role to an already-running session instead of spawning a process
Body: We built an external adapter (herdr_session) that sends the wake prompt to an existing terminal pane and reads the tail. The docs describe spawn-style adapters (runChildProcess) well, but not session-attach adapters: how clearSession should be used when the target session disappears, whether usage can be omitted without breaking budgets, and how a role can be marked externally managed. Request: a short doc section and an example of a non-spawning adapter, plus guidance on usageBasis when tokens are unavailable.
