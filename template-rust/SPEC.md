# Rust Template Specification

> Project template specification

## Overview

Cookiecutter template for Rust projects.

## Structure

```
{{project_name}}/
├── src/
│   └── lib.rs
├── tests/
│   └── integration_tests.rs
├── .github/
│   └── workflows/
│       └── ci.yml
├── Cargo.toml
├── rustfmt.toml
├── clippy.toml
├── README.md
├── LICENSE
└── .gitignore
```

## Tools

- Cargo for build/package
- Clippy for linting
- rustfmt for formatting
- cargo-audit for security
- cargo-tarpaulin for coverage

## Variables

- `project_name` - Repository name
- `crate_name` - Rust crate name
- `description` - Project description
- `author` - Author name
- `email` - Author email
