# Phenotype.Validation - Rust

## Overview

Rust implementation of the Phenotype.Validation schema validation library.

## Installation

```toml
[dependencies]
phenotype-validation = "0.1.0"
```

## Quick Start

```rust
use phenotype_validation::JsonSchemaValidator;

let validator = JsonSchemaValidator::new();
let result = validator.validate(schema_json, document_json)?;
assert!(result.is_valid);
```

## License

MIT
