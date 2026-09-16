# Mojo Template Specification

> Phenotype Template: Mojo Template

**Version**: 1.0 | **Status**: Stable | **Last Updated**: 2026-04-02

## Overview

Template for Mojo projects in the Phenotype ecosystem.

**Features**:
- Modular AI project structure
- Pre-configured CI/CD
- Standard tooling integration
- Documentation structure

## Quick Start

```bash
# Use template
copier copy gh:<REDACTED>/template-lang-mojo ./my-project

# Or
mkdir my-project && cd my-project
curl -sL https://github.com/<REDACTED>/template-lang-mojo/archive/main.tar.gz | tar xz --strip-components=1
```

## Structure

```
my-project/
├── src/              # Source code
├── tests/            # Test files
├── docs/             # Documentation
├── .github/          # GitHub Actions
├── README.md         # Project README
└── LICENSE           # MIT License
```

## License

MIT
