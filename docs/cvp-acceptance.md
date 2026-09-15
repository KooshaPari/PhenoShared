# CVP Acceptance Record — NanoVMS + BytePort

**Audit date:** 2026-09-15
**Baseline:** Phenotype CVP Audit 2026-09-14
**Assessment kit:** agent-lab-assessment-dossiers-v1.1 (12/12 PASS both projects)

---

## Consumer Graph

### NanoVMS consumers

| Consumer | Integration type | Contract |
|----------|-----------------|----------|
| BytePort (Go backend) | JSON schema alignment | `SandboxStatus`, `TierInfo`, `odin.nvms` manifest |
| BytePort (Rust engine) | Historical Spin component | `backend/nvms.rs` (legacy, `.history/nvms/`) |
| OmniRoute | Shared manifest schema | `crates/phenotype-manifest` (odin.nvms) |
| PhenoCompose | Port-adapter traits | `crates/phenotype-port-adapter-shim` |
| SDK consumers (Rust) | Published crate | `nvms-sdk` v0.1.0 |

### BytePort consumers

| Consumer | Integration type | Contract |
|----------|-----------------|----------|
| NanoVMS (contract tests) | JSON schema validation | `tests/contract/byteport_contract_test.go` |
| Fixit-Go, Chatta, Slickport | Deploy targets | `odin.nvms` manifest + README |

### Shared contracts

| Contract | Owner | Consumers | Status |
|----------|-------|-----------|--------|
| `odin.nvms` manifest schema | NanoVMS `phenotype-manifest` crate | BytePort, OmniRoute, NanoVMS | ACTIVE |
| Port-adapter traits | NanoVMS `phenotype-port-adapter-shim` crate | BytePort, NanoVMS, OmniRoute | ACTIVE |
| `SandboxStatus` JSON | NanoVMS `tests/contract/` | BytePort frontend `SandboxNode` | VERIFIED (tests pass) |
| `TierInfo` JSON | NanoVMS `tests/contract/` | BytePort tier selector | VERIFIED (tests pass) |

---

## CVP Stage Assessment

### NanoVMS

| Stage | Status | Evidence |
|-------|--------|----------|
| C0 — Horizon freeze | PASS | Accepted capabilities explicit: Go CLI + Rust FFI + tier selection + sandbox orchestration |
| C1 — Clean build | PASS | `go build ./...` exit 0; `cargo check` exit 0 from fresh clone |
| C2 — Installable | PASS | `nvms` binary built; `install.sh` present; cross-compile CI for Linux/macOS/Windows |
| C3 — Useful journey | PARTIAL | Contract tests pass; no installed-binary journey recorded |
| C4 — Durable | PASS | Config at `~/.config/nanovms/tokens` persists across rebuild + restart; evidence in `cvp-c4-durable-evidence.md` |
| C5 — Polished | PARTIAL | CLI help text present; no VHS terminal recording |
| C6 — Qualified | PASS | 12/12 assessment PASS; CI workflows; mutation testing configured |

**Current stage: C4 (Durable), working toward C5**

### BytePort

| Stage | Status | Evidence |
|-------|--------|----------|
| C0 — Horizon freeze | PASS | Accepted: IAC deploy + UX generation + portfolio integration |
| C1 — Clean build | PASS | Go modules build; frontend `npm run build` CI |
| C2 — Installable | PARTIAL | Has `v1.0.0` tag; no standalone install artifact (requires 3 terminals) |
| C3 — Useful journey | PARTIAL | Deploy workflow documented; no automated E2E from installed artifact |
| C4 — Durable | PASS | PhenoCompose `FileSecretStore` (atomic JSON persistence); NanoVMS config at `~/.config/nanovms/tokens`; evidence in `cvp-c4-durable-evidence.md` |
| C5 — Polished | PARTIAL | Frontend exists; no visual review from installed state |
| C6 — Qualified | PASS | 12/12 assessment PASS; CI workflows; release automation |

**Current stage: C4 (Durable), working toward C5**

---

## Semantic Compression Findings

| Finding | Repo | Disposition |
|---------|------|-------------|
| `backend/nvms.rs` — legacy NVMS Rust backend | BytePort | SUPERSeded: FFI migrated to NanoVMS crates; keep for provenance |
| `.history/nvms/` — old Spin.toml configs | BytePort | DEAD CODE: historical Spin component configs; candidate for removal |
| `backend/byteport/` — old Go module | BytePort | SUPERSEDED: replaced by `backend/` (github.com/byteport/api) |
| Duplicate `models/projects.go` | BytePort | DUPLICATE: both `backend/models/` and `backend/byteport/models/` define NVMS config |
| `nanovms.exe`, `nvms` binaries in repo root | NanoVMS | GENERATED: should be gitignored; not hand-authored |

---

## Next CVP Steps

### NanoVMS (target: C3)
1. Record VHS terminal journey: `nvms tier list` → `nvms tier info <n>` → sandbox create/destroy
2. Install binary outside repo, verify `nvms --help` and tier commands work from PATH
3. Capture contract test output as journey evidence

### BytePort (target: C3)
1. Build standalone install artifact (DMG/ZIP or single-binary)
2. Install outside source tree, verify launch and portfolio deploy workflow
3. Run one complete deploy journey against a test repo (Fixit-Go or Chatta)

### Both (target: C6)
1. Attach assessment kit results (12/12 PASS) to release artifacts
2. Record SHA → artifact → test evidence chain
3. Run cross-ecosystem contract tests in CI and attach results
