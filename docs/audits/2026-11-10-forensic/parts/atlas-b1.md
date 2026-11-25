## Rust workspace atlas

### substrate / fabric
Runtime graph, daemon, and CLI surfaces that back the fabric runtime; `substrate*` has 15 crate dirs, `fabric*` 20.

| Crate | LOC | Purpose |
|---|---|---|
| `fabric-graph` | 9,188 | Core graph store for the fabric runtime |
| `fabric-daemon` | 7,318 | Long-running fabric daemon |
| `fabric-cli` | 3,854 | Fabric command-line client |

### browser
Browser automation and lease brokering; only `substrate-browser-broker` is enumerated in the source inventory.

| Crate | LOC | Purpose |
|---|---|---|
| `substrate-browser-broker` | 4,845 | Broker for browser profile leases and sessions |

### eidolon
Sandboxed agent runtime with desktop and mobile frontends (`eidolon*` = 4 crate dirs).

| Crate | LOC | Purpose |
|---|---|---|
| `eidolon-sandbox` | 22,828 | Sandboxed execution core for Eidolon agents |
| `eidolon-desktop` | 7,702 | Desktop client surface |
| `eidolon-mobile` | 7,549 | Mobile client surface |
| `eidolon-core` | 3,833 | Shared core types and logic |

### pheno-compose
No `pheno-compose` crate is enumerated in the source atlas crate inventory.

| Crate | LOC | Purpose |
|---|---|---|
| UNKNOWN | UNKNOWN | Not listed in source inventory |

### sharecli
Terminal and fleet share layer (`sharecli*` = 12 crate dirs); largest non-agileplus family member.

| Crate | LOC | Purpose |
|---|---|---|
| `sharecli` | 90,061 | Main ShareCLI binary and command surface |
| `sharecli-fuse` | 7,879 | FUSE mount layer |
| `sharecli-ipc` | 4,700 | Inter-process messaging |
| `sharecli-session` | 4,194 | Session lifecycle management |
| `sharecli-fleet` | 3,685 | Fleet coordination |

