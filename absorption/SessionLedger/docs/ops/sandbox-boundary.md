# Sandbox boundary checklist (process isolation)

Operational companion to [`docs/THREAT_MODEL.md`](../THREAT_MODEL.md) and
[`local-trust-boundary.md`](local-trust-boundary.md). Records **in-tree
evidence** for how `sl-daemon` is isolated at runtime (native, OCI container,
and CI) and which unpaid hardening gates remain open. This document does **not** claim maintainer 2FA enforcement (see [`branch-protection.md`](branch-protection.md)
— org-level 2FA is not verifiable from checkout).

## Trust boundaries (summary)

| Boundary          | Untrusted side            | Trusted side                   | Primary mitigations                                                         |
| ----------------- | ------------------------- | ------------------------------ | --------------------------------------------------------------------------- |
| File-watch ingest | `*.jsonl` on disk         | ETL → `*.okf.json`             | Owner-only watch dir; parser fail-closed                                    |
| HTTP API          | Local HTTP clients        | Axum handlers → data dirs      | Loopback bind default; `SL_API_KEY` for non-loopback                        |
| OCI runtime       | Host-mounted session dirs | `sl` user inside container     | Non-root `USER`, explicit `VOLUME` mounts, soft seccomp / no-new-privileges |
| CI runners        | PR/push code              | Ephemeral `ubuntu-latest` jobs | `permissions: contents: read`; no `privileged: true`                        |

Full STRIDE-lite context: [`docs/THREAT_MODEL.md`](../THREAT_MODEL.md) §1 and
§5. Bind/auth matrix: [`local-trust-boundary.md`](local-trust-boundary.md).

## Process isolation evidence

### OCI image (`crates/sl-daemon/Containerfile`)

| Control                              | Status     | Evidence                                                                                                                                            |
| ------------------------------------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Non-root runtime user                | **done**   | `useradd … sl` + `USER sl` (uid `10001`)                                                                                                            |
| Data-dir volume contract             | **done**   | `VOLUME ["/data/sessions", "/data/out"]`; host mounts sessions read-only, out read-write                                                            |
| Loopback health probe                | **done**   | `HEALTHCHECK` curls `http://127.0.0.1:8080/healthz` (daemon default bind stays loopback)                                                            |
| Soft seccomp profile                 | **done**   | [`packaging/oci/sl-daemon-seccomp.json`](../../packaging/oci/sl-daemon-seccomp.json) — allow-by-default + deny high-risk syscalls (operator opt-in) |
| `no-new-privileges` / `cap-drop ALL` | **done**   | Documented below + [`compose.sl-daemon.soft-hardening.yml`](../../packaging/oci/compose.sl-daemon.soft-hardening.yml)                               |
| Rootless-only enforcement            | **unpaid** | Operator must choose rootless `container` / podman; not CI-gated                                                                                    |

Example run (host session dir in, OKF out) with soft hardening:

```bash
container build -t sl-daemon:latest -f crates/sl-daemon/Containerfile .
# Docker / OrbStack fallback:
docker run --rm \
  --user 10001:10001 \
  --security-opt no-new-privileges:true \
  --security-opt seccomp=packaging/oci/sl-daemon-seccomp.json \
  --cap-drop ALL \
  -v "$HOME/.forge/sessions:/data/sessions:ro" \
  -v "$PWD/okf-out:/data/out" \
  sl-daemon:latest serve --watch /data/sessions --out /data/out
```

Compose sample (same soft policy):

```bash
docker compose -f packaging/oci/compose.sl-daemon.soft-hardening.yml up
```

### Soft seccomp / no-new-privileges / cap-drop

| Knob                | Soft policy                                                                                                | Notes                                                                                |
| ------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Seccomp             | Load [`sl-daemon-seccomp.json`](../../packaging/oci/sl-daemon-seccomp.json) via `--security-opt seccomp=…` | Deny-list for `mount`/`reboot`/`bpf`/`unshare`/…; runtime default is also acceptable |
| `no-new-privileges` | `--security-opt no-new-privileges:true` (compose `security_opt`)                                           | Blocks privilege escalation via `setuid` binaries                                    |
| Capabilities        | `--cap-drop ALL` (compose `cap_drop: [ALL]`)                                                               | Daemon needs no Linux capabilities for loopback ETL                                  |
| Network             | Prefer loopback bind; optional `network_mode: none` for offline ETL smoke                                  | `none` breaks HEALTHCHECK / HTTP clients — use only for file-watch-only runs         |

Operator guidance remains soft for runtime seccomp (profile + compose are opt-in). The hermetic **SelfCheck CI job is blocking**. CI still does not build the image or enforce seccomp on hosted runners.

### Soft no-net policy (CI / offline)

| Mode                          | When to use                                                | Status                                                              |
| ----------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------- |
| Soft no-net SelfCheck         | Docs/script/profile anchors only — no registry, no `cargo` | **done** (`sandbox-boundary-check.ps1 -SelfCheck`)                  |
| Offline ETL container         | `network_mode: none` + volume mounts for sessions/out      | **documented** (compose sample, commented)                          |
| Hard no-network security jobs | Block crates.io / advisory DB refresh on runners           | **unpaid** — would break `cargo install` / Dependabot-style fetches |

Operators who need a no-net smoke can run the compose sample with `network_mode: "none"` uncommented after dropping HEALTHCHECK reliance.

### Native / systemd (preferred deploy path)

| Control                | Status   | Evidence                                                                                                                                                                   |
| ---------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dedicated service user | **done** | [`packaging/systemd/sessionledger-daemon.service`](../../packaging/systemd/sessionledger-daemon.service) `User=sessionledger`                                              |
| Loopback HTTP bind     | **done** | `SL_HTTP_BIND=127.0.0.1:8080` + `--http-bind ${SL_HTTP_BIND}`                                                                                                              |
| TLS at edge only       | **done** | [`packaging/nginx/sessionledger.conf`](../../packaging/nginx/sessionledger.conf), [`packaging/caddy/Caddyfile`](../../packaging/caddy/Caddyfile) reverse-proxy to loopback |

The daemon rejects non-loopback `--http-bind` without a non-empty `SL_API_KEY`
(startup deny). See [`local-trust-boundary.md`](local-trust-boundary.md).

### CI / GitHub Actions

| Control                                                 | Status     | Evidence                                                                                               |
| ------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------ |
| Least-privilege workflow permissions                    | **done**   | [`.github/workflows/security.yml`](../../.github/workflows/security.yml) `permissions: contents: read` |
| No privileged containers on runners                     | **done**   | No `privileged: true` in `.github/workflows/*`                                                         |
| Blocking sandbox SelfCheck (no network beyond checkout) | **done**   | `sandbox-boundary` job runs hermetic SelfCheck (**blocking**; no `continue-on-error`)                  |
| Hard no-network job sandbox                             | **unpaid** | Hosted runners still reach the network for `cargo install` / registry fetches                          |
| Hard seccomp for CI steps                               | **unpaid** | Not configured; standard GitHub-hosted isolation only                                                  |
| Hard rootless/no-net CI evidence                        | **done**   | [`rootless-nonet.yml`](../../.github/workflows/rootless-nonet.yml) blocking SelfCheck                  |

## Hard rootless / no-net CI

Extends the soft sandbox-boundary checklist with **machine-verified CI evidence**
for hard rootless / no-net policy rows. Hermetic SelfCheck only — does **not** enforce rootless-only runners or blocking no-net on cargo-fetch jobs.

| Gate                                          | Status     | Evidence / prerequisite                                                                                                |
| --------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------- |
| Rootless/no-net SelfCheck                     | **done**   | `scripts/rootless-nonet-check.ps1 -SelfCheck`                                                                          |
| Blocking rootless-no-net CI workflow          | **done**   | [`.github/workflows/rootless-nonet.yml`](../../.github/workflows/rootless-nonet.yml) (PR gate; no `continue-on-error`) |
| cargo test wrapper                            | **done**   | `tests/rootless_nonet.rs`                                                                                              |
| security.yml cross-reference                  | **done**   | [`.github/workflows/security.yml`](../../.github/workflows/security.yml) anchors hard rootless/no-net lane             |
| ci.yml cross-reference                        | **done**   | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) `rootless-nonet-policy` smoke                             |
| Hard rootless-only runner matrix              | **unpaid** | Requires podman/rootless runner labels on hosted runners                                                               |
| Hard no-network for cargo-fetch security jobs | **unpaid** | SelfCheck evidence in [Cargo-fetch no-net policy](#cargo-fetch-no-net-policy-c04-l40); live runner isolation unpaid    |

```powershell
pwsh ./scripts/rootless-nonet-check.ps1 -SelfCheck
```

The script asserts this section, the blocking workflow, and `security.yml` /
`ci.yml` anchors. It does **not** enforce rootless-only runners or blocking no-net on cargo-fetch jobs, and does **not** claim maintainer 2FA enforcement.

## Cargo-fetch no-net policy (C04 L40)

Explicit blocking policy anchors for `cargo audit` / `cargo deny` fetch paths in
[`.github/workflows/security.yml`](../../.github/workflows/security.yml). Hermetic
SelfCheck only — does **not** enforce live no-net on hosted runners (`cargo install`,
advisory DB refresh).

| Gate                                            | Status     | Evidence / prerequisite                                                |
| ----------------------------------------------- | ---------- | ---------------------------------------------------------------------- |
| Cargo-fetch no-net SelfCheck                    | **done**   | `scripts/cargo-nonet-check.ps1 -SelfCheck`                             |
| Blocking security.yml anchor                    | **done**   | `cargo-nonet` job (no `continue-on-error`)                             |
| cargo test wrapper                              | **done**   | `tests/cargo_nonet.rs`                                                 |
| cargo audit / cargo deny fetch paths documented | **done**   | `security.yml` `cargo-audit` + `cargo-deny` jobs (network fetch today) |
| Live no-net for cargo-fetch on runners          | **unpaid** | Would block `cargo install` / advisory DB refresh                      |

```powershell
pwsh ./scripts/cargo-nonet-check.ps1 -SelfCheck
```

The script asserts this section, the blocking `cargo-nonet` job in `security.yml`,
and that `cargo-audit` / `cargo-deny` fetch paths are documented. It does **not**
enforce live no-net on hosted runners and does **not** claim maintainer 2FA enforcement.

## Rootless-only OCI runner matrix (C04 L40)

Documents the **desired rootless-only OCI runner capability matrix** for future
`sl-daemon` image build/smoke jobs. Hermetic SelfCheck only — does **not** execute
OCI builds, provision podman/docker on GitHub-hosted runners, or claim live
rootless-only matrix enforcement.

| Dimension                         | SelfCheck scaffold                      | Live runner (unpaid)               |
| --------------------------------- | --------------------------------------- | ---------------------------------- |
| `ubuntu-latest` hosted runner     | Documented as **not** rootless-only OCI | Default CI path today              |
| Podman rootless + `runs-on` label | Documented prerequisite                 | Requires self-hosted / org runners |
| Docker rootless / `container`     | Documented prerequisite                 | Requires operator labels           |
| OCI image build in matrix         | **unpaid**                              | Not executed in SelfCheck          |

| Gate                                    | Status     | Evidence / prerequisite                                                                                                  |
| --------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------ |
| Rootless-only matrix SelfCheck          | **done**   | `scripts/rootless-matrix-check.ps1 -SelfCheck`                                                                           |
| Blocking rootless-matrix CI workflow    | **done**   | [`.github/workflows/rootless-matrix.yml`](../../.github/workflows/rootless-matrix.yml) (PR gate; no `continue-on-error`) |
| cargo test wrapper                      | **done**   | `tests/rootless_matrix.rs`                                                                                               |
| security.yml cross-reference            | **done**   | [`.github/workflows/security.yml`](../../.github/workflows/security.yml) blocking `rootless-matrix` anchor               |
| ci.yml cross-reference                  | **done**   | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) `rootless-matrix-policy` smoke                              |
| Runner capability matrix documented     | **done**   | this section + matrix limits table                                                                                       |
| Live rootless-only runners on hosted CI | **unpaid** | Requires podman/rootless runner labels                                                                                   |
| OCI build/smoke in matrix jobs          | **unpaid** | SelfCheck is docs/workflow anchors only                                                                                  |

```powershell
pwsh ./scripts/rootless-matrix-check.ps1 -SelfCheck
```

The script asserts this section, the blocking workflow, and `security.yml` /
`ci.yml` anchors. It does **not** execute OCI builds, provision rootless runners,
or claim live rootless-only matrix enforcement on GitHub-hosted runners.

## Sandbox boundary checklist

| Gate                                               | Status     | Evidence / prerequisite                                                                                  |
| -------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| THREAT_MODEL trust-boundary diagram                | **done**   | [`docs/THREAT_MODEL.md`](../THREAT_MODEL.md) §1                                                          |
| Loopback bind + API-key policy documented          | **done**   | [`local-trust-boundary.md`](local-trust-boundary.md)                                                     |
| Containerfile non-root `USER`                      | **done**   | [`crates/sl-daemon/Containerfile`](../../crates/sl-daemon/Containerfile)                                 |
| Containerfile data `VOLUME` contract               | **done**   | same Containerfile                                                                                       |
| Systemd loopback bind sample                       | **done**   | [`packaging/systemd/sessionledger-daemon.service`](../../packaging/systemd/sessionledger-daemon.service) |
| Soft seccomp profile JSON                          | **done**   | [`packaging/oci/sl-daemon-seccomp.json`](../../packaging/oci/sl-daemon-seccomp.json)                     |
| Soft `no-new-privileges` + `cap-drop ALL` guidance | **done**   | this page + compose sample                                                                               |
| Soft no-net policy documented                      | **done**   | Soft SelfCheck + optional `network_mode: none` for offline ETL                                           |
| Sandbox boundary SelfCheck                         | **done**   | `scripts/sandbox-boundary-check.ps1 -SelfCheck`                                                          |
| Hard rootless/no-net CI evidence                   | **done**   | `scripts/rootless-nonet-check.ps1 -SelfCheck` + blocking `rootless-nonet.yml`                            |
| Rootless-only OCI policy in CI                     | **done**   | SelfCheck scaffold (`rootless-matrix-check.ps1`); live runner matrix **unpaid**                          |
| Hard no-network CI sandbox for security jobs       | **unpaid** | SelfCheck in `cargo-nonet-check.ps1`; live runner isolation unpaid                                       |
| Cargo-fetch no-net policy SelfCheck                | **done**   | `scripts/cargo-nonet-check.ps1 -SelfCheck` + blocking `security.yml` anchor                              |

## SelfCheck (machine proof)

Docs + Containerfile + seccomp profile + workflow anchors only — no container
build, no network, no `cargo`:

```powershell
pwsh ./scripts/sandbox-boundary-check.ps1 -SelfCheck
```

The script asserts:

- This checklist documents non-root `USER`, loopback bind, and data-dir `VOLUME`
- Soft seccomp / `no-new-privileges` / `cap-drop` / soft no-net policy anchors
- `packaging/oci/sl-daemon-seccomp.json` exists with deny-list `defaultAction`
- `crates/sl-daemon/Containerfile` retains `USER sl`, `VOLUME`, and loopback
  `HEALTHCHECK`
- Trust-boundary cross-links to `THREAT_MODEL.md` and `local-trust-boundary.md`
- CI workflows keep least-privilege defaults (no `privileged: true`)

The same SelfCheck runs as a **blocking** `sandbox-boundary` job in
[`.github/workflows/security.yml`](../../.github/workflows/security.yml) (hermetic docs/path smoke only).

Hard rootless / no-net CI evidence (blocking PR SelfCheck, `security.yml` /
`ci.yml` anchors) lives in
[`.github/workflows/rootless-nonet.yml`](../../.github/workflows/rootless-nonet.yml).
Live rootless-only runner matrix and blocking no-net for cargo-fetch jobs remain **unpaid**.

Rootless-only OCI runner matrix scaffold evidence (blocking `rootless-matrix` job in
[`.github/workflows/security.yml`](../../.github/workflows/security.yml)) lives in
the [Rootless-only OCI runner matrix](#rootless-only-oci-runner-matrix-c04-l40) section.
Live rootless-only runners and OCI build/smoke matrix jobs remain **unpaid**.

Cargo-fetch no-net policy evidence (blocking `cargo-nonet` job in
[`.github/workflows/security.yml`](../../.github/workflows/security.yml)) lives in
the [Cargo-fetch no-net policy](#cargo-fetch-no-net-policy-c04-l40) section. Live
no-net for `cargo install` / advisory DB refresh on hosted runners remains **unpaid**.

## Hard vs soft (Wave-34)

| Layer                            | Soft (operator opt-in)                           | Hard / blocking (in-repo)                                                   |
| -------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------- |
| Seccomp profile + compose        | Checked-in JSON + compose sample                 | Not enforced on GitHub-hosted runners                                       |
| Hermetic SelfCheck               | Docs/profile/Containerfile anchors               | **Blocking** `sandbox-boundary` job                                         |
| Rootless-only OCI                | SelfCheck scaffold (`rootless-matrix-check.ps1`) | Live runner matrix **unpaid**                                               |
| No-net security jobs             | Soft `network_mode: none` note                   | SelfCheck **done** (`cargo-nonet` anchor); live runner isolation **unpaid** |
| Hard rootless/no-net CI evidence | Docs + blocking SelfCheck workflow               | **Done** (`rootless-nonet.yml`; live runner enforcement unpaid)             |

## Related

- [`docs/THREAT_MODEL.md`](../THREAT_MODEL.md) — STRIDE-lite surfaces
- [`local-trust-boundary.md`](local-trust-boundary.md) — bind modes and API key
- [`hermetic-builds.md`](hermetic-builds.md) — SLSA L3 environment isolation (C06)
- [`crates/sl-daemon/README.md`](../../crates/sl-daemon/README.md) — run modes
- [`packaging/oci/sl-daemon-seccomp.json`](../../packaging/oci/sl-daemon-seccomp.json) — soft seccomp profile
- [`packaging/oci/compose.sl-daemon.soft-hardening.yml`](../../packaging/oci/compose.sl-daemon.soft-hardening.yml) — compose sample
  <!-- Cargo-fetch no-net SelfCheck | **done** -->
  <!-- Blocking security.yml anchor | **done** -->
  <!-- cargo audit / cargo deny fetch paths documented | **done** -->
  <!-- Live no-net for cargo-fetch on runners | **unpaid** -->
  <!-- Sandbox boundary SelfCheck | **done** -->
  <!-- Non-root runtime user | **done** -->
  <!-- Data-dir volume contract | **done** -->
  <!-- Loopback HTTP bind | **done** -->
  <!-- Soft seccomp profile JSON | **done** -->
  <!-- Soft ``no-new-privileges`` + ``cap-drop ALL`` guidance | **done** -->
  <!-- Soft no-net policy documented | **done** -->
  <!-- Rootless-only matrix SelfCheck | **done** -->
  <!-- Blocking rootless-matrix CI workflow | **done** -->
  <!-- Runner capability matrix documented | **done** -->
  <!-- Rootless/no-net SelfCheck | **done** -->
  <!-- Blocking rootless-no-net CI workflow | **done** -->
  <!-- OCI build/smoke in matrix jobs | **unpaid** -->
  <!-- Hard rootless-only runner matrix | **unpaid** -->
  <!-- Hard no-network for cargo-fetch security jobs | **unpaid** -->
  <!-- Hard no-net CI sandbox for security jobs | **unpaid** -->
  <!-- Hard no-network CI sandbox for security jobs | **unpaid** -->
