# Worklog: phenotype-vessel

## Date: 2026-04-02

### Summary
Fixed compilation errors, lifetime issues, and test failures. All 13 tests pass with clippy clean.

### Changes Made

#### 1. Import Fixes (`src/client.rs:5`)
**Before:**
```rust
use super::{ContainerRuntime, ContainerInfo, ContainerCreateConfig, VesselError};
```

**After:**
```rust
use crate::runtime::{ContainerInfo, ContainerCreateConfig};
use super::{ContainerRuntime, VesselError};
```

Fixed module path resolution - types are in `crate::runtime`, not `super`.

#### 2. Lifetime Fixes (`src/compose.rs:92-116`)
**Before:**
```rust
fn visit(
    service_name: &str,
    services: &HashMap<String, ComposeService>,
    ordered: &mut Vec<&ComposeService>,
    visited: &mut std::collections::HashSet<&str>,
)
```

**After:**
```rust
fn visit<'a>(
    service_name: &'a str,
    services: &'a HashMap<String, ComposeService>,
    ordered: &mut Vec<&'a ComposeService>,
    visited: &mut std::collections::HashSet<&'a str>,
)
```

Added explicit lifetime parameter `'a` to ensure borrowed references live long enough.

#### 3. Temporary Value Lifetime (`src/runtime.rs`)
Changed `Vec<&str>` to `Vec<String>` in `create_container` methods for both Docker and Podman runtimes.

**Before:**
```rust
let mut args = vec!["create"];
args.push(&format!("{}={}", env.0, env.1));
```

**After:**
```rust
let mut args: Vec<String> = vec!["create".to_string()];
args.push(format!("{}={}", env.0, env.1));
```

This fixes the "temporary value dropped while borrowed" error.

#### 4. Default Derive (`src/compose.rs:22`)
**Before:**
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComposeService {
```

**After:**
```rust
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ComposeService {
```

Required for `ComposeService::default()` in tests.

#### 5. Doctest Fix (`src/lib.rs:15-21`)
**Before:**
```rust
//! let client = ContainerClient::new(DockerRuntime);
//! let image = client.pull_image("nginx:latest").await?;
//! let container = client.run(&image, "my-container").await?;
```

**After:**
```rust
//! # async fn quickstart() -> Result<(), Box<dyn std::error::Error>> {
//! let client = ContainerClient::new(DockerRuntime);
//! let image = client.pull_image("nginx:latest").await?;
//! let container = client.run("nginx:latest", "my-container").await?;
//! # Ok(())
//! # }
```

- Wrapped in async function
- Fixed `run()` call to use `&str` instead of `&Image`

#### 6. Clippy Fixes

**Redundant Closure (`src/client.rs:45`):**
```rust
// Before
.map_err(|e| VesselError::Runtime(e))?
// After
.map_err(VesselError::Runtime)?
```

**Derivable Default (`src/container.rs:49`):**
```rust
// Before: Manual impl Default
// After: #[derive(Default)]
```

### Verification Results

| Check | Status |
|-------|--------|
| `cargo check` | ✅ Pass |
| `cargo test` | ✅ 13 tests pass |
| `cargo clippy -- -D warnings` | ✅ Clean |

### Files Modified
- `src/client.rs` - Import paths
- `src/compose.rs` - Lifetime annotations, Default derive
- `src/runtime.rs` - String ownership fixes
- `src/container.rs` - Default derive
- `src/lib.rs` - Doctest fix

### Notes
- Container runtime integration requires Docker/Podman CLI
- All tests are unit tests; integration tests require container runtime
