# Functional Requirements — Settly

## FR-CFG: Configuration Management

### FR-CFG-001: Config Loading
The system SHALL load configuration from TOML, YAML, and JSON files.
**Traces to:** E1.1
**Code Location:** `src/adapters/`

### FR-CFG-002: Environment Override
The system SHALL read environment variables with `SETTLY_` prefix and merge into config.
**Traces to:** E1.2
**Code Location:** `src/adapters/`

### FR-CFG-003: CLI Injection
The system SHALL accept CLI arguments and merge into config with highest priority.
**Traces to:** E1.3
**Code Location:** `src/application/`

## FR-LAYER: Layering System

### FR-LAYER-001: Priority Ordering
The system SHALL define layer priority: `default < file < env < CLI`.
**Traces to:** E2.1
**Code Location:** `src/domain/layer.rs`

### FR-LAYER-002: Deep Merge
The system SHALL perform deep merge of layered configs, with higher priority values overriding lower.
**Traces to:** E2.2
**Code Location:** `src/domain/`

### FR-LAYER-003: Conflict Detection
The system SHALL detect and report conflicting values across layers.
**Traces to:** E2.3
**Code Location:** `src/application/`

## FR-VAL: Validation

### FR-VAL-001: Schema Validation
The system SHALL validate configs against JSON Schema.
**Traces to:** E3.1
**Code Location:** `src/domain/validation.rs`

### FR-VAL-002: Custom Validators
The system SHALL support custom validator functions.
**Traces to:** E3.2
**Code Location:** `src/domain/validation.rs`

### FR-VAL-003: Error Reporting
The system SHALL provide detailed error messages with path to invalid field.
**Traces to:** E3.3
**Code Location:** `src/infrastructure/error.rs`

## FR-INT: Integration

### FR-INT-001: Serde Support
The system SHALL support Serde Serialize/Deserialize for all config types.
**Traces to:** E4.1
**Code Location:** `src/domain/`

### FR-INT-002: Type-Safe Access
The system SHALL provide type-safe getters for config values.
**Traces to:** E4.2
**Code Location:** `src/domain/config.rs`

### FR-INT-003: Hot Reload
The system SHALL optionally watch config files and reload on change.
**Traces to:** E4.3
**Code Location:** `src/adapters/`
