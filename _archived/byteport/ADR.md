# ADR — BytePort

## ADR-001 — NVMS/BytePort IaC Manifest Format

**Status:** Accepted

**Context:** Need a single-file format to describe multi-service applications and their AWS infrastructure requirements.

**Decision:** Use a custom NVMS manifest format (`.nvms` / `odin.nvms`) as the primary IaC definition file.

**Rationale:** NVMS provides a project-specific, concise manifest structure tailored to BytePort's deployment model. Avoids full Terraform/CloudFormation verbosity for portfolio-scale deployments.

**Alternatives Considered:**
- Terraform HCL: powerful but heavyweight for portfolio use cases
- Docker Compose: container-focused, not IaC for cloud provisioning
- Pulumi: programmatic but adds runtime dependency

---

## ADR-002 — AWS as Primary Deployment Target

**Status:** Accepted

**Context:** Need a cloud provider for hosting deployed portfolio projects.

**Decision:** Target AWS as the sole cloud provider for v1.

**Rationale:** Widest service coverage. Credentials via standard `~/.aws/credentials` or env vars. EC2, ECS, and Lambda cover the deployment patterns needed for portfolio projects.

**Alternatives Considered:**
- GCP: less familiar IAM model
- Azure: Windows-centric toolchain
- Fly.io / Railway: simpler but less control

---

## ADR-003 — Go Backend + Web Frontend Architecture

**Status:** Accepted

**Context:** Platform needs both a server-side deployment engine and a user-facing management frontend.

**Decision:** Go for the backend deployment engine (`backend/`), web frontend (`frontend/`) for management UI.

**Rationale:** Go provides excellent AWS SDK support and concurrency for running parallel deployment tasks. Web frontend decouples UI iteration from backend logic.

---

## ADR-004 — LLM-Assisted Portfolio Template Generation

**Status:** Accepted

**Context:** Generated portfolio widgets need human-readable descriptions and well-structured content, not just raw API data.

**Decision:** Integrate an LLM (OpenAI ChatGPT as default, LLaMA as local alternative) to enhance generated portfolio component text.

**Rationale:** LLMs can produce compelling project summaries from structured data. Two-backend strategy (cloud + local) avoids hard dependency on paid APIs.

**Alternatives Considered:**
- Template strings only: functional but produces generic copy
- Human-written descriptions: requires manual work per project, defeats automation goal

---

## ADR-005 — CLI-First Interface

**Status:** Accepted

**Context:** Developers interact with BytePort primarily during deployment workflows in their terminal.

**Decision:** CLI is the primary interface. Web UI is secondary for status/monitoring.

**Rationale:** CLI fits naturally into existing developer workflows and CI/CD pipelines. Scriptable and composable.
