# DEPENDENCIES.md Standard Template

**Purpose**: Every project must declare its dependencies for traceability and maintenance.

## Required Sections

### 1. Direct Dependencies (Internal)

Phenotype workspace crates this project directly uses:

```markdown
## Direct Dependencies

| Crate/Project | Purpose | Version Constraint |
|---------------|---------|-------------------|
| phenotype-error-core | Error handling types | ^0.2.0 |
| phenotype-logging | Structured logging | ^0.2.0 |
| phenotype-config-core | Configuration | ^0.2.0 |
```

### 2. Workspace Dependencies

Paths to local workspace dependencies:

```markdown
## Workspace Dependencies

```
../crates/phenotype-error-core
../crates/phenotype-logging
```
```

### 3. External Dependencies

Key external crates/libraries:

```markdown
## External Dependencies

| Crate/Library | Purpose | Version |
|---------------|---------|---------|
| serde | Serialization | ^1.0 |
| tokio | Async runtime | ^1.0 |
| thiserror | Error derive | ^1.0 |
| anyhow | Error handling | ^1.0 |
```

### 4. Platform Dependencies

For platform-level projects:

```markdown
## Platform Dependencies

| Platform | Integration Point |
|----------|------------------|
| AgilePlus | Queue integration |
| thegent | Agent orchestration |
```

### 5. Dev/Test Dependencies

```markdown
## Development Dependencies

| Tool/Crate | Purpose |
|------------|---------|
| phenotype-test-fixtures | Test utilities |
| tokio-test | Async testing |
| mockall | Mocking |
```

## Optional Sections

### Dependency Update Policy

```markdown
## Update Policy

- **Critical security patches**: Within 24 hours
- **Minor updates**: Weekly batch
- **Major updates**: Quarterly review with ADR
```

### Known Constraints

```markdown
## Constraints

- Locked to tokio 1.x until ecosystem upgrades
- serde pinned for binary compatibility
```

## Validation

Checklist:
- [ ] All direct deps listed with versions
- [ ] Workspace paths verified
- [ ] External deps have version constraints
- [ ] Dev deps separated from runtime deps
- [ ] No orphaned dependencies

## Example: Complete DEPENDENCIES.md

See `template-commons/templates/DEPENDENCIES.md.example`
