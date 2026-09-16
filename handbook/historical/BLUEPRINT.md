# [PROJECT NAME] - Complete Architecture Blueprint

> **📋 INSTRUCTIONS:** This is a comprehensive template. Replace ALL `[PLACEHOLDERS]` with actual project details.
> Delete this instruction block and the "How to Fill This Template" section after completing the document.

**Status:** `[Draft | Active | Deprecated]`
**Version:** `X.Y.Z`
**Last Updated:** `YYYY-MM-DD`
**Next Review:** `YYYY-MM-DD`
**Maintainers:** `[Team/Person Names]`
**Repository:** `[GitHub/GitLab URL]`

---

## 📖 How to Fill This Template

### Initial Setup (First Time)
1. **Copy this file** to your project root or `docs/` directory
2. **Rename** to `ARCHITECTURE_BLUEPRINT.md`
3. **Search and replace** `[PROJECT NAME]` with your actual project name
4. **Fill in all sections** marked with `[PLACEHOLDERS]`
5. **Delete** this "How to Fill This Template" section
6. **Commit** to version control

### Ongoing Maintenance
- **Update monthly** or after significant changes
- **Review during retrospectives** and architecture reviews
- **Create ADRs** for all significant decisions
- **Track changes** in the "Document History" section
- **Keep diagrams current** - regenerate when structure changes

### Section-by-Section Guide

| Section | What to Document | When to Update |
|---------|------------------|----------------|
| **Project Overview** | Purpose, capabilities, stakeholders | Rarely (major pivots only) |
| **Technology Stack** | All technologies with versions | When dependencies change |
| **Architecture Diagrams** | System structure, data flows | When architecture changes |
| **Directory Structure** | Actual file tree | When structure changes |
| **Layer Responsibilities** | Actual components in each layer | When components added/removed |
| **Data Models** | Entities, relationships, schemas | When models change |
| **API Specifications** | Endpoints, tools, resources | When APIs change |
| **Testing Strategy** | Coverage, test types, examples | Monthly or when strategy changes |
| **Design Patterns** | Actual patterns in use | When patterns adopted/deprecated |
| **External Integrations** | All external services | When integrations change |
| **Deployment** | Environments, CI/CD, configs | When deployment changes |
| **Observability** | Logging, metrics, tracing | When observability changes |
| **Security** | Auth, encryption, compliance | When security changes |
| **Performance** | Benchmarks, bottlenecks, optimizations | Quarterly or when issues arise |
| **Technical Debt** | Known issues, remediation plans | Monthly |
| **Roadmap** | Future plans, deprecations | Quarterly |
| **ADRs** | All architectural decisions | When decisions made |

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Diagrams](#architecture-diagrams)
4. [Directory Structure](#directory-structure)
5. [Layer Responsibilities](#layer-responsibilities)
6. [Data Models](#data-models)
7. [API Specifications](#api-specifications)
8. [Testing Strategy](#testing-strategy)
9. [Design Patterns](#design-patterns)
10. [External Integrations](#external-integrations)
11. [Deployment Architecture](#deployment-architecture)
12. [Observability](#observability)
13. [Security Architecture](#security-architecture)
14. [Performance Architecture](#performance-architecture)
15. [Technical Debt & Roadmap](#technical-debt--roadmap)
16. [Architectural Decision Records](#architectural-decision-records)
17. [Development Workflow](#development-workflow)
18. [Troubleshooting Guide](#troubleshooting-guide)
19. [Glossary](#glossary)
20. [Document History](#document-history)

---

## 🎯 Project Overview

### Purpose
**What:** `[Brief description of what this project does]`

**Why:** `[Why this project exists - business problem it solves]`

**Who:** `[Target users/stakeholders]`

**Example:**
```
What: A Model Context Protocol (MCP) server for AI agent orchestration
Why: Enable LLM-based agents to interact with external tools and workflows
Who: AI developers, automation engineers, enterprise teams
```

### Key Capabilities

**Core Features:**
- `[Feature 1]` - `[Brief description]`
- `[Feature 2]` - `[Brief description]`
- `[Feature 3]` - `[Brief description]`

**Unique Value Propositions:**
- `[What makes this project unique/better]`
- `[Key differentiator]`

### Project Metrics

| Metric | Current Value | Target | Status |
|--------|--------------|--------|--------|
| **Lines of Code** | `[X,XXX]` | N/A | 📊 |
| **Test Coverage** | `[XX%]` | `[XX%]` | `[✅/⚠️/❌]` |
| **Active Users** | `[XXX]` | `[XXX]` | `[✅/⚠️/❌]` |
| **Uptime** | `[XX.XX%]` | `[99.9%]` | `[✅/⚠️/❌]` |
| **Response Time (p95)** | `[XXXms]` | `[XXXms]` | `[✅/⚠️/❌]` |
| **Technical Debt Ratio** | `[XX%]` | `[<10%]` | `[✅/⚠️/❌]` |

### Stakeholders

| Role | Name/Team | Responsibility | Contact |
|------|-----------|----------------|---------|
| **Product Owner** | `[Name]` | `[Responsibility]` | `[Email/Slack]` |
| **Tech Lead** | `[Name]` | `[Responsibility]` | `[Email/Slack]` |
| **DevOps Lead** | `[Name]` | `[Responsibility]` | `[Email/Slack]` |
| **Security Lead** | `[Name]` | `[Responsibility]` | `[Email/Slack]` |

---

## 🛠️ Technology Stack

### Core Technologies

| Layer | Technology | Version | Status | Rationale | ADR |
|-------|-----------|---------|--------|-----------|-----|
| **Language** | `[Python/Node/Go]` | `[X.Y]` | ✅ Active | `[Why chosen]` | `[ADR-XXX]` |
| **Framework** | `[FastAPI/Django/Express]` | `[X.Y]` | ✅ Active | `[Why chosen]` | `[ADR-XXX]` |
| **Database** | `[PostgreSQL/MongoDB]` | `[X.Y]` | ✅ Active | `[Why chosen]` | `[ADR-XXX]` |
| **Cache** | `[Redis/Memcached]` | `[X.Y]` | ✅ Active | `[Why chosen]` | `[ADR-XXX]` |
| **Message Queue** | `[NATS/RabbitMQ/Kafka]` | `[X.Y]` | ✅ Active | `[Why chosen]` | `[ADR-XXX]` |
| **Testing** | `[pytest/Jest/Go test]` | `[X.Y]` | ✅ Active | `[Why chosen]` | `[ADR-XXX]` |

### Infrastructure

| Component | Technology | Version | Status | Notes |
|-----------|-----------|---------|--------|-------|
| **Container Runtime** | `[Docker]` | `[X.Y]` | ✅ Active | `[Notes]` |
| **Orchestration** | `[Kubernetes/Docker Compose]` | `[X.Y]` | ✅ Active | `[Notes]` |
| **CI/CD** | `[GitHub Actions/GitLab CI]` | `[X.Y]` | ✅ Active | `[Notes]` |
| **Monitoring** | `[Prometheus/Datadog]` | `[X.Y]` | ✅ Active | `[Notes]` |
| **Logging** | `[ELK/Loki]` | `[X.Y]` | ✅ Active | `[Notes]` |
| **Tracing** | `[Jaeger/OpenTelemetry]` | `[X.Y]` | ✅ Active | `[Notes]` |

### Development Tools

| Tool | Purpose | Version | Status |
|------|---------|---------|--------|
| **Linter** | `[flake8/ESLint]` | `[X.Y]` | ✅ Active |
| **Formatter** | `[black/Prettier]` | `[X.Y]` | ✅ Active |
| **Type Checker** | `[mypy/TypeScript]` | `[X.Y]` | ✅ Active |
| **Dependency Manager** | `[uv/npm/go mod]` | `[X.Y]` | ✅ Active |
| **Pre-commit Hooks** | `[pre-commit]` | `[X.Y]` | ✅ Active |

### Deprecated Technologies

| Technology | Deprecated Date | Replaced By | Migration Status | Notes |
|------------|----------------|-------------|------------------|-------|
| `[Old Tech]` | `[YYYY-MM-DD]` | `[New Tech]` | `[Complete/In Progress/Planned]` | `[Notes]` |

---

## 🏗️ Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  [List actual clients: Web UI, Mobile App, CLI, API consumers]     │
└────────────────────────────┬────────────────────────────────────────┘
                             │ [Protocol: HTTP/gRPC/WebSocket]
┌────────────────────────────▼────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
│  [List actual entry points: REST API, GraphQL, MCP Tools, etc.]    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│  [List actual use cases/services]                                   │
│  • [UseCase1Service]                                                │
│  • [UseCase2Service]                                                │
│  • [UseCase3Service]                                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                        DOMAIN LAYER                                 │
│  [List actual entities and value objects]                           │
│  • Entities: [Entity1, Entity2, Entity3]                           │
│  • Value Objects: [VO1, VO2, VO3]                                  │
│  • Domain Services: [Service1, Service2]                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                             │
│  [List actual adapters]                                             │
│  • Repositories: [Repo1, Repo2]                                    │
│  • External Services: [Service1, Service2]                         │
│  • Message Brokers: [Broker1, Broker2]                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Instructions:** Replace the bracketed placeholders with your actual components. Keep the diagram updated as architecture evolves.

### Dependency Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY DIRECTION                             │
│                                                                     │
│  Infrastructure Layer  →  Application Layer  →  Domain Layer       │
│  (Adapters)               (Use Cases, Ports)     (Entities, VOs)   │
│                                                                     │
│  ✅ ALLOWED:                                                        │
│  • Infrastructure → Application                                     │
│  • Infrastructure → Domain                                          │
│  • Application → Domain                                             │
│                                                                     │
│  ❌ FORBIDDEN:                                                      │
│  • Domain → Application                                             │
│  • Domain → Infrastructure                                          │
│  • Application → Infrastructure                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
[Client Request]
      │
      ▼
[Driving Adapter]  ← Infrastructure Layer
      │            (FastAPI endpoint, MCP tool, CLI command)
      │
      ▼
[Application Service]  ← Application Layer
      │                 (Use case orchestration)
      │
      ├──→ [Domain Entity]  ← Domain Layer
      │    (Business logic)
      │
      ├──→ [Port Interface]  ← Application Layer
      │    (Abstract contract)
      │
      ▼
[Driven Adapter]  ← Infrastructure Layer
      │           (Database, External API, Message Queue)
      │
      ▼
[External System]
```

**Instructions:** Customize this with your actual flow. Add specific examples of requests flowing through your system.

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    [FEATURE NAME] FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. [Client] sends [request type] to [endpoint/tool]               │
│     ↓                                                               │
│  2. [DrivingAdapter] validates and parses request                   │
│     ↓                                                               │
│  3. [ApplicationService] orchestrates:                              │
│     ├─→ Calls [DomainEntity].method()                              │
│     ├─→ Calls [Port].method() (implemented by [Adapter])           │
│     └─→ Publishes [DomainEvent]                                    │
│     ↓                                                               │
│  4. [DrivenAdapter] persists/retrieves data                         │
│     ↓                                                               │
│  5. [DrivingAdapter] formats and returns response                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Instructions:** Create one diagram per major feature. Replace placeholders with actual component names.

---

## 📁 Directory Structure

### Current Project Tree

```
[project-root]/
├── src/                                    # Source code
│   └── [project_name]/
│       ├── __init__.py
│       │
│       ├── domain/                         # ❌ NO external dependencies
│       │   ├── __init__.py
│       │   ├── entities/                   # [List actual entities]
│       │   │   ├── __init__.py
│       │   │   ├── [entity1].py
│       │   │   └── [entity2].py
│       │   ├── value_objects/              # [List actual VOs]
│       │   │   ├── __init__.py
│       │   │   ├── [vo1].py
│       │   │   └── [vo2].py
│       │   ├── services/                   # [List actual domain services]
│       │   │   ├── __init__.py
│       │   │   └── [service].py
│       │   ├── events/                     # [List actual domain events]
│       │   │   ├── __init__.py
│       │   │   └── [event].py
│       │   └── exceptions.py               # Domain-specific exceptions
│       │
│       ├── application/                    # ✅ Depends on Domain
│       │   ├── __init__.py
│       │   ├── services/                   # [List actual use cases]
│       │   │   ├── __init__.py
│       │   │   ├── [usecase1]_service.py
│       │   │   └── [usecase2]_service.py
│       │   ├── ports/                      # [List actual ports]
│       │   │   ├── __init__.py
│       │   │   ├── [repository]_port.py
│       │   │   └── [service]_port.py
│       │   ├── commands/                   # [List actual commands]
│       │   │   ├── __init__.py
│       │   │   └── [command].py
│       │   ├── queries/                    # [List actual queries]
│       │   │   ├── __init__.py
│       │   │   └── [query].py
│       │   └── dto/                        # Data Transfer Objects
│       │       ├── __init__.py
│       │       └── [dto].py
│       │
│       └── infrastructure/                 # ✅ Depends on Application
│           ├── __init__.py
│           ├── adapters/                   # [List actual adapters]
│           │   ├── __init__.py
│           │   ├── driving/                # Input adapters
│           │   │   ├── api/                # [REST/GraphQL/etc]
│           │   │   ├── cli/                # [CLI commands]
│           │   │   └── mcp/                # [MCP tools]
│           │   └── driven/                 # Output adapters
│           │       ├── persistence/        # [Database adapters]
│           │       ├── messaging/          # [Message queue adapters]
│           │       └── external/           # [External API clients]
│           ├── config/                     # Configuration
│           │   ├── __init__.py
│           │   └── settings.py
│           └── factories/                  # Object factories
│               ├── __init__.py
│               └── [factory].py
│
├── tests/                                  # Test suite
│   ├── __init__.py
│   ├── unit/                               # Fast, isolated tests
│   │   ├── domain/                         # [Domain tests]
│   │   ├── application/                    # [Application tests]
│   │   └── infrastructure/                 # [Infrastructure tests]
│   ├── integration/                        # Integration tests
│   │   ├── adapters/                       # [Adapter tests]
│   │   └── repositories/                   # [Repository tests]
│   ├── e2e/                                # End-to-end tests
│   │   └── [feature]_test.py
│   ├── fixtures/                           # Shared test fixtures
│   │   ├── __init__.py
│   │   └── [fixture].py
│   └── conftest.py                         # Pytest configuration
│
├── docs/                                   # Documentation
│   ├── ARCHITECTURE_BLUEPRINT.md           # THIS DOCUMENT
│   ├── adr/                                # Architectural Decision Records
│   │   ├── 0001-[decision].md
│   │   └── 0002-[decision].md
│   ├── api/                                # API documentation
│   │   └── [api-spec].md
│   └── guides/                             # User/developer guides
│       └── [guide].md
│
├── scripts/                                # Utility scripts
│   ├── setup.sh                            # Environment setup
│   ├── migrate.py                          # Database migrations
│   └── [script].py
│
├── config/                                 # Configuration files
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
│
├── .github/                                # GitHub-specific files
│   └── workflows/                          # CI/CD workflows
│       ├── test.yml
│       └── deploy.yml
│
├── docker/                                 # Docker files
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
├── pyproject.toml                          # Python project metadata
├── requirements.txt                        # Python dependencies
├── .gitignore                              # Git ignore rules
├── .pre-commit-config.yaml                 # Pre-commit hooks
├── README.md                               # Project README
└── LICENSE                                 # License file
```

**Instructions:**
1. Replace `[project-root]` and `[project_name]` with actual names
2. List all actual files in each directory (replace `[entity1]`, `[usecase1]`, etc.)
3. Remove directories that don't exist in your project
4. Add any custom directories specific to your project
5. Update this tree whenever structure changes significantly

### File Count by Layer

| Layer | Files | Lines of Code | Percentage |
|-------|-------|---------------|------------|
| **Domain** | `[XX]` | `[X,XXX]` | `[XX%]` |
| **Application** | `[XX]` | `[X,XXX]` | `[XX%]` |
| **Infrastructure** | `[XX]` | `[X,XXX]` | `[XX%]` |
| **Tests** | `[XX]` | `[X,XXX]` | `[XX%]` |
| **Total** | `[XX]` | `[X,XXX]` | `100%` |

**Instructions:** Update these metrics monthly or after significant changes. Use tools like `cloc` or `tokei` to generate accurate counts.

---

## 🔄 Layer Responsibilities

### Domain Layer (`src/[project]/domain/`)

**Purpose:** Pure business logic and rules. NO external dependencies.

**Current Components:**

#### Entities
| Entity | Purpose | Key Methods | Status |
|--------|---------|-------------|--------|
| `[Entity1]` | `[What it represents]` | `[method1(), method2()]` | ✅ Active |
| `[Entity2]` | `[What it represents]` | `[method1(), method2()]` | ✅ Active |

**Example:**
```python
# src/[project]/domain/entities/[entity].py
class [Entity]:
    """[Description of what this entity represents]"""

    def __init__(self, id: str, [attributes]):
        self.id = id
        # ... attributes

    def [business_method](self) -> [ReturnType]:
        """[What this method does]"""
        # Business logic here
        pass
```

#### Value Objects
| Value Object | Purpose | Immutable | Validation |
|--------------|---------|-----------|------------|
| `[VO1]` | `[What it represents]` | ✅ Yes | `[Rules]` |
| `[VO2]` | `[What it represents]` | ✅ Yes | `[Rules]` |

**Example:**
```python
# src/[project]/domain/value_objects/[vo].py
@dataclass(frozen=True)
class [ValueObject]:
    """[Description]"""
    [attribute]: [Type]

    def __post_init__(self):
        """Validate invariants"""
        if [validation_condition]:
            raise ValueError("[Error message]")
```

#### Domain Services
| Service | Purpose | Key Methods | Status |
|---------|---------|-------------|--------|
| `[Service1]` | `[What it does]` | `[method1(), method2()]` | ✅ Active |

#### Domain Events
| Event | Trigger | Subscribers | Status |
|-------|---------|-------------|--------|
| `[Event1]` | `[When it's published]` | `[Who listens]` | ✅ Active |

**Dependencies:** None (pure Python only)

**Status:** `[Stable | In Development | Needs Refactoring]`

**Violations:** `[List any current violations of domain purity]`

---

### Application Layer (`src/[project]/application/`)

**Purpose:** Orchestrate domain objects to fulfill use cases.

**Current Components:**

#### Use Cases / Services
| Service | Purpose | Dependencies | Status |
|---------|---------|--------------|--------|
| `[UseCase1Service]` | `[What it does]` | `[Ports it uses]` | ✅ Active |
| `[UseCase2Service]` | `[What it does]` | `[Ports it uses]` | ✅ Active |

**Example:**
```python
# src/[project]/application/services/[usecase]_service.py
class [UseCase]Service:
    """[Description of use case]"""

    def __init__(
        self,
        [repository]: [RepositoryPort],
        [service]: [ServicePort]
    ):
        self.[repository] = [repository]
        self.[service] = [service]

    def execute(self, command: [Command]) -> [Result]:
        """[What this use case does]"""
        # 1. Validate input
        # 2. Load domain entities
        # 3. Execute business logic
        # 4. Persist changes
        # 5. Publish events
        # 6. Return result
        pass
```

#### Ports (Interfaces)
| Port | Purpose | Implementations | Status |
|------|---------|----------------|--------|
| `[RepositoryPort]` | `[Data access]` | `[Adapter1, Adapter2]` | ✅ Active |
| `[ServicePort]` | `[External service]` | `[Adapter1]` | ✅ Active |

**Example:**
```python
# src/[project]/application/ports/[repository]_port.py
class [Repository]Port(ABC):
    """[Description of repository contract]"""

    @abstractmethod
    def save(self, entity: [Entity]) -> None:
        """[What this method does]"""
        pass

    @abstractmethod
    def find_by_id(self, id: str) -> Optional[[Entity]]:
        """[What this method does]"""
        pass
```

#### Commands / Queries
| Command/Query | Purpose | Handler | Status |
|---------------|---------|---------|--------|
| `[Command1]` | `[What it represents]` | `[Service]` | ✅ Active |
| `[Query1]` | `[What it retrieves]` | `[Service]` | ✅ Active |

**Dependencies:** Domain layer only

**Status:** `[Stable | In Development | Needs Refactoring]`

---

### Infrastructure Layer (`src/[project]/infrastructure/`)

**Purpose:** Implement technical details and external integrations.

**Current Components:**

#### Driving Adapters (Inputs)
| Adapter | Type | Entry Points | Status |
|---------|------|--------------|--------|
| `[APIAdapter]` | REST API | `[/endpoint1, /endpoint2]` | ✅ Active |
| `[MCPAdapter]` | MCP Tools | `[tool1, tool2]` | ✅ Active |
| `[CLIAdapter]` | CLI | `[command1, command2]` | ✅ Active |

**Example:**
```python
# src/[project]/infrastructure/adapters/driving/api/[endpoint].py
@router.post("/[endpoint]")
async def [endpoint_handler](
    request: [RequestDTO],
    service: [Service] = Depends(get_service)
) -> [ResponseDTO]:
    """[What this endpoint does]"""
    command = [Command](...)
    result = service.execute(command)
    return [ResponseDTO].from_result(result)
```

#### Driven Adapters (Outputs)
| Adapter | Type | Implements Port | Status |
|---------|------|----------------|--------|
| `[PostgreSQLAdapter]` | Database | `[RepositoryPort]` | ✅ Active |
| `[NATSAdapter]` | Message Queue | `[EventBusPort]` | ✅ Active |
| `[HTTPClientAdapter]` | External API | `[ServicePort]` | ✅ Active |

**Example:**
```python
# src/[project]/infrastructure/adapters/driven/persistence/[repository].py
class [Repository]Adapter([Repository]Port):
    """[Description of adapter]"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, entity: [Entity]) -> None:
        """[What this method does]"""
        orm_entity = [Mapper].to_orm(entity)
        self.session.add(orm_entity)
        self.session.commit()
```

**Dependencies:** Application and Domain layers

**Status:** `[Stable | In Development | Needs Refactoring]`

---

## 📊 Data Models

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ENTITY RELATIONSHIPS                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Entity1]                                                          │
│  ├── id: UUID                                                       │
│  ├── [attribute1]: [Type]                                           │
│  ├── [attribute2]: [Type]                                           │
│  └── [relationship] ──→ [Entity2] (1:N)                            │
│                                                                     │
│  [Entity2]                                                          │
│  ├── id: UUID                                                       │
│  ├── [entity1_id]: UUID (FK)                                        │
│  ├── [attribute1]: [Type]                                           │
│  └── [relationship] ──→ [Entity3] (N:M)                            │
│                                                                     │
│  [Entity3]                                                          │
│  ├── id: UUID                                                       │
│  ├── [attribute1]: [Type]                                           │
│  └── [attribute2]: [Type]                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Instructions:** Replace with your actual entities and relationships. Use standard notation:
- `1:1` = One-to-one
- `1:N` = One-to-many
- `N:M` = Many-to-many
- `FK` = Foreign key

### Domain Entities

#### [Entity1]

**Purpose:** `[What this entity represents in the business domain]`

**Attributes:**
| Attribute | Type | Required | Validation | Description |
|-----------|------|----------|------------|-------------|
| `id` | `UUID` | ✅ Yes | Unique | Primary identifier |
| `[attr1]` | `[Type]` | `[Yes/No]` | `[Rules]` | `[Description]` |
| `[attr2]` | `[Type]` | `[Yes/No]` | `[Rules]` | `[Description]` |

**Business Rules:**
- `[Rule 1: Description]`
- `[Rule 2: Description]`
- `[Rule 3: Description]`

**State Transitions:**
```
[InitialState] ──[action1]──→ [State2] ──[action2]──→ [FinalState]
                                │
                                └──[action3]──→ [State3]
```

**Example:**
```python
class [Entity1]:
    """[Description]"""

    def __init__(self, id: UUID, [attributes]):
        self.id = id
        self.[attr1] = [attr1]
        self._state = [InitialState]

    def [business_method](self) -> None:
        """[What this method does]"""
        if self._state != [RequiredState]:
            raise InvalidStateError(f"Cannot [action] in state {self._state}")

        # Business logic
        self._state = [NewState]
```

**Database Schema:**
```sql
CREATE TABLE [entity1_table] (
    id UUID PRIMARY KEY,
    [attr1] [TYPE] NOT NULL,
    [attr2] [TYPE],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_[entity1]_[attr] ON [entity1_table]([attr]);
```

### Value Objects

#### [ValueObject1]

**Purpose:** `[What this value object represents]`

**Attributes:**
| Attribute | Type | Validation |
|-----------|------|------------|
| `[attr1]` | `[Type]` | `[Rules]` |
| `[attr2]` | `[Type]` | `[Rules]` |

**Invariants:**
- `[Invariant 1: Must always be true]`
- `[Invariant 2: Must always be true]`

**Example:**
```python
@dataclass(frozen=True)
class [ValueObject1]:
    """[Description]"""
    [attr1]: [Type]
    [attr2]: [Type]

    def __post_init__(self):
        if [validation_condition]:
            raise ValueError("[Error message]")

    def [method](self) -> [ReturnType]:
        """[What this method does]"""
        return [calculation]
```

### Aggregates

**Aggregate Root:** `[Entity1]`

**Aggregate Boundary:**
```
[Entity1] (Root)
├── [Entity2] (Child)
│   └── [ValueObject1]
└── [Entity3] (Child)
    └── [ValueObject2]
```

**Consistency Rules:**
- `[Rule 1: What must be consistent within this aggregate]`
- `[Rule 2: What must be consistent within this aggregate]`

**Instructions:** Document all aggregates in your domain. An aggregate is a cluster of entities and value objects that are treated as a single unit for data changes.

---

## 🔌 API Specifications

### REST API Endpoints

#### [Resource Name]

**Base URL:** `[https://api.example.com/v1]`

| Method | Endpoint | Purpose | Auth | Status |
|--------|----------|---------|------|--------|
| `GET` | `/[resource]` | List all | ✅ Required | ✅ Active |
| `GET` | `/[resource]/{id}` | Get by ID | ✅ Required | ✅ Active |
| `POST` | `/[resource]` | Create new | ✅ Required | ✅ Active |
| `PUT` | `/[resource]/{id}` | Update | ✅ Required | ✅ Active |
| `DELETE` | `/[resource]/{id}` | Delete | ✅ Required | ✅ Active |

**Example: Create [Resource]**

```http
POST /[resource]
Content-Type: application/json
Authorization: Bearer {token}

{
  "[field1]": "[value1]",
  "[field2]": "[value2]"
}
```

**Response:**
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "[uuid]",
  "[field1]": "[value1]",
  "[field2]": "[value2]",
  "created_at": "2025-10-13T12:00:00Z"
}
```

**Error Responses:**
| Status Code | Reason | Response Body |
|-------------|--------|---------------|
| `400` | Bad Request | `{"error": "Invalid [field]"}` |
| `401` | Unauthorized | `{"error": "Authentication required"}` |
| `404` | Not Found | `{"error": "[Resource] not found"}` |
| `500` | Server Error | `{"error": "Internal server error"}` |

### MCP Tools (if applicable)

| Tool Name | Purpose | Parameters | Returns | Status |
|-----------|---------|------------|---------|--------|
| `[tool1]` | `[What it does]` | `[param1, param2]` | `[ReturnType]` | ✅ Active |
| `[tool2]` | `[What it does]` | `[param1, param2]` | `[ReturnType]` | ✅ Active |

**Example: [Tool1]**

```python
@mcp.tool()
async def [tool1](
    [param1]: [Type],
    [param2]: [Type]
) -> dict:
    """[Description of what this tool does]"""
    # Implementation
    return {"result": "[value]"}
```

### MCP Resources (if applicable)

| Resource URI | Purpose | Content Type | Status |
|--------------|---------|--------------|--------|
| `[resource://type/id]` | `[What it provides]` | `[text/json/etc]` | ✅ Active |

### GraphQL Schema (if applicable)

```graphql
type [Type] {
  id: ID!
  [field1]: [Type]!
  [field2]: [Type]
  [relationship]: [[RelatedType]]
}

type Query {
  [query1]([param]: [Type]!): [Type]
  [query2]: [[Type]]
}

type Mutation {
  [mutation1]([input]: [InputType]!): [Type]
}
```

### WebSocket Events (if applicable)

| Event | Direction | Payload | Purpose |
|-------|-----------|---------|---------|
| `[event1]` | Client → Server | `{[data]}` | `[Purpose]` |
| `[event2]` | Server → Client | `{[data]}` | `[Purpose]` |

---

## 🧪 Testing Strategy

### Test Pyramid

```
Current Distribution:                    Target Distribution:
        /\                                      /\
       /E2E\         ← [X] tests                /E2E\         ← [Target]
      /------\         ([X%] coverage)         /------\         ([X%])
     /  INT   \      ← [X] tests              /  INT   \      ← [Target]
    /----------\       ([X%] coverage)       /----------\       ([X%])
   /    UNIT    \    ← [X] tests            /    UNIT    \    ← [Target]
  /--------------\     ([X%] coverage)     /--------------\     ([X%])
```

### Coverage by Layer

| Layer | Unit Tests | Integration Tests | E2E Tests | Coverage | Target |
|-------|-----------|-------------------|-----------|----------|--------|
| **Domain** | `[XXX]` | `[XX]` | `[X]` | `[XX%]` | `[90%+]` |
| **Application** | `[XXX]` | `[XX]` | `[X]` | `[XX%]` | `[85%+]` |
| **Infrastructure** | `[XX]` | `[XXX]` | `[X]` | `[XX%]` | `[70%+]` |
| **Overall** | `[XXX]` | `[XXX]` | `[XX]` | `[XX%]` | `[80%+]` |

### Test Types

#### Unit Tests (Fast, Isolated)

**Location:** `tests/unit/`

**Purpose:** Test individual components in isolation

**Example:**
```python
# tests/unit/domain/test_[entity].py
def test_[entity]_[behavior]():
    """Test that [entity] [does something] when [condition]"""
    # Arrange
    entity = [Entity]([params])

    # Act
    result = entity.[method]()

    # Assert
    assert result == [expected]
```

**Coverage Target:** 90%+ for domain, 85%+ for application

#### Integration Tests (Slower, Real Dependencies)

**Location:** `tests/integration/`

**Purpose:** Test adapters with real external services

**Example:**
```python
# tests/integration/adapters/test_[repository].py
def test_[repository]_saves_and_retrieves_[entity]():
    """Test that [repository] can persist and retrieve [entity]"""
    # Arrange
    session = create_test_session()
    repository = [Repository]Adapter(session)
    entity = [Entity]([params])

    # Act
    repository.save(entity)
    retrieved = repository.find_by_id(entity.id)

    # Assert
    assert retrieved.id == entity.id
    assert retrieved.[attr] == entity.[attr]
```

**Coverage Target:** 70%+ for infrastructure

#### End-to-End Tests (Slowest, Full System)

**Location:** `tests/e2e/`

**Purpose:** Test complete user flows through the system

**Example:**
```python
# tests/e2e/test_[feature]_flow.py
async def test_complete_[feature]_flow():
    """Test complete [feature] flow from request to response"""
    # Arrange
    client = TestClient(app)

    # Act
    response = client.post("/[endpoint]", json={[data]})

    # Assert
    assert response.status_code == 201
    assert response.json()["[field]"] == [expected]
```

**Coverage Target:** Key user flows only

### Test Doubles

#### Fakes (Preferred)

**Location:** `tests/fixtures/fakes/`

**Purpose:** Lightweight, in-memory implementations of ports

**Example:**
```python
# tests/fixtures/fakes/[repository]_fake.py
class Fake[Repository]([Repository]Port):
    """In-memory implementation for testing"""

    def __init__(self):
        self._storage: Dict[str, [Entity]] = {}

    def save(self, entity: [Entity]) -> None:
        self._storage[entity.id] = entity

    def find_by_id(self, id: str) -> Optional[[Entity]]:
        return self._storage.get(id)
```

#### Mocks (Use Sparingly)

**Purpose:** Verify interactions between components

**Example:**
```python
from unittest.mock import Mock

def test_[service]_publishes_event():
    """Test that [service] publishes [event] when [condition]"""
    # Arrange
    event_bus = Mock()
    service = [Service](event_bus=event_bus)

    # Act
    service.[method]([params])

    # Assert
    event_bus.publish.assert_called_once_with(
        [Event]([expected_params])
    )
```

### TDD Workflow

**For New Features:**
1. ✅ Write failing application service test (High Gear)
2. ✅ Define/update ports if needed
3. ✅ Implement application service
4. ✅ Write domain tests if new business logic (Low Gear)
5. ✅ Implement driving adapter with integration test
6. ✅ Implement driven adapter with integration test
7. ✅ Write E2E test for happy path
8. ✅ Refactor continuously

**For Bug Fixes:**
1. ✅ Write failing test that reproduces the bug
2. ✅ Fix the bug
3. ✅ Verify test passes
4. ✅ Refactor if needed

### Test Naming Convention

```python
# Pattern: test_when_<condition>_should_<expected_behavior>
def test_when_user_is_inactive_should_raise_authentication_error():
    pass

def test_when_order_is_confirmed_should_publish_event():
    pass

def test_when_payment_fails_should_rollback_transaction():
    pass
```

---

## 🎨 Design Patterns

### Creational Patterns

#### Factory Method

**Location:** `[src/infrastructure/factories/]`

**Purpose:** `[Create objects without specifying exact class]`

**Implementation:**
| Factory | Creates | Used By | Status |
|---------|---------|---------|--------|
| `[Factory1]` | `[Object1, Object2]` | `[Component]` | ✅ Active |

**Example:**
```python
# src/infrastructure/factories/[factory].py
class [Factory]:
    """[Description]"""

    def create_[object](self, type: str, config: dict) -> [Interface]:
        if type == "[type1]":
            return [Implementation1](**config)
        elif type == "[type2]":
            return [Implementation2](**config)
        else:
            raise ValueError(f"Unknown type: {type}")
```

#### Builder

**Location:** `[src/domain/]`

**Purpose:** `[Construct complex objects step by step]`

**Implementation:**
| Builder | Builds | Used By | Status |
|---------|--------|---------|--------|
| `[Builder1]` | `[Entity1]` | `[Tests, Services]` | ✅ Active |

**Example:**
```python
# src/domain/[builder].py
class [Entity]Builder:
    """[Description]"""

    def __init__(self):
        self._[attr1] = None
        self._[attr2] = None

    def with_[attr1](self, value: [Type]) -> '[Entity]Builder':
        self._[attr1] = value
        return self

    def with_[attr2](self, value: [Type]) -> '[Entity]Builder':
        self._[attr2] = value
        return self

    def build(self) -> [Entity]:
        if not self._[attr1] or not self._[attr2]:
            raise ValueError("Missing required attributes")
        return [Entity](self._[attr1], self._[attr2])
```

### Structural Patterns

#### Adapter (Core Pattern)

**Location:** `[src/infrastructure/adapters/]`

**Purpose:** `[Convert interface of a class into another interface]`

**Implementation:**
| Adapter | Adapts | Implements Port | Status |
|---------|--------|----------------|--------|
| `[Adapter1]` | `[External System]` | `[Port1]` | ✅ Active |

**Example:**
```python
# src/infrastructure/adapters/driven/[adapter].py
class [Adapter]([Port]):
    """Adapts [external system] to [port] interface"""

    def __init__(self, [external_client]):
        self.[client] = [external_client]

    def [port_method](self, [params]) -> [ReturnType]:
        """[Description]"""
        # Convert to external format
        external_request = self._to_external_format([params])

        # Call external system
        external_response = self.[client].[method](external_request)

        # Convert to domain format
        return self._to_domain_format(external_response)
```

#### Decorator

**Location:** `[src/application/decorators/]`

**Purpose:** `[Add behavior to objects dynamically]`

**Implementation:**
| Decorator | Adds | Wraps | Status |
|-----------|------|-------|--------|
| `[Decorator1]` | `[Behavior]` | `[Service]` | ✅ Active |

**Example:**
```python
# src/application/decorators/[decorator].py
class [Decorator]:
    """[Description of what behavior is added]"""

    def __init__(self, wrapped: [Interface]):
        self._wrapped = wrapped

    def [method](self, [params]) -> [ReturnType]:
        """[Description]"""
        # Before behavior
        [pre_action]

        try:
            # Delegate to wrapped object
            result = self._wrapped.[method]([params])

            # After behavior (success)
            [post_action_success]

            return result
        except Exception as e:
            # After behavior (failure)
            [post_action_failure]
            raise
```

#### Facade

**Location:** `[src/application/services/]`

**Purpose:** `[Provide simplified interface to complex subsystem]`

**Implementation:**
Application services act as facades over domain complexity.

### Behavioral Patterns

#### Strategy

**Location:** `[src/domain/services/]`

**Purpose:** `[Define family of algorithms, make them interchangeable]`

**Implementation:**
| Strategy Interface | Implementations | Used By | Status |
|-------------------|----------------|---------|--------|
| `[Strategy1]` | `[Impl1, Impl2, Impl3]` | `[Entity]` | ✅ Active |

**Example:**
```python
# src/domain/services/[strategy].py
class [Strategy](ABC):
    """[Description of strategy family]"""

    @abstractmethod
    def [method](self, [params]) -> [ReturnType]:
        """[What this strategy does]"""
        pass

class [ConcreteStrategy1]([Strategy]):
    """[Description of this specific strategy]"""

    def [method](self, [params]) -> [ReturnType]:
        # Implementation 1
        pass

class [ConcreteStrategy2]([Strategy]):
    """[Description of this specific strategy]"""

    def [method](self, [params]) -> [ReturnType]:
        # Implementation 2
        pass
```

#### Command

**Location:** `[src/application/commands/]`

**Purpose:** `[Encapsulate request as an object]`

**Implementation:**
All use cases are implemented as command objects.

**Example:**
```python
# src/application/commands/[command].py
@dataclass(frozen=True)
class [Command]:
    """[Description of what this command represents]"""
    [param1]: [Type]
    [param2]: [Type]

# src/application/services/[handler].py
class [Command]Handler:
    """[Description of what this handler does]"""

    def handle(self, command: [Command]) -> [Result]:
        """[Description]"""
        # Handle command
        pass
```

#### Observer (Domain Events)

**Location:** `[src/domain/events/]`

**Purpose:** `[Define one-to-many dependency between objects]`

**Implementation:**
| Event | Published By | Subscribers | Status |
|-------|-------------|-------------|--------|
| `[Event1]` | `[Entity]` | `[Handler1, Handler2]` | ✅ Active |

**Example:**
```python
# src/domain/events/[event].py
@dataclass(frozen=True)
class [Event]:
    """[Description of what this event represents]"""
    occurred_at: datetime
    aggregate_id: str
    [data1]: [Type]
    [data2]: [Type]

# src/domain/entities/[entity].py
class [Entity]:
    def __init__(self):
        self._events: List[DomainEvent] = []

    def [business_method](self):
        # Business logic
        self._events.append([Event](...))

    def collect_events(self) -> List[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
```

### Python-Specific Patterns

#### Context Managers

**Purpose:** `[Resource management with guaranteed cleanup]`

**Example:**
```python
class [ResourceManager]:
    """[Description]"""

    def __enter__(self):
        # Setup
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup
        pass

# Usage
with [ResourceManager]() as resource:
    resource.[method]()
```

#### Generators

**Purpose:** `[Lazy evaluation for large datasets]`

**Example:**
```python
def [generator]([params]) -> Iterator[[Type]]:
    """[Description]"""
    for item in [large_dataset]:
        yield [process](item)
```

### Anti-Patterns (Avoided)

| Anti-Pattern | Why Avoided | Alternative |
|--------------|-------------|-------------|
| **Singleton** | Global state, hard to test | Dependency Injection |
| **God Object** | Too many responsibilities | Split into focused services |
| **Anemic Domain Model** | No business logic in entities | Rich domain model |
| **Magic Numbers** | Unclear meaning | Named constants |

---

## 🔌 External Integrations

### Integration Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Your Application]                                                 │
│         │                                                           │
│         ├──→ [Database]           (PostgreSQL/MongoDB/etc)         │
│         │    • Connection: [Details]                               │
│         │    • Auth: [Method]                                      │
│         │                                                           │
│         ├──→ [Message Queue]      (NATS/RabbitMQ/Kafka)           │
│         │    • Connection: [Details]                               │
│         │    • Topics: [List]                                      │
│         │                                                           │
│         ├──→ [External API 1]     (Service Name)                   │
│         │    • Endpoint: [URL]                                     │
│         │    • Auth: [Method]                                      │
│         │                                                           │
│         └──→ [External API 2]     (Service Name)                   │
│              • Endpoint: [URL]                                     │
│              • Auth: [Method]                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Current Integrations

| Integration | Type | Purpose | Adapter | Status | SLA |
|-------------|------|---------|---------|--------|-----|
| `[Service1]` | Database | `[Purpose]` | `[Adapter]` | ✅ Active | `[99.9%]` |
| `[Service2]` | API | `[Purpose]` | `[Adapter]` | ✅ Active | `[99.5%]` |
| `[Service3]` | Queue | `[Purpose]` | `[Adapter]` | ✅ Active | `[99.9%]` |

### Integration Details

#### [Integration1]

**Type:** `[Database/API/Queue/Cache/etc]`

**Purpose:** `[What this integration provides]`

**Connection Details:**
- **Endpoint:** `[URL or connection string]`
- **Protocol:** `[HTTP/gRPC/TCP/etc]`
- **Port:** `[Port number]`
- **Authentication:** `[Method: API Key/OAuth/Certificate/etc]`

**Configuration:**
```yaml
# config/[environment].yaml
[integration]:
  host: [hostname]
  port: [port]
  username: ${[ENV_VAR]}
  password: ${[ENV_VAR]}
  [other_config]: [value]
```

**Adapter Implementation:**
- **Location:** `[src/infrastructure/adapters/driven/[adapter].py]`
- **Implements Port:** `[PortName]`
- **Dependencies:** `[library1==x.y.z, library2==x.y.z]`

**Error Handling:**
| Error Type | Handling Strategy | Retry Policy |
|------------|------------------|--------------|
| `[Error1]` | `[Strategy]` | `[Policy]` |
| `[Error2]` | `[Strategy]` | `[Policy]` |

**Circuit Breaker:**
- **Enabled:** `[Yes/No]`
- **Failure Threshold:** `[X failures]`
- **Timeout:** `[X seconds]`
- **Reset Timeout:** `[X seconds]`

**Rate Limiting:**
- **Limit:** `[X requests per Y seconds]`
- **Strategy:** `[Token bucket/Leaky bucket/Fixed window]`

**Monitoring:**
- **Health Check:** `[Endpoint or method]`
- **Metrics:** `[request_count, error_rate, latency]`
- **Alerts:** `[When to alert]`

**Example Usage:**
```python
# src/infrastructure/adapters/driven/[adapter].py
class [Integration]Adapter([Port]):
    """[Description]"""

    def __init__(self, config: [Config]):
        self.client = [Client](
            host=config.host,
            port=config.port,
            auth=[Auth](config.username, config.password)
        )

    def [method](self, [params]) -> [ReturnType]:
        """[Description]"""
        try:
            response = self.client.[method]([params])
            return self._parse_response(response)
        except [SpecificError] as e:
            logger.error(f"[Integration] error: {e}")
            raise [DomainError](f"Failed to [action]: {e}")
```

**Testing:**
```python
# tests/integration/adapters/test_[adapter].py
def test_[adapter]_[behavior]():
    """Test [adapter] [does something]"""
    # Arrange
    config = [TestConfig]()
    adapter = [Adapter](config)

    # Act
    result = adapter.[method]([params])

    # Assert
    assert result.[attribute] == [expected]
```

---

## 🚀 Deployment Architecture

### Environment Overview

| Environment | Purpose | URL | Status | Auto-Deploy |
|-------------|---------|-----|--------|-------------|
| **Development** | Local development | `localhost:[port]` | ✅ Active | ❌ No |
| **Staging** | Pre-production testing | `[staging-url]` | ✅ Active | ✅ Yes |
| **Production** | Live system | `[production-url]` | ✅ Active | ⚠️ Manual |

### Deployment Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Load Balancer]                                                    │
│         │                                                           │
│         ├──→ [App Instance 1]  (Container/VM)                      │
│         │    • CPU: [X cores]                                       │
│         │    • RAM: [X GB]                                          │
│         │    • Disk: [X GB]                                         │
│         │                                                           │
│         ├──→ [App Instance 2]  (Container/VM)                      │
│         │    • CPU: [X cores]                                       │
│         │    • RAM: [X GB]                                          │
│         │    • Disk: [X GB]                                         │
│         │                                                           │
│         └──→ [App Instance N]  (Container/VM)                      │
│              • CPU: [X cores]                                       │
│              • RAM: [X GB]                                          │
│              • Disk: [X GB]                                         │
│                                                                     │
│  [Database Cluster]                                                 │
│         ├──→ [Primary]                                              │
│         └──→ [Replica 1, Replica 2]                                │
│                                                                     │
│  [Cache Cluster]                                                    │
│         └──→ [Cache Nodes]                                          │
│                                                                     │
│  [Message Queue Cluster]                                            │
│         └──→ [Queue Nodes]                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Infrastructure as Code

**Tool:** `[Terraform/CloudFormation/Pulumi/Ansible]`

**Location:** `[infrastructure/]`

**Resources:**
- `[Resource 1: Description]`
- `[Resource 2: Description]`
- `[Resource 3: Description]`

### CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CI/CD PIPELINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Commit] → [Push to Git]                                          │
│                  │                                                  │
│                  ▼                                                  │
│            [CI Triggers]                                            │
│                  │                                                  │
│                  ├──→ [Lint & Format Check]                        │
│                  │    • [Tool 1]                                    │
│                  │    • [Tool 2]                                    │
│                  │                                                  │
│                  ├──→ [Type Check]                                  │
│                  │    • [Tool]                                      │
│                  │                                                  │
│                  ├──→ [Unit Tests]                                  │
│                  │    • Coverage: [X%]                              │
│                  │                                                  │
│                  ├──→ [Integration Tests]                           │
│                  │    • Coverage: [X%]                              │
│                  │                                                  │
│                  ├──→ [Security Scan]                               │
│                  │    • [Tool]                                      │
│                  │                                                  │
│                  ├──→ [Build Docker Image]                          │
│                  │    • Tag: [strategy]                             │
│                  │                                                  │
│                  ├──→ [Push to Registry]                            │
│                  │    • Registry: [URL]                             │
│                  │                                                  │
│                  └──→ [Deploy]                                      │
│                       ├─→ [Staging] (auto)                          │
│                       └─→ [Production] (manual approval)            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Pipeline Configuration:**
- **Location:** `[.github/workflows/ or .gitlab-ci.yml]`
- **Trigger:** `[On push to main/develop]`
- **Duration:** `[~X minutes]`

### Deployment Strategy

**Strategy:** `[Blue-Green/Rolling/Canary]`

**Rollback Plan:**
1. `[Step 1]`
2. `[Step 2]`
3. `[Step 3]`

**Deployment Checklist:**
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Database migrations tested
- [ ] Configuration updated
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Stakeholders notified

### Configuration Management

**Method:** `[Environment variables/Config files/Secrets manager]`

**Secrets Storage:** `[Kubernetes Secrets/AWS Secrets Manager/Vault]`

**Configuration Files:**
```
config/
├── development.yaml
├── staging.yaml
└── production.yaml
```

**Environment Variables:**
| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `[VAR1]` | `[Purpose]` | ✅ Yes | `[None]` |
| `[VAR2]` | `[Purpose]` | ❌ No | `[Default]` |

---

## 📊 Observability

### Logging

**Framework:** `[structlog/standard logging/winston/etc]`

**Log Levels:**
| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Development debugging | `[Example message]` |
| **INFO** | Normal operations | `[Example message]` |
| **WARNING** | Potential issues | `[Example message]` |
| **ERROR** | Errors that need attention | `[Example message]` |
| **CRITICAL** | System failures | `[Example message]` |

**Log Format:**
```json
{
  "timestamp": "2025-10-13T12:00:00.000Z",
  "level": "INFO",
  "logger": "[module.name]",
  "message": "[Log message]",
  "context": {
    "request_id": "[uuid]",
    "user_id": "[uuid]",
    "[custom_field]": "[value]"
  }
}
```

**Log Aggregation:**
- **System:** `[ELK/Loki/CloudWatch/etc]`
- **Retention:** `[X days]`
- **Query Interface:** `[Kibana/Grafana/etc]`

**Sensitive Data Handling:**
- ✅ PII is masked/redacted
- ✅ Passwords never logged
- ✅ API keys never logged
- ✅ Credit card numbers never logged

### Metrics

**System:** `[Prometheus/StatsD/CloudWatch/etc]`

**Key Metrics:**

#### Application Metrics
| Metric | Type | Purpose | Alert Threshold |
|--------|------|---------|----------------|
| `[metric1]_total` | Counter | `[Purpose]` | `[Threshold]` |
| `[metric2]_duration_seconds` | Histogram | `[Purpose]` | `[Threshold]` |
| `[metric3]_active` | Gauge | `[Purpose]` | `[Threshold]` |

#### Business Metrics
| Metric | Type | Purpose | Alert Threshold |
|--------|------|---------|----------------|
| `[business_metric1]` | Counter | `[Purpose]` | `[Threshold]` |
| `[business_metric2]` | Gauge | `[Purpose]` | `[Threshold]` |

#### Infrastructure Metrics
| Metric | Type | Purpose | Alert Threshold |
|--------|------|---------|----------------|
| `cpu_usage_percent` | Gauge | CPU utilization | `> 80%` |
| `memory_usage_percent` | Gauge | Memory utilization | `> 85%` |
| `disk_usage_percent` | Gauge | Disk utilization | `> 90%` |
| `request_latency_p95` | Histogram | Response time | `> 500ms` |
| `error_rate` | Gauge | Error percentage | `> 1%` |

**Dashboards:**
- **Main Dashboard:** `[URL]` - Overview of system health
- **Performance Dashboard:** `[URL]` - Latency and throughput
- **Business Dashboard:** `[URL]` - Business KPIs

### Tracing

**System:** `[Jaeger/Zipkin/OpenTelemetry/etc]`

**Instrumentation:**
- ✅ HTTP requests
- ✅ Database queries
- ✅ External API calls
- ✅ Message queue operations
- ✅ Critical business operations

**Trace Context Propagation:**
```
[Client Request]
  trace_id: [uuid]
  span_id: [uuid]
      │
      ├──→ [Service A]
      │    span_id: [uuid]
      │    parent_span_id: [uuid]
      │
      ├──→ [Service B]
      │    span_id: [uuid]
      │    parent_span_id: [uuid]
      │
      └──→ [Database]
           span_id: [uuid]
           parent_span_id: [uuid]
```

**Sampling Strategy:** `[Always/Probabilistic/Rate-limited]`

**Retention:** `[X days]`

### Health Checks

**Endpoints:**
| Endpoint | Type | Checks | Response Time |
|----------|------|--------|---------------|
| `/health` | Liveness | `[App is running]` | `< 100ms` |
| `/ready` | Readiness | `[DB, Cache, Queue]` | `< 500ms` |

**Health Check Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T12:00:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "cache": {
      "status": "healthy",
      "latency_ms": 2
    },
    "message_queue": {
      "status": "healthy",
      "latency_ms": 3
    }
  }
}
```

### Alerting

**Alert Manager:** `[PagerDuty/Opsgenie/AlertManager/etc]`

**Alert Rules:**
| Alert | Condition | Severity | Notification |
|-------|-----------|----------|--------------|
| `[Alert1]` | `[Condition]` | Critical | `[Channel]` |
| `[Alert2]` | `[Condition]` | Warning | `[Channel]` |

**On-Call Rotation:** `[Schedule/Tool]`

---

## 🔒 Security Architecture

### Authentication

**Method:** `[OAuth2/JWT/API Keys/etc]`

**Flow Diagram:**
```
[Client]
   │
   ├──→ [1. Request with credentials]
   │
   ▼
[Auth Service]
   │
   ├──→ [2. Validate credentials]
   │
   ├──→ [3. Generate token]
   │
   ▼
[Client]
   │
   ├──→ [4. Request with token]
   │
   ▼
[API Gateway]
   │
   ├──→ [5. Validate token]
   │
   ├──→ [6. Extract claims]
   │
   ▼
[Application]
```

**Token Details:**
- **Type:** `[JWT/Opaque/etc]`
- **Expiration:** `[X hours/days]`
- **Refresh:** `[Yes/No]`
- **Storage:** `[Where tokens are stored]`

**Implementation:**
```python
# src/infrastructure/auth/[auth].py
class [Auth]Middleware:
    """[Description]"""

    async def __call__(self, request: Request):
        token = self._extract_token(request)
        if not token:
            raise UnauthorizedError("Missing authentication token")

        claims = self._validate_token(token)
        request.state.user = User.from_claims(claims)

        return await self._next(request)
```

### Authorization

**Method:** `[RBAC/ABAC/ACL/etc]`

**Roles:**
| Role | Permissions | Description |
|------|-------------|-------------|
| `[Role1]` | `[Permission1, Permission2]` | `[Description]` |
| `[Role2]` | `[Permission1, Permission3]` | `[Description]` |

**Permission Matrix:**
| Resource | Create | Read | Update | Delete |
|----------|--------|------|--------|--------|
| `[Resource1]` | `[Role1]` | `[Role1, Role2]` | `[Role1]` | `[Role1]` |
| `[Resource2]` | `[Role2]` | `[Role1, Role2]` | `[Role2]` | `[Role2]` |

**Implementation:**
```python
# src/infrastructure/auth/[authz].py
def require_permission(permission: str):
    """Decorator to check permissions"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user = request.state.user
            if not user.has_permission(permission):
                raise ForbiddenError(f"Missing permission: {permission}")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@require_permission("resource:write")
async def create_resource(request: Request):
    pass
```

### Data Encryption

**At Rest:**
- **Database:** `[Encryption method]`
- **File Storage:** `[Encryption method]`
- **Backups:** `[Encryption method]`

**In Transit:**
- **TLS Version:** `[1.2/1.3]`
- **Cipher Suites:** `[List]`
- **Certificate Management:** `[Let's Encrypt/etc]`

**Sensitive Data:**
| Data Type | Encryption | Key Management |
|-----------|-----------|----------------|
| `[PII]` | `[Method]` | `[KMS/Vault/etc]` |
| `[Passwords]` | `[bcrypt/argon2]` | N/A (hashed) |
| `[API Keys]` | `[Method]` | `[KMS/Vault/etc]` |

### Security Scanning

**Tools:**
| Tool | Purpose | Frequency | Status |
|------|---------|-----------|--------|
| `[Tool1]` | Dependency scanning | On commit | ✅ Active |
| `[Tool2]` | SAST | On commit | ✅ Active |
| `[Tool3]` | DAST | Weekly | ✅ Active |
| `[Tool4]` | Container scanning | On build | ✅ Active |

**Vulnerability Management:**
- **Tracking:** `[Tool/System]`
- **SLA:** `[Critical: X days, High: Y days, etc]`
- **Process:** `[Description of remediation process]`

### Compliance

**Standards:**
- `[GDPR/HIPAA/SOC2/etc]` - `[Status]`
- `[Standard2]` - `[Status]`

**Data Retention:**
| Data Type | Retention Period | Deletion Method |
|-----------|-----------------|-----------------|
| `[Type1]` | `[X days/years]` | `[Hard delete/Soft delete]` |
| `[Type2]` | `[X days/years]` | `[Hard delete/Soft delete]` |

**Audit Logging:**
- **Events Logged:** `[List of auditable events]`
- **Retention:** `[X years]`
- **Access:** `[Who can access audit logs]`

---

## ⚡ Performance Architecture

### Performance Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Response Time (p50)** | `< [X]ms` | `[Y]ms` | `[✅/⚠️/❌]` |
| **Response Time (p95)** | `< [X]ms` | `[Y]ms` | `[✅/⚠️/❌]` |
| **Response Time (p99)** | `< [X]ms` | `[Y]ms` | `[✅/⚠️/❌]` |
| **Throughput** | `> [X] req/s` | `[Y] req/s` | `[✅/⚠️/❌]` |
| **Error Rate** | `< [X]%` | `[Y]%` | `[✅/⚠️/❌]` |
| **Uptime** | `> [X]%` | `[Y]%` | `[✅/⚠️/❌]` |

### Performance Bottlenecks

| Component | Bottleneck | Impact | Mitigation | Status |
|-----------|-----------|--------|------------|--------|
| `[Component1]` | `[Issue]` | `[Impact]` | `[Solution]` | `[Status]` |
| `[Component2]` | `[Issue]` | `[Impact]` | `[Solution]` | `[Status]` |

### Caching Strategy

**Layers:**
```
[Client]
   │
   ├──→ [Browser Cache] (TTL: [X]s)
   │
   ▼
[CDN] (TTL: [X]s)
   │
   ▼
[Application Cache] (TTL: [X]s)
   │
   ├──→ [In-Memory Cache] (Redis/Memcached)
   │
   ▼
[Database Query Cache] (TTL: [X]s)
```

**Cache Policies:**
| Resource | Strategy | TTL | Invalidation |
|----------|----------|-----|--------------|
| `[Resource1]` | `[LRU/LFU/TTL]` | `[X]s` | `[On update/Manual]` |
| `[Resource2]` | `[LRU/LFU/TTL]` | `[X]s` | `[On update/Manual]` |

### Database Optimization

**Indexes:**
| Table | Columns | Type | Purpose |
|-------|---------|------|---------|
| `[table1]` | `[col1, col2]` | `[B-tree/Hash]` | `[Purpose]` |
| `[table2]` | `[col1]` | `[B-tree/Hash]` | `[Purpose]` |

**Query Optimization:**
- ✅ N+1 queries eliminated
- ✅ Proper use of indexes
- ✅ Query result caching
- ✅ Connection pooling

**Connection Pool:**
- **Min Connections:** `[X]`
- **Max Connections:** `[Y]`
- **Timeout:** `[Z]s`

### Load Testing

**Tool:** `[k6/JMeter/Locust/etc]`

**Scenarios:**
| Scenario | Users | Duration | Target RPS | Status |
|----------|-------|----------|------------|--------|
| `[Scenario1]` | `[X]` | `[Y]min` | `[Z]` | `[Pass/Fail]` |
| `[Scenario2]` | `[X]` | `[Y]min` | `[Z]` | `[Pass/Fail]` |

**Results:**
```
Last Run: [YYYY-MM-DD]
Peak RPS: [X]
Avg Response Time: [Y]ms
p95 Response Time: [Z]ms
Error Rate: [W]%
```

### Scalability

**Horizontal Scaling:**
- **Current Instances:** `[X]`
- **Max Instances:** `[Y]`
- **Auto-scaling:** `[Enabled/Disabled]`
- **Trigger:** `[CPU > X% or Memory > Y%]`

**Vertical Scaling:**
- **Current Resources:** `[X CPU, Y GB RAM]`
- **Max Resources:** `[X CPU, Y GB RAM]`

**Database Scaling:**
- **Read Replicas:** `[X]`
- **Sharding:** `[Yes/No]`
- **Partitioning:** `[Yes/No]`

---

## 🚧 Technical Debt & Roadmap

### Technical Debt Inventory

**Total Debt:** `[X hours/days/weeks]`

**Debt by Category:**
| Category | Items | Estimated Effort | Priority |
|----------|-------|-----------------|----------|
| **Architecture** | `[X]` | `[Y hours]` | `[High/Medium/Low]` |
| **Code Quality** | `[X]` | `[Y hours]` | `[High/Medium/Low]` |
| **Testing** | `[X]` | `[Y hours]` | `[High/Medium/Low]` |
| **Documentation** | `[X]` | `[Y hours]` | `[High/Medium/Low]` |
| **Performance** | `[X]` | `[Y hours]` | `[High/Medium/Low]` |
| **Security** | `[X]` | `[Y hours]` | `[High/Medium/Low]` |

### Known Issues

#### High Priority

| Issue | Impact | Affected Components | Remediation Plan | Target Date |
|-------|--------|-------------------|------------------|-------------|
| `[Issue1]` | `[Impact]` | `[Components]` | `[Plan]` | `[YYYY-MM-DD]` |
| `[Issue2]` | `[Impact]` | `[Components]` | `[Plan]` | `[YYYY-MM-DD]` |

#### Medium Priority

| Issue | Impact | Affected Components | Remediation Plan | Target Date |
|-------|--------|-------------------|------------------|-------------|
| `[Issue1]` | `[Impact]` | `[Components]` | `[Plan]` | `[YYYY-MM-DD]` |

#### Low Priority

| Issue | Impact | Affected Components | Remediation Plan | Target Date |
|-------|--------|-------------------|------------------|-------------|
| `[Issue1]` | `[Impact]` | `[Components]` | `[Plan]` | `[YYYY-MM-DD]` |

### Deprecated Components

| Component | Deprecated Date | Reason | Replacement | Removal Date | Migration Status |
|-----------|----------------|--------|-------------|--------------|------------------|
| `[Component1]` | `[YYYY-MM-DD]` | `[Reason]` | `[New Component]` | `[YYYY-MM-DD]` | `[X%]` |
| `[Component2]` | `[YYYY-MM-DD]` | `[Reason]` | `[New Component]` | `[YYYY-MM-DD]` | `[X%]` |

### Roadmap

#### Q[X] [YEAR] (Current Quarter)

**Theme:** `[Theme description]`

**Objectives:**
- `[Objective 1]`
- `[Objective 2]`
- `[Objective 3]`

**Deliverables:**
| Feature/Improvement | Status | Owner | Target Date |
|-------------------|--------|-------|-------------|
| `[Feature1]` | `[In Progress/Planned]` | `[Name]` | `[YYYY-MM-DD]` |
| `[Feature2]` | `[In Progress/Planned]` | `[Name]` | `[YYYY-MM-DD]` |

#### Q[X+1] [YEAR] (Next Quarter)

**Theme:** `[Theme description]`

**Planned Features:**
- `[Feature 1]`
- `[Feature 2]`
- `[Feature 3]`

#### Q[X+2] [YEAR]

**Theme:** `[Theme description]`

**Planned Features:**
- `[Feature 1]`
- `[Feature 2]`

### Refactoring Priorities

| Priority | Component | Reason | Effort | Impact | Status |
|----------|-----------|--------|--------|--------|--------|
| 1 | `[Component1]` | `[Reason]` | `[X days]` | `[High/Medium/Low]` | `[Status]` |
| 2 | `[Component2]` | `[Reason]` | `[X days]` | `[High/Medium/Low]` | `[Status]` |
| 3 | `[Component3]` | `[Reason]` | `[X days]` | `[High/Medium/Low]` | `[Status]` |

---

## 📝 Architectural Decision Records (ADRs)

### ADR Process

**When to Create an ADR:**
- Introducing a new major technology
- Changing architectural patterns
- Deviating from established conventions
- Making decisions with long-term impact
- Resolving significant technical debates

**ADR Template:**
```markdown
# ADR-XXX: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-YYY]
**Date:** YYYY-MM-DD
**Deciders:** [Names]
**Tags:** [architecture, database, security, etc]

## Context
[Describe the problem, forces at play, and context. What was the state of the system?]

## Decision
[Describe the decision made. Be clear, specific, and unambiguous.]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

### Neutral
- [Impact 1]

## Implementation
[How will this be implemented? What is the migration path?]

## Alternatives Considered
- **Alternative 1:** [Why rejected]
- **Alternative 2:** [Why rejected]

## References
- [Link to relevant documentation]
- [Link to discussion/RFC]
```

### Active ADRs

| ADR | Title | Date | Status | Tags |
|-----|-------|------|--------|------|
| [ADR-001](docs/adr/0001-xxx.md) | `[Title]` | `[YYYY-MM-DD]` | Accepted | `[tags]` |
| [ADR-002](docs/adr/0002-xxx.md) | `[Title]` | `[YYYY-MM-DD]` | Accepted | `[tags]` |
| [ADR-003](docs/adr/0003-xxx.md) | `[Title]` | `[YYYY-MM-DD]` | Accepted | `[tags]` |

### Superseded ADRs

| ADR | Title | Date | Superseded By | Reason |
|-----|-------|------|---------------|--------|
| [ADR-XXX](docs/adr/0xxx-xxx.md) | `[Title]` | `[YYYY-MM-DD]` | ADR-YYY | `[Reason]` |

### Example ADR

```markdown
# ADR-001: Use Hexagonal Architecture

**Status:** Accepted
**Date:** 2025-10-13
**Deciders:** Architecture Team
**Tags:** architecture, design-patterns

## Context
We need a software architecture that:
- Decouples business logic from external technologies
- Enables comprehensive testing without external dependencies
- Allows swapping implementations without changing core logic
- Supports long-term maintainability

Traditional layered architecture creates tight coupling between layers,
making testing difficult and technology changes expensive.

## Decision
Adopt Hexagonal Architecture (Ports & Adapters pattern) as the standard
architecture for all new development.

## Consequences

### Positive
- Business logic is pure and testable in isolation
- External technologies (databases, APIs) are easily swappable
- Clear boundaries between layers
- Aligns with TDD practices
- Reduces technical debt

### Negative
- Initial learning curve for team
- More interfaces to maintain
- May seem over-engineered for simple features

### Neutral
- Requires discipline to maintain boundaries
- Need to educate new team members

## Implementation
1. Create standard project structure (see Directory Structure section)
2. Migrate existing code incrementally
3. Establish code review checklist for architecture compliance
4. Provide training on hexagonal architecture principles

## Alternatives Considered
- **Traditional Layered Architecture:** Rejected - tight coupling, poor testability
- **Clean Architecture:** Rejected - too prescriptive, excessive layering
- **Microservices:** Rejected - premature for current scale

## References
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [TDD Architecture Guide](work-prompts/tdd-architecture-prompts.md)
```

---

## 🔧 Development Workflow

### Feature Development Checklist

#### Planning Phase
- [ ] Feature requirements documented
- [ ] Use case identified
- [ ] Acceptance criteria defined
- [ ] Technical approach discussed
- [ ] Effort estimated

#### Design Phase
- [ ] Domain model designed (if new entities)
- [ ] Ports identified (if new integrations)
- [ ] API contract defined
- [ ] Database schema designed (if needed)
- [ ] Security considerations reviewed

#### Implementation Phase (TDD)
1. [ ] Write failing application service test (High Gear)
2. [ ] Define/update ports if needed
3. [ ] Implement application service
4. [ ] Write domain tests if new business logic (Low Gear)
5. [ ] Implement domain logic
6. [ ] Implement driving adapter (API/MCP/CLI) with integration test
7. [ ] Implement driven adapter (DB/External API) with integration test
8. [ ] Write E2E test for happy path
9. [ ] Refactor continuously

#### Quality Phase
- [ ] All tests passing
- [ ] Code coverage meets targets
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Security scan passes
- [ ] Performance acceptable
- [ ] Documentation updated

#### Review Phase
- [ ] Code reviewed by peer
- [ ] Architecture compliance verified
- [ ] Security reviewed (if applicable)
- [ ] Performance reviewed (if applicable)
- [ ] Feedback addressed

#### Deployment Phase
- [ ] Merged to main branch
- [ ] CI/CD pipeline passes
- [ ] Deployed to staging
- [ ] Smoke tests pass
- [ ] Deployed to production (if approved)
- [ ] Monitoring verified
- [ ] Stakeholders notified

### Code Review Checklist

#### Architecture
- [ ] Follows hexagonal architecture boundaries
- [ ] Domain layer has no external dependencies
- [ ] Application layer depends only on domain
- [ ] Infrastructure layer implements ports correctly
- [ ] Dependency direction is correct

#### Code Quality
- [ ] Follows PEP 8 / style guide
- [ ] Names are descriptive and intention-revealing
- [ ] Functions are small and focused
- [ ] No code duplication
- [ ] Error handling is appropriate
- [ ] No magic numbers or strings

#### Testing
- [ ] Tests follow FIRST principles
- [ ] Test coverage meets targets
- [ ] Tests are readable and maintainable
- [ ] Test doubles used appropriately
- [ ] Edge cases covered

#### Security
- [ ] Input validation present
- [ ] Authentication/authorization checked
- [ ] Sensitive data not logged
- [ ] SQL injection prevented
- [ ] XSS prevented (if applicable)

#### Performance
- [ ] No N+1 queries
- [ ] Appropriate use of caching
- [ ] Database indexes present
- [ ] No blocking operations in async code

#### Documentation
- [ ] Public APIs documented
- [ ] Complex logic explained
- [ ] ADR created (if significant decision)
- [ ] README updated (if needed)

### Git Workflow

**Branch Strategy:** `[GitFlow/GitHub Flow/Trunk-based]`

**Branch Naming:**
```
feature/[ticket-id]-[short-description]
bugfix/[ticket-id]-[short-description]
hotfix/[ticket-id]-[short-description]
refactor/[short-description]
```

**Commit Message Format:**
```
[type]([scope]): [subject]

[body]

[footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Adding tests
- `docs`: Documentation changes
- `chore`: Maintenance tasks

**Example:**
```
feat(auth): add OAuth2 authentication

Implement OAuth2 authentication flow with support for
Google and GitHub providers.

Closes #123
```

### Release Process

1. **Prepare Release**
   - [ ] Create release branch
   - [ ] Update version number
   - [ ] Update CHANGELOG
   - [ ] Run full test suite

2. **Deploy to Staging**
   - [ ] Deploy release branch
   - [ ] Run smoke tests
   - [ ] Perform manual testing

3. **Deploy to Production**
   - [ ] Get approval
   - [ ] Deploy to production
   - [ ] Monitor for errors
   - [ ] Verify key metrics

4. **Post-Release**
   - [ ] Tag release in Git
   - [ ] Merge to main
   - [ ] Announce release
   - [ ] Update documentation

---

## 🔍 Troubleshooting Guide

### Common Issues

#### Issue: [Common Problem 1]

**Symptoms:**
- `[Symptom 1]`
- `[Symptom 2]`

**Possible Causes:**
1. `[Cause 1]`
2. `[Cause 2]`

**Resolution Steps:**
1. `[Step 1]`
2. `[Step 2]`
3. `[Step 3]`

**Prevention:**
- `[How to prevent this issue]`

#### Issue: [Common Problem 2]

**Symptoms:**
- `[Symptom 1]`
- `[Symptom 2]`

**Possible Causes:**
1. `[Cause 1]`
2. `[Cause 2]`

**Resolution Steps:**
1. `[Step 1]`
2. `[Step 2]`

**Prevention:**
- `[How to prevent this issue]`

### Debugging Checklist

#### Application Not Starting
- [ ] Check environment variables
- [ ] Verify database connectivity
- [ ] Check port availability
- [ ] Review application logs
- [ ] Verify dependencies installed

#### Performance Issues
- [ ] Check database query performance
- [ ] Review cache hit rates
- [ ] Check for N+1 queries
- [ ] Review connection pool settings
- [ ] Check for memory leaks

#### Integration Failures
- [ ] Verify external service availability
- [ ] Check authentication credentials
- [ ] Review network connectivity
- [ ] Check rate limits
- [ ] Review adapter configuration

### Diagnostic Commands

```bash
# Check application health
curl http://localhost:[port]/health

# View recent logs
tail -f logs/[app].log

# Check database connectivity
[database-cli] -h [host] -p [port] -u [user]

# View running processes
ps aux | grep [app-name]

# Check port usage
lsof -i :[port]

# View system resources
top
htop

# Check disk space
df -h

# View network connections
netstat -an | grep [port]
```

### Log Analysis

**Common Error Patterns:**
| Pattern | Meaning | Action |
|---------|---------|--------|
| `[Error Pattern 1]` | `[Meaning]` | `[Action]` |
| `[Error Pattern 2]` | `[Meaning]` | `[Action]` |

**Log Locations:**
- Application logs: `[path]`
- Error logs: `[path]`
- Access logs: `[path]`
- Audit logs: `[path]`

---

## 📚 Glossary

### Domain Terms

| Term | Definition | Example |
|------|------------|---------|
| `[Term1]` | `[Definition]` | `[Example]` |
| `[Term2]` | `[Definition]` | `[Example]` |
| `[Term3]` | `[Definition]` | `[Example]` |

### Technical Terms

| Term | Definition | Related Concepts |
|------|------------|------------------|
| **Aggregate** | Cluster of entities and value objects treated as a single unit | Entity, Value Object, Aggregate Root |
| **Adapter** | Implementation of a port that connects to external systems | Port, Hexagonal Architecture |
| **Port** | Interface that defines a contract for external interactions | Adapter, Dependency Inversion |
| **Entity** | Object with identity that persists over time | Domain Model, Aggregate |
| **Value Object** | Immutable object defined by its attributes | Domain Model, Entity |
| **Use Case** | Application-specific business rule | Application Service, Command |
| **Domain Event** | Something that happened in the domain | Event Sourcing, Observer Pattern |
| **Repository** | Abstraction for data access | Persistence, Adapter |
| **DTO** | Data Transfer Object for crossing boundaries | API, Serialization |
| **ADR** | Architectural Decision Record | Documentation, Governance |

### Acronyms

| Acronym | Full Form | Description |
|---------|-----------|-------------|
| **API** | Application Programming Interface | Interface for software interaction |
| **CRUD** | Create, Read, Update, Delete | Basic data operations |
| **DTO** | Data Transfer Object | Object for data transfer |
| **ORM** | Object-Relational Mapping | Database abstraction |
| **TDD** | Test-Driven Development | Development methodology |
| **CI/CD** | Continuous Integration/Continuous Deployment | Automation pipeline |
| **SLA** | Service Level Agreement | Service guarantee |
| **RPS** | Requests Per Second | Throughput metric |
| **TTL** | Time To Live | Cache expiration |
| **JWT** | JSON Web Token | Authentication token |

---

## 📜 Document History

### Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| `1.0.0` | `[YYYY-MM-DD]` | `[Name]` | Initial version |
| `1.1.0` | `[YYYY-MM-DD]` | `[Name]` | `[Summary of changes]` |
| `1.2.0` | `[YYYY-MM-DD]` | `[Name]` | `[Summary of changes]` |

### Recent Changes

**[YYYY-MM-DD]** - Version X.Y.Z
- `[Change 1]`
- `[Change 2]`
- `[Change 3]`

**[YYYY-MM-DD]** - Version X.Y.Z
- `[Change 1]`
- `[Change 2]`

### Review History

| Review Date | Reviewer | Findings | Actions Taken |
|-------------|----------|----------|---------------|
| `[YYYY-MM-DD]` | `[Name]` | `[Findings]` | `[Actions]` |
| `[YYYY-MM-DD]` | `[Name]` | `[Findings]` | `[Actions]` |

### Maintenance Schedule

**Review Frequency:** `[Monthly/Quarterly]`

**Next Review:** `[YYYY-MM-DD]`

**Review Owners:** `[Names]`

**Update Triggers:**
- New major feature added
- Architecture pattern changed
- Technology stack updated
- Significant refactoring completed
- ADR created or updated
- Performance targets changed
- Security requirements changed

---

## 🎯 Quick Reference

### Key Contacts

| Role | Name | Email | Slack |
|------|------|-------|-------|
| **Product Owner** | `[Name]` | `[email]` | `[@handle]` |
| **Tech Lead** | `[Name]` | `[email]` | `[@handle]` |
| **DevOps Lead** | `[Name]` | `[email]` | `[@handle]` |
| **Security Lead** | `[Name]` | `[email]` | `[@handle]` |

### Important Links

| Resource | URL | Purpose |
|----------|-----|---------|
| **Repository** | `[GitHub/GitLab URL]` | Source code |
| **CI/CD** | `[URL]` | Build pipeline |
| **Staging** | `[URL]` | Staging environment |
| **Production** | `[URL]` | Production environment |
| **Monitoring** | `[URL]` | Dashboards |
| **Documentation** | `[URL]` | Full documentation |
| **Issue Tracker** | `[URL]` | Bug/feature tracking |

### Command Cheat Sheet

```bash
# Development
[command to start dev server]
[command to run tests]
[command to run linter]
[command to format code]

# Database
[command to run migrations]
[command to seed database]
[command to backup database]

# Deployment
[command to build]
[command to deploy to staging]
[command to deploy to production]

# Troubleshooting
[command to view logs]
[command to check health]
[command to restart service]
```

---

## ✅ Completion Checklist

Before marking this document as complete, ensure:

- [ ] All `[PLACEHOLDERS]` replaced with actual values
- [ ] All diagrams updated with actual components
- [ ] Directory structure matches actual project
- [ ] All sections filled with real data
- [ ] ADRs created for significant decisions
- [ ] Technical debt documented
- [ ] Roadmap defined
- [ ] Contact information current
- [ ] Links verified and working
- [ ] Document reviewed by team
- [ ] "How to Fill This Template" section deleted
- [ ] Committed to version control

---

**Document Version:** `X.Y.Z`
**Last Updated:** `YYYY-MM-DD`
**Next Review:** `YYYY-MM-DD`
**Status:** `[Draft | Active | Deprecated]`

---

## 📄 License

`[License information if applicable]`

---

**End of Document**

*This document is a living blueprint and must be updated regularly to reflect the current state of the architecture.*
