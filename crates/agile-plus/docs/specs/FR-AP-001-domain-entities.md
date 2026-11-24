# FR-AP-001: Domain Entity Specifications

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2026-06-16  

## Overview

This document specifies the SSOT (Single Source of Truth) for all AgilePlus domain entities. Each entity is defined with its fields, lifecycle states, validation rules, and traceability linkage requirements.

---

## FR-AP-001.1: Project Entity

**Definition:** A top-level organizational unit that owns modules, cycles, features, epics, and stories.

### Fields

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `id` | i64 | Yes | Primary key, auto-generated | Unique per system |
| `slug` | String | Yes | `[a-z0-9-]+`, non-empty | URL-safe identifier; must be unique per system |
| `name` | String | Yes | Non-empty, max 255 chars | Human-readable display name |
| `description` | Option<String> | No | Max 2000 chars | Optional long-form description |
| `created_at` | DateTime<Utc> | Yes | Immutable | System-generated timestamp |
| `updated_at` | DateTime<Utc> | Yes | Mutable | System-updated timestamp |

### Validation Rules

- **slug:** Must match regex `^[a-z0-9-]+$`; must be non-empty after trimming
- **name:** Must be non-empty after trimming; leading/trailing whitespace trimmed on construction
- **Uniqueness:** `slug` must be globally unique within the system
- **Derived slug:** Can be generated from `name` via `Project::slug_from_name()` algorithm (lowercase + alphanumeric substitution)

### Acceptance Criteria

- [ ] Project with valid slug and name can be created
- [ ] Project construction rejects empty slug or name
- [ ] Project construction rejects invalid slug format (uppercase, special chars)
- [ ] Project slug is globally unique (enforced at persistence layer)
- [ ] Slug derivation from name produces valid URL-safe identifiers

---

## FR-AP-001.2: Epic Entity

**Definition:** A large body of work scoped to a project, containing multiple stories.

### Fields

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `id` | i64 | Yes | Primary key, auto-generated | Unique per system |
| `project_id` | i64 | Yes | Foreign key | Must reference existing Project |
| `title` | String | Yes | Non-empty, max 500 chars | Trimmed on construction |
| `description` | Option<String> | No | Max 5000 chars | Optional narrative description |
| `status` | EpicStatus | Yes | Enum value | Default: `Backlog` |
| `owner_id` | Option<i64> | No | Foreign key to User | Optional epic owner/sponsor |
| `requirement_id` | Option<String> | No | Max 100 chars | External traceability (e.g., Tracera FR ID) |
| `created_at` | DateTime<Utc> | Yes | Immutable | System-generated |
| `updated_at` | DateTime<Utc> | Yes | Mutable | System-updated |

### Lifecycle States

```
Backlog -> Active -> Review -> Done
         -> (cancel)
Active -> Cancelled
Review -> Active (reopen)
```

| State | Meaning | Terminal? |
|-------|---------|-----------|
| `Backlog` | Epic created but not started | No |
| `Active` | Epic currently in execution | No |
| `Review` | Epic complete, awaiting verification | No |
| `Done` | Epic successfully completed | No |
| `Cancelled` | Epic abandoned or deprioritized | Yes |

### Validation Rules

- **title:** Must be non-empty after trimming
- **project_id:** Must reference existing Project at persistence time
- **owner_id:** If set, must reference existing User
- **requirement_id:** If set, should be linkable to Tracera (validated by TraceabilityPort)
- **status transitions:** Must follow state machine rules (see `EpicStatus::can_transition_to()`)

### Acceptance Criteria

- [ ] Epic can be created with non-empty title and valid project_id
- [ ] Epic construction rejects empty title
- [ ] Epic defaults to `Backlog` status on creation
- [ ] Epic status transitions follow allowed paths (Backlog→Active, Active→Review, etc.)
- [ ] Epic status transitions reject invalid paths (e.g., Backlog→Done)
- [ ] Epic `updated_at` is refreshed on status transition
- [ ] Epic with `requirement_id` can be queried alongside linked Tracera artifact

---

## FR-AP-001.3: Story Entity

**Definition:** A user-facing deliverable owned by an Epic, containing concrete acceptance contracts.

### Fields

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `id` | i64 | Yes | Primary key, auto-generated | Unique per system |
| `epic_id` | i64 | Yes | Foreign key | Must reference existing Epic |
| `project_id` | i64 | Yes | Foreign key (denormalized) | Copied from Epic for query efficiency |
| `title` | String | Yes | Non-empty, max 500 chars | Trimmed on construction |
| `description` | Option<String> | No | Max 5000 chars | User story narrative: "As a <role>, I want <goal> so that <benefit>" |
| `status` | StoryStatus | Yes | Enum value | Default: `Todo` |
| `points` | Option<u32> | No | > 0 when set | Story point estimate (Fibonacci/planning poker scale) |
| `assignee_id` | Option<i64> | No | Foreign key to User | Developer/owner responsible for story |
| `requirement_id` | Option<String> | No | Max 100 chars | External traceability (e.g., Tracera FR ID) |
| `created_at` | DateTime<Utc> | Yes | Immutable | System-generated |
| `updated_at` | DateTime<Utc> | Yes | Mutable | System-updated |

### Lifecycle States

```
Todo -> InProgress -> Review -> Done
     -> Cancelled
InProgress -> Blocked
Blocked -> InProgress
Review -> InProgress (rework)
```

| State | Meaning | Terminal? |
|-------|---------|-----------|
| `Todo` | Story not yet started | No |
| `InProgress` | Story actively being worked | No |
| `Review` | Story complete, awaiting verification | No |
| `Done` | Story successfully completed | No |
| `Blocked` | Story waiting on external dependency | No |
| `Cancelled` | Story abandoned or out of scope | Yes |

### Validation Rules

- **title:** Must be non-empty after trimming
- **epic_id:** Must reference existing Epic at persistence time
- **project_id:** Must match Epic's project_id (denormalization invariant)
- **points:** If set (Some), must be > 0; `Some(0)` is rejected
- **assignee_id:** If set, must reference existing User
- **requirement_id:** If set, should be linkable to Tracera (validated by TraceabilityPort)
- **status transitions:** Must follow state machine rules

### Acceptance Criteria

- [ ] Story can be created with non-empty title, valid epic_id, and project_id
- [ ] Story construction rejects empty title
- [ ] Story construction rejects points = 0 (Some(0))
- [ ] Story defaults to `Todo` status on creation
- [ ] Story status transitions follow allowed paths
- [ ] Story status transitions reject invalid paths (e.g., Todo→Done, Review→Blocked)
- [ ] Story `updated_at` is refreshed on status transition
- [ ] Story with `requirement_id` can be queried alongside linked Tracera artifact
- [ ] Story-point estimates are used in velocity/burndown calculations

---

## FR-AP-001.4: Feature Entity

**Definition:** The central planning unit; a software feature tracked through a structured lifecycle.

### Fields

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `id` | i64 | Yes | Primary key, auto-generated | Unique per system |
| `slug` | String | Yes | `[a-z0-9-]+`, non-empty | URL-safe feature identifier |
| `friendly_name` | String | Yes | Non-empty, max 500 chars | Human-readable display name |
| `state` | FeatureState | Yes | Enum value | Default: `Created` |
| `spec_hash` | [u8; 32] | Yes | SHA256 hash | Content hash of specification document |
| `target_branch` | String | Yes | Git branch name | Merge target (default: `main`) |
| `plane_issue_id` | Option<String> | No | Max 100 chars | External issue tracker link (Plane) |
| `plane_state_id` | Option<String> | No | Max 100 chars | External state sync ID (Plane) |
| `labels` | Vec<String> | Yes | Variable length | Classification labels (type, domain, priority) |
| `module_id` | Option<i64> | No | Foreign key | Optional containing module |
| `project_id` | Option<i64> | No | Foreign key | Optional containing project |
| `created_at_commit` | Option<String> | No | Git SHA | Commit where feature was created |
| `last_modified_commit` | Option<String> | No | Git SHA | Latest commit modifying feature |
| `created_at` | DateTime<Utc> | Yes | Immutable | System-generated |
| `updated_at` | DateTime<Utc> | Yes | Mutable | System-updated |

### Lifecycle States

```
Created -> Specified -> Researched -> Planned -> Implementing -> Validated -> Shipped -> Retrospected (terminal)
```

| State | Meaning | Terminal? |
|-------|---------|-----------|
| `Created` | Feature initialized, minimal spec | No |
| `Specified` | Full specification document written | No |
| `Researched` | Research/spike completed, risks identified | No |
| `Planned` | Architecture and work packages defined | No |
| `Implementing` | Development actively in progress | No |
| `Validated` | Testing and verification complete | No |
| `Shipped` | Merged to target branch and deployed | No |
| `Retrospected` | Post-release review completed | Yes |

### Validation Rules

- **slug:** Must match `^[a-z0-9-]+$`
- **friendly_name:** Must be non-empty after trimming
- **spec_hash:** Must be valid SHA256 (32 bytes)
- **target_branch:** Must be a valid Git branch name
- **state transitions:** Linear progression only (no backtracking except lookahead)
- **labels:** Can be empty, but if present, each label must be non-empty and unique

### Acceptance Criteria

- [ ] Feature can be created with valid slug, friendly_name, and spec_hash
- [ ] Feature construction rejects invalid slug format
- [ ] Feature defaults to `Created` state on initialization
- [ ] Feature state transitions follow linear progression
- [ ] Feature state transitions reject backward/lateral moves
- [ ] Feature transitions update `updated_at` timestamp
- [ ] Feature `spec_hash` changes are tracked for specification changes
- [ ] Feature links to Plane issues are maintained across state transitions

---

## FR-AP-001.5: WorkPackage Entity

**Definition:** A concrete implementation unit under a Feature; may be assigned to an agent and linked to a PR.

### Fields

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `id` | i64 | Yes | Primary key, auto-generated | Unique per system |
| `feature_id` | i64 | Yes | Foreign key | Must reference existing Feature |
| `title` | String | Yes | Non-empty, max 500 chars | Work package name |
| `state` | WpState | Yes | Enum value | Default: `Planned` |
| `sequence` | i32 | Yes | Non-negative integer | Execution order within feature |
| `file_scope` | Vec<String> | Yes | Variable length | Paths to affected source files |
| `acceptance_criteria` | String | Yes | Non-empty, max 5000 chars | Concrete, verifiable completion criteria |
| `agent_id` | Option<String> | No | Max 100 chars | Claude agent assigned to implement |
| `pr_url` | Option<String> | No | Max 500 chars | Link to GitHub PR (if created) |
| `pr_state` | Option<PrState> | No | Enum value | Current PR state (Open, Review, etc.) |
| `worktree_path` | Option<String> | No | Max 500 chars | Git worktree path (local development) |
| `plane_sub_issue_id` | Option<String> | No | Max 100 chars | External sub-issue ID (Plane) |
| `base_commit` | Option<String> | No | Git SHA | PR base commit |
| `head_commit` | Option<String> | No | Git SHA | PR head commit |
| `created_at` | DateTime<Utc> | Yes | Immutable | System-generated |
| `updated_at` | DateTime<Utc> | Yes | Mutable | System-updated |

### Lifecycle States

```
Planned -> Doing -> Review -> Done
                 -> Blocked
        Blocked -> Doing
        Review -> Doing (rework)
```

| State | Meaning | Terminal? |
|-------|---------|-----------|
| `Planned` | Work package initialized, waiting to start | No |
| `Doing` | Implementation actively in progress | No |
| `Review` | Implementation complete, awaiting review | No |
| `Done` | Work package complete and merged | Yes |
| `Blocked` | Work blocked on external dependency/decision | No |

### Validation Rules

- **title:** Must be non-empty after trimming
- **feature_id:** Must reference existing Feature
- **acceptance_criteria:** Must be non-empty; describes concrete, verifiable outcomes
- **sequence:** Must be >= 0; defines execution order
- **file_scope:** Can be empty initially; populated as work progresses
- **agent_id:** If set, should be verifiable against agent registry
- **pr_url:** If set, must be valid GitHub PR URL
- **base_commit/head_commit:** If set, must be valid Git SHAs

### Acceptance Criteria

- [ ] WorkPackage can be created with valid feature_id, title, and acceptance_criteria
- [ ] WorkPackage construction rejects empty title or acceptance_criteria
- [ ] WorkPackage defaults to `Planned` state
- [ ] WorkPackage state transitions follow allowed paths
- [ ] WorkPackage state transitions reject invalid paths (e.g., Planned→Done, Review→Blocked)
- [ ] WorkPackage with agent_id can be queried for agent assignment tracking
- [ ] WorkPackage with pr_url tracks PR state across transitions
- [ ] Sequence ordering is enforced (no duplicates within feature)

---

## FR-AP-001.6: TraceRef Entity

**Definition:** A unidirectional reference from an AgilePlus entity to an external traceability artifact (e.g., Tracera requirement).

### Fields

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `trace_id` | String | Yes | Max 100 chars | External artifact ID (e.g., "FR-001", UUID) |
| `artifact_type` | String | Yes | Max 50 chars | Classification (see enum values below) |
| `entity_id` | Uuid | Yes | Valid v4 UUID | AgilePlus domain entity (Epic, Story, Task, etc.) |

### Artifact Type Enum

| Type | Example | Meaning |
|------|---------|---------|
| `requirement` | FR-001, NFR-005 | Functional or non-functional requirement |
| `specification` | SPEC-123 | Detailed specification document |
| `evidence` | EV-042 | Test result, acceptance evidence, proof artifact |
| `architecture` | ARCH-008 | System design document |
| `test_case` | TC-101 | Test specification or automation |
| `issue` | GH#1234, JIRA#456 | External issue tracker reference |
| `commit` | abc1234def5678 | Git commit hash for traceability |

### Linking Rules

- **One-way:** TraceRef points FROM AgilePlus entity TO external artifact
- **Non-null:** All fields required; no optional references
- **Uniqueness:** (entity_id, trace_id) tuple must be unique (no duplicate traces)
- **Bidirectional validation:** External system (Tracera) must independently confirm the link
- **Lifecycle:** TraceRef created on demand, not deleted (archived via status flags in external system)

### Validation Rules

- **trace_id:** Must be non-empty; must be valid in external system
- **artifact_type:** Must be one of the enum values (validated at persistence layer)
- **entity_id:** Must be valid UUID v4; must reference existing AgilePlus entity

### Acceptance Criteria

- [ ] TraceRef can be created with valid trace_id, artifact_type, and entity_id
- [ ] TraceRef construction rejects invalid artifact_type
- [ ] TraceRef construction rejects invalid UUID format
- [ ] Multiple TraceRefs can reference the same external artifact
- [ ] TraceRef uniqueness constraint prevents duplicate (entity_id, trace_id) pairs
- [ ] TraceRef serialization round-trips correctly (JSON in/out)
- [ ] External traceability system confirms backward link to AgilePlus entity

---

## FR-AP-001.7: AcceptanceContract Entity

**Definition:** A collection of acceptance criteria with verification status; drives story acceptance.

### Fields

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `id` | i64 | Yes | Primary key, auto-generated | Unique per system |
| `story_id` | i64 | Yes | Foreign key | Must reference existing Story |
| `title` | String | Yes | Non-empty, max 500 chars | Contract name/version |
| `criteria` | Vec<AcceptanceCriteria> | Yes | Non-empty | List of acceptance criteria (see below) |
| `lifecycle_status` | ContractStatus | Yes | Enum value | Default: `Draft` |
| `verified_count` | i32 | Yes | >= 0 | Count of verified criteria |
| `total_count` | i32 | Yes | > 0 | Total criteria count |
| `created_at` | DateTime<Utc> | Yes | Immutable | System-generated |
| `updated_at` | DateTime<Utc> | Yes | Mutable | System-updated |

### AcceptanceCriteria Substructure

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `id` | i64 | Yes | Primary key | Unique within contract |
| `sequence` | i32 | Yes | Non-negative | Ordering within criteria list |
| `criterion_text` | String | Yes | Non-empty, max 1000 chars | Human-readable acceptance criterion |
| `verifiable` | bool | Yes | Always true | Criteria must be testable |
| `trace_ref_ids` | Vec<String> | No | Variable length | Links to external evidence (Tracera) |
| `verification_status` | VerificationStatus | Yes | Enum value | (see below) |

### Contract Lifecycle Status

| Status | Meaning | Terminal? |
|--------|---------|-----------|
| `Draft` | Contract under construction | No |
| `Active` | Contract ready for work (linked to story) | No |
| `Verified` | All criteria verified; story can transition to Done | No |
| `Archived` | Contract superseded or no longer active | Yes |

### Verification Status

| Status | Meaning |
|--------|---------|
| `Unverified` | Criterion not yet checked |
| `Pending` | Verification in progress |
| `Verified` | Criterion confirmed satisfied |
| `Failed` | Criterion check failed; rework required |

### Validation Rules

- **criteria:** Vector must be non-empty; each criterion must have unique sequence and non-empty text
- **verified_count:** Must be <= total_count; updated on criterion verification
- **total_count:** Must equal len(criteria); updated when criteria added/removed
- **lifecycle transitions:** Draft→Active→Verified; Verified→Archived; Active→Archived
- **story linkage:** AcceptanceContract must reference existing Story; story cannot move to Done without verified contract

### Acceptance Criteria

- [ ] AcceptanceContract can be created with non-empty criteria list and story_id
- [ ] AcceptanceContract defaults to `Draft` status
- [ ] AcceptanceContract rejects empty criteria
- [ ] AcceptanceContract verified_count auto-increments on criterion verification
- [ ] AcceptanceContract verified_count matches count of Verified criteria
- [ ] AcceptanceContract can transition from Draft→Active→Verified
- [ ] AcceptanceContract status transitions update `updated_at`
- [ ] Story cannot move to Done status without all AcceptanceContract criteria verified
- [ ] AcceptanceCriteria can be linked to Tracera evidence artifacts (via TraceRef)
- [ ] AcceptanceCriteria can be marked Verified only if linked to external evidence

---

## Relationship Diagram

```
Project
  ├─ Epic (1:N)
  │    └─ Story (1:N)
  │         ├─ AcceptanceContract (1:N)
  │         │    └─ AcceptanceCriteria (1:N)
  │         │         └─ TraceRef (0:N) → Tracera
  │         └─ TraceRef (0:N) → Tracera
  ├─ Feature (1:N)
  │    └─ WorkPackage (1:N)
  │         └─ TraceRef (0:N) → Tracera
  └─ Module (1:N)
       └─ Cycle (1:N)

User (external identity)
  ├─ Project.owner_id (0:N)
  ├─ Epic.owner_id (0:N)
  ├─ Story.assignee_id (0:N)
  └─ WorkPackage.agent_id (0:N)
```

---

## Cross-Cutting Concerns

### Traceability

- **All entities** (Epic, Story, WorkPackage, Feature) MAY carry optional `requirement_id` link to Tracera
- **AcceptanceCriteria** MUST link to Tracera evidence before marking Verified (FR-AP-002.2)
- **TraceRef** port provides async link/query operations; linked entities must be queryable together

### Audit Trail

- **created_at, updated_at** fields are immutable/system-managed
- **Commits:** Feature tracks created_at_commit and last_modified_commit for spec changes
- **WorkPackage:** base_commit/head_commit track PR integration

### State Machine Consistency

- **All stateful entities** enforce transitions via `can_transition_to()` methods
- **Invalid transitions** return `DomainError::InvalidTransition` with context
- **Status changes** must be explicit API calls (no implicit state drift)

---

## Implementation Notes

- All domain entities use Serde for JSON serialization (required for API, storage, sync)
- Timestamp arithmetic (burndown, velocity) uses DateTime<Utc> and chrono
- UUID identifiers (especially TraceRef.entity_id) require uuid crate with Serialize/Deserialize
- Foreign key references are i64 (database-native); validation deferred to persistence adapters
- Validation is split: domain layer enforces invariants; adapters enforce unique constraints, FK integrity

---

**Prepared by:** Architecture Team  
**Related Specs:** NFR-AP-001 (Traceability), NFR-AP-002 (Verification), NFR-AP-003 (Bidirectional Linking)
