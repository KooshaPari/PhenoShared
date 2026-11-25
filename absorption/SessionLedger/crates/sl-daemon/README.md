# sl-daemon

SessionLedger ETL daemon. Watches a directory of `*.jsonl` session transcripts
and, for every new or changed file, runs the session-ledger pipeline
(**ingest → compile → export**), writing one `<session-id>.okf.json` per session.

```text
  watcher (notify / scan) ──Sender<PathBuf>──▶ mpsc(256) ──▶ consumer (ETL) ──▶ *.okf.json
```

## Build & test (isolated)

Always build/test this crate **in isolation** — never the bare workspace root,
because `sl-viewer` pulls `webkit2gtk-sys`, which does not resolve on macOS:

```bash
cargo test -p sl-daemon
cargo run  -p sl-daemon -- serve --watch ~/.forge/sessions --out ./okf-out
cargo run  -p sl-daemon -- serve --watch ./sessions --out ./okf-out --once   # single sweep
```

Optional OTLP/gRPC trace export is feature-gated, so normal builds do not need
a collector or the OpenTelemetry exporter dependencies:

```bash
cargo build -p sl-daemon --features otel
SL_OTLP_ENDPOINT=http://localhost:4317 cargo run -p sl-daemon --features otel -- serve --watch ./sessions --out ./okf-out
```

`OTEL_EXPORTER_OTLP_ENDPOINT` is also accepted when `SL_OTLP_ENDPOINT` is not
set. If neither variable is set, the feature-enabled binary uses the same local
fmt logs and `RUST_LOG` filtering as the default build.

OTLP **metrics** push is a soft stub (`--features otel-metrics`, optional
`SL_OTLP_METRICS=1` acknowledgment). Default Prometheus `GET /metrics` is
unchanged — see [`docs/ops/otlp-metrics.md`](../../docs/ops/otlp-metrics.md).

Optional jemalloc (`tikv-jemallocator`) is also feature-gated and **Unix-only**.
Default builds (including Windows) keep the system allocator:

```bash
cargo build -p sl-daemon --features jemalloc
```

See [`docs/ops/jemalloc.md`](../../docs/ops/jemalloc.md) and
`pwsh ./scripts/jemalloc-check.ps1 -SelfCheck`.

## Run options

### 1. Native process-compose (preferred for local dev — no container)

````bash
SL_WATCH_DIR=~/.forge/sessions SL_OUT_DIR=./okf-out SL_HTTP_BIND=127.0.0.1:8080 \
  process-compose -f crates/sl-daemon/process-compose.yaml up

### Optional Langfuse-compatible tracing

SessionLedger remains local-first. To opt into exporting operational OpenTelemetry
spans over OTLP/HTTP, set the following environment variables before starting the
daemon:

```sh
export SL_LANGFUSE_ENABLED=1
export SL_LANGFUSE_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel/v1/traces
export SL_LANGFUSE_PUBLIC_KEY=pk-lf-...
export SL_LANGFUSE_SECRET_KEY=sk-lf-...
````

Only route, operation, outcome, duration, and correlation metadata are exported.
Session prompts, responses, file contents, paths, and credentials are excluded.
The exporter is fail-open: invalid configuration or a remote outage leaves local
ingestion and replay running and emits a warning. Keep keys in the environment or
your secret manager; they are never logged.

````

### 2. Apple `container` (default OCI runtime — OSS, per-container VM)

Apple `container` is the workspace default OCI runtime; Docker/OrbStack are
labelled fallbacks only. From the repo root:

```bash
container build -t sl-daemon:latest -f crates/sl-daemon/Containerfile .
container run --rm \
  -v "$HOME/.forge/sessions:/data/sessions:ro" \
  -v "$PWD/okf-out:/data/out" \
  sl-daemon:latest serve --watch /data/sessions --out /data/out
````

## Flags

| Flag            | Meaning                                                |
| --------------- | ------------------------------------------------------ |
| `--watch <dir>` | Directory of `*.jsonl` transcripts to watch (required) |
| `--out <dir>`   | Where `<id>.okf.json` files are written (auto-created) |
| `--once`        | Single deterministic sweep, then exit (CI / cron)      |

The HTTP listener defaults to loopback (`127.0.0.0/8` or `::1`) with optional
`SL_API_KEY` on mutating routes. Non-loopback `--http-bind` requires a non-empty
`SL_API_KEY` and gates all `/api/*` routes. Ingest admission is configured with
`SL_INGEST_MAX_BODY_BYTES` (default `1048576`) and `SL_INGEST_MAX_CONCURRENCY`
(default `8`). Shared-key / non-loopback binds also enable a process-wide
`/api/*` rate limit (`SL_API_RATE_LIMIT`, default `60` per
`SL_API_RATE_WINDOW_MS` default `1000`); open loopback leaves it off for DX.
Shared-key / non-loopback binds also enable an `/api/*` circuit breaker
(`SL_API_CIRCUIT_BREAKER`, failure threshold `SL_API_CIRCUIT_FAILURE_THRESHOLD`
default `5`, open window `SL_API_CIRCUIT_OPEN_MS` default `30000`) that returns
`503` + `Retry-After` after consecutive 5xx. CLI outbound calls retry transient
failures via `SL_HTTP_RETRY_MAX` / `SL_HTTP_RETRY_BASE_MS`. See
[`docs/ops/local-trust-boundary.md`](../../docs/ops/local-trust-boundary.md) for
the bind/auth matrix, rate limit, circuit breaker, error envelope, audit fields,
and operational boundary.

## Shell completions

`sl-daemon` ships `clap_complete` support via the `completions` subcommand and
commits generated scripts under [`completions/`](./completions/) for bash, zsh,
fish, and PowerShell.

Generate on demand:

```bash
cargo run -p sl-daemon -- completions bash > crates/sl-daemon/completions/sl-daemon.bash
cargo run -p sl-daemon -- completions zsh > crates/sl-daemon/completions/_sl-daemon
cargo run -p sl-daemon -- completions fish > crates/sl-daemon/completions/sl-daemon.fish
cargo run -p sl-daemon -- completions powershell > crates/sl-daemon/completions/sl-daemon.ps1
```

Install the committed artifacts (from the repo root):

```bash
sh scripts/install-sl-daemon-completions.sh          # bash+zsh+fish+powershell
sh scripts/install-sl-daemon-completions.sh zsh      # one shell
pwsh -NoProfile -File scripts/install-sl-daemon-completions.ps1 -Shell powershell
```

See also [`CONTRIBUTING.md`](../../CONTRIBUTING.md#shell-completions-sl-daemon).
Richer `--help` examples are attached via clap `after_help` on the top-level
CLI and on `serve`, `export`, `search`, `tag`, `archive`, `restore`, `replay`,
`validate`, and `completions`.
