# Feature Specification: Authvault Core

**Feature Branch**: `001-authvault-core`
**Created**: 2026-04-02
**Status**: Active
**Mission**: security

## Overview

Authvault is a hexagonal architecture-based authentication and authorization framework with OAuth2, JWT, and RBAC/ABAC support.

### Implemented Features

- JWT tokens with RS256/HS256
- OAuth2 client credentials flow
- Password hashing (argon2, bcrypt)
- RBAC with role hierarchy
- ABAC with attribute-based policies
- Session management with refresh tokens
- Rate limiting
- Audit logging

### Pending Features

- Multi-factor authentication
- Passwordless authentication
- Delegation and federation

## User Scenarios & Testing

### User Story 1 — User Authentication (Priority: P1)

A user registers and logs in with credentials.

**Given** a new user, **When** they register with email and password, **Then** their identity is stored securely with hashed password.

**Given** valid credentials, **When** a user logs in, **Then** they receive a JWT token with their roles and permissions.

### User Story 2 — Token Validation (Priority: P1)

An API validates incoming requests using JWT tokens.

**Given** a valid JWT token, **When** the API validates it, **Then** it returns the user's claims including roles.

**Given** an expired token, **When** validation is attempted, **Then** it returns an appropriate error.

### User Story 3 — Policy-Based Authorization (Priority: P1)

A user attempts to access a resource that requires specific attributes.

**Given** a user with attributes, **When** they access a protected resource, **Then** the policy engine evaluates their attributes against the resource policy.

**Given** a user without required attributes, **When** they access a protected resource, **Then** access is denied with appropriate error.

## Requirements

### Functional Requirements

- **FR-001**: System MUST support user registration with email and password
- **FR-002**: System MUST support user login with credential verification
- **FR-003**: System MUST generate JWT tokens with user claims
- **FR-004**: System MUST validate JWT tokens and extract claims
- **FR-005**: System MUST support RBAC with role hierarchy
- **FR-006**: System MUST support ABAC with attribute-based policies
- **FR-007**: System MUST hash passwords using argon2 or bcrypt
- **FR-008**: System MUST support session management with refresh tokens

### Non-Functional Requirements

- **NFR-001**: All domain logic must be pure (no external dependencies)
- **NFR-002**: Error types must use `thiserror` with `#[from]` conversions
- **NFR-003**: All public items must have rustdoc documentation

## Key Entities

- **Identity**: User entity with email, hashed password, roles
- **Claims**: JWT claims including user_id, roles, permissions
- **Policy**: Authorization rule with conditions and effects
- **Session**: Active session with refresh token support

## Acceptance Criteria

1. `cargo clippy -- -D warnings` passes with 0 warnings
2. `cargo test` passes all tests
3. `cargo doc` produces no missing documentation warnings
