# NFR-AP-001..004: Traceability and Verification Requirements

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2026-06-16  

## Overview

This document specifies the non-functional requirements (NFRs) governing traceability, verification, and bidirectional linking between AgilePlus domain entities and external traceability systems (primarily Tracera).

**Key Principle:** Every artifact in the system must be traceable to requirements and verified against evidence. Stories cannot reach "Done" without acceptance contracts; criteria cannot be marked "Verified" without external evidence links.

---

## NFR-AP-001: Acceptance Contract Requirement for Story Completion

**Requirement:** Every Story must have at least one AcceptanceContract before transitioning to "Done" status.

### Rationale

- Prevents incomplete acceptance criteria from being hidden
- Ensures explicit definition of "Done" for each story
- Enables verification step before story closure
- Supports planning poker and story refinement workflows

### Specification

| Aspect | Detail |
|--------|--------|
| **Scope** | Story.transition_status(StoryStatus::Done) |
| **Trigger** | Story attempting transition from Review→Done, InProgress→Done, or any→Done |
| **Rule** | If attempted transition target is `Done`, verify: (a) AcceptanceContract exists for story_id, AND (b) AcceptanceContract.lifecycle_status == `Verified` |
| **Enforcement** | Domain layer (Story aggregate) checks before state transition; returns `DomainError::InvalidTransition` with reason "story requires verified acceptance contract" |
| **Scope Exception** | Stories in `Cancelled` status do NOT require acceptance contracts (terminal state without contract) |

### Acceptance Criteria

- [ ] Story.transition_status(Done) rejects if no AcceptanceContract exists
- [ ] Story.transition_status(Done) rejects if AcceptanceContract.lifecycle_status != Verified
- [ ] Story.transition_status(Done) accepts if AcceptanceContract.lifecycle_status == Verified
- [ ] Story.transition_status(Cancelled) succeeds regardless of AcceptanceContract state
- [ ] Blocked/Review stories may exist without verified contracts (only Done requires it)
- [ ] Error message clearly indicates missing/unverified contract

### Verification Method

```
1. Create a Story in Todo status (no contract required at creation)
2. Attempt Story.transition_status(Done) → Verify rejection with clear error
3. Create AcceptanceContract with Draft status
4. Attempt Story.transition_status(Done) → Verify rejection (contract not Verified)
5. Transition AcceptanceContract to Verified (all criteria marked Verified)
6. Attempt Story.transition_status(Done) → Verify success
7. Test Story.transition_status(Cancelled) → Verify success regardless of contract
```

### Implementation Notes

- Acceptance contract check happens at transition time, not creation time
- Query: `SELECT AcceptanceContract WHERE story_id = ? AND lifecycle_status = 'verified' LIMIT 1`
- Error: Include story_id and contract count in error message for debugging

---

## NFR-AP-002: Evidence Requirement for Acceptance Criteria Verification

**Requirement:** All AcceptanceCriteria must be linked to at least one external traceability artifact (Tracera evidence) before being marked "Verified".

### Rationale

- Creates immutable audit trail (evidence artifact is source of truth)
- Prevents manual approval without supporting documentation
- Enables traceability back to test cases, bug reports, requirements
- Supports governance and compliance workflows

### Specification

| Aspect | Detail |
|--------|--------|
| **Scope** | AcceptanceCriteria.transition(VerificationStatus::Verified) |
| **Trigger** | Attempting to mark criterion as Verified |
| **Rule** | If target status is `Verified`, verify: (a) AcceptanceCriteria.trace_ref_ids is non-empty, AND (b) All referenced trace IDs resolve in Tracera (via TraceabilityPort.get_traces()) |
| **Enforcement** | Domain layer checks before verification; returns error if no trace_refs or Tracera resolution fails |
| **Scope Exception** | Criteria in `Pending` or `Unverified` status may exist without trace_refs; only Verified requires them |

### Specification Details

**Minimum Linking Rule:** Each criterion must have ≥1 `trace_ref_id` before verification.

**Valid Evidence Types (artifact_type in TraceRef):**
- `evidence` — Test result, screenshot, log, execution trace
- `test_case` — Test specification or test automation run
- `issue` — GitHub issue, PR comment, bug tracker link
- `specification` — Detailed spec section or design doc
- `commit` — Git commit SHA confirming implementation

**Resolution Validation:**
- TraceabilityPort.get_traces(criterion_entity_id) must return non-empty Vec<TraceRef>
- If Tracera is unavailable (network error), defer verification with clear error
- If trace_ref_id does not exist in Tracera, reject with "trace not found" error

### Acceptance Criteria

- [ ] AcceptanceCriteria.transition(Verified) rejects if trace_ref_ids is empty
- [ ] AcceptanceCriteria.transition(Verified) rejects if any trace_ref_id does not resolve in Tracera
- [ ] AcceptanceCriteria.transition(Verified) accepts if ≥1 valid trace_ref exists and resolves
- [ ] AcceptanceCriteria.transition(Unverified/Pending) succeeds regardless of trace_refs
- [ ] Error message includes missing trace_id and artifact details for debugging
- [ ] Tracera unavailability is surfaced as `Err(String)` not silent failure

### Verification Method

```
1. Create AcceptanceCriteria with empty trace_ref_ids
2. Attempt criterion.transition(Verified) → Verify rejection
3. Create TraceRef in Tracera (e.g., test case TC-101)
4. Link trace_ref_id = "TC-101" to AcceptanceCriteria
5. Call TraceabilityPort.get_traces(criterion_id) → Mock returns [TraceRef { trace_id: "TC-101", ... }]
6. Attempt criterion.transition(Verified) → Verify success
7. Remove trace_ref_id and attempt transition → Verify rejection
```

### Implementation Notes

- TraceRef linking is idempotent; multiple refs per criterion are allowed
- Query: `SELECT trace_ref_ids FROM AcceptanceCriteria WHERE id = ?`
- Resolution is async; callers must await TraceabilityPort.get_traces()
- On successful transition, set verification_time and verifier_id (audit trail)

---

## NFR-AP-003: Bidirectional Traceability Linking

**Requirement:** All TraceRef links must be bidirectional; the external traceability system (Tracera) must independently confirm the link back to AgilePlus.

### Rationale

- Prevents orphaned links (AgilePlus claims link Tracera doesn't know about)
- Enables round-trip consistency checks
- Supports document regeneration (Tracera can export all AgilePlus references)
- Ensures referential integrity across system boundaries

### Specification

| Aspect | Detail |
|--------|--------|
| **Scope** | TraceRef creation and usage |
| **Trigger** | Creating or reading a TraceRef link |
| **Rule** | When linking AgilePlus entity to external artifact: (a) Create TraceRef in AgilePlus, (b) Call TraceabilityPort.link_trace() to notify Tracera, (c) Verify Tracera responds with confirmation, (d) Only on success, persist TraceRef locally |
| **Query Rule** | When reading traceability: (a) Query AgilePlus TraceRefs, (b) Call TraceabilityPort.get_traces() to verify Tracera still knows about the link, (c) Flag stale links (Tracera says no) for audit |
| **Enforcement** | Persistence and query adapters implement bidirectional checks; return error if Tracera doesn't confirm |
| **Scope Exception** | NoopTraceAdapter (testing, local mode) skips Tracera confirmation |

### Linking Lifecycle

```
AgilePlus                                Tracera
---------                                -------
Entity created (id=42)
    |
    +-- TraceRef creation requested
            |
            +-- Call TraceabilityPort.link_trace(entity_id=42, trace_ref={trace_id:"FR-001"})
                    |
                    +-- Tracera receives notification
                        |
                        +-- Create back-reference: FR-001 → AgilePlus:Story:42
                        |
                        +-- Return Ok(()) confirmation
                    |
                    +-- Persist TraceRef locally
                    |
                    +-- Emit "traceability-linked" event

Later: AgilePlus queries traceability
    |
    +-- Call TraceabilityPort.get_traces(entity_id=42)
            |
            +-- Tracera looks up back-references for Story:42
            |
            +-- Returns [TraceRef { trace_id: "FR-001", ... }]
            |
            +-- Check: AgilePlus local TraceRef matches Tracera response?
            |   YES → Link is valid
            |   NO  → Stale link warning (investigate)
```

### Bidirectional Validation Rules

1. **On Creation:** TraceRef.link_trace() must return success before local persistence
2. **On Query:** Mismatch between AgilePlus and Tracera TraceRefs logged as audit event
3. **Stale Link Detection:** If AgilePlus has TraceRef but Tracera.get_traces() doesn't return it:
   - Log warning: `stale_trace_detected { story_id: 42, trace_id: "FR-001" }`
   - Include in reports as "Dangling Reference"
   - Do NOT auto-delete (require manual reconciliation)
4. **Orphaned Requirement:** If Tracera requirement is deleted but AgilePlus still references it:
   - TraceabilityPort.get_traces() returns empty for that entity
   - Update affected entity status to "Orphaned" (special flag)
   - Notify product/PM for decision

### Acceptance Criteria

- [ ] TraceRef.link_trace() succeeds and Tracera confirms back-reference
- [ ] TraceRef.link_trace() fails if Tracera doesn't confirm (returned error)
- [ ] TraceRef not persisted to AgilePlus if Tracera confirmation fails
- [ ] TraceabilityPort.get_traces() returns linked TraceRefs from Tracera
- [ ] Mismatch detection logs warning if AgilePlus and Tracera diverge
- [ ] Stale links flagged in UI and reports (not silently ignored)
- [ ] NoopTraceAdapter passes bidirectional checks for local testing

### Verification Method

```
1. Mock Tracera TraceabilityPort to return success on link_trace()
2. Create TraceRef { entity_id: 42, trace_id: "FR-001" }
3. Call link_trace() → Verify Tracera confirmation received
4. Persist TraceRef locally
5. Later: Call get_traces(42) → Mock Tracera returns [TraceRef{trace_id:"FR-001"}]
6. Verify: AgilePlus TraceRef ⊆ Tracera response (bidirectional match)
7. Test stale link: Mock Tracera returns empty for entity_id 42
8. Verify: Audit log shows "stale_trace_detected"
9. Test Tracera unavailable: Mock link_trace() returns Err("network timeout")
10. Verify: TraceRef not persisted; error bubbled to caller
```

### Implementation Notes

- TraceRef linking is transactional (link_trace + persist or rollback)
- Mismatch detection runs in background audits, not on every read
- Bidirectional check is a "soft" guard (warns, doesn't block); use for governance reporting
- Stale link count in project/story dashboards enables holistic view

---

## NFR-AP-004: Traceability Reference Validation

**Requirement:** All external traceability references (requirement_id, trace_ref_id, plane_issue_id) must be validated against their source systems before acceptance.

### Rationale

- Prevents broken links (typos, deleted requirements)
- Enables early detection of synchronization failures
- Supports imports and bulk updates

### Specification

| Aspect | Detail |
|--------|--------|
| **Scope** | Setting requirement_id on Epic/Story; creating TraceRef; linking Plane issue |
| **Rule** | Before persisting reference: Call source system (Tracera, Plane) to verify artifact exists; on failure, return error with context |
| **Lazy Validation** | Validation deferred to persistence adapter (not domain layer) to allow testing with NoopTraceAdapter |
| **Async** | Validation is async (network I/O); adapters return `async fn` results |

### Reference Types

| Reference | Source | Validation Method |
|-----------|--------|-------------------|
| Epic.requirement_id | Tracera | Query Tracera for requirement ID (FR/NFR format) |
| Story.requirement_id | Tracera | Query Tracera for requirement ID |
| TraceRef.trace_id | Various | Query appropriate system (Tracera, GitHub, Plane) |
| WorkPackage.plane_sub_issue_id | Plane | Query Plane API for sub-issue |
| Feature.plane_issue_id | Plane | Query Plane API for issue |

### Validation Rules

- **Duplicate Prevention:** Check for existing reference before creating new one
- **Format Validation:** Basic regex before system lookup (e.g., FR-\d+ for Tracera)
- **System Availability:** If source system unavailable, log warning but allow persistence (soft validation)
- **Deletion Handling:** If requirement is later deleted in Tracera, update related entities to "orphaned" state

### Acceptance Criteria

- [ ] Epic.requirement_id is validated against Tracera before persistence
- [ ] Story.requirement_id is validated against Tracera before persistence
- [ ] TraceRef.trace_id is validated against source system before persistence
- [ ] Invalid references rejected with clear error message (missing artifact ID, format issue)
- [ ] Duplicates rejected with informative message
- [ ] System unavailability logged but doesn't block persistence (soft guard)
- [ ] Orphaned references (deleted in source) are flagged in UI and reports

### Verification Method

```
1. Create Epic with invalid requirement_id = "INVALID-9999"
2. Attempt persistence → Call Tracera validation
3. Mock Tracera returns 404 for "INVALID-9999"
4. Verify: Persistence rejected with "Tracera requirement not found"
5. Create Epic with valid requirement_id = "FR-001"
6. Mock Tracera returns 200
7. Verify: Epic persisted with requirement_id set
8. Test system unavailable: Mock Tracera timeout
9. Verify: Warning logged; persistence proceeds (soft validation)
```

### Implementation Notes

- Validation calls happen in persistence adapters, not domain
- NoopTraceAdapter accepts all references (no validation)
- Bulk imports use batch validation API if available
- Stale reference detection runs nightly as cleanup job

---

## Traceability Audit Report

**Requirement:** The system must generate a traceability audit report showing:
- All entities with requirement_id links
- All criteria with evidence links
- Stale/orphaned references
- Bidirectional link mismatches

### Report Format

```
# Traceability Audit Report
Generated: 2026-06-16 14:32:00 UTC

## Summary
- Epics: 42 total, 40 linked (95%)
- Stories: 128 total, 125 linked (98%)
- Criteria: 256 total, 240 verified (94%)
- Stale Links: 3
- Orphaned References: 1

## Linked Entities
### Epics
- EP-001 (Linked: FR-042)
- EP-002 (Linked: FR-043, FR-044)
...

### Stories
- ST-001 (Linked: FR-042, Criteria: 3/3 verified)
...

## Stale Links
- Story:ST-042 → FR-999 (Not found in Tracera)
- WorkPackage:WP-003 → GH#12345 (PR closed without merge)

## Orphaned References
- Epic:EP-005 → FR-888 (Requirement deleted in Tracera)

## Bidirectional Mismatches
- Story:ST-050: AgilePlus has 2 refs, Tracera knows of 1 (investigation needed)
```

### Report Generation

| Metric | Method | Frequency |
|--------|--------|-----------|
| **Link Coverage** | COUNT(entities WITH requirement_id) / COUNT(entities) | Daily |
| **Verification Coverage** | COUNT(criteria.verified) / COUNT(criteria) | Daily |
| **Stale Detection** | Mismatch between AgilePlus TraceRefs and Tracera.get_traces() | Nightly |
| **Orphaned Detection** | Tracera requirement not found for epic/story requirement_id | Nightly |

---

## Cross-Cutting Concerns

### Error Handling

All traceability operations return explicit errors:

```rust
pub enum TraceabilityError {
    NotFound(String),          // Artifact doesn't exist in external system
    InvalidFormat(String),     // ID format invalid
    BidirectionalMismatch { entity_id, trace_id }, // Link confirmed only one-way
    SystemUnavailable(String), // Tracera/Plane API down
    Unauthorized(String),      // Auth failed
}
```

### Telemetry

- **link_trace_duration_ms** — Time to confirm bidirectional link
- **trace_resolution_latency_ms** — Time to resolve TraceRef
- **stale_link_count** — Count of orphaned references
- **verification_coverage_pct** — % of criteria verified

### Deprecation

Future versions may:
- Auto-delete stale links after N days (requires policy setting)
- Require bidirectional checks (hard, not soft validation)
- Archive orphaned entities automatically

---

## Implementation Guidance

### Order of Implementation

1. **Phase 1 (MVP):** Acceptance contracts required for Done (NFR-AP-001)
2. **Phase 2:** Evidence requirement for verification (NFR-AP-002)
3. **Phase 3:** Bidirectional checking (NFR-AP-003)
4. **Phase 4:** Reference validation + audit reports (NFR-AP-004)

### Testing Strategy

- **Unit tests:** Mock TraceabilityPort for each NFR
- **Integration tests:** Real Tracera instance (dev environment)
- **Contract tests:** Tracera API changes detected early
- **Smoke tests:** Daily validation of production traceability state

### Rollout Plan

- Feature-flag each NFR for gradual rollout
- Start with logging (observe impact); then enforce
- Provide migration path for existing entities (backfill traces)
- Document exceptions and overrides for emergency cases

---

**Prepared by:** Architecture Team  
**Related Specs:** FR-AP-001 (Domain Entities), requirements-traceability.md  
**Status:** Ready for implementation review
