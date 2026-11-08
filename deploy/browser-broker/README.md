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
