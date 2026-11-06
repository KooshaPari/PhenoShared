# PLAN.md - PhenoProc

Process management registry for the Phenotype ecosystem.

## Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Core Process Management | 2 weeks | ProcessPool, ManagedProcess implementations |
| 2. Command Deduplication | 1 week | pheno-proc-dedup for dedup logic |
| 3. Priority Queue | 1 week | pheno-proc-queue for task queuing |
| 4. IPC Primitives | 2 weeks | Shared memory, Unix domain sockets |
| 5. Integration | 1 week | Wire into pheno CLI |

## Key Deliverables

- `pheno-proc-core` - ProcessPool, ManagedProcess
- `pheno-proc-dedup` - Command deduplication
- `pheno-proc-queue` - Priority task queue
- `pheno-proc-shm` - Shared memory IPC
- `pheno-proc-uds` - Unix domain sockets

## Resource Estimate

- **Dev time**: 7 person-weeks
- **Dependencies**: tokio, async-trait
- **Testing**: Unit + integration tests

---

Generated: 2026-04-03
