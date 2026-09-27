# Day 1 — Home Mac Runner Setup

Register the home Mac as `home-mac` in the Tailscale tailnet and bring it online as a Woodpecker heavy runner with labels `[self-hosted, heavy, home]`.

**Estimated wall-clock:** ~1 hour.

## Prerequisites

- oci-primary up (per `day1-oci-first-light.md`).
- Forgejo reachable via Tailscale.
- Woodpecker server running on oci-primary.
- Home Mac: Apple Silicon, macOS 14+, admin user available.
- Xcode CLT installed (`xcode-select --install`).
- Homebrew installed.

## Step 1 — Install Tailscale

```
brew install --cask tailscale
open /Applications/Tailscale.app
# Sign in with the same account as oci-primary; accept tag:home tag.
tailscale status | grep home-mac
```

## Step 2 — Install Woodpecker agent

```
brew install woodpecker-ci/tap/woodpecker-agent  # or download binary from github.com/woodpecker-ci/woodpecker/releases
mkdir -p ~/Library/Application\ Support/woodpecker-agent
```

Fetch the registration token:

```
bw get password woodpecker/agent-secrets/home-mac
```

## Step 3 — Configure the agent

Create `~/Library/Application Support/woodpecker-agent/config.env` (placeholders):

```
WOODPECKER_SERVER=oci-primary:9000
WOODPECKER_AGENT_SECRET=<WP-01>
WOODPECKER_FILTER_LABELS=self-hosted,heavy,home
WOODPECKER_MAX_WORKFLOWS=1
WOODPECKER_BACKEND=local
```

## Step 4 — launchd plist

Register the script `iac/scripts/register-home-runner.sh` which writes `~/Library/LaunchAgents/com.phenotype.woodpecker-agent.plist`:

```
cd /Users/<you>/CodeProjects/Phenotype/repos/phenotype-infra/iac/scripts
./register-home-runner.sh
launchctl load ~/Library/LaunchAgents/com.phenotype.woodpecker-agent.plist
launchctl list | grep phenotype
```

## Step 5 — Parsec gating (ADR 0008)

The launchd plist starts a companion watcher (Rust binary `parsec-watcher`, Phase 1 stub: shell loop). The watcher:

- polls `pgrep -f Parsec.app` every 5 s;
- on detection, sends `SIGSTOP` to the woodpecker-agent PID;
- on Parsec exit, sends `SIGCONT`.

Phase 1: document the manual flow; Phase 2: ship the Rust watcher. See `docs/adr/0008-parsec-gaming-mode-pause.md`.

## Step 6 — Smoke test

Trigger a heavy job from Woodpecker UI targeting `runs-on: [self-hosted, heavy, home]`:

```yaml
steps:
  smoke:
    image: rust:1.80
    commands: [rustc --version, echo hello-from-home-mac]
    runs-on: [self-hosted, heavy, home]
```

Expect the job to land on `home-mac` within seconds; confirm in Woodpecker UI and agent logs:

```
tail -f /tmp/woodpecker-agent.log
```

## Step 7 — Security review

- Confirm the agent runs as an **unprivileged user** (not `root`, not primary admin user). Create `woodpecker` local user if needed.
- Confirm Tailscale ACLs prevent inbound from cloud nodes except Woodpecker server gRPC (9000).
- Confirm `~/Library/Application Support/woodpecker-agent/config.env` has mode 0600.

## Rollback

- `launchctl unload ~/Library/LaunchAgents/com.phenotype.woodpecker-agent.plist`
- Revoke Woodpecker agent secret via Woodpecker admin UI.
- Optional: `tailscale logout` on this machine.
