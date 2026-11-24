# Browser broker deployment

This directory holds the pieces needed to run `brokerd` on a remote host,
including the Jcode Cloud machine described in the harness docs.

**Status: manifests only.** They were written from the binary's actual CLI
surface and have **not** been exercised against a live cloud host, because that
requires `jcode login`. Treat them as a starting point, not a verified deployment.

## Why loopback-only

`brokerd` refuses to bind a non-loopback address without a bearer token. That is
deliberate: the viewer can render any live session, including an authenticated
one, so it must never be reachable by an unauthenticated caller.

The intended shape is:

```
client -> SSH port-forward / existing outbound tunnel -> 127.0.0.1:8787
```

Do not publish the viewer port. There is no TLS termination in `brokerd`, so
exposing it directly would send the bearer token in clear text.

## Layout on the host

| Path | Purpose |
|---|---|
| `/var/lib/browser-broker/profiles/<principal>/<profile>/gen-<n>/` | one browser data directory per generation |
| `/var/lib/browser-broker/leases/` | lease records |
| `/var/lib/browser-broker/fences.json` | monotonic fencing token per profile |

`profiles/` and `leases/` are owner-only (`0700`). Anything that holds
authenticated cookies lives under `profiles/`, so treat the whole state directory
as sensitive and back it up only encrypted.

## Build

The binary is built by the normal workspace build, then copied into the image:

```sh
cargo build --release -p substrate-browser-broker
podman build -t localhost/browser-broker -f deploy/browser-broker/Containerfile .
```

## Run

```sh
BROKER_TOKEN="$(head -c 32 /dev/urandom | base64)" \
  podman run --rm -p 127.0.0.1:8787:8787 \
    -e BROKER_TOKEN -v browser-broker-state:/var/lib/browser-broker \
    localhost/browser-broker
```

Then from the client side:

```sh
ssh -N -L 8787:127.0.0.1:8787 <host>
curl -H "Authorization: Bearer $BROKER_TOKEN" http://127.0.0.1:8787/v1/sessions
```

## Endpoints

| Route | Returns |
|---|---|
| `GET /healthz` | `{"status":"ok"}`, no auth |
| `GET /v1/leases` | every lease record, expired or not |
| `GET /v1/sessions` | live sessions with lease id, holder, scope, generation |
| `GET /v1/view/{lease_id}` | metadata plus `png_base64` |
| `GET /v1/view/{lease_id}/png` | `image/png` of that exact lease's page |

A lease that is not live returns `404`. The viewer never falls back to another
browser.

## What is not solved here

1. **No TLS.** Keep it on loopback and tunnel.
2. **No token rotation.** Restart with a new `--token-env` value.
3. **No per-caller authorisation.** One token sees every session. Per-principal
   tokens are a later change to `AppState::authorised`.
4. **Leases are not reaped on crash.** A killed `brokerd` leaves lease records
   until their TTL passes; `sweep_expired` runs on the next grant, so the window
   is bounded by the TTL.
5. **Chrome is inside the container.** It needs `--no-sandbox`-free operation, so
   the image must run as a non-root user with a writable `/tmp`; the provided
   unit and Containerfile both do this.

## Running it on macOS (launchd)

`browser-broker.service` is the systemd unit. On macOS the equivalent is a per-user launchd
agent, shipped here as the template `com.kooshapari.browser-broker.plist.in`. It is a template
because launchd does **not** expand `~` or environment variables in `ProgramArguments`,
`StandardOutPath`, `StandardErrorPath` or `WorkingDirectory`, so the absolute home directory has
to be substituted before the plist is installed.

Install:

```sh
install -d ~/.local/bin ~/.local/state ~/Library/LaunchAgents
install -m 755 brokerd ~/.local/bin/brokerd
install -m 755 browser-broker-run ~/.local/bin/browser-broker-run
install -m 600 /dev/null ~/.local/state/browser-broker.env
printf 'BROKER_TOKEN=%s\n' "$(openssl rand -base64 32 | tr -d '=+/')" \
  > ~/.local/state/browser-broker.env
sed "s|__HOME__|$HOME|g" com.kooshapari.browser-broker.plist.in \
  > ~/Library/LaunchAgents/com.kooshapari.browser-broker.plist
chmod 644 ~/Library/LaunchAgents/com.kooshapari.browser-broker.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kooshapari.browser-broker.plist
launchctl enable gui/$(id -u)/com.kooshapari.browser-broker
```

Check and manage it:

```sh
launchctl print gui/$(id -u)/com.kooshapari.browser-broker | head -30
lsof -nP -iTCP:8788 -sTCP:LISTEN
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8788/v1/sessions   # 401
launchctl kickstart -k gui/$(id -u)/com.kooshapari.browser-broker   # restart
launchctl bootout  gui/$(id -u)/com.kooshapari.browser-broker   # stop
```

### Why a wrapper script

`brokerd --token-env BROKER_TOKEN` takes the **name** of an environment variable, not a value.
The wrapper sources the 0600 env file into the process environment and `exec`s `brokerd`. The
token therefore never appears in `argv` (so never in `ps`), never in the plist, and never in the
log. Anything running as the same user can still read it from the environment or the env file -
that is the same trust boundary as the file itself.

### Notes

- The plist binds **loopback only**. `127.0.0.1:8788` is used here because `127.0.0.1:8787` is
  already taken on this host by a herdr control bridge.
- `KeepAlive` is `SuccessfulExit = false`: the service restarts after a crash or a signal, but not
  after a clean exit, so `launchctl bootout` genuinely stops it.
- `ThrottleInterval` is 10s so a failing daemon cannot spin.

### TLS on the daemon

The daemon supports `--tls-cert` / `--tls-key` and serves HTTPS when both are given. On this host it
is **prepared but not enabled**: the certificate is in the login keychain but its **trust settings
are not applied**, because `security add-trusted-cert` requires an interactive "Always Trust"
confirmation. Serving HTTPS that no client trusts is worse for clients than plain HTTP on
loopback, so the wrapper keeps the `--tls-*` lines commented out until the trust is granted.

To enable it:

```sh
security add-trusted-cert -r trustRoot \
  -k ~/Library/Keychains/login.keychain-db \
  ~/.local/state/browser-broker/tls/cert.pem
# click "Always Trust" when prompted
# then uncomment the two --tls-* lines in ~/.local/bin/browser-broker-run
launchctl kickstart -k gui/$(id -u)/com.kooshapari.browser-broker
```

TLS is worth enabling once the daemon can serve the MCP's **mutations** over HTTP. With
`BROKERD_URL` unset the MCP works the shared on-disk lease store directly and never calls the
daemon, so TLS on the daemon currently protects a surface nothing calls yet.
