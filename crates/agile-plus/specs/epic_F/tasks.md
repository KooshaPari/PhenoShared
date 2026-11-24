# Work Packages: epic_F

**Generated:** 2026-06-29T23:27:33Z

## Summary

Total units: 2

| WP ID | Title | Type | Dependencies | Status |
|-------|-------|------|--------------|--------|
| F1 | DAG manifest schema and validator | automation | — | planned |
| F2 | Wire DAG executor to agileplus | automation | F1 | planned |

---

## Work Package F1: DAG manifest schema and validator

**Prompt:** `tasks/WPF1.md`

Define and implement the DAG manifest JSON schema with validation for unit_ids, dependencies, and metadata. Includes schema documentation and unit tests.

### Subtasks
- [ ] T001
- [ ] T002
- [ ] T003

---

## Work Package F2: Wire DAG executor to agileplus

**Prompt:** `tasks/WPF2.md`

Create run_dag_units.py that reads a DAG manifest, generates spec.md and work-package files following AgilePlus conventions, and validates no duplicate unit_ids.

### Subtasks
- [ ] T004
- [ ] T005
- [ ] T006

### Dependencies
- `F1`

---
