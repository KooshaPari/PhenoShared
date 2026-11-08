# Functional Requirements — helix-logging

## FR-INIT-001
`Logger::init(config: LoggerConfig) -> Result<(), LogError>` SHALL set the global `log` logger.

## FR-INIT-002
`LoggerConfig` SHALL expose fields: `level: LevelFilter`, `format: OutputFormat`, `include_timestamps: bool`, `include_location: bool`.

## FR-LEVEL-001
The library SHALL support log levels: Trace, Debug, Info, Warn, Error via the `log` crate facade.

## FR-CID-001
`Logger::with_correlation_id(id: &str, f: impl FnOnce())` SHALL store the ID in thread-local storage for the duration of `f`.

## FR-CID-002
All log messages emitted within `with_correlation_id` scope SHALL include `"correlation_id": "<id>"` in JSON output.

## FR-JSON-001
JSON output SHALL include fields: `level`, `timestamp` (RFC 3339), `message`, `target`, and any key-value pairs.

## FR-JSON-002
JSON output SHALL be one object per line (NDJSON format).

## FR-TEXT-001
Text output SHALL include: `[LEVEL timestamp target] message`.

## FR-COMPAT-001
`helix-logging` SHALL implement `log::Log` so that `log::info\!()`, `log::warn\!()` etc. are captured.

## FR-ERR-001
`LogError` SHALL have variants: `AlreadyInitialised`, `InvalidConfig`.

## FR-BUILD-001
`cargo build` SHALL succeed with `edition = "2021"` or later.

## FR-TEST-001
`cargo test` SHALL pass.

## FR-TEST-002
At least one test SHALL verify that JSON output contains `correlation_id` field when set.

## FR-LINT-001
`cargo clippy -- -D warnings` SHALL exit 0.
