# template-lang-kotlin Specification

> Kotlin language layer templates composed on top of template-commons

## Overview

template-lang-kotlin provides Kotlin project scaffolding templates with Gradle build configuration, dependency management, and validation gates.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 template-lang-kotlin                              │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │   Scaffold   │ │   Build      │ │  Validation  │          │
│  │   Templates  │ │   Configs    │ │  Gates       │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Contract

| Field | Value |
|-------|-------|
| layer_type | language |
| language | Kotlin |
| build_system | Gradle (Kotlin DSL) |
| versioning | semver |

## Validation Gates

1. `gradle build` must succeed
2. `ktlint` must pass
3. `detekt` static analysis must pass
4. Test coverage > 80%
