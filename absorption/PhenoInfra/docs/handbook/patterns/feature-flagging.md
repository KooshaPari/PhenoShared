# Feature Flagging Pattern

**Status:** adopted · **Applies to:** every task assigned to a subagent (codex-spark, thegent, codex) that asks the subagent to *modify* an existing struct field, config entry, or typed value, when the subagent comes back with a "false premise" verdict (the existing field does not have the role, the shape, or the type the task assumed).

## Overview

The fleet runs on greenfield tasks. A "greenfield" task in this handbook means a task whose deliverable is *purely additive*: a new struct field, a new optional config entry, a new variant on a closed enum, a new method on an existing type, a new crate member, a new endpoint. A greenfield task has no migration cost, no backwards-compatibility clause, no "while we're here" refactor, and no dead-code-cleanup obligation. The deliverable lands, the test suite turns green, the PR is one diff, and the blast radius is the *new* surface area only.

The opposite — the **brownfield** task — asks a subagent to modify an existing field's type, role, or wrapping. A brownfield task has a blast radius: existing call sites, the wire format, derived `Debug` / `Serialize` / `Display` implementations, panic messages, log lines, config-file parsers, and any persisted state all have to be considered. Brownfield tasks are the workhorse of large refactors, but they are the *wrong* tool for the recurring subagent loop the org runs in waves 4+5.

The failure mode this page exists to prevent is the **brownfield reflex**: a subagent is assigned a task shaped like "modify field X to have shape Y" (e.g., "wrap `ServerConfig::token` in `phenotype_secret::Secret` so the bearer token stops leaking through `format!`"), the subagent comes back with "false premise — `ServerConfig` has no field named `token`," and the orchestrator pushes back, asks the subagent to look again, or refactors whichever field is closest to the desired role. The push-back path is wrong: the subagent's "false premise" verdict is the greenfield-task trigger, not a dispute to resolve. Pivot to the greenfield task (add a new field with the desired shape, leave the existing fields alone), ship the additive PR, and continue the wave.

> **Scope note.** This page is the *workflow* rule for handling a subagent's "false premise" verdict on a *field-addition* task. The *field-level contract* for the wrappers themselves (e.g., the `Display` / `Debug` / `Serialize` invariants of `phenotype_secret::Secret`) lives on the per-primitive pattern docs (see [secrets](secrets.md)). The *delegation* rule for the subagent itself — the part that says "use codex-spark first, give it a disjoint fileset, work in a per-worker worktree, never stash" — lives at [delegation/codex-first](delegation/codex-first.md). This page is the bridge between the two: when the subagent's "false premise" report comes back, the orchestrator's response is the greenfield pivot documented here.

## The Rule

When a subagent reports a "false premise" verdict on a task that asked it to *modify* an existing field, config entry, or typed value, the orchestrator pivots to a **greenfield task** in the same wave. The pivot has exactly three moves, in this order, no substitutions:

| Move | Action | Why |
|------|--------|-----|
| 1. Accept the verdict. | The orchestrator treats the subagent's "false premise" report as authoritative. No re-investigation, no "are you sure?", no push-back. The subagent ran the same toolchain the orchestrator would have run; the verdict stands. | A false-premise push-back loop burns a subagent turn, a worker context, and a wave slot, and almost always returns the same verdict on the second pass. The pivot costs one PR; the push-back loop costs one PR plus one turn. |
| 2. Re-shape the task as a greenfield addition. | The deliverable becomes "add a new field named `<role>` of type `Option<T>` (or the closest equivalent for the role) at the right struct / config / enum, with the *desired* shape, wrapping, and security posture from day 1." The existing fields are *not* part of the deliverable. | A greenfield addition has zero blast radius. Existing call sites, the wire format, derived impls, and persisted state are untouched. The new field is born correct: the wrapper, the `Option`-ness, the `#[serde(skip_serializing_if = "Option::is_none")]` annotation, the `Display` / `Debug` redaction, the env-var precedence — all decided once, on day 1, by the orchestrator, not by a series of field-level refactors. |
| 3. Land the additive PR. | The new field is wired through the constructors, the config loader, the env-var precedence (where applicable), the test helpers, and the integration tests in the same diff. The `Default` impl (where applicable) sets the new field to the safe-by-default value (`None` for `Option<T>`, the closed-enum's `Disabled` variant for a feature flag, etc.). | The new field is a *contract marker*: its presence on the struct tells the reviewer "this struct now has a feature that can be turned on"; its `None` / disabled default tells the reviewer "this feature is off by default, opt-in per deployment." The marker is the pattern. |

**Hard rule:** the pivot is *additive only*. The orchestrator does not "while-we're-here" refactor the existing field that the task was originally about. The existing field is left exactly as it was — same type, same role, same default, same accessors, same test surface. If the existing field is provably dead code (no call sites, no consumers, no wire-format role, no test references), the deletion is a *separate* PR with its own subagent task and its own false-premise-or-not verdict. The deletion is never bundled into the greenfield addition.

**Hard rule:** the new field is added with the *desired* type, wrapper, and security posture on day 1 — not with the existing field's type as a starting point and a "TODO: wrap in Secret" follow-up. The whole point of the pivot is to avoid the field-level refactor chain ("add field, then wrap it, then redact its `Display`, then add the env-var loader, then …"). The new field is born with the full contract; the PR is one diff, not a series.

**Hard rule:** the new field's type is `Option<T>` (or `#[serde(default)]` with a safe default) when the feature is *opt-in per deployment*. The `Option`-ness is the feature flag. A non-optional field that is set to a placeholder value (`String::new()`, `0`, `false`) is a violation: it forces every deployment to invent a placeholder and silently ships a footgun in the deployments that forget. The `Option<T>` is the pattern; the absence of the value is the off-state; the presence is the on-state.

**Hard rule:** the greenfield task is *not* a "wrap an existing field" task in disguise. If the orchestrator is tempted to phrase the new task as "take the existing `api_key: String` field and *also* add an `auth_token: Option<Secret<String>>` field, then migrate consumers one by one," the orchestrator has re-entered the brownfield pattern and the pivot has failed. The new field is independent of the old field; consumers opt into the new field on their own schedule; the old field is left for its own brownfield refactor PR (which may never happen, and that is fine).

**Hard rule:** the subagent that reports the "false premise" is the *same* subagent that gets the greenfield task. Re-dispatching to a different subagent (or a different worker context) burns the worker's disjoint-fileset assumption and re-loads the codebase for a task that is a one-line PR. The same subagent picks up the pivoted task in the same worker context and ships the addition.

**Hard rule:** the orchestrator logs the pivot. The commit message, the PR description, or the wave-status note records "originally asked subagent to refactor field X; subagent reported false premise; pivoted to greenfield addition of field Y." The log entry is the audit trail for the next wave's orchestrator, who will see the new field on the struct and wonder why two fields with overlapping roles coexist. The log entry answers the question before it is asked.

## Canonical Pattern

### A. The subagent's "false premise" report (the trigger)

```text
// subagent returns:
verdict: false_premise
reason: "ServerConfig has no field named `token`. The struct has
        socket_path, tcp_port, tcp_only, and stats_interval. None of
        these match the bearer-token role the task assumed."
        // (excerpted from a codex-spark verdict in wave 4)
```

The orchestrator reads the verdict, does *not* push back, and re-shapes the task as a greenfield addition. The next subagent prompt is the pivot, not a re-investigation.

### B. The pivoted task (the greenfield addition)

```text
// orchestrator re-prompts the same subagent in the same worker context:
task: "Add an `auth_token: Option<Secret<String>>` field to
       `ServerConfig` in `phenotype-daemon/src/main.rs`. The field is
       the bearer token for incoming connections; wrapping it in
       `phenotype_secret::Secret` keeps the value out of `format!`,
       `tracing::info!`, `serde_json::to_string`, derived `Debug`,
       and panic messages. Wire the field through:
         1. The struct definition (new field, doc comment, no
            `#[serde(...)]` attribute that would leak the value).
         2. The `Default` impl (set to `None`).
         3. The env-var loader (read `PHENOTYPE_DAEMON_AUTH_TOKEN`
            and wrap in `Secret::from`).
         4. The test helper (pass `None` to preserve the
            unauthenticated default behaviour).
       Do NOT touch the existing `socket_path`, `tcp_port`,
       `tcp_only`, or `stats_interval` fields. Do NOT bundle a
       refactor of any other field. The PR is purely additive.
       cargo check + cargo test on phenotype-daemon both pass."
```

The prompt is the contract: additive, scoped, the four wiring surfaces named, the existing fields explicitly off-limits, the greenfield discipline stated.

### C. The additive diff (the landed PR)

```rust
// phenotype-daemon/Cargo.toml               (the new dep — one line)
//
// Redaction-aware Secret<String> wrapper shared by every Pheno* crate.
// Used here for ServerConfig::auth_token so bearer tokens never leak
// through format!, tracing::info!, serde_json::to_string, panic
// messages, or derived Debug.
+phenotype-secret = { path = "../../phenoShared/crates/phenotype-secret" }
```

```rust
// phenotype-daemon/src/main.rs               (the new field — additive)
//
+use phenotype_secret::Secret;
+
 struct ServerConfig {
     socket_path: PathBuf,
     tcp_port: u16,
     tcp_only: bool,
+    /// Optional bearer token required to authenticate incoming
+    /// connections. Wrapped in [`Secret`] so accidental `format!`,
+    /// `tracing::info!`, or `serde_json::to_string` calls redact the
+    /// value rather than leaking it through logs / errors / config
+    /// dumps.
+    auth_token: Option<Secret<String>>,
 }

 impl Default for ServerConfig {
     fn default() -> Self {
         Self {
             socket_path: PathBuf::from(DEFAULT_SOCKET_PATH),
             tcp_port: DEFAULT_TCP_PORT,
             tcp_only: cfg!(windows),
+            auth_token: None,
         }
     }
 }
```

```rust
// phenotype-daemon/src/main.rs               (the env-var loader — additive)
//
 impl ServerConfig {
     pub fn from_env() -> Result<Self, ConfigError> {
+        let auth_token = std::env::var("PHENOTYPE_DAEMON_AUTH_TOKEN")
+            .ok()
+            .map(Secret::from);
         Ok(Self {
             socket_path: std::env::var("PHENOTYPE_DAEMON_SOCKET_PATH")
                 .map(PathBuf::from)
                 .unwrap_or_else(|_| PathBuf::from(DEFAULT_SOCKET_PATH)),
             tcp_port: parse_port("PHENOTYPE_DAEMON_TCP_PORT", DEFAULT_TCP_PORT)?,
             tcp_only: parse_bool("PHENOTYPE_DAEMON_TCP_ONLY", cfg!(windows))?,
+            auth_token,
         })
     }
 }
```

The diff is purely additive: one new dep line, one new `use`, one new struct field with doc comment, one new field in `Default`, one new field in the env-var loader. The four existing fields are byte-identical. The blast radius is the *new* surface area (the `auth_token` field, the `PHENOTYPE_DAEMON_AUTH_TOKEN` env var, the `Secret::from` wrapper); the *existing* surface area (the four untouched fields, the existing env vars, the wire format of any persisted config) is zero.

### D. The "forward-looking" variant (the new field without a current consumer)

The Eidolon variant of the pivot adds a new field *without* a current consumer: the field is a placeholder for a future integration that the implementer has not yet built. The new field is still additive; the wiring surfaces are smaller (no env-var loader, no test helper for the field itself), but the discipline is the same:

```rust
// crates/eidolon-mobile/src/lib.rs         (the forward-looking field)
//
 pub struct MobileClient {
     #[allow(dead_code)]
     platform: String,
+    /// Optional client credential used for upstream authentication
+    /// (e.g. iOS Xcode Test Manager, Android UiAutomator bridges).
+    /// Wrapped in `phenotype_secret::Secret` so accidental `format!`,
+    /// `dbg!`, or `serde_json::to_string` calls cannot leak the value
+    /// to logs or wire payloads.
+    ///
+    /// **Forward-looking.** The field is `None` for unauthenticated
+    /// local automation; the iOS / Android implementer passes
+    /// `Some(Secret)` when integrating with a remote device farm
+    /// that requires a bearer token. The field exists on the struct
+    /// from day 1 so the wrapper's `Display` / `Debug` / `Serialize`
+    /// invariants are enforced by the type system before the
+    /// consumer is built.
+    #[allow(dead_code)]
+    client_secret: Option<phenotype_secret::Secret<String>>,
 }

 impl MobileClient {
-    pub fn new(platform: &str) -> Self {
-        Self { platform: platform.to_string() }
+    pub fn new(
+        platform: &str,
+        client_secret: Option<phenotype_secret::Secret<String>>,
+    ) -> Self {
+        Self {
+            platform: platform.to_string(),
+            client_secret,
+        }
     }
 }
```

```rust
// crates/eidolon-mobile/tests/test_mobile.rs   (the test helper update)
//
 fn make_client(platform: &str) -> Arc<dyn MobileAutomator> {
-    Arc::new(MobileClient::new(platform))
+    Arc::new(MobileClient::new(platform, None))
 }
```

The `#[allow(dead_code)]` on the field is the explicit acknowledgement that the field has no current consumer; the doc comment's **Forward-looking.** callout is the audit trail for the next reviewer who wonders why the field exists. The `None` in the test helper is the feature flag's off-state: the field is present on the struct (the marker says "this struct supports the feature"), the value is `None` (the marker says "this test does not exercise the feature"). Both markers are the pattern.

> **Hard rule for the forward-looking variant.** The `#[allow(dead_code)]` and the **Forward-looking.** doc comment are *required*, not optional. They are the audit trail: a future reviewer (or a future clippy run with `#![deny(dead_code)]`) needs to be able to tell, from the source alone, that the field's emptiness is deliberate. A bare `#[allow(dead_code)]` with no doc comment is a violation; a doc comment with no `#[allow(dead_code)]` is a violation (clippy will fail the build before the comment is read).

## Reference

The two waves-4+5 lifts that anchor the rule, in chronological order. Each lift is a single PR, purely additive, with the subagent's "false premise" verdict as the trigger and the greenfield pivot as the response. The "Origin consumer" column is the struct / config that received the new field; the "Field added" column is the new field's name, type, and wrapper; the "Old fields touched" column is the proof that the pivot stayed additive (it should read "none" in every row).

| Wave | Repo · PR | Origin consumer | Field added | Wrapper / posture | Old fields touched | Notes |
|------|-----------|----------------|-------------|-------------------|--------------------|-------|
| 4 | PhenoAgent · `8f0e288` (phenotype-daemon: add auth_token to ServerConfig) | `phenotype_daemon::ServerConfig` | `auth_token: Option<Secret<String>>` | `phenotype_secret::Secret` (Display / Debug / Serialize → `[REDACTED]`); env-var loader reads `PHENOTYPE_DAEMON_AUTH_TOKEN`; `Default = None` | **none** (the four pre-existing fields — `socket_path`, `tcp_port`, `tcp_only`, `stats_interval` — are byte-identical) | The canonical wave-4 example. The subagent's "false premise" verdict was on a task that asked it to *wrap the existing token field*; the pivot added `auth_token` as a new field with the wrapping on day 1. `cargo check + cargo test` on `phenotype-daemon` both pass (15 tests). |
| 5 | Eidolon · `2b95264` (feat(eidolon-mobile): wire phenotype-secret as forward-looking credential) | `eidolon_mobile::MobileClient` | `client_secret: Option<phenotype_secret::Secret<String>>` | `phenotype_secret::Secret` (same redaction invariants as PhenoAgent); `MobileClient::new` takes the secret as an optional second argument; `Default = None` | **none** (the pre-existing `platform: String` field is byte-identical) | The forward-looking variant. The field is `#[allow(dead_code)]` with a **Forward-looking.** doc comment because the iOS / Android implementer has not yet built the consumer; the field exists on the struct from day 1 so the wrapper's invariants are enforced by the type system before the consumer lands. The test helper passes `None` to preserve the unauthenticated local-automation behaviour. |

### Anti-patterns the rule rejects

The following three shapes are *not* the greenfield pivot and are rejected on sight by the orchestrator:

1. **The push-back loop.** Re-dispatching the same task to the same or a different subagent with a "are you sure?" or "look again" framing. The subagent's verdict is authoritative; the loop burns a turn and almost always returns the same verdict.
2. **The "wrap the closest existing field" pivot.** Adding the new field but also re-shaping the existing field that the task was originally about (e.g., changing `api_key: String` to `api_key: Secret<String>` in the same PR). The existing field's refactor is a *separate* brownfield PR with its own subagent task; bundling the two defeats the additive discipline.
3. **The "placeholder value" non-`Option` field.** Adding the new field as `auth_token: String = String::new()` (or `0`, or `false`) instead of `auth_token: Option<Secret<String>>`. The placeholder is a footgun: deployments that forget to set the env var get an empty string passed to a credential-checking code path, which either silently authenticates as "anonymous" or panics on the first request. The `Option<T>` is the pattern; the `None` default is the safe-by-default behaviour.

### Related patterns

- [secrets](secrets.md) — the `phenotype_secret::Secret` wrapper contract (`Display` / `Debug` / `Serialize` → `[REDACTED]`, single auditable accessor `expose()`) that the new field in both reference rows wraps the credential in.
- [service-integration](service-integration.md) — the four-line `main.rs` recipe that the greenfield addition sits one layer below; the new field is consumed by the `init_tracing` / `build_default_client` / `Secret::from` / `TokenBucket::new` wiring, and the `Option<None>` placeholder for credentials (step 3 of the recipe) is exactly the off-state of the feature flag.
- [module-decoupling](module-decoupling.md) — the producer-side lift rule that brought `phenotype-secret` into `phenoShared` in the first place; the greenfield additions documented here are the *consumer-side* moves that wire the lifted crate into a new struct.
- [delegation/codex-first](delegation/codex-first.md) — the subagent rule that produces the "false premise" verdict in the first place (codex-spark first, disjoint filesets, per-worker worktrees, never stash); this page is the orchestrator-side response to the verdict.
