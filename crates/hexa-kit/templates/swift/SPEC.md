# Swift Template Specification

> Phenotype Template: Swift Template

**Version**: 1.0 | **Status**: Stable | **Last Updated**: 2026-04-02

## Overview

Template for Swift projects in the Phenotype ecosystem.

**Features**:
- Swift Package Manager
- Pre-configured CI/CD
- Standard tooling integration
- Documentation structure

## Quick Start

```bash
# Use template
copier copy gh:<REDACTED>/template-lang-swift ./my-project

# Or
mkdir my-project && cd my-project
curl -sL https://github.com/KooshaPari/template-lang-swift/archive/main.tar.gz | tar xz --strip-components=1
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
