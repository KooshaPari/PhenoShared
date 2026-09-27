# Functional Requirements — BytePort

## FR-MANIFEST — IaC Manifest

| ID | Requirement | Traces To |
|----|-------------|-----------|
| FR-MANIFEST-001 | The system SHALL parse a BytePort/NVMS manifest file defining app structure and infra | E1.1 |
| FR-MANIFEST-002 | The system SHALL validate the manifest against a defined schema and fail loudly on errors | E1.1 |
| FR-MANIFEST-003 | The manifest SHALL support defining multiple services within a single file | E1.2 |
| FR-MANIFEST-004 | Each service definition SHALL include: name, runtime, port, source repo reference | E1.2 |

## FR-DEPLOY — AWS Deployment

| ID | Requirement | Traces To |
|----|-------------|-----------|
| FR-DEPLOY-001 | The system SHALL provision AWS infrastructure described in the manifest | E2.1 |
| FR-DEPLOY-002 | Provisioned resources SHALL be visible in the AWS console after a successful deploy | E2.1 |
| FR-DEPLOY-003 | The system SHALL pull application source code from the specified GitHub repository | E2.2 |
| FR-DEPLOY-004 | Source pull SHALL use the branch or ref specified in the manifest | E2.2 |
| FR-DEPLOY-005 | The system SHALL output live endpoint URLs on successful deployment | E2.3 |
| FR-DEPLOY-006 | The system SHALL report per-service deployment status (success/failure/pending) | E2.3 |

## FR-PORTFOLIO — Portfolio UX Generation

| ID | Requirement | Traces To |
|----|-------------|-----------|
| FR-PORTFOLIO-001 | The system SHALL generate portfolio site component templates for each deployed project | E3.1 |
| FR-PORTFOLIO-002 | Generated templates SHALL include live endpoint URLs | E3.2 |
| FR-PORTFOLIO-003 | Generated templates SHALL provide UI widgets for interaction with the deployed project | E3.2 |
| FR-PORTFOLIO-004 | LLM-assisted text generation SHALL enhance template descriptions | E3.3 |
| FR-PORTFOLIO-005 | LLM integration SHALL support both OpenAI (ChatGPT) and local (LLaMA) backends | E3.3 |

## FR-CLI — CLI Interface

| ID | Requirement | Traces To |
|----|-------------|-----------|
| FR-CLI-001 | The `byteport deploy` command SHALL trigger the full deploy + portfolio generation pipeline | E4.1 |
| FR-CLI-002 | The `byteport status` command SHALL display health and endpoint for each deployed service | E4.2 |
| FR-CLI-003 | All CLI errors SHALL print a clear message to stderr and exit non-zero | E4.1 |
| FR-CLI-004 | The CLI SHALL read AWS credentials from environment variables or ~/.aws/credentials | E4.1 |
