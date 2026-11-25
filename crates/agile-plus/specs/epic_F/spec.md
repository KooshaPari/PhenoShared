# DAG foundation + automation

**Epic:** epic_F
**Generated:** 2026-06-29T23:27:33Z
**Status:** Draft
**Type:** automation

## Overview

Foundation DAG epic covering DAG unit execution pipeline, manifest reading, and work-package generation for the compute/infra epic. Units are executed in topological order with validation and reporting.

## DAG Units

| Unit ID | Title | Type | Dependencies |
|---------|-------|------|--------------|
| F1 | DAG manifest schema and validator | automation | — |
| F2 | Wire DAG executor to agileplus | automation | F1 |

## Unit Details

### F1: DAG manifest schema and validator

Define and implement the DAG manifest JSON schema with validation for unit_ids, dependencies, and metadata. Includes schema documentation and unit tests.

#### Subtasks
- [ ] T001
- [ ] T002
- [ ] T003

---

### F2: Wire DAG executor to agileplus

Create run_dag_units.py that reads a DAG manifest, generates spec.md and work-package files following AgilePlus conventions, and validates no duplicate unit_ids.

#### Subtasks
- [ ] T004
- [ ] T005
- [ ] T006

---
