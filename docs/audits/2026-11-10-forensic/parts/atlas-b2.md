### eyetracker
Gaze and eye-tracking family: 8 crate dirs, headed by the inference engine.

| Crate | LOC | Purpose |
|---|---|---|
| `eyetracker-inference` | 5,605 | Inference engine; the family's only crate measured above 5k LOC |
| `eyetracker-*` (7 further dirs) | UNKNOWN | Remaining eyetracker crates; LOC not itemized in source |

### routing / router
Cross-family request routing, the CLI dispatch surfaces, and the `engine-*` adapter layer the gateway drives.

| Crate | LOC | Purpose |
|---|---|---|
| `gateway` | 70,752 | Cross-family request routing; dispatches to the engine crates |
| `focus-cli` + `fabric-cli` | 7,719 | CLI dispatch surfaces (3,865 + 3,854) |

### omniroute
No `omniroute` crate is itemized in any inventory, family rollup, or directory map, and the ~324 crates that no inventory names are unclassified, so both presence and size are UNKNOWN.

| Crate | LOC | Purpose |
|---|---|---|
| UNKNOWN | UNKNOWN | No omniroute entry exists in the source |

### infra / config
Daemon, transport, and platform-shim crates from the source's INFRA subgraph; `gateway` and `hexa-kit` are sectioned elsewhere.

| Crate | LOC | Purpose |
|---|---|---|
| `fabric-daemon` + `teamcomm-daemon` | 10,937 | Daemon processes (7,318 + 3,619) |
| `substrate-browser-broker` + `apisync` + `pine-syscall` | 13,743 | Browser-broker, API-sync, and syscall shims (4,845 + 4,520 + 4,378) |
| `sharecli-{ipc,session,fleet}` | 12,579 | IPC/session/fleet transport daemons (4,700 + 4,194 + 3,685) |

### tui / gui
Terminal, desktop, mobile, and canvas presentation crates; `sharecli-thermal-tui` and `fabric-{tui,gui,web}` are named in the source but carry no crate LOC.

| Crate | LOC | Purpose |
|---|---|---|
| `eidolon-desktop` + `eidolon-mobile` | 15,251 | Desktop and mobile presentation crates (7,702 + 7,549) |
| `pheno-terminal` + `connector-canvas` | 9,588 | Terminal and canvas surfaces (5,640 + 3,948) |

### tests / support
The cross-repo `tests/` tree (297 tracked files, LOC not given) plus the FFI/FUSE/process-runtime support crates.

| Crate | LOC | Purpose |
|---|---|---|
| `focus-ffi` + `sharecli-fuse` + `pheno-proc-runtime` | 15,730 | FFI, FUSE, and process-runtime support crates (3,546 + 7,879 + 4,305) |

### other / absorbed
Duplicated and absorbed trees: `absorption/` 4,414 files, `_archived/` 632, `archive/`+`archives/` 225, `docs/absorbed-from-*`, `.vendor/lancedb`. LOC figures source-wide are `find`-based upper bounds (~2.2x overcount), and the source's remaining prefix families are summarized by counts only, not per-crate LOC.

| Crate | LOC | Purpose |
|---|---|---|
| `agile-plus/` | 132,228 | Nested workspace of 51 agileplus crates (duplicate copy) |
| `hexa-kit/` | 91,295 | Nested host of the third agileplus copy (25 nested crates) |

### Family totals

| Family | Crates | LOC |
|---|---|---|
| substrate/fabric | 3 named of 35 dirs (`substrate*` 15, `fabric*` 20) | 20,360 (9,188 + 7,318 + 3,854) |
| browser | 1 named | 4,845 |
| eidolon | 4 | 41,912 (22,828 + 7,702 + 7,549 + 3,833) |
| pheno-compose | UNKNOWN | UNKNOWN |
| sharecli | 5 named of 12 dirs | 110,519 (90,061 + 7,879 + 4,700 + 4,194 + 3,685) |
| eyetracker | 8 | 5,605 itemized; family total UNKNOWN |
| routing/router | 3 named (+7 `engine-*`) | 78,471 itemized (70,752 + 3,865 + 3,854) |
| omniroute | UNKNOWN | UNKNOWN |
| infra/config | 8 named | 37,259 (10,937 + 13,743 + 12,579) |
| tui/gui | 8 named (4 with LOC) | 24,839 itemized (15,251 + 9,588) |
| tests/support | 3 named (+`tests/` tree) | 15,730 (3,546 + 7,879 + 4,305) |
| other/absorbed | 2 named + absorbed trees | 223,523 (132,228 + 91,295) |

**Reconciliation, and why the column does not sum.** The family rows are a ledger of what the source
tiers named, not a census. Two properties follow, and neither is a defect in the source:

- **Not exhaustive.** Roughly two dozen crates are individually named, against 372 `crates/` dirs and
  283 declared workspace paths. The remainder (~324 crates) is named by no inventory and carries no
  per-crate LOC anywhere, so it is recorded UNKNOWN rather than estimated.
- **Not additive.** Families overlap by design. `fabric-cli` appears under both substrate/fabric and
  routing/router; `eidolon-desktop`/`-mobile` under both eidolon and tui/gui; `sharecli-fuse` under both
  sharecli and tests/support; `fabric-daemon`, `substrate-browser-broker`, and `sharecli-{ipc,session,fleet}`
  under both substrate/browser/sharecli and infra/config. Summing the column double-counts those crates.

Consequently the workspace-member LOC is NOT reconciled to the 304,248 first-party Rust LOC stated in
"Scale and shape". The gap is unmeasured, not zero.

