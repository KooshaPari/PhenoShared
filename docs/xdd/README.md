# xDD Methodologies Compendium

[![Release](https://img.shields.io/github/v/release/KooshaPari/phenoXdd?include_prereleases&sort=semver)](https://github.com/KooshaPari/phenoXdd/releases)
[![License](https://img.shields.io/github/license/KooshaPari/phenoXdd)](LICENSE)
[![Phenotype](https://img.shields.io/badge/Phenotype-org-blueviolet)](https://github.com/KooshaPari)


**See also (org hub):** [`docs/engineering/100-PRACTICES.md`](../docs/engineering/100-PRACTICES.md) (180+ numbered practices), [`WRAP_AND_ROLL_GOVERNANCE.md`](../docs/engineering/WRAP_AND_ROLL_GOVERNANCE.md), [`TOP_LEVEL_REPO_LAYOUT.md`](../docs/engineering/TOP_LEVEL_REPO_LAYOUT.md), and [`plans/xdd-hexagonal-reference-architecture.md`](../plans/xdd-hexagonal-reference-architecture.md).

## Executive Summary

This repository documents **100+** extreme/extended Development Disciplines (xDD) - a comprehensive collection of software engineering methodologies, practices, processes, and principles for building maintainable, extensible, and high-quality software systems.

---

## Table of Contents

1. [Core Development Disciplines](#core-development-disciplines)
2. [Architecture Principles](#architecture-principles)
3. [Design Principles](#design-principles)
4. [Testing Methodologies](#testing-methodologies)
5. [Documentation Methodologies](#documentation-methodologies)
6. [Process & Workflow](#process--workflow)
7. [Code Quality Practices](#code-quality-practices)
8. [Collaboration & Team Practices](#collaboration--team-practices)
9. [Operational Practices](#operational-practices)
10. [Advanced Topics](#advanced-topics)
11. [Domain-Driven Design Extensions](#domain-driven-design-extensions)
12. [Platform-Specific Practices](#platform-specific-practices)

---

## Core Development Disciplines

### 1. TDD - Test-Driven Development
- Write tests BEFORE writing implementation code
- Red-Green-Refactor cycle
- Tests as specification
- _References: Beck 2003, Evans 2003_

### 2. BDD - Behavior-Driven Development
- Ubiquitous language shared between tech and business
- Gherkin syntax (Given-When-Then)
- Living documentation
- _References: North 2006, Smart 2014_

### 3. ATDD - Acceptance Test-Driven Development
- Tests written from acceptance criteria
- Collaboration between devs, QA, and business
- Executable specifications
- _References: Adzic 2009_

### 4. SDD - Specification-Driven Development
- Formal specifications as first-class artifacts
- Spec-first implementation
- Specification coverage metrics
- _References: IEEE 829_

### 5. FDD - Feature-Driven Development
- Model features collaboratively
- Build by feature
- Feature-based planning
- _References: Palmer 2002_

### 6. Bite-Size Development
- Small, incremental changes
- Single-responsibility commits
- Quick feedback cycles
- _Internal practice_

### 7. Example-Driven Development (EDD)
- Learn through concrete examples
- Property-based testing inspiration
- Exploratory specification
- _References: Fry 2014_

### 8. Chaos Engineering (TBD - Test-By Destruction)
- Deliberately inject failures
- Verify system resilience
- Production hypothesis testing
- _References: Netflix Chaos Monkey_

### 9. PRD - Property-Based Development
- Define invariants and properties
- Generate random test cases
- Formal verification lite
- _References: QuickCheck, Haskell_

### 10. Contract-First Development (CFD)
- Define API contracts before implementation
- Consumer-driven contracts
- Contract testing
- _References: REST, GraphQL, gRPC_

---

## Architecture Principles

### 11. Hexagonal Architecture (Ports & Adapters)
- Core business logic isolated
- Ports define interfaces
- Adapters implement external concerns
- _References: Cockburn 2005, Larman 2001_

### 12. Clean Architecture
- Dependency inversion principle
- Layers: Entities, Use Cases, Interface Adapters, Frameworks
- _References: Uncle Bob (Robert C. Martin)_

### 13. Onion Architecture
- Core domain at center
- concentric rings of dependencies
- Infrastructure pushed to edges
- _References: Jeffrey Palermo_

### 14. CQRS - Command Query Responsibility Segregation
- Separate read and write models
- Event sourcing for write model
- Optimized read representations
- _References: Greg Young_

### 15. Event Sourcing
- Store events, not state
- Complete audit trail
- Time-travel debugging
- _References: EventStore, Greg Young_

### 16. Event-Driven Architecture
- Decoupled via events
- Async communication
- Event pub/sub patterns
- _References:EDA patterns_

### 17. Microservices Architecture
- Small, autonomous services
- Single responsibility per service
- Decentralized data management
- _References: Richardson 2014_

### 18. Service-Oriented Architecture (SOA)
- Service reuse
- Enterprise service bus
- Service contracts
- _References: OASIS_

### 19. Serverless Architecture
- Function as a Service
- Event-driven execution
- Stateless compute
- _References: AWS Lambda docs_

### 20. Edge Computing Architecture
- Process at network edge
- Low latency
- Distributed intelligence
- _References: Edge computing patterns_

### 21. Reactive Architecture
- Responsive systems
- Message-driven
- Elastic and resilient
- _References: Reactive Manifesto_

### 22. Space-Based Architecture
- Distributed memory
- Processing grid
- Async messaging
- _References: Nygard 2007_

### 23. Pipeline Architecture
- Linear data flow
- Filter stages
- Pipe connections
- _References: Pipes and Filters pattern_

### 24. Microkernel Architecture
- Core system with plugins
- Minimal core functionality
- Extension points
- _References: Plugin patterns_

### 25. Modular Monolith
- Well-defined modules
- Enforced boundaries
- Single deployment, clear separation
- _Internal practice_

---

## Design Principles

### 26. SOLID Principles
- **S**ingle Responsibility
- **O**pen/Closed
- **L**iskov Substitution
- **I**nterface Segregation
- **D**ependency Inversion
- _References: Robert C. Martin_

### 27. DRY - Don't Repeat Yourself
- Single source of truth
- Eliminate duplication
- Abstract common patterns
- _References: Pragmatic Programmer_

### 28. KISS - Keep It Simple, Stupid
- Prefer simplicity
- Avoid over-engineering
- YAGNI - You Aren't Gonna Need It
- _References: Occam's razor_

### 29. POLA - Principle of Least Astonishment
- Behavior matches expectations
- Consistent interfaces
- Predictable systems
- _References: UI design principles_

### 30. LoD - Law of Demeter
- Talk only to immediate friends
- Minimize coupling
- Encapsulation
- _References: Demeter project_

### 31. ACP - Abstractions, Coffee, Pastries (Principle of Relevant Abstractions)
- Use appropriate abstraction levels
- Don't over-abstract
- Code for readability
- _Internal humor/principle_

### 32. Encapsulate What Varies
- Identify variability
- Isolate behind interfaces
- Enable substitution
- _References: GoF patterns_

### 33. Favor Composition over Inheritance
- Flexible structures
- Runtime behavior
- Reduced coupling
- _References: GoF Design Patterns_

### 34. Program to Interfaces, Not Implementations
- Decoupled design
- Pluggable components
- Testability
- _References: GoF, Java best practices_

### 35. Stable Abstractions Principle
- Abstract at stable points
- Concrete at volatile points
- Acyclic dependencies
- _References: Robert C. Martin_

---

## Testing Methodologies

### 36. Test Pyramid
- Many unit tests
- Fewer integration tests
- Fewest E2E tests
- _References: Mike Cohn_

### 37. Testing Trophy
- More integration tests
- Few unit tests
- Some E2E
- _References: Kent C. Dodds_

### 38. ICE Testing - Input Coverage Estimation
- Input space analysis
- Boundary testing
- Equivalence partitioning
- _Internal practice_

### 39. Mutation Testing
- Inject artificial bugs
- Verify test quality
- Measure test effectiveness
- _References: Pitest_

### 40. Property-Based Testing
- Generate random inputs
- Verify invariants
- Shrink failures
- _References: QuickCheck_

### 41. Stateful/Model-Based Testing
- Define state machines
- Generate sequences
- Verify properties
- _References: state machine testing_

### 42. Snapshot Testing
- Capture output snapshots
- Detect regressions
- Approve changes intentionally
- _References: Jest, Swift_

### 43. Golden Master Testing
- Record all outputs
- Compare against baseline
- Useful for legacy systems
- _References: Characterization tests_

### 44. Conformance Testing
- Verify protocol compliance
- Test specifications
- Interoperability
- _References: RFC testing_

### 45. Fuzz Testing
- Random inputs
- Crash detection
- Security testing
- _References: AFL, libFuzzer_

### 46. Penetration Testing
- Simulate attacks
- Security validation
- Vulnerability assessment
- _References: OWASP_

### 47. Performance Testing
- Load testing
- Stress testing
- Endurance testing
- _References: JMeter, k6_

### 48. Smoke Testing
- Quick sanity checks
- Critical path coverage
- Build validation
- _References: QA practices_

### 49. Sanity Testing
- Verify specific fixes
- Narrow scope
- Quick turnaround
- _References: QA practices_

### 50. Regression Testing
- Prevent feature breakage
- Automated regression suite
- Continuous validation
- _References: QA practices_

### 51. A/B Testing
- Compare variants
- Statistical validation
- User behavior analysis
- _References: Product analytics_

### 52. Canary Testing
- Gradual rollout
- Monitor metrics
- Quick rollback capability
- _References: Deployment practices_

### 53. Shadow Testing
- Run new system parallel
- Compare outputs
- No real traffic
- _References: Migration practices_

---

## Documentation Methodologies

### 54. Documentation-Driven Development
- Write docs first
- API documentation as specification
- Docs as deliverable
- _References: Sphinx, Javadoc_

### 55. Living Documentation
- Documentation in version control
- Generated from code
- Always current
- _References: Bryan Dollery_

### 56. ADRs - Architecture Decision Records
- Document architectural choices
- Context and consequences
- Track rationale
- _References: Michael Nygard_

### 57. C4 Model Documentation
- Context, Containers, Components, Code
- Hierarchical views
- Stakeholder communication
- _References: Simon Brown_

### 58. Runbook Documentation
- Operational procedures
- Incident response
- Troubleshooting guides
- _References: SRE practices_

### 59. API Documentation
- OpenAPI/Swagger specs
- Interactive documentation
- Examples and tutorials
- _References: OpenAPI Initiative_

### 60. README-Driven Development
- Write README first
- Project overview
- Getting started
- _References: Daniel Doubrovkine_

---

## Process & Workflow

### 61. Continuous Integration (CI)
- Automated builds
- Test on every commit
- Fast feedback
- _References: Martin Fowler_

### 62. Continuous Delivery (CD)
- Deployable at any time
- Automated deployment pipeline
- Feature flags
- _References: Jez Humble_

### 63. Continuous Deployment
- Auto-deploy to production
- Progressive delivery
- Monitoring gates
- _References: DORA metrics_

### 64. Trunk-Based Development
- Short-lived branches
- Frequent integration
- Feature toggles
- _References: Paul Hammant_

### 65. GitFlow Workflow
- Main, develop, feature branches
- Release branches
- Hotfix branches
- _References: Vincent Driessen_

### 66. GitHub Flow
- Simple branch model
- Pull requests
- Immediate deployment
- _References: GitHub_

### 67. Semantic Versioning
- MAJOR.MINOR.PATCH
- Breaking changes
- API compatibility
- _References: SemVer.org_

### 68. Conventional Commits
- Structured commit messages
- Automated changelog
- Semantic versioning
- _References: Conventional Commits_

### 69. Release Train
- Time-based releases
- Feature complete by date
- Regular cadence
- _References: SAFe_

### 70. Agile Methodologies
- Iterative development
- Adaptive planning
- Continuous improvement
- _References: Agile Manifesto_

### 71. Scrum
- Sprints
- Daily standups
- Sprint retrospectives
- _References: Scrum Guide_

### 72. Kanban
- Visual workflow
- WIP limits
- Continuous flow
- _References: David J. Anderson_

### 73. Shape Up
- 6-week cycles
- Hill charts
- Appetite-driven
- _References: Basecamp_

---

## Code Quality Practices

### 74. Code Review
- Peer inspection
- Knowledge sharing
- Quality gates
- _References: MR practices_

### 75. Pair Programming
- Driver and navigator
- Real-time review
- Collective ownership
- _References: XP practices_

### 76. Mob Programming
- Whole team, one machine
- Rotating driver
- Collective intelligence
- _References: Mob Programming_

### 77. Linting
- Automated style checks
- Code quality rules
- Consistent formatting
- _References: ESLint, Clippy_

### 78. Formatting
- Automated formatting
- Opinionated style
- No bike-shedding
- _References: Prettier, rustfmt_

### 79. Static Analysis
- Automated code analysis
- Bug detection
- Security scanning
- _References: SonarQube_

### 80. Dynamic Analysis
- Runtime behavior analysis
- Memory leak detection
- Performance profiling
- _References: Valgrind_

### 81. Code Complexity Analysis
- Cyclomatic complexity
- Cognitive complexity
- Maintainability index
- _References: Halstead metrics_

### 82. Dependency Analysis
- Vulnerability scanning
- License compliance
- Update management
- _References: Dependabot_

### 83. Dead Code Elimination
- Remove unused code
- Keep codebase lean
- Improve maintenance
- _References: Code coverage tools_

### 84. Technical Debt Tracking
- Measure and prioritize
- Allocate refactoring time
- Prevent accumulation
- _References: Wardley maps_

---

## Collaboration & Team Practices

### 85. Mob Programming
- Whole team development
- Continuous code review
- Shared learning
- _References: Mob Programming book_

### 86. Pair Rotations
- Regular pairing changes
- Knowledge distribution
- Fresh perspectives
- _References: XP practices_

### 87. Rubber Duck Debugging
- Explain code verbally
- Self-debugging technique
- Fresh perspective
- _References: Pragmatic Programmer_

### 88. 12-Factor App Methodology
- Cloud-native best practices
- Stateless processes
- Declarative configuration
- _References: Heroku_

### 89. SRE Practices
- Service Level Objectives
- Error budgets
- Toil reduction
- _References: Google SRE_

### 90. DevOps Culture
- Shared responsibility
- Automation first
- Feedback loops
- _References: DevOps Handbook_

---

## Operational Practices

### 91. Infrastructure as Code
- Version controlled infra
- Reproducible environments
- Automated provisioning
- _References: Terraform, Pulumi_

### 92. GitOps
- Git as single source of truth
- Automated deployments
- Drift detection
- _References: Weaveworks_

### 93. Observability
- Metrics, logs, traces
- Distributed tracing
- Alerting
- _References: OpenTelemetry_

### 94. Feature Flags
- Gradual rollouts
- A/B testing
- Quick rollbacks
- _References: LaunchDarkly_

### 95. Blue-Green Deployment
- Parallel environments
- Instant switchover
- Zero-downtime
- _References: AWS_

### 96. Canary Releases
- Incremental rollout
- Traffic splitting
- Monitoring gates
- _References: Release engineering_

### 97. ChatOps
- Runbooks in chat
- Incident collaboration
- Automated actions
- _References: GitHub, Slack_

### 98. Runbooks Automation
- Self-healing systems
- Automated remediation
- Documented procedures
- _References: SRE practices_

---

## Advanced Topics

### 99. Domain-Driven Design (DDD)
- Bounded contexts
- Ubiquitous language
- Aggregates, Entities, Value Objects
- _References: Evans 2003_

### 100. Strategic DDD
- Context mapping
- Core/Supporting/Generic domains
- Integration patterns
- _References: Evans, Vernon 2013_

### 101. Tactical DDD
- Building blocks
- Domain events
- Domain services
- _References: Vernon 2013_

### 102. CQRS + DDD
- Separation at domain level
- Event sourcing integration
- Read model optimization
- _References: DDD-CQRS-ES sample_

### 103. Event Storming
- Rapid domain discovery
- Business process modeling
- Stakeholder collaboration
- _References: Alberto Brandolini_

### 104. User Story Mapping
- User journey visualization
- Backlog organization
- Release planning
- _References: Jeff Patton_

### 105. Impact Mapping
- Goal alignment
- Strategic planning
- Metric definition
- _References: Gojko Adzic_

### 106. Example Mapping
- Clarify requirements
- Reduce ambiguity
- Discovery workshops
- _References: Cucumber_

### 107. Real-Time Risk Management
- Continuous risk assessment
- Mitigation strategies
- Risk-adjusted planning
- _References: Agile risk management_

### 108. Cumulative Flow Diagrams
- Work item visualization
- Bottleneck detection
- Throughput analysis
- _References: Kanban metrics_

### 109. Lead Time Optimization
- Idea to production
- Cycle time analysis
- Bottleneck removal
- _References: DORA metrics_

### 110. Deployment Frequency
- Ship small, ship often
- Reduced risk per change
- Continuous delivery maturity
- _References: DORA State of DevOps_

---

## Domain-Driven Design Extensions

### 111. Bounded Context
- Clear domain boundaries
- Explicit contracts
- Autonomous teams
- _References: Evans_

### 112. Context Mapping
- Relationship types
- Integration patterns
- Team structure
- _References: Strategic DDD_

### 113. Ubiquitous Language
- Shared vocabulary
- Domain experts + devs
- Living glossary
- _References: Evans_

### 114. Aggregate Pattern
- Consistency boundary
- Transaction scope
- Root entity
- _References: Evans, Vernon_

### 115. Repository Pattern
- Collection abstraction
- Persistence independence
- Domain-friendly API
- _References: Evans_

### 116. Factory Pattern (DDD)
- Complex creation
- Aggregate factories
- Encapsulation
- _References: Evans, GoF_

### 117. Domain Events
- Immutable event records
- Event sourcing
- Temporal modeling
- _References: Vernon_

### 118. Anti-Corruption Layer
- Protect domain model
- Adapter/translator
- Isolation layer
- _References: Evans_

### 119. Published Language
- Shared vocabulary
- Schema definition
- Integration contract
- _References: Evans_

### 120. Open Host Service
- Published protocol
- Integration API
- External access
- _References: Evans_

---

## Platform-Specific Practices

### 121. Rust: Ownership Model
- Memory safety without GC
- Borrow checker
- Lifetime annotations
- _References: Rust Book_

### 122. Rust: Zero-Cost Abstractions
- No runtime overhead
- Inline optimizations
- Performance-first
- _References: Rust ethos_

### 123. Go: Goroutine Patterns
- Concurrent execution
- Channel communication
- Select statements
- _References: Go concurrency patterns_

### 124. TypeScript: Type-Driven Development
- Strict typing
- Type guards
- Discriminated unions
- _References: TypeScript docs_

### 125. Python: Type Hints + Mypy
- Gradual typing
- Type checking
- IDE support
- _References: PEP 484_

### 126. Cloud-Native Patterns
- Sidecar pattern
- Ambassador pattern
- Adapter pattern
- _References: Cloud Design Patterns_

### 127. Kubernetes Patterns
- Operator pattern
- Sidecar pattern
- Init container pattern
- _References: Kubernetes docs_

### 128. GraphQL: Schema-First Development
- Schema definition
- Type safety
- Resolver implementation
- _References: GraphQL spec_

### 129. gRPC: Contract-First Development
- Proto definitions
- Code generation
- Contract testing
- _References: gRPC docs_

### 130. Event Streaming
- Kafka topics
- Consumer groups
- Exactly-once semantics
- _References: Kafka docs_

---

## Additional Practices

### 131. API-First Development
- Design APIs before code
- OpenAPI specs
- Mocking
- _References: API design_

### 132. Consumer-Driven Contracts
- Consumer defines needs
- Provider validates
- Pact testing
- _References: Pact_

### 133. Schema-First Development
- Define data schemas
- Type safety
- Validation
- _References: JSON Schema_

### 134. Golden Path Engineering
- Opinionated defaults
- Fast onboarding
- Best practice automation
- _References: Platform engineering_

### 135. Internal Developer Platform
- Self-service capabilities
- Reduced cognitive load
- Platform as product
- _References: Team Topologies_

### 136. Progressive Web App
- Offline capability
- Push notifications
- App-like experience
- _References: Google PWA_

### 137. Design System Engineering
- Component library
- Design tokens
- Documentation site
- _References: Storybook_

### 138. Accessibility-First Development
- WCAG compliance
- Screen reader support
- Keyboard navigation
- _References: A11y_

### 139. Internationalization (i18n)
- Locale support
- Translation management
- RTL support
- _References: i18n patterns_

### 140. Localization (L10n)
- Cultural adaptation
- Regional formats
- Content localization
- _References: L10n best practices_

---

## Meta-Practices & Integration Patterns

### 141. Decision Making Framework
- RACI for decisions
- Consensus seeking
- Escalation paths
- _Internal practice_

### 142. Escalation Patterns
- Clear escalation paths
- Time-boxed resolution
- Post-mortem culture
- _References: Incident management_

### 143. Wrap-Over Rules
- Standard operating procedures
- Governance overlay
- Exception handling
- _References: DinoForge practices_

### 144. Code Freeze Protocol
- Pre-release hardening
- Exception process
- Rollback triggers
- _References: Release management_

### 145. Architectural Review Board
- Cross-functional review
- Standards enforcement
- Technical governance
- _References: TOGAF_

### 146. Security Review Process
- Threat modeling
- Security testing
- Compliance validation
- _References: OWASP SAMM_

### 147. Privacy by Design
- Data minimization
- Consent management
- Right to erasure
- _References: GDPR_

### 148. Ethics in Engineering
- Ethical decision framework
- Bias detection
- Responsible AI
- _References: ACM ethics_

### 149. Sustainability Engineering
- Energy efficiency
- Carbon awareness
- Green software
- _References: Green Software Foundation_

### 150. Technical Due Diligence
- Codebase assessment
- Architecture review
- Risk identification
- _References: Engineering practices_

---

## Implementation Matrix

| Practice | Complexity | Team Size | Project Type | Maturity Level |
|----------|------------|-----------|--------------|----------------|
| TDD | Medium | 1+ | All | Foundation |
| BDD | High | 3+ | Business-facing | Intermediate |
| Hexagonal | High | 3+ | Complex domains | Advanced |
| CQRS | Very High | 5+ | Scalable systems | Expert |
| Event Sourcing | Very High | 5+ | Audit-critical | Expert |
| Microservices | Very High | 10+ | Large systems | Advanced |
| Trunk-Based | Medium | 3+ | Fast teams | Intermediate |
| GitOps | Medium | 4+ | Cloud-native | Intermediate |

---

## Quick Start Guides

### TDD Starter
```bash
# Red - Write failing test
# Green - Make it pass
# Refactor - Improve code
```

### Hexagonal Architecture Starter
```bash
# 1. Identify domain core
# 2. Define ports (interfaces)
# 3. Implement adapters
# 4. Wire via DI
```

### BDD Starter
```gherkin
Feature: User registration
  Scenario: Valid email registration
    Given I am on the registration page
    When I enter a valid email
    Then I should see success message
```

---

## Contributing

This is a living document. Submit PRs to add new methodologies or improve descriptions.

## License

MIT
