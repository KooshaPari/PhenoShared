# oci-lottery

OCI Always-Free **A1.Flex** capacity lottery daemon. Polls
`oci compute instance launch` across configured regions until Oracle hands
out capacity, then fires a success-hook chain (post-acquire script,
webhook, governance commit, iMessage relay) and exits.

Per Phenotype scripting policy this is the canonical Rust replacement for
ad-hoc shell loops (`while; do oci compute instance launch ... ; sleep 120; done`).

## Why

OCI Always-Free Ampere capacity is rationed: launches return
`Out of host capacity` for hours/days at a time. Reddit consensus:
poll roughly every 2 minutes from at least one region, with jitter, until
you win the lottery. This daemon does that, persistently, across regions,
without re-implementing OCI auth — it shells out to the user's existing
`oci` CLI + `~/.oci/config`.

## Install

```bash
cargo build --release -p oci-lottery
sudo install -m 0755 target/release/oci-lottery /usr/local/bin/oci-lottery
```

## Configure

Drop a JSON file at `~/.cloudprovider/oci-lottery.json`:

```json
{
  "regions": ["ap-tokyo-1", "ap-osaka-1", "eu-frankfurt-1", "us-ashburn-1", "sa-saopaulo-1"],
  "shape": "VM.Standard.A1.Flex",
  "ocpus": 4,
  "memory_gb": 24,
  "image_ocid": "ocid1.image.oc1.ap-tokyo-1...",
  "subnet_ocid": "ocid1.subnet.oc1.ap-tokyo-1...",
  "compartment_ocid": "ocid1.compartment.oc1...",
  "display_name": "phenotype-arm-mesh-node",
  "ssh_authorized_keys_path": "/Users/you/.ssh/id_ed25519.pub",
  "profile": "DEFAULT",
  "backoff_min_secs": 60,
  "backoff_max_secs": 180
}
```

Optional environment:

| Variable | Purpose |
|---|---|
| `OCI_LOTTERY_WEBHOOK_URL` | POST-on-success (Slack/Discord/iMessage relay). |
| `PHENOTYPE_INFRA_REPO`    | Path to `phenotype-infra` for compute-mesh-state.md commit. |
| `AGENT_IMESSAGE_CLI`      | Override iMessage CLI binary (default `agent-imessage`). |
| `RUST_LOG`                | Log level (default `info`). |

## Run as a launchd service (macOS)

```bash
cp dist/phenotype-oci-lottery.plist ~/Library/LaunchAgents/dev.phenotype.oci-lottery.plist
sed -i '' "s|REPLACE_ME|$USER|g" ~/Library/LaunchAgents/dev.phenotype.oci-lottery.plist
launchctl load -w ~/Library/LaunchAgents/dev.phenotype.oci-lottery.plist
```

`KeepAlive=true` + `RunAtLoad=true` survives reboots.

## Observe

```bash
tail -f ~/Library/Logs/phenotype-oci-lottery.out.log
cat ~/.cloudprovider/oci-lottery-state.json | jq
```

State file shape:

```json
{
  "attempts": 217,
  "last_attempt": "2026-04-25T14:02:11Z",
  "last_region": "ap-tokyo-1",
  "last_ad": 1,
  "last_error": "out-of-capacity",
  "started_at": "2026-04-22T08:00:00Z",
  "acquired": false
}
```

On success, `~/.cloudprovider/oci-instance.json` materializes:

```json
{
  "instance_ocid": "ocid1.instance.oc1.ap-tokyo-1.....",
  "region": "ap-tokyo-1",
  "ad": 2,
  "public_ip": "140.x.y.z",
  "acquired_at": "2026-04-25T14:02:42Z"
}
```

## Success-flow diagram

```
                  +-----------------------+
                  |   LAUNCH SUCCESS      |
                  | instance_ocid + IP    |
                  +-----------+-----------+
                              |
       +----------------------+----------------------+
       |              |               |              |
       v              v               v              v
 ~/.local/bin/   $OCI_LOTTERY_   git commit       agent-imessage
 oci-post-       WEBHOOK_URL    compute-mesh-     notify
 acquire.sh      (curl POST)    state.md (✅ OCI)  (failsoft)
       |              |               |              |
       +------ failsoft (warn + continue) ----------+
                              |
                              v
                       process exits 0
```

Each hook is **failsoft** — failure of any one stage logs a warning and
the chain continues. Failures do not block subsequent hooks or stop
the daemon from exiting cleanly after acquisition.

## Operational notes

- **Throttle**: backoff defaults are `60..=180s` per attempt. Reddit
  consensus is "≥2 min minimum" to avoid `TooManyRequests` from the
  control plane. Don't drop below 60s.
- **AD coverage**: by default the daemon iterates ADs 1..=3 per region.
  ap-tokyo-1 / ap-osaka-1 only have AD-1 — non-existent ADs are skipped
  silently after the AD-list lookup.
- **Quota**: Always-Free is 4 OCPU + 24 GB across **all** A1 instances in
  the tenancy. If you already hold an A1 instance, lower `ocpus` /
  `memory_gb` accordingly or you'll hit `LimitExceeded` (which the daemon
  treats as `out-of-capacity` and keeps retrying).
- **Auth**: the daemon never touches `~/.oci/config`. Configure your CLI
  separately (`oci setup config`) before starting the service.
