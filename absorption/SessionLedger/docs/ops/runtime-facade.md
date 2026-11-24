# Runtime facade — process-compose default + optional engines

SessionLedger brings up the local stack through a thin **runtime facade**
(`scripts/runtime-up.ps1` / `scripts/runtime-up.sh`). The facade picks an
engine from `SL_RUNTIME` and always prefers a **CLI/ops** lifecycle — never a
tray or resident companion ([ADR 0001](../adr/0001-desktop-companion-scope.md)).

## Default (zero hard deps beyond process-compose)

```bash
./scripts/runtime-up.sh
# Windows:
pwsh ./scripts/runtime-up.ps1
```

Equivalent to `process-compose -f process-compose.yaml up` (daemon + viewer with
`/readyz` readiness). Install
[process-compose](https://github.com/F1bonacc1/process-compose) if missing.

| Env                                                       | Effect                                                                        |
| --------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `SL_RUNTIME` unset / `process-compose` / `pc` / `default` | Root `process-compose.yaml`                                                   |
| `SL_RUNTIME=pheno` (`pheno-compose`, `nvms`)              | Delegate to `pheno-compose` or `nvms` CLI                                     |
| `SL_RUNTIME=podman`                                       | `podman-compose` if present, else `podman build` + `run` from `Containerfile` |
| `SL_RUNTIME=wsl`                                          | Re-enter WSL and run the shell facade with process-compose                    |
| `SL_RUNTIME=apple` / `container`                          | Apple `container` build/run (`crates/sl-daemon/Containerfile`)                |

Extra args after the script are forwarded to the selected engine (`up`,
`podman run`, etc.).

## Engine matrix

| Engine                  | Host                | Starts                           | Hard dependency             | Notes                                                                                                                        |
| ----------------------- | ------------------- | -------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **process-compose**     | Win / macOS / Linux | `sl-daemon` + `sl-viewer`        | `process-compose` on `PATH` | **Default.** Native cargo processes; no OCI.                                                                                 |
| **PhenoCompose / nvms** | Win / macOS / Linux | Via external CLI                 | `pheno-compose` or `nvms`   | Not vendored. Stub: [`compose/pheno-compose.yaml`](../../compose/pheno-compose.yaml). Clear error + install URLs if missing. |
| **Podman**              | Win / macOS / Linux | `sl-daemon` image                | `podman`                    | Uses root or `crates/sl-daemon` `Containerfile`. Optional `compose/podman-compose.yaml` if you add one.                      |
| **WSL**                 | Windows + WSL2      | Same as Linux path inside distro | `wsl.exe`                   | Guidance + re-exec; install process-compose/podman **inside** the distro.                                                    |
| **Apple Container**     | macOS               | `sl-daemon` image                | `container` CLI             | Workspace-preferred OCI on Apple Silicon; see daemon README.                                                                 |

On every run the scripts print an **engine probe** (what is / is not on `PATH`)
so operators can see optional modes without enabling them.

## Phenotype / PhenoCompose alignment

[PhenoCompose](https://github.com/KooshaPari/PhenoCompose) is the Phenotype
compose-facing layer over NVMS isolation tiers (WASM / gVisor / Firecracker).
SessionLedger **does not** depend on those crates for day-one local dev:

1. Default remains process-compose (matches FR-014 / existing runbook).
2. `SL_RUNTIME=pheno` delegates to an installed `pheno-compose` or `nvms`
   binary and may pass `-f compose/pheno-compose.yaml`.
3. If the CLI is missing, the facade exits non-zero with install hints
   (`get.nvms.dev`, `cargo install pheno-compose --features nvms-driver`) and
   points back to process-compose.

Treat the stub YAML as documentation until PhenoCompose’s compose schema and
`up` subcommand are stable for this repo.

## Podman / Containerfile path

```bash
SL_RUNTIME=podman ./scripts/runtime-up.sh
# optional:
# SL_PODMAN_IMAGE=sl-daemon:dev SL_PORT=8080
```

Build context is the repo root. Data defaults to `./.sl-data` mounted at
`/data`. For Apple:

```bash
SL_RUNTIME=apple ./scripts/runtime-up.sh
# or: SL_RUNTIME=container
```

## Relationship to `make dev` / future `just up`

Today `make dev` still calls `process-compose up` directly after `make build`.
The facade is the portable entrypoint for multi-engine selection; a sibling
`just`/`task` lane may call these scripts as `up`. Prefer the facade when you
need PhenoCompose, Podman, WSL, or Apple Container without changing Make.

## Out of scope

- Tray / menubar / auto-start companions (ADR 0001).
- Vendoring PhenoCompose or nvms into this repository.
- Replacing CI’s direct `cargo` / smoke harnesses with the facade.

## Related

- [`runbook.md`](runbook.md) — health probes, load smoke, common failures
- [`../adr/0001-desktop-companion-scope.md`](../adr/0001-desktop-companion-scope.md)
- Root [`process-compose.yaml`](../../process-compose.yaml)
- [`crates/sl-daemon/Containerfile`](../../crates/sl-daemon/Containerfile)
- [`crates/sl-daemon/README.md`](../../crates/sl-daemon/README.md) — Apple `container` examples
